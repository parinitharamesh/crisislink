"""Emergency updates service (MongoDB).

Pure data-layer logic: validation, query building and CRUD against the
``emergency_updates`` collection. No Flask objects in here, so it is easy to test.

Relationship to MySQL
---------------------
``incident_id`` refers to ``INCIDENT.incident_id`` in MySQL. MongoDB cannot enforce
foreign keys, so the *route layer* verifies the incident exists (see
``incident_exists``) when an update is created or its incident_id is changed.
Deleting an incident in MySQL does NOT cascade to MongoDB.
"""

import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING

from config.mongodb import (
    UPDATE_TYPES, UPDATE_STATUSES, UPDATE_PRIORITIES,
    get_collection, updates_collection_name,
)

TITLE_MIN, TITLE_MAX = 3, 200
MESSAGE_MIN, MESSAGE_MAX = 1, 5000
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
SORTABLE_FIELDS = {'created_at', 'updated_at', 'incident_id', 'title'}
EDITABLE_FIELDS = {'incident_id', 'title', 'message', 'update_type', 'status', 'priority'}


class ValidationError(Exception):
    """Raised with a dict of {field: message}."""

    def __init__(self, errors):
        super().__init__('Validation failed')
        self.errors = errors


# ── Helpers ──────────────────────────────────────────────────────────────────

def utcnow():
    # Naive UTC (PyMongo stores/returns naive UTC datetimes by default).
    # Truncated to milliseconds because that is MongoDB's date precision, so the
    # value returned on create is identical to what is read back later.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(microsecond=(now.microsecond // 1000) * 1000)


def collection():
    return get_collection(updates_collection_name())


def parse_object_id(value):
    """Return ObjectId or raise ValidationError for malformed IDs."""
    if not isinstance(value, str) or len(value) != 24:
        raise ValidationError({'update_id': 'Invalid update ID'})
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ValidationError({'update_id': 'Invalid update ID'})


def _parse_positive_int(value, field):
    if isinstance(value, bool):
        raise ValidationError({field: f'{field} must be a positive integer'})
    if isinstance(value, float):
        if not value.is_integer():
            raise ValidationError({field: f'{field} must be a positive integer'})
        value = int(value)
    if isinstance(value, str):
        if not re.fullmatch(r'\d{1,10}', value.strip()):
            raise ValidationError({field: f'{field} must be a positive integer'})
        value = int(value.strip())
    if not isinstance(value, int) or value < 1:
        raise ValidationError({field: f'{field} must be a positive integer'})
    return value


def _parse_enum(value, allowed, field):
    if not isinstance(value, str) or value.strip().upper() not in allowed:
        raise ValidationError({field: f'{field} must be one of {allowed}'})
    return value.strip().upper()


def _parse_text(value, field, lo, hi):
    if not isinstance(value, str):
        raise ValidationError({field: f'{field} must be a string'})
    value = value.strip()
    if len(value) < lo:
        raise ValidationError({field: f'{field} must be at least {lo} character(s)'})
    if len(value) > hi:
        raise ValidationError({field: f'{field} must be at most {hi} characters'})
    return value


def _collect(fn, errors, *args):
    try:
        return fn(*args)
    except ValidationError as exc:
        errors.update(exc.errors)
        return None


def serialize(doc):
    """Convert a Mongo document into a JSON-safe dict."""
    if doc is None:
        return None
    out = dict(doc)
    out['_id'] = str(out['_id'])
    for key in ('created_at', 'updated_at'):
        if isinstance(out.get(key), datetime):
            out[key] = out[key].isoformat() + 'Z'
    return out


# ── Validation ───────────────────────────────────────────────────────────────

def validate_create(data):
    """Validate a create payload; returns the cleaned fields."""
    if not isinstance(data, dict):
        raise ValidationError({'body': 'JSON object body is required'})

    errors = {}
    for field in ('incident_id', 'title', 'message'):
        if data.get(field) in (None, ''):
            errors[field] = f'{field} is required'

    clean = {}
    if 'incident_id' not in errors:
        clean['incident_id'] = _collect(_parse_positive_int, errors, data['incident_id'], 'incident_id')
    if 'title' not in errors:
        clean['title'] = _collect(_parse_text, errors, data['title'], 'title', TITLE_MIN, TITLE_MAX)
    if 'message' not in errors:
        clean['message'] = _collect(_parse_text, errors, data['message'], 'message', MESSAGE_MIN, MESSAGE_MAX)

    clean['update_type'] = _collect(_parse_enum, errors, data.get('update_type', 'GENERAL'), UPDATE_TYPES, 'update_type')
    clean['status'] = _collect(_parse_enum, errors, data.get('status', 'ACTIVE'), UPDATE_STATUSES, 'status')
    clean['priority'] = _collect(_parse_enum, errors, data.get('priority', 'MEDIUM'), UPDATE_PRIORITIES, 'priority')

    if errors:
        raise ValidationError(errors)
    return clean


def validate_update(data):
    """Validate a partial-update payload; returns only the editable fields supplied."""
    if not isinstance(data, dict) or not data:
        raise ValidationError({'body': 'JSON object body with at least one field is required'})

    unknown = set(data) - EDITABLE_FIELDS
    if unknown:
        raise ValidationError({'body': f'Fields not editable or unknown: {sorted(unknown)}'})

    errors = {}
    clean = {}
    if 'incident_id' in data:
        clean['incident_id'] = _collect(_parse_positive_int, errors, data['incident_id'], 'incident_id')
    if 'title' in data:
        clean['title'] = _collect(_parse_text, errors, data['title'], 'title', TITLE_MIN, TITLE_MAX)
    if 'message' in data:
        clean['message'] = _collect(_parse_text, errors, data['message'], 'message', MESSAGE_MIN, MESSAGE_MAX)
    if 'update_type' in data:
        clean['update_type'] = _collect(_parse_enum, errors, data['update_type'], UPDATE_TYPES, 'update_type')
    if 'status' in data:
        clean['status'] = _collect(_parse_enum, errors, data['status'], UPDATE_STATUSES, 'status')
    if 'priority' in data:
        clean['priority'] = _collect(_parse_enum, errors, data['priority'], UPDATE_PRIORITIES, 'priority')

    if errors:
        raise ValidationError(errors)
    return clean


def parse_list_params(args, role=''):
    """Turn query-string args into (mongo_query, sort_spec, page, limit)."""
    errors = {}
    query = {}

    if args.get('incident_id'):
        v = _collect(_parse_positive_int, errors, args.get('incident_id'), 'incident_id')
        if v is not None:
            query['incident_id'] = v
    if args.get('status'):
        v = _collect(_parse_enum, errors, args.get('status'), UPDATE_STATUSES, 'status')
        if v is not None:
            query['status'] = v
    if args.get('priority'):
        v = _collect(_parse_enum, errors, args.get('priority'), UPDATE_PRIORITIES, 'priority')
        if v is not None:
            query['priority'] = v
    if args.get('update_type'):
        v = _collect(_parse_enum, errors, args.get('update_type'), UPDATE_TYPES, 'update_type')
        if v is not None:
            query['update_type'] = v
    if args.get('search'):
        pattern = re.escape(args.get('search').strip()[:100])
        if pattern:
            query['$or'] = [
                {'title': {'$regex': pattern, '$options': 'i'}},
                {'message': {'$regex': pattern, '$options': 'i'}},
            ]

    # Citizens never see DRAFT updates
    if role == 'CITIZEN':
        if query.get('status') == 'DRAFT':
            query['status'] = {'$in': []}          # matches nothing
        elif 'status' not in query:
            query['status'] = {'$ne': 'DRAFT'}

    sort_by = args.get('sort_by', 'created_at')
    if sort_by not in SORTABLE_FIELDS:
        errors['sort_by'] = f'sort_by must be one of {sorted(SORTABLE_FIELDS)}'
    order = args.get('order', 'desc').lower()
    if order not in ('asc', 'desc'):
        errors['order'] = "order must be 'asc' or 'desc'"

    page = limit = None
    try:
        page = int(args.get('page', 1))
        limit = int(args.get('limit', DEFAULT_PAGE_SIZE))
        if page < 1 or limit < 1:
            raise ValueError
    except (TypeError, ValueError):
        errors['pagination'] = 'page and limit must be positive integers'
    if limit is not None and limit > MAX_PAGE_SIZE:
        limit = MAX_PAGE_SIZE

    if errors:
        raise ValidationError(errors)

    direction = ASCENDING if order == 'asc' else DESCENDING
    sort_spec = [(sort_by, direction), ('_id', direction)]
    return query, sort_spec, page, limit


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_update(clean, user_id, user_name=''):
    now = utcnow()
    doc = {
        **clean,
        'created_by': int(user_id),
        'created_by_name': user_name or '',
        'updated_by': None,
        'created_at': now,
        'updated_at': now,
    }
    result = collection().insert_one(doc)
    doc['_id'] = result.inserted_id
    return serialize(doc)


def list_updates(query, sort_spec, page, limit):
    col = collection()
    total = col.count_documents(query)
    docs = list(col.find(query).sort(sort_spec).skip((page - 1) * limit).limit(limit))
    return {
        'updates': [serialize(d) for d in docs],
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit if total else 0,
    }


def get_update(update_id, role=''):
    doc = collection().find_one({'_id': parse_object_id(update_id)})
    if doc and role == 'CITIZEN' and doc.get('status') == 'DRAFT':
        return None
    return serialize(doc)


def get_raw(update_id):
    return collection().find_one({'_id': parse_object_id(update_id)})


def apply_update(update_id, clean, user_id):
    """Apply a validated partial update; returns the updated document (or None)."""
    fields = dict(clean)
    fields['updated_at'] = utcnow()
    fields['updated_by'] = int(user_id)
    result = collection().update_one({'_id': parse_object_id(update_id)}, {'$set': fields})
    if result.matched_count == 0:
        return None
    return serialize(get_raw(update_id))


def delete_update(update_id):
    """Delete exactly one document by its _id. Returns True if deleted."""
    result = collection().delete_one({'_id': parse_object_id(update_id)})
    return result.deleted_count == 1


def analytics():
    """Aggregation pipelines: counts by status / priority / type and busiest incidents."""
    col = collection()

    def group_by(field):
        rows = col.aggregate([
            {'$group': {'_id': f'${field}', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1, '_id': 1}},
        ])
        return {r['_id']: r['count'] for r in rows}

    top_incidents = [
        {'incident_id': r['_id'], 'update_count': r['count'], 'last_update': r['last']}
        for r in col.aggregate([
            {'$group': {'_id': '$incident_id', 'count': {'$sum': 1}, 'last': {'$max': '$created_at'}}},
            {'$sort': {'count': -1, '_id': 1}},
            {'$limit': 5},
        ])
    ]
    for r in top_incidents:
        if isinstance(r['last_update'], datetime):
            r['last_update'] = r['last_update'].isoformat() + 'Z'

    return {
        'total': col.count_documents({}),
        'by_status': group_by('status'),
        'by_priority': group_by('priority'),
        'by_update_type': group_by('update_type'),
        'top_incidents': top_incidents,
    }


# ── MySQL cross-reference ────────────────────────────────────────────────────

def incident_exists(incident_id):
    """Check MySQL for INCIDENT.incident_id. Returns True / False, or None if MySQL
    could not be queried (caller decides how to react)."""
    try:
        from config.database import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM INCIDENT WHERE incident_id = %s', (incident_id,))
                return cur.fetchone() is not None
    except Exception:
        return None

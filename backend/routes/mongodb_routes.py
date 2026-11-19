"""MongoDB routes – incident reports, emergency updates (Phase B CRUD), analytics."""

import os
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from pymongo.errors import PyMongoError
from config.mongodb import get_collection, init_mongo_collections, mongo_is_available
from middleware.auth_middleware import role_required
from services import emergency_updates_service as updates_svc
from services.emergency_updates_service import ValidationError
from datetime import datetime
from bson import ObjectId

mongo_bp = Blueprint('mongo', __name__)


def oid_to_str(doc):
    """Convert ObjectId fields to strings for JSON serialization."""
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


# ─── INCIDENT REPORTS ────────────────────────────────────────────────────────

@mongo_bp.route('/reports', methods=['GET'])
def get_reports():
    """GET all incident reports with optional filtering."""
    try:
        verify_jwt_in_request()
        collection = get_collection('incident_reports')

        inc_id   = request.args.get('incident_id')
        tag      = request.args.get('tag')
        search   = request.args.get('search')

        query = {}
        if inc_id:
            query['incident_id'] = int(inc_id)
        if tag:
            query['tags'] = {'$in': [tag]}
        if search:
            query['$text'] = {'$search': search}

        # MongoDB FIND with projection, filtering, sorting
        docs = list(
            collection.find(
                query,
                projection={
                    'title': 1, 'incident_id': 1, 'report_date': 1,
                    'severity': 1, 'tags': 1, 'author': 1, '_id': 1
                }
            ).sort('report_date', -1).limit(50)
        )

        return jsonify({'reports': [oid_to_str(d) for d in docs]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mongo_bp.route('/reports', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_report():
    """INSERT a new incident report document."""
    data = request.get_json()
    if not data.get('title') or not data.get('incident_id'):
        return jsonify({'error': 'title and incident_id are required'}), 400

    uid = get_jwt_identity()
    casualties = data.get('casualties') or {}
    doc = {
        'incident_id':   int(data['incident_id']),
        'title':         data['title'],
        'content':       data.get('content', ''),
        'severity':      data.get('severity', 'MEDIUM'),
        'affected_zones':data.get('affected_zones', []),
        'casualties': {
            'deaths':   data.get('deaths', casualties.get('deaths', 0)),
            'injured':  data.get('injured', casualties.get('injured', 0)),
            'missing':  data.get('missing', casualties.get('missing', 0))
        },
        'resources_deployed': data.get('resources_deployed', []),
        'tags':          data.get('tags', []),
        'author':        uid,
        'report_date':   datetime.utcnow(),
        'last_updated':  datetime.utcnow()
    }

    try:
        collection = get_collection('incident_reports')
        result = collection.insert_one(doc)
        return jsonify({'message': 'Report created', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mongo_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    try:
        verify_jwt_in_request()
        collection = get_collection('incident_reports')
        doc = collection.find_one({'_id': ObjectId(report_id)})
        if not doc:
            return jsonify({'error': 'Report not found'}), 404
        return jsonify({'report': oid_to_str(doc)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mongo_bp.route('/reports/<report_id>', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_report(report_id):
    """UPDATE a report document."""
    data = request.get_json()
    update_fields = {k: v for k, v in data.items() if k != '_id'}
    update_fields['last_updated'] = datetime.utcnow()

    try:
        collection = get_collection('incident_reports')
        result = collection.update_one(
            {'_id': ObjectId(report_id)},
            {'$set': update_fields}
        )
        if result.matched_count == 0:
            return jsonify({'error': 'Report not found'}), 404
        return jsonify({'message': 'Report updated', 'modified': result.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mongo_bp.route('/reports/<report_id>', methods=['DELETE'])
@role_required('ADMIN')
def delete_report(report_id):
    """DELETE a report document."""
    try:
        collection = get_collection('incident_reports')
        result = collection.delete_one({'_id': ObjectId(report_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Report not found'}), 404
        return jsonify({'message': 'Report deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── EMERGENCY UPDATES (Phase B – full CRUD on `emergency_updates`) ─────────────
#
# Authorization matrix
#   READ    any authenticated user (CITIZEN cannot see DRAFT updates)
#   CREATE  ADMIN, COORDINATOR
#   UPDATE  ADMIN (any update) / COORDINATOR (only updates they created)
#   DELETE  ADMIN only
#
# `incident_id` references MySQL INCIDENT.incident_id (verified at write time;
# MongoDB itself does not enforce the relationship).

def _json_error(message, status, **extra):
    body = {'error': message}
    body.update(extra)
    return jsonify(body), status


def mongo_guarded(fn):
    """Map validation / MongoDB failures to clean JSON responses.

    MongoDB being down returns 503 for these routes only - the MySQL-backed
    endpoints are unaffected. Raw exception text (which may contain the
    connection string) is never returned to the client.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValidationError as exc:
            return _json_error('Validation failed', 400, details=exc.errors)
        except PyMongoError as exc:
            current_app.logger.error('MongoDB error: %s', type(exc).__name__)
            return _json_error('MongoDB is currently unavailable', 503)
        except Exception as exc:  # pragma: no cover - last-resort safety net
            current_app.logger.exception('Unexpected error in emergency updates route')
            return _json_error('Internal server error', 500)
    return wrapper


def _verify_incident(incident_id):
    """Return an error response tuple if the MySQL incident is missing/unreachable, else None."""
    if os.environ.get('EMERGENCY_UPDATES_VERIFY_INCIDENT', 'true').lower() != 'true':
        return None
    exists = updates_svc.incident_exists(incident_id)
    if exists is None:
        return _json_error('Cannot verify incident: relational database unavailable', 503)
    if not exists:
        return _json_error('Incident not found', 404, details={'incident_id': f'Incident {incident_id} does not exist'})
    return None


@mongo_bp.route('/status', methods=['GET'])
def mongo_status():
    """Lightweight availability probe for the frontend."""
    verify_jwt_in_request()
    return jsonify({'mongodb': 'up' if mongo_is_available() else 'down'}), 200


@mongo_bp.route('/updates', methods=['GET'])
@mongo_guarded
def get_updates():
    verify_jwt_in_request()
    query, sort_spec, page, limit = updates_svc.parse_list_params(
        request.args, role=get_jwt().get('role', ''))
    return jsonify(updates_svc.list_updates(query, sort_spec, page, limit)), 200


@mongo_bp.route('/updates', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
@mongo_guarded
def post_update():
    clean = updates_svc.validate_create(request.get_json(silent=True))
    err = _verify_incident(clean['incident_id'])
    if err:
        return err
    claims = get_jwt()
    doc = updates_svc.create_update(clean, get_jwt_identity(), claims.get('name', ''))
    return jsonify({'message': 'Update created', 'id': doc['_id'], 'update': doc}), 201


@mongo_bp.route('/updates/analytics', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
@mongo_guarded
def updates_analytics():
    return jsonify({'analytics': updates_svc.analytics()}), 200


@mongo_bp.route('/updates/<update_id>', methods=['GET'])
@mongo_guarded
def get_update(update_id):
    verify_jwt_in_request()
    doc = updates_svc.get_update(update_id, role=get_jwt().get('role', ''))
    if doc is None:
        return _json_error('Update not found', 404)
    return jsonify({'update': doc}), 200


@mongo_bp.route('/updates/<update_id>', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
@mongo_guarded
def put_update(update_id):
    existing = updates_svc.get_raw(update_id)          # 400 on malformed id
    if existing is None:
        return _json_error('Update not found', 404)

    claims = get_jwt()
    uid = int(get_jwt_identity())
    if claims.get('role') != 'ADMIN' and existing.get('created_by') != uid:
        return _json_error('Access denied. Coordinators can only edit their own updates', 403)

    clean = updates_svc.validate_update(request.get_json(silent=True))
    if 'incident_id' in clean and clean['incident_id'] != existing.get('incident_id'):
        err = _verify_incident(clean['incident_id'])
        if err:
            return err

    doc = updates_svc.apply_update(update_id, clean, uid)
    if doc is None:
        return _json_error('Update not found', 404)
    return jsonify({'message': 'Update saved', 'update': doc}), 200


@mongo_bp.route('/updates/<update_id>', methods=['DELETE'])
@role_required('ADMIN')
@mongo_guarded
def remove_update(update_id):
    if not updates_svc.delete_update(update_id):       # 400 on malformed id
        return _json_error('Update not found', 404)
    return jsonify({'message': 'Update deleted', 'id': update_id}), 200


# ─── AGGREGATION PIPELINE DEMO ───────────────────────────────────────────────

@mongo_bp.route('/reports/analytics', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def report_analytics():
    """
    MongoDB Aggregation Pipeline demonstration (Unit 4 – NoSQL).
    Groups incident reports by severity, counts and sums casualties.
    """
    try:
        collection = get_collection('incident_reports')
        pipeline = [
            # Stage 1: Filter only reports with content
            {'$match': {'content': {'$exists': True, '$ne': ''}}},
            # Stage 2: Group by severity
            {'$group': {
                '_id':           '$severity',
                'report_count':  {'$sum': 1},
                'total_deaths':  {'$sum': '$casualties.deaths'},
                'total_injured': {'$sum': '$casualties.injured'},
                'total_missing': {'$sum': '$casualties.missing'},
                'unique_incidents': {'$addToSet': '$incident_id'}
            }},
            # Stage 3: Project output shape
            {'$project': {
                'severity':         '$_id',
                'report_count':     1,
                'total_deaths':     1,
                'total_injured':    1,
                'total_missing':    1,
                'incident_count':   {'$size': '$unique_incidents'},
                '_id': 0
            }},
            # Stage 4: Sort by severity criticality
            {'$sort': {'total_deaths': -1}}
        ]
        result = list(collection.aggregate(pipeline))
        return jsonify({'analytics': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mongo_bp.route('/init', methods=['POST'])
@role_required('ADMIN')
def init_collections():
    """Initialize MongoDB collections and seed data."""
    try:
        init_mongo_collections()

        # Seed some initial knowledge documents
        reports = get_collection('incident_reports')
        if reports.count_documents({}) == 0:
            seed_docs = [
                {
                    'incident_id': 1,
                    'title': 'Kerala Flood 2024 – Initial Assessment',
                    'content': 'Severe flooding in northern Kerala. Ernakulam district worst affected. '
                               'Over 5000 families displaced. Key roads blocked. Rescue operations ongoing.',
                    'severity': 'CRITICAL',
                    'affected_zones': ['Ernakulam', 'Aluva', 'Perumbavoor'],
                    'casualties': {'deaths': 12, 'injured': 45, 'missing': 8},
                    'resources_deployed': ['NDRF boats', 'Army helicopters', 'Medical teams'],
                    'tags': ['flood', 'kerala', 'rescue', 'evacuation'],
                    'author': 'system',
                    'report_date': datetime.utcnow(),
                    'last_updated': datetime.utcnow()
                },
                {
                    'incident_id': 2,
                    'title': 'Cyclone Biparjoy – Puri Impact Report',
                    'content': 'Cyclone made landfall near Puri. Coastal communities severely affected. '
                               'Evacuation completed before landfall. Relief distribution underway.',
                    'severity': 'HIGH',
                    'affected_zones': ['Puri', 'Jagatsinghpur', 'Kendrapara'],
                    'casualties': {'deaths': 3, 'injured': 22, 'missing': 1},
                    'resources_deployed': ['Odisha SDRF teams', 'Medical camps', 'Relief food packs'],
                    'tags': ['cyclone', 'odisha', 'coastal', 'evacuation'],
                    'author': 'system',
                    'report_date': datetime.utcnow(),
                    'last_updated': datetime.utcnow()
                },
                {
                    'incident_id': 3,
                    'title': 'Assam Flood 2024 – Weekly Situation Report',
                    'content': 'Brahmaputra river overflow continues. Over 2 lakh people affected in Kamrup. '
                               'Relief camps operational at 6 locations. Food and water distribution in progress.',
                    'severity': 'HIGH',
                    'affected_zones': ['Kamrup', 'Morigaon', 'Nagaon'],
                    'casualties': {'deaths': 18, 'injured': 67, 'missing': 15},
                    'resources_deployed': ['NDRF teams', 'Rescue boats', 'Food rations', 'Medical units'],
                    'tags': ['flood', 'assam', 'brahmaputra', 'relief', 'evacuation'],
                    'author': 'system',
                    'report_date': datetime.utcnow(),
                    'last_updated': datetime.utcnow()
                }
            ]
            reports.insert_many(seed_docs)

        return jsonify({'message': 'MongoDB initialized with seed data'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

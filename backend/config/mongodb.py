"""MongoDB connection and collection helpers.

Configuration (all optional, read from the environment / root .env):
    MONGO_URI                   default: mongodb://localhost:27017   (no credentials)
    MONGO_DB_NAME               default: crisislink_nosql
    MONGO_UPDATES_COLLECTION    default: emergency_updates
    MONGO_TIMEOUT_MS            default: 3000  (fail fast when MongoDB is down)

Credentials must only ever come from the environment - never hard-code them.
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import PyMongoError

_client = None

# ── Emergency updates schema (documented in docs/MONGODB_PHASE_B.md) ─────────
UPDATE_TYPES = ['GENERAL', 'STATUS', 'WARNING', 'EVACUATION', 'RESOURCE', 'WEATHER', 'ROAD_CLOSURE']
UPDATE_STATUSES = ['DRAFT', 'ACTIVE', 'RESOLVED', 'ARCHIVED']
UPDATE_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

EMERGENCY_UPDATES_VALIDATOR = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['incident_id', 'title', 'message', 'update_type', 'status',
                     'priority', 'created_by', 'created_at', 'updated_at'],
        'properties': {
            'incident_id':     {'bsonType': ['int', 'long'], 'minimum': 1},
            'title':           {'bsonType': 'string', 'minLength': 3, 'maxLength': 200},
            'message':         {'bsonType': 'string', 'minLength': 1, 'maxLength': 5000},
            'update_type':     {'enum': UPDATE_TYPES},
            'status':          {'enum': UPDATE_STATUSES},
            'priority':        {'enum': UPDATE_PRIORITIES},
            'created_by':      {'bsonType': ['int', 'long']},
            'created_by_name': {'bsonType': 'string'},
            'updated_by':      {'bsonType': ['int', 'long', 'null']},
            'created_at':      {'bsonType': 'date'},
            'updated_at':      {'bsonType': 'date'},
        },
    }
}


def updates_collection_name() -> str:
    return os.environ.get('MONGO_UPDATES_COLLECTION', 'emergency_updates')


def get_mongo_client():
    global _client
    if _client is None:
        uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
        timeout = int(os.environ.get('MONGO_TIMEOUT_MS', '3000'))
        _client = MongoClient(uri, serverSelectionTimeoutMS=timeout)
    return _client


def get_mongo_db():
    client = get_mongo_client()
    return client[os.environ.get('MONGO_DB_NAME', 'crisislink_nosql')]


def get_collection(name: str):
    return get_mongo_db()[name]


def mongo_is_available() -> bool:
    """Cheap ping used by health checks. Never raises."""
    try:
        get_mongo_client().admin.command('ping')
        return True
    except Exception:
        return False


def init_emergency_updates_collection():
    """Create the emergency_updates collection with validator + indexes.

    Idempotent: safe to call repeatedly. Returns the collection.
    """
    db = get_mongo_db()
    name = updates_collection_name()
    if name not in db.list_collection_names():
        try:
            db.create_collection(name, validator=EMERGENCY_UPDATES_VALIDATOR,
                                 validationAction='error')
        except (PyMongoError, NotImplementedError):
            # Some servers/mocks may reject validators; app-level validation still applies.
            db.create_collection(name)
    else:
        try:
            db.command('collMod', name, validator=EMERGENCY_UPDATES_VALIDATOR,
                       validationAction='error')
        except (PyMongoError, NotImplementedError):
            pass

    col = db[name]
    col.create_index([('incident_id', ASCENDING), ('created_at', DESCENDING)],
                     name='idx_incident_created')
    col.create_index([('status', ASCENDING), ('priority', ASCENDING)],
                     name='idx_status_priority')
    col.create_index([('update_type', ASCENDING)], name='idx_update_type')
    col.create_index([('created_at', DESCENDING)], name='idx_created_at')
    col.create_index([('created_by', ASCENDING)], name='idx_created_by')
    return col


def init_mongo_collections():
    """Initialize collections and indexes (existing + Phase B)."""
    db = get_mongo_db()

    # incident_reports collection
    reports = db['incident_reports']
    reports.create_index([('incident_id', ASCENDING)])
    reports.create_index([('report_date', DESCENDING)])
    reports.create_index([('tags', ASCENDING)])
    reports.create_index([('title', TEXT), ('content', TEXT)])

    # situation_updates collection (legacy - kept for backward compatibility)
    updates = db['situation_updates']
    updates.create_index([('incident_id', ASCENDING)])
    updates.create_index([('timestamp', DESCENDING)])

    # field_observations collection
    observations = db['field_observations']
    observations.create_index([('location', '2dsphere')])
    observations.create_index([('incident_id', ASCENDING)])

    # Phase B: emergency_updates
    init_emergency_updates_collection()

    print("[MongoDB] Collections and indexes initialized.")

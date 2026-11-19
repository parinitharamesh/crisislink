"""
Phase B tests - MongoDB emergency updates CRUD (Flask test client).

Isolation / safety
------------------
* Uses database ``crisislink_test`` and collection ``emergency_updates_test`` ONLY.
  The suite refuses to run if the database name does not contain "test".
* Your real ``crisislink_nosql`` data and all MySQL data are never touched
  (MySQL is not contacted; the incident lookup is stubbed).

Two modes
---------
1. Default (no MongoDB server needed): an in-memory ``mongomock`` client.
2. Real MongoDB: set TEST_MONGO_URI, e.g.
       $env:TEST_MONGO_URI = "mongodb://localhost:27017"
   The same tests then run against your local mongod (test collection only).

Run from the backend folder:
    python -m pytest tests/test_mongo_updates.py -v
"""
import os
import sys
import time

import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BACKEND_DIR)

os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-not-for-production-use-0123456789'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['MONGO_DB_NAME'] = 'crisislink_test'
os.environ['MONGO_UPDATES_COLLECTION'] = 'emergency_updates_test'
os.environ['EMERGENCY_UPDATES_VERIFY_INCIDENT'] = 'true'

assert 'test' in os.environ['MONGO_DB_NAME'], 'Refusing to run tests against a non-test database'

from flask_jwt_extended import create_access_token        # noqa: E402
from pymongo import MongoClient                            # noqa: E402
from pymongo.errors import ServerSelectionTimeoutError     # noqa: E402

import config.mongodb as mongo_cfg                         # noqa: E402
from services import emergency_updates_service as svc      # noqa: E402
from app import create_app                                 # noqa: E402

KNOWN_INCIDENTS = {1, 2, 3}
BASE = '/api/mongo/updates'


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def mongo_client():
    real_uri = os.environ.get('TEST_MONGO_URI')
    if real_uri:
        client = MongoClient(real_uri, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')          # fail loudly if the URI is wrong
    else:
        import mongomock
        client = mongomock.MongoClient()
    return client


@pytest.fixture()
def app(mongo_client, monkeypatch):
    mongo_cfg._client = mongo_client
    monkeypatch.setattr(svc, 'incident_exists', lambda i: i in KNOWN_INCIDENTS)
    mongo_client['crisislink_test']['emergency_updates_test'].drop()   # test collection only
    mongo_cfg.init_emergency_updates_collection()
    application = create_app()
    application.config['TESTING'] = True
    yield application
    mongo_client['crisislink_test']['emergency_updates_test'].drop()
    mongo_cfg._client = None


@pytest.fixture()
def client(app):
    return app.test_client()


def _token(app, user_id, role, name='Test User'):
    with app.app_context():
        return {'Authorization': 'Bearer ' + create_access_token(
            identity=str(user_id), additional_claims={'role': role, 'name': name})}


@pytest.fixture()
def admin(app):
    return _token(app, 1, 'ADMIN', 'Admin A')


@pytest.fixture()
def coord(app):
    return _token(app, 2, 'COORDINATOR', 'Coord B')


@pytest.fixture()
def coord2(app):
    return _token(app, 3, 'COORDINATOR', 'Coord C')


@pytest.fixture()
def citizen(app):
    return _token(app, 4, 'CITIZEN', 'Citizen D')


def payload(**over):
    body = {'incident_id': 1, 'title': 'Bridge closed', 'message': 'NH-47 bridge closed due to flooding.',
            'update_type': 'ROAD_CLOSURE', 'status': 'ACTIVE', 'priority': 'HIGH'}
    body.update(over)
    return body


def create(client, headers, **over):
    r = client.post(BASE, json=payload(**over), headers=headers)
    assert r.status_code == 201, r.get_json()
    return r.get_json()['update']


# ── CREATE ───────────────────────────────────────────────────────────────────

def test_create_success(client, coord):
    r = client.post(BASE, json=payload(), headers=coord)
    body = r.get_json()
    assert r.status_code == 201
    u = body['update']
    assert body['id'] == u['_id'] and len(u['_id']) == 24
    assert u['incident_id'] == 1 and u['title'] == 'Bridge closed'
    assert u['update_type'] == 'ROAD_CLOSURE' and u['status'] == 'ACTIVE' and u['priority'] == 'HIGH'
    assert u['created_by'] == 2 and u['created_by_name'] == 'Coord B'
    assert u['created_at'] and u['updated_at'] and u['created_at'] == u['updated_at']


def test_create_applies_defaults(client, admin):
    r = client.post(BASE, json={'incident_id': 2, 'title': 'Hello', 'message': 'World'}, headers=admin)
    u = r.get_json()['update']
    assert r.status_code == 201
    assert (u['update_type'], u['status'], u['priority']) == ('GENERAL', 'ACTIVE', 'MEDIUM')


@pytest.mark.parametrize('missing', ['incident_id', 'title', 'message'])
def test_create_missing_required_field(client, coord, missing):
    body = payload()
    del body[missing]
    r = client.post(BASE, json=body, headers=coord)
    assert r.status_code == 400
    assert missing in r.get_json()['details']


def test_create_empty_body(client, coord):
    assert client.post(BASE, json={}, headers=coord).status_code == 400


def test_create_non_json_body(client, coord):
    r = client.post(BASE, data='not json', content_type='text/plain', headers=coord)
    assert r.status_code == 400


@pytest.mark.parametrize('field,value', [
    ('incident_id', 'abc'), ('incident_id', -5), ('incident_id', 0), ('incident_id', 1.5), ('incident_id', True),
    ('title', 'ab'), ('title', 'x' * 201), ('title', 123), ('message', ' '), ('message', 'm' * 5001),
    ('update_type', 'NOPE'), ('status', 'DONE'), ('priority', 'URGENT'), ('priority', 5),
])
def test_create_invalid_input(client, coord, field, value):
    r = client.post(BASE, json=payload(**{field: value}), headers=coord)
    assert r.status_code == 400, (field, value, r.get_json())
    assert field in r.get_json()['details']


def test_create_enum_is_case_insensitive_and_trimmed(client, coord):
    u = create(client, coord, title='  Padded title  ', priority='critical')
    assert u['title'] == 'Padded title' and u['priority'] == 'CRITICAL'


def test_create_unknown_incident_returns_404(client, coord):
    r = client.post(BASE, json=payload(incident_id=999), headers=coord)
    assert r.status_code == 404


def test_create_when_mysql_unavailable_returns_503(client, coord, monkeypatch):
    monkeypatch.setattr(svc, 'incident_exists', lambda i: None)
    assert client.post(BASE, json=payload(), headers=coord).status_code == 503


# ── READ ─────────────────────────────────────────────────────────────────────

def test_get_all(client, admin, coord):
    create(client, coord, title='First one')
    create(client, coord, title='Second one', incident_id=2)
    r = client.get(BASE, headers=admin)
    body = r.get_json()
    assert r.status_code == 200
    assert body['total'] == 2 and len(body['updates']) == 2
    assert {'page', 'limit', 'pages'} <= set(body)


def test_get_all_empty(client, admin):
    body = client.get(BASE, headers=admin).get_json()
    assert body['updates'] == [] and body['total'] == 0 and body['pages'] == 0


def test_get_by_id(client, admin, coord):
    created = create(client, coord)
    r = client.get(f'{BASE}/{created["_id"]}', headers=admin)
    assert r.status_code == 200
    assert r.get_json()['update'] == created


def test_get_by_id_not_found(client, admin):
    assert client.get(f'{BASE}/{"a" * 24}', headers=admin).status_code == 404


@pytest.mark.parametrize('bad_id', ['123', 'not-an-object-id', 'z' * 24, '5' * 23])
def test_get_by_id_invalid_id(client, admin, bad_id):
    r = client.get(f'{BASE}/{bad_id}', headers=admin)
    assert r.status_code == 400
    assert 'update_id' in r.get_json()['details']


def test_filter_by_incident(client, admin, coord):
    create(client, coord, incident_id=1, title='For one')
    create(client, coord, incident_id=2, title='For two')
    create(client, coord, incident_id=2, title='For two again')
    body = client.get(BASE, query_string={'incident_id': 2}, headers=admin).get_json()
    assert body['total'] == 2 and all(u['incident_id'] == 2 for u in body['updates'])


def test_filter_by_status(client, admin, coord):
    create(client, coord, status='ACTIVE', title='Active one')
    create(client, coord, status='RESOLVED', title='Resolved one')
    body = client.get(BASE, query_string={'status': 'resolved'}, headers=admin).get_json()
    assert body['total'] == 1 and body['updates'][0]['status'] == 'RESOLVED'


def test_filter_by_priority_and_type(client, admin, coord):
    create(client, coord, priority='LOW', update_type='WEATHER', title='Weather low')
    create(client, coord, priority='CRITICAL', update_type='EVACUATION', title='Evac crit')
    assert client.get(BASE, query_string={'priority': 'CRITICAL'}, headers=admin).get_json()['total'] == 1
    assert client.get(BASE, query_string={'update_type': 'WEATHER'}, headers=admin).get_json()['total'] == 1
    both = client.get(BASE, query_string={'priority': 'LOW', 'update_type': 'EVACUATION'}, headers=admin)
    assert both.get_json()['total'] == 0


def test_filter_combined_incident_and_status(client, admin, coord):
    create(client, coord, incident_id=1, status='ACTIVE', title='A one')
    create(client, coord, incident_id=2, status='ACTIVE', title='B two')
    create(client, coord, incident_id=2, status='ARCHIVED', title='C three')
    body = client.get(BASE, query_string={'incident_id': 2, 'status': 'ACTIVE'}, headers=admin).get_json()
    assert body['total'] == 1 and body['updates'][0]['title'] == 'B two'


def test_search_is_literal_not_regex(client, admin, coord):
    create(client, coord, title='Road (north) closed')
    create(client, coord, title='Something else')
    assert client.get(BASE, query_string={'search': 'road (north'}, headers=admin).get_json()['total'] == 1
    assert client.get(BASE, query_string={'search': '.*'}, headers=admin).get_json()['total'] == 0


def test_invalid_filter_values(client, admin):
    for qs in ({'status': 'BOGUS'}, {'priority': 'x'}, {'update_type': 'x'}, {'incident_id': 'abc'},
               {'sort_by': 'password'}, {'order': 'sideways'}, {'page': 0}, {'limit': 'ten'}):
        r = client.get(BASE, query_string=qs, headers=admin)
        assert r.status_code == 400, qs


def test_pagination(client, admin, coord):
    for i in range(5):
        create(client, coord, title=f'Update number {i}')
    p1 = client.get(BASE, query_string={'limit': 2, 'page': 1}, headers=admin).get_json()
    p3 = client.get(BASE, query_string={'limit': 2, 'page': 3}, headers=admin).get_json()
    p4 = client.get(BASE, query_string={'limit': 2, 'page': 4}, headers=admin).get_json()
    assert p1['total'] == 5 and p1['pages'] == 3 and len(p1['updates']) == 2
    assert len(p3['updates']) == 1 and p4['updates'] == []
    ids = [u['_id'] for u in p1['updates']]
    p2 = client.get(BASE, query_string={'limit': 2, 'page': 2}, headers=admin).get_json()
    assert not set(ids) & {u['_id'] for u in p2['updates']}


def test_limit_is_capped(client, admin):
    assert client.get(BASE, query_string={'limit': 5000}, headers=admin).get_json()['limit'] == 100


def test_sorting(client, admin, coord):
    create(client, coord, title='Bbb title')
    time.sleep(0.01)
    create(client, coord, title='Aaa title')
    newest = client.get(BASE, headers=admin).get_json()['updates']
    assert newest[0]['title'] == 'Aaa title'                      # default: newest first
    oldest = client.get(BASE, query_string={'order': 'asc'}, headers=admin).get_json()['updates']
    assert oldest[0]['title'] == 'Bbb title'
    by_title = client.get(BASE, query_string={'sort_by': 'title', 'order': 'asc'}, headers=admin).get_json()['updates']
    assert by_title[0]['title'] == 'Aaa title'


def test_citizen_cannot_see_drafts(client, citizen, coord):
    draft = create(client, coord, status='DRAFT', title='Secret draft')
    create(client, coord, status='ACTIVE', title='Public one')
    body = client.get(BASE, headers=citizen).get_json()
    assert body['total'] == 1 and body['updates'][0]['title'] == 'Public one'
    assert client.get(BASE, query_string={'status': 'DRAFT'}, headers=citizen).get_json()['total'] == 0
    assert client.get(f'{BASE}/{draft["_id"]}', headers=citizen).status_code == 404


# ── UPDATE ───────────────────────────────────────────────────────────────────

def test_update_success_changes_fields_and_updated_at(client, coord):
    created = create(client, coord)
    time.sleep(0.01)
    r = client.put(f'{BASE}/{created["_id"]}', json={'title': 'Bridge reopened', 'status': 'RESOLVED'}, headers=coord)
    u = r.get_json()['update']
    assert r.status_code == 200
    assert u['title'] == 'Bridge reopened' and u['status'] == 'RESOLVED'
    assert u['message'] == created['message']                      # untouched
    assert u['created_at'] == created['created_at']                # immutable
    assert u['updated_at'] > created['updated_at']                 # bumped
    assert u['updated_by'] == 2 and u['created_by'] == 2


def test_admin_can_edit_any_update(client, admin, coord):
    created = create(client, coord)
    r = client.put(f'{BASE}/{created["_id"]}', json={'priority': 'LOW'}, headers=admin)
    assert r.status_code == 200 and r.get_json()['update']['priority'] == 'LOW'
    assert r.get_json()['update']['created_by'] == 2               # creator preserved
    assert r.get_json()['update']['updated_by'] == 1


def test_coordinator_cannot_edit_someone_elses_update(client, coord, coord2):
    created = create(client, coord)
    r = client.put(f'{BASE}/{created["_id"]}', json={'title': 'Hijacked title'}, headers=coord2)
    assert r.status_code == 403
    assert client.get(f'{BASE}/{created["_id"]}', headers=coord).get_json()['update']['title'] == 'Bridge closed'


def test_citizen_cannot_update(client, citizen, coord):
    created = create(client, coord)
    assert client.put(f'{BASE}/{created["_id"]}', json={'title': 'Nope nope'}, headers=citizen).status_code == 403


def test_update_invalid_input(client, coord):
    created = create(client, coord)
    uid = created['_id']
    assert client.put(f'{BASE}/{uid}', json={'priority': 'URGENT'}, headers=coord).status_code == 400
    assert client.put(f'{BASE}/{uid}', json={'title': ''}, headers=coord).status_code == 400
    assert client.put(f'{BASE}/{uid}', json={}, headers=coord).status_code == 400
    assert client.put(f'{BASE}/{uid}', json={'incident_id': 'x'}, headers=coord).status_code == 400


def test_update_cannot_change_immutable_fields(client, coord):
    created = create(client, coord)
    for field, value in (('created_by', 99), ('created_at', '2000-01-01'), ('_id', 'x'), ('bogus', 1)):
        r = client.put(f'{BASE}/{created["_id"]}', json={field: value}, headers=coord)
        assert r.status_code == 400, field


def test_update_invalid_id(client, coord):
    assert client.put(f'{BASE}/not-valid', json={'title': 'Valid title'}, headers=coord).status_code == 400


def test_update_not_found(client, coord):
    assert client.put(f'{BASE}/{"b" * 24}', json={'title': 'Valid title'}, headers=coord).status_code == 404


def test_update_incident_id_is_verified(client, coord):
    created = create(client, coord)
    assert client.put(f'{BASE}/{created["_id"]}', json={'incident_id': 999}, headers=coord).status_code == 404
    ok = client.put(f'{BASE}/{created["_id"]}', json={'incident_id': 3}, headers=coord)
    assert ok.status_code == 200 and ok.get_json()['update']['incident_id'] == 3


# ── DELETE ───────────────────────────────────────────────────────────────────

def test_delete_success_only_removes_target(client, admin, coord):
    keep = create(client, coord, title='Keep me please')
    gone = create(client, coord, title='Delete me please')
    r = client.delete(f'{BASE}/{gone["_id"]}', headers=admin)
    assert r.status_code == 200 and r.get_json()['id'] == gone['_id']
    assert client.get(f'{BASE}/{gone["_id"]}', headers=admin).status_code == 404
    assert client.get(f'{BASE}/{keep["_id"]}', headers=admin).status_code == 200
    assert client.get(BASE, headers=admin).get_json()['total'] == 1


def test_delete_forbidden_for_coordinator_and_citizen(client, coord, citizen):
    created = create(client, coord)
    assert client.delete(f'{BASE}/{created["_id"]}', headers=coord).status_code == 403
    assert client.delete(f'{BASE}/{created["_id"]}', headers=citizen).status_code == 403
    assert client.get(f'{BASE}/{created["_id"]}', headers=coord).status_code == 200


def test_delete_invalid_and_missing_id(client, admin):
    assert client.delete(f'{BASE}/abc', headers=admin).status_code == 400
    assert client.delete(f'{BASE}/{"c" * 24}', headers=admin).status_code == 404


def test_delete_twice(client, admin, coord):
    created = create(client, coord)
    assert client.delete(f'{BASE}/{created["_id"]}', headers=admin).status_code == 200
    assert client.delete(f'{BASE}/{created["_id"]}', headers=admin).status_code == 404


# ── AUTH ─────────────────────────────────────────────────────────────────────

def test_unauthenticated_requests_rejected(client):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json=payload()).status_code == 401
    assert client.get(f'{BASE}/{"a" * 24}').status_code == 401
    assert client.put(f'{BASE}/{"a" * 24}', json={'title': 'Valid title'}).status_code == 401
    assert client.delete(f'{BASE}/{"a" * 24}').status_code == 401
    assert client.get(f'{BASE}/analytics').status_code == 401


def test_garbage_token_rejected(client):
    # The app's existing JWT handling answers 401 or 422 for malformed tokens; either way it is rejected.
    assert client.get(BASE, headers={'Authorization': 'Bearer garbage'}).status_code in (401, 422)


def test_citizen_cannot_create(client, citizen):
    assert client.post(BASE, json=payload(), headers=citizen).status_code == 403


# ── ANALYTICS ────────────────────────────────────────────────────────────────

def test_analytics(client, admin, coord, citizen):
    create(client, coord, incident_id=1, status='ACTIVE', priority='HIGH', update_type='WARNING', title='W one')
    create(client, coord, incident_id=1, status='RESOLVED', priority='HIGH', update_type='STATUS', title='S two')
    create(client, coord, incident_id=2, status='ACTIVE', priority='LOW', update_type='STATUS', title='S three')
    r = client.get(f'{BASE}/analytics', headers=admin)
    a = r.get_json()['analytics']
    assert r.status_code == 200 and a['total'] == 3
    assert a['by_status'] == {'ACTIVE': 2, 'RESOLVED': 1}
    assert a['by_priority'] == {'HIGH': 2, 'LOW': 1}
    assert a['by_update_type'] == {'STATUS': 2, 'WARNING': 1}
    assert a['top_incidents'][0]['incident_id'] == 1 and a['top_incidents'][0]['update_count'] == 2
    assert client.get(f'{BASE}/analytics', headers=citizen).status_code == 403


def test_analytics_route_not_shadowed_by_id_route(client, admin):
    assert client.get(f'{BASE}/analytics', headers=admin).status_code == 200


# ── MONGODB FAILURE ──────────────────────────────────────────────────────────

def test_mongo_failure_returns_503_not_500(client, admin, coord, monkeypatch):
    def boom():
        raise ServerSelectionTimeoutError('mongodb://user:secret@host:27017 timed out')
    monkeypatch.setattr(svc, 'collection', boom)
    for r in (client.get(BASE, headers=admin),
              client.post(BASE, json=payload(), headers=coord),
              client.get(f'{BASE}/{"a" * 24}', headers=admin),
              client.put(f'{BASE}/{"a" * 24}', json={'title': 'Valid title'}, headers=coord),
              client.delete(f'{BASE}/{"a" * 24}', headers=admin),
              client.get(f'{BASE}/analytics', headers=admin)):
        assert r.status_code == 503
        assert 'secret' not in r.get_data(as_text=True)            # no credential leakage
        assert 'unavailable' in r.get_json()['error']


def test_real_unreachable_mongodb_returns_503_and_app_stays_up(client, admin, mongo_client):
    """Uses a REAL PyMongo client pointed at a dead port (no server needed)."""
    mongo_cfg._client = MongoClient('mongodb://127.0.0.1:1', serverSelectionTimeoutMS=300)
    try:
        r = client.get(BASE, headers=admin)
        assert r.status_code == 503
        assert client.get('/health').status_code == 200            # rest of app unaffected
        assert client.get('/api/mongo/status', headers=admin).get_json() == {'mongodb': 'down'}
    finally:
        mongo_cfg._client = mongo_client


def test_status_endpoint_up(client, admin):
    assert client.get('/api/mongo/status', headers=admin).get_json() == {'mongodb': 'up'}


# ── SERVICE-LEVEL ────────────────────────────────────────────────────────────

def test_parse_object_id():
    assert str(svc.parse_object_id('a' * 24)) == 'a' * 24
    for bad in (None, 123, '', 'xyz', 'g' * 24):
        with pytest.raises(svc.ValidationError):
            svc.parse_object_id(bad)


def test_ensure_indexes_created(app, mongo_client):
    names = set(mongo_client['crisislink_test']['emergency_updates_test'].index_information())
    assert {'idx_incident_created', 'idx_status_priority', 'idx_update_type', 'idx_created_at'} <= names

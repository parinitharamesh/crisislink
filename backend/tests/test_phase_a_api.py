"""
Phase A API tests - resource/shelter allocation through the real Flask app.

!! Run ONLY against a scratch copy of the database (it changes stock/occupancy) !!

Prerequisites (scratch DB with migrations 06-08 applied, test passwords set):
    MYSQL_DATABASE=crisislink_test  MYSQL_USER=<limited user>  MYSQL_PASSWORD=<pw>
    TEST_COORD_EMAIL / TEST_CITIZEN_EMAIL / TEST_PASSWORD  (accounts that exist in that DB)

Run (PowerShell, from the backend folder):
    python tests/test_phase_a_api.py
Uses Flask's built-in test client, so the server does NOT need to be running.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app                      # noqa: E402
from config.database import get_db              # noqa: E402

COORD   = os.environ.get('TEST_COORD_EMAIL',   'ravi.coordinator@ndrf.in')
CITIZEN = os.environ.get('TEST_CITIZEN_EMAIL', 'arun.kumar@gmail.com')
PASSWD  = os.environ.get('TEST_PASSWORD')
if not PASSWD:
    sys.exit('Set TEST_PASSWORD (password of the two test accounts in the scratch DB).')

app = create_app()
client = app.test_client()
results = []


def check(name, condition, detail=''):
    results.append(bool(condition))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f'  -> {detail}' if detail else ''))


def login(email):
    r = client.post('/api/auth/login', json={'email': email, 'password': PASSWD})
    assert r.status_code == 200, f'login failed for {email}: {r.status_code} {r.get_json()}'
    return {'Authorization': 'Bearer ' + r.get_json()['token']}


def q(sql, args=()):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def post(headers, body):
    return client.post('/api/assignments', json=body, headers=headers)


coord, citizen = login(COORD), login(CITIZEN)

# ---- access control & validation ------------------------------------------------
check('no token -> 401', client.post('/api/assignments', json={}).status_code == 401)
check('citizen cannot allocate -> 403', post(citizen, {'request_id': 9, 'resource_id': 2}).status_code == 403)
check('missing request_id -> 400', post(coord, {'resource_id': 2}).status_code == 400)
check('non-numeric quantity -> 400', post(coord, {'request_id': 9, 'resource_id': 2, 'quantity': 'abc'}).status_code == 400)
check('quantity 0 -> 400', post(coord, {'request_id': 9, 'resource_id': 2, 'quantity': 0}).status_code == 400)
check('nothing to allocate -> 400', post(coord, {'request_id': 9}).status_code == 400)
check('unknown request -> 404', post(coord, {'request_id': 99999, 'resource_id': 2}).status_code == 404)

# ---- partial stock allocation -----------------------------------------------------
q('UPDATE RESOURCE SET quantity = 1 WHERE resource_id = 6')           # request 8 needs 2 tents
r = post(coord, {'request_id': 8, 'resource_id': 6})
body = r.get_json()
check('partial allocation -> 201', r.status_code == 201, body)
check('  quantity_allocated == 1', body.get('quantity_allocated') == 1)
check('  message says partial', 'partial' in (body.get('message') or ''))
st = q('SELECT quantity, status FROM RESOURCE WHERE resource_id = 6')[0]
check('  stock 0 and EXHAUSTED', st['quantity'] == 0 and st['status'] == 'EXHAUSTED', st)
check('  request became ASSIGNED', q('SELECT status FROM EMERGENCY_REQUEST WHERE request_id = 8')[0]['status'] == 'ASSIGNED')
check('  exhausted resource -> 409', post(coord, {'request_id': 8, 'resource_id': 6}).status_code == 409)

q('UPDATE RESOURCE SET quantity = 3 WHERE resource_id = 6')
r = post(coord, {'request_id': 8, 'resource_id': 6, 'quantity': 5})
check('explicit quantity above stock -> 409', r.status_code == 409, r.get_json())
q_before = q('SELECT quantity FROM RESOURCE WHERE resource_id = 6')[0]['quantity']
check('  stock unchanged after rejection', q_before == 3, q_before)

# ---- shelter occupancy -----------------------------------------------------------
r = post(coord, {'request_id': 8, 'shelter_id': 2})                   # shelter 2: 195/200
body = r.get_json()
check('shelter partial housing -> 201', r.status_code == 201 and body.get('people_housed') == 5, body)
sh = q('SELECT current_occupancy, status FROM SHELTER WHERE shelter_id = 2')[0]
check('  occupancy 200 and FULL', sh['current_occupancy'] == 200 and sh['status'] == 'FULL', sh)
shelter_aid = body.get('assignment_id')
check('  full shelter -> 409', post(coord, {'request_id': 8, 'shelter_id': 2}).status_code == 409)
check('  closed shelter -> 409', post(coord, {'request_id': 8, 'shelter_id': 4}).status_code == 409)

# ---- cancellation returns everything ---------------------------------------------
r = client.put(f'/api/assignments/{shelter_aid}/status', json={'status': 'CANCELLED'}, headers=coord)
check('cancel assignment -> 200', r.status_code == 200, r.get_json())
sh = q('SELECT current_occupancy FROM SHELTER WHERE shelter_id = 2')[0]['current_occupancy']
check('  occupancy back to 195', sh == 195, sh)
r = client.put(f'/api/assignments/{shelter_aid}/status', json={'status': 'ACTIVE'}, headers=coord)
check('re-activate cancelled -> 409', r.status_code == 409, r.get_json())

# ---- existing endpoints still work ---------------------------------------------------
for path in ('/api/assignments', '/api/shelters', '/api/resources', '/api/incidents', '/api/requests', '/api/dashboard/stats'):
    check(f'GET {path} -> 200', client.get(path, headers=coord).status_code == 200)
locs = client.get('/api/organizations/locations', headers=coord).get_json()['locations']
check('locations list = 8 selectable places (hierarchy nodes hidden)', len(locs) == 8, len(locs))

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

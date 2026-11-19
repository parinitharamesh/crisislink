"""
CrisisLink – Comprehensive Test Suite
Tests all phases: MySQL, MongoDB, Neo4j, ChromaDB, Flask API, Auth
Run: python test_all.py  (with Docker services running)
"""

import sys
import json
import time
import requests

BASE = "http://localhost:5000"
TOKEN = None
ADMIN_TOKEN = None

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

results = {"passed": 0, "failed": 0, "tests": []}

def test(name, fn):
    try:
        fn()
        print(f"  {PASS} {name}")
        results["passed"] += 1
        results["tests"].append({"name": name, "status": "PASS"})
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results["failed"] += 1
        results["tests"].append({"name": name, "status": "FAIL", "error": str(e)})

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

# ── Health ────────────────────────────────────────────────────────────────────
section("1. API Health")
def check_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

test("Backend health check", check_health)

# ── Auth ──────────────────────────────────────────────────────────────────────
section("2. Authentication")
ts = int(time.time())

def reg_citizen():
    r = requests.post(f"{BASE}/api/auth/register", json={
        "full_name": f"Test Citizen {ts}", "email": f"test.citizen.{ts}@test.com",
        "password": "TestPass123!", "role": "CITIZEN"
    })
    assert r.status_code == 201, f"Got {r.status_code}: {r.text}"
    global TOKEN
    TOKEN = r.json()["token"]
test("Register citizen", reg_citizen)

def reg_dup():
    r = requests.post(f"{BASE}/api/auth/register", json={
        "full_name": "Dup", "email": f"test.citizen.{ts}@test.com",
        "password": "TestPass123!", "role": "CITIZEN"
    })
    assert r.status_code == 409
test("Duplicate email rejected (409)", reg_dup)

def login_admin():
    r = requests.post(f"{BASE}/api/auth/login", json={
        "email": "admin@crisislink.in", "password": "Password123!"
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    global ADMIN_TOKEN
    ADMIN_TOKEN = r.json()["token"]
    assert r.json()["user"]["role"] == "ADMIN"
test("Admin login", login_admin)

def login_wrong_pass():
    r = requests.post(f"{BASE}/api/auth/login", json={
        "email": "admin@crisislink.in", "password": "wrongpassword"
    })
    assert r.status_code == 401
test("Wrong password rejected (401)", login_wrong_pass)

def get_me():
    r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Get current user (/me)", get_me)

def no_token():
    r = requests.get(f"{BASE}/api/requests")
    assert r.status_code == 401
test("Unauthenticated request rejected (401)", no_token)

# ── Emergency Requests ─────────────────────────────────────────────────────────
section("3. Emergency Requests (MySQL)")
REQ_ID = None

def create_req():
    r = requests.post(f"{BASE}/api/requests", json={
        "request_type": "RESCUE", "description": "Test rescue request from automated test suite",
        "people_count": 5, "medical_needed": True, "priority": "HIGH", "location_id": 1
    }, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 201, f"Got {r.status_code}: {r.text}"
    global REQ_ID
    REQ_ID = r.json()["request_id"]
test("Create emergency request", create_req)

def get_requests():
    r = requests.get(f"{BASE}/api/requests", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert "requests" in r.json()
test("Get all requests", get_requests)

def get_single_req():
    r = requests.get(f"{BASE}/api/requests/{REQ_ID}", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.json()["request"]["request_id"] == REQ_ID
test("Get single request by ID", get_single_req)

def update_req_status():
    r = requests.put(f"{BASE}/api/requests/{REQ_ID}/status",
        json={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
test("Update request status (COORDINATOR)", update_req_status)

def req_stats():
    r = requests.get(f"{BASE}/api/requests/stats/summary",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
    assert "stats" in r.json()
test("Request aggregate statistics", req_stats)

# ── Incidents ─────────────────────────────────────────────────────────────────
section("4. Incidents")
def get_incidents():
    r = requests.get(f"{BASE}/api/incidents", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["incidents"]) > 0
test("Get incidents (with seed data)", get_incidents)

def get_incident_summary():
    r = requests.get(f"{BASE}/api/incidents/summary", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Incident summary view (CTE)", get_incident_summary)

# ── Resources ─────────────────────────────────────────────────────────────────
section("5. Resources")
def get_resources():
    r = requests.get(f"{BASE}/api/resources", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["resources"]) > 0
test("Get resources", get_resources)

def get_resource_types():
    r = requests.get(f"{BASE}/api/resources/types", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["resource_types"]) >= 10
test("Get 10+ resource types", get_resource_types)

def get_availability():
    r = requests.get(f"{BASE}/api/resources/availability", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Resource availability view", get_availability)

# ── Shelters ──────────────────────────────────────────────────────────────────
section("6. Shelters")
def get_shelters():
    r = requests.get(f"{BASE}/api/shelters", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["shelters"]) > 0
test("Get shelters with occupancy %", get_shelters)

def shelter_status():
    r = requests.get(f"{BASE}/api/shelters/status", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Shelter status view (vw_shelter_status)", shelter_status)

# ── Dashboard ─────────────────────────────────────────────────────────────────
section("7. Dashboard")
def admin_dashboard():
    r = requests.get(f"{BASE}/api/dashboard/stats", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
    data = r.json()
    for key in ["request_stats","active_incidents","shelter_overview","resource_summary"]:
        assert key in data, f"Missing: {key}"
test("Admin dashboard stats (all views + window functions)", admin_dashboard)

# ── Organizations ─────────────────────────────────────────────────────────────
section("8. Organizations & Locations")
def get_orgs():
    r = requests.get(f"{BASE}/api/organizations", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["organizations"]) >= 6
test("Get 6+ organizations", get_orgs)

def get_locations():
    r = requests.get(f"{BASE}/api/organizations/locations", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["locations"]) >= 8
test("Get 8+ locations", get_locations)

# ── MongoDB ───────────────────────────────────────────────────────────────────
section("9. MongoDB (NoSQL)")
def mongo_init():
    r = requests.post(f"{BASE}/api/mongo/init", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
test("MongoDB init + seed data", mongo_init)

def mongo_get_reports():
    r = requests.get(f"{BASE}/api/mongo/reports", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["reports"]) >= 3
test("MongoDB find reports (FIND + projection + sort)", mongo_get_reports)

def mongo_analytics():
    r = requests.get(f"{BASE}/api/mongo/reports/analytics", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200
test("MongoDB aggregation pipeline", mongo_analytics)

# ── Neo4j ─────────────────────────────────────────────────────────────────────
section("10. Neo4j (Graph DB)")
def neo4j_sync():
    r = requests.post(f"{BASE}/api/graph/sync", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
test("Neo4j sync from MySQL", neo4j_sync)

def neo4j_stats():
    r = requests.get(f"{BASE}/api/graph/stats", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert len(r.json()["nodes"]) > 0
test("Neo4j graph stats (nodes + relationships)", neo4j_stats)

def neo4j_trace():
    r = requests.get(f"{BASE}/api/graph/incident/1/trace", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Neo4j Cypher: trace incident (multi-hop traversal)", neo4j_trace)

def neo4j_orgs():
    r = requests.get(f"{BASE}/api/graph/incident/1/organizations", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Neo4j Cypher: organizations by incident", neo4j_orgs)

def neo4j_locations():
    r = requests.get(f"{BASE}/api/graph/locations/connected", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
test("Neo4j Cypher: connected locations", neo4j_locations)

# ── ChromaDB ──────────────────────────────────────────────────────────────────
section("11. ChromaDB (Vector DB)")
def chroma_init():
    r = requests.post(f"{BASE}/api/search/init", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    assert r.json()["count"] >= 15
test("ChromaDB init + 15 knowledge docs", chroma_init)

def chroma_stats():
    r = requests.get(f"{BASE}/api/search/stats", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.json()["total_documents"] >= 15
test("ChromaDB stats (document count)", chroma_stats)

def chroma_search():
    r = requests.get(f"{BASE}/api/search/search?q=flood+evacuation+rescue&n=5",
        headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert len(data["results"]) > 0
    assert data["results"][0]["similarity"] > 0
test("ChromaDB semantic search (cosine similarity)", chroma_search)

def chroma_category_filter():
    r = requests.get(f"{BASE}/api/search/search?q=medical+supplies&category=medical",
        headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    data = r.json()
    for result in data["results"]:
        assert result["metadata"]["category"] == "medical"
test("ChromaDB metadata filter (category=medical)", chroma_category_filter)

# ── Role-based access ─────────────────────────────────────────────────────────
section("12. Role-Based Access Control")
def citizen_cant_update_status():
    r = requests.put(f"{BASE}/api/requests/1/status",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 403
test("Citizen cannot update request status (403)", citizen_cant_update_status)

def citizen_cant_create_incident():
    r = requests.post(f"{BASE}/api/incidents", json={
        "incident_type": "FLOOD", "title": "Test", "start_date": "2024-01-01", "location_id": 1
    }, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 403
test("Citizen cannot create incident (403)", citizen_cant_create_incident)

# ── Summary ───────────────────────────────────────────────────────────────────
section("TEST SUMMARY")
total = results["passed"] + results["failed"]
print(f"\n  Total:  {total}")
print(f"  Passed: {results['passed']} \033[92m✓\033[0m")
print(f"  Failed: {results['failed']} \033[91m✗\033[0m")
print(f"\n  Pass rate: {results['passed'] / total * 100:.1f}%")

if results["failed"] > 0:
    print("\n  Failed tests:")
    for t in results["tests"]:
        if t["status"] == "FAIL":
            print(f"    - {t['name']}: {t.get('error','')}")

with open("test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\n  Results saved to test_results.json")

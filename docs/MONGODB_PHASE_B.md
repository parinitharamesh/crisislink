# Phase B – MongoDB Emergency Updates

MySQL remains the primary relational database. MongoDB stores **emergency updates** –
short, frequently written, document-shaped messages attached to an incident.

## Collection: `emergency_updates`

Database: `MONGO_DB_NAME` (default `crisislink_nosql`) · Collection: `MONGO_UPDATES_COLLECTION` (default `emergency_updates`)

| Field | BSON type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | auto | Returned to clients as a 24-char hex string |
| `incident_id` | int | yes | ≥ 1. References MySQL `INCIDENT.incident_id` (see below) |
| `title` | string | yes | 3–200 chars, trimmed |
| `message` | string | yes | 1–5000 chars, trimmed |
| `update_type` | string enum | yes (default `GENERAL`) | `GENERAL, STATUS, WARNING, EVACUATION, RESOURCE, WEATHER, ROAD_CLOSURE` |
| `status` | string enum | yes (default `ACTIVE`) | `DRAFT, ACTIVE, RESOLVED, ARCHIVED` |
| `priority` | string enum | yes (default `MEDIUM`) | `LOW, MEDIUM, HIGH, CRITICAL` |
| `created_by` | int | yes | MySQL `USER.user_id` taken from the JWT (never from the request body) |
| `created_by_name` | string | no | Display-name snapshot at creation time, so lists render without a cross-database join. The only intentional denormalisation. |
| `updated_by` | int / null | no | User who last edited the update |
| `created_at` | date (UTC) | yes | Set by the server, immutable |
| `updated_at` | date (UTC) | yes | Set by the server on every create/edit |

Dates are stored at millisecond precision and returned as ISO-8601 strings with a `Z` suffix.

### Relationship with MySQL (not enforced by MongoDB)
`incident_id` points to `INCIDENT.incident_id`. MongoDB has no foreign keys, so:
* **Create / change of `incident_id`:** the API checks MySQL; unknown incident → `404`, MySQL unreachable → `503`.
  Disable with `EMERGENCY_UPDATES_VERIFY_INCIDENT=false` (MySQL-less demos only).
* **Deleting an incident in MySQL does not delete its updates in MongoDB.** Orphans are possible by design;
  they stay readable by incident id and an admin can delete them.
* Only `user_id` / `incident_id` are stored – no other MySQL data is copied.

### Validation & indexes
* Server-side `$jsonSchema` validator on the collection (`validationAction: error`) mirroring the table above,
  created/updated by `init_emergency_updates_collection()`. The Flask API also validates every request before it reaches MongoDB.
* Indexes: `idx_incident_created (incident_id↑, created_at↓)`, `idx_status_priority`, `idx_update_type`, `idx_created_at`, `idx_created_by`.
* Create everything with `python scripts/init_mongo.py` (idempotent, non-destructive) or `POST /api/mongo/init` (ADMIN).

## API (all under `/api/mongo`, JWT required, JSON)

| Method & path | Roles | Success | Errors |
|---|---|---|---|
| `GET /updates` | any logged-in user¹ | 200 `{updates,total,page,limit,pages}` | 400 bad filter, 401, 503 |
| `GET /updates/<id>` | any logged-in user¹ | 200 `{update}` | 400 bad id, 404, 401, 503 |
| `POST /updates` | ADMIN, COORDINATOR | 201 `{message,id,update}` | 400 validation, 403, 404 unknown incident, 503 |
| `PUT /updates/<id>` | ADMIN (any) · COORDINATOR (own only) | 200 `{message,update}` | 400, 403, 404, 503 |
| `DELETE /updates/<id>` | ADMIN | 200 `{message,id}` | 400 bad id, 403, 404, 503 |
| `GET /updates/analytics` | ADMIN, COORDINATOR | 200 `{analytics}` – totals by status/priority/type, top incidents | 403, 503 |
| `GET /status` | any logged-in user | 200 `{mongodb:"up"|"down"}` | 401 |

¹ `CITIZEN` users never see `DRAFT` updates (filtered out of lists, `404` by id).

List query parameters: `incident_id`, `status`, `priority`, `update_type`, `search` (literal, case-insensitive match on title/message),
`page` (default 1), `limit` (default 20, max 100), `sort_by` (`created_at|updated_at|incident_id|title`), `order` (`asc|desc`, default `desc`).

Update payloads accept only `incident_id, title, message, update_type, status, priority`; `_id`, `created_by`, `created_at`
(and any unknown field) are rejected with 400.

Error bodies: `{"error": "...", "details": {"field": "message"}}`. When MongoDB is down these routes return
`503 {"error": "MongoDB is currently unavailable"}`; the MySQL-backed endpoints are unaffected and no connection string is ever returned.

The pre-existing `/api/mongo/reports*` endpoints are unchanged. The old `/api/mongo/updates` pair (which wrote to the
`situation_updates` collection) now serves `emergency_updates`; legacy `situation_updates` documents are left untouched in MongoDB.

## Frontend
| Page | Purpose |
|---|---|
| `/updates` | List, filters (incident / status / priority / type / search), pagination, create form, delete with confirmation |
| `/updates/[id]` | Details, edit form, delete with confirmation |
| `/reports` | Existing page, re-enabled (set `NEXT_PUBLIC_MONGODB_ENABLED=false` for MySQL-only mode); Updates tab now shows emergency updates |
| `/dashboard/admin` | Existing dashboard (used by ADMIN and COORDINATOR) gains an "Emergency Updates" card that degrades gracefully if MongoDB is down |

## Tests
`backend/tests/test_mongo_updates.py` (65 tests). See the README for how to run it, including against a real local MongoDB
via `TEST_MONGO_URI`. Tests only use database `crisislink_test` / collection `emergency_updates_test`.

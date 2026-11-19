# CrisisLink – Disaster Response Coordination System

> 🎓 **University DBMS Project** | MySQL · MongoDB · Neo4j · ChromaDB · Flask · Next.js

A centralized disaster response coordination platform connecting citizens with rescue organizations, resources, and shelters during emergencies.

---

## 🏗️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python Flask REST API |
| Relational DB | MySQL 8.0 |
| NoSQL DB | MongoDB 7.0 |
| Graph DB | Neo4j 5.15 |
| Vector DB | ChromaDB |
| Containerization | Docker Compose |
| Authentication | JWT (bcrypt hashing) |

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://docker.com) installed and running
- Git

### Setup (Windows CMD)

```bat
cd crisislink
copy .env.example .env
docker-compose up -d
```

Wait ~60 seconds for all services to start, then:

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5000
- **Neo4j Browser:** http://localhost:7474

### Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@crisislink.in | Password123! |
| Coordinator | ravi.coordinator@ndrf.in | Password123! |
| Citizen | arun.kumar@gmail.com | Password123! |

---

## 🪟 Phase B – MongoDB Emergency Updates (Windows 11, no Docker)

MySQL stays the primary database. MongoDB powers the **Emergency Updates** module (full CRUD) – see
[`docs/MONGODB_PHASE_B.md`](docs/MONGODB_PHASE_B.md) for the schema, API and authorization rules.
If MongoDB is stopped, only the MongoDB pages/endpoints report "unavailable" – everything MySQL-based keeps working.

### 1. Is MongoDB already installed / running? (PowerShell)

```powershell
Get-Command mongod -ErrorAction SilentlyContinue      # prints a path if installed
Get-Service -Name MongoDB -ErrorAction SilentlyContinue   # Status should be "Running"
Test-NetConnection localhost -Port 27017              # TcpTestSucceeded : True when reachable
```

* Service **Running** and port test **True** → skip to step 3.
* Service exists but **Stopped** → open PowerShell **as Administrator** and run `Start-Service MongoDB`.
* Nothing found → step 2.

### 2. Install MongoDB Community Server (only if needed)

Either use winget (PowerShell as Administrator):

```powershell
winget install MongoDB.Server
winget install MongoDB.Shell          # optional: mongosh command-line client
```

or download the MSI from https://www.mongodb.com/try/download/community → choose **Complete** →
keep **"Install MongoDB as a Service"** ticked (Run as Network Service). Afterwards re-run the checks in step 1
(you may need to open a new PowerShell window so `PATH` refreshes).
A fresh install listens on `localhost:27017` **without authentication**.

### 3. Configure the connection string

Open (or create from `.env.example`) the `.env` file in the project root and add:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=crisislink_nosql
```

If you enabled MongoDB authentication, use `MONGO_URI=mongodb://<username>:<password>@localhost:27017/?authSource=admin`
with your own values – never commit real credentials (`.env` is git-ignored).
`MONGO_USER` / `MONGO_PASSWORD` in `.env.example` are only used by the Docker setup.

### 4. Backend: dependencies, collection, run

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
python scripts/init_mongo.py         # creates the collection, validator and indexes (safe to re-run)
python app.py                        # Flask on http://localhost:5000
```

(`python app_local.py` also works and registers the same MongoDB routes.)
Quick check: open http://localhost:5000/health. When logged in, `GET /api/mongo/status` returns `{"mongodb":"up"}`.
Your MySQL must already be set up with the existing migrations; Phase B adds **no** MySQL changes.

### 5. Frontend

```powershell
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Log in as an ADMIN or COORDINATOR → sidebar **Emergency Updates** (CITIZENs get a read-only view).
To run MySQL-only (hide the MongoDB Reports page), create `frontend/.env.local` with `NEXT_PUBLIC_MONGODB_ENABLED=false`.

### 6. Run the Phase B tests

```powershell
cd backend
pip install -r requirements-test.txt
python -m pytest tests/test_mongo_updates.py -v
```

By default the tests use an in-memory `mongomock` database, so no server is needed and nothing real is touched.
To run the same tests against your real local MongoDB (they only use database `crisislink_test`,
collection `emergency_updates_test`; your `crisislink_nosql` data is not touched):

```powershell
$env:TEST_MONGO_URI = "mongodb://localhost:27017"
python -m pytest tests/test_mongo_updates.py -v
Remove-Item Env:TEST_MONGO_URI
```

The Phase A API test (`tests/test_phase_a_api.py`) is unchanged and still needs a scratch MySQL database as described in its header.

---

## 📁 Project Structure

```
crisislink/
├── backend/                    # Flask REST API
│   ├── app.py                  # Application entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config/
│   │   ├── database.py         # MySQL connection (PyMySQL)
│   │   ├── mongodb.py          # MongoDB connection (PyMongo)
│   │   ├── neo4j_db.py         # Neo4j driver
│   │   └── chromadb_config.py  # ChromaDB + sentence-transformers
│   ├── middleware/
│   │   └── auth_middleware.py  # JWT + role-based access
│   └── routes/
│       ├── auth_routes.py      # Register, Login, JWT
│       ├── request_routes.py   # Emergency requests CRUD
│       ├── incident_routes.py  # Incident management
│       ├── resource_routes.py  # Resource + type management
│       ├── shelter_routes.py   # Shelter + occupancy
│       ├── assignment_routes.py# Resource-to-request assignment
│       ├── inventory_routes.py # Inventory IN/OUT transactions
│       ├── dashboard_routes.py # Stats (views, window functions)
│       ├── org_routes.py       # Organizations + locations
│       ├── mongodb_routes.py   # MongoDB reports + Emergency Updates CRUD (Phase B) + analytics
│       ├── neo4j_routes.py     # Cypher queries + graph sync
│       └── chroma_routes.py    # Semantic vector search
├── frontend/                   # Next.js 14 App Router
│   ├── src/app/                # All 15 pages
│   ├── src/components/         # Reusable UI components
│   └── src/lib/                # API client, auth context
├── database/
│   ├── migrations/
│   │   ├── 01_schema.sql       # 11 tables DDL
│   │   ├── 03_views_triggers.sql
│   │   ├── 04_procedures_functions.sql
│   │   └── 05_indexes_security.sql
│   ├── seeds/
│   │   └── 02_sample_data.sql  # Realistic seed data
│   └── advanced_sql/
│       └── advanced_queries.sql # All Unit 1-3 SQL demos
├── docs/                       # Project documentation
├── docker-compose.yml
├── .env.example
├── setup.bat                   # Windows one-click setup
└── test_all.py                 # Comprehensive test suite
```

---

## 📊 Database Design

### 11 Core Tables

| # | Table | Purpose |
|---|---|---|
| 1 | ORGANIZATION | Rescue/relief organizations |
| 2 | USER | Citizens, coordinators, admins |
| 3 | LOCATION | Geographic locations |
| 4 | RESOURCE_TYPE | Resource category lookup |
| 5 | RESOURCE | Physical resources |
| 6 | SHELTER | Emergency shelters |
| 7 | INCIDENT | Disaster events |
| 8 | EMERGENCY_REQUEST | Citizen emergency requests |
| 9 | REQUEST_RESOURCE_TYPE | M:N junction (composite PK) |
| 10 | ASSIGNMENT | Links requests to resources/shelters |
| 11 | INVENTORY_TRANSACTION | Resource audit trail |

### Key Constraints
- `USER.email` – UNIQUE
- `REQUEST_RESOURCE_TYPE` – Composite Primary Key (request_id, type_id)
- `ASSIGNMENT` – CHECK: at least one of resource_id or shelter_id
- `SHELTER` – CHECK: occupancy between 0 and capacity
- `RESOURCE` – CHECK: quantity >= 0

---

## 📚 DBMS Syllabus Coverage

### Unit 1 – Introduction to DBMS and SQL
- ER diagram and relational schema design
- DDL: CREATE, ALTER, DROP
- DML: INSERT, UPDATE, DELETE, SELECT
- Primary keys, foreign keys, composite keys
- UNIQUE, NOT NULL, CHECK, DEFAULT constraints

### Unit 2 – Advanced SQL
- INNER/LEFT/RIGHT JOINs
- Nested and correlated subqueries
- Aggregate functions (COUNT, SUM, AVG, MAX, MIN)
- GROUP BY, HAVING
- NULL handling (IFNULL, COALESCE)
- Views (6 views)
- Triggers (5 triggers)
- Stored functions (3 functions)
- Stored procedures (4 procedures)
- CTEs and recursive CTEs
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, SUM OVER)
- Full-text search (NATURAL LANGUAGE, BOOLEAN MODE)

### Unit 3 – Design and Optimization
- Functional dependency analysis
- Normalization (1NF → BCNF)
- EXPLAIN query plans
- Index optimization
- Query performance comparison

### Unit 4 – Next-Generation Data Management
- Transactions (START TRANSACTION, COMMIT, ROLLBACK)
- Concurrency control (SELECT ... FOR UPDATE)
- MongoDB (CRUD, aggregation pipeline, indexes)
- Neo4j (Cypher queries, graph traversal)
- ChromaDB (vector embeddings, semantic search)
- Next.js + SQL web application

---

## 🧪 Testing

```bash
python test_all.py
```

Tests cover: MySQL, MongoDB, Neo4j, ChromaDB, Auth, RBAC, all API endpoints.

---

## 📄 License

University project – for educational purposes only.

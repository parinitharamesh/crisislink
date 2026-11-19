# CrisisLink – Complete Project Documentation

## Table of Contents

1. [Project Abstract](#1-project-abstract)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Scope](#4-scope)
5. [Technology Stack and Justification](#5-technology-stack-and-justification)
6. [System Architecture](#6-system-architecture)
7. [ER Diagram](#7-er-diagram)
8. [Relational Schema](#8-relational-schema)
9. [Functional Dependencies](#9-functional-dependencies)
10. [Normalization Analysis](#10-normalization-analysis)
11. [SQL DDL and DML Scripts](#11-sql-ddl-and-dml-scripts)
12. [Advanced SQL Query Explanations](#12-advanced-sql-query-explanations)
13. [Transactions and Concurrency](#13-transactions-and-concurrency)
14. [Query Optimization](#14-query-optimization)
15. [MongoDB Commands and Explanations](#15-mongodb-commands-and-explanations)
16. [Neo4j Graph Model and Cypher Queries](#16-neo4j-graph-model-and-cypher-queries)
17. [ChromaDB and Vector Search](#17-chromadb-and-vector-search)
18. [API Documentation](#18-api-documentation)
19. [Frontend Structure](#19-frontend-structure)
20. [Setup Instructions](#20-setup-instructions)
21. [Testing Instructions](#21-testing-instructions)
22. [Screenshots Checklist](#22-screenshots-checklist)
23. [Syllabus Mapping](#23-syllabus-mapping)

---

## 1. Project Abstract

CrisisLink is a centralized disaster response coordination system that connects citizens in distress with rescue organizations, emergency resources, and shelters. The system uses a multi-database architecture: MySQL 8.0 as the primary relational database for structured records, MongoDB for flexible document-oriented incident reports, Neo4j for graph-based relationship exploration, and ChromaDB for semantic vector search over disaster knowledge.

The application features role-based access (Citizen, Coordinator, Admin), emergency request submission and tracking, resource allocation with inventory management, shelter occupancy control, and real-time dashboard analytics. Built with a Flask REST API backend and Next.js frontend, the project demonstrates comprehensive DBMS concepts including SQL operations, normalization, transactions, concurrency control, query optimization, and next-generation database technologies.

---

## 2. Problem Statement

During a disaster, emergency requests, shelter occupancy, medical needs, rescue teams, and relief supplies are tracked separately across different communication channels and spreadsheets. This fragmentation makes it difficult to:

- Identify suitable resources quickly
- Avoid duplicate or conflicting assignments
- Monitor limited inventory in real-time
- Coordinate multiple organizations effectively
- Track response progress across incidents

CrisisLink provides a centralized, database-backed system for recording emergencies, managing resources, coordinating assignments, and tracking response progress — with proper data integrity, concurrency control, and multi-database integration.

---

## 3. Objectives

1. Allow citizens to submit emergency requests and track their status
2. Maintain structured records of incidents, locations, organizations, resources, and shelters
3. Enable coordinators to assign resources and shelters to emergency requests
4. Manage shelter occupancy with transaction-safe capacity enforcement
5. Track resource inventory with a full audit trail
6. Store detailed incident reports as flexible MongoDB documents
7. Model entity relationships in Neo4j for graph-based exploration
8. Provide semantic search over disaster knowledge using ChromaDB vector embeddings
9. Demonstrate comprehensive DBMS concepts from all four syllabus units

---

## 4. Scope

### In Scope
- User registration and JWT-based authentication with role-based access
- Emergency request submission and lifecycle management
- Incident creation and management
- Resource and resource type management
- Shelter management with occupancy tracking
- Resource-to-request assignment with stored procedures
- Inventory transaction logging
- MongoDB document storage for incident reports
- Neo4j graph synchronization and Cypher queries
- ChromaDB vector search over disaster knowledge
- Dashboard with real-time statistics

### Out of Scope
- Payment processing
- Real-time chat or messaging
- Push notifications
- GPS/map integration
- Mobile native applications

---

## 5. Technology Stack and Justification

| Component | Technology | Justification |
|---|---|---|
| **Relational DB** | MySQL 8.0 | Industry standard; supports all required SQL features (views, triggers, stored procedures, CTEs, window functions, full-text search, transactions, locking) |
| **Backend API** | Python Flask | Lightweight, explicit, easy for students to understand; excellent MySQL and MongoDB connectors |
| **Frontend** | Next.js 14 + TypeScript | Modern React framework with App Router; required by Unit 4 syllabus |
| **NoSQL DB** | MongoDB 7.0 | Document-oriented storage for flexible incident reports with nested structures |
| **Graph DB** | Neo4j 5.15 | Explicitly required by Unit 4 syllabus; models disaster response entity relationships |
| **Vector DB** | ChromaDB | Lightweight vector database for semantic search; CPU-compatible sentence-transformer embeddings |
| **Auth** | JWT + bcrypt | Stateless authentication; secure password hashing with 12-round bcrypt |
| **CSS** | Tailwind CSS | Utility-first styling; responsive design without complex CSS frameworks |
| **Container** | Docker Compose | Runs all four databases plus backend in isolated, reproducible containers |

---

## 6. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                       │
│         (Landing, Login, Register, 12+ Dashboard Pages)      │
│              http://localhost:3000                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/REST (Axios)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask REST API Backend                      │
│    Routes: auth, requests, incidents, resources, shelters,   │
│    assignments, inventory, mongo, neo4j, chroma, dashboard   │
│              http://localhost:5000                            │
└────┬──────────┬──────────┬──────────┬───────────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌───────┐ ┌─────────┐
│ MySQL   │ │MongoDB │ │ Neo4j │ │ChromaDB │
│ 8.0     │ │  7.0   │ │ 5.15  │ │         │
│ Port    │ │ Port   │ │ Port  │ │ Port    │
│ 3307    │ │ 27017  │ │ 7687  │ │ 8001    │
│         │ │        │ │       │ │         │
│ Source  │ │ Reports│ │ Graph │ │ Vector  │
│ of      │ │ Updates│ │ Model │ │ Search  │
│ Truth   │ │ Docs   │ │       │ │         │
└─────────┘ └────────┘ └───────┘ └─────────┘
```

**Data Flow:**
1. MySQL is the **source of truth** for all structured application data
2. MongoDB stores **unstructured/semi-structured** incident reports and situation updates
3. Neo4j mirrors MySQL relationships as a **graph** for traversal queries
4. ChromaDB stores **vector embeddings** of disaster knowledge for semantic search

---

## 7. ER Diagram

```
ORGANIZATION ──────1:M──── USER
     │                      │
     ├──────1:M──── RESOURCE    LOCATION
     │                │           │
     ├──────1:M──── SHELTER      ├──1:M── INCIDENT
     │                │           ├──1:M── RESOURCE
                      │           ├──1:M── SHELTER
                      │           └──1:M── EMERGENCY_REQUEST
                      │
              RESOURCE_TYPE ──1:M── RESOURCE
                                      │
    INCIDENT ──1:M── EMERGENCY_REQUEST │
                        │              │
                        ├──M:N── RESOURCE_TYPE
                        │    (REQUEST_RESOURCE_TYPE)
                        │
                        └──1:M── ASSIGNMENT ──M:1── RESOURCE
                                    │         ──M:1── SHELTER
                                    │
                              INVENTORY_TRANSACTION
```

### Relationship Cardinalities

| Relationship | Cardinality |
|---|---|
| ORGANIZATION → USER | 1:M (nullable FK – citizens may not belong to an org) |
| ORGANIZATION → RESOURCE | 1:M |
| ORGANIZATION → SHELTER | 1:M |
| LOCATION → INCIDENT | 1:M |
| LOCATION → RESOURCE | 1:M |
| LOCATION → SHELTER | 1:M |
| LOCATION → EMERGENCY_REQUEST | 1:M |
| RESOURCE_TYPE → RESOURCE | 1:M |
| INCIDENT → EMERGENCY_REQUEST | 1:M (nullable FK) |
| USER → EMERGENCY_REQUEST | 1:M |
| EMERGENCY_REQUEST ↔ RESOURCE_TYPE | M:N (via REQUEST_RESOURCE_TYPE) |
| EMERGENCY_REQUEST → ASSIGNMENT | 1:M |
| RESOURCE → ASSIGNMENT | 1:M (nullable FK) |
| SHELTER → ASSIGNMENT | 1:M (nullable FK) |
| RESOURCE → INVENTORY_TRANSACTION | 1:M |
| ASSIGNMENT → INVENTORY_TRANSACTION | 1:M (nullable FK) |

---

## 8. Relational Schema

### Primary Key and Foreign Key Mapping

| Table | Primary Key | Foreign Keys |
|---|---|---|
| ORGANIZATION | org_id (AUTO_INCREMENT) | — |
| LOCATION | location_id (AUTO_INCREMENT) | — |
| RESOURCE_TYPE | type_id (AUTO_INCREMENT) | — |
| USER | user_id (AUTO_INCREMENT) | org_id → ORGANIZATION(org_id) [NULLABLE] |
| INCIDENT | incident_id (AUTO_INCREMENT) | location_id → LOCATION, reported_by → USER [NULLABLE] |
| RESOURCE | resource_id (AUTO_INCREMENT) | type_id → RESOURCE_TYPE, location_id → LOCATION, org_id → ORGANIZATION |
| SHELTER | shelter_id (AUTO_INCREMENT) | location_id → LOCATION, org_id → ORGANIZATION |
| EMERGENCY_REQUEST | request_id (AUTO_INCREMENT) | user_id → USER, incident_id → INCIDENT [NULLABLE], location_id → LOCATION |
| REQUEST_RESOURCE_TYPE | **(request_id, type_id)** Composite | request_id → EMERGENCY_REQUEST, type_id → RESOURCE_TYPE |
| ASSIGNMENT | assignment_id (AUTO_INCREMENT) | request_id → EMERGENCY_REQUEST, resource_id → RESOURCE [NULLABLE], shelter_id → SHELTER [NULLABLE], assigned_by → USER [NULLABLE] |
| INVENTORY_TRANSACTION | transaction_id (AUTO_INCREMENT) | resource_id → RESOURCE, assignment_id → ASSIGNMENT [NULLABLE], performed_by → USER [NULLABLE] |

### Constraints Summary

| Constraint Type | Examples |
|---|---|
| PRIMARY KEY | All 11 tables; REQUEST_RESOURCE_TYPE uses composite PK |
| FOREIGN KEY | 18 foreign key relationships with ON DELETE/UPDATE actions |
| UNIQUE | USER.email, ORGANIZATION.org_name, RESOURCE_TYPE.type_name |
| NOT NULL | All mandatory fields |
| CHECK | latitude [-90,90], longitude [-180,180], quantity ≥ 0, occupancy ≤ capacity, people_count ≥ 1, assignment must have resource OR shelter |
| DEFAULT | CURRENT_TIMESTAMP for dates, 'PENDING' for statuses, 0 for occupancy |
| ENUM | role, incident_type, request_type, status fields |

---

## 9. Functional Dependencies

### ORGANIZATION
- **org_id → {org_name, org_type, contact_no, address, created_at}**
- org_name → org_id (since org_name is UNIQUE)

### USER
- **user_id → {full_name, email, password_hash, phone, role, org_id, is_active, created_at}**
- email → user_id (since email is UNIQUE)

### LOCATION
- **location_id → {area_name, district, state, latitude, longitude, created_at}**

### RESOURCE_TYPE
- **type_id → {type_name, description}**
- type_name → type_id (since type_name is UNIQUE)

### RESOURCE
- **resource_id → {resource_name, type_id, quantity, unit, status, location_id, org_id, description, created_at, updated_at}**

### SHELTER
- **shelter_id → {shelter_name, address, capacity, current_occupancy, has_medical_facility, status, location_id, org_id, created_at, updated_at}**

### INCIDENT
- **incident_id → {incident_type, title, start_date, end_date, description, affected_area, severity, status, location_id, reported_by, created_at}**

### EMERGENCY_REQUEST
- **request_id → {request_type, description, people_count, medical_needed, priority, status, request_time, resolved_time, user_id, incident_id, location_id}**

### REQUEST_RESOURCE_TYPE
- **(request_id, type_id) → {quantity_required}**

### ASSIGNMENT
- **assignment_id → {assigned_time, status, remarks, request_id, resource_id, shelter_id, assigned_by}**

### INVENTORY_TRANSACTION
- **transaction_id → {quantity, transaction_type, notes, transaction_time, resource_id, assignment_id, performed_by}**

---

## 10. Normalization Analysis

### First Normal Form (1NF)
All tables satisfy 1NF:
- Every column contains atomic (indivisible) values
- No repeating groups
- Every table has a primary key
- Example: Resource types needed by a request are stored in the separate REQUEST_RESOURCE_TYPE junction table, not as a comma-separated list

### Second Normal Form (2NF)
All tables satisfy 2NF:
- All non-key attributes are fully functionally dependent on the entire primary key
- The only composite key table is REQUEST_RESOURCE_TYPE where (request_id, type_id) → quantity_required; quantity_required depends on the full composite key, not just one part
- All other tables have single-column primary keys, so 2NF is automatically satisfied

### Third Normal Form (3NF)
All tables satisfy 3NF:
- No transitive dependencies exist
- Example: In RESOURCE, org_name is NOT stored (it would create org_id → org_name transitive dependency). Instead, org_id is a foreign key, and org_name lives only in ORGANIZATION

### Boyce-Codd Normal Form (BCNF)
All tables satisfy BCNF:
- For every non-trivial functional dependency X → Y, X is a superkey
- The primary key of each table is the only determinant of non-key attributes
- No anomalies possible under the current design

### Higher Normal Forms
- **4NF**: No multi-valued dependencies exist. The M:N relationship between requests and resource types is properly decomposed via REQUEST_RESOURCE_TYPE
- **5NF**: No join dependencies that aren't implied by candidate keys

---

## 11. SQL DDL and DML Scripts

See files:
- `database/migrations/01_schema.sql` – All 11 table CREATE statements
- `database/seeds/02_sample_data.sql` – INSERT statements for realistic data
- `database/advanced_sql/advanced_queries.sql` – Complete SQL demonstrations

### DDL Examples
```sql
-- CREATE with constraints
CREATE TABLE EMERGENCY_REQUEST (
    request_id    INT UNSIGNED AUTO_INCREMENT,
    request_type  ENUM('RESCUE','MEDICAL','SHELTER','FOOD','WATER','EVACUATION','OTHER') NOT NULL,
    people_count  INT UNSIGNED NOT NULL DEFAULT 1,
    CONSTRAINT pk_emergency_request PRIMARY KEY (request_id),
    CONSTRAINT chk_people_count CHECK (people_count >= 1)
);

-- ALTER (adding full-text index)
ALTER TABLE EMERGENCY_REQUEST ADD FULLTEXT INDEX ft_request_description (description);

-- DROP (demonstration only)
-- DROP TABLE IF EXISTS temp_demo_table;
```

### DML Examples
```sql
-- INSERT
INSERT INTO ORGANIZATION (org_name, org_type, contact_no, address)
VALUES ('Red Cross India', 'NGO', '+91-11-23716441', 'New Delhi');

-- UPDATE
UPDATE EMERGENCY_REQUEST SET status = 'RESOLVED' WHERE request_id = 1;

-- DELETE
DELETE FROM INVENTORY_TRANSACTION WHERE transaction_id = 999;

-- SELECT with multiple joins
SELECT er.request_id, u.full_name, l.area_name, er.priority
FROM EMERGENCY_REQUEST er
INNER JOIN USER u ON er.user_id = u.user_id
INNER JOIN LOCATION l ON er.location_id = l.location_id;
```

---

## 12. Advanced SQL Query Explanations

### Joins
- **INNER JOIN**: Request details with user and location (used throughout the app)
- **LEFT JOIN**: All requests including those with no assignments
- **RIGHT JOIN**: All organizations including those with no resources

### Subqueries
- **Nested**: Find resources whose type is needed by CRITICAL requests
- **Correlated**: Citizens with more than 1 emergency request
- **EXISTS**: Incidents with at least one CRITICAL request

### Views (6 views)
1. `vw_active_requests` – Active requests with joins to user, location, incident
2. `vw_resource_availability` – Resource availability per organization (GROUP BY)
3. `vw_shelter_status` – Shelter occupancy with calculated percentages
4. `vw_incident_summary` – Incident overview with request and assignment counts
5. `vw_unassigned_requests` – Pending requests needing coordinator action
6. `vw_inventory_audit` – Full inventory audit trail with all joins

### Triggers (5 triggers)
1. `trg_resource_qty_check` – Prevent negative quantity; auto-update status
2. `trg_shelter_occupancy_update` – Enforce capacity constraints
3. `trg_inventory_out_deduct` – Auto-update resource quantity on IN/OUT
4. `trg_request_resolved_time` – Auto-set resolved_time when status = RESOLVED
5. `trg_critical_request_audit` – Audit logging for CRITICAL requests

### Stored Functions (3)
1. `fn_shelter_occupancy_pct(shelter_id)` – Returns occupancy percentage
2. `fn_resource_active_assignments(resource_id)` – Active assignment count
3. `fn_incident_pending_requests(incident_id)` – Pending request count

### Stored Procedures (4)
1. `sp_allocate_resource` – Safe atomic resource allocation with locking
2. `sp_dashboard_stats` – Multi-result-set dashboard statistics
3. `sp_update_shelter_occupancy` – Transaction-safe occupancy update
4. `sp_find_resources_for_request` – Matching resources for a request

### CTEs and Recursive CTEs
- CTE: `vw_request_chain` – Incident request breakdown with percentage
- Recursive CTE: Location hierarchy traversal (state → district → area)

### Window Functions
- `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()` – Priority ranking within incidents
- `SUM() OVER()` – Running total of affected people
- `AVG() OVER()` – Average people per request within incident
- `LAG()`, `LEAD()` – Previous/next quantity comparison
- `PERCENT_RANK()` – Percentile positioning

### Full-Text Search
- NATURAL LANGUAGE MODE: Relevance-scored search across request descriptions
- BOOLEAN MODE: Required/excluded term search (+flood -medical)

---

## 13. Transactions and Concurrency

### Transaction Demonstrations

```sql
-- Safe resource allocation (in sp_allocate_resource)
START TRANSACTION;
SELECT status, quantity FROM RESOURCE WHERE resource_id = ? FOR UPDATE;  -- Lock row
-- Validate availability
INSERT INTO ASSIGNMENT (...) VALUES (...);
UPDATE EMERGENCY_REQUEST SET status = 'ASSIGNED' WHERE request_id = ?;
UPDATE RESOURCE SET status = 'DEPLOYED' WHERE resource_id = ?;
COMMIT;
```

### Concurrency Control
- **SELECT ... FOR UPDATE**: Row-level pessimistic locking for resources and shelters
- **Double Allocation Prevention**: sp_allocate_resource locks the resource row before checking availability
- **Shelter Overbooking Prevention**: sp_update_shelter_occupancy locks the shelter row and validates capacity

### Rollback Scenarios
```sql
START TRANSACTION;
UPDATE SHELTER SET current_occupancy = current_occupancy + 500 WHERE shelter_id = 1;
-- Would violate capacity CHECK constraint
ROLLBACK;  -- Changes discarded
```

---

## 14. Query Optimization

### Indexes Created

| Table | Index | Type |
|---|---|---|
| EMERGENCY_REQUEST | idx_req_status_priority | Composite B-tree |
| EMERGENCY_REQUEST | ft_request_description | Full-text |
| ASSIGNMENT | idx_assign_request | B-tree |
| RESOURCE | idx_resource_status | B-tree |
| USER | idx_user_email_role | Composite B-tree |
| (16+ more indexes) | ... | B-tree |

### EXPLAIN Analysis

```sql
-- Before index: Full table scan
EXPLAIN SELECT * FROM EMERGENCY_REQUEST WHERE status = 'PENDING';
-- type: ALL, rows: ~all rows

-- After index (idx_req_status): Index range scan
EXPLAIN SELECT * FROM EMERGENCY_REQUEST WHERE status = 'PENDING';
-- type: ref, key: idx_req_status, rows: ~subset
```

---

## 15. MongoDB Commands and Explanations

### Collection: `incident_reports`
Stores detailed incident reports with nested document structure.

```javascript
// INSERT
db.incident_reports.insertOne({
  incident_id: 1,
  title: "Kerala Flood 2024 – Assessment",
  content: "Severe flooding in northern Kerala...",
  severity: "CRITICAL",
  casualties: { deaths: 12, injured: 45, missing: 8 },  // Nested object
  tags: ["flood", "kerala", "rescue"],                    // Array field
  report_date: new Date()
});

// FIND with projection and sorting
db.incident_reports.find(
  { severity: "CRITICAL" },
  { title: 1, incident_id: 1, report_date: 1 }
).sort({ report_date: -1 });

// UPDATE
db.incident_reports.updateOne(
  { _id: ObjectId("...") },
  { $set: { content: "Updated content", last_updated: new Date() } }
);

// DELETE
db.incident_reports.deleteOne({ _id: ObjectId("...") });

// TEXT SEARCH
db.incident_reports.find({ $text: { $search: "flood rescue" } });

// AGGREGATION PIPELINE
db.incident_reports.aggregate([
  { $match: { content: { $exists: true } } },
  { $group: {
      _id: "$severity",
      report_count: { $sum: 1 },
      total_deaths: { $sum: "$casualties.deaths" }
  }},
  { $sort: { total_deaths: -1 } }
]);
```

### Indexes
- `incident_id` (ascending)
- `report_date` (descending)
- `tags` (ascending)
- `(title, content)` (text index)

---

## 16. Neo4j Graph Model and Cypher Queries

### Node Labels
Organization, User, Location, Incident, EmergencyRequest, Resource, ResourceType, Shelter, Assignment

### Relationships
- `ORGANIZATION_OWNS_RESOURCE`, `ORGANIZATION_MANAGES_SHELTER`
- `LOCATION_HAS_INCIDENT`, `RESOURCE_LOCATED_AT`, `SHELTER_LOCATED_AT`
- `INCIDENT_GENERATES_REQUEST`, `REQUEST_HAS_ASSIGNMENT`
- `ASSIGNMENT_USES_RESOURCE`, `ASSIGNMENT_USES_SHELTER`
- `RESOURCE_BELONGS_TO_TYPE`

### Cypher Queries

```cypher
// Query 1: Trace incident → requests → assignments → resources
MATCH (i:Incident {incident_id: 1})
OPTIONAL MATCH (i)-[:INCIDENT_GENERATES_REQUEST]->(er)
OPTIONAL MATCH (er)-[:REQUEST_HAS_ASSIGNMENT]->(a)
OPTIONAL MATCH (a)-[:ASSIGNMENT_USES_RESOURCE]->(r)
RETURN i.title, er.type, a.status, r.name;

// Query 2: Find available resources
MATCH (r:Resource)-[:RESOURCE_BELONGS_TO_TYPE]->(rt:ResourceType)
WHERE r.status = 'AVAILABLE'
MATCH (o:Organization)-[:ORGANIZATION_OWNS_RESOURCE]->(r)
RETURN r.name, rt.name, o.name, r.quantity;

// Query 3: Organizations involved in incident response
MATCH (i:Incident {incident_id: 1})
  -[:INCIDENT_GENERATES_REQUEST]->(er)
  -[:REQUEST_HAS_ASSIGNMENT]->(a)
  -[:ASSIGNMENT_USES_RESOURCE]->(r)
  <-[:ORGANIZATION_OWNS_RESOURCE]-(o)
RETURN DISTINCT o.name, COUNT(r) AS resources;

// Query 4: Connected locations
MATCH (l:Location)-[:LOCATION_HAS_INCIDENT]->(i:Incident)
RETURN l.area_name, COLLECT(i.type) AS incident_types;
```

### Synchronization
MySQL → Neo4j sync is triggered via the `/api/graph/sync` endpoint. This reads all MySQL data and creates/updates corresponding Neo4j nodes and relationships, ensuring consistency.

---

## 17. ChromaDB and Vector Search

### Concept
ChromaDB stores text documents as high-dimensional vector embeddings. When a user submits a natural language query, it is also embedded, and the cosine similarity between query and document vectors determines relevance.

### Embedding Model
- **all-MiniLM-L6-v2** – 384-dimensional sentence transformer
- Runs on CPU (no GPU required)
- ~80MB download on first use

### Operations
```python
# Collection creation
collection = client.get_or_create_collection(
    name="crisis_knowledge",
    embedding_function=SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2"),
    metadata={"hnsw:space": "cosine"}
)

# Adding documents (auto-generates embeddings)
collection.upsert(ids=["kb-001"], documents=["Flood evacuation procedure..."], metadatas=[{"category": "flood"}])

# Semantic search
results = collection.query(query_texts=["people trapped in flood"], n_results=5)

# Metadata filtering
results = collection.query(query_texts=["medical supplies"], where={"category": "medical"})

# Delete
collection.delete(ids=["kb-001"])
```

### Knowledge Base
15 disaster response documents covering: flood evacuation, rescue procedures, medical triage, cyclone preparedness, shelter management, food distribution, water supply, earthquake response, landslide rescue, coordination, survival, chemical leak response, volunteer management, emergency communication.

---

## 18. API Documentation

### Base URL: `http://localhost:5000`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | — | Register new user |
| POST | /api/auth/login | — | Login, receive JWT |
| GET | /api/auth/me | JWT | Get current user |
| GET | /api/requests | JWT | List requests (role-filtered) |
| POST | /api/requests | JWT | Submit emergency request |
| GET | /api/requests/:id | JWT | Get request details |
| PUT | /api/requests/:id/status | COORD/ADMIN | Update request status |
| GET | /api/incidents | JWT | List incidents |
| POST | /api/incidents | COORD/ADMIN | Create incident |
| PUT | /api/incidents/:id | COORD/ADMIN | Update incident |
| GET | /api/resources | JWT | List resources |
| POST | /api/resources | COORD/ADMIN | Add resource |
| GET | /api/resources/types | JWT | List resource types |
| GET | /api/shelters | JWT | List shelters |
| POST | /api/shelters | COORD/ADMIN | Create shelter |
| PUT | /api/shelters/:id/occupancy | COORD/ADMIN | Update occupancy (SP) |
| GET | /api/assignments | JWT | List assignments |
| POST | /api/assignments | COORD/ADMIN | Create assignment (SP) |
| GET | /api/inventory | JWT | List transactions |
| POST | /api/inventory | COORD/ADMIN | Record transaction |
| GET | /api/dashboard/stats | JWT | Dashboard statistics |
| GET/POST | /api/mongo/reports | JWT/ADMIN | MongoDB CRUD |
| GET | /api/mongo/reports/analytics | ADMIN | Aggregation pipeline |
| POST | /api/graph/sync | ADMIN | Sync MySQL → Neo4j |
| GET | /api/graph/incident/:id/trace | JWT | Cypher trace query |
| GET | /api/search/search?q=... | JWT | Semantic vector search |
| POST | /api/search/init | ADMIN | Init ChromaDB knowledge base |

---

## 19. Frontend Structure

15 pages built with Next.js 14 App Router:

| # | Page | Path | Role |
|---|---|---|---|
| 1 | Landing | / | Public |
| 2 | Login | /login | Public |
| 3 | Registration | /register | Public |
| 4 | Citizen Dashboard | /dashboard/citizen | CITIZEN |
| 5 | Submit Request | /requests/submit | CITIZEN |
| 6 | My Requests | /requests | ALL |
| 7 | Admin Dashboard | /dashboard/admin | COORD/ADMIN |
| 8 | Incidents | /incidents | COORD/ADMIN |
| 9 | Resources | /resources | COORD/ADMIN |
| 10 | Shelters | /shelters | COORD/ADMIN |
| 11 | Assignments | /assignments | COORD/ADMIN |
| 12 | Inventory | /inventory | COORD/ADMIN |
| 13 | MongoDB Reports | /reports | COORD/ADMIN |
| 14 | Neo4j Graph | /graph | COORD/ADMIN |
| 15 | Vector Search | /search | ALL |

---

## 20. Setup Instructions

### Prerequisites
1. Docker Desktop installed and running
2. At least 4GB RAM available for Docker
3. Git installed

### Steps

```bash
# 1. Clone or navigate to project
cd crisislink

# 2. Create .env file
copy .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Wait 60 seconds for MySQL to initialize

# 5. Open in browser
# Frontend: http://localhost:3000
# Backend:  http://localhost:5000/health

# 6. Login with demo credentials (see README)

# 7. Initialize MongoDB and ChromaDB (Admin dashboard)
# Click "Seed Data" on MongoDB Reports page
# Click "Init Knowledge Base" on Vector Search page

# 8. Sync Neo4j
# Click "Sync MySQL → Neo4j" on Graph page
```

### Manual Backend (without Docker)
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Manual Frontend (without Docker)
```bash
cd frontend
npm install
npm run dev
```

---

## 21. Testing Instructions

### Automated Test Suite
```bash
# Ensure all Docker services are running first
docker-compose up -d

# Wait for services to be healthy
# Then run the test suite
python test_all.py
```

The test suite covers:
- API health check
- User registration and duplicate prevention
- Login with correct and incorrect credentials
- JWT authentication and authorization
- Emergency request CRUD
- Incident management
- Resource and type listing
- Shelter management
- Dashboard statistics (views, window functions)
- MongoDB CRUD and aggregation
- Neo4j sync and Cypher queries
- ChromaDB initialization and semantic search
- Role-based access control enforcement

---

## 22. Screenshots Checklist

When preparing your report, capture screenshots of:

1. [ ] Landing page
2. [ ] Registration form
3. [ ] Login page
4. [ ] Citizen dashboard
5. [ ] Emergency request submission form
6. [ ] Submitted requests list
7. [ ] Admin/Coordinator dashboard with stats
8. [ ] Incident management page
9. [ ] Resource management page
10. [ ] Shelter management with occupancy bars
11. [ ] Assignment creation form
12. [ ] Inventory transaction log
13. [ ] MongoDB reports page with seed data
14. [ ] MongoDB aggregation results
15. [ ] Neo4j graph statistics
16. [ ] Neo4j incident trace results
17. [ ] ChromaDB semantic search with results
18. [ ] ChromaDB category filter
19. [ ] MySQL Workbench: EXPLAIN query plan
20. [ ] Docker Compose services running
21. [ ] Test suite results (all passing)

---

## 23. Syllabus Mapping

| # | Syllabus Topic | Implementation Location |
|---|---|---|
| | **UNIT 1** | |
| 1 | Database introduction and architecture | System architecture (Section 6) |
| 2 | ER model | ER diagram (Section 7) |
| 3 | ER → Relational schema conversion | Schema design (01_schema.sql) |
| 4 | Relational algebra (σ, π, ×, ⋈) | advanced_queries.sql §1.1–1.4 |
| 5 | Aggregate functions and grouping | §1.5–1.6 + views + dashboard |
| 6 | SQL overview and structure | All SQL files |
| 7 | DDL (CREATE, ALTER, DROP) | 01_schema.sql + 05_indexes.sql |
| 8 | DML (INSERT, UPDATE, DELETE, SELECT) | 02_sample_data.sql + all routes |
| 9 | Constraints and keys | 01_schema.sql (PK, FK, UNIQUE, CHECK, NOT NULL, DEFAULT) |
| | **UNIT 2** | |
| 10 | Set operations (UNION) | advanced_queries.sql §1.7 |
| 11 | NULL handling | §2.3 (IFNULL, COALESCE, IS NULL) |
| 12 | Nested subqueries | §2.4 |
| 13 | Correlated subqueries | §2.5 |
| 14 | JOIN expressions | §2.1 (LEFT), §2.2 (RIGHT) + all routes |
| 15 | Views | 03_views_triggers.sql (6 views) |
| 16 | Triggers | 03_views_triggers.sql (5 triggers) |
| 17 | Stored functions | 04_procedures_functions.sql (3 functions) |
| 18 | Stored procedures | 04_procedures_functions.sql (4 procedures) |
| 19 | CTEs | 04_procedures_functions.sql + §2.9 |
| 20 | Recursive CTEs | §2.10 |
| 21 | Window functions | §2.11 + vw_request_priority_rank |
| 22 | Full-text search | §2.8 (NATURAL LANGUAGE + BOOLEAN) |
| | **UNIT 3** | |
| 23 | Functional dependencies | Documentation Section 9 |
| 24 | Normalization (1NF–BCNF) | Documentation Section 10 |
| 25 | Query optimization | 05_indexes.sql + EXPLAIN demos |
| 26 | Inference rules | Documentation Section 9 |
| | **UNIT 4** | |
| 27 | Transactions | sp_allocate_resource (START/COMMIT/ROLLBACK) |
| 28 | Concurrency control / Locking | SELECT ... FOR UPDATE in procedures |
| 29 | NoSQL / MongoDB | mongodb_routes.py + reports page |
| 30 | Graph databases (Neo4j) | neo4j_routes.py + graph page |
| 31 | Vector databases (ChromaDB) | chroma_routes.py + search page |
| 32 | Vector search | Semantic similarity search |
| 33 | Next.js + SQL integration | Complete frontend (15 pages) |

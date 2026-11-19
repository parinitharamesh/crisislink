-- =============================================================================
-- CrisisLink – Advanced SQL Demonstrations
-- FILE: advanced_queries.sql
-- PURPOSE: Demonstrate all Unit 1, 2, 3 SQL topics with meaningful examples
-- =============================================================================

USE crisislink_db;

-- ===========================================================================
-- UNIT 1: RELATIONAL ALGEBRA and BASIC SQL
-- ===========================================================================

-- 1.1 SELECTION σ – filter rows
SELECT * FROM EMERGENCY_REQUEST WHERE priority = 'CRITICAL' AND status = 'PENDING';

-- 1.2 PROJECTION π – select specific columns
SELECT request_id, request_type, priority, people_count FROM EMERGENCY_REQUEST;

-- 1.3 CARTESIAN PRODUCT (illustrative; rarely used in practice)
SELECT u.full_name, r.resource_name
FROM `USER` u, RESOURCE r
WHERE u.role = 'COORDINATOR' LIMIT 20;

-- 1.4 INNER JOIN – requests with their submitters and location
SELECT er.request_id, u.full_name AS citizen, l.area_name AS location,
       er.request_type, er.priority, er.status
FROM EMERGENCY_REQUEST er
INNER JOIN `USER`   u ON er.user_id     = u.user_id
INNER JOIN LOCATION l ON er.location_id = l.location_id;

-- 1.5 AGGREGATE FUNCTIONS
SELECT
    COUNT(*)                             AS total_requests,
    SUM(people_count)                    AS total_affected,
    AVG(people_count)                    AS avg_affected,
    MAX(people_count)                    AS max_in_one_request,
    MIN(people_count)                    AS min_in_one_request
FROM EMERGENCY_REQUEST;

-- 1.6 GROUP BY and HAVING – requests per incident, only those with 3+ requests
SELECT incident_id, COUNT(*) AS req_count, SUM(people_count) AS total_affected
FROM EMERGENCY_REQUEST
WHERE incident_id IS NOT NULL
GROUP BY incident_id
HAVING COUNT(*) >= 2
ORDER BY total_affected DESC;

-- 1.7 SET OPERATIONS – UNION
-- All locations that either have a resource or a shelter:
SELECT l.location_id, l.area_name, 'Has Resource' AS role
FROM LOCATION l
WHERE l.location_id IN (SELECT DISTINCT location_id FROM RESOURCE)
UNION
SELECT l.location_id, l.area_name, 'Has Shelter'
FROM LOCATION l
WHERE l.location_id IN (SELECT DISTINCT location_id FROM SHELTER)
ORDER BY location_id;

-- ===========================================================================
-- UNIT 2: ADVANCED SQL
-- ===========================================================================

-- 2.1 LEFT JOIN – all requests including those with no assignment
SELECT er.request_id, er.request_type, er.status, a.assignment_id,
       a.status AS assign_status
FROM EMERGENCY_REQUEST er
LEFT JOIN ASSIGNMENT a ON er.request_id = a.request_id
ORDER BY er.request_id;

-- 2.2 RIGHT JOIN – all organizations, including those with no resources
SELECT o.org_name, r.resource_name, r.status
FROM RESOURCE r
RIGHT JOIN ORGANIZATION o ON r.org_id = o.org_id
ORDER BY o.org_name;

-- 2.3 NULL HANDLING – requests not linked to any incident
SELECT request_id, request_type, IFNULL(incident_id, 'Standalone') AS incident_ref,
       COALESCE(incident_id, 0) AS incident_num
FROM EMERGENCY_REQUEST
WHERE incident_id IS NULL;

-- 2.4 NESTED SUBQUERY – find resources whose type is needed by CRITICAL requests
SELECT resource_id, resource_name, status, quantity
FROM RESOURCE
WHERE type_id IN (
    SELECT DISTINCT rrt.type_id
    FROM REQUEST_RESOURCE_TYPE rrt
    INNER JOIN EMERGENCY_REQUEST er ON rrt.request_id = er.request_id
    WHERE er.priority = 'CRITICAL'
)
AND status = 'AVAILABLE';

-- 2.5 CORRELATED SUBQUERY – citizens with more than 1 emergency request
SELECT u.user_id, u.full_name, u.email,
       (SELECT COUNT(*) FROM EMERGENCY_REQUEST er WHERE er.user_id = u.user_id) AS request_count
FROM `USER` u
WHERE (SELECT COUNT(*) FROM EMERGENCY_REQUEST er WHERE er.user_id = u.user_id) > 1;

-- 2.6 EXISTS subquery – incidents that have at least one CRITICAL request
SELECT incident_id, title, incident_type, severity
FROM INCIDENT i
WHERE EXISTS (
    SELECT 1 FROM EMERGENCY_REQUEST er
    WHERE er.incident_id = i.incident_id AND er.priority = 'CRITICAL'
);

-- 2.7 AGGREGATE with HAVING (NOT EXISTS pattern)
-- Organizations with NO active resource assignments
SELECT o.org_id, o.org_name
FROM ORGANIZATION o
WHERE o.org_id NOT IN (
    SELECT DISTINCT r.org_id
    FROM RESOURCE r
    INNER JOIN ASSIGNMENT a ON a.resource_id = r.resource_id
    WHERE a.status = 'ACTIVE'
);

-- 2.8 FULL-TEXT SEARCH (Unit 2 – Full-text search functions)
-- Search emergency requests containing "flood" or "water"
SELECT request_id, request_type, description, priority,
       MATCH(description) AGAINST ('flood water rescue' IN NATURAL LANGUAGE MODE) AS relevance_score
FROM EMERGENCY_REQUEST
WHERE MATCH(description) AGAINST ('flood water rescue' IN NATURAL LANGUAGE MODE)
ORDER BY relevance_score DESC;

-- BOOLEAN MODE full-text search
SELECT request_id, description
FROM EMERGENCY_REQUEST
WHERE MATCH(description) AGAINST ('+flood -medical' IN BOOLEAN MODE);

-- 2.9 CTE – Common Table Expressions (Unit 2)
WITH incident_request_stats AS (
    SELECT
        er.incident_id,
        COUNT(*)                      AS request_count,
        SUM(er.people_count)          AS total_affected,
        SUM(er.medical_needed)        AS medical_requests,
        COUNT(CASE WHEN er.status = 'PENDING' THEN 1 END) AS pending_count
    FROM EMERGENCY_REQUEST er
    WHERE er.incident_id IS NOT NULL
    GROUP BY er.incident_id
),
ranked_incidents AS (
    SELECT
        irs.*,
        i.title,
        i.severity,
        RANK() OVER (ORDER BY irs.total_affected DESC) AS severity_rank
    FROM incident_request_stats irs
    INNER JOIN INCIDENT i ON i.incident_id = irs.incident_id
)
SELECT * FROM ranked_incidents ORDER BY severity_rank;

-- 2.10 RECURSIVE CTE – organizational hierarchy (demonstration)
-- Note: our schema is flat, so we simulate a region hierarchy
WITH RECURSIVE location_chain AS (
    -- Base: all states
    SELECT location_id, area_name, state, district, 1 AS depth
    FROM LOCATION
    WHERE district = state  -- top level
    UNION ALL
    -- Recursive: districts within states
    SELECT l.location_id, l.area_name, l.state, l.district, lc.depth + 1
    FROM LOCATION l
    INNER JOIN location_chain lc ON l.state = lc.state AND l.district != lc.district
    WHERE lc.depth < 3
)
SELECT DISTINCT location_id, area_name, state, district, depth
FROM location_chain
ORDER BY state, depth, area_name;

-- 2.11 WINDOW FUNCTIONS (Unit 2)
-- Rank resources by quantity within each resource type
SELECT
    resource_id,
    resource_name,
    quantity,
    status,
    type_id,
    ROW_NUMBER()  OVER (PARTITION BY type_id ORDER BY quantity DESC) AS row_num,
    RANK()        OVER (PARTITION BY type_id ORDER BY quantity DESC) AS rnk,
    DENSE_RANK()  OVER (PARTITION BY type_id ORDER BY quantity DESC) AS dense_rnk,
    PERCENT_RANK()OVER (PARTITION BY type_id ORDER BY quantity DESC) AS pct_rank,
    -- Cumulative sum per type
    SUM(quantity) OVER (PARTITION BY type_id ORDER BY quantity DESC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_qty,
    -- Total quantity for that type (window aggregate)
    SUM(quantity) OVER (PARTITION BY type_id)      AS type_total_qty,
    -- Lead/lag for spotting quantity trends
    LAG(quantity, 1)  OVER (PARTITION BY type_id ORDER BY resource_id) AS prev_qty,
    LEAD(quantity, 1) OVER (PARTITION BY type_id ORDER BY resource_id) AS next_qty
FROM RESOURCE
ORDER BY type_id, rnk;

-- 2.12 VIEWS usage
SELECT * FROM vw_active_requests WHERE priority = 'CRITICAL';
SELECT * FROM vw_shelter_status WHERE available_spots > 0;
SELECT * FROM vw_incident_summary WHERE incident_status = 'ACTIVE';

-- ===========================================================================
-- UNIT 3 – TRANSACTIONS and LOCKING (Unit 4)
-- ===========================================================================

-- Demo: Full transaction for resource allocation
START TRANSACTION;

-- Lock the resource row to prevent concurrent allocation
SELECT resource_id, status, quantity
FROM RESOURCE WHERE resource_id = 1 FOR UPDATE;

-- Update quantity
UPDATE RESOURCE SET quantity = quantity - 10 WHERE resource_id = 1;

-- Record the inventory transaction
INSERT INTO INVENTORY_TRANSACTION (quantity, transaction_type, notes, resource_id, assignment_id, performed_by)
VALUES (10, 'OUT', 'Dispatched for emergency flood relief', 1, 1, 1);

-- Commit if everything is fine
COMMIT;

-- Demo: ROLLBACK scenario
START TRANSACTION;
UPDATE SHELTER SET current_occupancy = current_occupancy + 100 WHERE shelter_id = 1;
-- This would violate the CHECK constraint; we explicitly rollback:
ROLLBACK;

-- ===========================================================================
-- UNIT 3 – QUERY OPTIMIZATION with EXPLAIN
-- ===========================================================================

-- Before index: full table scan on EMERGENCY_REQUEST
EXPLAIN SELECT * FROM EMERGENCY_REQUEST WHERE status = 'PENDING';

-- After index exists (idx_req_status): index range scan
EXPLAIN SELECT * FROM EMERGENCY_REQUEST WHERE status = 'PENDING' AND priority = 'CRITICAL';

-- EXPLAIN JOIN performance
EXPLAIN
SELECT er.request_id, u.full_name, l.area_name, er.priority
FROM EMERGENCY_REQUEST er
INNER JOIN `USER`   u ON er.user_id     = u.user_id
INNER JOIN LOCATION l ON er.location_id = l.location_id
WHERE er.status = 'PENDING';

-- EXPLAIN FORMAT=JSON for detailed optimizer output
EXPLAIN FORMAT=JSON
SELECT * FROM EMERGENCY_REQUEST WHERE incident_id = 1 AND status != 'CLOSED';

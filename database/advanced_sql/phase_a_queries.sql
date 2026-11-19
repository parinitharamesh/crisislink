-- =============================================================================
-- CrisisLink - Advanced queries (all READ-ONLY, safe on real data)
-- Needs migrations 06-08 applied.   Run:  mysql -u <user> -p crisislink_db < phase_a_queries.sql
-- =============================================================================

-- Q1  INNER JOIN : every incident with its assigned coordinator
SELECT 'Q1 INNER JOIN' AS q;
SELECT i.incident_id, i.title, i.severity, i.status, u.full_name AS coordinator
FROM INCIDENT i
INNER JOIN `USER` u ON u.user_id = i.coordinator_id
ORDER BY i.incident_id;

-- Q2  LEFT JOIN : all coordinators, including those with NO incident
SELECT 'Q2 LEFT JOIN' AS q;
SELECT u.user_id, u.full_name, COUNT(i.incident_id) AS incidents_managed
FROM `USER` u
LEFT JOIN INCIDENT i ON i.coordinator_id = u.user_id
WHERE u.role = 'COORDINATOR'
GROUP BY u.user_id, u.full_name
ORDER BY incidents_managed DESC, u.user_id;

-- Q3  MULTI-TABLE JOIN (6 tables) : who needs what, where, and what was sent
SELECT 'Q3 MULTI-TABLE JOIN' AS q;
SELECT er.request_id, req.full_name AS citizen, er.request_type, er.priority,
       l.area_name, inc.title AS incident,
       r.resource_name, a.quantity_allocated, coord.full_name AS assigned_by
FROM EMERGENCY_REQUEST er
JOIN `USER` req            ON req.user_id   = er.user_id
JOIN LOCATION l            ON l.location_id = er.location_id
LEFT JOIN INCIDENT inc     ON inc.incident_id = er.incident_id
LEFT JOIN ASSIGNMENT a     ON a.request_id  = er.request_id
LEFT JOIN RESOURCE r       ON r.resource_id = a.resource_id
LEFT JOIN `USER` coord     ON coord.user_id = a.assigned_by
WHERE a.resource_id IS NOT NULL
ORDER BY er.request_id, a.assignment_id
LIMIT 8;

-- Q4  NESTED subquery (NOT IN) : resources never allocated to any request
SELECT 'Q4 NESTED - unallocated resources' AS q;
SELECT resource_id, resource_name, quantity, status
FROM RESOURCE
WHERE resource_id NOT IN (SELECT resource_id FROM ASSIGNMENT WHERE resource_id IS NOT NULL);

-- Q5  NESTED subquery (IN + GROUP BY/HAVING) : citizens with more than one request
SELECT 'Q5 NESTED - repeat requesters' AS q;
SELECT user_id, full_name, email
FROM `USER`
WHERE user_id IN (SELECT user_id FROM EMERGENCY_REQUEST GROUP BY user_id HAVING COUNT(*) > 1);

-- Q6  NESTED subquery + function : shelters that can still take people, above-average free space
SELECT 'Q6 NESTED + FUNCTION - shelters with free capacity' AS q;
SELECT shelter_id, shelter_name, capacity, current_occupancy,
       fn_shelter_available_capacity(shelter_id) AS free_beds
FROM SHELTER
WHERE fn_shelter_available_capacity(shelter_id) >
      (SELECT AVG(fn_shelter_available_capacity(shelter_id)) FROM SHELTER WHERE status <> 'CLOSED')
ORDER BY free_beds DESC;

-- Q7  CORRELATED subquery : incidents whose total resource requirement exceeds the average incident
SELECT 'Q7 CORRELATED - requirement above average' AS q;
SELECT i.incident_id, i.title,
       (SELECT SUM(rr.quantity_required)
          FROM EMERGENCY_REQUEST er
          JOIN REQUEST_RESOURCE_TYPE rr ON rr.request_id = er.request_id
         WHERE er.incident_id = i.incident_id) AS units_required
FROM INCIDENT i
WHERE (SELECT SUM(rr.quantity_required)
         FROM EMERGENCY_REQUEST er
         JOIN REQUEST_RESOURCE_TYPE rr ON rr.request_id = er.request_id
        WHERE er.incident_id = i.incident_id)
      >
      (SELECT AVG(t.total) FROM (
            SELECT SUM(rr.quantity_required) AS total
              FROM EMERGENCY_REQUEST er
              JOIN REQUEST_RESOURCE_TYPE rr ON rr.request_id = er.request_id
             WHERE er.incident_id IS NOT NULL
             GROUP BY er.incident_id) t);

-- Q8  CORRELATED subquery : locations whose request count is above the overall average per location
SELECT 'Q8 CORRELATED - hot-spot locations' AS q;
SELECT l.location_id, l.area_name,
       (SELECT COUNT(*) FROM EMERGENCY_REQUEST er WHERE er.location_id = l.location_id) AS requests
FROM LOCATION l
WHERE (SELECT COUNT(*) FROM EMERGENCY_REQUEST er WHERE er.location_id = l.location_id)
      > (SELECT COUNT(*) / COUNT(DISTINCT location_id) FROM EMERGENCY_REQUEST);

-- Q9  CTE : incidents with total allocated resources (uses fn_incident_total_allocated)
SELECT 'Q9 CTE - incidents and allocated resources' AS q;
WITH incident_requests AS (
    SELECT incident_id, COUNT(*) AS request_count
    FROM EMERGENCY_REQUEST
    WHERE incident_id IS NOT NULL
    GROUP BY incident_id
)
SELECT i.incident_id, i.title, i.status, ir.request_count,
       fn_incident_total_allocated(i.incident_id) AS units_allocated
FROM INCIDENT i
LEFT JOIN incident_requests ir ON ir.incident_id = i.incident_id
ORDER BY units_allocated DESC, i.incident_id;

-- Q10 CTE : emergency requests summarised by status, with percentage share
SELECT 'Q10 CTE - requests by status' AS q;
WITH by_status AS (
    SELECT status, COUNT(*) AS n FROM EMERGENCY_REQUEST GROUP BY status
), total AS (
    SELECT SUM(n) AS all_requests FROM by_status
)
SELECT b.status, b.n AS requests, ROUND(100 * b.n / t.all_requests, 1) AS pct
FROM by_status b CROSS JOIN total t
ORDER BY b.n DESC;

-- Q11 CTE + window function : locations ranked by number of requests
SELECT 'Q11 CTE - busiest locations' AS q;
WITH per_location AS (
    SELECT l.location_id, l.area_name, l.state, COUNT(er.request_id) AS requests
    FROM LOCATION l
    JOIN EMERGENCY_REQUEST er ON er.location_id = l.location_id
    GROUP BY l.location_id, l.area_name, l.state
)
SELECT area_name, state, requests, RANK() OVER (ORDER BY requests DESC) AS busiest_rank
FROM per_location
ORDER BY busiest_rank, area_name
LIMIT 5;

-- Q12 RECURSIVE CTE : the location hierarchy as an indented tree (top-down)
SELECT 'Q12 RECURSIVE - location tree (top-down)' AS q;
WITH RECURSIVE tree AS (
    SELECT location_id, parent_location_id, area_name, 0 AS depth,
           CAST(LPAD(location_id, 4, '0') AS CHAR(200)) AS sort_key
    FROM LOCATION WHERE parent_location_id IS NULL
    UNION ALL
    SELECT c.location_id, c.parent_location_id, c.area_name, t.depth + 1,
           CONCAT(t.sort_key, '/', LPAD(c.location_id, 4, '0'))
    FROM LOCATION c JOIN tree t ON c.parent_location_id = t.location_id
)
SELECT CONCAT(REPEAT('    ', depth), area_name) AS location_tree, depth
FROM tree
WHERE depth <= 2 AND (depth < 2 OR location_id IN (17, 18))   -- keep the printout short: India, states, Kerala's districts
ORDER BY sort_key;

-- Q13 RECURSIVE CTE (bottom-up) : every request counted at EVERY level above its location.
--     India must equal the grand total of requests.
SELECT 'Q13 RECURSIVE - requests rolled up the hierarchy' AS q;
WITH RECURSIVE ancestors AS (
    SELECT location_id AS origin, location_id AS node, parent_location_id AS parent
    FROM LOCATION
    UNION ALL
    SELECT a.origin, l.location_id, l.parent_location_id
    FROM ancestors a
    JOIN LOCATION l ON l.location_id = a.parent
), per_location AS (
    SELECT location_id, COUNT(*) AS n FROM EMERGENCY_REQUEST GROUP BY location_id
)
SELECT l.area_name, vt.depth AS level, SUM(p.n) AS requests_in_region
FROM ancestors a
JOIN per_location p    ON p.location_id = a.origin
JOIN LOCATION l        ON l.location_id = a.node
JOIN vw_location_tree vt ON vt.location_id = l.location_id
WHERE vt.depth <= 1
GROUP BY l.location_id, l.area_name, vt.depth
ORDER BY vt.depth, requests_in_region DESC, l.area_name;
SELECT 'check: grand total of requests' AS q, COUNT(*) AS total_requests FROM EMERGENCY_REQUEST;

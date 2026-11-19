-- =============================================================================
-- CrisisLink - Phase A test script (migrations 06-08)
-- !! RUN ONLY ON A SCRATCH COPY OF THE DATABASE, NEVER ON YOUR REAL DATA !!
--    (it changes stock, occupancy and statuses to test the logic)
-- Usage:  mysql --force -u <admin> -p crisislink_test < phase_a_tests.sql
--         (--force keeps going after the errors that are EXPECTED below)
-- Each test prints  [expected]  next to the actual value.
-- =============================================================================

-- ---------- 1. FUNCTIONS ----------------------------------------------------
SELECT 'F1 shelter 1 free beds'            AS test, fn_shelter_available_capacity(1)   AS actual, 180  AS expected;
SELECT 'F1 shelter 2 free beds'            AS test, fn_shelter_available_capacity(2)   AS actual, 5    AS expected;
SELECT 'F1 closed shelter 4 -> 0'          AS test, fn_shelter_available_capacity(4)   AS actual, 0    AS expected;
SELECT 'F1 unknown shelter -> NULL'        AS test, fn_shelter_available_capacity(999) AS actual, NULL AS expected;
SELECT 'F2 incident 1 allocated units'     AS test, fn_incident_total_allocated(1)     AS actual, 74   AS expected;
SELECT 'F2 incident 3 allocated units'     AS test, fn_incident_total_allocated(3)     AS actual, 2    AS expected;

-- ---------- 2. RESOURCE ALLOCATION -----------------------------------------
-- request 9 (WATER, needs type 2 x2), resource 2 = Water Tanker, stock 10
SELECT 'before: stock of resource 2' AS info, quantity, status FROM RESOURCE WHERE resource_id = 2;

CALL sp_allocate_assignment(9, 2, NULL, NULL, NULL, 2, 'test: default quantity', @aid, @st, @msg);
SELECT 'A1 default qty = requirement (2)' AS test, @st AS status, @msg AS message;
SELECT 'A1 stock 10 -> 8 (deducted ONCE)' AS test, quantity AS actual, 8 AS expected FROM RESOURCE WHERE resource_id = 2;
SELECT 'A1 request became ASSIGNED'       AS test, status AS actual, 'ASSIGNED' AS expected FROM EMERGENCY_REQUEST WHERE request_id = 9;
SELECT 'A1 assignment stores quantity'    AS test, quantity_allocated AS actual, 2 AS expected FROM ASSIGNMENT WHERE assignment_id = @aid;
SELECT 'A1 citizen notified'              AS test, COUNT(*) AS actual, 1 AS expected FROM NOTIFICATION WHERE request_id = 9 AND notif_type = 'ASSIGNMENT';
SET @water_aid = @aid;

CALL sp_allocate_assignment(9, 2, 1, NULL, NULL, 2, 'test: exceeds requirement', @aid, @st, @msg);
SELECT 'A2 over-allocation rejected' AS test, @st AS status, @msg AS message;
SELECT 'A2 stock unchanged (8)'      AS test, quantity AS actual, 8 AS expected FROM RESOURCE WHERE resource_id = 2;

-- partial allocation: request 8 needs 2 tents (type 6); leave only 1 tent in stock
UPDATE RESOURCE SET quantity = 1 WHERE resource_id = 6;
CALL sp_allocate_assignment(8, 6, NULL, NULL, NULL, 2, 'test: partial', @aid, @st, @msg);
SELECT 'A3 partial allocation (1 of 2)'        AS test, @st AS status, @msg AS message;
SELECT 'A3 stock 0 and EXHAUSTED by trigger'   AS test, CONCAT(quantity, '/', status) AS actual, '0/EXHAUSTED' AS expected FROM RESOURCE WHERE resource_id = 6;
SET @tent_aid = @aid;

CALL sp_allocate_assignment(8, 6, NULL, NULL, NULL, 2, 'test: exhausted', @aid, @st, @msg);
SELECT 'A4 exhausted resource rejected' AS test, @st AS status, @msg AS message;

UPDATE RESOURCE SET quantity = 3 WHERE resource_id = 6;       -- restock (trigger -> AVAILABLE)
CALL sp_allocate_assignment(8, 6, 5, NULL, NULL, 2, 'test: more than stock', @aid, @st, @msg);
SELECT 'A5 explicit qty > stock rejected' AS test, @st AS status, @msg AS message;

CALL sp_allocate_assignment(8, 6, NULL, NULL, NULL, 2, 'test: top-up the rest', @aid, @st, @msg);
SELECT 'A6 top-up allocates remaining 1' AS test, @st AS status, @msg AS message;
SELECT 'A6 stock 3 -> 2'                 AS test, quantity AS actual, 2 AS expected FROM RESOURCE WHERE resource_id = 6;

CALL sp_allocate_assignment(8, 6, NULL, NULL, NULL, 2, 'test: already fulfilled', @aid, @st, @msg);
SELECT 'A7 fully allocated -> rejected' AS test, @st AS status, @msg AS message;

CALL sp_allocate_assignment(NULL, NULL, NULL, NULL, NULL, 2, 'x', @aid, @st, @msg);
SELECT 'A8 nothing to allocate -> rejected' AS test, @st AS status, @msg AS message;
CALL sp_allocate_assignment(9999, 2, 1, NULL, NULL, 2, 'x', @aid, @st, @msg);
SELECT 'A9 unknown request -> rejected' AS test, @st AS status, @msg AS message;

-- ---------- 3. SHELTER OCCUPANCY -------------------------------------------
-- request 8 has 20 people; shelter 2 has only 5 free beds (195/200)
CALL sp_allocate_assignment(8, NULL, NULL, 2, NULL, 2, 'test: partial housing', @aid, @st, @msg);
SELECT 'S1 partial housing (5 of 20)'      AS test, @st AS status, @msg AS message;
SELECT 'S1 occupancy 200 and FULL'         AS test, CONCAT(current_occupancy, '/', status) AS actual, '200/FULL' AS expected FROM SHELTER WHERE shelter_id = 2;

CALL sp_allocate_assignment(8, NULL, NULL, 2, NULL, 2, 'test: full shelter', @aid, @st, @msg);
SELECT 'S2 full shelter rejected' AS test, @st AS status, @msg AS message;

CALL sp_allocate_assignment(8, NULL, NULL, 3, NULL, 2, 'test: house the remaining 15', @aid, @st, @msg);
SELECT 'S3 remaining 15 housed in shelter 3' AS test, @st AS status, @msg AS message;
SELECT 'S3 shelter 3 occupancy 15'           AS test, current_occupancy AS actual, 15 AS expected FROM SHELTER WHERE shelter_id = 3;
SET @shelter3_aid = @aid;

CALL sp_allocate_assignment(8, NULL, NULL, 3, NULL, 2, 'test: nobody left', @aid, @st, @msg);
SELECT 'S4 everyone already housed -> rejected' AS test, @st AS status, @msg AS message;

CALL sp_allocate_assignment(9, NULL, NULL, 3, 400, 2, 'test: too many people', @aid, @st, @msg);
SELECT 'S5 explicit people > free rejected' AS test, @st AS status, @msg AS message;

CALL sp_allocate_assignment(9, NULL, NULL, 4, NULL, 2, 'test: closed', @aid, @st, @msg);
SELECT 'S6 CLOSED shelter rejected' AS test, @st AS status, @msg AS message;

-- ---------- 4. CANCEL = give everything back (trigger) ---------------------
UPDATE ASSIGNMENT SET status = 'CANCELLED' WHERE assignment_id = @shelter3_aid;
SELECT 'C1 shelter 3 occupancy back to 0' AS test, current_occupancy AS actual, 0 AS expected FROM SHELTER WHERE shelter_id = 3;

UPDATE ASSIGNMENT SET status = 'CANCELLED' WHERE assignment_id = @water_aid;
SELECT 'C2 stock back 8 -> 10'            AS test, quantity AS actual, 10 AS expected FROM RESOURCE WHERE resource_id = 2;

UPDATE ASSIGNMENT SET status = 'CANCELLED' WHERE assignment_id = @water_aid;       -- no transition -> no second refund
SELECT 'C3 second cancel gives NO extra stock' AS test, quantity AS actual, 10 AS expected FROM RESOURCE WHERE resource_id = 2;

UPDATE ASSIGNMENT SET status = 'ACTIVE' WHERE assignment_id = @water_aid;          -- EXPECTED ERROR
SELECT 'C4 re-activation blocked (error above expected)' AS test, status AS actual, 'CANCELLED' AS expected FROM ASSIGNMENT WHERE assignment_id = @water_aid;

-- ---------- 5. AUDIT + NOTIFICATION TRIGGERS ------------------------------
SET @app_user_id = 2;
UPDATE INCIDENT SET status = 'MONITORING' WHERE incident_id = 1;
UPDATE INCIDENT SET status = 'MONITORING' WHERE incident_id = 1;                   -- same value -> must NOT audit
SELECT 'T1 exactly one audit row'  AS test, COUNT(*) AS actual, 1 AS expected FROM INCIDENT_STATUS_AUDIT WHERE incident_id = 1;
SELECT 'T1 audit row content'      AS info, old_status, new_status, changed_by_user_id, db_account FROM INCIDENT_STATUS_AUDIT WHERE incident_id = 1;
UPDATE INCIDENT SET status = 'ACTIVE' WHERE incident_id = 1;                       -- restore

-- ---------- 6. LOCATION HIERARCHY GUARD -----------------------------------
UPDATE LOCATION SET parent_location_id = 9 WHERE location_id = 9;                  -- EXPECTED ERROR (self parent)
UPDATE LOCATION SET parent_location_id = 1 WHERE location_id = 9;                  -- EXPECTED ERROR (cycle)
SELECT 'L1 India still top level' AS test, parent_location_id AS actual, NULL AS expected FROM LOCATION WHERE location_id = 9;

-- ---------- 7. FILTER PROCEDURE -------------------------------------------
CALL sp_get_requests_by_filter('RESOLVED', 'CRITICAL', 10);
CALL sp_get_requests_by_filter(NULL, 'CRITICAL', 3);
CALL sp_get_requests_by_filter('NOT_A_STATUS', NULL, 10);                          -- EXPECTED ERROR

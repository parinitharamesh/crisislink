-- =============================================================================
-- CrisisLink – Disaster Response Coordination System
-- FILE: 04_procedures_functions.sql  (Phase 3 – Advanced SQL Part 2)
-- PURPOSE: Stored Procedures, Functions, CTEs, Window Functions
-- =============================================================================

USE crisislink_db;

DELIMITER $$

-- =============================================================================
-- STORED FUNCTIONS (Unit 2 – Functions)
-- =============================================================================

-- FUNCTION 1: Calculate shelter occupancy percentage
DROP FUNCTION IF EXISTS fn_shelter_occupancy_pct$$
CREATE FUNCTION fn_shelter_occupancy_pct(p_shelter_id INT UNSIGNED)
RETURNS DECIMAL(5,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_capacity INT;
    DECLARE v_occupancy INT;

    SELECT capacity, current_occupancy
    INTO v_capacity, v_occupancy
    FROM SHELTER WHERE shelter_id = p_shelter_id;

    IF v_capacity IS NULL OR v_capacity = 0 THEN
        RETURN 0.00;
    END IF;

    RETURN ROUND((v_occupancy * 100.0) / v_capacity, 2);
END$$

-- FUNCTION 2: Get active assignment count for a resource
DROP FUNCTION IF EXISTS fn_resource_active_assignments$$
CREATE FUNCTION fn_resource_active_assignments(p_resource_id INT UNSIGNED)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*) INTO v_count
    FROM ASSIGNMENT
    WHERE resource_id = p_resource_id
      AND status IN ('PENDING','ACTIVE');

    RETURN v_count;
END$$

-- FUNCTION 3: Get pending request count for an incident
DROP FUNCTION IF EXISTS fn_incident_pending_requests$$
CREATE FUNCTION fn_incident_pending_requests(p_incident_id INT UNSIGNED)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*) INTO v_count
    FROM EMERGENCY_REQUEST
    WHERE incident_id = p_incident_id
      AND status IN ('PENDING','ASSIGNED','IN_PROGRESS');

    RETURN v_count;
END$$

-- =============================================================================
-- STORED PROCEDURES (Unit 2 – Stored Procedures)
-- =============================================================================

-- PROCEDURE 1: Safe resource allocation with transaction and locking
--              Demonstrates: START TRANSACTION, SELECT FOR UPDATE, COMMIT, ROLLBACK
DROP PROCEDURE IF EXISTS sp_allocate_resource$$
CREATE PROCEDURE sp_allocate_resource(
    IN  p_request_id    INT UNSIGNED,
    IN  p_resource_id   INT UNSIGNED,
    IN  p_shelter_id    INT UNSIGNED,
    IN  p_assigned_by   INT UNSIGNED,
    IN  p_remarks       TEXT,
    OUT p_assignment_id INT UNSIGNED,
    OUT p_status        VARCHAR(50),
    OUT p_message       VARCHAR(500)
)
allocation: BEGIN
    DECLARE v_resource_status  VARCHAR(20);
    DECLARE v_resource_qty     INT;
    DECLARE v_shelter_capacity INT;
    DECLARE v_shelter_occupancy INT;
    DECLARE v_request_status   VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status  = 'ERROR';
        SET p_message = 'Database error during assignment. Transaction rolled back.';
    END;

    -- Start transaction (Unit 4 – Transactions)
    START TRANSACTION;

    -- Validate request exists and is open
    SELECT status INTO v_request_status
    FROM EMERGENCY_REQUEST
    WHERE request_id = p_request_id
    FOR UPDATE;  -- Lock the row (Unit 4 – Locking)

    IF v_request_status IS NULL THEN
        ROLLBACK;
        SET p_status  = 'FAIL';
        SET p_message = CONCAT('Emergency request #', p_request_id, ' not found.');
        SET p_assignment_id = NULL;
        LEAVE allocation;
    END IF;

    IF v_request_status IN ('RESOLVED','CLOSED') THEN
        ROLLBACK;
        SET p_status  = 'FAIL';
        SET p_message = 'Cannot assign to a RESOLVED or CLOSED request.';
        SET p_assignment_id = NULL;
        LEAVE allocation;
    END IF;

    -- Check resource if provided
    IF p_resource_id IS NOT NULL THEN
        SELECT status, quantity
        INTO v_resource_status, v_resource_qty
        FROM RESOURCE WHERE resource_id = p_resource_id FOR UPDATE;

        IF v_resource_status NOT IN ('AVAILABLE') OR v_resource_qty <= 0 THEN
            ROLLBACK;
            SET p_status  = 'FAIL';
            SET p_message = CONCAT('Resource #', p_resource_id, ' is not available. Status: ', IFNULL(v_resource_status,'N/A'));
            SET p_assignment_id = NULL;
            LEAVE allocation;
        END IF;
    END IF;

    -- Check shelter if provided
    IF p_shelter_id IS NOT NULL THEN
        SELECT capacity, current_occupancy
        INTO v_shelter_capacity, v_shelter_occupancy
        FROM SHELTER WHERE shelter_id = p_shelter_id FOR UPDATE;

        IF v_shelter_occupancy >= v_shelter_capacity THEN
            ROLLBACK;
            SET p_status  = 'FAIL';
            SET p_message = CONCAT('Shelter #', p_shelter_id, ' is at full capacity.');
            SET p_assignment_id = NULL;
            LEAVE allocation;
        END IF;
    END IF;

    -- Insert the assignment
    INSERT INTO ASSIGNMENT (assigned_time, status, remarks, request_id, resource_id, shelter_id, assigned_by)
    VALUES (NOW(), 'ACTIVE', p_remarks, p_request_id,
            NULLIF(p_resource_id, 0), NULLIF(p_shelter_id, 0), p_assigned_by);

    SET p_assignment_id = LAST_INSERT_ID();

    -- Update request status to ASSIGNED
    UPDATE EMERGENCY_REQUEST
    SET status = 'ASSIGNED'
    WHERE request_id = p_request_id AND status = 'PENDING';

    -- Update resource status to DEPLOYED if resource assigned
    IF p_resource_id IS NOT NULL THEN
        UPDATE RESOURCE SET status = 'DEPLOYED'
        WHERE resource_id = p_resource_id;
    END IF;

    COMMIT;

    SET p_status  = 'SUCCESS';
    SET p_message = CONCAT('Assignment #', p_assignment_id, ' created successfully.');
END$$

-- PROCEDURE 2: Get dashboard statistics for admin
DROP PROCEDURE IF EXISTS sp_dashboard_stats$$
CREATE PROCEDURE sp_dashboard_stats()
BEGIN
    -- Total requests by status
    SELECT status, COUNT(*) AS request_count, SUM(people_count) AS people_affected
    FROM EMERGENCY_REQUEST
    GROUP BY status;

    -- Resources availability summary
    SELECT
        rt.type_name,
        SUM(CASE WHEN r.status = 'AVAILABLE' THEN r.quantity ELSE 0 END) AS available,
        SUM(CASE WHEN r.status = 'DEPLOYED'  THEN r.quantity ELSE 0 END) AS deployed,
        COUNT(r.resource_id) AS total_resources
    FROM RESOURCE_TYPE rt
    LEFT JOIN RESOURCE r ON r.type_id = rt.type_id
    GROUP BY rt.type_id, rt.type_name;

    -- Active incidents with request counts
    SELECT i.incident_id, i.title, i.incident_type, i.severity,
           COUNT(DISTINCT er.request_id) AS requests
    FROM INCIDENT i
    LEFT JOIN EMERGENCY_REQUEST er ON er.incident_id = i.incident_id
    WHERE i.status = 'ACTIVE'
    GROUP BY i.incident_id, i.title, i.incident_type, i.severity;

    -- Shelter occupancy
    SELECT shelter_name, capacity, current_occupancy,
           ROUND(current_occupancy * 100.0 / capacity, 1) AS pct_full
    FROM SHELTER
    WHERE status != 'CLOSED'
    ORDER BY pct_full DESC;
END$$

-- PROCEDURE 3: Update shelter occupancy safely (with locking)
DROP PROCEDURE IF EXISTS sp_update_shelter_occupancy$$
CREATE PROCEDURE sp_update_shelter_occupancy(
    IN  p_shelter_id     INT UNSIGNED,
    IN  p_delta          INT,          -- positive = people arriving, negative = leaving
    OUT p_new_occupancy  INT,
    OUT p_message        VARCHAR(200)
)
BEGIN
    DECLARE v_capacity    INT;
    DECLARE v_occupancy   INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_message = 'Error updating shelter occupancy. Rolled back.';
    END;

    START TRANSACTION;

    SELECT capacity, current_occupancy
    INTO v_capacity, v_occupancy
    FROM SHELTER WHERE shelter_id = p_shelter_id FOR UPDATE;

    SET v_occupancy = v_occupancy + p_delta;

    IF v_occupancy < 0 THEN
        ROLLBACK;
        SET p_message = 'Cannot reduce occupancy below 0.';
        SET p_new_occupancy = -1;
    ELSEIF v_occupancy > v_capacity THEN
        ROLLBACK;
        SET p_message = CONCAT('Shelter full. Max: ', v_capacity);
        SET p_new_occupancy = -1;
    ELSE
        UPDATE SHELTER
        SET current_occupancy = v_occupancy
        WHERE shelter_id = p_shelter_id;
        COMMIT;
        SET p_new_occupancy = v_occupancy;
        SET p_message = 'Occupancy updated successfully.';
    END IF;
END$$

-- PROCEDURE 4: Search resources matching a request type
DROP PROCEDURE IF EXISTS sp_find_resources_for_request$$
CREATE PROCEDURE sp_find_resources_for_request(IN p_request_id INT UNSIGNED)
BEGIN
    SELECT
        r.resource_id,
        r.resource_name,
        r.quantity,
        r.status         AS resource_status,
        rt.type_name,
        l.area_name      AS resource_location,
        o.org_name       AS organization,
        rrt.quantity_required
    FROM REQUEST_RESOURCE_TYPE rrt
    INNER JOIN RESOURCE_TYPE rt ON rrt.type_id  = rt.type_id
    INNER JOIN RESOURCE r       ON r.type_id    = rt.type_id
    INNER JOIN LOCATION l       ON r.location_id = l.location_id
    INNER JOIN ORGANIZATION o   ON r.org_id     = o.org_id
    WHERE rrt.request_id = p_request_id
      AND r.status = 'AVAILABLE'
      AND r.quantity >= rrt.quantity_required
    ORDER BY r.quantity DESC;
END$$

DELIMITER ;


-- =============================================================================
-- CTEs and Window Functions (Unit 2 – CTEs and Window Functions)
-- These are placed in the advanced_sql directory for documentation but
-- also defined here as named queries accessible from application
-- =============================================================================

-- CTE Example 1: Recursive-style CTE for incident request chains
-- (Stored as a view with CTE internally)
CREATE OR REPLACE VIEW vw_request_chain AS
WITH request_summary AS (
    SELECT
        er.incident_id,
        er.request_type,
        COUNT(*)                   AS type_count,
        SUM(er.people_count)       AS type_affected,
        SUM(CASE WHEN er.medical_needed = 1 THEN 1 ELSE 0 END) AS medical_count
    FROM EMERGENCY_REQUEST er
    WHERE er.incident_id IS NOT NULL
    GROUP BY er.incident_id, er.request_type
),
incident_totals AS (
    SELECT
        incident_id,
        SUM(type_count)     AS total_requests,
        SUM(type_affected)  AS total_affected,
        SUM(medical_count)  AS total_medical
    FROM request_summary
    GROUP BY incident_id
)
SELECT
    rs.incident_id,
    i.title          AS incident_title,
    rs.request_type,
    rs.type_count,
    rs.type_affected,
    rs.medical_count,
    it.total_requests,
    it.total_affected,
    ROUND(rs.type_count * 100.0 / it.total_requests, 1) AS pct_of_incident
FROM request_summary rs
INNER JOIN incident_totals it ON rs.incident_id = it.incident_id
INNER JOIN INCIDENT i         ON i.incident_id  = rs.incident_id
ORDER BY rs.incident_id, rs.type_count DESC;

-- Window Function View: Request ranking by priority within each incident
CREATE OR REPLACE VIEW vw_request_priority_rank AS
SELECT
    er.request_id,
    er.incident_id,
    i.title          AS incident_title,
    er.request_type,
    er.priority,
    er.people_count,
    er.status,
    -- Window function: rank within incident by priority (CRITICAL=1)
    ROW_NUMBER() OVER (
        PARTITION BY er.incident_id
        ORDER BY
            FIELD(er.priority,'CRITICAL','HIGH','MEDIUM','LOW'),
            er.request_time ASC
    )                AS priority_rank,
    -- Running total of affected people per incident
    SUM(er.people_count) OVER (
        PARTITION BY er.incident_id
        ORDER BY er.request_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                AS running_people_total,
    -- Average priority people count per incident
    AVG(er.people_count) OVER (PARTITION BY er.incident_id)
                     AS avg_people_per_request,
    -- Dense rank across all requests by priority
    DENSE_RANK() OVER (
        ORDER BY FIELD(er.priority,'CRITICAL','HIGH','MEDIUM','LOW')
    )                AS global_priority_rank
FROM EMERGENCY_REQUEST er
LEFT JOIN INCIDENT i ON er.incident_id = i.incident_id;

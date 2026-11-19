-- =============================================================================
-- CrisisLink - FILE: 08_advanced_routines.sql
-- PURPOSE : New stored functions, stored procedures, triggers and a view.
-- RE-RUNNABLE: every object is DROP ... IF EXISTS / CREATE OR REPLACE'd.
-- Only objects created by THIS file (or the no-op trigger from 03, which is
-- replaced as agreed) are dropped. Existing routines are NOT touched.
-- RUN AS  : administrative MySQL account (CREATE ROUTINE / TRIGGER privileges)
-- REQUIRES: 06_additive_schema.sql and 07_hierarchy_and_coordinator_data.sql
-- =============================================================================

USE crisislink_db;

DELIMITER $$

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- F1: free beds in a shelter. CLOSED shelters have 0 usable capacity. NULL if unknown shelter.
DROP FUNCTION IF EXISTS fn_shelter_available_capacity$$
CREATE FUNCTION fn_shelter_available_capacity(p_shelter_id INT UNSIGNED)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_cap INT;
    DECLARE v_occ INT;
    DECLARE v_status VARCHAR(10);

    SELECT capacity, current_occupancy, status
      INTO v_cap, v_occ, v_status
      FROM SHELTER WHERE shelter_id = p_shelter_id;

    IF v_cap IS NULL THEN
        RETURN NULL;
    END IF;
    IF v_status = 'CLOSED' THEN
        RETURN 0;
    END IF;
    RETURN GREATEST(v_cap - v_occ, 0);
END$$

-- F2: total resource units currently allocated to an incident (cancelled assignments excluded)
DROP FUNCTION IF EXISTS fn_incident_total_allocated$$
CREATE FUNCTION fn_incident_total_allocated(p_incident_id INT UNSIGNED)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_total INT;

    SELECT COALESCE(SUM(a.quantity_allocated), 0)
      INTO v_total
      FROM ASSIGNMENT a
      JOIN EMERGENCY_REQUEST er ON er.request_id = a.request_id
     WHERE er.incident_id = p_incident_id
       AND a.status <> 'CANCELLED';

    RETURN v_total;
END$$

-- =============================================================================
-- PROCEDURES
-- =============================================================================

-- P1: allocate a resource (partial quantities allowed) and/or a shelter place
--     to an emergency request, atomically.
--   * p_quantity NULL  -> allocate what the request still needs, capped by stock
--                         (partial allocation); explicit quantity > stock is REJECTED
--   * p_people   NULL  -> house the people still unhoused, capped by free beds
--   * Row locks (FOR UPDATE) on request, resource and shelter prevent two
--     coordinators over-allocating at the same time.
--   * Stock is deducted by inserting an OUT row in INVENTORY_TRANSACTION; the
--     existing trigger trg_inventory_out_deduct performs the deduction ONCE.
DROP PROCEDURE IF EXISTS sp_allocate_assignment$$
CREATE PROCEDURE sp_allocate_assignment(
    IN  p_request_id  INT UNSIGNED,
    IN  p_resource_id INT UNSIGNED,
    IN  p_quantity    INT UNSIGNED,
    IN  p_shelter_id  INT UNSIGNED,
    IN  p_people      INT UNSIGNED,
    IN  p_assigned_by INT UNSIGNED,
    IN  p_remarks     TEXT,
    OUT p_assignment_id INT UNSIGNED,
    OUT p_status        VARCHAR(20),
    OUT p_message       VARCHAR(500)
)
proc: BEGIN
    DECLARE v_req_status  VARCHAR(20);
    DECLARE v_req_people  INT;
    DECLARE v_res_qty     INT;
    DECLARE v_res_status  VARCHAR(20);
    DECLARE v_type_id     INT UNSIGNED;
    DECLARE v_required    INT;
    DECLARE v_already     INT DEFAULT 0;
    DECLARE v_qty         INT DEFAULT NULL;
    DECLARE v_sh_cap      INT;
    DECLARE v_sh_occ      INT;
    DECLARE v_sh_status   VARCHAR(10);
    DECLARE v_housed_prev INT DEFAULT 0;
    DECLARE v_people      INT DEFAULT NULL;
    DECLARE v_free        INT;
    DECLARE v_err         TEXT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_err = MESSAGE_TEXT;
        ROLLBACK;
        SET p_assignment_id = NULL;
        SET p_status  = 'ERROR';
        SET p_message = CONCAT('Database error: ', COALESCE(v_err, 'unknown'));
    END;

    SET p_assignment_id = NULL;
    SET p_status  = 'ERROR';
    SET p_message = '';

    IF p_resource_id IS NULL AND p_shelter_id IS NULL THEN
        SET p_message = 'Provide a resource, a shelter, or both.';
        LEAVE proc;
    END IF;
    IF p_quantity IS NOT NULL AND p_quantity < 1 THEN
        SET p_message = 'Quantity must be at least 1.';
        LEAVE proc;
    END IF;
    IF p_people IS NOT NULL AND p_people < 1 THEN
        SET p_message = 'People count must be at least 1.';
        LEAVE proc;
    END IF;
    IF p_quantity IS NOT NULL AND p_resource_id IS NULL THEN
        SET p_message = 'A quantity needs a resource.';
        LEAVE proc;
    END IF;
    IF p_people IS NOT NULL AND p_shelter_id IS NULL THEN
        SET p_message = 'A people count needs a shelter.';
        LEAVE proc;
    END IF;

    START TRANSACTION;

    -- ---- request ----------------------------------------------------------
    SELECT status, people_count INTO v_req_status, v_req_people
      FROM EMERGENCY_REQUEST WHERE request_id = p_request_id FOR UPDATE;

    IF v_req_status IS NULL THEN
        ROLLBACK; SET p_message = 'Emergency request not found.'; LEAVE proc;
    END IF;
    IF v_req_status IN ('RESOLVED', 'CLOSED') THEN
        ROLLBACK; SET p_message = CONCAT('Request is already ', v_req_status, '; cannot allocate.'); LEAVE proc;
    END IF;

    -- ---- resource part ----------------------------------------------------
    IF p_resource_id IS NOT NULL THEN
        SELECT quantity, status, type_id INTO v_res_qty, v_res_status, v_type_id
          FROM RESOURCE WHERE resource_id = p_resource_id FOR UPDATE;

        IF v_res_status IS NULL THEN
            ROLLBACK; SET p_message = 'Resource not found.'; LEAVE proc;
        END IF;
        IF v_res_status IN ('MAINTENANCE', 'EXHAUSTED') OR v_res_qty <= 0 THEN
            ROLLBACK; SET p_message = CONCAT('Resource is not allocatable (status ', v_res_status, ', stock ', v_res_qty, ').'); LEAVE proc;
        END IF;

        -- what the request asked for of this resource type (NULL = no stated requirement)
        SELECT quantity_required INTO v_required
          FROM REQUEST_RESOURCE_TYPE WHERE request_id = p_request_id AND type_id = v_type_id;

        -- units of this type already given to this request (cancelled ones do not count)
        SELECT COALESCE(SUM(a.quantity_allocated), 0) INTO v_already
          FROM ASSIGNMENT a JOIN RESOURCE r ON r.resource_id = a.resource_id
         WHERE a.request_id = p_request_id AND r.type_id = v_type_id AND a.status <> 'CANCELLED';

        IF p_quantity IS NULL THEN
            IF v_required IS NULL THEN
                SET v_qty = 1;
            ELSE
                SET v_qty = LEAST(GREATEST(v_required - v_already, 0), v_res_qty);   -- partial allocation
                IF v_required - v_already <= 0 THEN
                    ROLLBACK; SET p_message = 'The requirement for this resource type is already fully allocated.'; LEAVE proc;
                END IF;
            END IF;
        ELSE
            SET v_qty = p_quantity;
            IF v_qty > v_res_qty THEN
                ROLLBACK;
                SET p_message = CONCAT('Insufficient stock: requested ', v_qty, ', available ', v_res_qty, '.');
                LEAVE proc;
            END IF;
            IF v_required IS NOT NULL AND v_already + v_qty > v_required THEN
                ROLLBACK;
                SET p_message = CONCAT('Over-allocation: request needs ', v_required, ', already allocated ', v_already, ', cannot add ', v_qty, '.');
                LEAVE proc;
            END IF;
        END IF;
    END IF;

    -- ---- shelter part -----------------------------------------------------
    IF p_shelter_id IS NOT NULL THEN
        SELECT capacity, current_occupancy, status INTO v_sh_cap, v_sh_occ, v_sh_status
          FROM SHELTER WHERE shelter_id = p_shelter_id FOR UPDATE;

        IF v_sh_status IS NULL THEN
            ROLLBACK; SET p_message = 'Shelter not found.'; LEAVE proc;
        END IF;
        IF v_sh_status = 'CLOSED' THEN
            ROLLBACK; SET p_message = 'Shelter is CLOSED.'; LEAVE proc;
        END IF;

        SET v_free = v_sh_cap - v_sh_occ;
        IF v_free <= 0 THEN
            ROLLBACK; SET p_message = 'Shelter is full.'; LEAVE proc;
        END IF;

        SELECT COALESCE(SUM(people_housed), 0) INTO v_housed_prev
          FROM ASSIGNMENT WHERE request_id = p_request_id AND status <> 'CANCELLED';

        IF p_people IS NULL THEN
            IF v_req_people - v_housed_prev <= 0 THEN
                ROLLBACK; SET p_message = 'Everyone in this request is already housed.'; LEAVE proc;
            END IF;
            SET v_people = LEAST(v_req_people - v_housed_prev, v_free);                -- partial housing
        ELSE
            SET v_people = p_people;
            IF v_people > v_free THEN
                ROLLBACK;
                SET p_message = CONCAT('Insufficient shelter capacity: requested ', v_people, ', free ', v_free, '.');
                LEAVE proc;
            END IF;
        END IF;
    END IF;

    -- ---- write ------------------------------------------------------------
    INSERT INTO ASSIGNMENT (status, remarks, request_id, resource_id, shelter_id, assigned_by,
                            quantity_allocated, people_housed)
    VALUES ('ACTIVE', p_remarks, p_request_id, p_resource_id, p_shelter_id, p_assigned_by,
            v_qty, v_people);
    SET p_assignment_id = LAST_INSERT_ID();

    IF p_resource_id IS NOT NULL THEN
        -- AFTER INSERT trigger trg_inventory_out_deduct subtracts the stock (once)
        INSERT INTO INVENTORY_TRANSACTION (quantity, transaction_type, notes, resource_id, assignment_id, performed_by)
        VALUES (v_qty, 'OUT', CONCAT('Allocated to request #', p_request_id), p_resource_id, p_assignment_id, p_assigned_by);
    END IF;

    IF p_shelter_id IS NOT NULL THEN
        -- BEFORE UPDATE trigger trg_shelter_occupancy_update maintains OPEN/FULL
        UPDATE SHELTER SET current_occupancy = current_occupancy + v_people WHERE shelter_id = p_shelter_id;
    END IF;

    IF v_req_status = 'PENDING' THEN
        UPDATE EMERGENCY_REQUEST SET status = 'ASSIGNED' WHERE request_id = p_request_id;
    END IF;

    COMMIT;

    SET p_status  = 'SUCCESS';
    SET p_message = CONCAT('Assignment #', p_assignment_id, ' created.',
        IF(v_qty IS NOT NULL, CONCAT(' Resource units allocated: ', v_qty,
                                     IF(p_quantity IS NULL AND v_required IS NOT NULL AND v_qty < v_required - v_already,
                                        ' (partial - stock was the limit)', ''), '.'), ''),
        IF(v_people IS NOT NULL, CONCAT(' People housed: ', v_people,
                                        IF(p_people IS NULL AND v_people < v_req_people - v_housed_prev,
                                           ' (partial - shelter capacity was the limit)', ''), '.'), ''));
END$$

-- P2: list emergency requests filtered by status and/or priority (NULL = any)
DROP PROCEDURE IF EXISTS sp_get_requests_by_filter$$
CREATE PROCEDURE sp_get_requests_by_filter(
    IN p_status   VARCHAR(20),
    IN p_priority VARCHAR(20),
    IN p_limit    INT
)
BEGIN
    IF p_status IS NOT NULL AND p_status NOT IN ('PENDING','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid status filter';
    END IF;
    IF p_priority IS NOT NULL AND p_priority NOT IN ('LOW','MEDIUM','HIGH','CRITICAL') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid priority filter';
    END IF;

    SELECT er.request_id, er.request_type, er.priority, er.status, er.people_count,
           er.request_time, u.full_name AS requester, l.area_name, l.district, er.incident_id,
           (SELECT COUNT(*) FROM ASSIGNMENT a
             WHERE a.request_id = er.request_id AND a.status <> 'CANCELLED') AS active_assignments
      FROM EMERGENCY_REQUEST er
      JOIN `USER` u    ON u.user_id = er.user_id
      JOIN LOCATION l  ON l.location_id = er.location_id
     WHERE (p_status   IS NULL OR er.status   = p_status)
       AND (p_priority IS NULL OR er.priority = p_priority)
     ORDER BY FIELD(er.priority, 'CRITICAL','HIGH','MEDIUM','LOW'), er.request_time
     LIMIT p_limit;
END$$

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- T0: the placeholder trigger from 03 did nothing (WHERE FALSE) -> replaced by T1 below
DROP TRIGGER IF EXISTS trg_critical_request_audit$$

-- T1: audit every incident status change
DROP TRIGGER IF EXISTS trg_incident_status_audit$$
CREATE TRIGGER trg_incident_status_audit
AFTER UPDATE ON INCIDENT
FOR EACH ROW
BEGIN
    IF NOT (OLD.status <=> NEW.status) THEN
        INSERT INTO INCIDENT_STATUS_AUDIT (incident_id, old_status, new_status, changed_by_user_id, db_account)
        VALUES (NEW.incident_id, OLD.status, NEW.status, @app_user_id, CURRENT_USER());
    END IF;
END$$

-- T2: tell the citizen when the status of their request changes
DROP TRIGGER IF EXISTS trg_request_status_notify$$
CREATE TRIGGER trg_request_status_notify
AFTER UPDATE ON EMERGENCY_REQUEST
FOR EACH ROW
BEGIN
    IF NOT (OLD.status <=> NEW.status) THEN
        INSERT INTO NOTIFICATION (user_id, request_id, notif_type, title, message)
        VALUES (NEW.user_id, NEW.request_id,
                IF(NEW.status = 'ASSIGNED', 'ASSIGNMENT', 'REQUEST_UPDATE'),
                CONCAT('Request #', NEW.request_id, ' is now ', NEW.status),
                CONCAT('Your ', NEW.request_type, ' request status changed from ', OLD.status, ' to ', NEW.status, '.'));
    END IF;
END$$

-- T3: a cancelled assignment can never be re-activated (would double-count stock)
DROP TRIGGER IF EXISTS trg_assignment_cancel_guard$$
CREATE TRIGGER trg_assignment_cancel_guard
BEFORE UPDATE ON ASSIGNMENT
FOR EACH ROW
BEGIN
    IF OLD.status = 'CANCELLED' AND NEW.status <> 'CANCELLED' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A cancelled assignment cannot be re-activated; create a new assignment instead.';
    END IF;
END$$

-- T4: cancelling an assignment returns the stock and frees the shelter places.
--     Fires only on the transition to CANCELLED, so it can never run twice.
DROP TRIGGER IF EXISTS trg_assignment_cancel_restore$$
CREATE TRIGGER trg_assignment_cancel_restore
AFTER UPDATE ON ASSIGNMENT
FOR EACH ROW
BEGIN
    IF OLD.status <> 'CANCELLED' AND NEW.status = 'CANCELLED' THEN
        IF NEW.resource_id IS NOT NULL AND NEW.quantity_allocated IS NOT NULL THEN
            -- the IN row makes trg_inventory_out_deduct add the stock back
            INSERT INTO INVENTORY_TRANSACTION (quantity, transaction_type, notes, resource_id, assignment_id, performed_by)
            VALUES (NEW.quantity_allocated, 'IN',
                    CONCAT('Stock returned: assignment #', NEW.assignment_id, ' cancelled'),
                    NEW.resource_id, NEW.assignment_id, NEW.assigned_by);
        END IF;
        IF NEW.shelter_id IS NOT NULL AND NEW.people_housed IS NOT NULL THEN
            UPDATE SHELTER
               SET current_occupancy = GREATEST(CAST(current_occupancy AS SIGNED) - CAST(NEW.people_housed AS SIGNED), 0)
             WHERE shelter_id = NEW.shelter_id;
        END IF;
    END IF;
END$$

-- T5: the location hierarchy may not contain a cycle (self-parent or parent = own descendant)
DROP TRIGGER IF EXISTS trg_location_no_cycle$$
CREATE TRIGGER trg_location_no_cycle
BEFORE UPDATE ON LOCATION
FOR EACH ROW
BEGIN
    DECLARE v_is_descendant INT DEFAULT 0;

    IF NEW.parent_location_id IS NOT NULL AND NOT (OLD.parent_location_id <=> NEW.parent_location_id) THEN
        IF NEW.parent_location_id = NEW.location_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A location cannot be its own parent.';
        END IF;

        SELECT COUNT(*) INTO v_is_descendant
          FROM (
              WITH RECURSIVE descendants AS (
                  SELECT location_id FROM LOCATION WHERE parent_location_id = NEW.location_id
                  UNION ALL
                  SELECT c.location_id FROM LOCATION c
                    JOIN descendants d ON c.parent_location_id = d.location_id
              )
              SELECT location_id FROM descendants
          ) x
         WHERE x.location_id = NEW.parent_location_id;

        IF v_is_descendant > 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cycle detected: the new parent is a descendant of this location.';
        END IF;
    END IF;
END$$

DELIMITER ;

-- =============================================================================
-- VIEW: location hierarchy (recursive CTE inside a view, MySQL 8.0)
-- =============================================================================
CREATE OR REPLACE VIEW vw_location_tree AS
WITH RECURSIVE tree AS (
    SELECT location_id, parent_location_id, area_name,
           0 AS depth,
           CAST(area_name AS CHAR(500)) AS path
      FROM LOCATION
     WHERE parent_location_id IS NULL
    UNION ALL
    SELECT c.location_id, c.parent_location_id, c.area_name,
           t.depth + 1,
           CONCAT(t.path, ' > ', c.area_name)
      FROM LOCATION c
      JOIN tree t ON c.parent_location_id = t.location_id
)
SELECT location_id, parent_location_id, area_name, depth, path FROM tree;

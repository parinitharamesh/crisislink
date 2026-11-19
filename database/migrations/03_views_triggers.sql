-- =============================================================================
-- CrisisLink – Disaster Response Coordination System
-- FILE: 03_views_triggers.sql  (Phase 3 – Advanced SQL Part 1)
-- PURPOSE: Views, Triggers covering Unit 2 syllabus topics
-- =============================================================================

USE crisislink_db;

-- =============================================================================
-- VIEWS (Unit 2 – Views)
-- =============================================================================

-- VIEW 1: Active emergency requests with requester and location info
CREATE OR REPLACE VIEW vw_active_requests AS
SELECT
    er.request_id,
    er.request_type,
    er.description,
    er.people_count,
    er.medical_needed,
    er.priority,
    er.status,
    er.request_time,
    u.full_name      AS requester_name,
    u.phone          AS requester_phone,
    l.area_name      AS location_name,
    l.district,
    l.state,
    i.title          AS incident_title,
    i.incident_type
FROM EMERGENCY_REQUEST er
INNER JOIN `USER`       u  ON er.user_id     = u.user_id
INNER JOIN LOCATION     l  ON er.location_id = l.location_id
LEFT  JOIN INCIDENT     i  ON er.incident_id = i.incident_id
WHERE er.status NOT IN ('CLOSED');

-- VIEW 2: Resource availability summary per organization
CREATE OR REPLACE VIEW vw_resource_availability AS
SELECT
    o.org_id,
    o.org_name,
    rt.type_name     AS resource_type,
    COUNT(r.resource_id)   AS total_resources,
    SUM(r.quantity)        AS total_quantity,
    SUM(CASE WHEN r.status = 'AVAILABLE' THEN r.quantity ELSE 0 END) AS available_qty,
    SUM(CASE WHEN r.status = 'DEPLOYED'  THEN r.quantity ELSE 0 END) AS deployed_qty
FROM ORGANIZATION o
LEFT JOIN RESOURCE      r  ON r.org_id  = o.org_id
LEFT JOIN RESOURCE_TYPE rt ON r.type_id = rt.type_id
GROUP BY o.org_id, o.org_name, rt.type_name;

-- VIEW 3: Shelter occupancy status
CREATE OR REPLACE VIEW vw_shelter_status AS
SELECT
    s.shelter_id,
    s.shelter_name,
    s.address,
    s.capacity,
    s.current_occupancy,
    (s.capacity - s.current_occupancy)   AS available_spots,
    ROUND(s.current_occupancy * 100.0 / s.capacity, 1) AS occupancy_pct,
    s.has_medical_facility,
    s.status,
    l.area_name    AS location_name,
    l.district,
    o.org_name     AS operated_by
FROM SHELTER s
INNER JOIN LOCATION     l ON s.location_id = l.location_id
INNER JOIN ORGANIZATION o ON s.org_id      = o.org_id;

-- VIEW 4: Incident response summary (joins multiple tables)
CREATE OR REPLACE VIEW vw_incident_summary AS
SELECT
    i.incident_id,
    i.title          AS incident_title,
    i.incident_type,
    i.severity,
    i.status         AS incident_status,
    i.start_date,
    l.area_name      AS location_name,
    l.state,
    COUNT(DISTINCT er.request_id)    AS total_requests,
    SUM(er.people_count)             AS total_affected,
    COUNT(DISTINCT a.assignment_id)  AS total_assignments,
    SUM(CASE WHEN er.status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_count,
    SUM(CASE WHEN er.status = 'PENDING'  THEN 1 ELSE 0 END) AS pending_count
FROM INCIDENT i
INNER JOIN LOCATION l            ON i.location_id  = l.location_id
LEFT  JOIN EMERGENCY_REQUEST er  ON er.incident_id = i.incident_id
LEFT  JOIN ASSIGNMENT a          ON a.request_id   = er.request_id
GROUP BY i.incident_id, i.title, i.incident_type, i.severity,
         i.status, i.start_date, l.area_name, l.state;

-- VIEW 5: Coordinator dashboard – requests needing action (PENDING + no assignment)
CREATE OR REPLACE VIEW vw_unassigned_requests AS
SELECT
    er.request_id,
    er.request_type,
    er.priority,
    er.people_count,
    er.medical_needed,
    er.request_time,
    u.full_name   AS citizen_name,
    u.phone       AS citizen_phone,
    l.area_name,
    l.district,
    i.title       AS incident_title,
    TIMESTAMPDIFF(HOUR, er.request_time, NOW()) AS hours_waiting
FROM EMERGENCY_REQUEST er
INNER JOIN `USER`   u ON er.user_id     = u.user_id
INNER JOIN LOCATION l ON er.location_id = l.location_id
LEFT  JOIN INCIDENT i ON er.incident_id = i.incident_id
WHERE er.status = 'PENDING'
  AND er.request_id NOT IN (SELECT DISTINCT request_id FROM ASSIGNMENT);

-- VIEW 6: Inventory audit view (joins resources, assignments, users)
CREATE OR REPLACE VIEW vw_inventory_audit AS
SELECT
    it.transaction_id,
    it.transaction_type,
    it.quantity,
    it.notes,
    it.transaction_time,
    r.resource_name,
    rt.type_name   AS resource_type,
    o.org_name     AS organization,
    a.assignment_id,
    u.full_name    AS performed_by
FROM INVENTORY_TRANSACTION it
INNER JOIN RESOURCE      r  ON it.resource_id   = r.resource_id
INNER JOIN RESOURCE_TYPE rt ON r.type_id        = rt.type_id
INNER JOIN ORGANIZATION  o  ON r.org_id         = o.org_id
LEFT  JOIN ASSIGNMENT    a  ON it.assignment_id = a.assignment_id
LEFT  JOIN `USER`        u  ON it.performed_by  = u.user_id
ORDER BY it.transaction_time DESC;

-- =============================================================================
-- TRIGGERS (Unit 2 – Triggers)
-- =============================================================================

DELIMITER $$

-- TRIGGER 1: Update resource status when quantity drops to 0
CREATE TRIGGER trg_resource_qty_check
BEFORE UPDATE ON RESOURCE
FOR EACH ROW
BEGIN
    -- Prevent negative quantity
    IF NEW.quantity < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Resource quantity cannot be negative.';
    END IF;

    -- Auto-mark as EXHAUSTED when quantity hits 0
    IF NEW.quantity = 0 AND OLD.quantity > 0 THEN
        SET NEW.status = 'EXHAUSTED';
    END IF;

    -- Auto-mark as AVAILABLE when restocked from 0
    IF NEW.quantity > 0 AND OLD.quantity = 0 AND NEW.status = 'EXHAUSTED' THEN
        SET NEW.status = 'AVAILABLE';
    END IF;
END$$

-- TRIGGER 2: Enforce shelter occupancy constraint on UPDATE
CREATE TRIGGER trg_shelter_occupancy_update
BEFORE UPDATE ON SHELTER
FOR EACH ROW
BEGIN
    IF NEW.current_occupancy < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Shelter occupancy cannot be negative.';
    END IF;

    IF NEW.current_occupancy > NEW.capacity THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Shelter occupancy cannot exceed total capacity.';
    END IF;

    -- Auto update status based on occupancy
    IF NEW.current_occupancy >= NEW.capacity THEN
        SET NEW.status = 'FULL';
    ELSEIF NEW.current_occupancy < NEW.capacity AND NEW.status = 'FULL' THEN
        SET NEW.status = 'OPEN';
    END IF;
END$$

-- TRIGGER 3: Update resource quantity automatically when inventory OUT transaction happens
CREATE TRIGGER trg_inventory_out_deduct
AFTER INSERT ON INVENTORY_TRANSACTION
FOR EACH ROW
BEGIN
    IF NEW.transaction_type = 'OUT' THEN
        UPDATE RESOURCE
        SET quantity = quantity - NEW.quantity
        WHERE resource_id = NEW.resource_id AND quantity >= NEW.quantity;

        IF ROW_COUNT() = 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Insufficient inventory for OUT transaction.';
        END IF;
    END IF;

    IF NEW.transaction_type = 'IN' THEN
        UPDATE RESOURCE
        SET quantity = quantity + NEW.quantity
        WHERE resource_id = NEW.resource_id;
    END IF;
END$$

-- TRIGGER 4: Auto-set EMERGENCY_REQUEST resolved_time when status becomes RESOLVED
CREATE TRIGGER trg_request_resolved_time
BEFORE UPDATE ON EMERGENCY_REQUEST
FOR EACH ROW
BEGIN
    IF NEW.status = 'RESOLVED' AND OLD.status != 'RESOLVED'
       AND NEW.resolved_time IS NULL THEN
        SET NEW.resolved_time = NOW();
    END IF;
END$$

-- TRIGGER 5: Log a message if CRITICAL request goes unassigned for over 2 hours
--            (Demonstration trigger – in production, this would alert coordinators)
CREATE TRIGGER trg_critical_request_audit
AFTER INSERT ON EMERGENCY_REQUEST
FOR EACH ROW
BEGIN
    -- Insert an audit log entry for CRITICAL requests
    IF NEW.priority = 'CRITICAL' THEN
        INSERT INTO INVENTORY_TRANSACTION
            (quantity, transaction_type, notes, transaction_time, resource_id, performed_by)
        SELECT 0, 'ADJUSTMENT',
               CONCAT('AUDIT: CRITICAL request #', NEW.request_id, ' submitted at ', NEW.request_time),
               NOW(), 1, NEW.user_id
        WHERE FALSE;  -- Placeholder structure; in real system would go to audit_log table
    END IF;
END$$

DELIMITER ;

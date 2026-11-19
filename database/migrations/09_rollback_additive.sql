-- =============================================================================
-- CrisisLink - FILE: 09_rollback_additive.sql      (MANUAL USE ONLY)
-- PURPOSE : Undo migrations 06, 07 and 08 and return to the original schema.
--
-- !! READ BEFORE RUNNING !!
--  * Take a fresh backup first (see database/BACKUP_AND_ROLLBACK.md).
--  * This DELETES the data stored in the NEW objects only:
--      - INCIDENT_STATUS_AUDIT rows, NOTIFICATION rows
--      - quantity_allocated / people_housed / coordinator_id / parent_location_id values
--      - the 16 location hierarchy nodes (India, 7 states, 8 districts) added by 07
--  * Original rows in every ORIGINAL table are kept.
--  * If a request/resource/shelter was created AT one of the 16 hierarchy nodes,
--    the final DELETE fails on purpose (foreign key) - nothing is half-removed.
--  * Re-runnable: each step checks that the object still exists.
--  * The safest rollback is always: restore the backup taken before migrating.
-- =============================================================================

USE crisislink_db;

-- 1. triggers added by 08 ---------------------------------------------------
DROP TRIGGER IF EXISTS trg_incident_status_audit;
DROP TRIGGER IF EXISTS trg_request_status_notify;
DROP TRIGGER IF EXISTS trg_assignment_cancel_guard;
DROP TRIGGER IF EXISTS trg_assignment_cancel_restore;
DROP TRIGGER IF EXISTS trg_location_no_cycle;

-- restore the original placeholder trigger removed by 08
DROP TRIGGER IF EXISTS trg_critical_request_audit;
DELIMITER $$
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

-- 2. routines and view added by 08 -------------------------------------------
DROP FUNCTION  IF EXISTS fn_shelter_available_capacity;
DROP FUNCTION  IF EXISTS fn_incident_total_allocated;
DROP PROCEDURE IF EXISTS sp_allocate_assignment;
DROP PROCEDURE IF EXISTS sp_get_requests_by_filter;
DROP VIEW      IF EXISTS vw_location_tree;

-- 3. helper procedures (conditional drops) -------------------------------------
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_rb_drop_constraint$$
CREATE PROCEDURE sp_rb_drop_constraint(IN p_table VARCHAR(64), IN p_name VARCHAR(64))
BEGIN
    DECLARE v_type VARCHAR(20);
    SELECT CONSTRAINT_TYPE INTO v_type FROM information_schema.TABLE_CONSTRAINTS
     WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND CONSTRAINT_NAME = p_name;
    IF v_type IS NOT NULL THEN
        SET @rb_ddl = CONCAT('ALTER TABLE `', p_table, '` DROP ',
                             IF(v_type = 'FOREIGN KEY', 'FOREIGN KEY ', 'CHECK '), '`', p_name, '`');
        PREPARE rb_stmt FROM @rb_ddl; EXECUTE rb_stmt; DEALLOCATE PREPARE rb_stmt;
    END IF;
END$$

DROP PROCEDURE IF EXISTS sp_rb_drop_column$$
CREATE PROCEDURE sp_rb_drop_column(IN p_table VARCHAR(64), IN p_col VARCHAR(64))
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND COLUMN_NAME = p_col) THEN
        SET @rb_ddl = CONCAT('ALTER TABLE `', p_table, '` DROP COLUMN `', p_col, '`');
        PREPARE rb_stmt FROM @rb_ddl; EXECUTE rb_stmt; DEALLOCATE PREPARE rb_stmt;
    END IF;
END$$

DROP PROCEDURE IF EXISTS sp_rb_drop_index$$
CREATE PROCEDURE sp_rb_drop_index(IN p_table VARCHAR(64), IN p_name VARCHAR(64))
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.STATISTICS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND INDEX_NAME = p_name) THEN
        SET @rb_ddl = CONCAT('DROP INDEX `', p_name, '` ON `', p_table, '`');
        PREPARE rb_stmt FROM @rb_ddl; EXECUTE rb_stmt; DEALLOCATE PREPARE rb_stmt;
    END IF;
END$$
DELIMITER ;

-- 4. new tables ----------------------------------------------------------------
DROP TABLE IF EXISTS NOTIFICATION;
DROP TABLE IF EXISTS INCIDENT_STATUS_AUDIT;

-- 5. ASSIGNMENT -----------------------------------------------------------------
CALL sp_rb_drop_constraint('ASSIGNMENT', 'chk_assign_qty_positive');
CALL sp_rb_drop_constraint('ASSIGNMENT', 'chk_assign_people_positive');
CALL sp_rb_drop_column('ASSIGNMENT', 'quantity_allocated');
CALL sp_rb_drop_column('ASSIGNMENT', 'people_housed');

-- 6. INCIDENT -------------------------------------------------------------------
CALL sp_rb_drop_constraint('INCIDENT', 'fk_incident_coordinator');
CALL sp_rb_drop_index('INCIDENT', 'idx_incident_coordinator');
CALL sp_rb_drop_column('INCIDENT', 'coordinator_id');

-- 7. LOCATION -------------------------------------------------------------------
-- detach everything, then remove ONLY the nodes created by migration 07
-- (country/state markers, and district nodes where area_name = district)
CALL sp_rb_drop_constraint('LOCATION', 'fk_location_parent');
CALL sp_rb_drop_index('LOCATION', 'idx_location_parent');
DELETE FROM LOCATION WHERE district IN ('(country)', '(state)') OR area_name = district;
CALL sp_rb_drop_column('LOCATION', 'parent_location_id');

DROP PROCEDURE IF EXISTS sp_rb_drop_constraint;
DROP PROCEDURE IF EXISTS sp_rb_drop_column;
DROP PROCEDURE IF EXISTS sp_rb_drop_index;

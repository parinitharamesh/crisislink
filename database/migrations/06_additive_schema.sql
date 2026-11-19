-- =============================================================================
-- CrisisLink - FILE: 06_additive_schema.sql
-- PURPOSE : ADDITIVE and RE-RUNNABLE schema changes. Nothing is dropped,
--           no existing table is recreated, no existing row is deleted.
-- ADDS    : ASSIGNMENT.quantity_allocated, ASSIGNMENT.people_housed,
--           INCIDENT.coordinator_id, LOCATION.parent_location_id,
--           table INCIDENT_STATUS_AUDIT, table NOTIFICATION
-- RUN AS  : an administrative MySQL account (needs ALTER / CREATE / REFERENCES)
-- ORDER   : 01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07 -> 08
-- ROLLBACK: see 09_rollback_additive.sql  (take a backup first!)
-- =============================================================================

USE crisislink_db;

DELIMITER $$

-- ---- idempotency helpers (MySQL has no ADD COLUMN IF NOT EXISTS) -----------
DROP PROCEDURE IF EXISTS sp_mig_add_column$$
CREATE PROCEDURE sp_mig_add_column(IN p_table VARCHAR(64), IN p_col VARCHAR(64), IN p_def VARCHAR(500))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND COLUMN_NAME = p_col) THEN
        SET @mig_ddl = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN `', p_col, '` ', p_def);
        PREPARE mig_stmt FROM @mig_ddl;
        EXECUTE mig_stmt;
        DEALLOCATE PREPARE mig_stmt;
    END IF;
END$$

-- works for FOREIGN KEY, CHECK and UNIQUE constraints (all in TABLE_CONSTRAINTS)
DROP PROCEDURE IF EXISTS sp_mig_add_constraint$$
CREATE PROCEDURE sp_mig_add_constraint(IN p_table VARCHAR(64), IN p_name VARCHAR(64), IN p_def VARCHAR(500))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND CONSTRAINT_NAME = p_name) THEN
        SET @mig_ddl = CONCAT('ALTER TABLE `', p_table, '` ADD CONSTRAINT `', p_name, '` ', p_def);
        PREPARE mig_stmt FROM @mig_ddl;
        EXECUTE mig_stmt;
        DEALLOCATE PREPARE mig_stmt;
    END IF;
END$$

DROP PROCEDURE IF EXISTS sp_mig_add_index$$
CREATE PROCEDURE sp_mig_add_index(IN p_table VARCHAR(64), IN p_name VARCHAR(64), IN p_cols VARCHAR(200))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND INDEX_NAME = p_name) THEN
        SET @mig_ddl = CONCAT('CREATE INDEX `', p_name, '` ON `', p_table, '` (', p_cols, ')');
        PREPARE mig_stmt FROM @mig_ddl;
        EXECUTE mig_stmt;
        DEALLOCATE PREPARE mig_stmt;
    END IF;
END$$

DELIMITER ;

-- =============================================================================
-- 1. ASSIGNMENT: track HOW MUCH stock / HOW MANY people each assignment used.
--    Both nullable: legacy rows keep NULL = "quantity not recorded".
-- =============================================================================
CALL sp_mig_add_column('ASSIGNMENT', 'quantity_allocated', 'INT UNSIGNED NULL COMMENT ''Units of the resource taken from stock by this assignment''');
CALL sp_mig_add_column('ASSIGNMENT', 'people_housed',      'INT UNSIGNED NULL COMMENT ''People placed in the shelter by this assignment''');

CALL sp_mig_add_constraint('ASSIGNMENT', 'chk_assign_qty_positive',
    'CHECK (quantity_allocated IS NULL OR (quantity_allocated > 0 AND resource_id IS NOT NULL))');
CALL sp_mig_add_constraint('ASSIGNMENT', 'chk_assign_people_positive',
    'CHECK (people_housed IS NULL OR (people_housed > 0 AND shelter_id IS NOT NULL))');

-- Backfill quantity_allocated from the existing OUT inventory transactions.
-- Only rows that have real evidence are filled; everything else stays NULL.
UPDATE ASSIGNMENT a
JOIN (
    SELECT assignment_id, SUM(quantity) AS qty
    FROM INVENTORY_TRANSACTION
    WHERE transaction_type = 'OUT' AND assignment_id IS NOT NULL
    GROUP BY assignment_id
) t ON t.assignment_id = a.assignment_id
SET a.quantity_allocated = t.qty
WHERE a.quantity_allocated IS NULL
  AND a.resource_id IS NOT NULL;

-- =============================================================================
-- 2. INCIDENT: assigned coordinator
-- =============================================================================
CALL sp_mig_add_column('INCIDENT', 'coordinator_id', 'INT UNSIGNED NULL COMMENT ''Coordinator responsible for this incident''');
CALL sp_mig_add_constraint('INCIDENT', 'fk_incident_coordinator',
    'FOREIGN KEY (coordinator_id) REFERENCES `USER`(user_id) ON DELETE SET NULL ON UPDATE CASCADE');
CALL sp_mig_add_index('INCIDENT', 'idx_incident_coordinator', 'coordinator_id');

-- =============================================================================
-- 3. LOCATION: parent-child hierarchy (Country > State > District > Area)
--    (self-referencing FK; cycles are blocked by a trigger in 08)
-- =============================================================================
CALL sp_mig_add_column('LOCATION', 'parent_location_id', 'INT UNSIGNED NULL COMMENT ''Parent region (NULL = top level)''');
CALL sp_mig_add_constraint('LOCATION', 'fk_location_parent',
    'FOREIGN KEY (parent_location_id) REFERENCES LOCATION(location_id) ON DELETE SET NULL ON UPDATE CASCADE');
CALL sp_mig_add_index('LOCATION', 'idx_location_parent', 'parent_location_id');

-- =============================================================================
-- 4. New tables
-- =============================================================================
CREATE TABLE IF NOT EXISTS INCIDENT_STATUS_AUDIT (
    audit_id           INT UNSIGNED AUTO_INCREMENT,
    incident_id        INT UNSIGNED NOT NULL,
    old_status         ENUM('ACTIVE','RESOLVED','MONITORING') NOT NULL,
    new_status         ENUM('ACTIVE','RESOLVED','MONITORING') NOT NULL,
    changed_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by_user_id INT UNSIGNED NULL COMMENT 'Application user (from session variable @app_user_id), if supplied',
    db_account         VARCHAR(100) NOT NULL COMMENT 'MySQL account that executed the change',
    CONSTRAINT pk_incident_status_audit PRIMARY KEY (audit_id),
    CONSTRAINT fk_isa_incident FOREIGN KEY (incident_id)
        REFERENCES INCIDENT(incident_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_isa_user FOREIGN KEY (changed_by_user_id)
        REFERENCES `USER`(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_isa_changed CHECK (old_status <> new_status),
    INDEX idx_isa_incident (incident_id, changed_at)
) ENGINE=InnoDB COMMENT='Audit trail of incident status changes (filled by trigger)';

CREATE TABLE IF NOT EXISTS NOTIFICATION (
    notification_id INT UNSIGNED AUTO_INCREMENT,
    user_id         INT UNSIGNED NOT NULL,
    request_id      INT UNSIGNED NULL,
    notif_type      ENUM('REQUEST_UPDATE','ASSIGNMENT','ANNOUNCEMENT') NOT NULL DEFAULT 'REQUEST_UPDATE',
    title           VARCHAR(200) NOT NULL,
    message         VARCHAR(500) NOT NULL,
    is_read         TINYINT(1)   NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_notification PRIMARY KEY (notification_id),
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id)
        REFERENCES `USER`(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notif_request FOREIGN KEY (request_id)
        REFERENCES EMERGENCY_REQUEST(request_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_notif_user_unread (user_id, is_read, created_at)
) ENGINE=InnoDB COMMENT='Per-user notifications (filled by trigger)';

-- helpers are not needed after the migration
DROP PROCEDURE IF EXISTS sp_mig_add_column;
DROP PROCEDURE IF EXISTS sp_mig_add_constraint;
DROP PROCEDURE IF EXISTS sp_mig_add_index;

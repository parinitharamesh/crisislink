-- =============================================================================
-- CrisisLink – Disaster Response Coordination System
-- FILE: 05_indexes_security.sql  (Phase 3 – Query Optimization + Security)
-- PURPOSE: Indexes, query optimization, MySQL users, GRANT/REVOKE
-- UNIT COVERAGE: Unit 3 (query optimization, indexes), Unit 4 (security)
-- =============================================================================

USE crisislink_db;

-- =============================================================================
-- INDEXES for Query Optimization (Unit 3 – Query Optimization)
-- =============================================================================

-- Index on EMERGENCY_REQUEST for common query patterns
CREATE INDEX idx_req_status        ON EMERGENCY_REQUEST (status);
CREATE INDEX idx_req_priority      ON EMERGENCY_REQUEST (priority);
CREATE INDEX idx_req_user          ON EMERGENCY_REQUEST (user_id);
CREATE INDEX idx_req_incident      ON EMERGENCY_REQUEST (incident_id);
CREATE INDEX idx_req_location      ON EMERGENCY_REQUEST (location_id);
CREATE INDEX idx_req_time          ON EMERGENCY_REQUEST (request_time);
-- Composite index for coordinator dashboard query (status + priority)
CREATE INDEX idx_req_status_priority ON EMERGENCY_REQUEST (status, priority, request_time);

-- Index on ASSIGNMENT
CREATE INDEX idx_assign_request    ON ASSIGNMENT (request_id);
CREATE INDEX idx_assign_resource   ON ASSIGNMENT (resource_id);
CREATE INDEX idx_assign_shelter    ON ASSIGNMENT (shelter_id);
CREATE INDEX idx_assign_status     ON ASSIGNMENT (status);

-- Index on RESOURCE for availability queries
CREATE INDEX idx_resource_status   ON RESOURCE (status);
CREATE INDEX idx_resource_type     ON RESOURCE (type_id);
CREATE INDEX idx_resource_org      ON RESOURCE (org_id);
CREATE INDEX idx_resource_location ON RESOURCE (location_id);

-- Index on SHELTER
CREATE INDEX idx_shelter_status    ON SHELTER (status);
CREATE INDEX idx_shelter_location  ON SHELTER (location_id);

-- Index on INCIDENT
CREATE INDEX idx_incident_status   ON INCIDENT (status);
CREATE INDEX idx_incident_type     ON INCIDENT (incident_type);
CREATE INDEX idx_incident_location ON INCIDENT (location_id);

-- Index on USER for login queries
CREATE INDEX idx_user_email_role   ON `USER` (email, role);
CREATE INDEX idx_user_org          ON `USER` (org_id);

-- Index on INVENTORY_TRANSACTION
CREATE INDEX idx_invt_resource     ON INVENTORY_TRANSACTION (resource_id);
CREATE INDEX idx_invt_time         ON INVENTORY_TRANSACTION (transaction_time);

-- =============================================================================
-- DATABASE SECURITY: MySQL Users and Roles (Unit 1 + Unit 4)
-- =============================================================================

-- Drop users if they exist (safe re-run)
DROP USER IF EXISTS 'crisislink_app'@'%';
DROP USER IF EXISTS 'crisislink_readonly'@'%';
DROP USER IF EXISTS 'crisislink_coordinator'@'%';

-- APPLICATION USER: Full DML access (SELECT, INSERT, UPDATE, DELETE)
--                   No DDL – cannot DROP or ALTER tables
CREATE USER 'crisislink_app'@'%' IDENTIFIED BY 'app_secure_pwd_2024';
GRANT SELECT, INSERT, UPDATE, DELETE ON crisislink_db.* TO 'crisislink_app'@'%';
-- Allow calling stored procedures
GRANT EXECUTE ON crisislink_db.* TO 'crisislink_app'@'%';

-- READ-ONLY USER: For reporting and analytics queries
CREATE USER 'crisislink_readonly'@'%' IDENTIFIED BY 'readonly_secure_pwd_2024';
GRANT SELECT ON crisislink_db.* TO 'crisislink_readonly'@'%';

-- COORDINATOR USER: Can SELECT all and UPDATE request status only
CREATE USER 'crisislink_coordinator'@'%' IDENTIFIED BY 'coordinator_secure_pwd_2024';
GRANT SELECT ON crisislink_db.*                                TO 'crisislink_coordinator'@'%';
GRANT INSERT, UPDATE ON crisislink_db.ASSIGNMENT              TO 'crisislink_coordinator'@'%';
GRANT UPDATE (status, resolved_time) ON crisislink_db.EMERGENCY_REQUEST TO 'crisislink_coordinator'@'%';
GRANT EXECUTE ON crisislink_db.*                              TO 'crisislink_coordinator'@'%';

-- Demonstrate REVOKE (Unit 1 – database security demonstration)
-- REVOKE DELETE ON crisislink_db.* FROM 'crisislink_coordinator'@'%';  -- already not granted
-- (This line shows how REVOKE works conceptually)

FLUSH PRIVILEGES;

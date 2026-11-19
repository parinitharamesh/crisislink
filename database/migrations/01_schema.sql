-- =============================================================================
-- CrisisLink – Disaster Response Coordination System
-- FILE: 01_schema.sql  (Phase 2 – MySQL Schema)
-- PURPOSE: DDL for all 11 core tables with constraints, keys, and indexes
-- UNIT COVERAGE: Unit 1 (DDL, keys, constraints) + Unit 3 (normalization, FDs)
-- =============================================================================

-- Use the database
USE crisislink_db;

-- Ensure clean state (for re-runs in dev)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS INVENTORY_TRANSACTION;
DROP TABLE IF EXISTS ASSIGNMENT;
DROP TABLE IF EXISTS REQUEST_RESOURCE_TYPE;
DROP TABLE IF EXISTS EMERGENCY_REQUEST;
DROP TABLE IF EXISTS SHELTER;
DROP TABLE IF EXISTS RESOURCE;
DROP TABLE IF EXISTS RESOURCE_TYPE;
DROP TABLE IF EXISTS INCIDENT;
DROP TABLE IF EXISTS `USER`;
DROP TABLE IF EXISTS LOCATION;
DROP TABLE IF EXISTS ORGANIZATION;
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- TABLE 1: ORGANIZATION
-- Stores rescue/relief organizations
-- Normal form: BCNF – org_id → {org_name, type, contact_no, address}
-- No partial or transitive dependencies
-- =============================================================================
CREATE TABLE ORGANIZATION (
    org_id      INT UNSIGNED AUTO_INCREMENT,
    org_name    VARCHAR(150)  NOT NULL,
    org_type    ENUM('NGO','GOVERNMENT','MILITARY','MEDICAL','PRIVATE','OTHER')
                              NOT NULL DEFAULT 'NGO',
    contact_no  VARCHAR(20)   NOT NULL,
    address     VARCHAR(300)  NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_organization PRIMARY KEY (org_id),
    CONSTRAINT uq_org_name     UNIQUE (org_name)
) ENGINE=InnoDB COMMENT='Organizations providing disaster response resources';

-- =============================================================================
-- TABLE 2: LOCATION
-- Geographic locations; used by resources, shelters, incidents, and requests
-- Normal form: BCNF – location_id → {area_name, latitude, longitude}
-- =============================================================================
CREATE TABLE LOCATION (
    location_id INT UNSIGNED AUTO_INCREMENT,
    area_name   VARCHAR(200)   NOT NULL,
    district    VARCHAR(100)   NOT NULL DEFAULT 'Unknown',
    state       VARCHAR(100)   NOT NULL DEFAULT 'Unknown',
    latitude    DECIMAL(9, 6)  NULL,
    longitude   DECIMAL(9, 6)  NULL,
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_location PRIMARY KEY (location_id),
    CONSTRAINT chk_latitude  CHECK (latitude  IS NULL OR latitude  BETWEEN -90  AND 90),
    CONSTRAINT chk_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
) ENGINE=InnoDB COMMENT='Geographic locations referenced across the system';

-- =============================================================================
-- TABLE 3: RESOURCE_TYPE
-- Lookup table for resource categories (Food, Water, Medical, etc.)
-- Normal form: BCNF – type_id → {name, description}
-- =============================================================================
CREATE TABLE RESOURCE_TYPE (
    type_id     INT UNSIGNED AUTO_INCREMENT,
    type_name   VARCHAR(100) NOT NULL,
    description TEXT         NULL,
    CONSTRAINT pk_resource_type PRIMARY KEY (type_id),
    CONSTRAINT uq_type_name     UNIQUE (type_name)
) ENGINE=InnoDB COMMENT='Lookup table for resource categories';

-- =============================================================================
-- TABLE 4: USER
-- Citizens, coordinators, admins – role-based access
-- Normal form: BCNF – user_id → {name, email, …}; email UNIQUE ensures no anomaly
-- FK: org_id → ORGANIZATION (nullable – citizens may not belong to an org)
-- =============================================================================
CREATE TABLE `USER` (
    user_id       INT UNSIGNED AUTO_INCREMENT,
    full_name     VARCHAR(150) NOT NULL,
    email         VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone         VARCHAR(20)  NULL,
    role          ENUM('CITIZEN','COORDINATOR','ADMIN') NOT NULL DEFAULT 'CITIZEN',
    org_id        INT UNSIGNED NULL,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_user    PRIMARY KEY (user_id),
    CONSTRAINT uq_email   UNIQUE (email),
    CONSTRAINT fk_user_org FOREIGN KEY (org_id)
        REFERENCES ORGANIZATION(org_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='System users: citizens, coordinators and admins';

-- =============================================================================
-- TABLE 5: INCIDENT
-- A disaster event (flood, fire, earthquake, etc.) at a location
-- Normal form: BCNF – incident_id → {incident_type, dates, description, location_id}
-- =============================================================================
CREATE TABLE INCIDENT (
    incident_id   INT UNSIGNED AUTO_INCREMENT,
    incident_type ENUM('FLOOD','FIRE','EARTHQUAKE','CYCLONE','LANDSLIDE',
                       'DROUGHT','TSUNAMI','INDUSTRIAL','OTHER') NOT NULL,
    title         VARCHAR(200) NOT NULL,
    start_date    DATE         NOT NULL,
    end_date      DATE         NULL,
    description   TEXT         NULL,
    affected_area VARCHAR(300) NULL,
    severity      ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    status        ENUM('ACTIVE','RESOLVED','MONITORING') NOT NULL DEFAULT 'ACTIVE',
    location_id   INT UNSIGNED NOT NULL,
    reported_by   INT UNSIGNED NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_incident PRIMARY KEY (incident_id),
    CONSTRAINT fk_incident_location FOREIGN KEY (location_id)
        REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_incident_reporter FOREIGN KEY (reported_by)
        REFERENCES `USER`(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_incident_dates CHECK (end_date IS NULL OR end_date >= start_date)
) ENGINE=InnoDB COMMENT='Disaster incidents linked to locations';

-- =============================================================================
-- TABLE 6: RESOURCE
-- Physical resources (boats, food kits, ambulances, etc.) owned by organizations
-- Normal form: BCNF – resource_id → {resource_name, type_id, capacity, org_id, location_id}
-- =============================================================================
CREATE TABLE RESOURCE (
    resource_id   INT UNSIGNED AUTO_INCREMENT,
    resource_name VARCHAR(200)  NOT NULL,
    type_id       INT UNSIGNED  NOT NULL,
    quantity      INT UNSIGNED  NOT NULL DEFAULT 1,
    unit          VARCHAR(50)   NOT NULL DEFAULT 'units',
    status        ENUM('AVAILABLE','DEPLOYED','MAINTENANCE','EXHAUSTED')
                                NOT NULL DEFAULT 'AVAILABLE',
    location_id   INT UNSIGNED  NOT NULL,
    org_id        INT UNSIGNED  NOT NULL,
    description   TEXT          NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_resource          PRIMARY KEY (resource_id),
    CONSTRAINT fk_resource_type     FOREIGN KEY (type_id)
        REFERENCES RESOURCE_TYPE(type_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_resource_location FOREIGN KEY (location_id)
        REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_resource_org      FOREIGN KEY (org_id)
        REFERENCES ORGANIZATION(org_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_resource_quantity CHECK (quantity >= 0)
) ENGINE=InnoDB COMMENT='Physical resources managed by organizations';

-- =============================================================================
-- TABLE 7: SHELTER
-- Emergency shelters with capacity and medical facility info
-- Normal form: BCNF – shelter_id → {name, address, capacities, location_id, org_id}
-- =============================================================================
CREATE TABLE SHELTER (
    shelter_id           INT UNSIGNED AUTO_INCREMENT,
    shelter_name         VARCHAR(200) NOT NULL,
    address              VARCHAR(300) NOT NULL,
    capacity             INT UNSIGNED NOT NULL,
    current_occupancy    INT UNSIGNED NOT NULL DEFAULT 0,
    has_medical_facility TINYINT(1)   NOT NULL DEFAULT 0,
    status               ENUM('OPEN','FULL','CLOSED') NOT NULL DEFAULT 'OPEN',
    location_id          INT UNSIGNED NOT NULL,
    org_id               INT UNSIGNED NOT NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                      ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_shelter           PRIMARY KEY (shelter_id),
    CONSTRAINT fk_shelter_location  FOREIGN KEY (location_id)
        REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_shelter_org       FOREIGN KEY (org_id)
        REFERENCES ORGANIZATION(org_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_capacity_positive     CHECK (capacity > 0),
    CONSTRAINT chk_occupancy_non_neg     CHECK (current_occupancy >= 0),
    CONSTRAINT chk_occupancy_not_exceed  CHECK (current_occupancy <= capacity)
) ENGINE=InnoDB COMMENT='Emergency shelters with capacity management';

-- =============================================================================
-- TABLE 8: EMERGENCY_REQUEST
-- Requests submitted by citizens during a disaster
-- Normal form: BCNF
--   request_id → {request_type, description, people_count, medical_needed,
--                 priority, status, user_id, incident_id, location_id}
-- =============================================================================
CREATE TABLE EMERGENCY_REQUEST (
    request_id    INT UNSIGNED AUTO_INCREMENT,
    request_type  ENUM('RESCUE','MEDICAL','SHELTER','FOOD','WATER',
                       'EVACUATION','OTHER') NOT NULL,
    description   TEXT         NOT NULL,
    people_count  INT UNSIGNED NOT NULL DEFAULT 1,
    medical_needed TINYINT(1)  NOT NULL DEFAULT 0,
    priority      ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    status        ENUM('PENDING','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED')
                               NOT NULL DEFAULT 'PENDING',
    request_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_time DATETIME     NULL,
    user_id       INT UNSIGNED NOT NULL,
    incident_id   INT UNSIGNED NULL,
    location_id   INT UNSIGNED NOT NULL,
    CONSTRAINT pk_emergency_request   PRIMARY KEY (request_id),
    CONSTRAINT fk_request_user        FOREIGN KEY (user_id)
        REFERENCES `USER`(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_request_incident    FOREIGN KEY (incident_id)
        REFERENCES INCIDENT(incident_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_request_location    FOREIGN KEY (location_id)
        REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_people_count       CHECK (people_count >= 1),
    CONSTRAINT chk_resolved_after_req CHECK (
        resolved_time IS NULL OR resolved_time >= request_time
    )
) ENGINE=InnoDB COMMENT='Emergency requests submitted by citizens';

-- =============================================================================
-- TABLE 9: REQUEST_RESOURCE_TYPE
-- M:N junction table – an emergency request can need multiple resource types
-- COMPOSITE PRIMARY KEY: (request_id, type_id)
-- Normal form: BCNF – (request_id, type_id) → quantity_required
-- =============================================================================
CREATE TABLE REQUEST_RESOURCE_TYPE (
    request_id        INT UNSIGNED NOT NULL,
    type_id           INT UNSIGNED NOT NULL,
    quantity_required INT UNSIGNED NOT NULL DEFAULT 1,
    CONSTRAINT pk_rrt   PRIMARY KEY (request_id, type_id),  -- Composite PK
    CONSTRAINT fk_rrt_request FOREIGN KEY (request_id)
        REFERENCES EMERGENCY_REQUEST(request_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rrt_type    FOREIGN KEY (type_id)
        REFERENCES RESOURCE_TYPE(type_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_rrt_qty    CHECK (quantity_required >= 1)
) ENGINE=InnoDB COMMENT='M:N between emergency requests and resource types needed';

-- =============================================================================
-- TABLE 10: ASSIGNMENT
-- Links a request to a resource and/or shelter
-- CONSTRAINT: at least one of resource_id or shelter_id must be present
-- Normal form: BCNF – assignment_id → {request_id, resource_id, shelter_id, status}
-- =============================================================================
CREATE TABLE ASSIGNMENT (
    assignment_id INT UNSIGNED AUTO_INCREMENT,
    assigned_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status        ENUM('PENDING','ACTIVE','COMPLETED','CANCELLED')
                               NOT NULL DEFAULT 'PENDING',
    remarks       TEXT         NULL,
    request_id    INT UNSIGNED NOT NULL,
    resource_id   INT UNSIGNED NULL,
    shelter_id    INT UNSIGNED NULL,
    assigned_by   INT UNSIGNED NULL,
    CONSTRAINT pk_assignment        PRIMARY KEY (assignment_id),
    CONSTRAINT fk_assignment_request  FOREIGN KEY (request_id)
        REFERENCES EMERGENCY_REQUEST(request_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_assignment_resource FOREIGN KEY (resource_id)
        REFERENCES RESOURCE(resource_id),
    CONSTRAINT fk_assignment_shelter  FOREIGN KEY (shelter_id)
        REFERENCES SHELTER(shelter_id),
    CONSTRAINT fk_assignment_by       FOREIGN KEY (assigned_by)
        REFERENCES `USER`(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    -- Business constraint: at least one of resource_id or shelter_id must be set
    CONSTRAINT chk_assignment_target  CHECK (
        resource_id IS NOT NULL OR shelter_id IS NOT NULL
    )
) ENGINE=InnoDB COMMENT='Assignments linking requests to resources and/or shelters';

-- =============================================================================
-- TABLE 11: INVENTORY_TRANSACTION
-- Tracks resource IN/OUT/TRANSFER operations for audit trail
-- Normal form: BCNF – transaction_id → {quantity, type, time, resource_id, assignment_id}
-- =============================================================================
CREATE TABLE INVENTORY_TRANSACTION (
    transaction_id   INT UNSIGNED AUTO_INCREMENT,
    quantity         INT UNSIGNED NOT NULL,
    transaction_type ENUM('IN','OUT','TRANSFER','ADJUSTMENT') NOT NULL,
    notes            TEXT         NULL,
    transaction_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resource_id      INT UNSIGNED NOT NULL,
    assignment_id    INT UNSIGNED NULL,
    performed_by     INT UNSIGNED NULL,
    CONSTRAINT pk_inventory_transaction  PRIMARY KEY (transaction_id),
    CONSTRAINT fk_invt_resource          FOREIGN KEY (resource_id)
        REFERENCES RESOURCE(resource_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_invt_assignment        FOREIGN KEY (assignment_id)
        REFERENCES ASSIGNMENT(assignment_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_invt_user              FOREIGN KEY (performed_by)
        REFERENCES `USER`(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_invt_quantity         CHECK (quantity > 0)
) ENGINE=InnoDB COMMENT='Audit trail for resource inventory changes';

-- =============================================================================
-- FULL-TEXT SEARCH indexes (Unit 2 – Full-text search functions)
-- =============================================================================
ALTER TABLE EMERGENCY_REQUEST ADD FULLTEXT INDEX ft_request_description (description);
ALTER TABLE INCIDENT          ADD FULLTEXT INDEX ft_incident_description (description, title);
ALTER TABLE RESOURCE          ADD FULLTEXT INDEX ft_resource_name (resource_name, description);

-- =============================================================================
-- End of schema
-- =============================================================================

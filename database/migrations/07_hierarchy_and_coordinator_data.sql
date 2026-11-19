-- =============================================================================
-- CrisisLink - FILE: 07_hierarchy_and_coordinator_data.sql
-- PURPOSE : Fill the new columns with meaningful data. RE-RUNNABLE
--           (every statement only inserts / updates rows that are still missing).
-- DOES NOT delete or change any existing LOCATION / INCIDENT row except to
-- fill the NEW columns parent_location_id and coordinator_id.
--
-- Location hierarchy built from the data already in LOCATION:
--     India (country)
--       +-- <State>            (7 states)
--             +-- <District>   (8 districts)
--                   +-- <Area> (the 8 ORIGINAL rows, now children of their district)
--
-- Marker convention for the NEW parent nodes (no extra column needed):
--     country node : district = '(country)'
--     state node   : district = '(state)'
--     district node: area_name = district  (e.g. 'Ernakulam' / 'Ernakulam')
-- =============================================================================

USE crisislink_db;

-- 1. Country root --------------------------------------------------------------
INSERT INTO LOCATION (area_name, district, state, latitude, longitude)
SELECT 'India', '(country)', '(country)', 22.3511, 78.6677
WHERE NOT EXISTS (SELECT 1 FROM LOCATION WHERE area_name = 'India' AND district = '(country)');

-- 2. State nodes (one per distinct state among the original area rows) ---------
INSERT INTO LOCATION (area_name, district, state, latitude, longitude)
SELECT s.state, '(state)', s.state, NULL, NULL
FROM (SELECT DISTINCT state FROM LOCATION
      WHERE district NOT IN ('(country)', '(state)') AND area_name <> district) s
WHERE NOT EXISTS (SELECT 1 FROM LOCATION x WHERE x.area_name = s.state AND x.district = '(state)');

-- 3. District nodes (one per distinct district among the original area rows) ---
INSERT INTO LOCATION (area_name, district, state, latitude, longitude)
SELECT d.district, d.district, d.state, NULL, NULL
FROM (SELECT DISTINCT district, state FROM LOCATION
      WHERE district NOT IN ('(country)', '(state)') AND area_name <> district) d
WHERE NOT EXISTS (SELECT 1 FROM LOCATION x
                  WHERE x.area_name = d.district AND x.district = d.district AND x.state = d.state);

-- 4. Link the levels together (only where parent is still NULL) ----------------
-- state -> country
UPDATE LOCATION st
JOIN LOCATION c ON c.area_name = 'India' AND c.district = '(country)'
SET st.parent_location_id = c.location_id
WHERE st.district = '(state)' AND st.parent_location_id IS NULL;

-- district -> state
UPDATE LOCATION d
JOIN LOCATION st ON st.district = '(state)' AND st.area_name = d.state
SET d.parent_location_id = st.location_id
WHERE d.area_name = d.district AND d.district NOT IN ('(country)', '(state)')
  AND d.parent_location_id IS NULL;

-- original area -> district
UPDATE LOCATION a
JOIN LOCATION d ON d.area_name = d.district AND d.district = a.district AND d.state = a.state
SET a.parent_location_id = d.location_id
WHERE a.area_name <> a.district AND a.district NOT IN ('(country)', '(state)')
  AND a.parent_location_id IS NULL;

-- 5. Incident coordinators ------------------------------------------------------
-- The person who reported each incident is already a coordinator/admin in the
-- seed data, so use that real relationship instead of inventing one.
UPDATE INCIDENT i
JOIN `USER` u ON u.user_id = i.reported_by AND u.role IN ('COORDINATOR', 'ADMIN')
SET i.coordinator_id = u.user_id
WHERE i.coordinator_id IS NULL;

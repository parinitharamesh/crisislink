-- =============================================================================
-- CrisisLink – Disaster Response Coordination System
-- FILE: 02_sample_data.sql  (Phase 2 – Seed Data)
-- PURPOSE: Realistic sample data for all 11 tables
-- =============================================================================

USE crisislink_db;

-- ─── ORGANIZATION ────────────────────────────────────────────────────────────
INSERT INTO ORGANIZATION (org_name, org_type, contact_no, address) VALUES
('National Disaster Response Force', 'GOVERNMENT', '+91-11-26701700', 'NDRF HQ, New Delhi'),
('Red Cross India Chapter',          'NGO',        '+91-11-23716441', 'Red Cross Road, New Delhi'),
('Army Medical Corps',               'MILITARY',   '+91-020-26063111', 'Pune Cantonment, Maharashtra'),
('Kerala Rescue Foundation',         'NGO',        '+91-471-2721400', 'Thiruvananthapuram, Kerala'),
('Apollo Emergency Response',        'MEDICAL',    '+91-40-23607777', 'Hyderabad, Telangana'),
('Odisha State Disaster Management', 'GOVERNMENT', '+91-674-2534929', 'Bhubaneswar, Odisha');

-- ─── LOCATION ────────────────────────────────────────────────────────────────
INSERT INTO LOCATION (area_name, district, state, latitude, longitude) VALUES
('Ernakulam North',     'Ernakulam',   'Kerala',       9.9816,  76.2999),
('Thiruvananthapuram Central', 'Thiruvananthapuram', 'Kerala', 8.5241, 76.9366),
('Puri Coastal Zone',   'Puri',        'Odisha',       19.8135, 85.8312),
('Brahmaputra Floodplain', 'Kamrup',   'Assam',        26.1445, 91.7362),
('Dehradun Valley',     'Dehradun',    'Uttarakhand',  30.3165, 78.0322),
('Visakhapatnam Port',  'Visakhapatnam','Andhra Pradesh',17.6868, 83.2185),
('Chennai Central',     'Chennai',     'Tamil Nadu',   13.0827, 80.2707),
('Mumbai Coastal',      'Mumbai',      'Maharashtra',  19.0760, 72.8777);

-- ─── RESOURCE_TYPE ───────────────────────────────────────────────────────────
INSERT INTO RESOURCE_TYPE (type_name, description) VALUES
('Food Rations',        'Ready-to-eat food packages for disaster victims'),
('Drinking Water',      'Purified water in bottles or tanker trucks'),
('Medical Supplies',    'First aid kits, medicines, and surgical equipment'),
('Rescue Boats',        'Inflatable and motorized boats for flood rescue'),
('Ambulances',          'Emergency medical transport vehicles'),
('Tents and Shelter',   'Temporary shelter materials and tents'),
('Communication Equipment', 'Radios, satellite phones, and repeaters'),
('Heavy Machinery',     'Cranes, excavators for debris removal'),
('Blankets and Clothing', 'Warm clothing and blankets for victims'),
('Generators',          'Portable power generators for emergency use');

-- ─── USER (passwords are bcrypt hashes of "Password123!") ───────────────────
-- Hash generated: $2b$12$...  (bcrypt, 12 rounds)
INSERT INTO `USER` (full_name, email, password_hash, phone, role, org_id) VALUES
('Admin User',           'admin@crisislink.in',       '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543210', 'ADMIN',       1),
('Coordinator Ravi',     'ravi.coordinator@ndrf.in',  '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543211', 'COORDINATOR', 1),
('Coordinator Priya',    'priya.coord@redcross.in',   '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543212', 'COORDINATOR', 2),
('Citizen Arun Kumar',   'arun.kumar@gmail.com',      '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543213', 'CITIZEN',     NULL),
('Citizen Meena Raj',    'meena.raj@gmail.com',       '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543214', 'CITIZEN',     NULL),
('Citizen Suresh Pillai','suresh.pillai@yahoo.com',   '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543215', 'CITIZEN',     NULL),
('Coordinator Anjali',   'anjali.ops@army.in',        '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543216', 'COORDINATOR', 3),
('Citizen Deepak Nair',  'deepak.nair@hotmail.com',   '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543217', 'CITIZEN',     NULL),
('Citizen Lakshmi Devi', 'lakshmi.d@gmail.com',       '$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543218', 'CITIZEN',     NULL),
('Coordinator Sanjay',   'sanjay.coord@kerala.gov.in','$2b$12$k/fyOdjWRuTY1hohZJ2zc.PjqwBE3z.h7hxv8ExpVnZ9bwBjMuPJC', '+91-9876543219', 'COORDINATOR', 4);

-- ─── INCIDENT ────────────────────────────────────────────────────────────────
INSERT INTO INCIDENT (incident_type, title, start_date, end_date, description, affected_area, severity, status, location_id, reported_by) VALUES
('FLOOD',       'Kerala Monsoon Flood 2024',      '2024-08-01', NULL,         'Severe flooding across Ernakulam district due to heavy monsoon rains. Multiple low-lying areas submerged.', 'Ernakulam district, northern Kerala', 'CRITICAL', 'ACTIVE',     1, 2),
('CYCLONE',     'Cyclone Biparjoy Aftermath',     '2024-06-15', '2024-06-25', 'Post-cyclone rescue operations along the Odisha coast after Biparjoy made landfall.', 'Puri coastal belt', 'HIGH', 'RESOLVED',  3, 2),
('FLOOD',       'Assam Brahmaputra Overflow 2024','2024-07-10', NULL,         'Annual Brahmaputra river flood affecting lakhs of people in Kamrup district.', 'Kamrup and Morigaon districts', 'HIGH', 'ACTIVE',     4, 7),
('LANDSLIDE',   'Dehradun Landslide Event',       '2024-08-05', '2024-08-15', 'Heavy rainfall triggered multiple landslides blocking major roads.', 'Mussoorie road and Chakrata belt', 'HIGH', 'RESOLVED',  5, 7),
('INDUSTRIAL',  'Visakhapatnam Chemical Leak',    '2024-05-20', '2024-05-22', 'Toxic gas leak from industrial plant requiring immediate evacuation.', 'GVMC zone 6', 'CRITICAL', 'RESOLVED',  6, 3),
('FLOOD',       'Chennai Heavy Rain 2024',        '2024-11-01', NULL,         'Unprecedented heavy rainfall causing urban flooding in Chennai.', 'Chennai metro area', 'HIGH', 'ACTIVE',     7, 3);

-- ─── RESOURCE ────────────────────────────────────────────────────────────────
INSERT INTO RESOURCE (resource_name, type_id, quantity, unit, status, location_id, org_id, description) VALUES
('Emergency Food Ration Pack A',    1, 500, 'packs',   'AVAILABLE', 1, 2, 'Each pack contains 3-day supply for one person'),
('Water Tanker – KL-01',            2, 10,  'tankers',  'AVAILABLE', 1, 4, '5000L capacity water tankers for flood zones'),
('First Aid Mega Kit',              3, 100, 'kits',     'AVAILABLE', 1, 5, 'Advanced first aid with surgical supplies'),
('NDRF Rescue Boat RB-07',          4, 5,   'boats',    'DEPLOYED',  1, 1, 'High-capacity rescue boat for flood operations'),
('Apollo Ambulance Unit-03',        5, 3,   'vehicles', 'AVAILABLE', 2, 5, 'ICU-equipped ambulances'),
('Tarpaulin Shelter Kit',           6, 200, 'kits',     'AVAILABLE', 3, 2, 'Emergency tarpaulin + poles for 10 people'),
('Satellite Phone Set',             7, 20,  'devices',  'AVAILABLE', 4, 1, 'Iridium satellite phones for communication'),
('Food Ration Pack B (Veg)',        1, 300, 'packs',    'AVAILABLE', 3, 2, 'Vegetarian emergency food packs'),
('Water Purification Unit',         2, 5,   'units',    'AVAILABLE', 3, 1, 'Portable water purification systems'),
('Army Medical Kit – Tier 2',       3, 80,  'kits',     'AVAILABLE', 4, 3, 'Military-grade trauma medical kits'),
('NDRF Rescue Boat RB-12',          4, 3,   'boats',    'AVAILABLE', 4, 1, 'Inflatable rescue boats for river floods'),
('Blanket Pack',                    9, 1000,'blankets',  'AVAILABLE', 1, 2, 'Thermal blankets for flood victims'),
('Diesel Generator 5kVA',           10,10,  'units',    'AVAILABLE', 2, 4, 'Portable generators for relief camps'),
('Heavy Excavator JCB-01',          8, 2,   'machines', 'AVAILABLE', 5, 1, 'For debris clearance after landslides'),
('Ambulance Unit Vizag-01',         5, 4,   'vehicles', 'AVAILABLE', 6, 5, 'Emergency ambulances for Visakhapatnam');

-- ─── SHELTER ─────────────────────────────────────────────────────────────────
INSERT INTO SHELTER (shelter_name, address, capacity, current_occupancy, has_medical_facility, status, location_id, org_id) VALUES
('Government HSS Flood Relief Camp', 'Near Aluva Town, Ernakulam', 500, 320, 1, 'OPEN',   1, 4),
('Red Cross Community Hall',         'Marine Drive, Kochi',        200, 195, 0, 'OPEN',   1, 2),
('St. Joseph College Camp',          'Devagiri, Kozhikode',        300, 0,   1, 'OPEN',   2, 2),
('Puri Cyclone Relief Camp',         'Puri Beach Road, Puri',      400, 0,   1, 'CLOSED', 3, 6),
('Brahmaputra Flood Shelter A',      'Guwahati Relief Zone 1',     600, 450, 1, 'OPEN',   4, 1),
('Brahmaputra Flood Shelter B',      'Guwahati Relief Zone 2',     400, 380, 0, 'OPEN',   4, 6),
('Dehradun Emergency Camp',          'ONGC Campus, Dehradun',      250, 0,   0, 'CLOSED', 5, 1),
('Chennai Flood Relief Centre',      'Anna University Campus',     800, 120, 1, 'OPEN',   7, 2);

-- ─── EMERGENCY_REQUEST ───────────────────────────────────────────────────────
INSERT INTO EMERGENCY_REQUEST (request_type, description, people_count, medical_needed, priority, status, request_time, user_id, incident_id, location_id) VALUES
('RESCUE',    'Family of 6 stranded on rooftop, water rising. Need rescue boat urgently.', 6,  1, 'CRITICAL', 'ASSIGNED',     '2024-08-02 09:15:00', 4, 1, 1),
('SHELTER',   'Lost home to flooding. 4 elderly members need shelter with medical care.',   4,  1, 'HIGH',     'RESOLVED',     '2024-08-02 10:30:00', 5, 1, 1),
('FOOD',      'Stranded in building with no food for 2 days. 15 people.',                 15, 0, 'HIGH',     'IN_PROGRESS',  '2024-08-02 11:00:00', 6, 1, 1),
('MEDICAL',   'Diabetic patient needs insulin injection. No medical help available.',      1,  1, 'CRITICAL', 'RESOLVED',     '2024-08-03 07:00:00', 4, 1, 1),
('EVACUATION','10 people need evacuation from Brahmaputra flood zone.',                   10, 0, 'HIGH',     'ASSIGNED',     '2024-07-12 14:00:00', 8, 3, 4),
('FOOD',      'Flood camp residents need drinking water. Supply exhausted.',               50, 0, 'HIGH',     'RESOLVED',     '2024-07-13 08:00:00', 9, 3, 4),
('RESCUE',    'Landslide debris blocking road. 3 vehicles and 12 people trapped.',        12, 1, 'CRITICAL', 'RESOLVED',     '2024-08-06 06:30:00', 8, 4, 5),
('SHELTER',   'Need temporary shelter for 20 people displaced by flooding.',              20, 0, 'MEDIUM',   'PENDING',      '2024-08-04 15:00:00', 9, 1, 1),
('WATER',     'No clean drinking water for past 3 days. 30 people affected.',            30, 0, 'HIGH',     'PENDING',      '2024-08-05 09:00:00', 4, 1, 1),
('MEDICAL',   'Pregnant woman needs emergency medical help – no ambulance available.',     1,  1, 'CRITICAL', 'IN_PROGRESS',  '2024-08-05 16:00:00', 6, 1, 1);

-- ─── REQUEST_RESOURCE_TYPE ───────────────────────────────────────────────────
INSERT INTO REQUEST_RESOURCE_TYPE (request_id, type_id, quantity_required) VALUES
(1, 4, 1),   -- Request 1 needs 1 Rescue Boat
(1, 3, 1),   -- Request 1 needs 1 Medical Supply kit
(2, 6, 1),   -- Request 2 needs shelter kit
(3, 1, 15),  -- Request 3 needs 15 Food Ration packs
(4, 3, 2),   -- Request 4 needs 2 Medical kits
(5, 4, 1),   -- Request 5 needs 1 rescue boat
(5, 2, 2),   -- Request 5 needs 2 water tankers
(6, 2, 3),   -- Request 6 needs 3 water units
(7, 8, 1),   -- Request 7 needs 1 heavy machinery
(7, 3, 3),   -- Request 7 needs 3 medical kits
(8, 6, 2),   -- Request 8 needs 2 shelter kits
(9, 2, 2),   -- Request 9 needs 2 water units
(10, 5, 1);  -- Request 10 needs 1 ambulance

-- ─── ASSIGNMENT ──────────────────────────────────────────────────────────────
INSERT INTO ASSIGNMENT (assigned_time, status, remarks, request_id, resource_id, shelter_id, assigned_by) VALUES
('2024-08-02 09:45:00', 'COMPLETED', 'Boat RB-07 deployed. Family rescued safely.',               1, 4,    NULL, 2),
('2024-08-02 10:55:00', 'COMPLETED', 'Victim placed in Government HSS camp.',                     2, NULL, 1,    2),
('2024-08-02 11:30:00', 'ACTIVE',    '15 food packs dispatched to building.',                     3, 1,    NULL, 3),
('2024-08-03 07:20:00', 'COMPLETED', 'First aid and insulin administered by medical team.',       4, 3,    NULL, 2),
('2024-07-12 14:30:00', 'ACTIVE',    'Boat dispatched with 5 rescuers.',                          5, 11,   NULL, 7),
('2024-07-13 08:30:00', 'COMPLETED', 'Water tanker delivered to camp.',                           6, 2,    NULL, 7),
('2024-08-06 07:00:00', 'COMPLETED', 'JCB deployed. Debris cleared in 4 hours.',                 7, 14,   NULL, 7),
('2024-08-02 11:00:00', 'COMPLETED', 'Medical kit and ambulance dispatched.',                     4, 5,    NULL, 3);

-- ─── INVENTORY_TRANSACTION ───────────────────────────────────────────────────
INSERT INTO INVENTORY_TRANSACTION (quantity, transaction_type, notes, transaction_time, resource_id, assignment_id, performed_by) VALUES
(100, 'IN',         'Initial stock received from Red Cross.',                       '2024-07-28 09:00:00', 1,  NULL, 3),
(50,  'OUT',        'Dispatched for flood relief – Request #3.',                    '2024-08-02 11:30:00', 1,  3,    3),
(1,   'OUT',        'Boat RB-07 deployed for rescue operation.',                    '2024-08-02 09:45:00', 4,  1,    2),
(1,   'IN',         'Boat RB-07 returned after successful rescue.',                 '2024-08-02 14:00:00', 4,  NULL, 2),
(20,  'OUT',        'Medical kits dispatched to flood zone.',                       '2024-08-03 07:20:00', 3,  4,    2),
(500, 'IN',         'New food ration stock from NDRF warehouse.',                   '2024-08-04 08:00:00', 1,  NULL, 1),
(2,   'OUT',        'Water tankers dispatched to Brahmaputra camp.',                '2024-07-13 08:30:00', 2,  6,    7),
(10,  'IN',         'Blanket stock donated by NGO partner.',                        '2024-08-01 10:00:00', 12, NULL, 3),
(100, 'IN',         'Tarpaulin kits received from government warehouse.',           '2024-06-14 09:00:00', 6,  NULL, 3),
(1,   'OUT',        'JCB excavator deployed for Dehradun debris removal.',          '2024-08-06 07:00:00', 14, 7,    7),
(5,   'ADJUSTMENT', 'Stock count correction after physical audit.',                 '2024-08-10 12:00:00', 8,  NULL, 1),
(3,   'OUT',        'Ambulances dispatched to medical emergency zone.',             '2024-08-05 16:30:00', 5,  8,    3);

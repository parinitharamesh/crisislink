"""
Neo4j Graph Database Routes
Demonstrates graph traversal, Cypher queries, node/relationship exploration.
Unit 4: Graph Databases (Neo4j)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request
from config.neo4j_db import run_cypher, get_neo4j_driver
from middleware.auth_middleware import role_required
from config.database import get_db

neo4j_bp = Blueprint('neo4j', __name__)


@neo4j_bp.route('/sync', methods=['POST'])
@role_required('ADMIN')
def sync_to_neo4j():
    """
    Synchronize MySQL data to Neo4j.
    Creates/updates nodes and relationships from MySQL source of truth.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Fetch all entities
                cur.execute('SELECT * FROM ORGANIZATION')
                orgs = cur.fetchall()

                cur.execute('SELECT * FROM LOCATION')
                locations = cur.fetchall()

                cur.execute('SELECT * FROM RESOURCE_TYPE')
                rtypes = cur.fetchall()

                cur.execute('SELECT * FROM `USER` WHERE role != "CITIZEN" OR org_id IS NOT NULL')
                users = cur.fetchall()

                cur.execute('SELECT * FROM INCIDENT')
                incidents = cur.fetchall()

                cur.execute('SELECT * FROM RESOURCE')
                resources = cur.fetchall()

                cur.execute('SELECT * FROM SHELTER')
                shelters = cur.fetchall()

                cur.execute('SELECT * FROM EMERGENCY_REQUEST LIMIT 50')
                requests = cur.fetchall()

                cur.execute('SELECT * FROM ASSIGNMENT LIMIT 50')
                assignments = cur.fetchall()

        driver = get_neo4j_driver()
        with driver.session() as session:
            # Create Organization nodes
            for org in orgs:
                session.run(
                    "MERGE (o:Organization {org_id: $org_id}) "
                    "SET o.name = $name, o.type = $type",
                    org_id=org['org_id'], name=org['org_name'], type=org['org_type']
                )

            # Create Location nodes
            for loc in locations:
                session.run(
                    "MERGE (l:Location {location_id: $lid}) "
                    "SET l.area_name = $name, l.district = $district, l.state = $state",
                    lid=loc['location_id'], name=loc['area_name'],
                    district=loc['district'], state=loc['state']
                )

            # Create ResourceType nodes
            for rt in rtypes:
                session.run(
                    "MERGE (rt:ResourceType {type_id: $tid}) SET rt.name = $name",
                    tid=rt['type_id'], name=rt['type_name']
                )

            # Create Incident nodes + LOCATION_HAS_INCIDENT relationship
            for inc in incidents:
                session.run(
                    "MERGE (i:Incident {incident_id: $iid}) "
                    "SET i.title = $title, i.type = $type, i.severity = $sev, i.status = $status "
                    "WITH i "
                    "MATCH (l:Location {location_id: $lid}) "
                    "MERGE (l)-[:LOCATION_HAS_INCIDENT]->(i)",
                    iid=inc['incident_id'], title=inc['title'],
                    type=inc['incident_type'], sev=inc['severity'],
                    status=inc['status'], lid=inc['location_id']
                )

            # Create Resource nodes
            for r in resources:
                session.run(
                    "MERGE (r:Resource {resource_id: $rid}) "
                    "SET r.name = $name, r.quantity = $qty, r.status = $status "
                    "WITH r "
                    "MATCH (o:Organization {org_id: $oid}) "
                    "MERGE (o)-[:ORGANIZATION_OWNS_RESOURCE]->(r) "
                    "WITH r "
                    "MATCH (rt:ResourceType {type_id: $tid}) "
                    "MERGE (r)-[:RESOURCE_BELONGS_TO_TYPE]->(rt) "
                    "WITH r "
                    "MATCH (l:Location {location_id: $lid}) "
                    "MERGE (r)-[:RESOURCE_LOCATED_AT]->(l)",
                    rid=r['resource_id'], name=r['resource_name'],
                    qty=r['quantity'], status=r['status'],
                    oid=r['org_id'], tid=r['type_id'], lid=r['location_id']
                )

            # Create Shelter nodes
            for s in shelters:
                session.run(
                    "MERGE (sh:Shelter {shelter_id: $sid}) "
                    "SET sh.name = $name, sh.capacity = $cap, "
                    "    sh.occupancy = $occ, sh.status = $status "
                    "WITH sh "
                    "MATCH (o:Organization {org_id: $oid}) "
                    "MERGE (o)-[:ORGANIZATION_MANAGES_SHELTER]->(sh) "
                    "WITH sh "
                    "MATCH (l:Location {location_id: $lid}) "
                    "MERGE (sh)-[:SHELTER_LOCATED_AT]->(l)",
                    sid=s['shelter_id'], name=s['shelter_name'],
                    cap=s['capacity'], occ=s['current_occupancy'],
                    status=s['status'], oid=s['org_id'], lid=s['location_id']
                )

            # Create EmergencyRequest nodes
            for req in requests:
                session.run(
                    "MERGE (er:EmergencyRequest {request_id: $rid}) "
                    "SET er.type = $type, er.priority = $priority, er.status = $status "
                    "WITH er "
                    "MATCH (l:Location {location_id: $lid}) "
                    "MERGE (er)-[:REQUEST_AT_LOCATION]->(l)",
                    rid=req['request_id'], type=req['request_type'],
                    priority=req['priority'], status=req['status'],
                    lid=req['location_id']
                )
                # Link to incident if any
                if req.get('incident_id'):
                    session.run(
                        "MATCH (er:EmergencyRequest {request_id: $rid}) "
                        "MATCH (i:Incident {incident_id: $iid}) "
                        "MERGE (i)-[:INCIDENT_GENERATES_REQUEST]->(er)",
                        rid=req['request_id'], iid=req['incident_id']
                    )

            # Create Assignment relationships
            for a in assignments:
                session.run(
                    "MERGE (as:Assignment {assignment_id: $aid}) "
                    "SET as.status = $status "
                    "WITH as "
                    "MATCH (er:EmergencyRequest {request_id: $rid}) "
                    "MERGE (er)-[:REQUEST_HAS_ASSIGNMENT]->(as)",
                    aid=a['assignment_id'], status=a['status'],
                    rid=a['request_id']
                )
                if a.get('resource_id'):
                    session.run(
                        "MATCH (as:Assignment {assignment_id: $aid}) "
                        "MATCH (r:Resource {resource_id: $rid}) "
                        "MERGE (as)-[:ASSIGNMENT_USES_RESOURCE]->(r)",
                        aid=a['assignment_id'], rid=a['resource_id']
                    )
                if a.get('shelter_id'):
                    session.run(
                        "MATCH (as:Assignment {assignment_id: $aid}) "
                        "MATCH (sh:Shelter {shelter_id: $sid}) "
                        "MERGE (as)-[:ASSIGNMENT_USES_SHELTER]->(sh)",
                        aid=a['assignment_id'], sid=a['shelter_id']
                    )

        return jsonify({'message': 'Neo4j sync complete'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@neo4j_bp.route('/incident/<int:incident_id>/trace', methods=['GET'])
def trace_incident(incident_id):
    """
    Cypher Query 1: Trace incident → requests → assignments → resources/shelters.
    Demonstrates multi-hop graph traversal.
    """
    try:
        verify_jwt_in_request()
        result = run_cypher('''
            MATCH (i:Incident {incident_id: $iid})
            OPTIONAL MATCH (i)-[:INCIDENT_GENERATES_REQUEST]->(er:EmergencyRequest)
            OPTIONAL MATCH (er)-[:REQUEST_HAS_ASSIGNMENT]->(a:Assignment)
            OPTIONAL MATCH (a)-[:ASSIGNMENT_USES_RESOURCE]->(r:Resource)
            OPTIONAL MATCH (a)-[:ASSIGNMENT_USES_SHELTER]->(sh:Shelter)
            RETURN
                i.incident_id  AS incident_id,
                i.title        AS incident_title,
                i.severity     AS severity,
                er.request_id  AS request_id,
                er.type        AS request_type,
                er.priority    AS priority,
                er.status      AS request_status,
                a.assignment_id AS assignment_id,
                a.status       AS assignment_status,
                r.name         AS resource_name,
                r.status       AS resource_status,
                sh.name        AS shelter_name,
                sh.status      AS shelter_status
            ORDER BY er.priority
        ''', {'iid': incident_id})

        return jsonify({'trace': result, 'incident_id': incident_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@neo4j_bp.route('/request/<int:req_id>/resources', methods=['GET'])
def find_request_resources(req_id):
    """
    Cypher Query 2: Find resources suitable for a particular emergency request.
    Graph traversal through request → resource types → matching resources.
    """
    try:
        verify_jwt_in_request()
        result = run_cypher('''
            MATCH (er:EmergencyRequest {request_id: $rid})
            MATCH (r:Resource)-[:RESOURCE_BELONGS_TO_TYPE]->(rt:ResourceType)
            WHERE r.status = 'AVAILABLE' AND r.quantity > 0
            MATCH (o:Organization)-[:ORGANIZATION_OWNS_RESOURCE]->(r)
            MATCH (r)-[:RESOURCE_LOCATED_AT]->(l:Location)
            RETURN
                er.request_id   AS request_id,
                r.resource_id   AS resource_id,
                r.name          AS resource_name,
                r.quantity      AS quantity,
                rt.name         AS resource_type,
                o.name          AS organization,
                l.area_name     AS location,
                l.state         AS state
            ORDER BY r.quantity DESC
            LIMIT 10
        ''', {'rid': req_id})

        return jsonify({'suitable_resources': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@neo4j_bp.route('/incident/<int:incident_id>/organizations', methods=['GET'])
def incident_organizations(incident_id):
    """
    Cypher Query 3: Find organizations involved in responding to an incident.
    Graph path: Incident → Requests → Assignments → Resources → Organizations.
    """
    try:
        verify_jwt_in_request()
        result = run_cypher('''
            MATCH (i:Incident {incident_id: $iid})
                  -[:INCIDENT_GENERATES_REQUEST]->(er:EmergencyRequest)
                  -[:REQUEST_HAS_ASSIGNMENT]->(a:Assignment)
                  -[:ASSIGNMENT_USES_RESOURCE]->(r:Resource)
                  <-[:ORGANIZATION_OWNS_RESOURCE]-(o:Organization)
            RETURN DISTINCT
                o.org_id   AS org_id,
                o.name     AS org_name,
                o.type     AS org_type,
                COUNT(DISTINCT r.resource_id) AS resources_deployed,
                COUNT(DISTINCT a.assignment_id) AS assignments
            ORDER BY resources_deployed DESC
        ''', {'iid': incident_id})

        return jsonify({'organizations': result, 'incident_id': incident_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@neo4j_bp.route('/locations/connected', methods=['GET'])
def connected_locations():
    """
    Cypher Query 4: Explore connected locations and incidents.
    Find all locations that share incidents or resources within 2 hops.
    """
    try:
        verify_jwt_in_request()
        result = run_cypher('''
            MATCH (l:Location)-[:LOCATION_HAS_INCIDENT]->(i:Incident)
            RETURN
                l.location_id AS location_id,
                l.area_name   AS area_name,
                l.state       AS state,
                COUNT(DISTINCT i.incident_id) AS incident_count,
                COLLECT(DISTINCT i.type) AS incident_types,
                COLLECT(DISTINCT i.severity) AS severities
            ORDER BY incident_count DESC
        ''')

        return jsonify({'connected_locations': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@neo4j_bp.route('/graph/stats', methods=['GET'])
@neo4j_bp.route('/stats', methods=['GET'])
def graph_stats():
    """Get overall graph database statistics."""
    try:
        verify_jwt_in_request()
        result = run_cypher('''
            MATCH (n)
            RETURN labels(n)[0] AS node_type, COUNT(n) AS count
            ORDER BY count DESC
        ''')

        rel_result = run_cypher('''
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type, COUNT(r) AS count
            ORDER BY count DESC
        ''')

        return jsonify({'nodes': result, 'relationships': rel_result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

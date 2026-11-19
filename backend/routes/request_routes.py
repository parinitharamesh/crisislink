"""Emergency request routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from config.database import get_db
from middleware.auth_middleware import role_required, get_current_user_id

request_bp = Blueprint('requests', __name__)


@request_bp.route('', methods=['GET'])
def get_requests():
    """Get requests – admins/coordinators see all, citizens see their own."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        claims  = get_jwt()
        role    = claims.get('role', 'CITIZEN')

        page  = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        status_filter   = request.args.get('status')
        priority_filter = request.args.get('priority')

        with get_db() as conn:
            with conn.cursor() as cur:
                where_clauses = []
                params = []

                if role == 'CITIZEN':
                    where_clauses.append('er.user_id = %s')
                    params.append(user_id)
                if status_filter:
                    where_clauses.append('er.status = %s')
                    params.append(status_filter)
                if priority_filter:
                    where_clauses.append('er.priority = %s')
                    params.append(priority_filter)

                where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

                cur.execute(f'''
                    SELECT er.request_id, er.request_type, er.description,
                           er.people_count, er.medical_needed, er.priority,
                           er.status, er.request_time, er.resolved_time,
                           u.full_name AS requester_name, u.phone AS requester_phone,
                           l.area_name, l.district, l.state,
                           i.title AS incident_title, i.incident_type,
                           er.incident_id, er.location_id
                    FROM EMERGENCY_REQUEST er
                    INNER JOIN `USER`   u ON er.user_id     = u.user_id
                    INNER JOIN LOCATION l ON er.location_id = l.location_id
                    LEFT  JOIN INCIDENT i ON er.incident_id = i.incident_id
                    {where_sql}
                    ORDER BY
                        FIELD(er.priority,'CRITICAL','HIGH','MEDIUM','LOW'),
                        er.request_time DESC
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

                # Get total count
                cur.execute(f'''
                    SELECT COUNT(*) AS total FROM EMERGENCY_REQUEST er {where_sql}
                ''', params)
                total = cur.fetchone()['total']

        return jsonify({'requests': rows, 'total': total, 'page': page, 'limit': limit}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@request_bp.route('', methods=['POST'])
def create_request():
    """Citizens (and all users) can submit emergency requests."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        data = request.get_json()
        required = ['request_type', 'description', 'location_id']
        for f in required:
            if not data.get(f):
                return jsonify({'error': f'Field "{f}" is required'}), 400

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO EMERGENCY_REQUEST
                    (request_type, description, people_count, medical_needed,
                     priority, status, user_id, incident_id, location_id)
                    VALUES (%s, %s, %s, %s, %s, 'PENDING', %s, %s, %s)
                ''', (
                    data['request_type'].upper(),
                    data['description'],
                    data.get('people_count', 1),
                    1 if data.get('medical_needed') else 0,
                    data.get('priority', 'MEDIUM').upper(),
                    user_id,
                    data.get('incident_id'),
                    data['location_id']
                ))
                req_id = cur.lastrowid

                # Insert resource type requirements if provided
                resource_types = data.get('resource_types', [])
                for rt in resource_types:
                    cur.execute('''
                        INSERT INTO REQUEST_RESOURCE_TYPE (request_id, type_id, quantity_required)
                        VALUES (%s, %s, %s)
                    ''', (req_id, rt['type_id'], rt.get('quantity_required', 1)))

        return jsonify({'message': 'Emergency request submitted', 'request_id': req_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@request_bp.route('/<int:req_id>', methods=['GET'])
def get_request(req_id):
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        claims  = get_jwt()
        role    = claims.get('role', 'CITIZEN')

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT er.*, u.full_name AS requester_name, u.phone,
                           l.area_name, l.district, l.state, l.latitude, l.longitude,
                           i.title AS incident_title, i.incident_type, i.severity
                    FROM EMERGENCY_REQUEST er
                    INNER JOIN `USER`   u ON er.user_id     = u.user_id
                    INNER JOIN LOCATION l ON er.location_id = l.location_id
                    LEFT  JOIN INCIDENT i ON er.incident_id = i.incident_id
                    WHERE er.request_id = %s
                ''', (req_id,))
                req = cur.fetchone()

                if not req:
                    return jsonify({'error': 'Request not found'}), 404
                if role == 'CITIZEN' and str(req['user_id']) != str(user_id):
                    return jsonify({'error': 'Access denied'}), 403

                # Get resource types needed
                cur.execute('''
                    SELECT rrt.type_id, rrt.quantity_required, rt.type_name
                    FROM REQUEST_RESOURCE_TYPE rrt
                    INNER JOIN RESOURCE_TYPE rt ON rrt.type_id = rt.type_id
                    WHERE rrt.request_id = %s
                ''', (req_id,))
                req['resource_types'] = cur.fetchall()

                # Get assignments
                cur.execute('''
                    SELECT a.*, r.resource_name, s.shelter_name,
                           u.full_name AS assigned_by_name
                    FROM ASSIGNMENT a
                    LEFT JOIN RESOURCE r ON a.resource_id = r.resource_id
                    LEFT JOIN SHELTER  s ON a.shelter_id  = s.shelter_id
                    LEFT JOIN `USER`   u ON a.assigned_by = u.user_id
                    WHERE a.request_id = %s
                ''', (req_id,))
                req['assignments'] = cur.fetchall()

        return jsonify({'request': req}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@request_bp.route('/<int:req_id>/status', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_status(req_id):
    data   = request.get_json()
    status = data.get('status', '').upper()
    valid  = ('PENDING','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED')
    if status not in valid:
        return jsonify({'error': f'Invalid status. Valid: {valid}'}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE EMERGENCY_REQUEST SET status = %s WHERE request_id = %s',
                    (status, req_id)
                )
                if cur.rowcount == 0:
                    cur.execute('SELECT request_id FROM EMERGENCY_REQUEST WHERE request_id = %s', (req_id,))
                    if not cur.fetchone():
                        return jsonify({'error': 'Request not found'}), 404

        return jsonify({'message': 'Status updated', 'status': status}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@request_bp.route('/stats/summary', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def request_stats():
    """Aggregate statistics – demonstrates GROUP BY, HAVING, aggregate functions."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        status,
                        priority,
                        COUNT(*) AS count,
                        SUM(people_count) AS total_affected,
                        AVG(people_count) AS avg_affected,
                        SUM(medical_needed) AS medical_count
                    FROM EMERGENCY_REQUEST
                    GROUP BY status, priority
                    ORDER BY FIELD(priority,'CRITICAL','HIGH','MEDIUM','LOW'), status
                ''')
                stats = cur.fetchall()

                cur.execute('''
                    SELECT COUNT(*) AS total, SUM(people_count) AS total_affected,
                           SUM(medical_needed) AS medical_needed_count
                    FROM EMERGENCY_REQUEST
                    WHERE status NOT IN ('CLOSED')
                ''')
                overview = cur.fetchone()

        return jsonify({'stats': stats, 'overview': overview}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

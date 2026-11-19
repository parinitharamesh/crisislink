"""Incident management routes."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from config.database import get_db
from middleware.auth_middleware import role_required

incident_bp = Blueprint('incidents', __name__)


@incident_bp.route('', methods=['GET'])
def get_incidents():
    """Return all incidents for authenticated users."""
    try:
        verify_jwt_in_request()

        page = max(1, int(request.args.get('page', 1)))
        limit = max(1, min(100, int(request.args.get('limit', 20))))
        offset = (page - 1) * limit

        filters = []
        params = []

        if request.args.get('status'):
            filters.append('i.status = %s')
            params.append(request.args.get('status', '').upper())
        if request.args.get('severity'):
            filters.append('i.severity = %s')
            params.append(request.args.get('severity', '').upper())
        if request.args.get('incident_type'):
            filters.append('i.incident_type = %s')
            params.append(request.args.get('incident_type', '').upper())

        where_sql = (' WHERE ' + ' AND '.join(filters)) if filters else ''

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT i.incident_id, i.incident_type, i.title, i.start_date,
                           i.end_date, i.description, i.affected_area, i.severity,
                           i.status, i.location_id, i.reported_by, i.created_at,
                           l.area_name, l.district, l.state,
                           u.full_name AS reported_by_name
                    FROM INCIDENT i
                    INNER JOIN LOCATION l ON i.location_id = l.location_id
                    LEFT JOIN `USER` u ON i.reported_by = u.user_id
                    {where_sql}
                    ORDER BY i.start_date DESC, i.incident_id DESC
                    LIMIT %s OFFSET %s
                    ''',
                    params + [limit, offset],
                )
                incidents = cur.fetchall()

                cur.execute(f'''SELECT COUNT(*) AS total FROM INCIDENT i {where_sql}''', params)
                total = cur.fetchone()['total']

        return jsonify({'incidents': incidents, 'total': total, 'page': page, 'limit': limit}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@incident_bp.route('', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_incident():
    """Create a new incident report."""
    data = request.get_json() or {}
    required = ['incident_type', 'title', 'start_date', 'location_id']
    for field in required:
        if field not in data or data.get(field) in (None, ''):
            return jsonify({'error': f'Field "{field}" is required.'}), 400

    try:
        user_id = get_jwt_identity()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO INCIDENT (
                        incident_type, title, start_date, end_date, description,
                        affected_area, severity, status, location_id, reported_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        data['incident_type'].upper(),
                        data['title'],
                        data['start_date'],
                        data.get('end_date'),
                        data.get('description'),
                        data.get('affected_area'),
                        data.get('severity', 'MEDIUM').upper(),
                        data.get('status', 'ACTIVE').upper(),
                        data['location_id'],
                        user_id,
                    ),
                )
                incident_id = cur.lastrowid

        return jsonify({'message': 'Incident created', 'incident_id': incident_id}), 201
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@incident_bp.route('/summary', methods=['GET'])
def incident_summary():
    """Return summary statistics for incident monitoring."""
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) AS total FROM INCIDENT')
                total = cur.fetchone()['total']

                cur.execute("SELECT status, COUNT(*) AS count FROM INCIDENT GROUP BY status ORDER BY status")
                by_status = cur.fetchall()

                cur.execute("SELECT severity, COUNT(*) AS count FROM INCIDENT GROUP BY severity ORDER BY severity")
                by_severity = cur.fetchall()

                cur.execute("SELECT COUNT(*) AS active FROM INCIDENT WHERE status = 'ACTIVE'")
                active = cur.fetchone()['active']

        return jsonify({
            'summary': {
                'total_incidents': total,
                'active_incidents': active,
                'by_status': by_status,
                'by_severity': by_severity,
            }
        }), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@incident_bp.route('/<int:incident_id>', methods=['GET'])
def get_incident(incident_id):
    """Return a single incident and its related metadata."""
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT i.incident_id, i.incident_type, i.title, i.start_date,
                           i.end_date, i.description, i.affected_area, i.severity,
                           i.status, i.location_id, i.reported_by, i.created_at,
                           l.area_name, l.district, l.state,
                           u.full_name AS reported_by_name
                    FROM INCIDENT i
                    INNER JOIN LOCATION l ON i.location_id = l.location_id
                    LEFT JOIN `USER` u ON i.reported_by = u.user_id
                    WHERE i.incident_id = %s
                    ''',
                    (incident_id,),
                )
                incident = cur.fetchone()

        if not incident:
            return jsonify({'error': 'Incident not found'}), 404

        return jsonify({'incident': incident}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@incident_bp.route('/<int:incident_id>', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_incident(incident_id):
    """Update incident details."""
    data = request.get_json() or {}
    if not data:
        return jsonify({'error': 'No fields provided to update'}), 400

    try:
        allowed_fields = {
            'incident_type': 'incident_type',
            'title': 'title',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'description': 'description',
            'affected_area': 'affected_area',
            'severity': 'severity',
            'status': 'status',
            'location_id': 'location_id',
        }

        assignments = []
        values = []
        for key, value in data.items():
            if key in allowed_fields:
                assignments.append(f"{allowed_fields[key]} = %s")
                values.append(value.upper() if key in {'incident_type', 'severity', 'status'} else value)

        if not assignments:
            return jsonify({'error': 'No valid incident fields provided'}), 400

        values.append(incident_id)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE INCIDENT SET {', '.join(assignments)} WHERE incident_id = %s",
                    tuple(values),
                )

                if cur.rowcount == 0:
                    return jsonify({'error': 'Incident not found'}), 404

        return jsonify({'message': 'Incident updated'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500

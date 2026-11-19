"""Dashboard statistics route using stored procedure."""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from config.database import get_db
from middleware.auth_middleware import role_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def dashboard_stats():
    """
    Calls sp_dashboard_stats stored procedure which returns multiple result sets.
    Also demonstrates window functions via vw_request_priority_rank.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Request status breakdown
                cur.execute('''
                    SELECT status,
                           COUNT(*) AS count,
                           SUM(people_count) AS total_affected
                    FROM EMERGENCY_REQUEST
                    GROUP BY status
                ''')
                request_stats = cur.fetchall()

                # Active incidents
                cur.execute('''
                    SELECT i.incident_id, i.title, i.incident_type, i.severity,
                           i.start_date, l.area_name,
                           COUNT(DISTINCT er.request_id) AS request_count,
                           SUM(COALESCE(er.people_count,0)) AS total_affected
                    FROM INCIDENT i
                    INNER JOIN LOCATION l ON i.location_id = l.location_id
                    LEFT  JOIN EMERGENCY_REQUEST er ON er.incident_id = i.incident_id
                    WHERE i.status = 'ACTIVE'
                    GROUP BY i.incident_id, i.title, i.incident_type, i.severity, i.start_date, l.area_name
                    ORDER BY i.start_date DESC
                ''')
                active_incidents = cur.fetchall()

                # Shelter occupancy overview
                cur.execute('''
                    SELECT SUM(capacity) AS total_capacity,
                           SUM(current_occupancy) AS total_occupied,
                           COUNT(*) AS total_shelters,
                           SUM(CASE WHEN status = 'FULL' THEN 1 ELSE 0 END) AS full_shelters,
                           SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_shelters
                    FROM SHELTER WHERE status != 'CLOSED'
                ''')
                shelter_overview = cur.fetchone()

                # Resource availability by type
                cur.execute('''
                    SELECT rt.type_name,
                           SUM(r.quantity) AS total_qty,
                           SUM(CASE WHEN r.status='AVAILABLE' THEN r.quantity ELSE 0 END) AS avail_qty,
                           SUM(CASE WHEN r.status='DEPLOYED'  THEN r.quantity ELSE 0 END) AS deployed_qty
                    FROM RESOURCE_TYPE rt
                    LEFT JOIN RESOURCE r ON r.type_id = rt.type_id
                    GROUP BY rt.type_id, rt.type_name
                    ORDER BY total_qty DESC
                ''')
                resource_summary = cur.fetchall()

                # Pending critical requests (window function demo)
                cur.execute('''
                    SELECT * FROM vw_request_priority_rank
                    WHERE status IN ('PENDING','ASSIGNED')
                    ORDER BY priority_rank
                    LIMIT 10
                ''')
                critical_requests = cur.fetchall()

                # Assignment counts
                cur.execute('''
                    SELECT status, COUNT(*) AS count
                    FROM ASSIGNMENT GROUP BY status
                ''')
                assignment_stats = cur.fetchall()

                # Total people affected across all active incidents
                cur.execute('''
                    SELECT COUNT(*) AS pending_requests
                    FROM EMERGENCY_REQUEST WHERE status = 'PENDING'
                ''')
                pending = cur.fetchone()

        return jsonify({
            'request_stats':     request_stats,
            'active_incidents':  active_incidents,
            'shelter_overview':  shelter_overview,
            'resource_summary':  resource_summary,
            'critical_requests': critical_requests,
            'assignment_stats':  assignment_stats,
            'pending_count':     pending['pending_requests']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/citizen/<int:uid>', methods=['GET'])
def citizen_dashboard(uid):
    """Citizen-specific dashboard data."""
    try:
        verify_jwt_in_request()
        role = get_jwt().get('role')
        user_id = get_jwt_identity()
        if role == 'CITIZEN' and str(user_id) != str(uid):
            return jsonify({'error': 'Access denied'}), 403
        if role not in ('CITIZEN', 'COORDINATOR', 'ADMIN'):
            return jsonify({'error': 'Access denied'}), 403

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT er.request_id, er.request_type, er.status,
                           er.priority, er.people_count,
                           er.request_time, er.resolved_time,
                           l.area_name,
                           COUNT(a.assignment_id) AS assignment_count
                    FROM EMERGENCY_REQUEST er
                    INNER JOIN LOCATION l ON er.location_id = l.location_id
                    LEFT  JOIN ASSIGNMENT a ON a.request_id = er.request_id
                    WHERE er.user_id = %s
                    GROUP BY er.request_id
                    ORDER BY er.request_time DESC
                ''', (uid,))
                requests = cur.fetchall()

                cur.execute('''
                    SELECT COUNT(*) AS total,
                           SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) AS pending,
                           SUM(CASE WHEN status='RESOLVED' THEN 1 ELSE 0 END) AS resolved
                    FROM EMERGENCY_REQUEST WHERE user_id = %s
                ''', (uid,))
                stats = cur.fetchone()

        return jsonify({'requests': requests, 'stats': stats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

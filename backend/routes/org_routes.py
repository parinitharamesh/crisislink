"""Organization routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request
from config.database import get_db
from middleware.auth_middleware import role_required

org_bp = Blueprint('organizations', __name__)


@org_bp.route('', methods=['GET'])
def get_orgs():
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT o.*,
                           COUNT(DISTINCT u.user_id)  AS user_count,
                           COUNT(DISTINCT r.resource_id) AS resource_count,
                           COUNT(DISTINCT s.shelter_id)  AS shelter_count
                    FROM ORGANIZATION o
                    LEFT JOIN `USER`   u ON u.org_id = o.org_id
                    LEFT JOIN RESOURCE r ON r.org_id = o.org_id
                    LEFT JOIN SHELTER  s ON s.org_id = o.org_id
                    GROUP BY o.org_id
                    ORDER BY o.org_name
                ''')
                rows = cur.fetchall()
        return jsonify({'organizations': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@org_bp.route('', methods=['POST'])
@role_required('ADMIN')
def create_org():
    data = request.get_json()
    required = ['org_name', 'org_type', 'contact_no', 'address']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'Field "{f}" is required'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO ORGANIZATION (org_name, org_type, contact_no, address)
                    VALUES (%s,%s,%s,%s)
                ''', (data['org_name'], data['org_type'].upper(),
                      data['contact_no'], data['address']))
                oid = cur.lastrowid
        return jsonify({'message': 'Organization created', 'org_id': oid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@org_bp.route('/locations', methods=['GET'])
def get_locations():
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                # Older local databases may not have migration 06's hierarchy
                # column yet. Keep the location picker usable with either schema.
                cur.execute("SHOW COLUMNS FROM LOCATION LIKE 'parent_location_id'")
                has_hierarchy = cur.fetchone() is not None
                if has_hierarchy:
                    cur.execute('''
                        SELECT l.* FROM LOCATION l
                        WHERE NOT EXISTS (
                            SELECT 1 FROM LOCATION c
                            WHERE c.parent_location_id = l.location_id
                        )
                        ORDER BY l.state, l.area_name
                    ''')  # leaf locations only; hierarchy nodes are grouping levels
                else:
                    cur.execute('SELECT * FROM LOCATION ORDER BY state, area_name')
                rows = cur.fetchall()
        return jsonify({'locations': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

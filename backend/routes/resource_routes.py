"""Resource management routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request
from config.database import get_db
from middleware.auth_middleware import role_required

resource_bp = Blueprint('resources', __name__)


@resource_bp.route('', methods=['GET'])
def get_resources():
    try:
        verify_jwt_in_request()
        page   = int(request.args.get('page', 1))
        limit  = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        status = request.args.get('status')
        type_id = request.args.get('type_id')

        where_parts, params = [], []
        if status:
            where_parts.append('r.status = %s'); params.append(status)
        if type_id:
            where_parts.append('r.type_id = %s'); params.append(type_id)

        where = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    SELECT r.*, rt.type_name, o.org_name,
                           l.area_name, l.district, l.state
                    FROM RESOURCE r
                    INNER JOIN RESOURCE_TYPE rt ON r.type_id    = rt.type_id
                    INNER JOIN ORGANIZATION  o  ON r.org_id     = o.org_id
                    INNER JOIN LOCATION      l  ON r.location_id= l.location_id
                    {where}
                    ORDER BY r.status, r.resource_name
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

                cur.execute(f'SELECT COUNT(*) AS total FROM RESOURCE r {where}', params)
                total = cur.fetchone()['total']

        return jsonify({'resources': rows, 'total': total}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resource_bp.route('', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_resource():
    data = request.get_json()
    required = ['resource_name', 'type_id', 'quantity', 'location_id', 'org_id']
    for f in required:
        if data.get(f) is None:
            return jsonify({'error': f'Field "{f}" is required'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO RESOURCE
                    (resource_name, type_id, quantity, unit, status, location_id, org_id, description)
                    VALUES (%s,%s,%s,%s,'AVAILABLE',%s,%s,%s)
                ''', (
                    data['resource_name'], data['type_id'], data['quantity'],
                    data.get('unit', 'units'), data['location_id'], data['org_id'],
                    data.get('description')
                ))
                rid = cur.lastrowid
        return jsonify({'message': 'Resource created', 'resource_id': rid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resource_bp.route('/<int:rid>', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_resource(rid):
    data = request.get_json()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE RESOURCE
                    SET resource_name = COALESCE(%s, resource_name),
                        quantity      = COALESCE(%s, quantity),
                        status        = COALESCE(%s, status),
                        description   = COALESCE(%s, description)
                    WHERE resource_id = %s
                ''', (
                    data.get('resource_name'), data.get('quantity'),
                    data.get('status'), data.get('description'), rid
                ))
                if cur.rowcount == 0:
                    cur.execute('SELECT resource_id FROM RESOURCE WHERE resource_id = %s', (rid,))
                    if not cur.fetchone():
                        return jsonify({'error': 'Resource not found'}), 404
        return jsonify({'message': 'Resource updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resource_bp.route('/types', methods=['GET'])
def get_resource_types():
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM RESOURCE_TYPE ORDER BY type_name')
                rows = cur.fetchall()
        return jsonify({'resource_types': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resource_bp.route('/types', methods=['POST'])
@role_required('ADMIN')
def create_resource_type():
    data = request.get_json()
    if not data.get('type_name'):
        return jsonify({'error': 'type_name is required'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO RESOURCE_TYPE (type_name, description) VALUES (%s,%s)',
                    (data['type_name'], data.get('description'))
                )
                tid = cur.lastrowid
        return jsonify({'message': 'Resource type created', 'type_id': tid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resource_bp.route('/availability', methods=['GET'])
def availability_summary():
    """Uses vw_resource_availability view."""
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM vw_resource_availability ORDER BY org_name, resource_type')
                rows = cur.fetchall()
        return jsonify({'availability': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

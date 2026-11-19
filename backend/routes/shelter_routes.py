"""Shelter management routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request
from config.database import get_db
from middleware.auth_middleware import role_required

shelter_bp = Blueprint('shelters', __name__)


@shelter_bp.route('', methods=['GET'])
def get_shelters():
    try:
        verify_jwt_in_request()
        page   = int(request.args.get('page', 1))
        limit  = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        status = request.args.get('status')
        medical = request.args.get('has_medical')

        where_parts, params = [], []
        if status:
            where_parts.append('s.status = %s'); params.append(status)
        if medical is not None:
            where_parts.append('s.has_medical_facility = %s'); params.append(int(medical))

        where = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    SELECT s.*, l.area_name, l.district, l.state,
                           o.org_name,
                           (s.capacity - s.current_occupancy) AS available_spots,
                           fn_shelter_occupancy_pct(s.shelter_id) AS occupancy_pct
                    FROM SHELTER s
                    INNER JOIN LOCATION     l ON s.location_id = l.location_id
                    INNER JOIN ORGANIZATION o ON s.org_id      = o.org_id
                    {where}
                    ORDER BY s.status, available_spots DESC
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

                cur.execute(f'SELECT COUNT(*) AS total FROM SHELTER s {where}', params)
                total = cur.fetchone()['total']

        return jsonify({'shelters': rows, 'total': total}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shelter_bp.route('', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_shelter():
    data = request.get_json()
    required = ['shelter_name', 'address', 'capacity', 'location_id', 'org_id']
    for f in required:
        if data.get(f) is None:
            return jsonify({'error': f'Field "{f}" is required'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO SHELTER
                    (shelter_name, address, capacity, current_occupancy,
                     has_medical_facility, status, location_id, org_id)
                    VALUES (%s,%s,%s,0,%s,'OPEN',%s,%s)
                ''', (
                    data['shelter_name'], data['address'], data['capacity'],
                    1 if data.get('has_medical_facility') else 0,
                    data['location_id'], data['org_id']
                ))
                sid = cur.lastrowid
        return jsonify({'message': 'Shelter created', 'shelter_id': sid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shelter_bp.route('/<int:sid>/occupancy', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_occupancy(sid):
    """Uses stored procedure sp_update_shelter_occupancy for safe update with locking."""
    data  = request.get_json()
    delta = data.get('delta')
    if delta is None:
        return jsonify({'error': 'delta (positive or negative integer) is required'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT shelter_id FROM SHELTER WHERE shelter_id = %s', (sid,))
                if not cur.fetchone():
                    return jsonify({'error': 'Shelter not found'}), 404

                cur.callproc('sp_update_shelter_occupancy', [sid, delta, 0, ''])
                cur.execute('SELECT @_sp_update_shelter_occupancy_2, @_sp_update_shelter_occupancy_3')
                res = cur.fetchone()

        # Parse stored procedure OUT params
        out_vals = list(res.values()) if res else [None, 'Error']
        new_occ, msg = out_vals[0], out_vals[1]

        if new_occ == -1:
            return jsonify({'error': msg}), 400

        return jsonify({'message': msg, 'new_occupancy': new_occ}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shelter_bp.route('/status', methods=['GET'])
def shelter_status():
    """Uses vw_shelter_status view."""
    try:
        verify_jwt_in_request()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM vw_shelter_status ORDER BY occupancy_pct DESC')
                rows = cur.fetchall()
        return jsonify({'shelters': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

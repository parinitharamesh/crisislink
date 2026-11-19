"""Assignment routes – allocation uses stored procedure sp_allocate_assignment;
cancelling is handled by trigger trg_assignment_cancel_restore."""

import pymysql
from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from config.database import get_db
from middleware.auth_middleware import role_required

assignment_bp = Blueprint('assignments', __name__)


@assignment_bp.route('', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def get_assignments():
    try:
        verify_jwt_in_request()
        page   = int(request.args.get('page', 1))
        limit  = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        req_id = request.args.get('request_id')

        where = 'WHERE a.request_id = %s' if req_id else ''
        params = [req_id] if req_id else []

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    SELECT a.*, er.request_type, er.priority, er.status AS request_status,
                           r.resource_name, r.status AS resource_status,
                           s.shelter_name, s.status AS shelter_status,
                           u.full_name AS assigned_by_name,
                           cit.full_name AS citizen_name,
                           l.area_name
                    FROM ASSIGNMENT a
                    INNER JOIN EMERGENCY_REQUEST er ON a.request_id  = er.request_id
                    LEFT  JOIN RESOURCE          r  ON a.resource_id = r.resource_id
                    LEFT  JOIN SHELTER           s  ON a.shelter_id  = s.shelter_id
                    LEFT  JOIN `USER`            u  ON a.assigned_by = u.user_id
                    INNER JOIN `USER`            cit ON er.user_id   = cit.user_id
                    INNER JOIN LOCATION          l  ON er.location_id= l.location_id
                    {where}
                    ORDER BY a.assigned_time DESC
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

        return jsonify({'assignments': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@assignment_bp.route('', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_assignment():
    """Allocate a resource (partial quantities allowed) and/or a shelter place.

    All business rules (stock check, over-allocation, shelter capacity, occupancy
    update, request status) live in the stored procedure sp_allocate_assignment,
    which runs as ONE atomic, row-locked transaction. This route only validates
    the input and translates the procedure result into HTTP.
    """
    data = request.get_json(silent=True) or {}

    def to_int(name, required=False):
        raw = data.get(name)
        if raw in (None, ''):
            if required:
                raise ValueError(f'{name} is required')
            return None
        try:
            val = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f'{name} must be a whole number')
        if val < 1:
            raise ValueError(f'{name} must be at least 1')
        return val

    try:
        request_id  = to_int('request_id', required=True)
        resource_id = to_int('resource_id')
        shelter_id  = to_int('shelter_id')
        quantity    = to_int('quantity') if resource_id else None
        people      = to_int('people') if shelter_id else None
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400

    if resource_id is None and shelter_id is None:
        return jsonify({'error': 'At least one of resource_id or shelter_id is required'}), 400

    user_id = int(get_jwt_identity())
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'CALL sp_allocate_assignment(%s, %s, %s, %s, %s, %s, %s, @aid, @st, @msg)',
                    (request_id, resource_id, quantity, shelter_id, people,
                     user_id, data.get('remarks') or '')
                )
                cur.execute('SELECT @aid AS aid, @st AS st, @msg AS msg')
                out = cur.fetchone()

                if out['st'] != 'SUCCESS':
                    msg = out['msg'] or 'Allocation failed'
                    if msg.startswith('Database error'):
                        return jsonify({'error': 'Allocation failed because of a database error'}), 500
                    if msg.endswith('not found.'):
                        return jsonify({'error': msg}), 404
                    if msg.startswith(('Provide', 'Quantity must', 'People count', 'A quantity', 'A people')):
                        return jsonify({'error': msg}), 400
                    return jsonify({'error': msg}), 409          # business-rule rejection

                cur.execute(
                    'SELECT quantity_allocated, people_housed FROM ASSIGNMENT WHERE assignment_id = %s',
                    (out['aid'],)
                )
                row = cur.fetchone() or {}

                # Preserve pre-Phase-A behaviour: a resource that has been allocated is
                # flagged DEPLOYED (dashboard deployed_qty and the Resources page filter
                # rely on it). sp_allocate_assignment does not set this itself. The
                # procedure has already rejected MAINTENANCE/EXHAUSTED, so only
                # AVAILABLE stock is promoted.
                if resource_id:
                    cur.execute('''
                        SELECT COUNT(*) AS trigger_count
                        FROM information_schema.TRIGGERS
                        WHERE TRIGGER_SCHEMA = DATABASE()
                          AND TRIGGER_NAME = 'trg_inventory_out_deduct'
                    ''')
                    has_inventory_trigger = cur.fetchone()['trigger_count'] > 0
                    allocated = row.get('quantity_allocated') or quantity or 0

                    if not has_inventory_trigger and allocated:
                        # Older local installs may not yet have migration 08's
                        # inventory trigger. Keep the stock update in this API path.
                        cur.execute('''
                            UPDATE RESOURCE
                            SET quantity = quantity - %s,
                                status = CASE WHEN quantity - %s <= 0
                                              THEN 'EXHAUSTED' ELSE 'DEPLOYED' END
                            WHERE resource_id = %s AND quantity >= %s
                        ''', (allocated, allocated, resource_id, allocated))
                        if cur.rowcount != 1:
                            raise RuntimeError('Resource stock changed during assignment')
                    else:
                        # The stored procedure already created the inventory OUT row;
                        # this preserves the existing display status when the trigger
                        # is present and has deducted stock.
                        cur.execute(
                            "UPDATE RESOURCE SET status = 'DEPLOYED' "
                            "WHERE resource_id = %s AND quantity > 0 AND status = 'AVAILABLE'",
                            (resource_id,)
                        )
        return jsonify({
            'message': out['msg'],
            'assignment_id': out['aid'],
            'quantity_allocated': row.get('quantity_allocated'),
            'people_housed': row.get('people_housed'),
            'inventory_deducted': row.get('quantity_allocated') or 0,   # kept for the existing frontend
        }), 201
    except Exception:
        return jsonify({'error': 'Could not create the assignment'}), 500


@assignment_bp.route('/<int:aid>/status', methods=['PUT'])
@role_required('ADMIN', 'COORDINATOR')
def update_assignment_status(aid):
    data   = request.get_json()
    status = data.get('status', '').upper()
    if status not in ('PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED'):
        return jsonify({'error': 'Invalid status'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE ASSIGNMENT SET status = %s WHERE assignment_id = %s',
                    (status, aid)
                )
                if cur.rowcount == 0:
                    cur.execute('SELECT assignment_id FROM ASSIGNMENT WHERE assignment_id = %s', (aid,))
                    if not cur.fetchone():
                        return jsonify({'error': 'Assignment not found'}), 404
        return jsonify({'message': 'Assignment status updated'}), 200
    except pymysql.MySQLError as e:
        if e.args and e.args[0] == 1644:          # raised by trg_assignment_cancel_guard
            return jsonify({'error': str(e.args[1])}), 409
        return jsonify({'error': 'Could not update the assignment'}), 500
    except Exception:
        return jsonify({'error': 'Could not update the assignment'}), 500


@assignment_bp.route('/find-resources/<int:req_id>', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def find_resources(req_id):
    """Uses sp_find_resources_for_request stored procedure."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.callproc('sp_find_resources_for_request', [req_id])
                rows = cur.fetchall()
        return jsonify({'available_resources': rows}), 200
    except Exception as e:
        # Fallback to direct query if procedure fetch fails
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT r.resource_id, r.resource_name, r.quantity,
                               r.status AS resource_status, rt.type_name,
                               l.area_name AS resource_location,
                               o.org_name AS organization,
                               rrt.quantity_required
                        FROM REQUEST_RESOURCE_TYPE rrt
                        INNER JOIN RESOURCE_TYPE rt ON rrt.type_id   = rt.type_id
                        INNER JOIN RESOURCE r       ON r.type_id     = rt.type_id
                        INNER JOIN LOCATION l        ON r.location_id = l.location_id
                        INNER JOIN ORGANIZATION o   ON r.org_id      = o.org_id
                        WHERE rrt.request_id = %s
                          AND r.status = 'AVAILABLE'
                          AND r.quantity >= rrt.quantity_required
                        ORDER BY r.quantity DESC
                    ''', (req_id,))
                    rows = cur.fetchall()
            return jsonify({'available_resources': rows}), 200
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

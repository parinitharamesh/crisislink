"""Inventory transaction routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from config.database import get_db
from middleware.auth_middleware import role_required

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def get_transactions():
    try:
        verify_jwt_in_request()
        page        = int(request.args.get('page', 1))
        limit       = int(request.args.get('limit', 50))
        offset      = (page - 1) * limit
        resource_id = request.args.get('resource_id')
        tx_type     = request.args.get('transaction_type')

        where_parts, params = [], []
        if resource_id:
            where_parts.append('it.resource_id = %s'); params.append(resource_id)
        if tx_type:
            where_parts.append('it.transaction_type = %s'); params.append(tx_type.upper())

        where = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    SELECT it.*, r.resource_name, rt.type_name,
                           o.org_name, a.assignment_id,
                           u.full_name AS performed_by_name
                    FROM INVENTORY_TRANSACTION it
                    INNER JOIN RESOURCE      r  ON it.resource_id   = r.resource_id
                    INNER JOIN RESOURCE_TYPE rt ON r.type_id        = rt.type_id
                    INNER JOIN ORGANIZATION  o  ON r.org_id         = o.org_id
                    LEFT  JOIN ASSIGNMENT    a  ON it.assignment_id = a.assignment_id
                    LEFT  JOIN `USER`        u  ON it.performed_by  = u.user_id
                    {where}
                    ORDER BY it.transaction_time DESC
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

                cur.execute(f'SELECT COUNT(*) AS total FROM INVENTORY_TRANSACTION it {where}', params)
                total = cur.fetchone()['total']

        return jsonify({'transactions': rows, 'total': total}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_bp.route('', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def create_transaction():
    """
    Create inventory transaction.
    The TRIGGER trg_inventory_out_deduct will auto-update resource quantity.
    """
    data = request.get_json()
    required = ['resource_id', 'quantity', 'transaction_type']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'Field "{f}" is required'}), 400

    tx_type = data['transaction_type'].upper()
    if tx_type not in ('IN', 'OUT', 'TRANSFER', 'ADJUSTMENT'):
        return jsonify({'error': 'transaction_type must be IN, OUT, TRANSFER, or ADJUSTMENT'}), 400

    try:
        user_id = get_jwt_identity()
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check resource exists and has sufficient quantity for OUT
                cur.execute(
                    'SELECT resource_id, quantity, status FROM RESOURCE WHERE resource_id = %s FOR UPDATE',
                    (data['resource_id'],)
                )
                res = cur.fetchone()
                if not res:
                    return jsonify({'error': 'Resource not found'}), 404

                if tx_type == 'OUT' and res['quantity'] < int(data['quantity']):
                    return jsonify({
                        'error': f'Insufficient quantity. Available: {res["quantity"]}, Requested: {data["quantity"]}'
                    }), 400

                cur.execute('''
                    INSERT INTO INVENTORY_TRANSACTION
                    (quantity, transaction_type, notes, resource_id, assignment_id, performed_by)
                    VALUES (%s,%s,%s,%s,%s,%s)
                ''', (
                    data['quantity'], tx_type, data.get('notes'),
                    data['resource_id'], data.get('assignment_id'),
                    user_id
                ))
                tid = cur.lastrowid

        return jsonify({'message': 'Transaction recorded', 'transaction_id': tid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_bp.route('/audit', methods=['GET'])
@role_required('ADMIN', 'COORDINATOR')
def audit_log():
    """Uses vw_inventory_audit view."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM vw_inventory_audit LIMIT 100')
                rows = cur.fetchall()
        return jsonify({'audit': rows}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

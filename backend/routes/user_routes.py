"""User management routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from config.database import get_db
from middleware.auth_middleware import role_required

user_bp = Blueprint('users', __name__)


@user_bp.route('', methods=['GET'])
@role_required('ADMIN')
def get_users():
    try:
        page   = int(request.args.get('page', 1))
        limit  = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        role   = request.args.get('role')

        where = 'WHERE u.role = %s' if role else ''
        params = [role] if role else []

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    SELECT u.user_id, u.full_name, u.email, u.phone,
                           u.role, u.is_active, u.created_at,
                           o.org_name
                    FROM `USER` u
                    LEFT JOIN ORGANIZATION o ON u.org_id = o.org_id
                    {where}
                    ORDER BY u.created_at DESC
                    LIMIT %s OFFSET %s
                ''', params + [limit, offset])
                rows = cur.fetchall()

                cur.execute(f'SELECT COUNT(*) AS total FROM `USER` u {where}', params)
                total = cur.fetchone()['total']

        return jsonify({'users': rows, 'total': total}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        verify_jwt_in_request()
        uid = get_jwt_identity()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT u.user_id, u.full_name, u.email, u.phone,
                           u.role, u.is_active, u.created_at, u.org_id,
                           o.org_name
                    FROM `USER` u
                    LEFT JOIN ORGANIZATION o ON u.org_id = o.org_id
                    WHERE u.user_id = %s
                ''', (uid,))
                user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user_bp.route('/profile', methods=['PUT'])
def update_profile():
    try:
        verify_jwt_in_request()
        uid  = get_jwt_identity()
        data = request.get_json()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE `USER`
                    SET full_name = COALESCE(%s, full_name),
                        phone     = COALESCE(%s, phone)
                    WHERE user_id = %s
                ''', (data.get('full_name'), data.get('phone'), uid))
        return jsonify({'message': 'Profile updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

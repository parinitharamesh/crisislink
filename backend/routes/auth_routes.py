"""Authentication routes – register and login."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
import bcrypt
from config.database import get_db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['full_name', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Field "{field}" is required'}), 400

    role = data.get('role', 'CITIZEN').upper()
    if role != 'CITIZEN':
        return jsonify({'error': 'Public registration is limited to CITIZEN accounts'}), 403

    # Hash password (bcrypt, 12 rounds)
    pwd_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt(12)).decode()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check email uniqueness
                cur.execute('SELECT user_id FROM `USER` WHERE email = %s', (data['email'],))
                if cur.fetchone():
                    return jsonify({'error': 'Email already registered'}), 409

                cur.execute(
                    '''INSERT INTO `USER`
                       (full_name, email, password_hash, phone, role, org_id)
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (data['full_name'], data['email'], pwd_hash,
                            data.get('phone'), role, None)
                )
                user_id = cur.lastrowid

        token = create_access_token(
            identity=str(user_id),
            additional_claims={'role': role, 'name': data['full_name']}
        )
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': {
                'user_id': user_id,
                'full_name': data['full_name'],
                'email': data['email'],
                'role': role,
                'org_id': None
            }
        }), 201

    except Exception as e:
        return jsonify({'error': 'Registration failed', 'detail': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''SELECT user_id, full_name, email, password_hash,
                              role, is_active, org_id
                       FROM `USER` WHERE email = %s''',
                    (data['email'],)
                )
                user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user['is_active']:
            return jsonify({'error': 'Account is deactivated'}), 403

        if not bcrypt.checkpw(data['password'].encode(), user['password_hash'].encode()):
            return jsonify({'error': 'Invalid email or password'}), 401

        token = create_access_token(
            identity=str(user['user_id']),
            additional_claims={
                'role':   user['role'],
                'name':   user['full_name'],
                'org_id': user['org_id']
            }
        )
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'user_id':   user['user_id'],
                'full_name': user['full_name'],
                'email':     user['email'],
                'role':      user['role'],
                'org_id':    user['org_id']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Login failed', 'detail': str(e)}), 500


@auth_bp.route('/me', methods=['GET'])
def me():
    from middleware.auth_middleware import jwt_required_custom, get_current_user_id
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        claims  = get_jwt()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT user_id, full_name, email, phone, role, org_id, created_at FROM `USER` WHERE user_id = %s',
                    (user_id,)
                )
                user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user}), 200
    except Exception as e:
        return jsonify({'error': 'Unauthorized', 'detail': str(e)}), 401

"""JWT authentication middleware."""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt


def jwt_required_custom(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({'error': 'Authentication required', 'detail': str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """Decorator: require one of the specified roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role', '')
                if user_role not in roles:
                    return jsonify({'error': f'Access denied. Required roles: {list(roles)}'}), 403
            except Exception as e:
                return jsonify({'error': 'Authentication required', 'detail': str(e)}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user_id():
    return get_jwt_identity()


def get_current_user_role():
    return get_jwt().get('role', '')

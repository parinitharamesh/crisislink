"""
CrisisLink – Disaster Response Coordination System
Flask Backend – Main Application Entry Point
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from dotenv import load_dotenv

# Load environment variables from repo root so local Windows runs work
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

def create_app():
    """Application factory."""
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────
    app.config['SECRET_KEY']             = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['JWT_SECRET_KEY']         = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False   # No expiry for dev; set timedelta in prod
    app.config['PROPAGATE_EXCEPTIONS']   = True

    # ── Extensions ─────────────────────────────────────────────────────────
    CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'],
         supports_credentials=True)
    JWTManager(app)

    @app.before_request
    def authenticate_api_request():
        if (
            not request.path.startswith('/api/')
            or request.method == 'OPTIONS'
            or request.endpoint is None
            or request.endpoint in {'auth.register', 'auth.login'}
        ):
            return None

        try:
            verify_jwt_in_request()
        except JWTExtendedException as exc:
            return {'error': 'Authentication required', 'detail': str(exc)}, 401

        return None

    # ── Register Blueprints ────────────────────────────────────────────────
    try:
        from .routes.auth_routes import auth_bp
        from .routes.user_routes import user_bp
        from .routes.request_routes import request_bp
        from .routes.incident_routes import incident_bp
        from .routes.resource_routes import resource_bp
        from .routes.shelter_routes import shelter_bp
        from .routes.assignment_routes import assignment_bp
        from .routes.inventory_routes import inventory_bp
        from .routes.dashboard_routes import dashboard_bp
        from .routes.org_routes import org_bp
    except ImportError:
        from routes.auth_routes import auth_bp
        from routes.user_routes import user_bp
        from routes.request_routes import request_bp
        from routes.incident_routes import incident_bp
        from routes.resource_routes import resource_bp
        from routes.shelter_routes import shelter_bp
        from routes.assignment_routes import assignment_bp
        from routes.inventory_routes import inventory_bp
        from routes.dashboard_routes import dashboard_bp
        from routes.org_routes import org_bp

    try:
        from .routes.mongodb_routes import mongo_bp
    except ImportError:
        try:
            from routes.mongodb_routes import mongo_bp
        except ImportError:
            mongo_bp = None

    try:
        from .routes.neo4j_routes import neo4j_bp
    except ImportError:
        try:
            from routes.neo4j_routes import neo4j_bp
        except ImportError:
            neo4j_bp = None

    try:
        from .routes.chroma_routes import chroma_bp
    except ImportError:
        try:
            from routes.chroma_routes import chroma_bp
        except ImportError:
            chroma_bp = None

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(user_bp,       url_prefix='/api/users')
    app.register_blueprint(request_bp,    url_prefix='/api/requests')
    app.register_blueprint(incident_bp,   url_prefix='/api/incidents')
    app.register_blueprint(resource_bp,   url_prefix='/api/resources')
    app.register_blueprint(shelter_bp,    url_prefix='/api/shelters')
    app.register_blueprint(assignment_bp, url_prefix='/api/assignments')
    app.register_blueprint(inventory_bp,  url_prefix='/api/inventory')
    if mongo_bp is not None:
        app.register_blueprint(mongo_bp, url_prefix='/api/mongo')
    if neo4j_bp is not None:
        app.register_blueprint(neo4j_bp, url_prefix='/api/graph')
    if chroma_bp is not None:
        app.register_blueprint(chroma_bp, url_prefix='/api/search')
    app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
    app.register_blueprint(org_bp,        url_prefix='/api/organizations')

    # ── Health check ───────────────────────────────────────────────────────
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'CrisisLink API'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('BACKEND_PORT', 5000)),
        debug=os.environ.get('FLASK_ENV', 'development') == 'development'
    )

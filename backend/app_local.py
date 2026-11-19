
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-dev-secret")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "local-dev-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

CORS(
    app,
    origins=["http://localhost:3000", "http://localhost:3001"],
    supports_credentials=True
)

JWTManager(app)

# Authentication
try:
    from .routes.auth_routes import auth_bp
    from .routes.org_routes import org_bp
    from .routes.resource_routes import resource_bp
    from .routes.request_routes import request_bp
    from .routes.incident_routes import incident_bp
    from .routes.assignment_routes import assignment_bp
    from .routes.shelter_routes import shelter_bp
    from .routes.inventory_routes import inventory_bp
    from .routes.user_routes import user_bp
    from .routes.dashboard_routes import dashboard_bp
except ImportError:
    from routes.auth_routes import auth_bp
    from routes.org_routes import org_bp
    from routes.resource_routes import resource_bp
    from routes.request_routes import request_bp
    from routes.incident_routes import incident_bp
    from routes.assignment_routes import assignment_bp
    from routes.shelter_routes import shelter_bp
    from routes.inventory_routes import inventory_bp
    from routes.user_routes import user_bp
    from routes.dashboard_routes import dashboard_bp

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

app.register_blueprint(auth_bp, url_prefix="/api/auth")

# Organizations and locations
app.register_blueprint(org_bp, url_prefix="/api/organizations")

# Resources and resource types
app.register_blueprint(resource_bp, url_prefix="/api/resources")

# Emergency requests
app.register_blueprint(request_bp, url_prefix="/api/requests")

# MySQL-backed coordination features
app.register_blueprint(incident_bp, url_prefix="/api/incidents")

app.register_blueprint(assignment_bp, url_prefix="/api/assignments")

app.register_blueprint(shelter_bp, url_prefix="/api/shelters")

app.register_blueprint(inventory_bp, url_prefix="/api/inventory")

app.register_blueprint(user_bp, url_prefix="/api/users")

# Dashboard
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")

if mongo_bp is not None:
    app.register_blueprint(mongo_bp, url_prefix="/api/mongo")
if neo4j_bp is not None:
    app.register_blueprint(neo4j_bp, url_prefix="/api/graph")
if chroma_bp is not None:
    app.register_blueprint(chroma_bp, url_prefix="/api/search")

@app.route("/health")
def health():
    return {"status": "ok", "service": "CrisisLink API"}, 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

import os
import re
from pathlib import Path

from flask import Flask, abort, request, send_file, send_from_directory
from flask_compress import Compress
from flask_cors import CORS

from config import CONFIG_MAP


_compress = Compress()


def create_app() -> Flask:
    env_name = os.environ.get("ACTIONHUB_ENV", "development")
    package_dir = Path(__file__).resolve().parent
    project_dir = package_dir.parent
    app = Flask(
        __name__,
        instance_relative_config=False,
        static_folder=str(project_dir / "static"),
    )
    app.config.from_object(CONFIG_MAP.get(env_name, CONFIG_MAP["development"]))

    # Re-read env-driven settings at app creation time so tests and scripts can override them dynamically.
    if os.environ.get("DATABASE"):
        app.config["DATABASE"] = os.environ["DATABASE"]
    if os.environ.get("JWT_SECRET_KEY"):
        app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
    if os.environ.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    if env_name == "production":
        runtime_secret = os.environ.get("SECRET_KEY", "")
        app.config["SECRET_KEY"] = runtime_secret
        if not runtime_secret:
            raise RuntimeError("SECRET_KEY is required when ACTIONHUB_ENV=production")

    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)

    _compress.init_app(app)

    # CORS for API endpoints (development - allow all origins)
    # In production, tighten this to specific origins
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

    # P1 — Cache-Control headers per asset path
    @app.after_request
    def set_cache_headers(response):
        path = request.path
        if path.startswith("/workflow/builder"):
            response.cache_control.no_store = True
            response.cache_control.max_age = 0
        elif path == "/static/js/drawflow_builder.js":
            response.cache_control.no_cache = True
            response.cache_control.max_age = 0
        if path.startswith("/static/vendor/"):
            response.cache_control.public = True
            response.cache_control.max_age = 31_536_000  # 1 year
            response.cache_control.immutable = True
        elif re.match(r"^/static/(css|js|img)/", path):
            response.cache_control.public = True
            response.cache_control.max_age = 86_400  # 1 day
        elif path.startswith("/api/"):
            response.cache_control.no_store = True
        elif response.mimetype == "text/html" and not path.startswith("/assets/"):
            response.cache_control.no_store = True
            response.cache_control.max_age = 0
        # Security headers (spec §17)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    from actionhub.middleware.db import close_db, init_app as init_db_app
    from actionhub.middleware.error_handlers import register_error_handlers
    from actionhub.auth.routes import auth_bp
    from actionhub.actions.routes import actions_bp
    from actionhub.dashboard.routes import dashboard_bp
    from actionhub.taxonomy.routes import taxonomy_bp
    from actionhub.export.routes import export_bp
    from actionhub.admin.routes import admin_bp
    from actionhub.gantt.routes import gantt_bp
    from actionhub.meetings.routes import meetings_bp
    from actionhub.notifications.routes import notifications_bp
    from actionhub.feedback.routes import feedback_bp
    from actionhub.evolution.routes import evolution_bp
    from actionhub.workflow.routes import workflow_bp
    from actionhub.i18n.routes import i18n_bp
    from actionhub.decisions.routes import decisions_bp

    init_db_app(app)
    register_error_handlers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(actions_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(taxonomy_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(gantt_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(evolution_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(i18n_bp)
    app.register_blueprint(decisions_bp)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "3.4"}

    # Serve Vite build assets (JS/CSS chunks)
    @app.route("/assets/<path:filename>")
    def serve_dist_assets(filename):
        return send_from_directory(
            os.path.join(app.static_folder, "dist", "assets"),
            filename
        )

    # Serve vite.svg from dist root
    @app.route("/vite.svg")
    def serve_vite_svg():
        return send_from_directory(os.path.join(app.static_folder, "dist"), "vite.svg")

    # SPA catch-all: serve React SPA for all non-API, non-asset routes
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        if path.startswith("api/"):
            abort(404)
        dist_path = os.path.join(app.static_folder, "dist", "index.html")
        if os.path.exists(dist_path):
            return send_from_directory(os.path.join(app.static_folder, "dist"), "index.html")
        return {"error": {"code": "SPA_BUILD_MISSING", "message": "Frontend build not found"}}, 503

    app.teardown_appcontext(close_db)
    return app

from flask import jsonify, request


def _is_api_request() -> bool:
    """Check if the current request is for an API endpoint."""
    return request.path.startswith("/api/")


def register_error_handlers(app) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": {"code": "BAD_REQUEST", "message": str(error)}}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": {"code": "UNAUTHORIZED", "message": str(error)}}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(error)}}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(error)}}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}), 500

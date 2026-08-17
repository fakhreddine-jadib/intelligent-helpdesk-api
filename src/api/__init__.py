"""Flask application factory."""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from src.config import CONFIG_BY_NAME


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure the Flask application."""
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    CORS(app, origins=app.config["CORS_ORIGINS"])

    from src.db import init_db
    init_db(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from src.api.routes.health import health_bp
    app.register_blueprint(health_bp, url_prefix="/api")

    from src.api.routes.predict import predict_bp
    app.register_blueprint(predict_bp, url_prefix="/api")

    from src.api.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api")

    from src.api.routes.tickets import tickets_bp
    app.register_blueprint(tickets_bp, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not_found",
                        "message": "Resource does not exist."}), 404

    @app.errorhandler(500)
    def server_error(_):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "internal_error",
                        "message": "An unexpected error occurred."}), 500

    app.logger.info("Application created in %s mode", config_name)
    return app
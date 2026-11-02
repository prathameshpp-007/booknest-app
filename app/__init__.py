import os
from flask import Flask
from app.catalog import BookCatalog


def create_app(test_config=None):
    """Application factory for BookNest."""
    app = Flask(__name__)

    # Default configuration
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "booknest-default-secret-key"),
        DATA_FILE=os.path.join(project_root, "data", "books.json"),
        APP_VERSION=os.environ.get("APP_VERSION", "1.0.0"),
    )

    if test_config:
        app.config.update(test_config)

    # Initialize thread-safe in-memory catalog
    app.catalog = BookCatalog(data_file=app.config.get("DATA_FILE"))

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    return app


import os
from datetime import datetime

from flask import Flask, session
from app.catalog import BookCatalog
from app.orders import OrderStore
from app.cart import load_cart, cart_count


def _format_currency(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _format_datetime(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%b %d, %Y %H:%M UTC")
    except (TypeError, ValueError):
        return value or ""


def create_app(test_config=None):
    """Application factory for BookNest."""
    app = Flask(__name__)

    # Default configuration
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "booknest-default-secret-key"),
        DATA_FILE=os.path.join(project_root, "data", "books.json"),
        ORDERS_FILE=os.path.join(project_root, "data", "orders.json"),
        APP_VERSION=os.environ.get("APP_VERSION", "1.0.0"),
    )

    if test_config:
        app.config.update(test_config)

    # Initialize thread-safe in-memory catalog
    app.catalog = BookCatalog(data_file=app.config.get("DATA_FILE"))

    # Initialize persistent order store
    app.orders = OrderStore(data_file=app.config.get("ORDERS_FILE"))

    app.add_template_filter(_format_currency, "currency")
    app.add_template_filter(_format_datetime, "datetime")

    # Expose the cart item count to every template (navigation badge)
    @app.context_processor
    def inject_globals():
        return {
            "cart_count": cart_count(load_cart(session)),
            "app_version": app.config.get("APP_VERSION", "1.0.0"),
        }

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    return app

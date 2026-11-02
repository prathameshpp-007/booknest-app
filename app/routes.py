from flask import Blueprint, current_app, jsonify, render_template, request

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Serves the main BookNest single-page web application."""
    app_version = current_app.config.get("APP_VERSION", "1.0.0")
    return render_template("index.html", app_version=app_version)


@bp.route("/health")
def health():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return jsonify({"status": "ok"}), 200


@bp.route("/api/books", methods=["GET"])
def get_books():
    """Returns a list of books filtered by search query 'q' and 'category'."""
    q = request.args.get("q", default="", type=str)
    category = request.args.get("category", default="", type=str)
    books = current_app.catalog.get_all(query=q, category=category)
    return jsonify(books), 200


@bp.route("/api/categories", methods=["GET"])
def get_categories():
    """Returns a list of all distinct book categories."""
    categories = current_app.catalog.get_categories()
    return jsonify(categories), 200


@bp.route("/api/books", methods=["POST"])
def add_book():
    """Adds a new book to the catalog from a JSON payload."""
    if not request.is_json:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format; expected an object"}), 400

    title = data.get("title")
    author = data.get("author")
    category = data.get("category")
    price = data.get("price")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "Field 'title' is required and cannot be empty"}), 400

    if not isinstance(author, str) or not author.strip():
        return jsonify({"error": "Field 'author' is required and cannot be empty"}), 400

    if not isinstance(category, str) or not category.strip():
        return jsonify({"error": "Field 'category' is required and cannot be empty"}), 400

    if price is None:
        return jsonify({"error": "Field 'price' is required"}), 400

    try:
        price_val = float(price)
        if price_val <= 0:
            return jsonify({"error": "Field 'price' must be a positive number greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Field 'price' must be a valid numeric value"}), 400

    new_book = current_app.catalog.add(
        title=title,
        author=author,
        category=category,
        price=price_val,
    )
    return jsonify(new_book), 201


@bp.route("/api/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id: int):
    """Deletes a book by ID. Returns 404 if not found."""
    deleted = current_app.catalog.delete(book_id)
    if not deleted:
        return jsonify({"error": f"Book with id {book_id} not found"}), 404
    return jsonify({"message": "Book deleted successfully", "id": book_id}), 200


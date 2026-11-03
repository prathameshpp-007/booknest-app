import re

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from app.cart import (
    MAX_QUANTITY,
    build_cart_summary,
    load_cart,
    save_cart,
)

bp = Blueprint("main", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@bp.route("/")
def index():
    """Serves the main BookNest single-page web application."""
    app_version = current_app.config.get("APP_VERSION", "1.0.0")
    return render_template("index.html", app_version=app_version)


@bp.route("/cart")
def cart_page():
    """Shopping cart page."""
    return render_template("cart.html")


@bp.route("/checkout")
def checkout_page():
    """Demo checkout page."""
    return render_template("checkout.html")


@bp.route("/orders")
def orders_page():
    """Order history page."""
    orders = current_app.orders.get_all()
    return render_template("orders.html", orders=orders)


@bp.route("/orders/<order_id>")
def order_detail_page(order_id: str):
    """Order confirmation / detail page."""
    order = current_app.orders.get_by_id(order_id)
    if not order:
        return render_template("order_not_found.html", order_id=order_id), 404
    is_confirmation = request.args.get("confirmed") == "1"
    return render_template(
        "order_confirmation.html", order=order, is_confirmation=is_confirmation
    )


@bp.route("/health")
def health():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Catalog API (existing functionality preserved)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Cart API
# ---------------------------------------------------------------------------
def _cart_response(cart=None, status=200):
    cart = cart if cart is not None else load_cart(session)
    summary, removed = build_cart_summary(current_app.catalog, cart)
    if removed:
        for book_id in removed:
            cart.pop(book_id, None)
        save_cart(session, cart)
        summary, _ = build_cart_summary(current_app.catalog, cart)
    return jsonify(summary), status


@bp.route("/api/cart", methods=["GET"])
def get_cart():
    """Returns the current cart with priced line items and totals."""
    return _cart_response()


@bp.route("/api/cart", methods=["POST"])
def add_to_cart():
    """Adds a book to the cart or increments its quantity."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON"}), 400

    book_id = data.get("book_id")
    try:
        book_id = int(book_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Field 'book_id' must be a valid integer"}), 400

    quantity = data.get("quantity", 1)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({"error": "Field 'quantity' must be a valid integer"}), 400

    if quantity < 1:
        return jsonify({"error": "Quantity must be at least 1"}), 400
    if quantity > MAX_QUANTITY:
        return jsonify({"error": f"Quantity cannot exceed {MAX_QUANTITY}"}), 400

    book = current_app.catalog.get_by_id(book_id)
    if not book:
        return jsonify({"error": f"Book with id {book_id} not found"}), 404

    cart = load_cart(session)
    key = str(book_id)
    cart[key] = min(cart.get(key, 0) + quantity, MAX_QUANTITY)
    save_cart(session, cart)
    return _cart_response(cart, status=201)


@bp.route("/api/cart/<int:book_id>", methods=["PATCH"])
def update_cart_item(book_id: int):
    """Sets the quantity for a cart item."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON"}), 400

    if "quantity" not in data:
        return jsonify({"error": "Field 'quantity' is required"}), 400

    try:
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"error": "Field 'quantity' must be a valid integer"}), 400

    if quantity < 1:
        return jsonify({"error": "Quantity must be at least 1. Use DELETE to remove an item."}), 400
    if quantity > MAX_QUANTITY:
        return jsonify({"error": f"Quantity cannot exceed {MAX_QUANTITY}"}), 400

    cart = load_cart(session)
    key = str(book_id)
    if key not in cart:
        return jsonify({"error": f"Book with id {book_id} is not in the cart"}), 404

    cart[key] = quantity
    save_cart(session, cart)
    return _cart_response(cart)


@bp.route("/api/cart/<int:book_id>", methods=["DELETE"])
def remove_cart_item(book_id: int):
    """Removes a single book from the cart."""
    cart = load_cart(session)
    key = str(book_id)
    if key not in cart:
        return jsonify({"error": f"Book with id {book_id} is not in the cart"}), 404
    cart.pop(key, None)
    save_cart(session, cart)
    return _cart_response(cart)


@bp.route("/api/cart", methods=["DELETE"])
def clear_cart():
    """Empties the cart."""
    save_cart(session, {})
    return _cart_response({})


# ---------------------------------------------------------------------------
# Checkout & Orders API
# ---------------------------------------------------------------------------
def _validate_customer(data):
    errors = {}

    name = data.get("name")
    if not isinstance(name, str) or len(name.strip()) < 2:
        errors["name"] = "Full name is required (at least 2 characters)."

    email = data.get("email")
    if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
        errors["email"] = "A valid email address is required."

    phone = data.get("phone")
    phone_digits = re.sub(r"\D", "", phone) if isinstance(phone, str) else ""
    if len(phone_digits) < 7 or len(phone_digits) > 15:
        errors["phone"] = "A valid phone number is required (7-15 digits)."

    address = data.get("address")
    if not isinstance(address, str) or len(address.strip()) < 5:
        errors["address"] = "Delivery address is required (at least 5 characters)."

    return errors


@bp.route("/api/checkout", methods=["POST"])
def checkout():
    """Creates a simulated (unpaid) demo order from the current cart."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON"}), 400

    errors = _validate_customer(data)
    if errors:
        return jsonify({"error": "Please fix the highlighted fields.", "fields": errors}), 400

    cart = load_cart(session)
    summary, removed = build_cart_summary(current_app.catalog, cart)
    if removed:
        for book_id in removed:
            cart.pop(book_id, None)
        save_cart(session, cart)

    if not summary["items"]:
        return jsonify({"error": "Your cart is empty. Add a book before checking out."}), 400

    customer = {
        "name": data["name"].strip(),
        "email": data["email"].strip(),
        "phone": data["phone"].strip(),
        "address": data["address"].strip(),
    }

    order = current_app.orders.create(
        customer=customer,
        items=summary["items"],
        subtotal=summary["subtotal"],
        total=summary["total"],
    )

    save_cart(session, {})

    return (
        jsonify(
            {
                "message": "Demo order created. No real payment was charged.",
                "order": order,
                "order_id": order["order_id"],
                "redirect_url": f"/orders/{order['order_id']}?confirmed=1",
            }
        ),
        201,
    )


@bp.route("/api/orders", methods=["GET"])
def get_orders():
    """Returns persisted order history, newest first."""
    return jsonify(current_app.orders.get_all()), 200


@bp.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id: str):
    order = current_app.orders.get_by_id(order_id)
    if not order:
        return jsonify({"error": f"Order {order_id} not found"}), 404
    return jsonify(order), 200

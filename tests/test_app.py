import pytest

from app import create_app


@pytest.fixture
def orders_file(tmp_path):
    """Isolated orders file so tests never touch the real data directory."""
    return str(tmp_path / "orders.json")


@pytest.fixture
def client(orders_file):
    """Test client fixture with fresh in-memory data for each test."""
    app = create_app({"TESTING": True, "ORDERS_FILE": orders_file})
    app.catalog.reload()
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """GET /health should return 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data == {"status": "ok"}


def test_index_page(client):
    """GET / should serve the HTML page containing the BookNest header and default version."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"BookNest" in response.data
    assert b"v1.0.0" in response.data


def test_index_page_custom_version():
    """GET / should display custom APP_VERSION if configured."""
    custom_app = create_app({"TESTING": True, "APP_VERSION": "2.4.0"})
    with custom_app.test_client() as c:
        response = c.get("/")
        assert response.status_code == 200
        assert b"v2.4.0" in response.data


def test_get_categories(client):
    """GET /api/categories should return a list of unique categories."""
    response = client.get("/api/categories")
    assert response.status_code == 200
    assert response.is_json
    categories = response.get_json()
    assert isinstance(categories, list)
    assert len(categories) >= 4
    assert "Software Engineering" in categories


def test_list_books(client):
    """GET /api/books should return all seeded books."""
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.is_json
    books = response.get_json()
    assert isinstance(books, list)
    assert len(books) >= 8
    first_book = books[0]
    assert "id" in first_book
    assert "title" in first_book
    assert "author" in first_book
    assert "category" in first_book
    assert "price" in first_book


def test_search_books_by_query(client):
    """GET /api/books?q=... should filter books matching title or author."""
    # Search by title keyword
    response = client.get("/api/books?q=Pragmatic")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 1
    assert "Pragmatic" in books[0]["title"]

    # Search by author keyword (case-insensitive)
    response = client.get("/api/books?q=martin")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) >= 1
    for b in books:
        assert "martin" in b["author"].lower() or "martin" in b["title"].lower()

    # Search non-matching query
    response = client.get("/api/books?q=NonExistentKeywordXYZ")
    assert response.status_code == 200
    assert response.get_json() == []


def test_search_books_by_category(client):
    """GET /api/books?category=... should filter books by category."""
    response = client.get("/api/books?category=Software+Engineering")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) > 0
    for b in books:
        assert b["category"] == "Software Engineering"


def test_search_books_combined_filters(client):
    """GET /api/books?q=...&category=... should filter by both criteria."""
    response = client.get("/api/books?q=Clean&category=Software+Engineering")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Clean Code"


def test_add_valid_book(client):
    """POST /api/books should create a new book and return 201."""
    new_book_payload = {
        "title": "Continuous Delivery",
        "author": "Jez Humble, David Farley",
        "category": "Cloud & DevOps",
        "price": 39.99,
    }
    response = client.post("/api/books", json=new_book_payload)
    assert response.status_code == 201
    assert response.is_json
    created = response.get_json()
    assert "id" in created
    assert created["title"] == new_book_payload["title"]
    assert created["author"] == new_book_payload["author"]
    assert created["category"] == new_book_payload["category"]
    assert created["price"] == 39.99

    # Verify it now appears in the book list
    list_res = client.get("/api/books")
    all_books = list_res.get_json()
    assert any(b["id"] == created["id"] for b in all_books)


def test_add_invalid_book_missing_fields(client):
    """POST /api/books with missing fields should return 400."""
    # Missing title
    res = client.post(
        "/api/books",
        json={"author": "Someone", "category": "Fiction", "price": 10.0},
    )
    assert res.status_code == 400
    assert "title" in res.get_json()["error"].lower()

    # Empty title
    res = client.post(
        "/api/books",
        json={"title": "  ", "author": "Someone", "category": "Fiction", "price": 10.0},
    )
    assert res.status_code == 400

    # Missing author
    res = client.post(
        "/api/books",
        json={"title": "A Book", "category": "Fiction", "price": 10.0},
    )
    assert res.status_code == 400
    assert "author" in res.get_json()["error"].lower()

    # Missing category
    res = client.post(
        "/api/books",
        json={"title": "A Book", "author": "Someone", "price": 10.0},
    )
    assert res.status_code == 400
    assert "category" in res.get_json()["error"].lower()

    # Missing price
    res = client.post(
        "/api/books",
        json={"title": "A Book", "author": "Someone", "category": "Fiction"},
    )
    assert res.status_code == 400
    assert "price" in res.get_json()["error"].lower()


def test_add_invalid_book_invalid_price(client):
    """POST /api/books with invalid price (negative, zero, string) should return 400."""
    # Negative price
    res = client.post(
        "/api/books",
        json={"title": "A Book", "author": "Author", "category": "Cat", "price": -5.0},
    )
    assert res.status_code == 400

    # Zero price
    res = client.post(
        "/api/books",
        json={"title": "A Book", "author": "Author", "category": "Cat", "price": 0},
    )
    assert res.status_code == 400

    # Non-numeric price
    res = client.post(
        "/api/books",
        json={"title": "A Book", "author": "Author", "category": "Cat", "price": "free"},
    )
    assert res.status_code == 400


def test_add_invalid_book_non_json(client):
    """POST /api/books with non-JSON payload should return 400."""
    res = client.post("/api/books", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_delete_book(client):
    """DELETE /api/books/<id> should remove book and return 200."""
    # Seed contains book with id=1
    response = client.delete("/api/books/1")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert "message" in data

    # Verify it is no longer in the list
    list_res = client.get("/api/books")
    ids = [b["id"] for b in list_res.get_json()]
    assert 1 not in ids


def test_delete_missing_book(client):
    """DELETE /api/books/<id> for non-existent ID should return 404."""
    response = client.delete("/api/books/99999")
    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()


# ===========================================================================
# Shopping cart, checkout and order management
# ===========================================================================
def test_cart_page_loads(client):
    """GET /cart should render the shopping cart page."""
    response = client.get("/cart")
    assert response.status_code == 200
    assert b"Your Cart" in response.data
    assert b"cart.js" in response.data


def test_checkout_page_loads(client):
    """GET /checkout should render the checkout page."""
    response = client.get("/checkout")
    assert response.status_code == 200
    assert b"Checkout" in response.data
    assert b"Demo checkout only" in response.data


def test_orders_page_loads_empty(client):
    """GET /orders should render the empty order history state."""
    response = client.get("/orders")
    assert response.status_code == 200
    assert b"My Orders" in response.data
    assert b"No orders yet" in response.data


def test_cart_starts_empty(client):
    """GET /api/cart should return an empty cart initially."""
    response = client.get("/api/cart")
    assert response.status_code == 200
    data = response.get_json()
    assert data["items"] == []
    assert data["count"] == 0
    assert data["subtotal"] == 0
    assert data["total"] == 0


def test_add_to_cart(client):
    """POST /api/cart should add a book and return calculated totals."""
    response = client.post("/api/cart", json={"book_id": 1, "quantity": 1})
    assert response.status_code == 201
    data = response.get_json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == 1
    assert data["items"][0]["title"] == "The Pragmatic Programmer"
    assert data["subtotal"] == 44.99
    assert data["total"] == 44.99


def test_add_to_cart_increments_quantity(client):
    """Adding the same book twice should increase its quantity."""
    client.post("/api/cart", json={"book_id": 1})
    response = client.post("/api/cart", json={"book_id": 1})
    assert response.status_code == 201
    data = response.get_json()
    assert data["count"] == 2
    assert data["items"][0]["quantity"] == 2
    assert data["total"] == 89.98


def test_add_multiple_books_cart_totals(client):
    """Cart subtotal should sum line totals across different books."""
    client.post("/api/cart", json={"book_id": 3, "quantity": 2})  # 37.50 x2
    response = client.post("/api/cart", json={"book_id": 6, "quantity": 1})  # 18.99
    data = response.get_json()
    assert data["count"] == 3
    assert data["subtotal"] == 93.99
    assert data["total"] == 93.99


def test_add_nonexistent_book_to_cart(client):
    """POST /api/cart with an unknown book should return 404."""
    response = client.post("/api/cart", json={"book_id": 99999})
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"].lower()


def test_add_to_cart_invalid_payload(client):
    """POST /api/cart should reject missing or invalid book_id/quantity."""
    assert client.post("/api/cart", json={}).status_code == 400
    assert client.post("/api/cart", json={"book_id": "abc"}).status_code == 400
    assert client.post("/api/cart", json={"book_id": 1, "quantity": 0}).status_code == 400
    assert client.post("/api/cart", json={"book_id": 1, "quantity": 500}).status_code == 400


def test_update_cart_quantity(client):
    """PATCH /api/cart/<id> should update quantity and totals."""
    client.post("/api/cart", json={"book_id": 1})
    response = client.patch("/api/cart/1", json={"quantity": 3})
    assert response.status_code == 200
    data = response.get_json()
    assert data["items"][0]["quantity"] == 3
    assert data["count"] == 3
    assert data["total"] == 134.97


def test_update_cart_quantity_validation(client):
    """PATCH /api/cart/<id> should reject invalid quantities and missing items."""
    client.post("/api/cart", json={"book_id": 1})
    assert client.patch("/api/cart/1", json={"quantity": 0}).status_code == 400
    assert client.patch("/api/cart/1", json={"quantity": "abc"}).status_code == 400
    assert client.patch("/api/cart/1", json={}).status_code == 400
    assert client.patch("/api/cart/2", json={"quantity": 2}).status_code == 404


def test_remove_cart_item(client):
    """DELETE /api/cart/<id> should remove a book from the cart."""
    client.post("/api/cart", json={"book_id": 1})
    client.post("/api/cart", json={"book_id": 2})
    response = client.delete("/api/cart/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["items"][0]["book_id"] == 2

    # Removing again should 404
    assert client.delete("/api/cart/1").status_code == 404


def test_clear_cart(client):
    """DELETE /api/cart should remove every item."""
    client.post("/api/cart", json={"book_id": 1})
    client.post("/api/cart", json={"book_id": 2})
    response = client.delete("/api/cart")
    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert client.get("/api/cart").get_json()["count"] == 0


def test_buy_now_flow_simulation(client):
    """Buy Now uses POST /api/cart then navigates to /checkout."""
    add_response = client.post("/api/cart", json={"book_id": 2, "quantity": 1})
    assert add_response.status_code == 201
    assert add_response.get_json()["count"] == 1

    checkout_page = client.get("/checkout")
    assert checkout_page.status_code == 200
    assert b"checkout.js" in checkout_page.data


def test_checkout_requires_cart(client):
    """POST /api/checkout with an empty cart should return 400."""
    response = client.post(
        "/api/checkout",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "5551234567",
            "address": "123 Book Street, Reading, CA 90210",
        },
    )
    assert response.status_code == 400
    assert "empty" in response.get_json()["error"].lower()


def test_checkout_validates_required_fields(client):
    """POST /api/checkout should report every missing required field."""
    client.post("/api/cart", json={"book_id": 1})
    response = client.post("/api/checkout", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert set(data["fields"].keys()) == {"name", "email", "phone", "address"}


def test_checkout_validates_email_and_phone(client):
    """POST /api/checkout should reject malformed email and phone values."""
    client.post("/api/cart", json={"book_id": 1})
    response = client.post(
        "/api/checkout",
        json={
            "name": "Jane Doe",
            "email": "not-an-email",
            "phone": "12",
            "address": "123 Book Street, Reading",
        },
    )
    assert response.status_code == 400
    fields = response.get_json()["fields"]
    assert "email" in fields
    assert "phone" in fields


def test_checkout_creates_order_and_clears_cart(client):
    """A valid checkout should persist an unpaid demo order and empty the cart."""
    client.post("/api/cart", json={"book_id": 1, "quantity": 2})
    client.post("/api/cart", json={"book_id": 6})

    response = client.post(
        "/api/checkout",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+1 555 123 4567",
            "address": "123 Book Street, Reading, CA 90210",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    order = data["order"]

    assert order["order_id"].startswith("BN-")
    assert order["status"] == "unpaid"
    assert order["payment"]["paid"] is False
    assert order["payment"]["provider"] == "demo"
    assert order["currency"] == "USD"
    assert order["customer"]["email"] == "jane@example.com"
    assert len(order["items"]) == 2
    assert order["total"] == 108.97
    assert "card" not in str(order).lower()
    assert "cvv" not in str(order).lower()
    assert data["redirect_url"].startswith(f"/orders/{order['order_id']}")

    # Cart is cleared after checkout
    assert client.get("/api/cart").get_json()["count"] == 0

    # Order appears in history
    history = client.get("/api/orders").get_json()
    assert len(history) == 1
    assert history[0]["order_id"] == order["order_id"]

    # Confirmation page renders
    page = client.get(f"/orders/{order['order_id']}?confirmed=1")
    assert page.status_code == 200
    assert order["order_id"].encode() in page.data
    assert b"Unpaid" in page.data


def test_order_ids_are_unique(client):
    """Each checkout should generate a distinct order ID."""
    customer = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "5551234567",
        "address": "123 Book Street, Reading",
    }
    ids = []
    for _ in range(3):
        client.post("/api/cart", json={"book_id": 1})
        response = client.post("/api/checkout", json=customer)
        assert response.status_code == 201
        ids.append(response.get_json()["order_id"])

    assert len(set(ids)) == 3


def test_order_not_found(client):
    """GET /orders/<unknown> and /api/orders/<unknown> should return 404."""
    assert client.get("/orders/BN-DOES-NOT-EXIST").status_code == 404
    assert client.get("/api/orders/BN-DOES-NOT-EXIST").status_code == 404


def test_orders_persist_across_app_restart(orders_file):
    """Orders written by one app instance should load in a new instance."""
    customer = {
        "name": "Persistent Reader",
        "email": "reader@example.com",
        "phone": "5559876543",
        "address": "42 Library Lane, Booktown",
    }

    first_app = create_app({"TESTING": True, "ORDERS_FILE": orders_file})
    with first_app.test_client() as c:
        c.post("/api/cart", json={"book_id": 5})
        created = c.post("/api/checkout", json=customer).get_json()["order"]

    second_app = create_app({"TESTING": True, "ORDERS_FILE": orders_file})
    with second_app.test_client() as c:
        history = c.get("/api/orders").get_json()
        assert len(history) == 1
        assert history[0]["order_id"] == created["order_id"]
        assert c.get(f"/api/orders/{created['order_id']}").status_code == 200


def test_checkout_removes_deleted_books_from_cart(client):
    """If a book is deleted from the catalog, checkout should drop it safely."""
    client.post("/api/cart", json={"book_id": 1})
    client.delete("/api/books/1")

    response = client.post(
        "/api/checkout",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "5551234567",
            "address": "123 Book Street, Reading",
        },
    )
    # The only cart item was deleted, so checkout should reject an empty cart.
    assert response.status_code == 400

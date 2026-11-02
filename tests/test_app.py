import pytest
from app import create_app


@pytest.fixture
def client():
    """Test client fixture with fresh in-memory data for each test."""
    app = create_app({"TESTING": True})
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

import json
import os
import threading
from typing import Dict, List, Optional


class BookCatalog:
    """Thread-safe in-memory book catalog seeded from a JSON file."""

    def __init__(self, data_file: Optional[str] = None):
        self._lock = threading.Lock()
        self.data_file = data_file
        self._books: List[Dict] = []
        self.reload()

    def reload(self) -> None:
        """Loads or reloads books from the seed data file."""
        with self._lock:
            if self.data_file and os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self._books = json.load(f)
            else:
                self._books = []

    def get_all(
        self, query: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict]:
        """Returns all books filtered by search query and category."""
        with self._lock:
            results = [dict(b) for b in self._books]

        if category and category.strip() and category.strip().lower() != "all":
            cat_lower = category.strip().lower()
            results = [
                b for b in results if b.get("category", "").strip().lower() == cat_lower
            ]

        if query and query.strip():
            q_lower = query.strip().lower()
            results = [
                b
                for b in results
                if q_lower in b.get("title", "").lower()
                or q_lower in b.get("author", "").lower()
            ]

        return results

    def get_by_id(self, book_id: int) -> Optional[Dict]:
        """Finds a single book by its ID."""
        with self._lock:
            for book in self._books:
                if book.get("id") == book_id:
                    return dict(book)
        return None

    def add(self, title: str, author: str, category: str, price: float) -> Dict:
        """Adds a new book with an auto-incremented ID."""
        with self._lock:
            max_id = max((b.get("id", 0) for b in self._books), default=0)
            new_id = max_id + 1
            new_book = {
                "id": new_id,
                "title": title.strip(),
                "author": author.strip(),
                "category": category.strip(),
                "price": round(float(price), 2),
            }
            self._books.append(new_book)
            return dict(new_book)

    def delete(self, book_id: int) -> bool:
        """Deletes a book by ID. Returns True if removed, False if not found."""
        with self._lock:
            for idx, book in enumerate(self._books):
                if book.get("id") == book_id:
                    del self._books[idx]
                    return True
        return False

    def get_categories(self) -> List[str]:
        """Returns a sorted list of unique categories currently present."""
        with self._lock:
            cats = {b.get("category", "").strip() for b in self._books if b.get("category")}
        return sorted(cats)


from typing import Dict, List, Optional, Tuple


MAX_QUANTITY = 99


def load_cart(session) -> Dict[str, int]:
    """Returns the cart from the session as {book_id_str: quantity}."""
    raw = session.get("cart")
    cart: Dict[str, int] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            try:
                book_id = int(key)
                quantity = int(value)
            except (TypeError, ValueError):
                continue
            if quantity > 0:
                cart[str(book_id)] = min(quantity, MAX_QUANTITY)
    return cart


def save_cart(session, cart: Dict[str, int]) -> None:
    session["cart"] = cart
    session.modified = True


def cart_count(cart: Dict[str, int]) -> int:
    return sum(cart.values())


def build_cart_summary(catalog, cart: Dict[str, int]) -> Tuple[Dict, List[str]]:
    """Builds a priced cart summary and a list of removed (missing) book ids."""
    items: List[Dict] = []
    removed: List[str] = []
    subtotal = 0.0

    for book_id_str, quantity in cart.items():
        book: Optional[Dict] = catalog.get_by_id(int(book_id_str))
        if not book:
            removed.append(book_id_str)
            continue
        price = float(book.get("price", 0))
        line_total = round(price * quantity, 2)
        subtotal += line_total
        items.append(
            {
                "book_id": book.get("id"),
                "title": book.get("title"),
                "author": book.get("author"),
                "category": book.get("category"),
                "price": round(price, 2),
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    subtotal = round(subtotal, 2)
    return (
        {
            "items": items,
            "subtotal": subtotal,
            "total": subtotal,
            "count": cart_count(cart),
            "currency": "USD",
        },
        removed,
    )

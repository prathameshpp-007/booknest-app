import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class OrderStore:
    """Thread-safe, file-backed order store.

    Orders are persisted as JSON so they survive application restarts. The
    store is intentionally simple to match BookNest's existing JSON storage
    architecture and can be swapped for a database later without changing the
    route contracts.
    """

    def __init__(self, data_file: Optional[str] = None):
        self._lock = threading.Lock()
        self.data_file = data_file
        self._orders: List[Dict] = []
        self.reload()

    def reload(self) -> None:
        """Loads orders from disk, starting empty when the file is absent."""
        with self._lock:
            self._orders = self._read_unlocked()

    def _read_unlocked(self) -> List[Dict]:
        if not self.data_file or not os.path.exists(self.data_file):
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_unlocked(self) -> None:
        if not self.data_file:
            return
        directory = os.path.dirname(self.data_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_file = f"{self.data_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._orders, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, self.data_file)

    def _generate_order_id_unlocked(self) -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        existing = {o.get("order_id") for o in self._orders}
        while True:
            candidate = f"BN-{date_part}-{uuid.uuid4().hex[:8].upper()}"
            if candidate not in existing:
                return candidate

    def create(self, customer: Dict, items: List[Dict], subtotal: float, total: float) -> Dict:
        """Persists a new unpaid demo order and returns it."""
        with self._lock:
            order = {
                "order_id": self._generate_order_id_unlocked(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "unpaid",
                "payment": {
                    "provider": "demo",
                    "method": "demo_checkout",
                    "status": "simulated",
                    "paid": False,
                    "label": "Demo order - no real payment was charged",
                },
                "currency": "USD",
                "customer": {
                    "name": customer["name"],
                    "email": customer["email"],
                    "phone": customer["phone"],
                    "address": customer["address"],
                },
                "items": items,
                "subtotal": round(subtotal, 2),
                "total": round(total, 2),
            }
            self._orders.append(order)
            self._write_unlocked()
            return json.loads(json.dumps(order))

    def get_all(self) -> List[Dict]:
        """Returns all orders, newest first."""
        with self._lock:
            orders = [json.loads(json.dumps(o)) for o in self._orders]
        return list(reversed(orders))

    def get_by_id(self, order_id: str) -> Optional[Dict]:
        with self._lock:
            for order in self._orders:
                if order.get("order_id") == order_id:
                    return json.loads(json.dumps(order))
        return None

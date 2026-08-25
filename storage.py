import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

# Thread‑safe in‑memory store for orders
_ORDER_LOCK = threading.Lock()
_ORDERS: Dict[str, Dict] = {}

# Optional persistence path – read from env var ORDERS_PERSIST_PATH
_PERSIST_PATH = os.getenv("ORDERS_PERSIST_PATH")

def _load_persisted_orders() -> None:
    """Load orders from JSON file if persistence is enabled."""
    if _PERSIST_PATH and os.path.isfile(_PERSIST_PATH):
        try:
            with open(_PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _ORDERS.update(data)
        except Exception as e:
            print(f"[storage] Failed to load persisted orders: {e}")

def _persist_orders() -> None:
    """Persist the current order dictionary to disk if enabled."""
    if _PERSIST_PATH:
        try:
            with open(_PERSIST_PATH, "w", encoding="utf-8") as f:
                json.dump(_ORDERS, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[storage] Failed to persist orders: {e}")

# Load persisted orders at import time
_load_persisted_orders()

def create_order(order_id: str, product_id: str, amount: float, customer_id: str) -> Dict:
    """Create a new order record.

    Args:
        order_id: Razorpay payment‑link identifier.
        product_id: Identifier from the product catalog.
        amount: Final price in INR.
        customer_id: Identifier for the buyer.
    Returns:
        The created order dictionary.
    """
    with _ORDER_LOCK:
        order = {
            "order_id": order_id,
            "product_id": product_id,
            "amount": amount,
            "customer_id": customer_id,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "paid_at": None,
        }
        _ORDERS[order_id] = order
        _persist_orders()
        return order

def update_order_status(order_id: str, status: str, paid_at: Optional[datetime] = None) -> None:
    """Update the status of an existing order.

    Args:
        order_id: Razorpay payment‑link identifier.
        status: New status (e.g., "paid", "failed").
        paid_at: Timestamp of payment capture, if applicable.
    """
    with _ORDER_LOCK:
        order = _ORDERS.get(order_id)
        if not order:
            raise KeyError(f"Order {order_id} not found")
        order["status"] = status
        if paid_at:
            order["paid_at"] = paid_at.isoformat()
        _persist_orders()

def get_order(order_id: str) -> Optional[Dict]:
    """Retrieve a single order by its ID."""
    return _ORDERS.get(order_id)

def get_all_orders() -> List[Dict]:
    """Return a list of all stored orders."""
    return list(_ORDERS.values())

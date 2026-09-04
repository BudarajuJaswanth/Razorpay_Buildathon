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

import supabase_db

# Load persisted orders from JSON or Supabase at import time
def _load_persisted_orders() -> None:
    """Load orders from JSON file and Supabase DB if available."""
    if _PERSIST_PATH and os.path.isfile(_PERSIST_PATH):
        try:
            with open(_PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _ORDERS.update(data)
        except Exception as e:
            print(f"[storage] Failed to load persisted orders: {e}")

    remote_orders = supabase_db.fetch_orders_from_supabase()
    if remote_orders:
        _ORDERS.update(remote_orders)

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

def create_order(
    order_id: str,
    product_id: str,
    amount: float,
    customer_id: str,
    shipping_address: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    is_subscription: bool = False
) -> Dict:
    """Create a new order record."""
    with _ORDER_LOCK:
        order = {
            "order_id": order_id,
            "product_id": product_id,
            "amount": amount,
            "customer_id": customer_id,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "paid_at": None,
            "shipping_address": shipping_address,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "is_subscription": is_subscription,
            "seller_payout": 0.0,
            "platform_fee": 0.0,
        }
        _ORDERS[order_id] = order
        _persist_orders()
        supabase_db.save_order_to_supabase(order)
        return order

def update_order_status(
    order_id: str,
    status: str,
    paid_at: Optional[datetime] = None,
    seller_payout: Optional[float] = None,
    platform_fee: Optional[float] = None,
    payment_id: Optional[str] = None,
    shipping_address: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None
) -> None:
    """Update the status of an existing order."""
    with _ORDER_LOCK:
        order = _ORDERS.get(order_id)
        if not order:
            raise KeyError(f"Order {order_id} not found")
        order["status"] = status
        if paid_at:
            order["paid_at"] = paid_at.isoformat()
        if seller_payout is not None:
            order["seller_payout"] = seller_payout
        if platform_fee is not None:
            order["platform_fee"] = platform_fee
        if payment_id is not None:
            order["payment_id"] = payment_id
        if shipping_address is not None:
            order["shipping_address"] = shipping_address
        if customer_name is not None:
            order["customer_name"] = customer_name
        if customer_phone is not None:
            order["customer_phone"] = customer_phone
        _persist_orders()
        supabase_db.save_order_to_supabase(order)

def get_order(order_id: str) -> Optional[Dict]:
    """Retrieve a single order by its ID."""
    return _ORDERS.get(order_id)

def get_all_orders() -> List[Dict]:
    """Return a list of all stored orders."""
    return list(_ORDERS.values())

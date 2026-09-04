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

_SUBSCRIPTIONS: Dict[str, Dict] = {}

def save_subscription(
    subscription_id: str,
    customer_email: str,
    customer_name: Optional[str] = None,
    plan_name: str = "KicksVault GrailPass VIP Club",
    amount: float = 299.0,
    status: str = "active",
    validity_days: int = 30,
    customer_phone: Optional[str] = None,
    shipping_address: Optional[str] = None
) -> Dict:
    """Save or update a customer VIP subscription record."""
    with _ORDER_LOCK:
        now = datetime.utcnow()
        valid_until = datetime.fromtimestamp(now.timestamp() + (validity_days * 86400))
        sub_record = {
            "subscription_id": subscription_id,
            "customer_email": (customer_email or "").strip().lower(),
            "customer_name": customer_name or customer_email.split('@')[0].capitalize(),
            "customer_phone": customer_phone or "+91 98765 43210",
            "shipping_address": shipping_address or "KicksVault VIP Member Hub, India",
            "plan_name": plan_name,
            "amount": amount,
            "billing_cycle": "Monthly",
            "status": status,
            "created_at": now.isoformat(),
            "valid_until": valid_until.isoformat(),
            "days_remaining": validity_days
        }
        _SUBSCRIPTIONS[subscription_id] = sub_record
        # Also map by email for fast lookup
        _SUBSCRIPTIONS[f"user:{sub_record['customer_email']}"] = sub_record
        return sub_record

def get_user_subscription(customer_email: str) -> Optional[Dict]:
    """Retrieve active subscription record for a specific user email."""
    if not customer_email:
        return None
    clean_email = customer_email.strip().lower()
    sub = _SUBSCRIPTIONS.get(f"user:{clean_email}")
    if sub:
        # Calculate dynamic remaining days
        try:
            valid_dt = datetime.fromisoformat(sub["valid_until"])
            remaining = (valid_dt - datetime.utcnow()).days
            sub["days_remaining"] = max(0, remaining)
        except Exception:
            pass
        return sub
    
    # Search in order history for subscription order
    for order in get_all_orders():
        if order.get("customer_id", "").strip().lower() == clean_email and (order.get("is_subscription") or order.get("product_id") == "grailpass_vip"):
            created_str = order.get("paid_at") or order.get("created_at") or datetime.utcnow().isoformat()
            try:
                created_dt = datetime.fromisoformat(created_str)
                valid_dt = datetime.fromtimestamp(created_dt.timestamp() + (30 * 86400))
            except Exception:
                valid_dt = datetime.fromtimestamp(datetime.utcnow().timestamp() + (30 * 86400))
            return {
                "subscription_id": order.get("order_id", "sub_vip_default"),
                "customer_email": clean_email,
                "customer_name": order.get("customer_name") or clean_email.split('@')[0].capitalize(),
                "plan_name": "KicksVault GrailPass VIP Club",
                "amount": order.get("amount", 299.0),
                "billing_cycle": "Monthly",
                "status": "active",
                "created_at": created_str,
                "valid_until": valid_dt.isoformat(),
                "days_remaining": max(0, (valid_dt - datetime.utcnow()).days)
            }
    return None

def get_all_subscriptions() -> List[Dict]:
    """Return all recorded VIP subscriptions for Admin HUD."""
    subs = []
    seen_ids = set()
    for key, sub in _SUBSCRIPTIONS.items():
        if not key.startswith("user:") and sub.get("subscription_id") not in seen_ids:
            seen_ids.add(sub["subscription_id"])
            subs.append(sub)
    
    # Also include any subscription orders from order ledger
    for order in get_all_orders():
        if (order.get("is_subscription") or order.get("product_id") == "grailpass_vip") and order.get("order_id") not in seen_ids:
            seen_ids.add(order["order_id"])
            created_str = order.get("paid_at") or order.get("created_at") or datetime.utcnow().isoformat()
            try:
                created_dt = datetime.fromisoformat(created_str)
                valid_dt = datetime.fromtimestamp(created_dt.timestamp() + (30 * 86400))
            except Exception:
                valid_dt = datetime.fromtimestamp(datetime.utcnow().timestamp() + (30 * 86400))
            subs.append({
                "subscription_id": order.get("order_id"),
                "customer_email": order.get("customer_id", "member@kicksvault.in"),
                "customer_name": order.get("customer_name") or "VIP Member",
                "customer_phone": order.get("customer_phone") or "+91 98765 43210",
                "shipping_address": order.get("shipping_address") or "KicksVault Hub",
                "plan_name": "KicksVault GrailPass VIP Club",
                "amount": order.get("amount", 299.0),
                "billing_cycle": "Monthly",
                "status": "active" if order.get("status") in ["paid", "created", "active"] else "expired",
                "created_at": created_str,
                "valid_until": valid_dt.isoformat(),
                "days_remaining": max(0, (valid_dt - datetime.utcnow()).days)
            })
    return subs

def get_order(order_id: str) -> Optional[Dict]:
    """Retrieve a single order by its ID."""
    return _ORDERS.get(order_id)

def get_all_orders() -> List[Dict]:
    """Return a list of all stored orders."""
    return list(_ORDERS.values())


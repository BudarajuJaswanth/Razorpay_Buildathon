import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Setup logging
logger = logging.getLogger("supabase_db")
logger.setLevel(logging.INFO)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/").replace("/rest/v1", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
DATABASE_URL: str = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""

_client = None
_is_supabase_available: bool = False
_db_status_message: str = "Uninitialized"

def get_client():
    """Returns the initialized Supabase client or None if unavailable."""
    global _client, _is_supabase_available, _db_status_message
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        _db_status_message = "Disabled: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing"
        logger.info(f"[Supabase] {_db_status_message}. Operating in local fallback mode.")
        _is_supabase_available = False
        return None

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        _is_supabase_available = True
        _db_status_message = "Connected to Supabase REST API"
        logger.info(f"[Supabase] Connected successfully to {SUPABASE_URL}")
        return _client
    except Exception as e:
        _is_supabase_available = False
        _db_status_message = f"Connection error: {str(e)}"
        logger.warning(f"[Supabase] Failed to initialize client ({e}). Operating in local fallback mode.")
        return None

def init_postgres_ddl_tables() -> bool:
    """Attempt direct PostgreSQL DDL execution if DATABASE_URL is available."""
    if not DATABASE_URL:
        logger.info("[Supabase] DATABASE_URL not set in env. Skipping direct Postgres DDL table execution.")
        return False

    try:
        import psycopg2
        logger.info("[Supabase] Executing DDL table self-bootstrapping via psycopg2...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cursor = conn.cursor()

        # Create Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                retail_price DOUBLE PRECISION NOT NULL,
                floor_price DOUBLE PRECISION NOT NULL,
                stock INTEGER NOT NULL DEFAULT 1,
                badge TEXT,
                image TEXT,
                brand TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Create Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                verified BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT TRUE,
                verification_token TEXT,
                avatar TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash TEXT;
            ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT TRUE;
            ALTER TABLE public.users ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT TRUE;
        """)

        # Create Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.orders (
                order_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                customer_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                paid_at TIMESTAMPTZ,
                shipping_address TEXT,
                customer_name TEXT,
                customer_phone TEXT,
                is_subscription BOOLEAN DEFAULT FALSE,
                seller_payout DOUBLE PRECISION DEFAULT 0.0,
                platform_fee DOUBLE PRECISION DEFAULT 0.0,
                payment_id TEXT
            );
        """)

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("[Supabase] PostgreSQL DDL tables successfully verified/created!")
        return True
    except Exception as e:
        logger.warning(f"[Supabase] Direct Postgres DDL initialization skipped ({e}).")
        return False

def seed_products_if_empty(catalog_dict: Dict[str, Dict]) -> bool:
    """Auto-seed initial 8 luxury sneaker items into Supabase 'products' table if empty."""
    client = get_client()
    if not client:
        return False

    try:
        res = client.table("products").select("id").execute()
        if res and res.data and len(res.data) > 0:
            logger.info(f"[Supabase] 'products' table already populated ({len(res.data)} items found).")
            return True

        logger.info(f"[Supabase] 'products' table is empty. Auto-seeding {len(catalog_dict)} luxury items...")
        items_to_insert = []
        for prod in catalog_dict.values():
            items_to_insert.append({
                "id": prod["id"],
                "name": prod["name"],
                "description": prod.get("description", ""),
                "retail_price": float(prod["retail_price"]),
                "floor_price": float(prod["floor_price"]),
                "stock": int(prod["stock"]),
                "badge": prod.get("badge", "Verified Authentic"),
                "image": prod.get("image", ""),
                "brand": prod.get("brand", "Jordan")
            })

        client.table("products").upsert(items_to_insert).execute()
        logger.info(f"[Supabase] Successfully seeded {len(items_to_insert)} luxury products into Supabase!")
        return True
    except Exception as e:
        logger.warning(f"[Supabase] Product seeding encountered notice ({e}). Operating in local memory mode.")
        return False

def sync_catalog_from_supabase(catalog_dict: Dict[str, Dict]) -> Dict[str, Dict]:
    """Fetch products from Supabase and merge with local catalog."""
    client = get_client()
    if not client:
        return catalog_dict

    try:
        res = client.table("products").select("*").execute()
        if res and res.data and len(res.data) > 0:
            for item in res.data:
                prod_id = item["id"]
                catalog_dict[prod_id] = {
                    "id": prod_id,
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "retail_price": float(item["retail_price"]),
                    "floor_price": float(item["floor_price"]),
                    "stock": int(item["stock"]),
                    "badge": item.get("badge", "Verified Authentic"),
                    "image": item.get("image", ""),
                    "brand": item.get("brand", "Jordan")
                }
            logger.info(f"[Supabase] Synced {len(res.data)} products into live catalog.")
    except Exception as e:
        logger.warning(f"[Supabase] Catalog sync notice ({e}). Using local catalog.")
    return catalog_dict

def save_product_to_supabase(product: Dict) -> bool:
    """Save or update a single product in Supabase."""
    client = get_client()
    if not client:
        return False

    try:
        item = {
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description", ""),
            "retail_price": float(product["retail_price"]),
            "floor_price": float(product["floor_price"]),
            "stock": int(product["stock"]),
            "badge": product.get("badge", "Verified Authentic"),
            "image": product.get("image", ""),
            "brand": product.get("brand", "Jordan")
        }
        client.table("products").upsert(item).execute()
        logger.info(f"[Supabase] Saved product '{product['id']}' to Supabase database.")
        return True
    except Exception as e:
        logger.warning(f"[Supabase] Failed to save product to Supabase ({e}). Local copy updated.")
        return False

def save_user_to_supabase(email: str, name: str, password_hash: str, role: str, verified: bool = True, verification_token: str = "", avatar: str = "") -> bool:
    """Save or update user account in Supabase 'users' table."""
    client = get_client()
    if not client:
        return False

    try:
        user_row = {
            "email": email.strip().lower(),
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "verified": verified,
            "is_verified": verified,
            "verification_token": verification_token,
            "avatar": avatar
        }
        client.table("users").upsert(user_row).execute()
        logger.info(f"[Supabase] Synced user '{email}' to Supabase users table.")
        return True
    except Exception as e:
        logger.warning(f"[Supabase] User sync notice ({e}). Saved locally.")
        return False

def fetch_users_from_supabase() -> Optional[Dict[str, Dict]]:
    """Fetch users from Supabase 'users' table."""
    client = get_client()
    if not client:
        return None

    try:
        res = client.table("users").select("*").execute()
        if res and res.data:
            users_map = {}
            for row in res.data:
                users_map[row["email"]] = {
                    "name": row["name"],
                    "password_hash": row.get("password_hash", ""),
                    "role": row.get("role", "user"),
                    "verified": row.get("verified", True),
                    "verification_token": row.get("verification_token", ""),
                    "avatar": row.get("avatar", "")
                }
            logger.info(f"[Supabase] Fetched {len(users_map)} users from Supabase.")
            return users_map
    except Exception as e:
        logger.warning(f"[Supabase] Users fetch notice ({e}).")
    return None

def save_order_to_supabase(order_data: Dict) -> bool:
    """Save or update order record in Supabase 'orders' table."""
    client = get_client()
    if not client:
        return False

    try:
        row = {
            "order_id": order_data["order_id"],
            "product_id": order_data["product_id"],
            "amount": float(order_data["amount"]),
            "customer_id": order_data["customer_id"],
            "status": order_data.get("status", "created"),
            "created_at": order_data.get("created_at") or datetime.utcnow().isoformat(),
            "paid_at": order_data.get("paid_at"),
            "shipping_address": order_data.get("shipping_address"),
            "customer_name": order_data.get("customer_name"),
            "customer_phone": order_data.get("customer_phone"),
            "is_subscription": order_data.get("is_subscription", False),
            "seller_payout": float(order_data.get("seller_payout", 0.0)),
            "platform_fee": float(order_data.get("platform_fee", 0.0)),
            "payment_id": order_data.get("payment_id")
        }
        client.table("orders").upsert(row).execute()
        logger.info(f"[Supabase] Synced order '{order_data['order_id']}' to Supabase orders table.")
        return True
    except Exception as e:
        logger.warning(f"[Supabase] Order sync notice ({e}). Saved locally.")
        return False

def fetch_orders_from_supabase() -> Optional[Dict[str, Dict]]:
    """Fetch all orders from Supabase 'orders' table."""
    client = get_client()
    if not client:
        return None

    try:
        res = client.table("orders").select("*").execute()
        if res and res.data:
            orders_map = {}
            for row in res.data:
                orders_map[row["order_id"]] = row
            logger.info(f"[Supabase] Fetched {len(orders_map)} orders from Supabase.")
            return orders_map
    except Exception as e:
        logger.warning(f"[Supabase] Orders fetch notice ({e}).")
    return None

def init_supabase_bootstrap(catalog_dict: Dict[str, Dict]) -> Dict[str, Any]:
    """Execute full self-bootstrapping lifecycle upon server startup."""
    logger.info("Initializing Autonomous Supabase Migration & Self-Bootstrapping...")

    # 1. Attempt PostgreSQL DDL Table Creation if DATABASE_URL present
    ddl_success = init_postgres_ddl_tables()

    # 2. Initialize Supabase client
    client = get_client()

    # 3. Auto-seed products if empty
    seed_success = False
    if client:
        seed_success = seed_products_if_empty(catalog_dict)
        # Sync live catalog from Supabase
        sync_catalog_from_supabase(catalog_dict)

    status = {
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY),
        "supabase_available": _is_supabase_available,
        "status_message": _db_status_message,
        "ddl_executed": ddl_success,
        "auto_seeded": seed_success,
        "product_count": len(catalog_dict)
    }
    logger.info(f"[Supabase Bootstrap Status] {status}")
    return status

def get_supabase_health() -> Dict[str, Any]:
    """Return health metrics and database status telemetry."""
    client = get_client()
    product_count = 0
    user_count = 0
    order_count = 0

    if client:
        try:
            p_res = client.table("products").select("id", count="exact").execute()
            product_count = len(p_res.data) if p_res.data else 0
        except Exception:
            pass

        try:
            u_res = client.table("users").select("email", count="exact").execute()
            user_count = len(u_res.data) if u_res.data else 0
        except Exception:
            pass

        try:
            o_res = client.table("orders").select("order_id", count="exact").execute()
            order_count = len(o_res.data) if o_res.data else 0
        except Exception:
            pass

    return {
        "status": "online" if _is_supabase_available else "local_fallback",
        "supabase_url": SUPABASE_URL,
        "is_available": _is_supabase_available,
        "message": _db_status_message,
        "metrics": {
            "products_in_db": product_count,
            "users_in_db": user_count,
            "orders_in_db": order_count
        }
    }

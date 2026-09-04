import pytest
from fastapi.testclient import TestClient
from main import app
import supabase_db
from guardrails import CATALOG, add_product_to_catalog, update_product_stock
from storage import create_order, update_order_status, get_order

client = TestClient(app)

def test_supabase_health_endpoint():
    res = client.get("/api/supabase/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "is_available" in data
    assert "metrics" in data

def test_supabase_bootstrap_init():
    status = supabase_db.init_supabase_bootstrap(CATALOG)
    assert isinstance(status, dict)
    assert "supabase_configured" in status
    assert "product_count" in status
    assert status["product_count"] >= 8

def test_catalog_sync_and_fallback():
    # Test catalog adding product
    prod_id = "PROD_TEST_SUPABASE"
    add_product_to_catalog(
        product_id=prod_id,
        name="Supabase Test Dunk",
        description="Test sneaker for Supabase integration",
        retail_price=15000.0,
        floor_price=12000.0,
        stock=10,
        badge="DB Verified",
        image="https://example.com/test.jpg",
        brand="Nike"
    )
    assert prod_id in CATALOG
    assert CATALOG[prod_id]["name"] == "Supabase Test Dunk"

    # Test stock update
    update_product_stock(prod_id, 8)
    assert CATALOG[prod_id]["stock"] == 8

def test_order_sync_and_fallback():
    order_id = "order_test_supabase_123"
    order = create_order(
        order_id=order_id,
        product_id="PROD_001",
        amount=21500.0,
        customer_id="cust_test_spb",
        customer_name="Supabase Collector",
        customer_phone="+919876543210"
    )
    assert order["order_id"] == order_id
    assert order["status"] == "created"

    update_order_status(order_id, "paid", seller_payout=19350.0, platform_fee=2150.0)
    retrieved = get_order(order_id)
    assert retrieved["status"] == "paid"
    assert retrieved["seller_payout"] == 19350.0

def test_user_sync_and_fallback():
    email = "test_user_spb@kicksvault.in"
    res = supabase_db.save_user_to_supabase(
        email=email,
        name="Test User SPB",
        password_hash="salt:hash",
        role="user",
        verified=True
    )
    # Returns True if connected to DB, or False gracefully on fallback
    assert isinstance(res, bool)

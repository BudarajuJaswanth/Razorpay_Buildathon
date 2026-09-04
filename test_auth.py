import time
import pytest
from fastapi.testclient import TestClient
from main import app
from auth import create_jwt_token, verify_jwt_token
import users

client = TestClient(app)

def test_jwt_create_and_verify():
    payload = {"user_id": "usr_test123", "email": "test@kicksvault.in", "role": "user"}
    token = create_jwt_token(payload, expires_in_seconds=3600)
    assert token is not None
    
    decoded = verify_jwt_token(token)
    assert decoded is not None
    assert decoded["user_id"] == "usr_test123"
    assert decoded["email"] == "test@kicksvault.in"
    assert decoded["role"] == "user"

def test_jwt_expired_token_rejected():
    payload = {"user_id": "usr_expired", "email": "expired@kicksvault.in", "role": "user"}
    token = create_jwt_token(payload, expires_in_seconds=-10)
    decoded = verify_jwt_token(token)
    assert decoded is None

def test_instant_registration_and_login():
    email = f"instant_user_{int(time.time())}@kicksvault.in"
    res = client.post("/api/auth/register", json={
        "name": "Instant Collector",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "token" in data
    assert data["role"] == "user"
    assert data["user"]["email"] == email

    # Test direct login with newly registered user
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert login_data["user"]["email"] == email

def test_admin_access_guardrail():
    payload = {
        "id": "PROD_TEST_AUTH",
        "name": "Test Sneaker Auth",
        "retail_price": 25000,
        "floor_price": 20000,
        "stock": 5,
        "image_url": "https://example.com/test.jpg",
        "brand": "Nike"
    }
    res = client.post("/api/admin/products", json=payload)
    assert res.status_code == 403

    user_token = create_jwt_token({"email": "collector@kicksvault.in", "role": "user"})
    res_user = client.post(
        "/api/admin/products", 
        json=payload, 
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res_user.status_code == 403

    admin_token = create_jwt_token({"email": "admin@kicksvault.in", "role": "admin"})
    res_admin = client.post(
        "/api/admin/products", 
        json=payload, 
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "created"

def test_google_login_invalid_credential_fails():
    res = client.post("/api/auth/google", json={"credential": "invalid_mock_credential_jwt"})
    assert res.status_code in [401, 500]

def test_jashubudaraju_admin_login():
    res = client.post("/api/auth/login", json={
        "email": "jashubudaraju@gmail.com",
        "password": "Jayaram@2006"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["role"] == "admin"
    assert data["user"]["email"] == "jashubudaraju@gmail.com"

def test_vip_subscription_endpoints():
    res = client.get("/api/user/subscription?email=jashubudaraju@gmail.com")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "subscription" in data

    admin_res = client.get("/api/admin/subscriptions")
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["status"] == "success"
    assert "subscriptions" in admin_data

def test_demo_login_endpoint_removed():
    res = client.post("/api/auth/demo-login", json={"role": "admin"})
    assert res.status_code in [404, 405]

import os
import json
import hmac
import hashlib
from datetime import datetime
from fastapi.testclient import TestClient

from main import app, DEV_AUTH_TOKEN

client = TestClient(app)

# Helper to compute signature for webhook payload

def compute_signature(secret: str, payload: dict) -> str:
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

# Load secret from env (fallback to default for test)
secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "default_secret")

# Sample order data for simulation

def sample_payload(order_id: str = "order_test_123", amount: float = 1000.0, product_id: str = "PROD_001", customer_id: str = "cust_test"):
    amount_paise = int(amount * 100)
    return {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": order_id,
                    "amount": amount_paise,
                    "amount_paid": amount_paise,
                    "currency": "INR",
                    "status": "paid",
                    "notes": {
                        "product_id": product_id,
                        "customer_id": customer_id,
                    },
                }
            }
        },
        "created_at": int(datetime.utcnow().timestamp()),
    }


def test_valid_webhook_updates_order():
    payload = sample_payload()
    signature = compute_signature(secret, payload)
    response = client.post("/api/webhook/razorpay", json=payload, headers={"X-Razorpay-Signature": signature})
    assert response.status_code == 200
    assert response.json().get("status") == "ok"
    # Verify order stored
    from storage import get_order
    order = get_order(payload["payload"]["payment_link"]["entity"]["id"])
    assert order is not None
    assert order["status"] == "paid"
    assert order["amount"] == payload["payload"]["payment_link"]["entity"]["amount_paid"] / 100


def test_invalid_signature_rejected():
    payload = sample_payload(order_id="order_bad_sig")
    bad_signature = "invalidsignature"
    response = client.post("/api/webhook/razorpay", json=payload, headers={"X-Razorpay-Signature": bad_signature})
    assert response.status_code == 400
    assert "Invalid Razorpay signature" in response.json().get("detail", "")


def test_missing_signature_rejected():
    payload = sample_payload(order_id="order_no_sig")
    response = client.post("/api/webhook/razorpay", json=payload)
    assert response.status_code == 400
    assert "Missing Razorpay signature" in response.json().get("detail", "")


def test_simulate_payment_endpoint_success():
    # Simulate payment via protected endpoint
    simulate_payload = {
        "order_id": "sim_order_001",
        "amount": 500.0,
        "product_id": "PROD_001",
        "customer_id": "cust_sim",
    }
    response = client.post(
        "/api/simulate-payment",
        json=simulate_payload,
        headers={"X-Dev-Token": DEV_AUTH_TOKEN},
    )
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp.get("status") == "simulated_ok"
    # Verify order created and marked paid
    from storage import get_order
    order = get_order(simulate_payload["order_id"])
    assert order is not None
    assert order["status"] == "paid"
    assert order["amount"] == simulate_payload["amount"]

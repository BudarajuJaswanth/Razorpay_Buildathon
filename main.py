import os
import json
import hmac
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Load environment variables
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

# Port configuration
PORT = int(os.getenv("PORT", 8000))

from storage import create_order, update_order_status, get_order, get_all_orders
from guardrails import CATALOG, get_catalog_summary
from agent import graph_app, AgentState, failure_recovery_node

app = FastAPI(title="KicksVault India — Razorpay Agentic Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# In-memory session store
_sessions: Dict[str, AgentState] = {}

# Last failed order tracking (for failure recovery workflow)
_last_failed: Dict[str, str] = {}  # session_id -> order_id

# Dev secret token for protected simulation endpoints
DEV_AUTH_TOKEN = os.getenv("DEV_AUTH_TOKEN", "dev-secret-token-razorpay-agentic-2026")

# ----- Pydantic models -----
class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    reply: str
    checkout_url: Optional[str] = None
    guardrail_triggered: bool = False
    agreed_price: Optional[float] = None
    negotiation_stage: int = 0
    product_id: Optional[str] = None

class SimulationRequest(BaseModel):
    order_id: str
    amount: float
    product_id: str = "PROD_001"
    customer_id: str = "cust_simulated"

class AgentTransactRequest(BaseModel):
    product_id: str
    proposed_price: float
    session_id: Optional[str] = None

class AgentTransactResponse(BaseModel):
    checkout_url: str
    agreed_price: float
    guardrail_triggered: bool
    order_id: str

# ----- Root -----
@app.get("/")
async def root_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "KicksVault India API is running. No static UI found."}

# ----- Chat Endpoint -----
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    state = _sessions.get(req.session_id)
    if not state:
        state = {
            "messages": [],
            "customer_id": f"cust_{req.session_id[-6:]}",
            "negotiation_stage": 0,
        }
        _sessions[req.session_id] = state

    # Check if there's a pending failure recovery for this session
    if _last_failed.get(req.session_id):
        state["failure_recovery"] = True
        state["order_id"] = _last_failed.pop(req.session_id)

    state.setdefault("messages", []).append(HumanMessage(content=req.message))

    # If failure recovery is flagged, run recovery node before sales
    if state.get("failure_recovery"):
        state = failure_recovery_node(state)
        _sessions[req.session_id] = state
        ai_msg = state["messages"][-1]
        return ChatResponse(
            reply=ai_msg.content,
            checkout_url=state.get("checkout_url"),
            guardrail_triggered=state.get("guardrail_triggered", False),
            agreed_price=state.get("agreed_price"),
            negotiation_stage=state.get("negotiation_stage", 0),
            product_id=state.get("product_id"),
        )

    state = graph_app.invoke(state)
    _sessions[req.session_id] = state

    ai_msg: BaseMessage = state["messages"][-1]
    if not isinstance(ai_msg, AIMessage):
        raise HTTPException(status_code=500, detail="Agent did not return an AIMessage")
    return ChatResponse(
        reply=ai_msg.content,
        checkout_url=state.get("checkout_url"),
        guardrail_triggered=state.get("guardrail_triggered", False),
        agreed_price=state.get("agreed_price"),
        negotiation_stage=state.get("negotiation_stage", 0),
        product_id=state.get("product_id"),
    )

# ----- Session Reset -----
@app.post("/api/reset-session")
async def reset_session(req: ChatRequest):
    if req.session_id in _sessions:
        del _sessions[req.session_id]
    return {"status": "reset", "session_id": req.session_id}

# ----- A2A Catalog Endpoint -----
@app.get("/api/agent/catalog")
async def a2a_catalog(agent_auth: Optional[str] = Header(None, alias="X-Agent-Auth")):
    return CATALOG

# ----- A2A Transaction Endpoint -----
@app.post("/api/agent/transact", response_model=AgentTransactResponse)
async def a2a_transact(req: AgentTransactRequest, agent_auth: Optional[str] = Header(None, alias="X-Agent-Auth")):
    from guardrails import PaymentProposal
    try:
        proposal = PaymentProposal(product_id=req.product_id, proposed_price=req.proposed_price)
        final_price = proposal.validate_and_compute_final_price()
        guardrail = final_price != req.proposed_price
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    order_id = f"order_{int(datetime.utcnow().timestamp())}_{req.product_id}"
    create_order(order_id, req.product_id, final_price, "external_agent")
    checkout_url = f"https://checkout.razorpay.com/v1/checkout?order_id={order_id}"

    return AgentTransactResponse(
        checkout_url=checkout_url,
        agreed_price=final_price,
        guardrail_triggered=guardrail,
        order_id=order_id,
    )

# ----- Webhook Endpoint -----
@app.post("/api/webhook/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay signature")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
    order_id = entity.get("id")
    amount = entity.get("amount_paid", 0) / 100
    notes = entity.get("notes", {})
    product_id = notes.get("product_id", "PROD_001")
    customer_id = notes.get("customer_id", "unknown_buyer")

    if event == "payment_link.paid":
        if get_order(order_id):
            update_order_status(order_id, "paid", datetime.utcnow())
        else:
            create_order(order_id, product_id, amount, customer_id)
            update_order_status(order_id, "paid", datetime.utcnow())
    elif event == "payment_link.failed":
        failure_reason = notes.get("reason", "unknown")
        if get_order(order_id):
            update_order_status(order_id, "failed", datetime.utcnow())
        else:
            create_order(order_id, product_id, amount, customer_id)
            update_order_status(order_id, "failed", datetime.utcnow())
        # Flag for session-based recovery
        for sess_id, sess in _sessions.items():
            if sess.get("customer_id") == customer_id:
                _last_failed[sess_id] = order_id
                break
    else:
        raise HTTPException(status_code=400, detail="Unsupported event type")
    return JSONResponse(content={"status": "ok"})

# ----- Simulate Payment Endpoint (dev protected) -----
@app.post("/api/simulate-payment")
async def simulate_payment(req: SimulationRequest, x_dev_token: Optional[str] = Header(None, alias="X-Dev-Token")):
    if x_dev_token != DEV_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid or missing X-Dev-Token header")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "default_secret")
    amount_paise = int(req.amount * 100)
    payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": req.order_id,
                    "amount": amount_paise,
                    "amount_paid": amount_paise,
                    "currency": "INR",
                    "status": "paid",
                    "notes": {
                        "product_id": req.product_id,
                        "customer_id": req.customer_id,
                    },
                }
            }
        },
        "created_at": int(datetime.utcnow().timestamp()),
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    computed_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if get_order(req.order_id):
        update_order_status(req.order_id, "paid", datetime.utcnow())
    else:
        create_order(req.order_id, req.product_id, req.amount, req.customer_id)
        update_order_status(req.order_id, "paid", datetime.utcnow())
    return {
        "status": "simulated_ok",
        "verified_hmac": computed_sig,
        "order_id": req.order_id,
        "amount": req.amount,
        "event": "payment_link.paid",
        "payload_preview": payload,
    }

# ----- Simulate Failure Endpoint (dev protected) -----
@app.post("/api/simulate-failure")
async def simulate_failure(req: SimulationRequest, x_dev_token: Optional[str] = Header(None, alias="X-Dev-Token")):
    if x_dev_token != DEV_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid or missing X-Dev-Token header")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "default_secret")
    amount_paise = int(req.amount * 100)
    payload = {
        "event": "payment_link.failed",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": req.order_id,
                    "amount": amount_paise,
                    "amount_paid": 0,
                    "currency": "INR",
                    "status": "failed",
                    "notes": {
                        "product_id": req.product_id,
                        "customer_id": req.customer_id,
                        "reason": "bank_transaction_timeout",
                        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    },
                }
            }
        },
        "created_at": int(datetime.utcnow().timestamp()),
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    computed_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if get_order(req.order_id):
        update_order_status(req.order_id, "failed", datetime.utcnow())
    else:
        create_order(req.order_id, req.product_id, req.amount, req.customer_id)
        update_order_status(req.order_id, "failed", datetime.utcnow())
    # Flag recovery for any session matching customer_id
    for sess_id, sess in _sessions.items():
        if sess.get("customer_id") == req.customer_id:
            _last_failed[sess_id] = req.order_id
            break
    return {
        "status": "simulated_failure",
        "verified_hmac": computed_sig,
        "order_id": req.order_id,
        "failure_metadata": {
            "reason": "bank_transaction_timeout",
            "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
            "session_id": req.customer_id,
        },
        "payload_preview": payload,
    }

# ----- Last Failed Order Endpoint -----
@app.get("/api/last-failed-order")
async def last_failed_order(session_id: str):
    order_id = _last_failed.get(session_id)
    if order_id:
        return {"order_id": order_id, "has_failure": True}
    return {"order_id": None, "has_failure": False}

# ----- Orders Endpoint -----
@app.get("/api/orders")
async def list_orders() -> List[Dict]:
    return get_all_orders()

# ----- Catalog Endpoint -----
@app.get("/api/catalog")
async def get_catalog() -> Dict:
    return CATALOG

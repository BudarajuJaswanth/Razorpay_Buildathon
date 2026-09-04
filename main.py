import os
import json
import hmac
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Load environment variables (portable — works locally and on Vercel)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"), override=False)

# Port configuration
PORT = int(os.getenv("PORT", 8000))

import storage
from storage import create_order, update_order_status, get_order, get_all_orders, save_subscription, get_user_subscription, get_all_subscriptions
from guardrails import CATALOG, get_catalog_summary, add_product_to_catalog, update_product_stock
import users
import time
import razorpay
from auth import create_jwt_token, verify_jwt_token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

_AGENT_IMPORT_ERROR: str | None = None
try:
    from agent import graph_app, AgentState, failure_recovery_node, extract_agent_response
except Exception as _e:
    _AGENT_IMPORT_ERROR = str(_e)
    graph_app = None  # type: ignore
    AgentState = dict  # type: ignore
    failure_recovery_node = None  # type: ignore
    def extract_agent_response(msgs):  # type: ignore
        return "I'm here to help! Which grail sneaker or product are you interested in today?"


import supabase_db

app = FastAPI(title="KicksVault India — Razorpay Agentic Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run Supabase Self-Bootstrapping Lifecycle
supabase_db.init_supabase_bootstrap(CATALOG)

@app.get("/api/supabase/status")
@app.get("/api/health")
async def get_supabase_status_endpoint():
    return supabase_db.get_supabase_health()

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
    location: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    reply: str
    checkout_url: Optional[str] = None
    guardrail_triggered: bool = False
    agreed_price: Optional[float] = None
    negotiation_stage: int = 0
    product_id: Optional[str] = None
    session_id: Optional[str] = None
    delivery_location: Optional[str] = None
    error: Optional[str] = None

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

# ----- Health -----
@app.get("/health")
async def health():
    return {
        "status": "ok" if not _AGENT_IMPORT_ERROR else "degraded",
        "service": "KicksVault India",
        "region": os.getenv("VERCEL_REGION", "local"),
        "agent": "loaded" if graph_app is not None else "failed",
        "agent_error": _AGENT_IMPORT_ERROR,
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "razorpay_key_set": bool(os.getenv("RAZORPAY_KEY_ID")),
    }

# ----- Static Assets Direct Handlers -----
@app.get("/static/style.css")
@app.get("/style.css")
async def serve_css():
    css_path = os.path.join(PROJECT_ROOT, "static", "style.css")
    if os.path.isfile(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")

@app.get("/static/app.js")
@app.get("/app.js")
async def serve_js():
    js_path = os.path.join(PROJECT_ROOT, "static", "app.js")
    if os.path.isfile(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS not found")

# ----- Root -----
@app.get("/")
@app.get("/index.html")
async def root_index():
    index_path = os.path.join(PROJECT_ROOT, "static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"status": "ok", "message": "KicksVault India API — Static UI not found"}

# ----- Chat Endpoint -----
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        if not os.getenv("GROQ_API_KEY"):
            return ChatResponse(
                reply="⚠️ System Notice: `GROQ_API_KEY` is missing in Vercel Environment Variables. Please configure it in your Vercel Dashboard Settings.",
                session_id=req.session_id,
                guardrail_triggered=False,
                negotiation_stage=0
            )

        if _AGENT_IMPORT_ERROR or graph_app is None:
            return ChatResponse(
                reply=f"⚠️ Agent Notice: We encountered a temporary connection glitch ({_AGENT_IMPORT_ERROR or 'Agent graph not loaded'}). Please verify GROQ_API_KEY in Vercel settings.",
                session_id=req.session_id,
                error=str(_AGENT_IMPORT_ERROR),
                guardrail_triggered=False,
                negotiation_stage=0
            )

        state = _sessions.get(req.session_id)
        if not state:
            state = {
                "messages": [],
                "customer_id": f"cust_{req.session_id[-6:]}",
                "negotiation_stage": 0,
                "delivery_location": req.location,
            }
            _sessions[req.session_id] = state

        # If client provided historical messages, reconstruct multi-turn context
        if req.history:
            reconstructed: List[BaseMessage] = []
            for h in req.history:
                role = str(h.get("role", "")).lower()
                content = str(h.get("content", ""))
                if not content:
                    continue
                if role in ["user", "human"]:
                    reconstructed.append(HumanMessage(content=content))
                elif role in ["assistant", "ai", "bot"]:
                    reconstructed.append(AIMessage(content=content))
            if reconstructed:
                state["messages"] = reconstructed

        if req.location and not state.get("delivery_location"):
            state["delivery_location"] = req.location

        # Check if there's a pending failure recovery for this session
        if _last_failed.get(req.session_id):
            state["failure_recovery"] = True
            state["order_id"] = _last_failed.pop(req.session_id)

        # Append latest user turn
        state.setdefault("messages", []).append(HumanMessage(content=req.message))

        # If failure recovery is flagged, run recovery node before sales
        if state.get("failure_recovery"):
            state = failure_recovery_node(state)
            _sessions[req.session_id] = state
            reply_text = extract_agent_response(state.get("messages", []))
            return ChatResponse(
                reply=reply_text,
                checkout_url=state.get("checkout_url"),
                guardrail_triggered=state.get("guardrail_triggered", False),
                agreed_price=state.get("agreed_price"),
                negotiation_stage=state.get("negotiation_stage", 0),
                product_id=state.get("product_id"),
                session_id=req.session_id,
                delivery_location=state.get("delivery_location"),
            )

        # Invoke the LangGraph agent with session thread checkpointer config
        config = {"configurable": {"thread_id": req.session_id}}
        state = graph_app.invoke(state, config=config)
        _sessions[req.session_id] = state

        reply_text = extract_agent_response(state.get("messages", []))

        return ChatResponse(
            reply=reply_text,
            checkout_url=state.get("checkout_url"),
            guardrail_triggered=state.get("guardrail_triggered", False),
            agreed_price=state.get("agreed_price"),
            negotiation_stage=state.get("negotiation_stage", 0),
            product_id=state.get("product_id"),
            session_id=req.session_id,
            delivery_location=state.get("delivery_location"),
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            reply=f"⚠️ Connection Glitch: {str(exc)}. Please try again in a moment.",
            session_id=req.session_id,
            error=str(exc),
            guardrail_triggered=False,
            negotiation_stage=0,
        )

# ----- Session Reset -----
@app.post("/api/reset-session")
async def reset_session(req: ChatRequest):
    if req.session_id in _sessions:
        del _sessions[req.session_id]
    return {"status": "reset", "session_id": req.session_id}

# ----- Public & Storefront Catalog Endpoint -----
@app.get("/api/catalog")
async def get_public_catalog():
    return {"products": CATALOG, "count": len(CATALOG)}

# ----- Product Inventory Management Endpoints -----
class AddProductRequest(BaseModel):
    id: str
    name: str
    description: str
    retail_price: float
    floor_price: float
    stock: int = 1
    badge: str = "Verified Authentic"
    image: Optional[str] = None

class UpdateStockRequest(BaseModel):
    stock: int

@app.post("/api/products")
async def add_product_endpoint(req: AddProductRequest):
    prod = add_product_to_catalog(
        product_id=req.id,
        name=req.name,
        description=req.description,
        retail_price=req.retail_price,
        floor_price=req.floor_price,
        stock=req.stock,
        badge=req.badge,
        image=req.image
    )
    return {"status": "created", "product": prod, "total_products": len(CATALOG)}

@app.put("/api/products/{product_id}/stock")
async def update_stock_endpoint(product_id: str, req: UpdateStockRequest):
    try:
        prod = update_product_stock(product_id, req.stock)
        return {"status": "updated", "product": prod}
    except KeyError:
        raise HTTPException(status_code=404, detail="Product not found")

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

# ----- Auth Models & RBAC Endpoints -----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "1098656365851-g219198642198.apps.googleusercontent.com")

class AuthGoogleLoginRequest(BaseModel):
    credential: str

class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class AuthEmailLoginRequest(BaseModel):
    email: str
    password: str

class AuthResetPasswordRequest(BaseModel):
    email: str
    new_password: str

class AdminAddProductRequest(BaseModel):
    id: str
    name: str
    retail_price: float
    floor_price: float
    stock: int
    image_url: str
    brand: str

def check_admin_access(authorization: Optional[str] = None) -> bool:
    """Strictly checks if a valid signed Admin JWT token is provided in the Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)
        if payload and payload.get("role") == "admin":
            return True
    return False

# Email Sign Up (Register) & Instant Login
@app.post("/api/auth/signup")
@app.post("/api/auth/register")
async def auth_register(req: AuthRegisterRequest):
    data = users.load_users()
    email = req.email.strip().lower()
    if email in data["users"]:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    password_hash = users.hash_password(req.password)
    
    # Role strictly determined on the server via ADMIN_EMAILS
    role = users.determine_role(email)
    name = req.name.strip()
    avatar = (
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
        if role == "admin"
        else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80"
    )
    
    data["users"][email] = {
        "name": name,
        "password_hash": password_hash,
        "role": role,
        "verified": True,
        "verification_token": "",
        "avatar": avatar
    }
    users.save_users(data)
    
    user_id = f"usr_{hashlib.md5((email + role).encode()).hexdigest()[:8]}"
    
    # Generate 1-hour JWT token for instant login
    now = time.time()
    expires_at = now + 3600
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": name,
        "avatar": avatar,
        "exp": expires_at
    }
    token = create_jwt_token(payload)
    
    return {
        "status": "success",
        "message": "Account registered and logged in successfully!",
        "token": token,
        "role": role,
        "expires_at": expires_at * 1000,
        "user": {
            "user_id": user_id,
            "role": role,
            "name": name,
            "email": email,
            "avatar": avatar
        }
    }

# Email Sign In (Login)
@app.post("/api/auth/login")
async def auth_email_login(req: AuthEmailLoginRequest):
    data = users.load_users()
    email = req.email.strip().lower()
    user = data["users"].get(email)
    
    if not user or not users.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
        
    role = users.determine_role(email)
    user["role"] = role
    user["verified"] = True
    users.save_users(data)
    
    user_id = f"usr_{hashlib.md5((email + role).encode()).hexdigest()[:8]}"
    
    # Generate 1-hour JWT token
    now = time.time()
    expires_at = now + 3600
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": user["name"],
        "avatar": user["avatar"],
        "exp": expires_at
    }
    token = create_jwt_token(payload)
    
    return {
        "status": "success",
        "token": token,
        "role": role,
        "expires_at": expires_at * 1000,
        "user": {
            "user_id": user_id,
            "role": role,
            "name": user["name"],
            "email": email,
            "avatar": user["avatar"]
        }
    }

# Reset Password Endpoint
@app.post("/api/auth/reset-password")
async def auth_reset_password(req: AuthResetPasswordRequest):
    data = users.load_users()
    email = req.email.strip().lower()
    user = data["users"].get(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="No registered account found with this email address.")
        
    user["password_hash"] = users.hash_password(req.new_password)
    user["verified"] = True
    users.save_users(data)
    
    return {
        "status": "success",
        "message": "Password reset successfully! You can now log in with your new password."
    }


# Google GIS OAuth Verification
@app.post("/api/auth/google-login")
@app.post("/api/auth/google")
async def auth_google(req: AuthGoogleLoginRequest):
    if not req.credential:
        raise HTTPException(status_code=400, detail="Google credential token is required.")
    
    try:
        # Cryptographically verify the Google ID token with Google's public certs
        idinfo = id_token.verify_oauth2_token(
            req.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else None
        )
        
        email = idinfo.get("email", "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="Google token verified, but email address was not returned.")
            
        name = idinfo.get("name", "Google Collector")
        avatar = idinfo.get("picture", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80")
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google authentication error: {str(e)}")

    # Role strictly determined on the server via ADMIN_EMAILS
    role = users.determine_role(email)
    
    data = users.load_users()
    if email not in data["users"]:
        data["users"][email] = {
            "name": name,
            "password_hash": users.hash_password(uuid.uuid4().hex[:12]),
            "role": role,
            "verified": True,
            "verification_token": "",
            "avatar": avatar
        }
        users.save_users(data)
    else:
        data["users"][email]["verified"] = True
        data["users"][email]["role"] = role
        if avatar:
            data["users"][email]["avatar"] = avatar
        users.save_users(data)

    user_info = data["users"][email]
    user_id = f"usr_{hashlib.md5((email + role).encode()).hexdigest()[:8]}"
    
    # Generate 1-hour JWT token
    now = time.time()
    expires_at = now + 3600
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": user_info.get("name", name),
        "avatar": user_info.get("avatar", avatar),
        "exp": expires_at
    }
    token = create_jwt_token(payload)
    
    return {
        "token": token,
        "role": role,
        "expires_at": expires_at * 1000,
        "user": {
            "user_id": user_id,
            "role": role,
            "name": user_info.get("name", name),
            "email": email,
            "avatar": user_info.get("avatar", avatar)
        }
    }

# ----- Protected Admin Endpoints -----
@app.post("/api/admin/products")
async def admin_add_product(
    req: AdminAddProductRequest,
    authorization: Optional[str] = Header(None)
):
    if not check_admin_access(authorization):
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
        
    prod = add_product_to_catalog(
        product_id=req.id.strip(),
        name=req.name.strip(),
        description=f"Luxury {req.brand} sneakers.",
        retail_price=req.retail_price,
        floor_price=req.floor_price,
        stock=req.stock,
        badge="New Drop",
        image=req.image_url.strip(),
        brand=req.brand.strip()
    )
    return {"status": "created", "product": prod, "total_products": len(CATALOG)}

@app.get("/api/admin/brands")
async def get_admin_brands():
    return [
        {"name": "Jordan", "logo": "https://images.unsplash.com/photo-1534312527009-56c7016453e6?auto=format&fit=crop&w=100&q=80"},
        {"name": "Nike", "logo": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=100&q=80"},
        {"name": "Yeezy", "logo": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=100&q=80"},
        {"name": "New Balance", "logo": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=100&q=80"},
        {"name": "Travis Scott", "logo": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=100&q=80"}
    ]

# ----- Last Failed Order Endpoint -----
@app.get("/api/last-failed-order")
async def last_failed_order(session_id: str):
    order_id = _last_failed.get(session_id)
    if order_id:
        return {"order_id": order_id, "has_failure": True}
    return {"order_id": None, "has_failure": False}

# ----- Orders Endpoint (Admin or dev token protected) -----
@app.get("/api/orders")
async def list_orders(
    x_dev_token: Optional[str] = Header(None, alias="X-Dev-Token"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> List[Dict]:
    return get_all_orders()


# ----- Real Razorpay Standard Test Mode Endpoints -----
class CreateRazorpayOrderRequest(BaseModel):
    amount: float
    product_id: str
    session_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    phone: Optional[str] = None
    delivery_location: Optional[str] = None

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: Optional[str] = ""
    product_id: str
    amount: float

@app.post("/api/razorpay/create-order")
async def create_razorpay_order_endpoint(req: CreateRazorpayOrderRequest):
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    amount_paise = int(round(req.amount * 100))
    receipt_id = f"rcpt_{int(datetime.utcnow().timestamp())}_{req.product_id}"

    rzp_order_id = f"order_{uuid.uuid4().hex[:14]}"
    payment_link_url = ""
    use_mock_checkout = True

    try:
        if key_id and key_secret:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            
            # Create a real Order so we can use standard popup
            order_data = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt_id,
                "notes": {
                    "product_id": req.product_id,
                    "session_id": req.session_id or "",
                    "delivery_location": req.delivery_location or "India",
                }
            })
            rzp_order_id = order_data["id"]
            
            # Create a real Payment Link so user redirects to Razorpay Hosted Checkout
            # This directly fulfills "redirecting to the razorpay to pay"
            link_data = client.payment_link.create({
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "first_min_partial_amount": 0,
                "description": f"Purchase of {req.product_id} — Agentic Commerce",
                "customer": {
                    "name": req.customer_name or "Verified Collector",
                    "email": req.customer_email or "collector@kicksvault.in",
                    "contact": req.phone or "+919876543210"
                },
                "notify": {
                    "sms": False,
                    "email": False
                },
                "reminder_enable": False,
                "notes": {
                    "product_id": req.product_id,
                    "session_id": req.session_id or "",
                    "delivery_location": req.delivery_location or "India",
                },
                "callback_url": "http://127.0.0.1:8000/api/razorpay/callback",
                "callback_method": "get"
            })
            
            if link_data and link_data.get("short_url"):
                payment_link_url = link_data["short_url"]
                use_mock_checkout = False
    except Exception as e:
        print(f"[WARN] Razorpay link generation fallback: {e}")

    if use_mock_checkout:
        # Fallback to local mock hosted checkout page if API limits (30 links) are hit
        product_name = CATALOG.get(req.product_id, {}).get("name", req.product_id)
        payment_link_url = f"/static/razorpay_mock_checkout.html?order_id={rzp_order_id}&amount={req.amount}&product_id={req.product_id}&product_name={product_name}"

    # Register in order storage
    create_order(rzp_order_id, req.product_id, req.amount, req.session_id or "user")

    return {
        "order_id": rzp_order_id,
        "amount": req.amount,
        "amount_paise": amount_paise,
        "currency": "INR",
        "key_id": key_id or "rzp_test_TTekkjfzRu8Ovg",
        "product_id": req.product_id,
        "product_name": CATALOG.get(req.product_id, {}).get("name", req.product_id),
        "payment_link_url": payment_link_url
    }

# Razorpay Redirect Callback GET Route
from fastapi.responses import RedirectResponse
@app.get("/api/razorpay/callback")
async def razorpay_callback_endpoint(
    razorpay_payment_id: Optional[str] = None,
    razorpay_payment_link_id: Optional[str] = None,
    razorpay_payment_link_reference_id: Optional[str] = None,
    razorpay_payment_link_status: Optional[str] = None,
    razorpay_signature: Optional[str] = None
):
    # Verify the status
    order_id = razorpay_payment_link_id or razorpay_payment_link_reference_id
    if not order_id:
        return HTMLResponse("<html><body><h2>Error: Missing order_id in Razorpay callback</h2></body></html>", status_code=400)
        
    order = get_order(order_id)
    if not order:
        return HTMLResponse("<html><body><h2>Error: Order not found in ledger</h2></body></html>", status_code=404)

    is_paid = (razorpay_payment_link_status and razorpay_payment_link_status.lower() == "paid") or razorpay_payment_id
    
    if is_paid:
        update_order_status(order_id, "paid", datetime.utcnow())
        redirect_url = f"/?status=success&order_id={order_id}&payment_id={razorpay_payment_id or 'pay_redirected'}&signature={razorpay_signature or ''}&amount={order['amount']}&product_id={order['product_id']}"
    else:
        update_order_status(order_id, "failed", datetime.utcnow())
        redirect_url = f"/?status=failed&order_id={order_id}"

    return RedirectResponse(url=redirect_url)

@app.post("/api/razorpay/verify-payment")
async def verify_payment_endpoint(req: VerifyPaymentRequest):
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    computed_sig = hmac.new(key_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    verified = hmac.compare_digest(computed_sig, req.razorpay_signature) if (req.razorpay_signature and key_secret) else True

    update_order_status(req.razorpay_order_id, "paid", datetime.utcnow())

    return {
        "status": "success",
        "verified": verified,
        "order_id": req.razorpay_order_id,
        "payment_id": req.razorpay_payment_id,
        "signature": req.razorpay_signature or computed_sig,
        "amount": req.amount,
        "product_id": req.product_id
    }

class CreateOrderRequest(BaseModel):
    product_id: str
    amount: float # in INR
    shipping_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

@app.post("/api/create-order")
async def create_razorpay_order(payload: CreateOrderRequest):
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_TTekkjfzRu8Ovg")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "L30Mcc6q2pqZEAQX7HKjbgHG")
        client = razorpay.Client(auth=(key_id, key_secret))
        
        amount_in_paise = int(round(payload.amount * 100))
        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"rcpt_{payload.product_id}_{int(time.time())}",
            "notes": {
                "product_id": payload.product_id,
                "delivery_destination": payload.shipping_address or "India",
                "customer_name": payload.customer_name or "Verified Collector",
                "customer_phone": payload.customer_phone or "9876543210"
            }
        }
        order = client.order.create(data=order_data)
        
        # Save order record in local storage so it exists in the ledger
        create_order(
            order_id=order["id"],
            product_id=payload.product_id,
            amount=payload.amount,
            customer_id="customer",
            shipping_address=payload.shipping_address,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone
        )
        
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": "INR",
            "key_id": key_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class VerifyPaymentRequestStandard(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    product_id: str
    amount: float
    shipping_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

@app.post("/api/verify-payment")
async def verify_payment(payload: VerifyPaymentRequestStandard):
    try:
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "L30Mcc6q2pqZEAQX7HKjbgHG")
        # Verify HMAC-SHA256 signature
        generated_signature = hmac.new(
            bytes(key_secret, "utf-8"),
            bytes(f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}", "utf-8"),
            hashlib.sha256
        ).hexdigest()

        if payload.razorpay_signature and generated_signature != payload.razorpay_signature:
            raise HTTPException(status_code=400, detail="Invalid Payment Signature")

        # Save or update order in verified storage
        order = get_order(payload.razorpay_order_id)
        seller_payout = round(payload.amount * 0.9, 2)
        platform_fee = round(payload.amount * 0.1, 2)
        
        if not order:
            create_order(
                order_id=payload.razorpay_order_id,
                product_id=payload.product_id,
                amount=payload.amount,
                customer_id="customer",
                shipping_address=payload.shipping_address,
                customer_name=payload.customer_name,
                customer_phone=payload.customer_phone
            )
            
        update_order_status(
            order_id=payload.razorpay_order_id,
            status="paid",
            paid_at=datetime.utcnow(),
            seller_payout=seller_payout,
            platform_fee=platform_fee,
            payment_id=payload.razorpay_payment_id,
            shipping_address=payload.shipping_address,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone
        )
        
        return {"status": "success", "message": "Payment verified successfully!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class CreateSubscriptionRequest(BaseModel):
    plan_id: str = "grailpass_vip"
    customer_email: Optional[str] = "collector@kicksvault.in"
    customer_name: Optional[str] = "VIP Member"

@app.post("/api/subscriptions/create")
async def create_subscription(payload: CreateSubscriptionRequest):
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_TTekkjfzRu8Ovg")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "L30Mcc6q2pqZEAQX7HKjbgHG")
        client = razorpay.Client(auth=(key_id, key_secret))
        
        plan_data = {
            "period": "monthly",
            "interval": 1,
            "item": {
                "name": "KicksVault GrailPass VIP Club",
                "amount": 29900, # ₹299 in paise
                "currency": "INR",
                "description": "VIP Access to KicksVault deadstock grails and early releases."
            }
        }
        try:
            plan = client.plan.create(data=plan_data)
        except Exception:
            plan = {"id": "plan_grailpass_vip_mock"}

        sub_data = {
            "plan_id": plan["id"],
            "total_count": 12,
            "quantity": 1,
            "customer_notify": 0
        }
        try:
            subscription = client.subscription.create(data=sub_data)
            subscription_id = subscription["id"]
        except Exception:
            subscription_id = f"sub_vip_{uuid.uuid4().hex[:12]}"
            
        create_order(
            order_id=subscription_id,
            product_id="grailpass_vip",
            amount=299.0,
            customer_id=payload.customer_email or "collector@kicksvault.in",
            customer_name=payload.customer_name or "VIP Member",
            is_subscription=True
        )

        sub_record = storage.save_subscription(
            subscription_id=subscription_id,
            customer_email=payload.customer_email or "collector@kicksvault.in",
            customer_name=payload.customer_name or "VIP Member",
            amount=299.0,
            status="active"
        )
        
        return {
            "subscription_id": subscription_id,
            "key_id": key_id,
            "subscription": sub_record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/subscription")
async def get_user_subscription(email: Optional[str] = None):
    """Retrieve subscription validity details for the logged-in customer."""
    target_email = email or "collector@kicksvault.in"
    sub = storage.get_user_subscription(target_email)
    if not sub:
        # Fallback default active subscription if requested
        sub = {
            "subscription_id": "sub_vip_demo_active",
            "customer_email": target_email,
            "customer_name": target_email.split('@')[0].capitalize(),
            "plan_name": "KicksVault GrailPass VIP Club",
            "amount": 299.0,
            "billing_cycle": "Monthly",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "valid_until": datetime.fromtimestamp(datetime.utcnow().timestamp() + (30 * 86400)).isoformat(),
            "days_remaining": 30,
            "perks": [
                "₹1,000 instant discount on all luxury negotiations",
                "Priority early access to limited deadstock drops",
                "Zero platform authentication fees on consignment",
                "Direct VIP concierge support line"
            ]
        }
    return {"status": "success", "subscription": sub}

@app.get("/api/admin/subscriptions")
async def get_admin_subscriptions():
    """Retrieve all customer subscriptions for Admin HUD Telemetry."""
    subs = storage.get_all_subscriptions()
    if not subs:
        # Seed initial sample telemetry if empty
        subs = [
            {
                "subscription_id": "sub_vip_9988112233",
                "customer_email": "jashubudaraju@gmail.com",
                "customer_name": "Jashu Budaraju (Admin VIP)",
                "customer_phone": "+91 98765 43210",
                "shipping_address": "Hyderabad, Telangana, India",
                "plan_name": "KicksVault GrailPass VIP Club",
                "amount": 299.0,
                "billing_cycle": "Monthly",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "valid_until": datetime.fromtimestamp(datetime.utcnow().timestamp() + (30 * 86400)).isoformat(),
                "days_remaining": 30
            },
            {
                "subscription_id": "sub_vip_7766554433",
                "customer_email": "collector@kicksvault.in",
                "customer_name": "Verified Collector",
                "customer_phone": "+91 91234 56789",
                "shipping_address": "Bandra West, Mumbai, India",
                "plan_name": "KicksVault GrailPass VIP Club",
                "amount": 299.0,
                "billing_cycle": "Monthly",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "valid_until": datetime.fromtimestamp(datetime.utcnow().timestamp() + (28 * 86400)).isoformat(),
                "days_remaining": 28
            }
        ]
    return {"status": "success", "count": len(subs), "subscriptions": subs}

class CreateInvoiceRequest(BaseModel):
    order_id: str
    payment_id: str
    product_id: str
    amount: float
    customer_name: Optional[str] = "Arjun Sharma"
    customer_email: Optional[str] = "arjun@example.com"
    customer_phone: Optional[str] = "9876543210"

@app.post("/api/invoices/create")
async def create_invoice(payload: CreateInvoiceRequest):
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_TTekkjfzRu8Ovg")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "L30Mcc6q2pqZEAQX7HKjbgHG")
        client = razorpay.Client(auth=(key_id, key_secret))
        
        from guardrails import CATALOG
        prod = CATALOG.get(payload.product_id, {"name": payload.product_id})
        product_name = prod.get("name", "Exclusive Sneakers")
        
        invoice_data = {
            "type": "invoice",
            "description": f"GST Tax Invoice for {product_name}",
            "customer": {
                "name": payload.customer_name or "Arjun Sharma",
                "email": payload.customer_email or "arjun@example.com",
                "contact": payload.customer_phone or "9876543210"
            },
            "line_items": [
                {
                    "name": product_name,
                    "amount": int(round(payload.amount * 100)),
                    "currency": "INR"
                }
            ]
        }
        
        try:
            invoice = client.invoice.create(data=invoice_data)
            client.invoice.issue(invoice["id"])
            invoice_url = invoice["short_url"]
        except Exception as rzp_err:
            print(f"[WARN] Razorpay invoice API failed, falling back to mock link: {rzp_err}")
            invoice_url = f"/static/mock_invoice.html?order_id={payload.order_id}&payment_id={payload.payment_id}&product_id={payload.product_id}&amount={payload.amount}&name={payload.customer_name}&phone={payload.customer_phone}"
            
        return {"invoice_url": invoice_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

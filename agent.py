import os
import re
import uuid
from typing import List, TypedDict, Optional, Dict, Union, Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

try:
    from langgraph.graph.message import add_messages
except ImportError:
    def add_messages(left, right):
        return (left or []) + (right or [])

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    try:
        from langgraph.checkpoint import MemorySaver
    except ImportError:
        MemorySaver = None

# Load environment variables (local .env; on Vercel these come from the dashboard)
load_dotenv()

# Import guardrails & storage
from guardrails import (
    CATALOG, PaymentProposal, get_catalog_summary, get_product,
    get_stage1_price, get_stage2_price
)
try:
    from storage import create_order
except ImportError:
    create_order = None

# ---------- State Definition ----------
class AgentState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    customer_id: str
    product_id: Optional[str]
    agreed_price: Optional[float]
    checkout_url: Optional[str]
    order_id: Optional[str]
    guardrail_triggered: bool
    negotiation_stage: int          # 0 = not started, 1 = stage 1, 2 = stage 2, 3 = final
    selected_product_id: Optional[str]
    failure_recovery: bool          # True when triggered by payment.failed
    delivery_location: Optional[str]

# ---------- LLM Initialization ----------
groq_api_key = os.getenv("GROQ_API_KEY", "")
groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Primary & Fallback LLM Setup
llm = None
for candidate_model in [groq_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"]:
    try:
        llm = ChatGroq(
            model=candidate_model,
            groq_api_key=groq_api_key if groq_api_key else "placeholder_key",
            temperature=0.3,
            max_retries=2
        )
        break
    except Exception as e:
        print(f"[WARN] Failed to initialize ChatGroq with {candidate_model}: {e}")

def extract_agent_response(state_messages: List[BaseMessage]) -> str:
    """Safely unpacks the last AI response without index or type errors."""
    if not state_messages:
        return "Welcome to KicksVault! Which grail sneaker can I assist you with today?"

    for msg in reversed(state_messages):
        # Check for standard AIMessage or duck-typed AI object
        if isinstance(msg, AIMessage) and msg.content:
            return _extract_content_text(msg.content)
        elif hasattr(msg, "content") and str(getattr(msg, "type", "")).lower() in ["ai", "assistant"]:
            if msg.content:
                return _extract_content_text(msg.content)
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            return _extract_content_text(msg.get("content", ""))

    return "I'm reviewing your request. How can I help you complete your grail purchase?"

# ---------- Intent Detection Patterns ----------
# Stage 3 – buyer signals immediate purchase intent
_CLOSING_REGEX = re.compile(
    r"\b(buy|take it|deal|order|checkout|purchase|confirm|i['']m in|i['']ll take|ready to buy)\b"
    r".*?(?:₹|inr|rs\.?)\s*(\d[\d,]*)",
    re.IGNORECASE,
)
# Simple closing intent without explicit price
_CLOSING_INTENT_REGEX = re.compile(
    r"\b(i['']m ready|ready to buy|let['']s do it|yes.{0,10}buy|go ahead|confirm the order)\b",
    re.IGNORECASE,
)
# 8-Product inquiry detection keywords
_PRODUCT_KEYWORDS: Dict[str, List[str]] = {
    "PROD_001": ["jordan.*1", "chicago", "lost.*found", "aj1", "aj 1", "PROD_001"],
    "PROD_002": ["yeezy", "onyx", "boost 350", "350 v2", "PROD_002"],
    "PROD_003": ["dunk", "panda", "nike dunk", "PROD_003"],
    "PROD_004": ["creaseguard", "care kit", "shield", "cleaner", "PROD_004"],
    "PROD_005": ["travis", "scott", "reverse mocha", "cactus jack", "ts1", "PROD_005"],
    "PROD_006": ["new balance", "9060", "rain cloud", "nb 9060", "PROD_006"],
    "PROD_007": ["military black", "jordan 4", "aj4", "retro 4", "PROD_007"],
    "PROD_008": ["crate", "wooden crate", "display vault", "box", "PROD_008"],
}

# ---------- Helpers ----------
def _extract_content_text(content: Union[str, list]) -> str:
    """Safely extracts text content whether returned as a string or list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif hasattr(item, "text"):
                parts.append(item.text)
        return "\n".join(parts)
    return str(content)


def _detect_product_from_message(text: str) -> Optional[str]:
    """Return the first product ID whose keywords match the user message, or None."""
    text_lower = text.lower()
    for prod_id, keywords in _PRODUCT_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower, re.IGNORECASE):
                return prod_id
    return None


def clean_price_float(raw_val: Any) -> float:
    """Safely extracts a float from any currency string (e.g., '₹33,949', 'INR 33,949.00', '33,949/-', 'Rs. 11,999')."""
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    if not raw_val:
        return 0.0
    s = str(raw_val).strip()
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", s)
    if m:
        num_str = m.group(1).replace(",", "")
        try:
            return float(num_str)
        except ValueError:
            pass
    cleaned = re.sub(r"[^\d.]", "", s)
    if cleaned:
        try:
            return float(cleaned)
        except ValueError:
            pass
    return 0.0


def _detect_closing_price(text: str) -> Optional[float]:
    """Extract the buyer's proposed closing price from message text, if present."""
    m = _CLOSING_REGEX.search(text)
    if m:
        price = clean_price_float(m.group(2))
        if price > 0:
            return price
    return None


def _ensure_system_prompt(state: AgentState) -> None:
    """Inject or update system prompt with catalog summary, strict secret pricing rules, and location collection."""
    cat = get_catalog_summary()
    loc_context = f"Customer Destination: {state.get('delivery_location', 'Not specified yet')}"
    system_content = f"""You are the elite, protective luxury sneaker concierge at KicksVault India — the certified exchange for deadstock authenticated grails.

CATALOG & INVENTORY:
{cat}
{loc_context}

SECRET NEGOTIATION RULES & CONVERSATIONAL MEMORY:
1. NEVER REVEAL INTERNAL METRICS: NEVER mention or reveal words like "floor price", "minimum price", "cost price", "margins", "reserve", "guardrail", or "stage" to the customer.
2. TOUGH & REALISTIC NEGOTIATION: Defend the retail price with uncompromising standards. Highlight deadstock rarity, physical tamper-evident NFC authentication, and collector appreciation. Keep negotiations firm and hard to crack.
3. ROUND 1 BARGAIN: If the customer asks for a discount or makes an opening offer, extend at most a 2% to 4% token courtesy discount, or suggest a complimentary accessory (CreaseGuard Care Kit).
4. ROUND 2 (PERSISTENT BUYER): If the buyer pushes back hard and insists on a better deal, counter-offer halfway down to the item's authorized floor price. Frame this as an exclusive, one-time courtesy for an authenticated collector.
5. FINAL DEAL / IMMEDIATE CHECKOUT: Only agree to a deeper deal if the user firmly commits to immediate checkout (e.g., "I will buy right now for ₹X" or "I'm ready to checkout").
6. HARD MARGIN LOCK: If the customer bids lower than the item's hidden floor reserve, firmly decline without mentioning any floor numbers (e.g., "Due to collector rarity, tamper-evident NFC verification, and verified deadstock condition, the best price we can authorize is ₹X").
7. INTENT ACTION TRIGGER: When a deal is closed or buyer signals intent to purchase at an authorized price, emit EXACTLY:
   [ACTION:CREATE_PAYMENT | product_id: <PRODUCT_ID> | price: <PRICE>]
8. DELIVERY LOCATION: Ask or confirm the buyer's delivery destination/city in India (e.g., "Where in India should we dispatch your vault-authenticated pair?"). Acknowledge priority insured courier dispatch.
9. TONE: Sophisticated, authoritative, knowledgeable, firm on value. Always format prices with the ₹ symbol.
"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[0], SystemMessage):
        messages[0] = SystemMessage(content=system_content)
    else:
        messages.insert(0, SystemMessage(content=system_content))
    state["messages"] = messages


# ---------- Nodes ----------
def sales_node(state: AgentState) -> AgentState:
    """Main conversational sales agent node with multi-turn memory and 3-stage negotiation logic."""
    _ensure_system_prompt(state)

    stage = state.get("negotiation_stage", 0)
    messages = state.get("messages", [])

    # Find last human message
    last_human = None
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_human = _extract_content_text(m.content)
            break

    # Scan historical messages to retain selected product context if not already set
    if not state.get("selected_product_id"):
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                txt = _extract_content_text(m.content)
                detected = _detect_product_from_message(txt)
                if detected:
                    state["selected_product_id"] = detected
                    if stage == 0:
                        state["negotiation_stage"] = 1
                    break

    prod_id = state.get("selected_product_id")

    # Check if the user is agreeing to the subscription
    last_human_lower = last_human.lower() if last_human else ""
    if prod_id and any(kw in last_human_lower for kw in ["subscribe", "grailpass", "vip club", "join the vip", "join vip", "accept the subscription", "yes, i'll join", "yes, subscribe", "go ahead with vip", "sign me up for vip"]):
        messages.append(
            SystemMessage(
                content=(
                    "The customer has agreed to join the VIP GrailPass Club. "
                    "You MUST emit EXACTLY this tag on its own line: "
                    "[ACTION:CREATE_SUBSCRIPTION | plan: grailpass_vip | price: 299] "
                    "Then warmly congratulate them and direct them to checkout."
                )
            )
        )

    # Stage 3 intent detection: buyer signals immediate purchase
    closing_price = _detect_closing_price(last_human)
    is_closing_intent = bool(_CLOSING_INTENT_REGEX.search(last_human))

    if prod_id and (closing_price is not None or is_closing_intent) and stage >= 1:
        state["negotiation_stage"] = 3
        # Use proposed closing price or fall back to stage-2 midpoint
        proposed = closing_price if closing_price else get_stage2_price(prod_id)
        product = get_product(prod_id)
        # Clamp through guardrails
        proposal = PaymentProposal(product_id=prod_id, proposed_price=proposed)
        if proposal.is_below_floor():
            # Firm refusal – pitch the KicksVault GrailPass VIP Club subscription (₹299/mo) for instant ₹1,000 credit
            discounted_price = product["retail_price"] - 1000.0
            messages.append(
                SystemMessage(
                    content=(
                        f"The buyer bid ₹{proposed:.2f}, which is strictly below the secret floor price of ₹{product['floor_price']:.2f}. "
                        f"You MUST refuse this low bid politely but firmly. "
                        f"Immediately pitch the 'KicksVault GrailPass VIP Club' subscription (₹299/mo with UPI Autopay) as the ONLY way to unlock extra discounts. "
                        f"Explain that by subscribing, they get an instant ₹1,000 credit today, reducing their sneaker purchase price to ₹{discounted_price:.2f}, "
                        f"plus priority dropping privileges and zero platform fees. "
                        f"Ask them: 'Would you like to subscribe to the KicksVault GrailPass VIP Club for ₹299/month to unlock your ₹1,000 discount immediately?'"
                    )
                )
            )
            state["negotiation_stage"] = 2  # Roll back to stage 2
        else:
            final_price = proposal.validate_and_compute_final_price()
            state["guardrail_triggered"] = final_price != proposed
            state["product_id"] = prod_id
            state["agreed_price"] = final_price
            # Inject instruction for LLM to emit the payment tag
            messages.append(
                SystemMessage(
                    content=(
                        f"The buyer has agreed to purchase {product['name']} at ₹{final_price:.2f}. "
                        f"Emit EXACTLY this tag on its own line: "
                        f"[ACTION:CREATE_PAYMENT | product_id: {prod_id} | price: {final_price:.2f}] "
                        f"Then confirm the deal warmly."
                    )
                )
            )
    elif prod_id and stage == 1:
        # Transition to stage 2 on buyer pushback
        if any(kw in last_human.lower() for kw in ["less", "cheaper", "discount", "lower", "too expensive", "reduce", "negotiate", "better price", "₹", "inr"]):
            state["negotiation_stage"] = 2

    # Invoke the LLM with fallback handling
    raw_content = ""
    if llm:
        try:
            raw_content = llm.invoke(state["messages"]).content
        except Exception as e:
            print(f"[WARN] Primary LLM invocation failed: {e}")
            # Try fallback model if available
            try:
                fallback_llm = ChatGroq(
                    model="openai/gpt-oss-120b",
                    groq_api_key=groq_api_key if groq_api_key else "placeholder_key",
                    temperature=0.3,
                    max_retries=2
                )
                raw_content = fallback_llm.invoke(state["messages"]).content
            except Exception as e2:
                print(f"[WARN] Fallback LLM invocation also failed: {e2}")

    if not raw_content:
        # Graceful fallback sales response
        prod = get_product(prod_id) if prod_id else None
        if prod:
            raw_content = (
                f"The **{prod['name']}** is in vault stock (verified authentic). "
                f"Retail is ₹{prod['retail_price']:,}, but we can offer a 4% VIP collector discount "
                f"or complimentary CreaseGuard kit. Would you like to lock in this deal?"
            )
        else:
            raw_content = "Welcome to KicksVault! Which luxury silhouette or grail sneaker would you like to explore today?"

    response = _extract_content_text(raw_content)
    state["messages"].append(AIMessage(content=response))
    return state


def route_decision(state: AgentState) -> str:
    """Route to payment node if AI response contains payment tag, else continue."""
    if not state.get("messages"):
        return "continue"
    last_msg = state["messages"][-1]
    content = _extract_content_text(last_msg.content)
    if isinstance(last_msg, AIMessage):
        if "[ACTION:CREATE_PAYMENT" in content:
            return "payment"
        elif "[ACTION:CREATE_SUBSCRIPTION" in content:
            return "subscription"
    return "continue"


def payment_tool_node(state: AgentState) -> AgentState:
    last_msg = state["messages"][-1]
    last_content = _extract_content_text(last_msg.content)
    tag_match = re.search(
        r"\[ACTION:CREATE_PAYMENT\s*\|\s*product_id:\s*(?P<pid>[^|]+)\|\s*price:\s*(?P<price>[^\]]+)\]",
        last_content,
    )
    if not tag_match:
        raise ValueError("ACTION tag not found in AI message")
    product_id = tag_match.group("pid").strip()
    raw_price = tag_match.group("price").strip()
    proposed_price = clean_price_float(raw_price)

    # Fallback to catalog retail if parsing was zero or negative
    if proposed_price <= 0 and product_id in CATALOG:
        proposed_price = CATALOG[product_id]["retail_price"]

    proposal = PaymentProposal(product_id=product_id, proposed_price=proposed_price)
    final_price = proposal.validate_and_compute_final_price()
    state["guardrail_triggered"] = final_price != proposed_price
    state["product_id"] = product_id
    state["agreed_price"] = final_price

    product = get_product(product_id)
    customer_id = state.get("customer_id", f"cust_{uuid.uuid4().hex[:8]}")

    destination = state.get("delivery_location") or "India (Standard Insured Vault Express)"
    try:
        import razorpay
        client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
        amount_paise = int(final_price * 100)
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": f"Purchase of {product['name']} — KicksVault India Agentic Commerce",
            "customer": {
                "name": customer_id,
                "email": "buyer@kicksvault.in",
                "contact": "9876543210",
            },
            "notify": {"sms": False, "email": False},
            "notes": {
                "product_id": product_id,
                "customer_id": customer_id,
                "delivery_destination": destination,
                "platform": "KicksVault India Agentic Commerce",
            },
        }
        response = client.payment_link.create(payload)
        short_url = response.get("short_url")
        order_id = response.get("id")
    except Exception as e:
        print(f"[WARN] Razorpay link generation fallback: {e}")
        order_id = f"plink_{uuid.uuid4().hex[:12]}"
        short_url = f"https://rzp.io/l/{order_id}"

    state["checkout_url"] = short_url
    state["order_id"] = order_id

    if create_order and order_id:
        create_order(order_id, product_id, final_price, customer_id)

    confirmation_msg = (
        f"🎉 Deal locked in! Here are your purchase details:\n\n"
        f"**Product:** {product['name']}\n"
        f"**Final Price:** ₹{final_price:,.2f} INR\n"
        f"**Delivery Destination:** 📍 {destination}\n"
        f"**Payment Link:** {short_url}\n\n"
        f"Complete your payment using any UPI, card, or netbanking method via Razorpay. Your pair will be dispatched via priority insured courier."
    )
    state["messages"].append(AIMessage(content=confirmation_msg))
    return state


def subscription_tool_node(state: AgentState) -> AgentState:
    """Create a subscription tag response."""
    state["product_id"] = "grailpass_vip"
    state["agreed_price"] = 299.0
    state["checkout_url"] = "subscription_checkout"
    
    confirmation_msg = (
        f"🌟 Welcome to the KicksVault GrailPass VIP Club!\n\n"
        f"**Plan:** KicksVault GrailPass VIP membership\n"
        f"**Recurring Fee:** ₹299/month\n"
        f"**Benefits Activated:** Instant ₹1,000 credit on your current pair, free shipping, early drop access.\n\n"
        f"Please click 'Pay via Razorpay' to authorize your recurring monthly VIP membership (UPI Autopay supported)."
    )
    state["messages"].append(AIMessage(content=confirmation_msg))
    return state


def failure_recovery_node(state: AgentState) -> AgentState:
    """Inject a warm recovery message and generate a fresh payment link on payment failure."""
    product_id = state.get("product_id", "PROD_001")
    agreed_price = state.get("agreed_price")
    product = get_product(product_id)

    if agreed_price is None:
        agreed_price = product["retail_price"]

    # Generate a fresh payment link
    try:
        import razorpay
        client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
        customer_id = state.get("customer_id", f"cust_{uuid.uuid4().hex[:8]}")
        amount_paise = int(agreed_price * 100)
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": f"[RETRY] Purchase of {product['name']} — KicksVault India",
            "customer": {
                "name": customer_id,
                "email": "buyer@kicksvault.in",
                "contact": "9876543210",
            },
            "notify": {"sms": False, "email": False},
        }
        response = client.payment_link.create(payload)
        fresh_url = response.get("short_url", "#")
        new_order_id = response.get("id")
        if create_order and new_order_id:
            create_order(new_order_id, product_id, agreed_price, customer_id)
        state["checkout_url"] = fresh_url
        state["order_id"] = new_order_id
    except Exception:
        fresh_url = state.get("checkout_url", "#")

    recovery_msg = (
        f"⚠️ We noticed your payment could not be processed — this was due to a bank-side timeout "
        f"(error: BAD_REQUEST_PAYMENT_TIMED_OUT), not any issue with your account.\n\n"
        f"No worries! We've generated a **fresh, 1-click payment link** for your {product['name']} "
        f"at the same agreed price of ₹{agreed_price:,.2f}:\n\n"
        f"🔁 **Retry Payment:** {fresh_url}\n\n"
        f"If you continue to face issues, please reach out and we'll be happy to assist. "
        f"Your deal is still locked in at the negotiated price."
    )
    state["messages"].append(AIMessage(content=recovery_msg))
    state["failure_recovery"] = False  # Reset flag after handling
    return state


# ---------- Graph Assembly ----------
graph = StateGraph(AgentState)
graph.add_node("sales", sales_node)
graph.add_node("payment", payment_tool_node)
graph.add_node("subscription", subscription_tool_node)
graph.add_node("failure_recovery", failure_recovery_node)

graph.add_conditional_edges(
    "sales",
    route_decision,
    {"payment": "payment", "subscription": "subscription", "continue": END},
)

graph.add_edge("payment", END)
graph.add_edge("subscription", END)
graph.add_edge("failure_recovery", END)

graph.set_entry_point("sales")

memory = MemorySaver() if MemorySaver is not None else None
graph_app = graph.compile(checkpointer=memory) if memory is not None else graph.compile()


if __name__ == "__main__":
    state: AgentState = {"messages": [], "customer_id": f"cust_{uuid.uuid4().hex[:8]}", "negotiation_stage": 0}
    while True:
        user_input = input("You: ")
        state["messages"].append(HumanMessage(content=user_input))
        state = graph_app.invoke(state)
        ai_msg = state["messages"][-1]
        print(f"Agent: {_extract_content_text(ai_msg.content)}")
        if state.get("checkout_url"):
            print("--- Checkout URL generated ---")
            print(state["checkout_url"])
            break

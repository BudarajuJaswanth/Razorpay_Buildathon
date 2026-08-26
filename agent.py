import os
import re
import uuid
from typing import List, TypedDict, Optional, Dict, Union

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

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
    messages: List[BaseMessage]
    customer_id: str
    product_id: Optional[str]
    agreed_price: Optional[float]
    checkout_url: Optional[str]
    order_id: Optional[str]
    guardrail_triggered: bool
    negotiation_stage: int          # 0 = not started, 1 = stage 1, 2 = stage 2, 3 = final
    selected_product_id: Optional[str]
    failure_recovery: bool          # True when triggered by payment.failed

# ---------- LLM Initialization ----------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

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
# Product inquiry detection
_PRODUCT_KEYWORDS: Dict[str, List[str]] = {
    "PROD_001": ["jordan", "chicago", "lost.*found", "aj1", "aj 1", "PROD_001"],
    "PROD_002": ["yeezy", "onyx", "boost 350", "PROD_002"],
    "PROD_003": ["dunk", "panda", "nike dunk", "PROD_003"],
    "PROD_004": ["creaseguard", "shield kit", "care kit", "accessory", "PROD_004"],
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


def _detect_closing_price(text: str) -> Optional[float]:
    """Extract the buyer's proposed closing price from message text, if present."""
    m = _CLOSING_REGEX.search(text)
    if m:
        raw = m.group(2).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def _ensure_system_prompt(state: AgentState) -> None:
    """Inject system prompt with catalog summary and negotiation rules."""
    if not any(isinstance(m, SystemMessage) for m in state.get("messages", [])):
        cat = get_catalog_summary()
        system_content = f"""You are a premium, persuasive sales representative for KicksVault India — a luxury, authenticated sneaker exchange.

CATALOG (your source of truth):
{cat}

NEGOTIATION RULES — follow these strictly:
1. STAGE 1 (First offer): Lead with craftsmanship, scarcity (mention exact stock count), and brand heritage. Offer at most a 4% goodwill discount off retail OR a complimentary CreaseGuard Shield Kit (PROD_004, value ₹1,499). Do NOT immediately jump to the floor price.
2. STAGE 2 (Buyer pushes back): Present the arithmetic midpoint between retail and floor as a "best we can do" counter. Emphasize exclusivity and limited availability again.
3. STAGE 3 (Buyer signals immediate intent): If the buyer explicitly says they will buy NOW at a specific price (e.g., "I'll buy it for ₹X right now"), and that price is at or above the floor price, emit the exact payment tag: [ACTION:CREATE_PAYMENT | product_id: <PRODUCT_ID> | price: <PRICE>]
4. HARD FLOOR INVARIANT: NEVER offer or accept any price below `floor_price`. If a buyer demands below floor, explain that KicksVault India maintains strict brand margin commitments and cannot proceed below that floor. Do NOT emit a payment tag for sub-floor requests.
5. TONE: Warm, confident, knowledgeable. Reference the product's story, authentication process, and collector value. Use ₹ symbol for prices.

When a buyer is negotiating, stay in character and follow the stage sequence. Do NOT skip stages unless the buyer explicitly confirms they are ready to transact.
"""
        state.setdefault("messages", []).insert(0, SystemMessage(content=system_content))


# ---------- Nodes ----------
def sales_node(state: AgentState) -> AgentState:
    """Main conversational sales agent node with 3-stage negotiation logic."""
    _ensure_system_prompt(state)

    # Determine current negotiation stage
    stage = state.get("negotiation_stage", 0)
    messages = state.get("messages", [])

    # Find last human message
    last_human = None
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_human = _extract_content_text(m.content)
            break

    if last_human:
        # Try to detect product if none selected yet
        if not state.get("selected_product_id"):
            detected = _detect_product_from_message(last_human)
            if detected:
                state["selected_product_id"] = detected
                if stage == 0:
                    state["negotiation_stage"] = 1

        prod_id = state.get("selected_product_id")

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
                # Firm refusal – let LLM handle the message
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

    # Invoke the LLM
    raw_content = llm.invoke(state["messages"]).content
    response = _extract_content_text(raw_content)
    state["messages"].append(AIMessage(content=response))
    return state


def route_decision(state: AgentState) -> str:
    """Route to payment node if AI response contains payment tag, else continue."""
    if not state.get("messages"):
        return "continue"
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and "[ACTION:CREATE_PAYMENT" in _extract_content_text(last_msg.content):
        return "payment"
    return "continue"


def payment_tool_node(state: AgentState) -> AgentState:
    """Create a Razorpay payment link and store the order."""
    last_msg = state["messages"][-1]
    last_content = _extract_content_text(last_msg.content)
    tag_match = re.search(
        r"\[ACTION:CREATE_PAYMENT\s*\|\s*product_id:\s*(?P<pid>[^|]+)\|\s*price:\s*(?P<price>[^\]]+)\]",
        last_content,
    )
    if not tag_match:
        raise ValueError("ACTION tag not found in AI message")
    product_id = tag_match.group("pid").strip()
    proposed_price = float(tag_match.group("price").strip())

    proposal = PaymentProposal(product_id=product_id, proposed_price=proposed_price)
    final_price = proposal.validate_and_compute_final_price()
    state["guardrail_triggered"] = final_price != proposed_price
    state["product_id"] = product_id
    state["agreed_price"] = final_price

    import razorpay
    client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
    product = get_product(product_id)
    amount_paise = int(final_price * 100)
    customer_id = state.get("customer_id", f"cust_{uuid.uuid4().hex[:8]}")
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
            "platform": "KicksVault India Agentic Commerce",
        },
    }
    response = client.payment_link.create(payload)
    short_url = response.get("short_url")
    order_id = response.get("id")
    state["checkout_url"] = short_url
    state["order_id"] = order_id

    if create_order and order_id:
        create_order(order_id, product_id, final_price, customer_id)

    confirmation_msg = (
        f"🎉 Deal locked in! Here are your purchase details:\n\n"
        f"**Product:** {product['name']}\n"
        f"**Final Price:** ₹{final_price:,.2f} INR\n"
        f"**Payment Link:** {short_url}\n\n"
        f"Complete your payment using any UPI, card, or netbanking method via Razorpay."
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
graph.add_node("failure_recovery", failure_recovery_node)

graph.add_conditional_edges(
    "sales",
    route_decision,
    {"payment": "payment", "continue": END},
)

graph.add_edge("payment", END)
graph.add_edge("failure_recovery", END)

graph.set_entry_point("sales")

graph_app = graph.compile()


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

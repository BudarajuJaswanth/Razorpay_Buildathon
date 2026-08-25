# KicksVault India — AI Agentic Commerce

> **Razorpay AI Buildathon 2026 — Track 1: AI Growth & Agentic Commerce**

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/chand/Razorpay_Buildathon)

---

## What Is This?

**KicksVault India** is an enterprise-grade, multi-page Agentic Commerce platform that pairs a conversational AI negotiation engine (Google Gemini via LangGraph) with Razorpay's instant payment rails to create a personalized, bargaining-capable luxury sneaker shopping experience.

### Key Features

| Feature | Implementation |
|---------|---------------|
| 🤖 **3-Stage AI Negotiation** | LangGraph state machine — Craftsmanship pitch → Midpoint offer → Closing |
| 🛡️ **Pydantic Financial Guardrails** | Zero-hallucination pricing — floor price is mathematically invariant |
| 💳 **Razorpay Payment Links** | Autonomous checkout via Razorpay SDK with HMAC-SHA256 webhook verification |
| 🔐 **Cryptographic Audit Trail** | Immutable webhook ledger with SHA256 signature verification |
| 🔄 **Graceful Failure Recovery** | Auto-generates fresh payment links on `payment_link.failed` events |
| 🤝 **A2A Commerce Protocol** | Machine-readable API for external AI agent transactions |
| 📱 **5-Page Luxury SPA** | Premium fintech UI (StockX/Stripe-inspired) with glassmorphism & Unsplash imagery |

---

## Architecture

```
Browser (SPA) → FastAPI (main.py) → LangGraph Agent (agent.py)
                                   ↓
                         Pydantic Guardrails (guardrails.py)
                                   ↓
                         Razorpay SDK → Payment Link
                                   ↓
                  Webhook → HMAC Verification → Storage
```

### Negotiation Flow
```
Stage 1 → 4% goodwill discount off retail + craftsmanship pitch
Stage 2 → Arithmetic midpoint: (retail + floor) / 2
Stage 3 → Buyer intent detected → [ACTION:CREATE_PAYMENT] → Razorpay SDK
Floor   → Hard refusal — brand margin explanation, no payment tag
```

---

## Tech Stack

- **Backend**: FastAPI + Python 3.12
- **AI Agent**: Google Gemini 3.6 Flash via LangGraph (StateGraph)
- **Guardrails**: Pydantic v2 with custom validators
- **Payments**: Razorpay SDK (payment links + webhook HMAC-SHA256)
- **Frontend**: Vanilla SPA — Plus Jakarta Sans + JetBrains Mono, Tailwind CSS CDN, Lucide Icons
- **Deployment**: Vercel (serverless Python)

---

## Local Development

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/Razorpay_Buildathon.git
cd Razorpay_Buildathon
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

```env
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
DEV_AUTH_TOKEN=dev-secret-token-razorpay-agentic-2026
```

### 3. Run Server
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open → **http://localhost:8000**

### 4. Run Tests
```bash
pytest -q
```

---

## Vercel Deployment

### Environment Variables (set in Vercel Dashboard)
| Variable | Description |
|----------|-------------|
| `RAZORPAY_KEY_ID` | Razorpay test/live key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook HMAC secret |
| `GEMINI_API_KEY` | Google Gemini API key |
| `DEV_AUTH_TOKEN` | Token for `/api/simulate-payment` & `/api/simulate-failure` |

### Deploy Steps
1. Fork this repository
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
3. Set the environment variables above
4. Deploy ✅

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the SPA frontend |
| `/api/chat` | POST | Conversational AI agent (3-stage negotiation) |
| `/api/catalog` | GET | Product catalog JSON |
| `/api/orders` | GET | All transactions (live ledger) |
| `/api/simulate-payment` | POST | Simulate `payment_link.paid` webhook (dev) |
| `/api/simulate-failure` | POST | Simulate `payment_link.failed` webhook (dev) |
| `/api/agent/catalog` | GET | A2A machine-readable catalog |
| `/api/agent/transact` | POST | A2A autonomous transaction endpoint |
| `/api/webhook/razorpay` | POST | Razorpay webhook receiver (HMAC verified) |
| `/api/reset-session` | POST | Clear session state |
| `/api/last-failed-order` | GET | Check for pending failure recovery |

---

## SPA Pages

| Page | Description |
|------|-------------|
| **Live Storefront** | Luxury sneaker grid with Unsplash imagery & "Negotiate Deal with AI" CTAs |
| **AI Concierge** | Full-height conversational chat with checkout card & simulation buttons |
| **Brand Story** | Editorial narrative — problem, solution & 4-phase architecture timeline |
| **Future Roadmap** | A2A protocol, Indic voice, bundle engine, native Razorpay.js modal |
| **Merchant HUD** | Sentinel monitor, transaction ledger, HMAC webhook terminal, simulation deck |

---

## License

MIT — Built for the **Razorpay AI Buildathon 2026**.

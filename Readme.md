# EscrowPay 
Trade safely. Get paid instantly.

EscrowPay is a modern, frictionless escrow backend built with FastAPI. It secures transactions between buyers and sellers using dynamically generated virtual accounts and automated payouts, ensuring trust for online trades. Built using the Nomba API.

## 🚀 Key Features

- Frictionless Onboarding: Deals can be created by either a buyer or a seller with just an email and bank account. The counterparty simply joins via an invite link.
- Dynamic Virtual Accounts: Every single deal generates a unique Nomba Virtual Account for perfectly isolated payment tracking.
- Automated Webhooks: Listens for `transaction.success` events with strict HMAC signature verification and idempotency checks to prevent double-funding.
- Smart Payouts: Features strict bank-account name validation before releasing funds to the seller, ensuring money only goes to the right person.
- Auto-Release Timeout: Funds automatically release to the seller after a configurable window (default 72 hours) if the buyer doesn't confirm or dispute.
- Dispute Protection: Either party can freeze funds at any point before release.

## 🛠️ Tech Stack

- Framework:FastAPI (Python)
- Database:PostgreSQL with Async SQLAlchemy & asyncpg
- Validation:Pydantic
- Background Jobs:APScheduler (auto-release timeout)
- Integrations:Nomba API (Virtual Accounts, Transfers, Webhooks)
- Deployment:Railway

## 📡 API Endpoints

| Method |  Endpoint     | Description |
|--------|---------------|-------------|
| `POST` | `/api/deals/` | Create a new escrow deal (provisions a Nomba virtual account) |
| `POST` | `/api/deals/webhook` | Nomba webhook receiver — detects payments, updates deal status |
| `GET` | `/api/deals/{deal_id}` | Get real-time deal status |
| `POST` | `/api/deals/{deal_id}/join` | Second party joins the deal with their bank details |
| `POST` | `/api/deals/{deal_id}/confirm` | Buyer confirms receipt — triggers payout to seller |
| `POST` | `/api/deals/{deal_id}/dispute` | Raise a dispute — freezes funds |
| `GET` | `/health` | Health check |
| `POST` | `/webhook` | Webhook alias |

## 🔄 Deal State Machine

CREATED → FUNDED → CONFIRMED → RELEASED
↘ DISPUTED (funds frozen)
↘ EXPIRED (auto-released to seller)
CREATED → CANCELLED
FUNDED → REFUNDED



## 🌐 Live Demo

  API Documentation (Swagger UI):  
    https://escrowpay-production-5728.up.railway.app/docs

  Health Check:  
    https://escrowpay-production-5728.up.railway.app/health


## ⚙️ Getting Started

### 1. Clone & Install

```bash
git clone https://github.com/Bishopxxx/EscrowPay.git
cd EscrowPay

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/escrowpay
NOMBA_API_URL=https://api.nomba.com
NOMBA_CLIENT_ID=your_client_id
NOMBA_PRIVATE_KEY=your_private_key
NOMBA_PARENT_ACCOUNT_ID=your_parent_account_id
NOMBA_SUB_ACCOUNT_ID=your_sub_account_id
NOMBA_WEBHOOK_SECRET=NombaHackathon2026
```

### 3. Run the App

The app automatically creates database tables on startup.

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Explore the API

👉   http://localhost:8000/docs  

## 🧪 Demo Flow

1. `POST /api/deals/` — Seller creates a deal, gets a virtual account number
2. Share the deal ID with the buyer
3. `POST /api/deals/{deal_id}/join` — Buyer joins with their details
4. Buyer transfers funds to the virtual account number
5. Nomba fires a `transaction.success` webhook → deal flips to `FUNDED`
6. `POST /api/deals/{deal_id}/confirm` — Buyer confirms receipt → funds released to seller
7. `GET /api/deals/{deal_id}` — Check deal status at any point

---

*Built for the DevCareer x Nomba Hackathon 2026*
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
- Partial Payment Handling: Funded amount accumulates across multiple transfers — deal only activates when fully funded.


## 🛠️ Tech Stack

- Framework:FastAPI (Python)
- Database:PostgreSQL with Async SQLAlchemy & asyncpg
- Validation:Pydantic
- Background Jobs:APScheduler (auto-release timeout)
- Frontend:Next.js (App Router), Tailwind CSS
- Integrations:Nomba API (Virtual Accounts, Transfers, Webhooks)
- Deployment:Railway

## 📡 API Endpoints

| Method |  Endpoint     | Description |
|--------|---------------|-------------|
| `POST` | `/api/deals/` | Create a new escrow deal (provisions a Nomba virtual account) |
| `GET` | `/api/deals/` | List all deals|
| `GET` | `/api/deals/banks` | List supported banks with codes|
| `POST` | `/api/deals/webhook` | Nomba webhook receiver; detects payments, updates deal status |
| `GET` | `/api/deals/{deal_id}` | Get real-time deal status |
| `GET` | `/api/deals/{deal_id}/transactions` | Get transaction history for a deal |
| `POST` | `/api/deals/{deal_id}/ship` | Seller marks items as shipped|
| `POST` | `/api/deals/{deal_id}/confirm` | Buyer confirms receipt — triggers payout to seller |
| `POST` | `/api/deals/{deal_id}/dispute` | Raise a dispute — freezes funds |
| `POST` | `/api/deals/{deal_id}/cancel` | Cancel deal - refunds buyer if already funded|
| `GET` | `/health` | Health check |
| `POST` | `/webhook` | Webhook alias |

## 🔄 Deal State Machine

CREATED → FUNDED → SHIPPED → CONFIRMED → RELEASED
↘ DISPUTED (funds frozen)
↘ EXPIRED (auto-released to seller)
CREATED → CANCELLED
FUNDED → REFUNDED


## 🌐 Live Demo

Frontend: https://escrowpay-frontend.vercel.app

API Documentation (Swagger UI): https://escrowpay-production-5728.up.railway.app/docs

Health Check: https://escrowpay-production-5728.up.railway.app/health

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

### 4. Frontend

```bash
cd escrowpay-frontend
npm install
npm run dev
```

### 5. Explore the API

👉 http://localhost:8000/docs

## 🧪 Demo Flow

1. Go to https://escrowpay-frontend.vercel.app/create — seller creates a deal, gets a unique virtual account number
2. Seller copies the deal link and sends it to the buyer
3. Buyer opens the link, enters their bank details, and joins the deal
4. Buyer transfers funds to the Nomba virtual account number
5. Nomba fires a `transaction.success` webhook → deal flips to `FUNDED`
6. Seller marks item as shipped → deal flips to `SHIPPED`
7. Buyer confirms receipt → funds released to seller → deal flips to `RELEASED`
8. Either party can raise a dispute at any point to freeze funds

---

*Built for the DevCareer x Nomba Hackathon 2026 — Virtual Accounts as Infrastructure track*
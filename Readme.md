# EscrowPay

Buyer-protection payment layer for Nigerian peer-to-peer commerce.

Funds are held in a Nomba virtual account until the buyer confirms delivery, then released to the seller.

## Stack
- FastAPI
- PostgreSQL (coming in build sprint)
- Nomba Virtual Account API, Webhooks, Transfers API

## Setup

```bash
cp .env.example .env
# Fill in your Nomba credentials

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints

- `GET /health` — health check
- `POST /webhook` — Nomba webhook receiver

## Built for Nomba x DevCareer Hackathon 2026


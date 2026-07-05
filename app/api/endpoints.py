import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.security import verify_signature
from app.database import get_db
from app.models.models import Deal, DealOriginator, DealStatus, Transaction, TransactionDirection, TransactionStatus, User
from app.schemas.schemas import DealCreate, DealOut
from app.services.nomba import create_virtual_account, verify_and_transfer

router = APIRouter(prefix="/api/deals", tags=["Deals"])


@router.post("/", response_model=DealOut, status_code=status.HTTP_201_CREATED)
async def create_frictionless_deal(payload: DealCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == payload.creator_email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            name=payload.creator_name,
            email=payload.creator_email,
            bank_account_number=payload.creator_bank_account_number,
            bank_code=payload.creator_bank_code
        )
        db.add(user)
        await db.flush()

    account_ref = f"VA-{uuid.uuid4().hex[:12].upper()}"
    account_name = f"Escrow {user.name[:20]}"

    try:
        nomba_data = await create_virtual_account(account_ref, account_name)
        v_account = nomba_data.get("bankAccountNumber")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Nomba virtual account provisioning failed: {str(e)}")

    new_deal = Deal(
        description=payload.description,
        amount=payload.amount,
        originator=payload.originator,
        virtual_account_number=v_account,
        status=DealStatus.CREATED,
        expires_at=datetime.utcnow() + timedelta(hours=48)
    )

    if payload.originator == DealOriginator.BUYER:
        new_deal.buyer_id = user.id
    else:
        new_deal.seller_id = user.id

    db.add(new_deal)
    # TODO: if commit fails after VA creation, log account_ref for manual reconciliation
    await db.commit()
    await db.refresh(new_deal)
    return new_deal


@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(deal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).filter(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/{deal_id}/confirm")
async def confirm_receipt(deal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).filter(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status != DealStatus.FUNDED:
        raise HTTPException(status_code=400, detail=f"Deal cannot be confirmed in status {deal.status.value}")

    # Fetch seller
    seller_result = await db.execute(select(User).filter(User.id == deal.seller_id))
    seller = seller_result.scalar_one_or_none()
    if not seller or not seller.bank_account_number or not seller.bank_code:
        raise HTTPException(status_code=400, detail="Seller bank details missing. Cannot process payout.")

    # Generate payout reference and mark as CONFIRMED before attempting transfer
    merchant_tx_ref = f"PAYOUT-{uuid.uuid4().hex[:8].upper()}"
    deal.status = DealStatus.CONFIRMED
    deal.merchant_tx_ref = merchant_tx_ref
    await db.flush()

    # Attempt payout
    try:
        transfer_response = await verify_and_transfer(
            seller_name=seller.name,
            amount=float(deal.amount),
            account_number=seller.bank_account_number,
            bank_code=seller.bank_code,
            merchant_tx_ref=merchant_tx_ref,
            narration=f"Escrow Payout: {deal.description[:20]}"
        )
        nomba_ref = transfer_response.get("id") or transfer_response.get("reference") or merchant_tx_ref
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Payout failed: {str(e)}")

    # Log outbound transaction as PENDING (confirmed by payout_success webhook later)
    outbound_txn = Transaction(
        deal_id=deal.id,
        amount=deal.amount,
        direction=TransactionDirection.OUTBOUND,
        status=TransactionStatus.PENDING,
        nomba_transaction_id=nomba_ref
    )
    db.add(outbound_txn)

    # Mark as RELEASED synchronously for demo purposes
    deal.status = DealStatus.RELEASED
    await db.commit()
    await db.refresh(deal)

    return {"message": "Receipt confirmed and funds released.", "deal_id": str(deal_id), "payout_ref": nomba_ref}

@router.post("/{deal_id}/dispute")
async def raise_dispute(deal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).filter(Deal.id == deal_id))
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status not in [DealStatus.FUNDED, DealStatus.SHIPPED]:
        raise HTTPException(status_code=400, detail=f"Cannot dispute deal in status {deal.status.value}")

    deal.status = DealStatus.DISPUTED
    await db.commit()
    await db.refresh(deal)
    return {"message": "Dispute raised. Funds are frozen.", "deal_id": str(deal_id)}


# @router.post("/webhook", tags=["Webhook"])
# async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
#     payload = await request.body()

#     # Step 1: Verify HMAC signature
#     signature = request.headers.get("nomba-signature", "")
#     if not verify_signature(payload, signature):
#         raise HTTPException(status_code=401, detail="Invalid webhook signature")

#     try:
#         event = json.loads(payload)
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid JSON payload")

#     event_type = event.get("event", "")

#     # Step 2: Only process payment success events
#     if event_type != "payment_success":
#         return {"received": True}

#     data = event.get("data", {})
#     nomba_tx_id = data.get("transactionId") or data.get("requestId")
#     virtual_account_number = data.get("aliasAccountNumber") or data.get("destinationAccount")
#     amount = Decimal(str(data.get("amount", 0)))

#     # Step 3: Idempotency check — have we already processed this transaction?
#     existing = await db.execute(
#         select(Transaction).filter(Transaction.nomba_transaction_id == nomba_tx_id)
#     )
#     if existing.scalar_one_or_none():
#         # Already processed — return 200 silently
#         return {"received": True}

#     # Step 4: Find the deal by virtual account number
#     result = await db.execute(
#         select(Deal).filter(Deal.virtual_account_number == virtual_account_number)
#     )
#     deal = result.scalar_one_or_none()

#     if not deal:
#         # No matching deal — log and return 200 (don't crash, Nomba will retry on non-200)
#         return {"received": True, "warning": "No deal found for this virtual account"}

#     # Step 5: Create a transaction record
#     transaction = Transaction(
#         deal_id=deal.id,
#         amount=amount,
#         direction=TransactionDirection.INBOUND,
#         status=TransactionStatus.SUCCESS,
#         nomba_transaction_id=nomba_tx_id
#     )
#     db.add(transaction)

#     # Step 6: Update funded_amount — add to existing, don't replace
#     deal.funded_amount = (deal.funded_amount or Decimal("0")) + amount

#     # Step 7: Flip status if fully funded
#     if deal.funded_amount >= deal.amount:
#         deal.status = DealStatus.FUNDED
#     # If underfunded, status stays CREATED — partial payment logged but deal not yet active

#     await db.commit()
#     return {"received": True}



@router.post("/webhook", tags=["Webhook"])
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload_bytes = await request.body()
    headers = dict(request.headers)

    try:
        event = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Verify signature using parsed payload + headers
    if not verify_signature(event, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = event.get("event_type", "")
    if event_type != "transaction.success":
        return {"received": True}

    data = event.get("data", {})
    transaction = data.get("transaction", {})
    merchant = data.get("merchant", {})

    nomba_tx_id = transaction.get("transactionId")
    virtual_account_number = merchant.get("walletId")
    amount = Decimal(str(transaction.get("amount", 0)))

    # Idempotency check
    existing = await db.execute(
        select(Transaction).filter(Transaction.nomba_transaction_id == nomba_tx_id)
    )
    if existing.scalar_one_or_none():
        return {"received": True}

    # Find deal
    result = await db.execute(
        select(Deal).filter(Deal.virtual_account_number == virtual_account_number)
    )
    deal = result.scalar_one_or_none()

    if not deal:
        return {"received": True, "warning": "No deal found for this virtual account"}

    # Create transaction record
    txn = Transaction(
        deal_id=deal.id,
        amount=amount,
        direction=TransactionDirection.INBOUND,
        status=TransactionStatus.SUCCESS,
        nomba_transaction_id=nomba_tx_id
    )
    db.add(txn)

    # Update funded amount
    deal.funded_amount = (deal.funded_amount or Decimal("0")) + amount

    if deal.funded_amount >= deal.amount:
        deal.status = DealStatus.FUNDED

    await db.commit()
    return {"received": True}
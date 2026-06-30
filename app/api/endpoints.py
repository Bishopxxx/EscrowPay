import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, Deal, DealStatus, DealOriginator
from app.schemas.schemas import DealCreate, DealOut
from app.services.nomba import create_virtual_account

router = APIRouter(prefix="/api/deals", tags=["Deals"])

@router.post("/", response_model=DealOut, status_code=status.HTTP_201_CREATED)
async def create_frictionless_deal(payload: DealCreate, db: AsyncSession = Depends(get_db)):
    # 1. Check if this user already exists in our database
    result = await db.execute(select(User).filter(User.email == payload.creator_email))
    user = result.scalar_one_or_none()

    # 2. If they don't exist, create them instantly using the provided bank details
    if not user:
        user = User(
            name=payload.creator_name,
            email=payload.creator_email,
            bank_account_number=payload.creator_bank_account_number,
            bank_code=payload.creator_bank_code
        )
        db.add(user)
        # We use flush() instead of commit() here. 
        # It generates the user.id so we can use it below, without locking the database yet.
        await db.flush() 

    # 3. Generate a dynamic Virtual Account via Nomba
    account_ref = f"VA-{uuid.uuid4().hex[:12].upper()}"
    account_name = f"Escrow {user.name[:20]}"
    
    try:
        nomba_data = await create_virtual_account(account_ref, account_name)
        v_account = nomba_data.get("accountNumber")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Nomba virtual account provisioning failed: {str(e)}")

    # 4. Initialize the Deal
    new_deal = Deal(
        description=payload.description,
        amount=payload.amount,
        originator=payload.originator,
        virtual_account_number=v_account,
        status=DealStatus.CREATED,
        expires_at = datetime.utcnow() + timedelta(hours=48)
    )

    # 5. Route the user to the correct side of the deal
    if payload.originator == DealOriginator.BUYER:
        new_deal.buyer_id = user.id
    else:
        new_deal.seller_id = user.id

    # 6. Save everything permanently
    # TODO: if commit fails after VA creation, log account_ref for manual reconciliation
    db.add(new_deal)
    await db.commit()
    await db.refresh(new_deal)

    return new_deal
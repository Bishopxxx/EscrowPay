import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.models import Deal, DealStatus, Transaction, TransactionDirection, TransactionStatus
from app.services.nomba import verify_and_transfer

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def auto_release_expired_deals():
    """
    Runs every hour. Finds all FUNDED deals past their expiry time
    and automatically releases funds to the seller.
    """
    logger.info("Running auto-release job...")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with AsyncSessionLocal() as db:
        # Find all expired FUNDED deals
        result = await db.execute(
            select(Deal).filter(
                Deal.status == DealStatus.FUNDED,
                Deal.expires_at <= now,
                Deal.seller_id.isnot(None)
            )
        )
        expired_deals = result.scalars().all()

        if not expired_deals:
            logger.info("No expired deals found.")
            return

        logger.info(f"Found {len(expired_deals)} expired deal(s) to auto-release.")

        for deal in expired_deals:
            try:
                # Fetch seller
                from app.models.models import User
                seller_result = await db.execute(
                    select(User).filter(User.id == deal.seller_id)
                )
                seller = seller_result.scalar_one_or_none()

                if not seller or not seller.bank_account_number or not seller.bank_code:
                    logger.warning(f"Deal {deal.id} expired but seller bank details missing — skipping.")
                    continue

                merchant_tx_ref = f"AUTOREL-{uuid.uuid4().hex[:8].upper()}"
                deal.status = DealStatus.CONFIRMED
                deal.merchant_tx_ref = merchant_tx_ref
                await db.flush()

                transfer_response = await verify_and_transfer(
                    seller_name=seller.name,
                    amount=float(deal.amount),
                    account_number=seller.bank_account_number,
                    bank_code=seller.bank_code,
                    merchant_tx_ref=merchant_tx_ref,
                    narration=f"Auto-release: {deal.description[:20]}"
                )

                nomba_ref = transfer_response.get("id") or transfer_response.get("reference") or merchant_tx_ref

                outbound_txn = Transaction(
                    deal_id=deal.id,
                    amount=deal.amount,
                    direction=TransactionDirection.OUTBOUND,
                    status=TransactionStatus.PENDING,
                    nomba_transaction_id=nomba_ref
                )
                db.add(outbound_txn)

                deal.status = DealStatus.RELEASED
                await db.commit()
                logger.info(f"Deal {deal.id} auto-released successfully. Ref: {nomba_ref}")

            except Exception as e:
                await db.rollback()
                logger.error(f"Auto-release failed for deal {deal.id}: {str(e)}")
                continue
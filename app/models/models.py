import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class DealStatus(enum.Enum):
    CREATED = "CREATED"
    FUNDED = "FUNDED"
    SHIPPED = "SHIPPED"
    CONFIRMED = "CONFIRMED"
    RELEASED = "RELEASED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"

class DealOriginator(enum.Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"

class TransactionDirection(enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class TransactionStatus(enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(20), nullable=True)
    bank_code: Mapped[str] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    deals_as_buyer: Mapped[list["Deal"]] = relationship("Deal", foreign_keys="Deal.buyer_id", back_populates="buyer")
    deals_as_seller:Mapped[list["Deal"]] = relationship("Deal", foreign_keys="Deal.seller_id", back_populates="seller")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    funded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[DealStatus] = mapped_column(SAEnum(DealStatus), default=DealStatus.CREATED)
    virtual_account_number: Mapped[str] = mapped_column(String(20), nullable=True)
    merchant_tx_ref: Mapped[str] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    buyer:Mapped["User"] = relationship("User", foreign_keys=[buyer_id], back_populates="deals_as_buyer")
    seller:Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="deals_as_seller")
    transactions:Mapped[list["Transaction"]] = relationship("Transaction", back_populates="deal")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(SAEnum(TransactionDirection), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING)
    nomba_transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    deal:Mapped["Deal"] = relationship("Deal", back_populates="transactions")
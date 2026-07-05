from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from app.models.models import DealOriginator, DealStatus, TransactionStatus, TransactionDirection


class UserCreate(BaseModel):
    # Name should be the same as account number
    name: str = Field(..., min_length=2, max_length=100) 
    email: EmailStr
    bank_account_number: str = Field(..., min_length=10, max_length=10)
    bank_code: str = Field(..., min_length=3, max_length=10)


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    bank_account_number: str | None
    bank_code: str | None

    class Config:
        from_attributes = True


class DealCreate(BaseModel):
    # Creator's personal info
    creator_name: str = Field(..., min_length=2, max_length=100)
    creator_email: EmailStr
    creator_bank_account_number: str = Field(..., min_length=10, max_length=10)
    creator_bank_code: str = Field(..., min_length=3, max_length=10)

    # Deal info
    description: str = Field(..., min_length=5, max_length=255)
    amount: Decimal = Field(..., gt=0)

    # Who is creating this
    originator: DealOriginator


class DealOut(BaseModel):
    id: UUID
    description: str
    amount: Decimal
    funded_amount: Decimal
    status: DealStatus
    virtual_account_number: str | None
    originator: DealOriginator

    class Config:
        from_attributes = True


class DealStatusUpdate(BaseModel):
    status: DealStatus


class TransactionOut(BaseModel):
    id: UUID
    deal_id: UUID
    amount: Decimal
    direction: TransactionDirection 
    status: TransactionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class DealJoin(BaseModel):
    joiner_name: str = Field(..., min_length=2, max_length=100)
    joiner_email: EmailStr
    joiner_bank_account_number: str = Field(..., min_length=10, max_length=10)
    joiner_bank_code: str = Field(..., min_length=3, max_length=10)
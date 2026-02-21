from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class TransactionCategory(str, Enum):
    GROCERIES = "groceries"
    FUEL = "fuel"
    RENT = "rent"
    UTILITIES = "utilities"  # electricity, internet, water, etc.
    SHOPPING = "shopping"
    CLOTHES = "clothes"
    CAR_SERVICE = "car_service"
    CAR_PURCHASE = "car_purchase"
    ENTERTAINMENT = "entertainment"
    DINING = "dining"
    HEALTHCARE = "healthcare"
    INSURANCE = "insurance"
    LOAN_PAYMENT = "loan_payment"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    DEBT_PAYMENT = "debt_payment"
    INCOME = "income"
    SAVINGS = "savings"
    OTHER = "other"


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    LOAN_PAYMENT = "loan_payment"
    DEBT_PAYMENT = "debt_payment"
    TRANSFER = "transfer"


class Transaction(BaseModel):
    date: datetime = Field(..., description="Transaction date")
    amount: float = Field(
        ...,
        description="Transaction amount (positive for income, negative for expenses)",
    )
    category: TransactionCategory = Field(..., description="Transaction category")
    description: str = Field(..., description="Transaction description")
    type: TransactionType = Field(..., description="Transaction type")
    account_type: str | None = Field(
        None, description="Account type (checking, savings, credit_card, etc.)"
    )

    class Config:
        use_enum_values = True

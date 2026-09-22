from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class TransactionCreate(BaseModel):
    transaction_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    transaction_type: Literal["CREDIT", "DEBIT"]

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True
    )


class TransactionResponse(BaseModel):
    transaction_id: str
    customer_id: str
    transaction_type: str
    amount: Decimal
    status: str
    attempts: int

    model_config = ConfigDict(
        from_attributes=True
    )
    

class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    page: int
    page_size: int
    total: int
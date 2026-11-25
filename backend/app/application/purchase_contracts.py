from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator

from app.domain.purchases import parse_amount, parse_trade_date


class PurchaseFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: UUID
    trade_date: date
    quantity: Decimal
    unit_price: Decimal
    commission: Decimal
    currency: Literal["EUR"]

    @field_validator("quantity", "unit_price", "commission", mode="before")
    @classmethod
    def validate_amount(cls, value: object, info: ValidationInfo) -> Decimal:
        return parse_amount(value, allow_zero=info.field_name == "commission")

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_date(cls, value: object) -> date:
        return parse_trade_date(value)


class PurchaseCreate(PurchaseFields):
    request_id: UUID


class PurchaseCorrection(PurchaseFields):
    expected_revision: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PurchaseResponse(BaseModel):
    id: UUID
    account_id: UUID
    listing_id: UUID
    symbol: str
    isin: str | None
    trade_date: date
    quantity: Decimal
    unit_price: Decimal
    commission: Decimal
    currency: str
    revision: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("quantity", "unit_price", "commission")
    def decimal_text(self, value: Decimal) -> str:
        return format(value, "f")


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
    kind: str
    reason: str | None
    before: dict[str, str] | None
    after: dict[str, str]
    created_at: datetime


class ListingResponse(BaseModel):
    id: UUID
    name: str
    symbol: str
    isin: str | None
    mic: str
    currency: str

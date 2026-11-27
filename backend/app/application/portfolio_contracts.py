import re
from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.purchases import parse_trade_date


class BondValuationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    purchase_revision: int = Field(strict=True, ge=1)
    value: Decimal
    paid_interest: Decimal
    observed_on: date

    @field_validator("value", "paid_interest", mode="before")
    @classmethod
    def amount(cls, value: object) -> Decimal:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,20}(?:\.[0-9]{1,2})?", value):
            raise ValueError("Podaj nieujemną kwotę w PLN, do 2 miejsc po kropce.")
        return Decimal(value)

    @field_validator("observed_on", mode="before")
    @classmethod
    def day(cls, value: object) -> date:
        return parse_trade_date(value)

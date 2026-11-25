from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from app.domain.purchases import parse_amount, parse_trade_date


class PriceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: UUID
    request_id: UUID
    price: Decimal
    observed_on: date
    currency: Literal["EUR"]

    @field_validator("price", mode="before", json_schema_input_type=str)
    @classmethod
    def validate_price(cls, value: object) -> Decimal:
        return parse_amount(value)

    @field_validator("observed_on", mode="before")
    @classmethod
    def validate_date(cls, value: object) -> date:
        try:
            return parse_trade_date(value)
        except ValueError as exc:
            raise ValueError(str(exc).replace("zakupu", "wyceny")) from exc


class PriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    listing_id: UUID
    price: Decimal
    currency: str
    observed_on: date
    source: Literal["MANUAL"]
    recorded_at: datetime

    @field_serializer("price")
    def decimal_text(self, value: Decimal) -> str:
        return format(value, "f")


class DisplayPosition(BaseModel):
    cost: str
    average_cost: str | None
    market_value: str | None
    gain: str | None
    gain_percent: str | None


class ValuationResponse(BaseModel):
    account_id: UUID
    listing_id: UUID
    symbol: str
    currency: str
    status: Literal["empty", "unpriced", "outdated", "priced"]
    latest_trade_date: date | None
    quantity: Decimal
    cost: Decimal
    average_cost: Decimal | None
    market_value: Decimal | None
    gain: Decimal | None
    gain_percent: Decimal | None
    price: PriceResponse | None
    history: list[PriceResponse]
    display: DisplayPosition

    @field_serializer("quantity", "cost", "average_cost", "market_value", "gain", "gain_percent")
    def decimal_text(self, value: Decimal | None) -> str | None:
        return format(value, "f") if value is not None else None

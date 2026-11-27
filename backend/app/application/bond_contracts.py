from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.domain.bonds import parse_rate, parse_series
from app.domain.purchases import parse_amount, parse_trade_date


class BondAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["STANDARD", "IKE_BONDS", "IKZE"]

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class BondFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series: str
    trade_date: date
    quantity: int = Field(strict=True, ge=1, le=999999999)
    unit_price: Decimal
    annual_rate: Decimal | None = None
    margin: Decimal | None = None
    source_url: str | None = Field(default=None, max_length=2000)

    @field_validator("series", mode="before")
    @classmethod
    def validate_series(cls, value: object) -> str:
        return parse_series(value)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_date(cls, value: object) -> date:
        return parse_trade_date(value)

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_price(cls, value: object) -> Decimal:
        amount = parse_amount(value)
        if amount.as_tuple().exponent < -2 or amount >= Decimal("10000000000"):
            raise ValueError("Cena w PLN: do 10 cyfr przed i 2 po kropce.")
        return amount

    @field_validator("annual_rate", "margin", mode="before")
    @classmethod
    def validate_rate(cls, value: object) -> Decimal | None:
        return parse_rate(value)

    @field_validator("source_url", mode="before")
    @classmethod
    def validate_source(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ValueError("Podaj adres HTTPS dokumentu emisji.")
        value = value.strip()
        try:
            url = urlsplit(value)
            valid = url.scheme == "https" and url.hostname and not url.username and not url.password
        except ValueError:
            valid = False
        if not valid or any(character.isspace() for character in value):
            raise ValueError("Podaj poprawny adres HTTPS dokumentu emisji.")
        return value

    @model_validator(mode="after")
    def validate_margin(self):
        if self.series.startswith("TOS") and self.margin is not None:
            raise ValueError("TOS ma oprocentowanie stałe; nie podawaj marży inflacyjnej.")
        return self


class BondCreate(BondFields):
    request_id: UUID


class BondCorrection(BondFields):
    expected_revision: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class BondResponse(BaseModel):
    id: UUID
    account_id: UUID
    issue_id: UUID
    terms_version: str
    series: str
    bond_type: str
    term_years: int
    trade_date: date
    quantity: int
    unit_price: Decimal
    cost: Decimal
    currency: Literal["PLN"] = "PLN"
    annual_rate: Decimal | None
    margin: Decimal | None
    source_url: str | None
    terms_status: Literal["MANUAL_UNVERIFIED"] = "MANUAL_UNVERIFIED"
    revision: int
    created_at: datetime

    @field_serializer("unit_price", "cost", "annual_rate", "margin")
    def decimal_text(self, value: Decimal | None) -> str | None:
        return format(value, "f") if value is not None else None

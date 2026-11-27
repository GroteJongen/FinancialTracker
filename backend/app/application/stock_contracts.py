import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=30)
    mic: str
    currency: Literal["PLN", "EUR", "USD"]
    isin: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("symbol", "mic", "isin", mode="before")
    @classmethod
    def clean_identifier(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("symbol")
    @classmethod
    def valid_symbol(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,29}", value):
            raise ValueError("Ticker: litery, cyfry, kropka lub myślnik; do 30 znaków.")
        return value

    @field_validator("mic")
    @classmethod
    def valid_mic(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z0-9]{4}", value):
            raise ValueError("Podaj czteroznakowy kod MIC giełdy.")
        return value

    @field_validator("isin")
    @classmethod
    def valid_isin(cls, value: str | None) -> str | None:
        if not value:
            return None
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value):
            raise ValueError("ISIN powinien mieć 12 znaków; możesz pozostawić to pole puste.")
        return value


class InvestmentAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["STANDARD", "IKE", "IKZE"]
    currency: Literal["PLN", "EUR", "USD"]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

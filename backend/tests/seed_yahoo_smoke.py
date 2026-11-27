"""Explicit synthetic CI quote for the existing SYN.TEST smoke holding, never Yahoo HTTP."""

import os
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.config import get_settings
from app.infrastructure.database import make_engine
from app.infrastructure.models import Instrument, Listing, YahooListing

if __name__ == "__main__":
    if os.environ.get("YAHOO_SYNTHETIC_SMOKE") != "1":
        raise RuntimeError("Only explicitly isolated synthetic CI data is supported.")
    settings = get_settings()
    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session, session.begin():
            listing = session.scalar(
                select(Listing)
                .join(Instrument)
                .where(
                    Listing.symbol == "SYN.TEST",
                    Listing.mic == "XWAR",
                    Instrument.name == "Spolka syntetyczna CI",
                    Instrument.owner_id == settings.local_owner_id,
                )
            )
            if listing is None:
                raise RuntimeError("Expected synthetic CI holding not found.")
            now = datetime.now(UTC)
            session.add(
                YahooListing(
                    listing_id=listing.id,
                    symbol="SYN.TEST.WA",
                    price=Decimal("110"),
                    quoted_at=now,
                    fetched_at=now,
                    attempted_at=now,
                )
            )
        print("PASS: explicit synthetic Yahoo smoke quote saved")
    finally:
        engine.dispose()

"""Separate public-network probe, never run by pytest or against private holdings."""

from app.infrastructure.yahoo import lookup

if __name__ == "__main__":
    quote = lookup("IUSQ.DE", "XETR", "EUR", "ETF")
    print(f"PASS: Yahoo IUSQ.DE / XETR / EUR, market time {quote.quoted_at.isoformat()}")

"""Separate read-only public-network check; excluded from pytest discovery."""
from datetime import date

from app.infrastructure.nbp import lookup

if __name__ == "__main__":
    quote = lookup("EUR", date(2025, 1, 3))
    print(f"PASS: public NBP EUR reference, {quote.effective_on}, table {quote.table_number}")

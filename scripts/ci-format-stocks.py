"""Temporary source formatting export for the constrained local runtime."""
import json
from pathlib import Path

paths = [
    "app/application/stock_contracts.py", "app/application/stocks.py",
    "app/application/purchases.py", "app/application/valuations.py",
    "app/application/purchase_contracts.py", "app/application/valuation_contracts.py",
    "app/infrastructure/models.py", "app/api/routes.py", "app/main.py",
    "migrations/versions/0005_stock_catalogue.py", "tests/conftest.py", "tests/test_stocks.py",
]
for name in paths:
    print("FORMAT_SYNC " + json.dumps({"path": "backend/" + name, "content": Path(name).read_text()}))

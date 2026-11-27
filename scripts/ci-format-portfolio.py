"""Temporary formatting export for the constrained local runtime."""
import json
from pathlib import Path

paths = [
    "app/domain/portfolio.py", "app/application/portfolio_contracts.py",
    "app/application/portfolio.py", "app/infrastructure/nbp.py",
    "app/infrastructure/models.py", "app/api/routes.py", "app/application/bonds.py",
    "migrations/versions/0006_portfolio.py", "tests/conftest.py",
    "tests/test_portfolio_domain.py", "tests/test_portfolio.py", "tests/test_nbp.py",
    "tests/network_nbp.py",
]
for name in paths:
    print("FORMAT_SYNC " + json.dumps({"path": "backend/" + name, "content": Path(name).read_text()}))

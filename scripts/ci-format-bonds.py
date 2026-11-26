"""Temporary formatting export for a workspace without Python 3.13."""
import json
from pathlib import Path

paths = [
    "app/domain/bonds.py", "app/application/bond_contracts.py", "app/application/bonds.py",
    "app/infrastructure/models.py", "app/api/routes.py",
    "migrations/versions/0004_bond_purchases.py", "tests/conftest.py", "tests/test_bonds.py",
]
for name in paths:
    print("FORMAT_SYNC " + json.dumps({"path": "backend/" + name, "content": Path(name).read_text()}))

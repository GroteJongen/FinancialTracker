import base64
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [dict(path=str(p.relative_to(root)), content=p.read_text()) for p in sorted((root / "backend").rglob("*.py")) if "__pycache__" not in p.parts and ".venv" not in p.parts]
print("PORTFOLIOS_FORMAT:" + base64.b64encode(json.dumps(files).encode()).decode())

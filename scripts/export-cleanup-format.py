import base64
import json
from pathlib import Path

files = [dict(path="backend/" + str(p), content=p.read_text()) for p in Path(".").rglob("*.py") if ".venv" not in str(p)]
print("CLEANUP_FORMAT:" + base64.b64encode(json.dumps(files).encode()).decode())

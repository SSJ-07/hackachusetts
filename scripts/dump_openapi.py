"""Print the FastAPI OpenAPI schema as JSON (feeds web/ `npm run gen:api`).

Usage (from web/):  python ../scripts/dump_openapi.py > openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.main import create_app  # noqa: E402

if __name__ == "__main__":
    json.dump(create_app().openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

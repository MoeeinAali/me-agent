"""Write the JSON Schemas the HW and the frontend consume.

Run from backend/:  uv run python ../scripts/export_schema.py
"""

import json
from pathlib import Path

from app.record.schema import Record

DATA = Path(__file__).resolve().parents[1] / "data"


def write(name: str, schema: dict[str, object]) -> None:
    path = DATA / name
    path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    write("record.schema.json", Record.model_json_schema())
    try:
        from app.domain import ChatResponse
    except ImportError:
        return
    write("api.schema.json", ChatResponse.model_json_schema())


if __name__ == "__main__":
    main()

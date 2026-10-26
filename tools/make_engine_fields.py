"""Enable the platform climb fields without changing other engine settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENGINE_FIELDS_PATH = PROJECT_DIR / "project" / "engine_field_values.gbsres"
DESIRED_VALUES: tuple[tuple[str, int | str], ...] = (
    ("FEAT_PLATFORM_COYOTE_TIME", 1),
    ("FEAT_PLATFORM_DROP_THROUGH", 1),
    # Tap, not hold (B-07): while falling, the engine re-arms its 15-frame
    # drop timer every frame the drop input is true, so holding Down+A fell
    # through every one-way shelf below. Tap re-arms only on a new press.
    ("INPUT_PLATFORM_DROP_THROUGH", "DROP_THRU_INPUT_DOWN_JUMP_TAP"),
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def update_engine_fields() -> bool:
    data = load_json(ENGINE_FIELDS_PATH)
    fields = data.get("engineFieldValues")
    if not isinstance(fields, list):
        raise ValueError(f"{ENGINE_FIELDS_PATH} has malformed engineFieldValues")

    desired = dict(DESIRED_VALUES)
    found: set[str] = set()
    for field in fields:
        field_id = field.get("id") if isinstance(field, dict) else None
        if isinstance(field_id, str) and field_id in desired:
            field["value"] = desired[field_id]
            found.add(field_id)
    for field_id, value in DESIRED_VALUES:
        if field_id not in found:
            fields.append({"id": field_id, "value": value})

    contents = json.dumps(data, indent=2) + "\n"
    if ENGINE_FIELDS_PATH.read_text(encoding="utf-8") == contents:
        print(f"unchanged {ENGINE_FIELDS_PATH.relative_to(PROJECT_DIR)}")
        return False
    ENGINE_FIELDS_PATH.write_text(contents, encoding="utf-8")
    print(f"wrote {ENGINE_FIELDS_PATH.relative_to(PROJECT_DIR)}")
    return True


def main() -> None:
    changed = update_engine_fields()
    state = "updated" if changed else "already current"
    print(f"engine fields {state}: coyote time, drop-through, Down+A tap")


if __name__ == "__main__":
    main()

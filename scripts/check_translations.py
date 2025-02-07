"""Check translation files for errors."""

import json
from pathlib import Path
import sys

BASE_TRANSLATION = Path("custom_components/volvo_cars/strings.json")
TRANSLATIONS_DIR = Path("custom_components/volvo_cars/translations")


def _flatten_items(data: dict, parent: str = "") -> dict:
    """Return a dict mapping dot-separated keys to their values."""
    items = {}
    for key, value in data.items():
        full_key = f"{parent}::{key}" if parent else key
        if isinstance(value, dict):
            items.update(_flatten_items(value, full_key))
        else:
            items[full_key] = value
    return items


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def main():
    """Check the translation files for errors."""

    ignore_errors = "--ignore-errors" in sys.argv
    errors = 0

    base_data = _load_json(BASE_TRANSLATION)
    base_items = _flatten_items(base_data)
    base_keys = set(base_items.keys())

    for file in TRANSLATIONS_DIR.glob("*.json"):
        print(f"--- {file.name} ---")

        translation_data = _load_json(file)
        trans_items = _flatten_items(translation_data)
        trans_keys = set(trans_items.keys())

        missing = base_keys - trans_keys
        orphaned = trans_keys - base_keys
        empty_values = [k for k, v in trans_items.items() if _is_empty(v)]

        if missing:
            print("  Missing keys:", sorted(missing))
            errors = errors + len(missing)

        if orphaned:
            print("  Orphaned keys:", sorted(orphaned))
            errors = errors + len(orphaned)

        if empty_values:
            print("  Empty values:", sorted(empty_values))
            errors = errors + len(empty_values)

        print()

    sys.exit(0) if ignore_errors else sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()

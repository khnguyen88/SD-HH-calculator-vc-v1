"""Entry point for the bburg-p-c template builder.

Run from repo root: `python drainage-calculator/build_bburg_template.py`
Output: docs/bburg-p-c-template.xlsx
"""
import sys
from pathlib import Path

# Make the sibling package importable when run as a script
sys.path.insert(0, str(Path(__file__).parent))

from bburg_template_builder.workbook import build_workbook

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "bburg-p-c-template.xlsx"


def main() -> None:
    wb = build_workbook()
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

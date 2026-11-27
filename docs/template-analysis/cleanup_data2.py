"""Clear DATA2 columns D-L in a workbook (Spec 3 pre-work).

Keeps A-C untouched. VLOOKUP ranges on STORM DRAIN COMPS stay as
$A$2:$D$101 — all 178 formulas unchanged. Idempotent.

Usage:
    python cleanup_data2.py <input.xlsx> <output.xlsx>
"""
import sys
from pathlib import Path

import openpyxl


COLUMNS_TO_CLEAR = ("D", "E", "F", "G", "H", "I", "J", "K", "L")
ROW_RANGE = range(1, 102)


def clean_data2(wb):
    ws = wb["DATA2"]
    for col_letter in COLUMNS_TO_CLEAR:
        for r in ROW_RANGE:
            cell = ws[f"{col_letter}{r}"]
            if cell.value is not None:
                cell.value = None
    return wb


def main(src, dst):
    wb = openpyxl.load_workbook(src)
    clean_data2(wb)
    wb.save(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: cleanup_data2.py <src.xlsx> <dst.xlsx>", file=sys.stderr)
        sys.exit(2)
    main(Path(sys.argv[1]), Path(sys.argv[2]))

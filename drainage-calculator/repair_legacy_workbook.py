"""Repair #REF! corruption in docs/bburg-p-c-legacy.xlsx in place.

Three kinds of damage, all from deleted ranges/links:
  * Inlet Spacing_10-yr / _2-yr: the routing-matrix formula in column AK lost its
    first argument. Row 16 in the reference sequence is $A$16, and the summary cells
    (M45:R45) are the row-16 results.
  * ' 10 Yr MoCo HGL': VLOOKUPs index column 17 into a 16-column range (B14:Q28),
    so X/Y resolve to #REF!; extending the range to R restores the Top column.
  * 'HGL 25-yr': every broken cell points at the absent external workbook
    [3]Storm Sewer -10yr.xlsx or at deleted internal ranges. Those cannot be
    recovered locally, so the formulas are cleared to blank rather than left as #REF!.

Run from repo root: python drainage-calculator/repair_legacy_workbook.py
"""
import re
import warnings
from pathlib import Path

from openpyxl import load_workbook

warnings.filterwarnings("ignore", message="Cannot parse header or footer")

LEGACY_PATH = Path(__file__).resolve().parent.parent / "docs" / "bburg-p-c-legacy.xlsx"
INLET_SHEETS = ("Inlet Spacing_10-yr", "Inlet Spacing_2-yr")
MISSING_INLET_ROW = 16


def _repair_inlet_sheet(ws) -> int:
    fixed = 0
    for row in ws.iter_rows():
        for cell in row:
            value = cell.value
            if not isinstance(value, str) or "#REF" not in value:
                continue
            r = cell.row
            expected = f"=IF(EXACT(#REF!,$S{r}),$R{r},0)"
            if value == expected:
                cell.value = f"=IF(EXACT($A${MISSING_INLET_ROW},$S{r}),$R{r},0)"
                fixed += 1
    # Summary row 45 is the row-16 case of the pattern used in rows 42-44, 46+.
    summary = {
        "M45": f"=IF(EXACT($M$41,$M{MISSING_INLET_ROW}),$P45,0)",
        "P45": (f"=(K{MISSING_INLET_ROW}/(2.3*(C{MISSING_INLET_ROW}+1.8*$N$6)))^0.667"
                f"/L{MISSING_INLET_ROW}"),
        "Q45": (f"=((K{MISSING_INLET_ROW}*$N$5)/(0.56*L{MISSING_INLET_ROW}^1.67"
                f"*M{MISSING_INLET_ROW}^0.5))^0.3745"),
        "R45": f"=IF(P{MISSING_INLET_ROW}=P45,100,+AB{MISSING_INLET_ROW}*100)",
    }
    for coord, formula in summary.items():
        if ws[coord].value is not None and "#REF" in str(ws[coord].value):
            ws[coord].value = formula
            fixed += 1
    return fixed


def _repair_moco_hgl(ws) -> int:
    fixed = 0
    for row in ws.iter_rows():
        for cell in row:
            value = cell.value
            if not isinstance(value, str):
                continue
            # Index 17 needs column R in range; index 16 (Q) is unchanged.
            if "'10 Yr Pipe Capacity'!B14:Q" in value:
                cell.value = value.replace("'10 Yr Pipe Capacity'!B14:Q",
                                           "'10 Yr Pipe Capacity'!B14:R")
                value = cell.value
                fixed += 1
            if "#REF" in value:
                cell.value = None
                fixed += 1
    return fixed


def _clear_broken(ws) -> int:
    cleared = 0
    for row in ws.iter_rows():
        for cell in row:
            value = cell.value
            if not isinstance(value, str):
                continue
            if value == "#REF!" or (value.startswith("=") and "#REF" in value):
                cell.value = None
                cleared += 1
    return cleared


def main() -> None:
    wb = load_workbook(LEGACY_PATH)
    total = 0
    for name in INLET_SHEETS:
        if name in wb.sheetnames:
            n = _repair_inlet_sheet(wb[name])
            print(f"{name}: repaired {n}")
            total += n
    if " 10 Yr MoCo HGL" in wb.sheetnames:
        n = _repair_moco_hgl(wb[" 10 Yr MoCo HGL"])
        print(f"' 10 Yr MoCo HGL': repaired {n}")
        total += n
    for name in wb.sheetnames:
        if name not in INLET_SHEETS and name != " 10 Yr MoCo HGL":
            n = _clear_broken(wb[name])
            if n:
                print(f"{name}: cleared {n} unrecoverable cell(s)")
                total += n
    wb.save(LEGACY_PATH)
    print(f"Wrote {LEGACY_PATH} ({total} cells changed)")

    # Verify
    wb = load_workbook(LEGACY_PATH)
    remaining = sum(
        1 for ws in wb.worksheets for row in ws.iter_rows() for cell in row
        if isinstance(cell.value, str) and "#REF" in cell.value
    )
    print(f"Remaining #REF formulas/values: {remaining}")


if __name__ == "__main__":
    main()

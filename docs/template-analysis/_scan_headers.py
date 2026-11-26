"""Verify two doc-correction claims:
  (1) STORM DRAIN COMPS col R vs S header labels
  (2) C_FACTOR col I vs W header labels
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
TARGETS = [HERE.parent / "template_wip_new.xlsx",
           HERE.parent / "template_golden.xlsx"]


def dump_sdc_row8(ws, cols=("R", "S")):
    print(f"  STORM DRAIN COMPS row-8 headers (data headers per Spec 1):")
    for col in cols:
        c = ws[f"{col}8"]
        print(f"    {col}8 = {c.value!r}")


def dump_cfactor_row(ws, row, cols=("I", "W")):
    print(f"  C_FACTOR row-{row} headers:")
    for col in cols:
        c = ws[f"{col}{row}"]
        print(f"    {col}{row} = {c.value!r}")


for p in TARGETS:
    if not p.exists():
        continue
    print(f"\n=== {p.name} ===")
    wb = openpyxl.load_workbook(p, data_only=False)

    sdc = wb["STORM DRAIN COMPS"]
    # Show rows 6-9 for R/S to capture any merged headers.
    print(f"  STORM DRAIN COMPS header rows 6-9 for R/S/AD/AE:")
    for r in range(6, 10):
        for col in ("R", "S", "AD", "AE"):
            v = sdc[f"{col}{r}"].value
            if v is not None:
                print(f"    {col}{r} = {v!r}")

    cf = wb["C_FACTOR"]
    # C_FACTOR header is typically row 4 or 5 (per spec).
    print(f"  C_FACTOR header rows 3-7 for I/W:")
    for r in range(3, 8):
        for col in ("I", "W"):
            v = cf[f"{col}{r}"].value
            if v is not None:
                print(f"    {col}{r} = {v!r}")

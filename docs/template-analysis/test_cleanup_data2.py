"""Verify DATA2 cleanup invariants.

After cleanup:
  - DATA2!A1:C101 unchanged (headers + values preserved).
  - DATA2!D1:L101 completely empty.
  - STORM DRAIN COMPS VLOOKUP formulas unchanged in string form.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"


def _assert_data2_clean(wb):
    ws = wb["DATA2"]
    for col_letter in ("A", "B", "C"):
        v = ws[f"{col_letter}1"].value
        assert v is not None, f"DATA2!{col_letter}1 header missing"
    assert ws["A2"].value == 0
    assert ws["B101"].value == 1
    assert ws["C101"].value == 0.7854
    for col_letter in ("D", "E", "F", "G", "H", "I", "J", "K", "L"):
        for r in range(1, 102):
            v = ws[f"{col_letter}{r}"].value
            assert v in (None, ""), (
                f"DATA2!{col_letter}{r} should be empty, got {v!r}"
            )


def _assert_sdc_vlookup_intact(wb, path_a=False):
    """WIP (pre-Path-A) VLOOKUPs at AZ/BB; golden (Path A, Spec 7) at BC/BE."""
    sdc = wb["STORM DRAIN COMPS"]
    if path_a:
        bc10 = sdc["BC10"].value
        be10 = sdc["BE10"].value
        assert bc10 == '=IFERROR(VLOOKUP(BB10,DATA2!$A$2:$D$101,2),"")', (
            f"BC10 formula drifted: {bc10!r}"
        )
        assert be10 == '=IFERROR(VLOOKUP(BB10,DATA2!$A$2:$D$101,3),"")', (
            f"BE10 formula drifted: {be10!r}"
        )
    else:
        az10 = sdc["AZ10"].value
        bb10 = sdc["BB10"].value
        assert az10 == '=IFERROR(VLOOKUP(AY10,DATA2!$A$2:$D$101,2),"")', (
            f"AZ10 formula drifted: {az10!r}"
        )
        assert bb10 == '=IFERROR(VLOOKUP(AY10,DATA2!$A$2:$D$101,3),"")', (
            f"BB10 formula drifted: {bb10!r}"
        )


def test_wip_data2_cleaned():
    wb = openpyxl.load_workbook(WIP, data_only=False)
    _assert_data2_clean(wb)
    _assert_sdc_vlookup_intact(wb, path_a=False)


def test_golden_data2_cleaned():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    _assert_data2_clean(wb)
    _assert_sdc_vlookup_intact(wb, path_a=True)

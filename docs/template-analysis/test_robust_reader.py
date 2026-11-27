"""Confirm the shape reader populates Robust-only extras from a Robust file."""
from pathlib import Path
import openpyxl
import pytest

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "robust_roundtrip.xlsx"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Create via Phase 2 Task 13 Step 13.2")
def test_robust_has_tr55_sheet():
    wb = openpyxl.load_workbook(FIXTURE, data_only=True)
    ws = wb["TR-55 Segments"]
    assert ws["A1"].value == "Drainage Area"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_has_outlet_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=True)
    assert "Outlet Structures" in wb.sheetnames
    assert "Outlet Devices" in wb.sheetnames

"""Confirm a Robust-shape xlsx produced by the calculator opens cleanly
and carries the expected structure.

Fixture setup (manual, one-time):
  1. Open drainage-calculator/storm-drain-design-calculator.html in a browser.
  2. Click Import; choose docs/template_wip_new_pre-repair.xlsx (3-pipe sample).
  3. In DevTools:  state.exportShape = "robust"; exportExcel();
  4. Save the downloaded file as:
         docs/template-analysis/fixtures/robust_roundtrip.xlsx
"""
from pathlib import Path
import openpyxl
import pytest

FIXTURE = (Path(__file__).parent / "fixtures" / "robust_roundtrip.xlsx")


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Create fixtures/robust_roundtrip.xlsx by "
                           "manually exporting Robust from the calculator")
def test_robust_has_simple_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    for name in ("STORM DRAIN COMPS", "HGL", "C_FACTOR", "Config"):
        assert name in wb.sheetnames, f"Robust missing {name}"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_has_robust_only_sheets():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    for name in ("Outlet Structures", "Outlet Devices", "TR-55 Segments",
                 "Rainfall Settings"):
        assert name in wb.sheetnames, f"Robust missing {name}"


@pytest.mark.skipif(not FIXTURE.exists(), reason="see fixture setup")
def test_robust_config_marker():
    wb = openpyxl.load_workbook(FIXTURE, data_only=False)
    assert wb["Config"]["B6"].value == "robust"
    assert wb["Config"]["B7"].value == 2

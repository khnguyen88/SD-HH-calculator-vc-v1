"""Verify detectShape returns correct value for all fixture shapes.

detectShape is a JS function in drainage-calculator/lib/xlsx-shape-reader.js.
This test exercises the Python-equivalent logic.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"
ROBUST = HERE / "fixtures" / "robust_minimal.xlsx"


def detect_shape_py(sheet_names):
    """Mirrors the JS detectShape logic in xlsx-shape-reader.js."""
    if "STORM DRAIN COMPS" in sheet_names:
        if "Outlet Structures" in sheet_names:
            return "robust"
        return "simple"
    return "unknown"


def test_wip_detects_simple():
    wb = openpyxl.load_workbook(WIP, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "simple"


def test_golden_detects_simple():
    wb = openpyxl.load_workbook(GOLDEN, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "simple"


def test_robust_detects_robust():
    wb = openpyxl.load_workbook(ROBUST, read_only=True)
    assert detect_shape_py(wb.sheetnames) == "robust"


def test_empty_detects_unknown():
    assert detect_shape_py(["Sheet1"]) == "unknown"

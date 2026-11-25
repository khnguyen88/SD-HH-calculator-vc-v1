"""Tests for extract.py - Pass A automated xlsx formula extraction."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "extract.py"
WIP = HERE.parent / "template_wip_new.xlsx"
OUT = HERE / "pass_a.json"


def run_extract():
    subprocess.check_call([sys.executable, str(SCRIPT), str(WIP), str(OUT)])
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_outputs_valid_json_with_sixteen_sheets():
    data = run_extract()
    assert "sheets" in data, "top-level 'sheets' key missing"
    assert len(data["sheets"]) == 16, f"expected 16 sheets, got {len(data['sheets'])}"


def test_each_sheet_has_required_keys():
    data = run_extract()
    required = {"name", "max_row", "max_col", "formula_count",
                "ref_error_count", "tables", "cross_sheet_refs"}
    for sh in data["sheets"]:
        missing = required - set(sh.keys())
        assert not missing, f"sheet {sh.get('name')!r} missing keys {missing}"


def test_hgl_25year_ref_errors_reported():
    data = run_extract()
    hgl25 = next(s for s in data["sheets"] if s["name"] == "HGL(25YEAR)")
    assert hgl25["ref_error_count"] >= 600, (
        f"HGL(25YEAR) should report >=600 #REF! formulas, "
        f"got {hgl25['ref_error_count']}")


def test_broken_defined_names_reported():
    data = run_extract()
    assert "broken_defined_names" in data
    broken = data["broken_defined_names"]
    assert len(broken) >= 25, f"expected >=25 broken names, got {len(broken)}"
    names = {b["name"] for b in broken}
    assert "_DUR1" in names
    assert "_INT1" in names

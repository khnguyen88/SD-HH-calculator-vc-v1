# Tests for repair.py - applies R1-R5 to template_wip_new.xlsx. Shared
# fixture `repaired_wb` lives in conftest.py so T9-T13 can reuse it.
from pathlib import Path

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"


def test_script_runs_and_produces_file(repaired_wb):
    assert WIP.exists()
    assert len(repaired_wb.sheetnames) == 16

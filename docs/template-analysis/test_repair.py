# Tests for repair.py - applies R1-R5 to template_wip_new.xlsx.
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
SCRIPT = HERE / "repair.py"
WIP = HERE.parent / "template_wip_new.xlsx"
BACKUP = HERE.parent / "template_wip_new_pre-repair.xlsx"


@pytest.fixture(scope="module")
def repaired_wb():
    assert BACKUP.exists(), "pre-repair backup missing - Task 1 not run"
    subprocess.check_call([sys.executable, str(SCRIPT), str(BACKUP), str(WIP)])
    return openpyxl.load_workbook(WIP, data_only=False)


def test_script_runs_and_produces_file(repaired_wb):
    assert WIP.exists()
    assert len(repaired_wb.sheetnames) == 16

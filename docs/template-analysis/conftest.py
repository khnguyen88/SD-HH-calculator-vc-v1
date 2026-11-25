# Shared pytest fixtures for the template-analysis test suite.
#
# repaired_wb runs repair.py once per module and loads the result. It
# is intentionally module-scoped: the subprocess cost is non-trivial
# and each test reads from the same workbook snapshot. Tests MUST
# treat the returned workbook as read-only - mutations will leak into
# subsequent tests.
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

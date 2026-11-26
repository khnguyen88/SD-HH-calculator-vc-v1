# Shared pytest fixtures for the template-analysis test suite.
#
# repaired_wb: runs repair.py once per module, loads the result. Reused by
#   test_repair.py. Module-scoped because the subprocess cost is non-trivial.
# golden_built: runs build_golden.py once per module, loads the result.
#   Used by test_build_golden.py. Module-scoped for the same reason.
#
# Both fixtures return read-only workbooks - tests MUST NOT mutate them.
import hashlib
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
REPAIR = HERE / "repair.py"
BUILD_GOLDEN = HERE / "build_golden.py"
WIP = HERE.parent / "template_wip_new.xlsx"
BACKUP = HERE.parent / "template_wip_new_pre-repair.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"

# Pinned SHA-256 of docs/template_wip_new.xlsx. When WIP is intentionally
# changed, update this hash in the same commit so reviewers see the
# golden rebuild is a deliberate consequence of the WIP change.
WIP_SHA256 = "bd39bc7eb38c18b6c558a1d4d2f4075cbe406751ac65897d609f9803897be73c"


@pytest.fixture(scope="module")
def repaired_wb():
    assert BACKUP.exists(), "pre-repair backup missing - Task 1 not run"
    subprocess.check_call([sys.executable, str(REPAIR), str(BACKUP), str(WIP)])
    return openpyxl.load_workbook(WIP, data_only=False)


@pytest.fixture(scope="module")
def golden_built(tmp_path_factory):
    # Pin the WIP input so an unintended WIP change can't silently alter
    # the golden output. When WIP changes on purpose, update WIP_SHA256
    # in the same commit as the WIP change.
    actual = hashlib.sha256(WIP.read_bytes()).hexdigest()
    assert actual == WIP_SHA256, (
        f"WIP input hash drift:\n  expected {WIP_SHA256}\n  got      {actual}\n"
        "If this WIP change is intentional, update WIP_SHA256 in conftest.py."
    )
    out = tmp_path_factory.mktemp("golden") / "template_golden.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(WIP), str(out)])
    return openpyxl.load_workbook(out, data_only=False)


@pytest.fixture(scope="module")
def golden_built_twice(tmp_path_factory, golden_built):
    # Idempotency check: run the builder on its own output, return both
    # workbooks so tests can diff them.
    out2 = tmp_path_factory.mktemp("golden2") / "template_golden_2.xlsx"
    # golden_built is already built at a tmp path; find it by rebuilding
    # into a known first path instead of trusting the fixture's return.
    first = tmp_path_factory.mktemp("golden1") / "template_golden_1.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(WIP), str(first)])
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(first), str(out2)])
    return openpyxl.load_workbook(first, data_only=False), openpyxl.load_workbook(out2, data_only=False)

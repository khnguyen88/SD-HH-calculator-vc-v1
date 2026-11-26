# Shared pytest fixtures for the template-analysis test suite.
#
# Spec-1 context: repair.py INTENTIONALLY overwrites template_wip_new.xlsx
# (that's the contract Spec-1 tests verify). That side effect makes the WIP
# file unsafe to read concurrently.
#
# Spec-2 fixtures therefore work off a FROZEN SNAPSHOT of WIP taken once at
# session start (autouse), before anything else touches the file. `wip_src`
# returns the snapshot path; all Spec-2 fixtures (and in-process per-task
# fixtures in test_build_golden.py) read from it. Spec-1's `repaired_wb`
# fixture continues to operate on the live WIP for its own contract.
import hashlib
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
REPAIR = HERE / "repair.py"
BUILD_GOLDEN = HERE / "build_golden.py"
WIP = HERE.parent / "template_wip_new.xlsx"
BACKUP = HERE.parent / "template_wip_new_pre-repair.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"

# Expected SHA-256 of docs/template_wip_new.xlsx on disk at session start.
# Drift signal only: if the snapshot's SHA differs from this value the
# session emits a warning and continues. Update this value in the same
# commit that intentionally changes WIP.
WIP_SHA256 = "9bb95719fea3b58c253da4984bf07e668170236bb70014365584869e572081e8"

_WIP_SNAPSHOT_HOLDER = {}


@pytest.fixture(scope="session", autouse=True)
def _wip_snapshot(tmp_path_factory):
    # Autouse: materialised before any other fixture in the session. Captures
    # the WIP bytes before Spec-1's repaired_wb fixture can clobber them.
    snap_dir = tmp_path_factory.mktemp("wip_snap")
    snap = snap_dir / "template_wip_new.xlsx"
    shutil.copy(WIP, snap)

    actual = hashlib.sha256(snap.read_bytes()).hexdigest()
    if actual != WIP_SHA256:
        warnings.warn(
            f"WIP SHA drift at session start (expected {WIP_SHA256}, got "
            f"{actual}). If the on-disk WIP changed intentionally, update "
            f"WIP_SHA256 in conftest.py in the same commit.",
            stacklevel=2,
        )

    _WIP_SNAPSHOT_HOLDER["path"] = snap
    return snap


@pytest.fixture(scope="session")
def wip_src(_wip_snapshot):
    # Public handle for the snapshot. Spec-2 fixtures and in-process per-task
    # fixtures use this instead of touching the live WIP.
    return _wip_snapshot


@pytest.fixture(scope="module")
def repaired_wb():
    # Spec-1 contract: repair.py writes to WIP. Unchanged from the Spec-1
    # fixture so test_repair.py keeps working.
    assert BACKUP.exists(), "pre-repair backup missing - Task 1 not run"
    subprocess.check_call([sys.executable, str(REPAIR), str(BACKUP), str(WIP)])
    return openpyxl.load_workbook(WIP, data_only=False)


@pytest.fixture(scope="module")
def golden_built(wip_src, tmp_path_factory):
    out = tmp_path_factory.mktemp("golden") / "template_golden.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(wip_src), str(out)])
    return openpyxl.load_workbook(out, data_only=False)


@pytest.fixture(scope="module")
def golden_built_twice(wip_src, tmp_path_factory):
    # Idempotency check: run the builder on its own output, return both
    # workbooks so tests can diff them.
    first = tmp_path_factory.mktemp("golden1") / "template_golden_1.xlsx"
    out2 = tmp_path_factory.mktemp("golden2") / "template_golden_2.xlsx"
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(wip_src), str(first)])
    subprocess.check_call([sys.executable, str(BUILD_GOLDEN), str(first), str(out2)])
    return (
        openpyxl.load_workbook(first, data_only=False),
        openpyxl.load_workbook(out2, data_only=False),
    )

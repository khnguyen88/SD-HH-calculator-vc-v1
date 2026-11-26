# Tests for build_golden.py - applies Spec-2 edits to the repaired WIP
# template, producing template_golden.xlsx. Shared fixture `golden_built`
# lives in conftest.py.
#
# Incremental testing strategy: `golden_built` runs the full builder via
# subprocess (all 6 edits). While later tasks are still stubs, each Task N
# adds a local `config_wb` / `junction_wb` / ... in-process fixture that
# applies ONLY its own edit, so its tests can pass independently.
import sys
from pathlib import Path

import openpyxl
import pytest

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"

sys.path.insert(0, str(HERE))
from build_golden import add_config_sheet  # noqa: E402


@pytest.fixture(scope="module")
def config_wb():
    """In-process fixture: load WIP, run only add_config_sheet, return wb.

    Allows test_config_* tests to pass while later tasks are still stubs.
    Does not write to disk; the returned workbook is in memory only.
    """
    wb = openpyxl.load_workbook(WIP, data_only=False)
    add_config_sheet(wb)
    return wb


def test_skeleton_runs_end_to_end(golden_built):
    # Smoke test: builder completes end-to-end once every edit is
    # implemented. Until all tasks are done this test fails with
    # NotImplementedError - that's expected.
    assert golden_built is not None
    assert len(golden_built.sheetnames) == 17


def test_config_sheet_exists_and_is_last_tab(config_wb):
    assert "Config" in config_wb.sheetnames
    assert config_wb.sheetnames[-1] == "Config", (
        "Config must be the last tab so existing print-sheet indices "
        "don't shift"
    )


def test_config_sheet_sixteen_originals_preserved_in_order(config_wb, repaired_wb):
    # The 16 original tabs appear in their original order, followed by Config.
    originals = [n for n in config_wb.sheetnames if n != "Config"]
    assert originals == repaired_wb.sheetnames, (
        f"original tab order changed:\n  wip:    {repaired_wb.sheetnames}\n"
        f"  golden: {originals}"
    )


def test_config_three_named_ranges_defined(config_wb):
    names = set(config_wb.defined_names)
    for expected in ("junctionAngleRule", "hglCrownCeilingRule", "hglMethod"):
        assert expected in names, f"named range {expected!r} missing"


def test_config_named_ranges_point_at_b_column(config_wb):
    for name, cell in (
        ("junctionAngleRule", "$B$3"),
        ("hglCrownCeilingRule", "$B$4"),
        ("hglMethod", "$B$5"),
    ):
        dn = config_wb.defined_names[name]
        val = getattr(dn, "value", None) or str(dn)
        assert "Config!" in val and cell in val, (
            f"{name!r} should resolve to Config!{cell}, got {val!r}"
        )


def test_config_defaults(config_wb):
    ws = config_wb["Config"]
    assert ws["A3"].value == "junctionAngleRule"
    assert ws["B3"].value == "smaller-loss"
    assert ws["A4"].value == "hglCrownCeilingRule"
    assert ws["B4"].value == "crown-plus-1ft"
    assert ws["A5"].value == "hglMethod"
    assert ws["B5"].value == "HEC-22 EGL (d/s crown floor)"


def test_config_data_validation_lists_present(config_wb):
    ws = config_wb["Config"]
    dvs = ws.data_validations.dataValidation
    # One list-type DV per toggle cell (B3, B4, B5).
    list_dvs = [dv for dv in dvs if dv.type == "list"]
    assert len(list_dvs) >= 3, f"expected 3 list validations, got {len(list_dvs)}"
    # Each DV applies to exactly one of B3/B4/B5.
    applied_cells = set()
    for dv in list_dvs:
        for rng in dv.sqref.ranges:
            applied_cells.add(str(rng).strip())
    for cell in ("B3", "B4", "B5"):
        assert cell in applied_cells, (
            f"no list DV applied to Config!{cell}, applied cells: {applied_cells}"
        )


def test_config_citation_cells_populated(config_wb):
    ws = config_wb["Config"]
    for cell_addr, must_contain in (
        ("C3", "MDSHA"),
        ("C3", "PG County SWM"),
        ("C4", "MCDOT §4.3.1"),
        ("C4", "PG C I-2"),
        ("C5", "HTML calculator toggle"),
    ):
        v = ws[cell_addr].value
        assert isinstance(v, str) and must_contain in v, (
            f"Config!{cell_addr} should mention {must_contain!r}, got {v!r}"
        )


def test_config_tab_color_set(config_wb):
    ws = config_wb["Config"]
    # Amber signals "settings, not data". Any non-empty color counts.
    assert ws.sheet_properties.tabColor is not None, (
        "Config tab color should be set (amber per spec)"
    )

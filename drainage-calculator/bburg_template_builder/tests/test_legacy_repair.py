"""Tests for the bburg-p-c-legacy.xlsx HGL chain repair.

The legacy ' 10 Yr MoCo HGL' sheet had: an empty Z column (no accumulated
downstream HGL, no tailwater seed), crown floors wired to the wrong pipe ends,
hand-tuned VLOOKUP ranges keyed on the To structure, and 4 of the 12 network
pipes missing entirely. The repair rewires the chain to the golden-tested
template rules (reference_calcs.hgl_walk_step).
"""
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY = REPO_ROOT / "docs" / "bburg-p-c-legacy.xlsx"
SHEET = " 10 Yr MoCo HGL"
CAP = "10 Yr Pipe Capacity"


@pytest.fixture
def repaired_path(tmp_path):
    dst = tmp_path / "legacy-repaired.xlsx"
    shutil.copy(LEGACY, dst)
    from bburg_template_builder.legacy_repair import repair_workbook
    repair_workbook(dst)
    return dst


def test_tailwater_input_present(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    label = str(ws["B4"].value or "")
    assert "TAILWATER" in label.upper()
    assert ws["E4"].value == pytest.approx(66.87)


def test_inverts_are_direct_capacity_refs_not_vlookups(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    for row, cap in [(12, 14), (13, 15), (16, 16), (19, 19), (22, 25), (27, 27)]:
        x = str(ws[f"X{row}"].value)
        ab = str(ws[f"AB{row}"].value)
        assert "VLOOKUP" not in x and "VLOOKUP" not in ab, f"row {row} kept a VLOOKUP"
        # X = d/s invert (cap Q), AB = u/s invert (cap P)
        assert x == f"='{CAP}'!Q{cap}", f"X{row}: {x}"
        assert ab == f"='{CAP}'!P{cap}", f"AB{row}: {ab}"


def test_z_chains_maxifs_with_tailwater_fallback(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    for row in (12, 15, 18, 21, 27):
        z = str(ws[f"Z{row}"].value)
        assert "MAXIFS" in z, f"Z{row} lost the junction MAXIFS: {z}"
        assert "$AE$12:$AE$37" in z and "$C$12:$C$37" in z, z
        assert "$E$4" in z, f"Z{row} missing tailwater fallback: {z}"
        assert "COUNTIF" in z, z


def test_crown_floors_use_max_on_the_correct_ends(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    for row in (12, 15, 21, 27):
        assert str(ws[f"AA{row}"].value) == f"=MAX(Z{row},Y{row})"
        assert str(ws[f"AD{row}"].value) == f"=AA{row}+R{row}"
        assert str(ws[f"AE{row}"].value) == f"=MAX(AD{row},AC{row})"
        assert str(ws[f"AF{row}"].value) == f"=AE{row}"
        # crowns: Y from the d/s invert X, AC from the u/s invert AB
        assert str(ws[f"Y{row}"].value) == f"=X{row}+Q{row}"
        assert str(ws[f"AC{row}"].value) == f"=AB{row}+Q{row}"


def test_missing_pipes_added(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    expected = {13: "A15", 16: "A16", 19: "A19", 22: "A25"}
    for row, cap_ref in expected.items():
        c = str(ws[f"C{row}"].value)
        d = str(ws[f"D{row}"].value)
        assert c == f"='{CAP}'!{cap_ref}", f"C{row}: {c}"
        assert d.startswith(f"='{CAP}'!B"), f"D{row}: {d}"


def test_elliptical_row_overrides_preserved(repaired_path):
    wb = load_workbook(repaired_path)
    ws = wb[SHEET]
    assert str(ws["Q21"].value) == "=33/12"          # crown rise of the 44.5x33 pipe
    assert "44.5" in str(ws["L21"].value)            # equal-area friction diameter
    assert "B15" in str(ws["H21"].value)             # elliptical area from Pipe Properties
    assert ",3,FALSE" in str(ws["U21"].value)        # Kb table column 3


def test_excel_computed_hgl_matches_golden(repaired_path):
    """COM's CalculateFullRebuild + Save bakes Excel's own AE values - the
    workbook must agree with the golden chain, not just the Python mirror."""
    wb = load_workbook(repaired_path, data_only=True)
    ws = wb[SHEET]
    golden = {
        12: 71.000,   # I-3     -> MH-3
        13: 70.670,   # MH-3    -> MH-2
        14: 69.536,   # I-1     -> I-2
        15: 69.521,   # I-2     -> MH-1
        16: 70.010,   # MH-2    -> I-2
        17: 69.300,   # MH-1    -> EX-I-1
        18: 69.000,   # EX-I-1  -> CULVERT
        19: 69.309,   # EX-I-2  -> MH-1
        21: 69.850,   # I-7     -> CULVERT
        22: 73.508,   # I-6     -> I-5
        26: 73.490,   # I-5     -> I-4
        27: 72.868,   # I-4     -> CULVERT
    }
    for row, want in golden.items():
        got = ws[f"AE{row}"].value
        assert got is not None, f"AE{row} has no cached value"
        assert got == pytest.approx(want, abs=0.005), \
            f"AE{row}: expected {want}, Excel computed {got:.3f}"


def test_chain_matches_golden_values(repaired_path):
    """Evaluate the repaired chain from the workbook's own cached capacity values."""
    from bburg_template_builder.legacy_repair import evaluate_chain
    got = evaluate_chain(repaired_path)
    golden = {
        ("I-3", "MH-3"): 71.000,
        ("MH-3", "MH-2"): 70.670,
        ("MH-2", "I-2"): 70.010,
        ("I-1", "I-2"): 69.536,
        ("I-2", "MH-1"): 69.521,
        ("EX-I-2", "MH-1"): 69.309,
        ("MH-1", "EX-I-1"): 69.300,
        ("EX-I-1", "CULVERT"): 69.000,
        ("I-7", "CULVERT"): 69.850,
        ("I-6", "I-5"): 73.508,
        ("I-5", "I-4"): 73.490,
        ("I-4", "CULVERT"): 72.868,
    }
    assert len(got) == 12, f"expected 12 pipe rows, got {len(got)}: {list(got)}"
    for key, want in golden.items():
        assert got[key] == pytest.approx(want, abs=0.005), \
            f"{key}: expected {want}, got {got[key]:.3f}"


def test_repair_is_idempotent(tmp_path):
    dst = tmp_path / "twice.xlsx"
    shutil.copy(LEGACY, dst)
    from bburg_template_builder.legacy_repair import repair_workbook
    repair_workbook(dst)
    repair_workbook(dst)
    wb = load_workbook(dst)
    assert str(wb[SHEET]["Z12"].value).count("MAXIFS") == 1

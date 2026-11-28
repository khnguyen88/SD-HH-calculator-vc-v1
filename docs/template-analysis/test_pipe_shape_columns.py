"""Spec 7 Path B: Pipe Shape / Width (in) / # columns on STORM DRAIN COMPS.

Columns are appended at BF/BG/BH/BI/BJ/BK (last used was BE). Formulas
on T, V, Y, AV, AW are rewritten to be shape-aware and multi-barrel aware.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def test_new_column_headers_present():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    assert sdc["N8"].value == "Size/Height (in)", \
        f"N8 header not updated: {sdc['N8'].value!r}"
    assert sdc["BF8"].value == "Pipe Shape"
    assert sdc["BG8"].value == "Width (in)"
    assert sdc["BH8"].value == "#"
    assert sdc["BI8"].value == "A (sf per barrel)"
    assert sdc["BJ8"].value == "R (ft per barrel)"
    assert sdc["BK8"].value == "D_eq (in)"


def test_pipe_shape_defaults_on_all_rows():
    """BF default = 'circular', BG blank, BH = 1 on every data row."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    for r in range(10, 99):
        assert sdc[f"BF{r}"].value == "circular", \
            f"BF{r} default should be 'circular', got {sdc[f'BF{r}'].value!r}"
        assert sdc[f"BG{r}"].value in (None, ""), \
            f"BG{r} should be blank by default, got {sdc[f'BG{r}'].value!r}"
        assert sdc[f"BH{r}"].value == 1, \
            f"BH{r} default should be 1, got {sdc[f'BH{r}'].value!r}"


def test_helper_formulas_branch_on_shape():
    """BI (area), BJ (hydraulic radius), BK (equivalent diameter) all
    branch on BF={rectangular, elliptical, else-circular}."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    bi10 = str(sdc["BI10"].value)
    bk10 = str(sdc["BK10"].value)
    bj10 = str(sdc["BJ10"].value)
    for formula, col_label in ((bi10, "BI"), (bk10, "BK")):
        assert 'BF10="rectangular"' in formula, (
            f"{col_label}10 missing rectangular branch: {formula!r}"
        )
        assert 'BF10="elliptical"' in formula, (
            f"{col_label}10 missing elliptical branch: {formula!r}"
        )
    assert "BK10" in bj10, f"BJ10 should derive from BK10: {bj10!r}"


def test_full_flow_capacity_formula_uses_helpers():
    """T (full flow) uses BI (area) and BJ (radius) with BH (barrels) multiplier."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    t10 = str(sdc["T10"].value)
    assert "BH10" in t10, f"T10 missing BH (barrel count) multiplier: {t10!r}"
    assert "BI10" in t10, f"T10 missing BI (area) reference: {t10!r}"
    assert "BJ10" in t10, f"T10 missing BJ (radius) reference: {t10!r}"


def test_friction_slope_formula_uses_per_barrel_q():
    """Y (friction slope) divides design Q by BH for per-barrel analysis."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    y10 = str(sdc["Y10"].value)
    assert "M10/BH10" in y10, (
        f"Y10 should divide design Q (M) by BH (barrel count): {y10!r}"
    )


def test_partial_flow_inputs_use_new_columns():
    """AV (Q per barrel) = M/BH; AW (effective D) = BK (shape-aware D_eq)."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    av10 = str(sdc["AV10"].value)
    aw10 = str(sdc["AW10"].value)
    assert "M10/BH10" in av10, f"AV10 should be M10/BH10: {av10!r}"
    assert aw10 == "=BK10", f"AW10 should pull from BK10: {aw10!r}"

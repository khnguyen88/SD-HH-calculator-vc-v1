"""Spec 7 Path A: Pipe Shape / Width (in) / # columns inserted at O/P/Q
on STORM DRAIN COMPS, right after N (Size/Height). All existing SDC
columns at col 15+ shifted right by 3. Helper columns BI/BJ/BK contain
shape-aware Area, Hydraulic Radius, and Equivalent Diameter formulas.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def test_new_column_headers_present():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    # Per user: shape first, then height/size, then width, then #.
    assert sdc["N8"].value == "Pipe Shape"
    assert sdc["O8"].value == "Size/Height (in)"
    assert sdc["P8"].value == "Width (in)"
    assert sdc["Q8"].value == "#"
    assert sdc["R8"].value == "Length (Ft)"
    assert sdc["S8"].value == "U/S Invert Elevation"
    assert sdc["T8"].value == "D/S Invert Elevation"
    assert sdc["U8"].value == "Angle Out of Pipe (Deg) - Whole #"
    assert sdc["V8"].value == "Manning Coeff"
    assert sdc["BI8"].value == "A (sf per barrel)"
    assert sdc["BJ8"].value == "R (ft per barrel)"
    assert sdc["BK8"].value == "D_eq (in)"


def test_pipe_shape_defaults_on_all_rows():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    for r in range(10, 99):
        assert sdc[f"N{r}"].value == "circular"
        assert sdc[f"P{r}"].value in (None, "")
        assert sdc[f"Q{r}"].value == 1


def test_pipe_shape_dropdown_data_validation():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    found_dv = False
    for dv in sdc.data_validations.dataValidation:
        if dv.type != "list":
            continue
        for rng in dv.sqref.ranges:
            cr = str(rng)
            if cr.startswith("N"):
                found_dv = True
                assert "circular" in str(dv.formula1)
                assert "elliptical" in str(dv.formula1)
                assert "rectangular" in str(dv.formula1)
    assert found_dv, "No list-type data validation found on N (Pipe Shape)"


def test_helper_formulas_branch_on_shape():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    bi10 = str(sdc["BI10"].value)
    bk10 = str(sdc["BK10"].value)
    bj10 = str(sdc["BJ10"].value)
    for formula, col in ((bi10, "BI"), (bk10, "BK")):
        assert 'N10="rectangular"' in formula, f"{col}10: {formula!r}"
        assert 'N10="elliptical"' in formula, f"{col}10: {formula!r}"
    assert "BK10" in bj10


def test_full_flow_capacity_formula_uses_helpers():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    w10 = str(sdc["W10"].value)
    assert "Q10" in w10, f"W10 missing Q (barrel count): {w10!r}"
    assert "BI10" in w10
    assert "BJ10" in w10


def test_friction_slope_formula_uses_per_barrel_q():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    ab10 = str(sdc["AB10"].value)
    assert "M10/Q10" in ab10, f"AB10: {ab10!r}"


def test_partial_flow_inputs_use_new_columns():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    sdc = wb["STORM DRAIN COMPS"]
    ay10 = str(sdc["AY10"].value)
    az10 = str(sdc["AZ10"].value)
    assert "M10/Q10" in ay10
    assert az10 == "=BK10"

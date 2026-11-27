"""HGL cols K/M formulas contain both method branches after Spec 3.

Row range: 7-91 (85 populated rows on both HGL and HGL(25YEAR)).
Column K is the only column where the two branches differ in body;
M uses the hglMethod IF-wrap defensively (both branches equal).

Column G on HGL / HGL(25YEAR) is a values-only input column (no
formulas in rows 7-91) — the G branch-check guards against a future
rewrite silently populating G with non-branched formulas.
"""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def test_hgl_g_is_values_only_no_hgl_method_needed():
    """Col G on HGL rows 7-91 has no formulas — nothing to branch.

    Regression: if a future task introduces formulas into G, they
    must also be hglMethod-wrapped (and this test updated to check
    them, matching the K/M pattern).
    """
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    formula_rows = []
    for r in range(7, 92):
        v = ws[f"G{r}"].value
        if v is not None and str(v).startswith("="):
            formula_rows.append((r, v))
    assert not formula_rows, (
        "HGL!G now contains formulas — update this test to assert "
        f"hglMethod branching on them. Found: {formula_rows[:3]!r}"
    )


def test_hgl_k_formulas_branch_on_hgl_method():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        v = ws[f"K{r}"].value
        if v is None or not str(v).startswith("="):
            continue
        assert "hglMethod" in str(v), f"HGL!K{r} missing hglMethod branch: {v!r}"
        hits += 1
    assert hits > 0


def test_hgl_m_formulas_branch_on_hgl_method():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        v = ws[f"M{r}"].value
        if v is None or not str(v).startswith("="):
            continue
        assert "hglMethod" in str(v), f"HGL!M{r} missing hglMethod branch: {v!r}"
        hits += 1
    assert hits > 0


def test_hgl_25yr_same_pattern():
    """HGL(25YEAR) cols K/M follow the same hglMethod wrap pattern.

    Col G on HGL(25YEAR) is also values-only (see
    test_hgl_g_is_values_only_no_hgl_method_needed).
    """
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    if "HGL(25YEAR)" not in wb.sheetnames:
        return
    ws = wb["HGL(25YEAR)"]
    # G should be values-only here too.
    g_formulas = [
        (r, ws[f"G{r}"].value) for r in range(7, 92)
        if ws[f"G{r}"].value is not None
        and str(ws[f"G{r}"].value).startswith("=")
    ]
    assert not g_formulas, (
        "HGL(25YEAR)!G now contains formulas — update this test. "
        f"Found: {g_formulas[:3]!r}"
    )
    for r in range(7, 92):
        for col in ("K", "M"):
            v = ws[f"{col}{r}"].value
            if v is None or not str(v).startswith("="):
                continue
            assert "hglMethod" in str(v), (
                f"HGL(25YEAR)!{col}{r} missing hglMethod branch: {v!r}"
            )


def test_hgl_k_branches_differ():
    """Regression: col K's two IF branches must have DIFFERENT bodies.

    Legacy branch keeps the D{r} us_crown term inside MAX(...);
    HEC-22 branch strips it. If both branches are identical, the
    toggle has no effect and the Spec 2 label-only behavior is still
    in place.
    """
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    found_differing = False
    for r in range(7, 92):
        v = ws[f"K{r}"].value
        if v is None or not str(v).startswith("="):
            continue
        # Formula shape: =IF(hglMethod="legacy...", <legacy>, <hec22>)
        # Look for the comma that separates the two branches at the
        # top-level of the IF — a crude but adequate check: the legacy
        # body contains "D"+str(r) and the hec22 variant does not.
        s = str(v)
        # Split roughly; this is a smoke test, not a parser.
        if f"D{r}" in s:
            # Count occurrences — should be 1 (legacy only), not 2.
            legacy_count = s.count(f"D{r}")
            if legacy_count == 1:
                found_differing = True
                break
    assert found_differing, (
        "HGL col K: no row shows the us_crown stripping — Task 18's "
        "formula rewrite may not be active on K."
    )

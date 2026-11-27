"""HGL cols G/K/M formulas contain both method branches after Spec 3.

Row range: 7-91 (85 populated rows on both HGL and HGL(25YEAR)).
Col G is stored as a CSE ArrayFormula; cols K and M are plain string
formulas. The _formula_text helper normalizes both.

Column K is the only column where the two branches differ in body
(legacy keeps D{r} us_crown; HEC-22 strips it). G and M use the
hglMethod IF-wrap defensively — both branches equal.
"""
from pathlib import Path
import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def _formula_text(v):
    """Return the formula source string for either a plain-text formula
    cell (starts with '=') or an openpyxl ArrayFormula CSE object."""
    if isinstance(v, ArrayFormula):
        return v.text
    if isinstance(v, str) and v.startswith("="):
        return v
    return None


def test_hgl_g_formulas_branch_on_hgl_method():
    """Col G on HGL rows 7-91 is CSE ArrayFormula — must carry hglMethod
    wrapping just like K and M. Task 18 handles ArrayFormula explicitly."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        text = _formula_text(ws[f"G{r}"].value)
        if text is None:
            continue
        assert "hglMethod" in text, f"HGL!G{r} missing hglMethod branch: {text!r}"
        hits += 1
    assert hits > 0, "No formulas found on HGL col G"


def test_hgl_k_formulas_branch_on_hgl_method():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        text = _formula_text(ws[f"K{r}"].value)
        if text is None:
            continue
        assert "hglMethod" in text, f"HGL!K{r} missing hglMethod branch: {text!r}"
        hits += 1
    assert hits > 0


def test_hgl_m_formulas_branch_on_hgl_method():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        text = _formula_text(ws[f"M{r}"].value)
        if text is None:
            continue
        assert "hglMethod" in text, f"HGL!M{r} missing hglMethod branch: {text!r}"
        hits += 1
    assert hits > 0


def test_hgl_25yr_same_pattern():
    """HGL(25YEAR) cols G/K/M follow the same hglMethod wrap pattern."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    if "HGL(25YEAR)" not in wb.sheetnames:
        return
    ws = wb["HGL(25YEAR)"]
    for col in ("G", "K", "M"):
        hits = 0
        for r in range(7, 92):
            text = _formula_text(ws[f"{col}{r}"].value)
            if text is None:
                continue
            assert "hglMethod" in text, (
                f"HGL(25YEAR)!{col}{r} missing hglMethod branch: {text!r}"
            )
            hits += 1
        assert hits > 0, f"No formulas found on HGL(25YEAR) col {col}"


def test_hgl_k_branches_differ():
    """Regression: col K's two IF branches must have DIFFERENT bodies.

    Legacy branch keeps the D{r} us_crown term inside MAX(...);
    HEC-22 branch strips it.
    """
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    found_differing = False
    for r in range(7, 92):
        text = _formula_text(ws[f"K{r}"].value)
        if text is None:
            continue
        if f"D{r}" in text:
            if text.count(f"D{r}") == 1:
                found_differing = True
                break
    assert found_differing, (
        "HGL col K: no row shows the us_crown stripping — Task 18's "
        "formula rewrite may not be active on K."
    )

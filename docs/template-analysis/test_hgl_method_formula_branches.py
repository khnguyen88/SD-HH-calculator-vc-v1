"""Spec 6: HGL formulas are HEC-22 only (no `hglMethod` toggle).

Previously (Spec 3 Task 18) this file asserted both method branches
inside each HGL col G/K/M formula. Spec 6 drops the legacy both-end
crown floor method, so formulas simplify to plain HEC-22.

Row range: 7-91 (85 populated rows on both HGL and HGL(25YEAR)).
Col G is CSE ArrayFormula; cols K and M are plain string formulas.
"""
from pathlib import Path
import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "template_golden.xlsx"


def _formula_text(v):
    """Return the formula source for either a plain-text formula cell
    (starts with '=') or an ArrayFormula CSE object."""
    if isinstance(v, ArrayFormula):
        return v.text
    if isinstance(v, str) and v.startswith("="):
        return v
    return None


def test_hgl_formulas_no_longer_carry_hgl_method_literal():
    """No populated HGL/HGL(25YEAR) G/K/M formula should mention hglMethod
    or 'legacy both-end crown floor' after Spec 6."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        for col in ("G", "K", "M"):
            for r in range(7, 92):
                text = _formula_text(ws[f"{col}{r}"].value)
                if text is None:
                    continue
                assert "hglMethod" not in text, (
                    f"{sheet_name}!{col}{r} still references hglMethod: {text!r}"
                )
                assert "legacy both-end crown floor" not in text, (
                    f"{sheet_name}!{col}{r} still references legacy label: {text!r}"
                )


def test_hgl_k_is_plain_hec22_max():
    """Col K should be =IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"") — HEC-22
    only, no us_crown (D{r}) term."""
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    ws = wb["HGL"]
    hits = 0
    for r in range(7, 92):
        text = _formula_text(ws[f"K{r}"].value)
        if text is None:
            continue
        expected = f'=IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"")'
        assert text == expected, (
            f"HGL!K{r} unexpected formula.\n  expected: {expected!r}\n  got:      {text!r}"
        )
        assert f"D{r}" not in text, f"HGL!K{r} still carries us_crown D{r}: {text!r}"
        hits += 1
    assert hits > 0, "No populated K rows on HGL — check fixture setup"


def test_hgl_25yr_k_is_plain_hec22_max():
    wb = openpyxl.load_workbook(GOLDEN, data_only=False)
    if "HGL(25YEAR)" not in wb.sheetnames:
        return
    ws = wb["HGL(25YEAR)"]
    hits = 0
    for r in range(7, 92):
        text = _formula_text(ws[f"K{r}"].value)
        if text is None:
            continue
        expected = f'=IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"")'
        assert text == expected, (
            f"HGL(25YEAR)!K{r} unexpected formula.\n  expected: {expected!r}\n  got:      {text!r}"
        )
        hits += 1
    assert hits > 0

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

sys.path.insert(0, str(HERE))
from build_golden import (
    add_config_sheet,
    add_hgl_crown_ceiling_checks,
    add_u7_small_area_tc_lookup,
    annotate_equations_sheet,
    annotate_hgl_method,
    rewire_junction_angle_rule,
)  # noqa: E402


@pytest.fixture(scope="module")
def config_wb(wip_src):
    """In-process fixture: load WIP snapshot, run only add_config_sheet, return wb.

    Allows test_config_* tests to pass while later tasks are still stubs.
    Uses the session-wide WIP snapshot from conftest.py (wip_src) so Spec-1's
    repaired_wb fixture can't clobber the bytes mid-session.
    """
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    return wb


@pytest.fixture(scope="module")
def junction_wb(wip_src):
    """In-process fixture: Task 1 + Task 2 edits only."""
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
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


def test_config_sheet_sixteen_originals_preserved_in_order(config_wb, wip_src):
    # The 16 original tabs appear in their original order, followed by Config.
    # Read sheet names from the WIP snapshot directly instead of depending on
    # Spec-1's repaired_wb fixture (which writes to the live WIP file and
    # conflicts with external file holders).
    wip_wb = openpyxl.load_workbook(wip_src, data_only=False)
    originals = [n for n in config_wb.sheetnames if n != "Config"]
    assert originals == wip_wb.sheetnames, (
        f"original tab order changed:\n  wip:    {wip_wb.sheetnames}\n"
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


# ---------------------------------------------------------------------------
# Task 2: rewire_junction_angle_rule
# ---------------------------------------------------------------------------

def test_junction_wip_has_max_pattern_originally(wip_src):
    # Control test: confirms the WIP's AD10 still carries the MAX pattern
    # before Edit 2 runs. Reads wip_src (snapshot), not repaired_wb, to stay
    # isolated from Spec-1 fixture side effects.
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    ws = wb["STORM DRAIN COMPS"]
    ad10 = ws["AD10"].value
    text = getattr(ad10, "text", None) or (ad10 if isinstance(ad10, str) else None)
    assert text is not None, f"AD10 unexpected type: {type(ad10)}"
    assert "MAX(IF($AQ$10:$AQ$98=$AR10,$R$10:$R$98))" in text, (
        f"WIP AD10 drifted - expected MAX-of-angle-by-max-Lv pattern, got {text!r}"
    )


def test_junction_ad_formula_references_toggle(junction_wb):
    ws = junction_wb["STORM DRAIN COMPS"]
    ad10 = ws["AD10"].value
    text = getattr(ad10, "text", None) or (ad10 if isinstance(ad10, str) else None)
    assert text is not None and "junctionAngleRule" in text, (
        f"golden AD10 should pivot on junctionAngleRule, got {text!r}"
    )


def test_junction_ad_formula_has_both_branches(junction_wb):
    ws = junction_wb["STORM DRAIN COMPS"]
    text = getattr(ws["AD10"].value, "text", None) or str(ws["AD10"].value)
    # smaller-loss branch picks the angle matching the MIN of positive Lv.
    assert "smaller-loss" in text, f"missing smaller-loss branch: {text!r}"
    # larger-loss branch preserves the original MAX pattern.
    assert "MAX(IF($AQ$10:$AQ$98=$AR10,$R$10:$R$98))" in text, (
        f"larger-loss branch should preserve WIP MAX pattern: {text!r}"
    )


def test_junction_ad_formula_applied_all_data_rows(junction_wb):
    ws = junction_wb["STORM DRAIN COMPS"]
    # Rows 10-98 all have an AD formula referencing junctionAngleRule.
    for r in range(10, 99):
        v = ws.cell(row=r, column=30).value  # AD = col 30
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text is not None and "junctionAngleRule" in text, (
            f"AD{r} missing toggle reference: {text!r}"
        )


def test_junction_ar_min_helper_populated(junction_wb):
    # The AR_min helper column exists somewhere and carries a MIN-of-positive-
    # Lv formula on every data row. Default placement is BE if AJ is occupied.
    ws = junction_wb["STORM DRAIN COMPS"]
    helper_col = None
    for col in range(1, ws.max_column + 2):
        v = ws.cell(row=10, column=col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        if isinstance(text, str) and "MIN(IF((" in text and "$AQ$10:$AQ$98>0" in text:
            helper_col = col
            break
    assert helper_col is not None, "AR_min helper column not found on row 10"
    # Rows 10-98 all carry the helper formula.
    for r in range(10, 99):
        v = ws.cell(row=r, column=helper_col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text and "MIN" in text, f"helper col row {r} missing MIN: {text!r}"


def test_junction_helper_cell_was_empty_in_wip(junction_wb, wip_src):
    # The chosen helper column must NOT have overwritten a user-typed value
    # in the WIP. AJ in WIP is a Table4 pass-through formula on every row;
    # if the builder chose AJ as the helper, something went wrong.
    gws = junction_wb["STORM DRAIN COMPS"]
    wip_wb = openpyxl.load_workbook(wip_src, data_only=False)
    wws = wip_wb["STORM DRAIN COMPS"]
    helper_col = None
    for col in range(1, gws.max_column + 2):
        v = gws.cell(row=10, column=col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        if isinstance(text, str) and "MIN(IF((" in text:
            helper_col = col
            break
    assert helper_col is not None
    for r in range(10, 20):
        wip_val = wws.cell(row=r, column=helper_col).value
        wip_text = getattr(wip_val, "text", None) or (wip_val if isinstance(wip_val, str) else None)
        if wip_text is not None and wip_text != "":
            raise AssertionError(
                f"helper column (col {helper_col}) had pre-existing content at row {r}: "
                f"{wip_text!r} - builder should have chosen a later empty column"
            )


def test_junction_rewire_idempotent(wip_src):
    # Running rewire_junction_angle_rule twice must produce identical output
    # and leave no orphaned helper columns in the BE-BT horizon.
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    ws = wb["STORM DRAIN COMPS"]

    def snap(col):
        return [
            (getattr(ws.cell(row=r, column=col).value, "text", None)
             or (ws.cell(row=r, column=col).value
                 if isinstance(ws.cell(row=r, column=col).value, str)
                 else None))
            for r in range(10, 99)
        ]

    ad_before = snap(30)   # AD
    be_before = snap(57)   # BE

    rewire_junction_angle_rule(wb)

    ad_after = snap(30)
    be_after = snap(57)

    assert ad_before == ad_after, "AD column drifted on re-run"
    assert be_before == be_after, "BE helper column drifted on re-run"

    # No orphan helpers in BF-BT after re-run.
    from openpyxl.utils import column_index_from_string, get_column_letter
    for col in range(column_index_from_string("BF"), column_index_from_string("BT") + 1):
        label = ws.cell(row=8, column=col).value
        assert label != "Lv_min helper (Spec 2, for smaller-loss toggle)", (
            f"stale helper label found at {get_column_letter(col)}8"
        )


# ---------------------------------------------------------------------------
# Task 3: add_hgl_crown_ceiling_checks
# ---------------------------------------------------------------------------
from openpyxl.utils import column_index_from_string, get_column_letter  # noqa: E402

CLEARANCE_HEADERS = ("Crown+1ft Check", "Rim-1ft Check", "Clearance Governing")


@pytest.fixture(scope="module")
def hgl_clearance_wb(wip_src):
    """In-process fixture: Tasks 1 + 2 + 3 edits only."""
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    return wb


@pytest.fixture(scope="module")
def hgl_method_wb(wip_src):
    """In-process fixture: Tasks 1 + 2 + 3 + 4 edits only."""
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    return wb


def _find_clearance_cols(ws, header_row=6):
    found = {}
    for col in range(1, ws.max_column + 2):
        v = ws.cell(row=header_row, column=col).value
        if isinstance(v, str) and v in CLEARANCE_HEADERS:
            found[v] = col
    return found


def test_hgl_clearance_three_columns_added(hgl_clearance_wb):
    ws = hgl_clearance_wb["HGL"]
    cols = _find_clearance_cols(ws)
    for hdr in CLEARANCE_HEADERS:
        assert hdr in cols, f"HGL missing clearance column {hdr!r}"


def test_hgl_25year_clearance_three_columns_added(hgl_clearance_wb):
    ws = hgl_clearance_wb["HGL(25YEAR)"]
    cols = _find_clearance_cols(ws)
    for hdr in CLEARANCE_HEADERS:
        assert hdr in cols, f"HGL(25YEAR) missing clearance column {hdr!r}"


def test_hgl_clearance_governing_references_toggle(hgl_clearance_wb):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = hgl_clearance_wb[sheet_name]
        cols = _find_clearance_cols(ws)
        gov_col = cols["Clearance Governing"]
        v = ws.cell(row=7, column=gov_col).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        assert text and "hglCrownCeilingRule" in text, (
            f"{sheet_name} Clearance Governing row 7 missing toggle: {text!r}"
        )


def test_hgl_clearance_formulas_applied_all_data_rows(hgl_clearance_wb):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = hgl_clearance_wb[sheet_name]
        cols = _find_clearance_cols(ws)
        for hdr in CLEARANCE_HEADERS:
            col = cols[hdr]
            for r in range(7, 92):
                v = ws.cell(row=r, column=col).value
                text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
                assert text and text.startswith("="), (
                    f"{sheet_name}!{get_column_letter(col)}{r} missing "
                    f"formula for {hdr!r}: {text!r}"
                )


def test_hgl_print_area_includes_new_columns(hgl_clearance_wb):
    import re
    ws = hgl_clearance_wb["HGL"]
    cols = _find_clearance_cols(ws)
    last_new_col = max(cols.values())
    pa = ws.print_area or ""
    m = re.search(r"\$([A-Z]+)\$\d+:\$([A-Z]+)\$\d+", pa)
    assert m, f"HGL print_area malformed or unset: {pa!r}"
    end_col_idx = column_index_from_string(m.group(2))
    assert end_col_idx >= last_new_col, (
        f"HGL print_area ends at col {m.group(2)} (idx {end_col_idx}); "
        f"clearance cols end at {last_new_col}"
    )


def test_hgl_25year_print_area_set(hgl_clearance_wb):
    ws = hgl_clearance_wb["HGL(25YEAR)"]
    assert ws.print_area, "HGL(25YEAR) print_area should be set by Edit 3"


def test_hgl_clearance_idempotent(wip_src):
    # Running Edit 3 twice must not add duplicate columns or drift values.
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)

    def snapshot(ws):
        cols = _find_clearance_cols(ws)
        return {
            hdr: [
                getattr(ws.cell(row=r, column=col).value, "text", None)
                or (ws.cell(row=r, column=col).value
                    if isinstance(ws.cell(row=r, column=col).value, str)
                    else None)
                for r in range(7, 92)
            ]
            for hdr, col in cols.items()
        }

    hgl_before = snapshot(wb["HGL"])
    hgl25_before = snapshot(wb["HGL(25YEAR)"])

    add_hgl_crown_ceiling_checks(wb)

    hgl_after = snapshot(wb["HGL"])
    hgl25_after = snapshot(wb["HGL(25YEAR)"])

    assert hgl_before == hgl_after, "HGL clearance columns drifted on re-run"
    assert hgl25_before == hgl25_after, "HGL(25YEAR) clearance columns drifted on re-run"


# ---------------------------------------------------------------------------
# Task 4: annotate_hgl_method
# ---------------------------------------------------------------------------

HGL_METHOD_ANNOTATION_CELL = "P3"


def test_hgl_method_annotation_on_hgl(hgl_method_wb):
    ws = hgl_method_wb["HGL"]
    v = ws[HGL_METHOD_ANNOTATION_CELL].value
    assert isinstance(v, str) and v.startswith("=") and "hglMethod" in v, (
        f"HGL!{HGL_METHOD_ANNOTATION_CELL} should be an hglMethod-referencing "
        f"formula, got {v!r}"
    )
    assert "HGL method:" in v, f"annotation label missing: {v!r}"


def test_hgl_method_annotation_on_hgl_25year(hgl_method_wb):
    ws = hgl_method_wb["HGL(25YEAR)"]
    v = ws[HGL_METHOD_ANNOTATION_CELL].value
    assert isinstance(v, str) and v.startswith("=") and "hglMethod" in v, (
        f"HGL(25YEAR)!{HGL_METHOD_ANNOTATION_CELL} should be an hglMethod-"
        f"referencing formula, got {v!r}"
    )


def test_hgl_method_annotation_inside_print_area(hgl_method_wb):
    import re
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = hgl_method_wb[sheet_name]
        m = re.search(r"\$([A-Z]+)\$\d+:\$([A-Z]+)\$\d+", ws.print_area or "")
        assert m, f"{sheet_name} print_area malformed: {ws.print_area!r}"
        end_col = column_index_from_string(m.group(2))
        ann_col = column_index_from_string("P")
        assert ann_col <= end_col, (
            f"{sheet_name} annotation col P (idx {ann_col}) outside print area "
            f"(ends at {m.group(2)}, idx {end_col})"
        )


def test_hgl_method_annotation_idempotent(wip_src):
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    before = {name: wb[name]["P3"].value for name in ("HGL", "HGL(25YEAR)")}
    annotate_hgl_method(wb)
    after = {name: wb[name]["P3"].value for name in ("HGL", "HGL(25YEAR)")}
    assert before == after, "P3 annotation drifted on re-run"


# ---------------------------------------------------------------------------
# Task 5: add_u7_small_area_tc_lookup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cfactor_tc_wb(wip_src):
    """In-process fixture: Tasks 1-5 edits only."""
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    return wb


CFACTOR_TC_COL_LETTER = "W"
CFACTOR_TC_HEADER_ROW = 2
CFACTOR_DATA_START = 6
CFACTOR_DATA_END = 88


def test_cfactor_tc_header_on_column_w(cfactor_tc_wb):
    ws = cfactor_tc_wb["C_FACTOR"]
    v = ws[f"{CFACTOR_TC_COL_LETTER}{CFACTOR_TC_HEADER_ROW}"].value
    assert v == "Tc (Table 3-3, small-area)", (
        f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{CFACTOR_TC_HEADER_ROW} should be "
        f"the Table 3-3 header, got {v!r}"
    )


def test_cfactor_tc_formula_on_all_data_rows(cfactor_tc_wb):
    ws = cfactor_tc_wb["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        v = ws[f"{CFACTOR_TC_COL_LETTER}{r}"].value
        assert isinstance(v, str) and v.startswith("="), (
            f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{r} missing formula, got {v!r}"
        )
        assert f"D{r}" in v, (
            f"C_FACTOR!{CFACTOR_TC_COL_LETTER}{r} should reference D{r}: {v!r}"
        )


def test_cfactor_tc_formula_structure_table_3_3(cfactor_tc_wb):
    ws = cfactor_tc_wb["C_FACTOR"]
    v6 = ws[f"{CFACTOR_TC_COL_LETTER}{CFACTOR_DATA_START}"].value
    for threshold in ("0.8", "0.65", "0.4"):
        assert threshold in v6, (
            f"Table 3-3 threshold {threshold!r} missing from W6 formula: {v6!r}"
        )
    for tc_val in ("5", "7", "10", "15"):
        assert tc_val in v6, f"Tc value {tc_val!r} missing from W6 formula: {v6!r}"


def test_cfactor_column_v_untouched_by_edit_5(wip_src, cfactor_tc_wb):
    wip_wb = openpyxl.load_workbook(wip_src, data_only=False)
    w_wip = wip_wb["C_FACTOR"]
    w_gold = cfactor_tc_wb["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        assert w_wip[f"V{r}"].value == w_gold[f"V{r}"].value, (
            f"C_FACTOR!V{r} changed: wip={w_wip[f'V{r}'].value!r}, "
            f"golden={w_gold[f'V{r}'].value!r}"
        )


def test_cfactor_column_i_untouched_by_edit_5(wip_src, cfactor_tc_wb):
    # Column I is C-Soil Group Impervious Area (feeds composite-C on col M).
    # Edit 5 must NOT touch it, regardless of what Spec-1 U7 claimed.
    wip_wb = openpyxl.load_workbook(wip_src, data_only=False)
    w_wip = wip_wb["C_FACTOR"]
    w_gold = cfactor_tc_wb["C_FACTOR"]
    for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1):
        assert w_wip[f"I{r}"].value == w_gold[f"I{r}"].value, (
            f"C_FACTOR!I{r} unexpectedly changed by Edit 5"
        )


def test_cfactor_tc_edit_idempotent(wip_src):
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    before = [wb["C_FACTOR"][f"W{r}"].value for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1)]
    add_u7_small_area_tc_lookup(wb)
    after = [wb["C_FACTOR"][f"W{r}"].value for r in range(CFACTOR_DATA_START, CFACTOR_DATA_END + 1)]
    assert before == after, "C_FACTOR!W column drifted on re-run"


# ---------------------------------------------------------------------------
# Task 6: annotate_equations_sheet
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def equations_wb(wip_src):
    """In-process fixture: all six edits."""
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    return wb


TOGGLES_HEADER = "--- Design-Rule Toggles (Config sheet) ---"
CITATIONS_HEADER = "--- Citation refresh (Spec 1 U1-U7) ---"


def _find_text_row(ws, needle):
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == needle:
                return cell.row
    return None


def test_equations_toggles_section_header_present(equations_wb):
    ws = equations_wb["EQUATIONS + INSTRUCTIONS"]
    assert _find_text_row(ws, TOGGLES_HEADER) is not None, (
        f"{TOGGLES_HEADER!r} missing from EQUATIONS + INSTRUCTIONS"
    )


def test_equations_citations_section_header_present(equations_wb):
    ws = equations_wb["EQUATIONS + INSTRUCTIONS"]
    assert _find_text_row(ws, CITATIONS_HEADER) is not None, (
        f"{CITATIONS_HEADER!r} missing from EQUATIONS + INSTRUCTIONS"
    )


def test_equations_live_toggle_cells_present(equations_wb):
    ws = equations_wb["EQUATIONS + INSTRUCTIONS"]
    found = {"junctionAngleRule": False, "hglCrownCeilingRule": False, "hglMethod": False}
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            if not isinstance(v, str) or not v.startswith("="):
                continue
            for name in found:
                if name in v:
                    found[name] = True
    for name, ok in found.items():
        assert ok, f"no live-reference formula found for {name!r}"


def test_equations_pg_citation_appears(equations_wb):
    ws = equations_wb["EQUATIONS + INSTRUCTIONS"]
    found = False
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "PG C I-2" in cell.value:
                found = True
    assert found, "PG C I-2 citation (HGL clearance disclosure) missing"


def test_equations_annotation_idempotent(wip_src):
    wb = openpyxl.load_workbook(wip_src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    ws = wb["EQUATIONS + INSTRUCTIONS"]

    def snap():
        return [
            (cell.coordinate, cell.value)
            for row in ws.iter_rows(min_row=50, max_row=ws.max_row, max_col=3)
            for cell in row
            if cell.value is not None
        ]

    before = snap()
    annotate_equations_sheet(wb)
    after = snap()
    assert before == after, "EQUATIONS + INSTRUCTIONS annotation drifted on re-run"


# ---------------------------------------------------------------------------
# Task 7: Workbook-wide invariants (end-of-file)
# ---------------------------------------------------------------------------

def test_invariants_zero_ref_errors(golden_built):
    for ws in golden_built.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str):
                    assert "#REF!" not in text, (
                        f"{ws.title}!{cell.coordinate} contains #REF!: {text!r}"
                    )


def test_invariants_zero_broken_defined_names(golden_built):
    for name in golden_built.defined_names:
        dn = golden_built.defined_names[name]
        val = getattr(dn, "value", None) or str(dn)
        assert "#REF!" not in val, (
            f"defined name {name!r} resolves to #REF!: {val!r}"
        )


def test_invariants_seventeen_sheets_config_last(golden_built):
    assert len(golden_built.sheetnames) == 17
    assert golden_built.sheetnames[-1] == "Config"


def test_invariants_original_sheet_order_preserved(wip_src, golden_built):
    wip_wb = openpyxl.load_workbook(wip_src, data_only=False)
    assert [n for n in golden_built.sheetnames if n != "Config"] == wip_wb.sheetnames


def test_invariants_no_external_links(golden_built):
    for ws in golden_built.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str):
                    # External workbook refs look like "[filename.xlsx]SheetName!A1".
                    assert not ("[" in text and ".xlsx]" in text), (
                        f"{ws.title}!{cell.coordinate} has external link: {text!r}"
                    )


def test_invariants_builder_idempotent(golden_built_twice):
    first, second = golden_built_twice
    assert set(first.defined_names) == set(second.defined_names), (
        "defined-name set changed on re-run"
    )
    for sheet in first.sheetnames:
        ws1 = first[sheet]
        ws2 = second[sheet]
        max_r = max(ws1.max_row, ws2.max_row)
        max_c = max(ws1.max_column, ws2.max_column)
        for r in range(1, max_r + 1):
            for c in range(1, max_c + 1):
                v1 = ws1.cell(row=r, column=c).value
                v2 = ws2.cell(row=r, column=c).value
                t1 = v1 if isinstance(v1, str) else getattr(v1, "text", None)
                t2 = v2 if isinstance(v2, str) else getattr(v2, "text", None)
                if t1 is not None or t2 is not None:
                    assert t1 == t2, (
                        f"idempotency drift on {sheet}!{ws1.cell(row=r,column=c).coordinate}: "
                        f"{t1!r} vs {t2!r}"
                    )
                else:
                    assert v1 == v2, (
                        f"idempotency drift on {sheet}!{ws1.cell(row=r,column=c).coordinate}: "
                        f"{v1!r} vs {v2!r}"
                    )

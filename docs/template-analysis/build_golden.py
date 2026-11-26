# Apply Spec-2 edits to the Spec-1 repaired WIP template to produce the
# golden rulebook-aligned template.
#
# Usage: python build_golden.py <wip_source.xlsx> <golden_output.xlsx>
#
# Six edits are applied in order (all idempotent):
#   1. add_config_sheet        - new Config tab with 3 toggle named ranges
#   2. rewire_junction_angle_rule - toggle-aware controlling-angle formula
#   3. add_hgl_crown_ceiling_checks - clearance columns on HGL + HGL(25YEAR)
#   4. annotate_hgl_method     - top-of-sheet hglMethod stamp
#   5. add_u7_small_area_tc_lookup - Table 3-3 Tc lookup on C_FACTOR col W
#   6. annotate_equations_sheet - toggle + citation annotations
#
# Spec: docs/superpowers/specs/2026-11-25-golden-template-design.md
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula


CONFIG_SHEET_NAME = "Config"

SDC_SHEET = "STORM DRAIN COMPS"
SDC_DATA_START = 10
SDC_DATA_END = 98

# Preferred helper column (first free). WIP's AJ is a Table4 pass-through
# on every data row, so AJ is not free. BE is the first free column past
# the active data block (A:BD).
HELPER_COL_PREFERRED = "BE"

# Row-8 label written by rewire_junction_angle_rule.  Unique to this builder;
# used by _clear_prior_junction_helper to detect and remove stale helpers.
HELPER_LABEL_TEXT = "Lv_min helper (Spec 2, for smaller-loss toggle)"


def _find_free_column_for_helper(ws, start_col_letter="BE"):
    # Scan columns right of (inclusive) start_col_letter for one with no
    # value in any data row. Returns the column letter.
    start_col = openpyxl.utils.column_index_from_string(start_col_letter)
    for col in range(start_col, start_col + 16):  # 16-col safety horizon
        letter = get_column_letter(col)
        occupied = any(
            ws.cell(row=r, column=col).value not in (None, "")
            for r in range(SDC_DATA_START, SDC_DATA_END + 1)
        )
        if not occupied:
            return letter
    raise RuntimeError(
        f"no free column found for AR_min helper near {start_col_letter}"
    )

CONFIG_ROWS = (
    # (name,                    default,                               list_options,                                                               citation)
    ("junctionAngleRule",       "smaller-loss",                       ("smaller-loss", "larger-loss"),
     'MDSHA Drainage Manual Ch. 5 "Storm Drain Systems" (Sept 2023); MCDOT §4.3.2.3 (June 2014). '
     'PG County SWM Ch. 8 p. 8-27 (Sept 30 2014) states the opposite rule - set to "larger-loss" '
     'for PG-reviewed projects. The WIP template\'s prior default behavior matches "larger-loss"; '
     'the golden default is "smaller-loss" (MDSHA primary source).'),
    ("hglCrownCeilingRule",     "crown-plus-1ft",                     ("crown-plus-1ft", "rim-only"),
     'MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft. '
     'PG C I-2 caps only at Rim − 12" (no explicit crown ceiling) - '
     'set to "rim-only" for PG-reviewed projects.'),
    ("hglMethod",               "HEC-22 EGL (d/s crown floor)",       ("HEC-22 EGL (d/s crown floor)", "legacy both-end crown floor"),
     "HTML calculator toggle landed 2026-11-09 (HEC-22 vs legacy both-end crown floor). "
     "Label-only in Spec 2; Spec 3 wires xlsx HGL computation to this toggle."),
)


def add_config_sheet(wb):
    # Idempotent: if Config already exists, remove and rebuild. Guarantees
    # the sheet ends up as the last tab even if a prior run left it mid-list.
    if CONFIG_SHEET_NAME in wb.sheetnames:
        del wb[CONFIG_SHEET_NAME]
    # Also drop any stale defined names so we don't double-register.
    for name in ("junctionAngleRule", "hglCrownCeilingRule", "hglMethod"):
        if name in wb.defined_names:
            del wb.defined_names[name]

    ws = wb.create_sheet(CONFIG_SHEET_NAME)
    ws.sheet_properties.tabColor = "FFC107"  # amber

    # Row 1 header, merged A1:C1.
    ws["A1"] = (
        "Project-level design-rule toggles - DO NOT DELETE. "
        "Read by Spec 3 calculator/visualizer import."
    )
    ws.merge_cells("A1:C1")
    ws["A1"].font = Font(bold=True)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    editable_fill = PatternFill("solid", fgColor="FFFBEB")  # light yellow
    mono = Font(name="Consolas", size=11)
    label_font = Font(bold=True)
    cite_font = Font(italic=True, color="666666")

    for row_idx, (name, default, options, citation) in enumerate(CONFIG_ROWS, start=3):
        # Column A: label.
        ws.cell(row=row_idx, column=1, value=name).font = label_font
        ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="right")

        # Column B: editable default value (dropdown-backed).
        b = ws.cell(row=row_idx, column=2, value=default)
        b.font = mono
        b.fill = editable_fill

        # Column C: citation / informational text.
        c = ws.cell(row=row_idx, column=3, value=citation)
        c.font = cite_font
        c.alignment = Alignment(wrap_text=True, vertical="top")

        # Columns E-G: hidden helper lists, one option pair per toggle at E/F/G.
        helper_col = 5 + (row_idx - 3)  # E=5, F=6, G=7
        for opt_idx, opt in enumerate(options, start=3):
            ws.cell(row=opt_idx, column=helper_col, value=opt)

        # Data validation: list sourced from this toggle's helper column.
        helper_letter = openpyxl.utils.get_column_letter(helper_col)
        dv = DataValidation(
            type="list",
            formula1=f"=${helper_letter}$3:${helper_letter}$4",
            allow_blank=False,
        )
        dv.error = f"Must be one of: {', '.join(options)}"
        dv.errorTitle = "Invalid toggle value"
        dv.errorStyle = "stop"
        ws.add_data_validation(dv)
        dv.add(b)

        # Workbook-scoped named range for this toggle.
        wb.defined_names[name] = DefinedName(
            name=name,
            attr_text=f"{CONFIG_SHEET_NAME}!$B${row_idx}",
        )

    # Hide helper columns E-G.
    for col_letter in ("E", "F", "G"):
        ws.column_dimensions[col_letter].hidden = True

    # Column widths.
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["C"].width = 70


def _clear_prior_junction_helper(ws):
    # Idempotency: clear any helper column left by a previous run of this
    # builder. Detect by matching the row-8 label string, which is unique
    # to our edit and won't collide with WIP content.
    start = openpyxl.utils.column_index_from_string(HELPER_COL_PREFERRED)
    for col in range(start, start + 16):
        if ws.cell(row=8, column=col).value == HELPER_LABEL_TEXT:
            for r in range(SDC_DATA_START, SDC_DATA_END + 1):
                ws.cell(row=r, column=col).value = None
            ws.cell(row=8, column=col).value = None


def rewire_junction_angle_rule(wb):
    ws = wb[SDC_SHEET]
    _clear_prior_junction_helper(ws)
    helper_letter = _find_free_column_for_helper(ws, HELPER_COL_PREFERRED)

    for r in range(SDC_DATA_START, SDC_DATA_END + 1):
        # AR_min helper: MIN of positive Lv values entering this structure.
        helper_formula = (
            f'=IFERROR(MIN(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}>0),'
            f'$AQ${SDC_DATA_START}:$AQ${SDC_DATA_END})),0)'
        )
        helper_coord = f"{helper_letter}{r}"
        ws[helper_coord] = ArrayFormula(helper_coord, helper_formula)

        # AD: toggle-aware controlling angle.
        #   smaller-loss (MDSHA): angle of MIN-Lv inflow among positive Lv's.
        #   larger-loss (PG):     angle of MAX-Lv inflow (= original WIP).
        ad_coord = f"AD{r}"
        ad_formula = (
            f'=IF(AR{r}="","",IF(AR{r}=0,"-",'
            f'IF(junctionAngleRule="smaller-loss",'
            f'MAX(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}={helper_letter}{r}),'
            f'$R${SDC_DATA_START}:$R${SDC_DATA_END})),'
            f'MAX(IF($AQ${SDC_DATA_START}:$AQ${SDC_DATA_END}=$AR{r},'
            f'$R${SDC_DATA_START}:$R${SDC_DATA_END})))))'
        )
        ws[ad_coord] = ArrayFormula(ad_coord, ad_formula)

    # Also write a header-row note so engineers can see which column is the
    # helper. Row 8 is the SDC's dynamic label row.
    ws[f"{helper_letter}8"] = HELPER_LABEL_TEXT


HGL_HEADER_ROW = 6
HGL_DATA_START = 7
HGL_DATA_END = 91

CLEARANCE_HEADERS = ("Crown+1ft Check", "Rim-1ft Check", "Clearance Governing")

# Column letters on both HGL sheets that this edit reads.
HGL_COL_UPSTREAM_CROWN = "D"    # U/S (FROM) CROWN
HGL_COL_HGL_AT_FROM = "M"       # HGL ELEV IN "FROM" STR
HGL_COL_RIM_IN_PLACE = "N"      # TOP/OPENING ELEV OF "FROM" STR (HGL sheet only)

SDC_LOOKUP_A = "'STORM DRAIN COMPS'!$A:$A"
SDC_LOOKUP_B = "'STORM DRAIN COMPS'!$B:$B"
SDC_RIM_RETURN = "'STORM DRAIN COMPS'!$AB:$AB"


def _rim_cell_formula_for_hgl_25year(r):
    # HGL(25YEAR) has no rim column; pull from SDC via (From, To) pair.
    return (
        f'IF(OR(A{r}="",B{r}=""),"",'
        f'XLOOKUP(1,({SDC_LOOKUP_A}=$A{r})*({SDC_LOOKUP_B}=$B{r}),'
        f'{SDC_RIM_RETURN}))'
    )


def _clear_prior_clearance_cols(ws):
    # Idempotency: scan the whole header row for cells whose text matches
    # one of our clearance headers. Clear the full data range and header
    # cell for any match.
    from openpyxl.cell.cell import MergedCell as _MergedCell
    for col in range(1, ws.max_column + 2):
        cell = ws.cell(row=HGL_HEADER_ROW, column=col)
        if isinstance(cell, _MergedCell):
            continue
        hdr = cell.value
        if isinstance(hdr, str) and hdr in CLEARANCE_HEADERS:
            for r in range(HGL_DATA_START, HGL_DATA_END + 1):
                ws.cell(row=r, column=col).value = None
            ws.cell(row=HGL_HEADER_ROW, column=col).value = None


def _first_empty_column_in_row(ws, row, start_col_letter):
    from openpyxl.cell.cell import MergedCell as _MergedCell
    start = openpyxl.utils.column_index_from_string(start_col_letter)
    for col in range(start, start + 32):
        cell = ws.cell(row=row, column=col)
        # Skip slave cells of a merged range — they are read-only and
        # cannot receive a header value.
        if isinstance(cell, _MergedCell):
            continue
        if cell.value in (None, ""):
            return col
    raise RuntimeError(
        f"no empty column found after {start_col_letter} on {ws.title}"
    )


def _add_checks_to_hgl_sheet(ws, rim_formula_fn, start_search_letter):
    _clear_prior_clearance_cols(ws)
    first_empty = _first_empty_column_in_row(ws, HGL_HEADER_ROW, start_search_letter)
    crown_col = first_empty
    rim_col = first_empty + 1
    gov_col = first_empty + 2

    crown_letter = openpyxl.utils.get_column_letter(crown_col)
    rim_letter = openpyxl.utils.get_column_letter(rim_col)
    gov_letter = openpyxl.utils.get_column_letter(gov_col)

    ws.cell(row=HGL_HEADER_ROW, column=crown_col, value="Crown+1ft Check")
    ws.cell(row=HGL_HEADER_ROW, column=rim_col, value="Rim-1ft Check")
    ws.cell(row=HGL_HEADER_ROW, column=gov_col, value="Clearance Governing")

    for r in range(HGL_DATA_START, HGL_DATA_END + 1):
        ws.cell(
            row=r, column=crown_col,
            value=(
                f'=IF({HGL_COL_HGL_AT_FROM}{r}="","",'
                f'IF({HGL_COL_HGL_AT_FROM}{r}-{HGL_COL_UPSTREAM_CROWN}{r}>1,'
                f'"FAIL","OK"))'
            ),
        )
        rim_expr = rim_formula_fn(r)
        ws.cell(
            row=r, column=rim_col,
            value=(
                f'=LET(rim,{rim_expr},hgl,{HGL_COL_HGL_AT_FROM}{r},'
                f'IF(OR(rim="",hgl=""),"",IF(rim-hgl<1,"FAIL","OK")))'
            ),
        )
        ws.cell(
            row=r, column=gov_col,
            value=(
                f'=IF(OR({crown_letter}{r}="",{rim_letter}{r}=""),"",'
                f'IF(hglCrownCeilingRule="crown-plus-1ft",'
                f'IF(OR({crown_letter}{r}="FAIL",{rim_letter}{r}="FAIL"),'
                f'"FAIL","OK"),{rim_letter}{r}))'
            ),
        )

    # Extend/set print area to include all three new columns through the
    # end of the data range.
    ws.print_area = f"$A$1:${gov_letter}${HGL_DATA_END}"


def add_hgl_crown_ceiling_checks(wb):
    hgl = wb["HGL"]
    _add_checks_to_hgl_sheet(
        hgl,
        rim_formula_fn=lambda r: f"{HGL_COL_RIM_IN_PLACE}{r}",
        start_search_letter="S",  # Q is user-input, R is a note
    )
    hgl25 = wb["HGL(25YEAR)"]
    _add_checks_to_hgl_sheet(
        hgl25,
        rim_formula_fn=_rim_cell_formula_for_hgl_25year,
        start_search_letter="W",  # Q-V are 25-yr aux columns
    )


def annotate_hgl_method(wb):
    raise NotImplementedError("Task 4")


def add_u7_small_area_tc_lookup(wb):
    raise NotImplementedError("Task 5")


def annotate_equations_sheet(wb):
    raise NotImplementedError("Task 6")


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_golden.py <wip_source.xlsx> <golden_output.xlsx>",
              file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])

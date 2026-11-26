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


HGL_METHOD_STAMP_COORD = "P3"


def annotate_hgl_method(wb):
    for sheet_name in ("HGL", "HGL(25YEAR)"):
        ws = wb[sheet_name]
        cell = ws[HGL_METHOD_STAMP_COORD]
        cell.value = '="HGL method: " & hglMethod'
        cell.font = Font(bold=True, italic=True)
        cell.alignment = Alignment(horizontal="right")


CFACTOR_SHEET = "C_FACTOR"
CFACTOR_TC_COL = "W"
CFACTOR_TC_HDR_ROW = 2
CFACTOR_DATA_RANGE = range(6, 89)  # inclusive 6..88


def add_u7_small_area_tc_lookup(wb):
    ws = wb[CFACTOR_SHEET]
    skipped = []

    ws[f"{CFACTOR_TC_COL}{CFACTOR_TC_HDR_ROW}"] = "Tc (Table 3-3, small-area)"

    for r in CFACTOR_DATA_RANGE:
        existing = ws[f"{CFACTOR_TC_COL}{r}"].value
        if existing is None or existing == "":
            pass
        elif isinstance(existing, str) and existing.startswith("=") and (
            f"D{r}" in existing or f"$D${r}" in existing
        ) and (f"M{r}" in existing or f"$M${r}" in existing):
            # Already looks like our formula from a prior run.
            continue
        else:
            skipped.append(r)
            continue
        ws[f"{CFACTOR_TC_COL}{r}"] = (
            f'=IF(D{r}="","",'
            f'IF(D{r}>2,"",'
            f'IF(M{r}>=0.8,5,'
            f'IF(M{r}>=0.65,7,'
            f'IF(M{r}>=0.4,10,15)))))'
        )

    if skipped:
        print(
            f"Edit 5: skipped C_FACTOR!{CFACTOR_TC_COL} on rows "
            f"{skipped} (pre-existing unrelated content)"
        )


EQ_SHEET = "EQUATIONS + INSTRUCTIONS"
EQ_TOGGLES_HEADER = "=== Design-Rule Toggles (Config sheet) ==="
EQ_CITATIONS_HEADER = "=== Citation refresh (Spec 1 U1-U7) ==="
EQ_BLOCK_HEIGHT = 36  # Number of rows our block occupies (conservative upper bound)


def _eq_find_row(ws, needle, col=1):
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == needle:
            return r
    return None


def annotate_equations_sheet(wb):
    ws = wb[EQ_SHEET]

    start = _eq_find_row(ws, EQ_TOGGLES_HEADER)
    if start is None:
        start = ws.max_row + 2  # one blank row spacer

    def write(row_offset, col, value, bold=False):
        c = ws.cell(row=start + row_offset, column=col, value=value)
        if bold:
            c.font = Font(bold=True)

    # Clear EQ_BLOCK_HEIGHT rows below start so a prior longer annotation is
    # replaced cleanly on idempotent re-run.
    for r in range(start, start + EQ_BLOCK_HEIGHT):
        for col in range(1, 4):
            ws.cell(row=r, column=col).value = None

    # Toggles section.
    write(0, 1, EQ_TOGGLES_HEADER, bold=True)
    write(1, 1, "junctionAngleRule =")
    write(1, 2, "=junctionAngleRule")
    write(2, 1, "Controlling-angle procedure at 2-inflow junctions.")
    write(3, 1, "  MDSHA Ch. 5 / MCDOT §4.3.2.3: smaller Lv’s angle controls  [smaller-loss, default]")
    write(4, 1, "  PG SWM Ch. 8 p. 8-27 (Sept 30 2014): larger H’s angle controls  [larger-loss]")
    write(5, 1, "  Set on Config!B3. Affects STORM DRAIN COMPS!AD (controlling angle) and downstream Hb.")

    write(7, 1, "hglCrownCeilingRule =")
    write(7, 2, "=hglCrownCeilingRule")
    write(8, 1, "HGL vertical-clearance ceiling.")
    write(9, 1, "  MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft  [crown-plus-1ft, default]")
    write(10, 1, "  PG C I-2: HGL ≤ Rim − 12” only (pipes may surcharge within the structure)  [rim-only]")
    write(11, 1, "  Set on Config!B4. Affects HGL and HGL(25YEAR) “Clearance Governing” column.")

    write(13, 1, "hglMethod =")
    write(13, 2, "=hglMethod")
    write(14, 1, "HGL-walk method.")
    write(15, 1, "  HEC-22 EGL (d/s crown floor) - HEC-22 §7.4 standard  [HEC-22, default]")
    write(16, 1, "  Legacy both-end crown floor - firm historical convention  [legacy]")
    write(17, 1, "  Set on Config!B5. Label-only in this template; Spec 3 wires xlsx HGL computation.")

    # Citations section.
    write(20, 1, EQ_CITATIONS_HEADER, bold=True)
    write(21, 1, "Junction-loss primary source - MDSHA Drainage Manual Ch. 5 p. 5-26 (Sept 2023), Fig 5-8")
    write(22, 1, "  (mirrored by MCDOT §4.3.2.3 p. 46, Revised Final June 2014).")
    write(23, 1, "Pipe slope - MCDOT §4.3.3(k) (15” and 18” ≥ 1.0%); our rule <24” ≥ 1.0% is a touch")
    write(24, 1, "  more conservative (catches 21” too) - intentional.")
    write(25, 1, "Time of concentration for small areas (≤ 2 acres) - MCDOT §3.2.1 Table 3-3:")
    write(26, 1, "  C ≥ 0.80 → 5 min; 0.65-0.79 → 7; 0.40-0.64 → 10; ≤ 0.39 → 15.")
    write(27, 1, "Composite C - MCDOT §3.4 area-weighted; PG SWM Ch. 8 §8.2.1 same intent.")
    write(28, 1, "PG DPIE checklist items affecting calculator-visible rules:")
    write(29, 1, "  C-19 (15” min pipe), G-8 (min cover: 1 ft RCP, 2 ft flexible),")
    write(30, 1, "  G-9 (0.1 ft min drop through structure), C-20 (400 ft max access spacing),")
    write(31, 1, "  C-21 (≤ 45° pipe-to-flat-wall), H-6 (last reach to outfall ≤ 1%),")
    write(32, 1, "  L-4 (channel armoring v > 5 fps cut / 4 fps fill),")
    write(33, 1, "  I-2 (HGL ≤ Rim − 1 ft; the crown-ceiling toggle disclosure).")


def enable_iterative_calculation(wb):
    # Belt-and-suspenders: repair.py also sets this on the WIP, but the
    # golden builder enforces it so the setting survives any WIP edit
    # that silently flips it back off. Required because the HGL walking
    # formulas (G/K/M on HGL, array-IF Tc on STORM DRAIN COMPS!K) use
    # whole-column IF(array) patterns that Excel's static analyzer flags
    # as potentially circular - with iterate=False, those cells open blank.
    wb.calculation.iterate = True
    wb.calculation.iterateCount = 100
    wb.calculation.iterateDelta = 0.001


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    add_config_sheet(wb)
    rewire_junction_angle_rule(wb)
    add_hgl_crown_ceiling_checks(wb)
    annotate_hgl_method(wb)
    add_u7_small_area_tc_lookup(wb)
    annotate_equations_sheet(wb)
    enable_iterative_calculation(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_golden.py <wip_source.xlsx> <golden_output.xlsx>",
              file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])

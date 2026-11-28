# Apply Spec-2 edits to the Spec-1 repaired WIP template to produce the
# golden rulebook-aligned template.
#
# Usage: python build_golden.py <wip_source.xlsx> <golden_output.xlsx>
#
# Seven edits are applied in order (all idempotent):
#   1. add_config_sheet        - new Config tab with 3 toggle named ranges
#   2. rewire_junction_angle_rule - toggle-aware controlling-angle formula
#   3. add_hgl_crown_ceiling_checks - clearance columns on HGL + HGL(25YEAR)
#   4. annotate_hgl_method     - top-of-sheet hglMethod stamp
#   5. add_u7_small_area_tc_lookup - Table 3-3 Tc lookup on C_FACTOR col W
#   6. annotate_equations_sheet - toggle + citation annotations
#   7. wire_hgl_method         - HGL G/K/M cols IF-branch on hglMethod (Spec 3)
#
# Spec: docs/superpowers/specs/2026-11-25-golden-template-design.md
import re
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
    # Spec 7 Path A awareness: if cols have been shifted (N8=Pipe Shape),
    # target the shifted positions: AD→AG, AQ→AT, AR→AU, R→U.
    path_a = ws["N8"].value == "Pipe Shape"
    ad_col  = "AG" if path_a else "AD"
    aq_col  = "AT" if path_a else "AQ"
    ar_col  = "AU" if path_a else "AR"
    ang_col = "U"  if path_a else "R"

    _clear_prior_junction_helper(ws)
    helper_letter = _find_free_column_for_helper(ws, HELPER_COL_PREFERRED)

    for r in range(SDC_DATA_START, SDC_DATA_END + 1):
        helper_formula = (
            f'=IFERROR(MIN(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*(${aq_col}${SDC_DATA_START}:${aq_col}${SDC_DATA_END}>0),'
            f'${aq_col}${SDC_DATA_START}:${aq_col}${SDC_DATA_END})),0)'
        )
        helper_coord = f"{helper_letter}{r}"
        ws[helper_coord] = ArrayFormula(helper_coord, helper_formula)

        ad_coord = f"{ad_col}{r}"
        ad_formula = (
            f'=IF({ar_col}{r}="","",IF({ar_col}{r}=0,"-",'
            f'IF(junctionAngleRule="smaller-loss",'
            f'MAX(IF(($B${SDC_DATA_START}:$B${SDC_DATA_END}=$A{r})'
            f'*(${aq_col}${SDC_DATA_START}:${aq_col}${SDC_DATA_END}={helper_letter}{r}),'
            f'${ang_col}${SDC_DATA_START}:${ang_col}${SDC_DATA_END})),'
            f'MAX(IF(${aq_col}${SDC_DATA_START}:${aq_col}${SDC_DATA_END}=${ar_col}{r},'
            f'${ang_col}${SDC_DATA_START}:${ang_col}${SDC_DATA_END})))))'
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
EQ_TOGGLES_HEADER = "--- Design-Rule Toggles (Config sheet) ---"
EQ_CITATIONS_HEADER = "--- Citation refresh (Spec 1 U1-U7) ---"
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


HGL_DATA_ROW_START = 7
HGL_DATA_ROW_END = 91
HGL_METHOD_LEGACY_LABEL = "legacy both-end crown floor"
HGL_METHOD_SHEETS = ("HGL", "HGL(25YEAR)")


def _hec22_strip_us_crown(legacy_body, us_crown_token):
    """Return the HEC-22 variant of a MAX(...) formula body.

    Drops the us_crown term from the first MAX(...) call encountered.
    Keeps everything else — IFERROR wrapper, IF(A{r}="",...) guard,
    additional MAX args like downstream chain lookups — verbatim.
    """
    # Match: MAX(<args>)  where <us_crown_token> is one of the comma-
    # separated args. Replace just that arg, preserving surrounding
    # tokens exactly.
    pattern = re.compile(
        r"MAX\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
    )

    def strip_arg(match):
        inside = match.group(1)
        # Split on commas that are not inside parens.
        parts = []
        depth = 0
        start = 0
        for i, ch in enumerate(inside):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(inside[start:i])
                start = i + 1
        parts.append(inside[start:])
        filtered = [p for p in parts if p.strip() != us_crown_token]
        if len(filtered) == len(parts):
            # us_crown token not present in this MAX — leave untouched.
            return match.group(0)
        return "MAX(" + ",".join(filtered) + ")"

    # Only transform the first MAX we see (the crown-floor MAX, not
    # any nested MAX(IF(...)) downstream chain lookup).
    out, n = pattern.subn(strip_arg, legacy_body, count=1)
    return out


_IF_WRAP_RE = re.compile(
    r'^IF\(hglMethod="legacy both-end crown floor",(.+),(.+)\)$',
    re.DOTALL
)


def _unwrap_hgl_method(body):
    """Return the HEC-22 branch of an IF(hglMethod="legacy...",legacy,hec22)
    wrapper. For bodies without the wrapper, returns None.

    Spec 6 inverse of Spec 3 Task 18's _wrap_if_hgl_method. Used to strip
    the toggle from old wrapped formulas when rebuilding golden.
    """
    m = _IF_WRAP_RE.match(body)
    if not m:
        return None
    # Group 2 is the hec22 branch — the whole point of the strip.
    return m.group(2)


def wire_hgl_method(wb):
    """Make HGL and HGL(25YEAR) formulas use HEC-22 only (Spec 6).

    Spec 3 Task 18 wrapped HGL cols G/K/M with IF(hglMethod="legacy...",
    legacy, hec22). Spec 6 drops support for the legacy PG-County rule
    (user project is MDSHA/MCDOT/HEC-22 only). This function:

    1. For col K (the only col where the two branches actually differ):
       strip the D{r} us_crown term from the MAX(...) call, producing
       =IFERROR(IF(A{r}="","",MAX(J{r}+G{r})),"") — HEC-22 only.

    2. For cols G and M (where Task 18 wrapped defensively; both IF
       branches had identical bodies): unwrap to the plain body.

    Handles both forms:
      - Repaired WIP (no IF-wrap yet; col K has MAX(D{r},J{r}+G{r})) →
        strip us_crown directly.
      - Old golden with Task 18's IF-wrap → unwrap, then strip.

    Idempotent: a second run on an already-simplified file produces the
    same bytes (no "hglMethod" literal remains to re-process).

    ArrayFormula on G is preserved. No usages of the hglMethod named
    range remain; the named range itself stays defined on the Config
    sheet for forward-compat.
    """
    for sheet_name in HGL_METHOD_SHEETS:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]

        for r in range(HGL_DATA_ROW_START, HGL_DATA_ROW_END + 1):
            # ---- Column G: ArrayFormula (CSE), no us_crown.
            gval = ws[f"G{r}"].value
            gtext = None
            is_array = False
            if isinstance(gval, ArrayFormula):
                gtext = gval.text
                is_array = True
            elif isinstance(gval, str) and gval.startswith("="):
                gtext = gval
            if gtext is not None:
                body = gtext.lstrip("=")
                unwrapped = _unwrap_hgl_method(body)
                if unwrapped is not None:
                    new_text = "=" + unwrapped
                    if is_array:
                        ws[f"G{r}"] = ArrayFormula(gval.ref, new_text)
                    else:
                        ws[f"G{r}"] = new_text

            # ---- Column K: plain formula, us_crown = D{r}.
            kval = ws[f"K{r}"].value
            if isinstance(kval, str) and kval.startswith("="):
                body = kval.lstrip("=")
                unwrapped = _unwrap_hgl_method(body)
                if unwrapped is not None:
                    # Formula was Task-18-wrapped — use the hec22 branch.
                    ws[f"K{r}"] = "=" + unwrapped
                else:
                    # Un-wrapped WIP formula — strip the us_crown term.
                    hec22 = _hec22_strip_us_crown(body, f"D{r}")
                    if hec22 != body:
                        ws[f"K{r}"] = "=" + hec22
                    # else: no us_crown present, leave alone.

            # ---- Column M: plain formula, no crown terms.
            mval = ws[f"M{r}"].value
            if isinstance(mval, str) and mval.startswith("="):
                body = mval.lstrip("=")
                unwrapped = _unwrap_hgl_method(body)
                if unwrapped is not None:
                    ws[f"M{r}"] = "=" + unwrapped

    return wb


PIPE_DATA_ROW_START = 10
PIPE_DATA_ROW_END = 98

# Path A insertion: Shape/Width/# at O/P/Q, after N (Size/Height). All
# existing SDC columns at O (col 15) or beyond shift right by 3.
PATH_A_INSERT_AT = 15
PATH_A_SHIFT_BY = 3

_PATH_A_CELL_REF_RE = re.compile(
    r"(?:(?P<sheet>'[^']+'|[A-Za-z_][A-Za-z0-9_]*)!)?"
    r"(?P<abs_col>\$?)(?P<col>[A-Z]{1,3})(?P<abs_row>\$?)(?P<row>\d+)"
)


def _shift_refs_to_sdc(formula, local_sheet, target_sheet="STORM DRAIN COMPS",
                      insert_at=PATH_A_INSERT_AT, amount=PATH_A_SHIFT_BY):
    """Shift col-letter refs that point to STORM DRAIN COMPS right by `amount`
    when they're at column index >= insert_at. Handles local refs on SDC and
    explicit 'STORM DRAIN COMPS'!<col><row> refs from any sheet."""
    import openpyxl.utils as _u
    target_norm = target_sheet.lower()

    def replace(m):
        sheet = m.group("sheet")
        col = m.group("col")
        col_idx = _u.column_index_from_string(col)
        if sheet is not None:
            sheet_clean = sheet.strip("'")
            is_target = sheet_clean.lower() == target_norm
        else:
            is_target = (local_sheet.lower() == target_norm)
        if is_target and col_idx >= insert_at:
            new_col = _u.get_column_letter(col_idx + amount)
            return (
                (m.group("sheet") + "!" if sheet else "")
                + m.group("abs_col") + new_col
                + m.group("abs_row") + m.group("row")
            )
        return m.group(0)
    return _PATH_A_CELL_REF_RE.sub(replace, formula)


def _swap_n_and_o_refs_on_sdc(wb):
    """Swap N{row} ↔ O{row} refs in SDC-targeting formulas across all
    sheets. Called after inserting the Pipe Shape column at N and
    shifting the pre-Spec-7 N (Size/Height) data to O."""
    import openpyxl.utils as _u
    from openpyxl.worksheet.formula import ArrayFormula
    target_norm = "storm drain comps"
    SWAP_RE = re.compile(
        r"(?:(?P<sheet>'[^']+'|[A-Za-z_][A-Za-z0-9_]*)!)?"
        r"(?P<abs_col>\$?)(?P<col>N|O)(?P<abs_row>\$?)(?P<row>\d+)"
    )

    def replace(local_sheet, m):
        sheet = m.group("sheet")
        col = m.group("col")
        if sheet is not None:
            sheet_clean = sheet.strip("'")
            is_target = sheet_clean.lower() == target_norm
        else:
            is_target = (local_sheet.lower() == target_norm)
        if not is_target:
            return m.group(0)
        new_col = "O" if col == "N" else "N"
        return (
            (m.group("sheet") + "!" if sheet else "")
            + m.group("abs_col") + new_col
            + m.group("abs_row") + m.group("row")
        )

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, ArrayFormula):
                    new_text = SWAP_RE.sub(lambda m: replace(ws.title, m), v.text)
                    if new_text != v.text:
                        cell.value = ArrayFormula(v.ref, new_text)
                elif isinstance(v, str) and v.startswith("="):
                    new_v = SWAP_RE.sub(lambda m: replace(ws.title, m), v)
                    if new_v != v:
                        cell.value = new_v


def _shift_all_formulas_path_a(wb):
    """Walk every formula on every sheet, shift col refs that target
    STORM DRAIN COMPS columns >= position 15 by +3. Handles plain string
    formulas and ArrayFormula CSE cells."""
    from openpyxl.worksheet.formula import ArrayFormula
    count = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, ArrayFormula):
                    new_text = _shift_refs_to_sdc(v.text, ws.title)
                    if new_text != v.text:
                        cell.value = ArrayFormula(v.ref, new_text)
                        count += 1
                elif isinstance(v, str) and v.startswith("="):
                    new_v = _shift_refs_to_sdc(v, ws.title)
                    if new_v != v:
                        cell.value = new_v
                        count += 1
    return count


def add_pipe_shape_columns(wb):
    """Spec 7 Path A: insert Pipe Shape / Width / # columns at O/P/Q on
    STORM DRAIN COMPS, right after N (Size/Height). All existing SDC
    columns at col 15 (O) or beyond shift right by 3. Helper columns
    appended at the new tail (post-shift BE→BH).

    Non-idempotent: re-runs on an already-shifted workbook would insert
    ANOTHER 3 columns. Guard via N8 header check — if O8 already says
    "Pipe Shape", skip the shift.

    Fixes the pre-existing EQUATIONS cell content bug separately via
    annotate_equations_sheet (headers no longer start with "=").
    """
    if "STORM DRAIN COMPS" not in wb.sheetnames:
        return wb
    ws = wb["STORM DRAIN COMPS"]

    # Idempotency guard: if O8 already says "Pipe Shape", skip insertion.
    if ws["N8"].value == "Pipe Shape":
        return wb

    # Insert 3 blank columns at position 15 (O) — shifts all content right.
    ws.insert_cols(PATH_A_INSERT_AT, PATH_A_SHIFT_BY)

    # Shift formula references across the entire workbook.
    _shift_all_formulas_path_a(wb)

    # Extend the Excel Table range (Table4 spans SDC data rows 10..98;
    # insert_cols should extend automatically but confirm the ref).
    for tbl in list(ws.tables.values()):
        # Table ref like 'A9:BE98' — need to extend end col by +3.
        ref = tbl.ref
        m = re.match(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", ref)
        if m:
            import openpyxl.utils as _u
            start_col, start_row, end_col, end_row = m.groups()
            end_idx = _u.column_index_from_string(end_col) + PATH_A_SHIFT_BY
            new_end_col = _u.get_column_letter(end_idx)
            tbl.ref = f"{start_col}{start_row}:{new_end_col}{end_row}"

    # Row-8 headers at the newly-inserted positions.
    # Per user: N=Pipe Shape (first), O=Size/Height (next), P=Width, Q=#.
    # Swap N↔O (N originally had Size/Height data; O is the newly-inserted
    # column). We also swap all N<row> ↔ O<row> cell refs across the
    # workbook so formulas keep pointing at the right physical data.
    # Step: save N data, write new content, swap formula refs.
    saved_n_data = {}
    for r in range(1, 100):
        saved_n_data[r] = ws[f"N{r}"].value
    # N now holds Pipe Shape; O holds Size/Height (data from pre-shift N).
    ws["N8"] = "Pipe Shape"
    ws["O8"] = "Size/Height (in)"
    ws["P8"] = "Width (in)"
    ws["Q8"] = "#"
    # Copy saved N data (rows 1-98 except header row 8) to O; write defaults to N.
    for r in range(1, 100):
        if r == 8:
            continue  # headers already set
        if saved_n_data[r] is not None:
            ws[f"O{r}"] = saved_n_data[r]

    # Data-entry defaults on rows 10-98 for Pipe Shape (N) and # (Q).
    for r in range(PIPE_DATA_ROW_START, PIPE_DATA_ROW_END + 1):
        ws[f"N{r}"] = "circular"
        ws[f"Q{r}"] = 1

    # Swap N↔O references in all formulas across the workbook. Only refs
    # to SDC (local or 'STORM DRAIN COMPS'! prefixed). N and O are both
    # < col 15 so they weren't touched by the earlier shift.
    _swap_n_and_o_refs_on_sdc(wb)

    # Data validation on N (Pipe Shape) — dropdown with 3 options.
    dv_shape = DataValidation(
        type="list",
        formula1='"circular,elliptical,rectangular"',
        allow_blank=True,
        showErrorMessage=True,
    )
    dv_shape.error = "Pipe Shape must be one of: circular, elliptical, rectangular"
    dv_shape.errorTitle = "Invalid Pipe Shape"
    dv_shape.prompt = "Choose: circular, elliptical, or rectangular"
    dv_shape.promptTitle = "Pipe Shape"
    dv_shape.add(f"N{PIPE_DATA_ROW_START}:N{PIPE_DATA_ROW_END}")
    ws.add_data_validation(dv_shape)

    # Helper columns at the new tail. Pre-insert last col was BE (57); after
    # +3 shift BE→BH (60). Fresh positions for helpers: BI/BJ/BK (61/62/63).
    ws["BI8"] = "A (sf per barrel)"
    ws["BJ8"] = "R (ft per barrel)"
    ws["BK8"] = "D_eq (in)"

    for r in range(PIPE_DATA_ROW_START, PIPE_DATA_ROW_END + 1):
        # BK: equivalent diameter (in), shape-aware.
        #   N=shape, O=height/size, P=width.
        ws[f"BK{r}"] = (
            f'=IF(N{r}="rectangular",'
            f'IF(OR(O{r}="",P{r}=""),"",2*O{r}*P{r}/(O{r}+P{r})),'
            f'IF(N{r}="elliptical",'
            f'IF(OR(O{r}="",P{r}=""),"",SQRT(O{r}*P{r})),'
            f'IF(O{r}="","",O{r})))'
        )
        # BI: Area A (sf per barrel).
        ws[f"BI{r}"] = (
            f'=IF(N{r}="rectangular",'
            f'IF(OR(O{r}="",P{r}=""),"",O{r}*P{r}/144),'
            f'IF(N{r}="elliptical",'
            f'IF(OR(O{r}="",P{r}=""),"",PI()*O{r}*P{r}/(4*144)),'
            f'IF(O{r}="","",PI()*O{r}^2/(4*144))))'
        )
        # BJ: Hydraulic radius R (ft per barrel). R = D_eq/4; in→ft.
        ws[f"BJ{r}"] = f'=IF(BK{r}="","",BK{r}/48)'

        # After shift: T→W (full flow), V→Y (Manning V), Y→AB (friction slope),
        # AV→AY (Q per barrel), AW→AZ (eff D), Z→AC (slope), S→V (Manning n).
        # Rewrite these to use helpers + Q (barrel count).
        ws[f"W{r}"] = (
            f'=IF(AC{r}="","",IF(BI{r}="","",'
            f'Q{r}*1.486/V{r}*BJ{r}^(2/3)*SQRT(AC{r})*BI{r}))'
        )
        ws[f"Y{r}"] = (
            f'=IF(AC{r}="","",IF(BJ{r}="","",'
            f'1.486/V{r}*BJ{r}^(2/3)*SQRT(AC{r})))'
        )
        ws[f"AB{r}"] = (
            f'=IF(A{r}="","",IF(BI{r}="","",IF(M{r}="","",'
            f'ROUND(((M{r}/Q{r}*V{r})/(1.486*BI{r}*BJ{r}^(2/3)))^2,6))))'
        )
        ws[f"AY{r}"] = f'=IF(M{r}="","",M{r}/Q{r})'
        ws[f"AZ{r}"] = f'=BK{r}'

    return wb


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
    wire_hgl_method(wb)
    add_pipe_shape_columns(wb)
    enable_iterative_calculation(wb)
    wb.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_golden.py <wip_source.xlsx> <golden_output.xlsx>",
              file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])

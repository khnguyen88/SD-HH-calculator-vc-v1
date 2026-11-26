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


def rewire_junction_angle_rule(wb):
    ws = wb[SDC_SHEET]
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
    ws[f"{helper_letter}8"] = "Lv_min helper (Spec 2, for smaller-loss toggle)"


def add_hgl_crown_ceiling_checks(wb):
    raise NotImplementedError("Task 3")


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

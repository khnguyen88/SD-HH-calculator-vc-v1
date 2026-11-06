"""Inlet Spacing_10-yr and Inlet Spacing_2-yr sheets.

Preserves legacy column layout but replaces hard-coded cell refs with:
- SUMIFS/SUMPRODUCT on DA_Catchments (keyed by Inlet_ID)
- XLOOKUP on IDF_Lookup (keyed by Tc)

Column layout (A..O):
  A: Inlet number       B: Catch basin type   C: Inlet length       D: Area (ac)
  E: C                  F: CA                 G: Bypass CA          H: Total CA
  I: Tc (min)           J: I (in/hr)          K: Q (cfs)            L: X-slope
  M: Grade              N: Computational      O: Allowable spread
"""
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation


HEADERS_ROW_8 = [
    "INLET", "CATCH BASIN", "INLET", "AREA",
    "", "", "BYPASS", "TOTAL",
    "T.O.C.", "I", "Q", "XSLOPE",
    "GRADE", "COMPUTATIONAL", "ALLOWABLE SPREAD",
]
HEADERS_ROW_9 = [
    "NUMBER", "TYPE", "LENGTH", "(acres)",
    "C", "CA", "CA", "CA",
    "(MIN)", "(IN/HR)", "(CFS)", "(FT/FT)",
    "(FT/FT)", "PROGRAM", "(FT)",
]


def _build_single_inlet_spacing(ws, storm: str, storm_label: str) -> None:
    ws["H1"] = "PROPOSED INLET SPACING SPREADS"
    ws["A4"] = "PROJECT:"
    ws["D4"] = "=Project_Name"
    ws["K4"] = "GUTTER DEPRESSION ="
    ws["N4"] = 0.0833
    ws["O4"] = "FEET"
    ws["M5"] = "N ="
    ws["N5"] = "=Manning_n_RCP"
    ws["A6"] = "CONTRACT NO. :"
    ws["H6"] = f"STORM FREQUENCY: {storm_label}"
    ws["K6"] = "GUTTER WIDTH ="
    ws["N6"] = 1.33
    ws["O6"] = "FEET"

    for c, h in enumerate(HEADERS_ROW_8, start=1):
        ws.cell(row=8, column=c, value=h)
    for c, h in enumerate(HEADERS_ROW_9, start=1):
        ws.cell(row=9, column=c, value=h)

    last_row = 30
    for r in range(11, last_row + 1):
        inlet_ref = f"$A{r}"

        # D: Area (ac) = SUMIFS/43560
        ws.cell(
            row=r, column=4,
            value=(f'=IF({inlet_ref}="","",'
                   f'SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{inlet_ref})/43560)')
        )
        # E: composite C (MDOT/MCDOT uses C_2-10 for both 2-yr and 10-yr events)
        ws.cell(
            row=r, column=5,
            value=(f'=IF({inlet_ref}="","",IFERROR('
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])'
                   f'/SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{inlet_ref}),0))')
        )
        # F: CA (ac*C)
        ws.cell(
            row=r, column=6,
            value=(f'=IF({inlet_ref}="","",'
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])/43560)')
        )
        # G: Bypass CA (user input; default 0)
        ws.cell(row=r, column=7, value=0)
        # H: Total CA
        ws.cell(row=r, column=8, value=f'=IF({inlet_ref}="","",F{r}+G{r})')
        # I: Tc (user input; default 5)
        ws.cell(row=r, column=9, value=5)
        # J: Intensity from IDF_Lookup
        ws.cell(
            row=r, column=10,
            value=(f'=IF({inlet_ref}="","",'
                   f'XLOOKUP(ROUND(I{r},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}]))')
        )
        # K: Q = Total CA * I
        ws.cell(row=r, column=11, value=f'=IF({inlet_ref}="","",H{r}*J{r})')

    dv_inlet = DataValidation(
        type="list",
        formula1='=INDIRECT("Structures[Structure_ID]")',
        allow_blank=True,
    )
    dv_inlet.add(f"A11:A{last_row}")
    ws.add_data_validation(dv_inlet)

    widths = [10, 12, 8, 8, 6, 8, 8, 8, 8, 8, 8, 8, 8, 14, 12]
    for i, w in enumerate(widths, start=1):
        col_letter = chr(ord("A") + i - 1)
        ws.column_dimensions[col_letter].width = w


def build_inlet_spacing_sheets(wb: Workbook) -> None:
    ws10 = wb.create_sheet("Inlet Spacing_10-yr")
    _build_single_inlet_spacing(ws10, storm="10yr", storm_label="10 - YEAR")
    ws2 = wb.create_sheet("Inlet Spacing_2-yr")
    _build_single_inlet_spacing(ws2, storm="2yr", storm_label="2 - YEAR")

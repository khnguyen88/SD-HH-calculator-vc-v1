"""10 Yr Pipe Capacity and 25 Yr Pipe Capacity sheets.

Same columns as legacy MDSHA format. Replaces hard-coded refs with structured
lookups: SUMIFS into DA_Catchments by Inlet_ID; XLOOKUP into Pipes / Pipe_Properties
/ IDF_Lookup.

Legacy layout (row 11 is header, data starts row 14):
  A From  B To  C Area_count  D Area(AC)  E C_runoff  F CA  G Adj.CA
  H SumA  I SumCA  J Tc  K Intensity  L Q  M Size  N Type  O n
"""
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import BLADENSBURG_PIPES


HEADERS_ROW_8_BASE = [
    "", "", "Contributing Area", "", "", "", "",
    "", "", "", "", "", "Pipe", "",
]
HEADERS_ROW_11 = [
    "FROM", "TO", "AREA", "AREA", "RUNOFF", "", "ADJ.",
    "SumA", "SumCA", "Conc>", "Intens.", "Q", "Size", "Type", "MANNING",
]
HEADERS_ROW_12 = [
    "", "", "(#)", "(AC.)", "COEF.", "", "",
    "", "", "(MIN)", "(IN/HR)", "(CFS)", "(IN)", "", "Coef.",
]


def _pipe_id_formula_from_from_structure(row: int) -> str:
    """Pipe_ID lookup: find the Pipe whose From/To match this row's From/To."""
    return (f'INDEX(Pipes[Pipe_ID],MATCH(1,'
            f'(Pipes[From_Structure]=A{row})*(Pipes[To_Structure]=B{row}),0))')


def _build_single_pipe_capacity(ws, storm: str, storm_label: str) -> None:
    ws["A1"] = "MARYLAND HIGHWAY / COUNTY STORM SEWER DESIGN"
    ws["A5"] = "DESIGNED BY:"
    ws["I5"] = "CONTRACT:"
    ws["I6"] = "TITLE:"

    # Row 8 header: the storm-year-labeled "runoff" header lands in column H.
    for c, h in enumerate(HEADERS_ROW_8_BASE, start=1):
        if c == 8:
            ws.cell(row=8, column=c, value=f"{storm_label} Year Runoff")
        else:
            ws.cell(row=8, column=c, value=h)
    for c, h in enumerate(HEADERS_ROW_11, start=1):
        ws.cell(row=11, column=c, value=h)
    for c, h in enumerate(HEADERS_ROW_12, start=1):
        ws.cell(row=12, column=c, value=h)

    # Seed From/To from Bladensburg so the sheet opens with a working example.
    for i, p in enumerate(BLADENSBURG_PIPES):
        r = 14 + i
        ws.cell(row=r, column=1, value=p["From_Structure"])
        ws.cell(row=r, column=2, value=p["To_Structure"])

    last_row = 50
    for r in range(14, last_row + 1):
        from_ref = f"$A{r}"
        pipe_ref = _pipe_id_formula_from_from_structure(r)

        # D: Area (ac) = SUMIFS / 43560
        ws.cell(
            row=r, column=4,
            value=(f'=IF({from_ref}="","",'
                   f'SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{from_ref})/43560)')
        )
        # E: composite C for the storm (25yr uses C_25; 10yr uses C_2-10)
        c_column = "C_25" if storm == "25yr" else "C_2-10"
        ws.cell(
            row=r, column=5,
            value=(f'=IF({from_ref}="","",IFERROR('
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={from_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[{c_column}])'
                   f'/SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{from_ref}),0))')
        )
        # F: CA = D * E
        ws.cell(row=r, column=6, value=f'=IF({from_ref}="","",D{r}*E{r})')
        # G: Adj. CA (user input or 0 default)
        ws.cell(row=r, column=7, value=0)
        # H: SumA
        ws.cell(row=r, column=8, value=f'=D{r}')
        # I: SumCA
        ws.cell(row=r, column=9, value=f'=F{r}')
        # J: Tc user input default 5
        ws.cell(row=r, column=10, value=5)
        # K: Intensity from IDF_Lookup
        ws.cell(
            row=r, column=11,
            value=(f'=IF({from_ref}="","",'
                   f'XLOOKUP(ROUND(J{r},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}]))')
        )
        # L: Q = SumCA * Intensity
        ws.cell(row=r, column=12, value=f'=IF({from_ref}="","",I{r}*K{r})')
        # M: Size (in) from Pipes table
        ws.cell(
            row=r, column=13,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Size_in]),""))')
        )
        # N: Material (Type) from Pipes
        ws.cell(
            row=r, column=14,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Material]),""))')
        )
        # O: Manning n from Pipes
        ws.cell(
            row=r, column=15,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Manning_n]),0.013))')
        )

    dv_from = DataValidation(type="list",
                             formula1='=INDIRECT("Structures[Structure_ID]")',
                             allow_blank=True)
    dv_from.add(f"A14:A{last_row}")
    ws.add_data_validation(dv_from)
    dv_to = DataValidation(type="list",
                           formula1='=INDIRECT("Structures[Structure_ID]")',
                           allow_blank=True)
    dv_to.add(f"B14:B{last_row}")
    ws.add_data_validation(dv_to)

    for i, w in enumerate([10, 10, 8, 8, 7, 7, 7, 8, 8, 7, 8, 8, 7, 8, 8], start=1):
        col_letter = chr(ord("A") + i - 1)
        ws.column_dimensions[col_letter].width = w


def build_pipe_capacity_sheets(wb: Workbook) -> None:
    ws10 = wb.create_sheet("10 Yr Pipe Capacity")
    _build_single_pipe_capacity(ws10, storm="10yr", storm_label="10")
    ws25 = wb.create_sheet("25 Yr Pipe Capacity")
    _build_single_pipe_capacity(ws25, storm="25yr", storm_label="25")

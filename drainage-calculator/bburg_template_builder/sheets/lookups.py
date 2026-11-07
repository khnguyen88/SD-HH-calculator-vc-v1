"""Small lookup tables: Landuse_Lookup, Pipe_Properties, Kb_Values."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import (
    LANDUSE_SEED, PIPE_PROPERTIES, KB_VALUES, PARTIAL_FLOW_SEED,
)


def _add_table(ws, name: str, ref: str) -> None:
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)


def build_landuse_lookup_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Landuse_Lookup")
    headers = ["Landuse", "C_2-10", "C_25", "Description"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (landuse, c_2_10, c_25, desc) in enumerate(LANDUSE_SEED):
        row = 2 + i
        ws.cell(row=row, column=1, value=landuse)
        ws.cell(row=row, column=2, value=c_2_10)
        ws.cell(row=row, column=3, value=c_25)
        ws.cell(row=row, column=4, value=desc)
    last_row = 1 + len(LANDUSE_SEED)
    _add_table(ws, "Landuse_Lookup", f"A1:D{last_row}")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 42


def build_pipe_properties_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Pipe_Properties")
    headers = ["Size", "Area", "Perimeter", "Hyd Radius"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (size, area, perim) in enumerate(PIPE_PROPERTIES):
        row = 2 + i
        ws.cell(row=row, column=1, value=size)
        ws.cell(row=row, column=2, value=area)
        ws.cell(row=row, column=3, value=perim)
        ws.cell(row=row, column=4, value=f"=B{row}/C{row}")
    last_row = 1 + len(PIPE_PROPERTIES)
    _add_table(ws, "Pipe_Properties", f"A1:D{last_row}")
    for col in ("A", "B", "C", "D"):
        ws.column_dimensions[col].width = 11

    # PartialFlow sub-table below with a 2-row gap
    pf_start = last_row + 3
    ws.cell(row=pf_start, column=1, value="y_over_do")
    ws.cell(row=pf_start, column=2, value="A_over_do2")
    ws.cell(row=pf_start, column=3, value="AR23_over_do83")
    for i, (y, a, ar) in enumerate(PARTIAL_FLOW_SEED):
        row = pf_start + 1 + i
        ws.cell(row=row, column=1, value=y)
        ws.cell(row=row, column=2, value=a)
        ws.cell(row=row, column=3, value=ar)
    pf_last_row = pf_start + len(PARTIAL_FLOW_SEED)
    _add_table(ws, "PartialFlow", f"A{pf_start}:C{pf_last_row}")


def build_kb_values_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Kb_Values")
    headers = ["Angle", "Inlet", "Manhole", "Bend", "Junction"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (angle, inlet, manhole, bend, junction) in enumerate(KB_VALUES):
        row = 2 + i
        ws.cell(row=row, column=1, value=angle)
        ws.cell(row=row, column=2, value=inlet)
        ws.cell(row=row, column=3, value=manhole)
        ws.cell(row=row, column=4, value=bend)
        ws.cell(row=row, column=5, value=junction)
    last_row = 1 + len(KB_VALUES)
    _add_table(ws, "Kb_Values", f"A1:E{last_row}")
    for col in ("A", "B", "C", "D", "E"):
        ws.column_dimensions[col].width = 10

"""Pipes sheet - one row per pipe reach."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import (
    BLADENSBURG_PIPES, DEFAULT_ROW_COUNTS, MATERIAL_MANNING, PIPE_PROPERTIES,
)


HEADERS = ["Pipe_ID", "From_Structure", "To_Structure", "Length_ft",
           "Size_in", "Material", "Manning_n", "Slope_ftft"]

MATERIAL_LIST = tuple(MATERIAL_MANNING.keys())
PIPE_SIZE_LIST = tuple(str(int(p[0])) for p in PIPE_PROPERTIES)


def build_pipes_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Pipes")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    # Helper range on columns J:K for the Material -> Manning_n map.
    ws.cell(row=1, column=10, value="Material")
    ws.cell(row=1, column=11, value="Default_n")
    for i, (mat, n) in enumerate(MATERIAL_MANNING.items()):
        ws.cell(row=2 + i, column=10, value=mat)
        ws.cell(row=2 + i, column=11, value=n)
    _last_mat_row = 1 + len(MATERIAL_MANNING)

    for i, p in enumerate(BLADENSBURG_PIPES):
        row = 2 + i
        ws.cell(row=row, column=1, value=p["Pipe_ID"])
        ws.cell(row=row, column=2, value=p["From_Structure"])
        ws.cell(row=row, column=3, value=p["To_Structure"])
        ws.cell(row=row, column=4, value=p["Length_ft"])
        ws.cell(row=row, column=5, value=p["Size_in"])
        ws.cell(row=row, column=6, value=p["Material"])
        ws.cell(row=row, column=8, value=p["Slope_ftft"])

    data_rows = max(DEFAULT_ROW_COUNTS["Pipes"], len(BLADENSBURG_PIPES))
    for i in range(data_rows):
        row = 2 + i
        ws.cell(
            row=row, column=7,
            value=(f'=IF(F{row}="","",'
                   f'XLOOKUP(F{row},$J$2:$J${_last_mat_row},$K$2:$K${_last_mat_row},0.013))')
        )

    last_row = 1 + data_rows
    table = Table(displayName="Pipes", ref=f"A1:H{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    dv_from = DataValidation(type="list",
                             formula1='=INDIRECT("Structures[Structure_ID]")',
                             allow_blank=True)
    dv_from.add(f"B2:B{last_row}")
    ws.add_data_validation(dv_from)

    dv_to = DataValidation(type="list",
                           formula1='=INDIRECT("Structures[Structure_ID]")',
                           allow_blank=True)
    dv_to.add(f"C2:C{last_row}")
    ws.add_data_validation(dv_to)

    dv_material = DataValidation(type="list",
                                 formula1=f'"{",".join(MATERIAL_LIST)}"',
                                 allow_blank=True)
    dv_material.add(f"F2:F{last_row}")
    ws.add_data_validation(dv_material)

    dv_size = DataValidation(type="list",
                             formula1=f'"{",".join(PIPE_SIZE_LIST)}"',
                             allow_blank=True)
    dv_size.add(f"E2:E{last_row}")
    ws.add_data_validation(dv_size)

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    for col in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col].width = 11
    ws.column_dimensions["J"].width = 10
    ws.column_dimensions["K"].width = 10

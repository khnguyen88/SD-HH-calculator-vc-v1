"""Structures sheet - one row per physical structure (inlet, manhole, outfall, etc.)."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import BLADENSBURG_STRUCTURES, DEFAULT_ROW_COUNTS


HEADERS = ["Structure_ID", "Type", "Description", "Rim_Elev",
           "Inv_In_Elev", "Inv_Out_Elev", "Angle_deg", "Linked_Pond_TW"]

TYPE_LIST = ("inlet", "manhole", "bend", "junction", "splitter", "outfall")


def build_structures_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Structures")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    for i, s in enumerate(BLADENSBURG_STRUCTURES):
        row = 2 + i
        ws.cell(row=row, column=1, value=s["Structure_ID"])
        ws.cell(row=row, column=2, value=s["Type"])
        ws.cell(row=row, column=3, value=s["Description"])
        ws.cell(row=row, column=4, value=s["Rim_Elev"])
        ws.cell(row=row, column=5, value=s["Inv_In_Elev"])
        ws.cell(row=row, column=6, value=s["Inv_Out_Elev"])
        ws.cell(row=row, column=7, value=s["Angle_deg"])

    data_rows = max(DEFAULT_ROW_COUNTS["Structures"], len(BLADENSBURG_STRUCTURES))
    last_row = 1 + data_rows
    table = Table(displayName="Structures", ref=f"A1:H{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    dv_type = DataValidation(type="list", formula1=f'"{",".join(TYPE_LIST)}"', allow_blank=True)
    dv_type.add(f"B2:B{last_row}")
    ws.add_data_validation(dv_type)

    dv_angle = DataValidation(type="whole", operator="between",
                              formula1="0", formula2="180", allow_blank=True)
    dv_angle.add(f"G2:G{last_row}")
    ws.add_data_validation(dv_angle)

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 28
    for col in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col].width = 12

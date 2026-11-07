"""NOAA14 sheet - Atlas 14 depth table for all MD counties + DC."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import (
    NOAA14_SEED, NOAA14_BLANK_COUNTIES, NOAA14_STORMS, NOAA14_DURATIONS_MIN,
)


def build_noaa14_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("NOAA14")

    headers = ["County", "lat", "lon", "Storm"] + [f"d{d}" for d in NOAA14_DURATIONS_MIN]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)

    row = 2
    for county, data in NOAA14_SEED.items():
        for storm in NOAA14_STORMS:
            ws.cell(row=row, column=1, value=county)
            ws.cell(row=row, column=2, value=data["lat"])
            ws.cell(row=row, column=3, value=data["lon"])
            ws.cell(row=row, column=4, value=storm)
            depths = data[storm]
            for i, d in enumerate(NOAA14_DURATIONS_MIN):
                ws.cell(row=row, column=5 + i, value=depths[d])
            row += 1

    for county in NOAA14_BLANK_COUNTIES:
        for storm in NOAA14_STORMS:
            ws.cell(row=row, column=1, value=county)
            ws.cell(row=row, column=4, value=storm)
            row += 1

    last_row = row - 1
    last_col_letter = chr(ord("A") + len(headers) - 1)
    table_ref = f"A1:{last_col_letter}{last_row}"
    table = Table(displayName="NOAA14", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    ws.column_dimensions["A"].width = 20
    for col in ("B", "C", "D"):
        ws.column_dimensions[col].width = 10
    for col in ("E", "F", "G", "H", "I"):
        ws.column_dimensions[col].width = 8

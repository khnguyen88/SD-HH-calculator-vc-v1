"""DA_Catchments sheet - long-form source of truth for Rational Method.

One row per (Inlet_ID, DA_ID, Soil, Slope, Landuse, Area). Inlets with N drainage
subareas appear as N rows with the same Inlet_ID. Downstream sheets read via
SUMIFS/SUMPRODUCT by Inlet_ID - never by hard-coded cell address.
"""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import (
    BLADENSBURG_DA_CATCHMENTS, DEFAULT_ROW_COUNTS, LANDUSE_SEED,
)


HEADERS = ["Inlet_ID", "DA_ID", "Soil", "Slope", "Landuse",
           "Area_SF", "C_2-10", "C_25", "Notes"]

SOIL_LIST = ("A", "B", "C", "D", "---")
SLOPE_LIST = ("0-2%", "2-7%", "7%+", "---")


def build_da_catchments_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("DA_Catchments")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    for i, seed in enumerate(BLADENSBURG_DA_CATCHMENTS):
        row = 2 + i
        ws.cell(row=row, column=1, value=seed["Inlet_ID"])
        ws.cell(row=row, column=2, value=seed["DA_ID"])
        ws.cell(row=row, column=3, value=seed["Soil"])
        ws.cell(row=row, column=4, value=seed["Slope"])
        ws.cell(row=row, column=5, value=seed["Landuse"])
        ws.cell(row=row, column=6, value=seed["Area_SF"])

    data_rows = max(DEFAULT_ROW_COUNTS["DA_Catchments"], len(BLADENSBURG_DA_CATCHMENTS))

    for i in range(data_rows):
        row = 2 + i
        ws.cell(
            row=row, column=7,
            value=f'=IF(E{row}="","",XLOOKUP(E{row},Landuse_Lookup[Landuse],Landuse_Lookup[C_2-10],""))'
        )
        ws.cell(
            row=row, column=8,
            value=f'=IF(E{row}="","",XLOOKUP(E{row},Landuse_Lookup[Landuse],Landuse_Lookup[C_25],""))'
        )

    last_row = 1 + data_rows
    table = Table(displayName="DA_Catchments", ref=f"A1:I{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    dv_soil = DataValidation(type="list", formula1=f'"{",".join(SOIL_LIST)}"', allow_blank=True)
    dv_soil.add(f"C2:C{last_row}")
    ws.add_data_validation(dv_soil)

    dv_slope = DataValidation(type="list", formula1=f'"{",".join(SLOPE_LIST)}"', allow_blank=True)
    dv_slope.add(f"D2:D{last_row}")
    ws.add_data_validation(dv_slope)

    landuse_names = [l[0] for l in LANDUSE_SEED]
    dv_landuse = DataValidation(type="list", formula1=f'"{",".join(landuse_names)}"', allow_blank=True)
    dv_landuse.add(f"E2:E{last_row}")
    ws.add_data_validation(dv_landuse)

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 6
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 8
    ws.column_dimensions["H"].width = 8
    ws.column_dimensions["I"].width = 24

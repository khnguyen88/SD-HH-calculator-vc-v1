"""Rationals-MCDOT report view - per-inlet calc-sheet layout, auto-filled from DA_Catchments.

Layout preserves legacy 30-row x 9-col block layout with 3 blocks per horizontal band
at columns B, K, T. Each block reads via SUMIFS/SUMPRODUCT on DA_Catchments by Inlet_ID.

Block anchor cells (Inlet_ID header):
  Band 1 rows 5..34:  B5, K5, T5
  Band 2 rows 35..64: B35, K35, T35
  ...
  Band 6 rows 155..184

Within each block (base_col is starting column):
  Header:           base_col+0 row+0  Inlet_ID (seeded or blank)
  Column labels:    rows +4..+5
  Landuse rows:     row +6 (FILTER dynamic arrays spill downward)
  TOTALS row:       row +15  Area/CA via SUMIFS/SUMPRODUCT
  Composite C:      rows +17..+18
  Tc section:       rows +19..+20
  Rainfall/Q rows:  rows +22..+24  (2yr, 10yr, 25yr)
"""
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from bburg_template_builder.seed_data import BLADENSBURG_STRUCTURES


ANCHOR_ROWS = [5, 35, 65, 95, 125, 155]  # 6 bands
ANCHOR_COLS = [2, 11, 20]  # three blocks per band (B, K, T)

STORMS_IN_BLOCK = ("2yr", "10yr", "25yr")


def _block_anchor(block_index: int) -> tuple[int, int]:
    band = block_index // len(ANCHOR_COLS)
    pos = block_index % len(ANCHOR_COLS)
    return ANCHOR_ROWS[band], ANCHOR_COLS[pos]


def _build_block(ws, block_index: int, inlet_id_value) -> None:
    anchor_row, anchor_col = _block_anchor(block_index)

    def col(offset: int) -> int:
        return anchor_col + offset

    def R(offset: int) -> int:
        return anchor_row + offset

    # Header
    ws.cell(row=R(0), column=col(0), value=inlet_id_value)
    ws.cell(row=R(1), column=col(3), value="COMPUTED")

    # Column labels
    ws.cell(row=R(4), column=col(0), value="SOIL TYPE")
    ws.cell(row=R(4), column=col(1), value="% SLOPE")
    ws.cell(row=R(4), column=col(2), value="LANDUSE")
    ws.cell(row=R(4), column=col(3), value="AREA (SF)")
    ws.cell(row=R(4), column=col(4), value="2, 10-YR")
    ws.cell(row=R(4), column=col(6), value="25-YR")
    ws.cell(row=R(5), column=col(4), value="C")
    ws.cell(row=R(5), column=col(5), value="CA")
    ws.cell(row=R(5), column=col(6), value="C")
    ws.cell(row=R(5), column=col(7), value="CA")

    inlet_ref_cell = f"{get_column_letter(col(0))}{R(0)}"
    filter_row = R(6)

    # FILTER formulas spill down from row +6
    filter_formulas = [
        (col(0), f'=IFERROR(FILTER(DA_Catchments[Soil],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(1), f'=IFERROR(FILTER(DA_Catchments[Slope],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(2), f'=IFERROR(FILTER(DA_Catchments[Landuse],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(3), f'=IFERROR(FILTER(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(4), f'=IFERROR(FILTER(DA_Catchments[C_2-10],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(5), f'=IFERROR(FILTER(DA_Catchments[Area_SF]*DA_Catchments[C_2-10],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(6), f'=IFERROR(FILTER(DA_Catchments[C_25],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
        (col(7), f'=IFERROR(FILTER(DA_Catchments[Area_SF]*DA_Catchments[C_25],DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")'),
    ]
    for col_num, formula in filter_formulas:
        ws.cell(row=filter_row, column=col_num, value=formula)

    totals_row = R(15)
    ws.cell(row=totals_row, column=col(2), value="TOTALS")
    ws.cell(
        row=totals_row, column=col(3),
        value=f"=SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{inlet_ref_cell})"
    )
    ws.cell(
        row=totals_row, column=col(5),
        value=(f"=SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref_cell})"
               f"*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])")
    )
    ws.cell(
        row=totals_row, column=col(7),
        value=(f"=SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref_cell})"
               f"*DA_Catchments[Area_SF]*DA_Catchments[C_25])")
    )

    # Composite C
    ws.cell(row=R(17), column=col(2), value="COMPOSITE C (2,10)")
    ws.cell(
        row=R(17), column=col(3),
        value=f"=IFERROR({get_column_letter(col(5))}{totals_row}/{get_column_letter(col(3))}{totals_row},0)"
    )
    ws.cell(row=R(18), column=col(2), value="COMPOSITE C (25)")
    ws.cell(
        row=R(18), column=col(3),
        value=f"=IFERROR({get_column_letter(col(7))}{totals_row}/{get_column_letter(col(3))}{totals_row},0)"
    )

    # Tc section
    ws.cell(row=R(19), column=col(0), value="TIME OF CONCENTRATION")
    ws.cell(row=R(20), column=col(0), value="Tc =")
    ws.cell(row=R(20), column=col(1), value=5)
    ws.cell(row=R(20), column=col(2), value="MIN")

    # Intensity + Q rows (storm 2, 10, 25)
    tc_cell_ref = f"{get_column_letter(col(1))}{R(20)}"
    ws.cell(row=R(21), column=col(3), value="STORM")
    ws.cell(row=R(21), column=col(4), value="i (IN/HR)")
    ws.cell(row=R(21), column=col(5), value="Q (CFS)")
    composite_c_210_ref = f"{get_column_letter(col(3))}{R(17)}"
    composite_c_25_ref = f"{get_column_letter(col(3))}{R(18)}"
    area_total_ref = f"{get_column_letter(col(3))}{totals_row}"
    for i, storm in enumerate(STORMS_IN_BLOCK):
        r = R(22 + i)
        label_year = {"2yr": 2, "10yr": 10, "25yr": 25}[storm]
        ws.cell(row=r, column=col(3), value=label_year)
        ws.cell(
            row=r, column=col(4),
            value=f"=XLOOKUP(ROUND({tc_cell_ref},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}])"
        )
        c_ref = composite_c_25_ref if storm == "25yr" else composite_c_210_ref
        ws.cell(
            row=r, column=col(5),
            value=f"={c_ref}*{get_column_letter(col(4))}{r}*{area_total_ref}/43560"
        )


def build_rationals_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Rationals-MCDOT")
    ws.cell(row=1, column=1, value="PROJECT:")
    ws.cell(row=1, column=2, value="=Project_Name")
    ws.cell(row=2, column=1, value="JOB #:")
    ws.cell(row=2, column=2, value="=Project_Number")

    inlet_structures = [s for s in BLADENSBURG_STRUCTURES if s["Type"] == "inlet"]
    total_blocks = len(ANCHOR_ROWS) * len(ANCHOR_COLS)
    for block_index in range(total_blocks):
        if block_index < len(inlet_structures):
            inlet_id_value = inlet_structures[block_index]["Structure_ID"]
        else:
            inlet_id_value = ""
        _build_block(ws, block_index, inlet_id_value)

    for band_start_col in ANCHOR_COLS:
        for offset, width in enumerate([8, 8, 14, 10, 6, 10, 6, 10, 2]):
            col_letter = get_column_letter(band_start_col + offset)
            ws.column_dimensions[col_letter].width = width

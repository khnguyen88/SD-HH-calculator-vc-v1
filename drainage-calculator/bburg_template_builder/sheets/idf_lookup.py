"""IDF_Lookup sheet - computes rainfall intensity at any Tc via power-law interp of NOAA14.

Formula model (per spec 5.3): for a given (County_Selected, storm, Tc), find the two
bracketing durations in {5,10,15,30,60} min, fit i = 60*a*t^(b-1) between them,
and return intensity at Tc.
"""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import NOAA14_STORMS, NOAA14_DURATIONS_MIN


DURATIONS = list(NOAA14_DURATIONS_MIN)  # [5, 10, 15, 30, 60]


def _depth_lookup_formula(county_ref: str, storm_literal: str, duration: int) -> str:
    """Return the SUMIFS-based formula for NOAA14 depth lookup at (county, storm, duration)."""
    depth_col = f"d{duration}"
    return (
        f'SUMIFS(NOAA14[{depth_col}],'
        f'NOAA14[County],{county_ref},'
        f'NOAA14[Storm],"{storm_literal}")'
    )


def _intensity_formula_for_tc_cell(tc_cell_ref: str, storm: str) -> str:
    """Build the intensity formula for a specific Tc cell and storm.

    Uses nested IFS to pick the correct bracketing duration pair:
      Tc <= 5:       i = 60 * d5 / 5
      5 < Tc <= 10:  fit (5, d5)-(10, d10) at Tc
      10 < Tc <= 15: fit (10, d10)-(15, d15) at Tc
      15 < Tc <= 30: fit (15, d15)-(30, d30) at Tc
      30 < Tc <= 60: fit (30, d30)-(60, d60) at Tc
      Tc > 60:       i = d60 (extrapolated flat)

    Power-law fit between (t_lo, d_lo) and (t_hi, d_hi) at Tc:
      b = LN(d_hi/d_lo) / LN(t_hi/t_lo)
      depth(Tc) = d_lo * (Tc/t_lo)^b
      i = 60 * depth(Tc) / Tc
    """
    county = "County_Selected"
    d_lookups = {d: _depth_lookup_formula(county, storm, d) for d in DURATIONS}

    def pl_i(t_lo: int, t_hi: int) -> str:
        d_lo_frag = d_lookups[t_lo]
        d_hi_frag = d_lookups[t_hi]
        b_expr = f"LN(({d_hi_frag})/({d_lo_frag}))/LN({t_hi}/{t_lo})"
        depth_tc = f"({d_lo_frag})*({tc_cell_ref}/{t_lo})^({b_expr})"
        return f"60*({depth_tc})/{tc_cell_ref}"

    i_at_or_below_5 = f"60*({d_lookups[5]})/5"
    i_above_60 = d_lookups[60]  # flat extrapolation

    return (
        f"=IFS("
        f"{tc_cell_ref}<=5,{i_at_or_below_5},"
        f"{tc_cell_ref}<=10,{pl_i(5, 10)},"
        f"{tc_cell_ref}<=15,{pl_i(10, 15)},"
        f"{tc_cell_ref}<=30,{pl_i(15, 30)},"
        f"{tc_cell_ref}<=60,{pl_i(30, 60)},"
        f"TRUE,{i_above_60}"
        f")"
    )


def build_idf_lookup_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("IDF_Lookup")

    headers = ["Tc_min"] + [f"i_{s}" for s in NOAA14_STORMS]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)

    tc_values = [round(5.0 + 0.1 * i, 1) for i in range(0, 551)]
    for i, tc in enumerate(tc_values):
        row = 2 + i
        ws.cell(row=row, column=1, value=tc)
        tc_cell_ref = f"$A{row}"
        for c, storm in enumerate(NOAA14_STORMS, start=2):
            ws.cell(row=row, column=c, value=_intensity_formula_for_tc_cell(tc_cell_ref, storm))

    last_col_letter = chr(ord("A") + len(headers) - 1)
    table_ref = f"A1:{last_col_letter}{1 + len(tc_values)}"
    table = Table(displayName="IDF_Lookup", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    ws.column_dimensions["A"].width = 10
    for i in range(2, len(headers) + 1):
        col_letter = chr(ord("A") + i - 1)
        ws.column_dimensions[col_letter].width = 10

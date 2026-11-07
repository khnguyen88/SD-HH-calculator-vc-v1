import re
from bburg_template_builder.sheets.da_catchments import build_da_catchments_sheet
from bburg_template_builder.seed_data import BLADENSBURG_DA_CATCHMENTS, DEFAULT_ROW_COUNTS


def test_sheet_created(empty_wb):
    build_da_catchments_sheet(empty_wb)
    assert "DA_Catchments" in empty_wb.sheetnames


def test_headers(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    expected = ["Inlet_ID", "DA_ID", "Soil", "Slope", "Landuse",
                "Area_SF", "C_2-10", "C_25", "Notes"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_default_row_count(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    expected_data_rows = max(DEFAULT_ROW_COUNTS["DA_Catchments"], len(BLADENSBURG_DA_CATCHMENTS))
    table = ws.tables["DA_Catchments"]
    end_cell = table.ref.split(":")[1]
    match = re.match(r"([A-Z]+)(\d+)", end_cell)
    assert match
    last_row = int(match.group(2))
    assert last_row - 1 == expected_data_rows


def test_bladensburg_seed_at_top(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    for i, seed in enumerate(BLADENSBURG_DA_CATCHMENTS):
        row = 2 + i
        assert ws.cell(row=row, column=1).value == seed["Inlet_ID"]
        assert ws.cell(row=row, column=2).value == seed["DA_ID"]
        assert ws.cell(row=row, column=6).value == seed["Area_SF"]


def test_c_values_are_literal_for_seeded_rows_and_formula_beyond(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    first_blank = 2 + len(BLADENSBURG_DA_CATCHMENTS)
    c_2_10_formula = ws.cell(row=first_blank, column=7).value
    c_25_formula = ws.cell(row=first_blank, column=8).value
    assert "Landuse_Lookup" in str(c_2_10_formula)
    assert "Landuse_Lookup" in str(c_25_formula)
    # Legacy-seeded rows carry their composite C directly.
    assert ws.cell(row=2, column=7).value == BLADENSBURG_DA_CATCHMENTS[0]["C_2_10"]


def test_soil_dropdown_present(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    soil_dvs = [dv for dv in ws.data_validations.dataValidation
                if any("C" in rng.coord.split(":")[0] for rng in dv.sqref.ranges)]
    assert soil_dvs, "No data validation found on Soil column (C)"

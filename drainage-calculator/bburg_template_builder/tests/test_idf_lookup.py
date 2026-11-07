import pytest
from bburg_template_builder.sheets.idf_lookup import build_idf_lookup_sheet


def test_idf_sheet_created(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    assert "IDF_Lookup" in empty_wb.sheetnames


def test_tc_column_5_to_60_at_0p1_increments(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    assert ws.cell(row=2, column=1).value == 5.0
    assert ws.cell(row=552, column=1).value == pytest.approx(60.0, abs=1e-6)


def test_headers(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    expected = ["Tc_min", "i_1yr", "i_2yr", "i_5yr", "i_10yr", "i_25yr", "i_50yr", "i_100yr", "i_500yr"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_table_registered(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    assert "IDF_Lookup" in ws.tables


def test_formula_uses_county_selected_and_noaa14(empty_wb):
    """The intensity formula must dereference County_Selected and lookup NOAA14 depths."""
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    # Mid-row: Tc = 7.0 min = row 2 + 20 = 22
    formula = ws.cell(row=22, column=5).value  # i_10yr column
    assert formula.startswith("="), f"Formula must start with =: got {formula!r}"
    assert "County_Selected" in formula
    assert "NOAA14" in formula
    assert "10yr" in formula

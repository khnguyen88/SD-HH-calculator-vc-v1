import pytest
from bburg_template_builder.sheets.noaa14 import build_noaa14_sheet
from bburg_template_builder.seed_data import NOAA14_SEED, NOAA14_BLANK_COUNTIES, NOAA14_STORMS


EXPECTED_COLUMNS = ["County", "lat", "lon", "Storm", "d5", "d10", "d15", "d30", "d60"]


def test_noaa14_sheet_created(empty_wb):
    build_noaa14_sheet(empty_wb)
    assert "NOAA14" in empty_wb.sheetnames


def test_headers_present(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(EXPECTED_COLUMNS) + 1)]
    assert actual == EXPECTED_COLUMNS


def test_one_row_per_county_per_storm(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    counties = len(NOAA14_SEED) + len(NOAA14_BLANK_COUNTIES)
    storms = len(NOAA14_STORMS)
    expected_data_rows = counties * storms
    last_row_with_county = max(
        r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value
    )
    assert last_row_with_county - 1 == expected_data_rows


def test_table_registered(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    assert "NOAA14" in ws.tables, f"Tables on sheet: {list(ws.tables.keys())}"


def test_montgomery_10yr_values_match_seed(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    seed = NOAA14_SEED["Montgomery"]["10yr"]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "Montgomery" and ws.cell(row=r, column=4).value == "10yr":
            assert ws.cell(row=r, column=5).value == seed[5]
            assert ws.cell(row=r, column=6).value == seed[10]
            assert ws.cell(row=r, column=7).value == seed[15]
            assert ws.cell(row=r, column=8).value == seed[30]
            assert ws.cell(row=r, column=9).value == seed[60]
            return
    pytest.fail("Montgomery / 10yr row not found")


def test_blank_counties_have_blank_depths(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "Allegany":
            for c in range(5, 10):
                assert ws.cell(row=r, column=c).value in (None, "")
            return
    pytest.fail("Allegany (a blank county) row not found")

import re
from bburg_template_builder.sheets.inlet_spacing import build_inlet_spacing_sheets


def test_both_sheets_created(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    assert "Inlet Spacing_10-yr" in empty_wb.sheetnames
    assert "Inlet Spacing_2-yr" in empty_wb.sheetnames


def test_no_hardcoded_rationals_cell_refs(empty_wb):
    """Forbidden: ='Rationals-MCDOT'!A1 style A1 cell references."""
    build_inlet_spacing_sheets(empty_wb)
    forbidden_pattern = re.compile(r"'Rationals-MCDOT'![A-Z]+\d+(?!:)")
    for sheet_name in ("Inlet Spacing_10-yr", "Inlet Spacing_2-yr"):
        ws = empty_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    assert not forbidden_pattern.search(cell.value), (
                        f"{sheet_name} {cell.coordinate}: hard-coded ref: {cell.value}"
                    )


def test_area_column_uses_sumifs_on_da_catchments(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_10-yr"]
    val = ws.cell(row=11, column=4).value
    assert "SUMIFS" in str(val) and "DA_Catchments" in str(val)


def test_intensity_column_uses_idf_lookup(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_10-yr"]
    val = ws.cell(row=11, column=10).value
    assert "IDF_Lookup" in str(val) or "XLOOKUP" in str(val)
    assert "i_10yr" in str(val)


def test_sheet_2yr_uses_i_2yr_column(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_2-yr"]
    val = ws.cell(row=11, column=10).value
    assert "i_2yr" in str(val)

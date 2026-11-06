from bburg_template_builder.sheets.rationals_mcdot import build_rationals_sheet


def test_sheet_created(empty_wb):
    build_rationals_sheet(empty_wb)
    assert "Rationals-MCDOT" in empty_wb.sheetnames


def test_first_block_has_inlet_id_header(empty_wb):
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    val = ws.cell(row=5, column=2).value
    assert val is not None


def test_block1_total_area_uses_sumifs(empty_wb):
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    totals_row = 20
    formula = ws.cell(row=totals_row, column=5).value
    assert "SUMIFS" in str(formula) or "SUMPRODUCT" in str(formula)
    assert "DA_Catchments" in str(formula)


def test_block1_intensity_uses_idf_lookup(empty_wb):
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    for storm_row in (27, 28, 29):
        formula = ws.cell(row=storm_row, column=6).value
        assert "IDF_Lookup" in str(formula) or "XLOOKUP" in str(formula)


def test_three_blocks_per_band(empty_wb):
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    assert ws.cell(row=5, column=2).value is not None
    assert ws.cell(row=5, column=11).value is not None
    assert ws.cell(row=5, column=20).value is not None

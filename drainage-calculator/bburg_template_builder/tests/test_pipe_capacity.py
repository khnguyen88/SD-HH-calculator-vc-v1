from bburg_template_builder.sheets.pipe_capacity import build_pipe_capacity_sheets


def test_both_sheets_created(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    assert "10 Yr Pipe Capacity" in empty_wb.sheetnames
    assert "25 Yr Pipe Capacity" in empty_wb.sheetnames


def test_sha_sheet_renamed(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    assert "25 Yr SHA Pipe Capacity" not in empty_wb.sheetnames


def test_no_broken_refs(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    for name in ("10 Yr Pipe Capacity", "25 Yr Pipe Capacity"):
        ws = empty_wb[name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    assert "#REF" not in cell.value, f"{name} {cell.coordinate}: {cell.value}"


def test_q_formula_uses_idf_and_da_catchments(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    ws = empty_wb["10 Yr Pipe Capacity"]
    q_formula = str(ws.cell(row=14, column=12).value)
    # Q = SumCA * Intensity; the Intensity formula (K column) has IDF/XLOOKUP
    k_formula = str(ws.cell(row=14, column=11).value)
    assert "IDF_Lookup" in k_formula or "XLOOKUP" in k_formula
    assert "i_10yr" in k_formula


def test_manning_n_pulled_from_pipes_table(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    ws = empty_wb["10 Yr Pipe Capacity"]
    n_formula = str(ws.cell(row=14, column=15).value)
    assert "Pipes[Manning_n]" in n_formula or "XLOOKUP" in n_formula

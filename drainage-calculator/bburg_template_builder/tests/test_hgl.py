from bburg_template_builder.sheets.hgl import build_hgl_sheet


def test_sheet_created(empty_wb):
    build_hgl_sheet(empty_wb)
    assert "HGL" in empty_wb.sheetnames


def test_top_inputs_present(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    labels = [ws.cell(row=r, column=c).value for r in range(1, 7) for c in range(1, 8)]
    label_text = " ".join(str(x) for x in labels if x)
    assert "TW_Elev_Start" in label_text or "Starting tailwater" in label_text
    assert "Storm" in label_text
    assert "HGL_Method" in label_text or "Method" in label_text


def test_hgl_has_expected_columns(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_cells = [ws.cell(row=8, column=c).value for c in range(1, 32)]
    header_text = " ".join(str(x) for x in header_cells if x)
    for required in ("Pipe_ID", "From", "To", "Q", "Size", "n",
                     "V", "Vh", "Sf", "Hf", "Kb", "Hb",
                     "HGL_dn", "EGL_dn", "HGL_up", "EGL_up", "Regime"):
        assert required in header_text, f"Missing column header: {required}"


def test_hgl_up_formula_branches_on_hgl_method(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 32)
               if ws.cell(row=header_row, column=c).value}
    hgl_up_col = headers["HGL_up"]
    val = str(ws.cell(row=10, column=hgl_up_col).value)
    assert "HGL_Method" in val
    assert "Legacy" in val
    assert val.startswith("=") and ("IF(" in val or "SWITCH(" in val)


def test_first_row_hgl_dn_raw_uses_tw_elev_start(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 32)
               if ws.cell(row=header_row, column=c).value}
    hgl_dn_raw_col = headers["HGL_dn_raw"]
    val = str(ws.cell(row=10, column=hgl_dn_raw_col).value)
    assert "TW_Elev_Start" in val


def test_crown_check_references_crown_freeboard(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 32)
               if ws.cell(row=header_row, column=c).value}
    found = False
    for name, col in headers.items():
        if "Crown_check" == str(name):
            val = str(ws.cell(row=10, column=col).value)
            if "Crown_Freeboard" in val:
                found = True
                break
    assert found, "No Crown_check column referencing Crown_Freeboard"

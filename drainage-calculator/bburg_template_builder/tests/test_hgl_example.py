from bburg_template_builder.sheets.hgl_example import build_hgl_example_sheet


def test_sheet_created(empty_wb):
    build_hgl_example_sheet(empty_wb)
    assert "HGL_Example" in empty_wb.sheetnames


def test_inputs_at_top(empty_wb):
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    labels = [str(ws.cell(row=r, column=1).value or "") for r in range(1, 10)]
    assert any("tailwater" in s.lower() or "TW" in s for s in labels)


def test_has_four_pipe_blocks(empty_wb):
    """Expect 4 pipe blocks (P-4, P-3, P-2, P-1 in d/s-to-u/s order)."""
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    pipe_labels = [
        str(ws.cell(row=r, column=1).value or "")
        for r in range(1, ws.max_row + 1)
    ]
    for pid in ("P-4", "P-3", "P-2", "P-1"):
        assert any(pid in s for s in pipe_labels), f"Missing pipe block for {pid}"


def test_side_by_side_method_columns(empty_wb):
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    headers = [str(ws.cell(row=10, column=c).value or "") for c in range(1, 8)]
    header_text = " ".join(headers)
    assert "HEC-22" in header_text
    assert "Legacy" in header_text

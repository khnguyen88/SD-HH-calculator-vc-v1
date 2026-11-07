import re
from bburg_template_builder.sheets.pipes import build_pipes_sheet
from bburg_template_builder.seed_data import BLADENSBURG_PIPES, DEFAULT_ROW_COUNTS


def test_sheet_created(empty_wb):
    build_pipes_sheet(empty_wb)
    assert "Pipes" in empty_wb.sheetnames


def test_headers(empty_wb):
    build_pipes_sheet(empty_wb)
    ws = empty_wb["Pipes"]
    expected = ["Pipe_ID", "From_Structure", "To_Structure", "Length_ft",
                "Size_in", "Material", "Manning_n", "Slope_ftft", "Design_Q_cfs"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_default_row_count(empty_wb):
    build_pipes_sheet(empty_wb)
    ws = empty_wb["Pipes"]
    tbl = ws.tables["Pipes"]
    end_cell = tbl.ref.split(":")[1]
    m = re.match(r"[A-Z]+(\d+)", end_cell)
    assert m and int(m.group(1)) - 1 == max(DEFAULT_ROW_COUNTS["Pipes"], len(BLADENSBURG_PIPES))


def test_manning_n_is_formula_defaulted_from_material(empty_wb):
    build_pipes_sheet(empty_wb)
    ws = empty_wb["Pipes"]
    first_blank_row = 2 + len(BLADENSBURG_PIPES)
    val = ws.cell(row=first_blank_row, column=7).value
    assert str(val).startswith("=") and "SWITCH" in str(val)
    # Must reference at least one Manning_n_* named range from Config
    assert "Manning_n_RCP" in str(val) or "Manning_n_HDPE" in str(val)

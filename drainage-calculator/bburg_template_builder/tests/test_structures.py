import re
from bburg_template_builder.sheets.structures import build_structures_sheet
from bburg_template_builder.seed_data import BLADENSBURG_STRUCTURES, DEFAULT_ROW_COUNTS


def test_sheet_created(empty_wb):
    build_structures_sheet(empty_wb)
    assert "Structures" in empty_wb.sheetnames


def test_headers(empty_wb):
    build_structures_sheet(empty_wb)
    ws = empty_wb["Structures"]
    expected = ["Structure_ID", "Type", "Description", "Rim_Elev",
                "Inv_In_Elev", "Inv_Out_Elev", "Angle_deg", "Linked_Pond_TW"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_default_row_count(empty_wb):
    build_structures_sheet(empty_wb)
    ws = empty_wb["Structures"]
    tbl = ws.tables["Structures"]
    end_cell = tbl.ref.split(":")[1]
    m = re.match(r"[A-Z]+(\d+)", end_cell)
    assert m and int(m.group(1)) - 1 == max(DEFAULT_ROW_COUNTS["Structures"], len(BLADENSBURG_STRUCTURES))


def test_type_dropdown_has_six_options(empty_wb):
    build_structures_sheet(empty_wb)
    ws = empty_wb["Structures"]
    type_dvs = [dv for dv in ws.data_validations.dataValidation if dv.type == "list"]
    found = False
    for dv in type_dvs:
        if "inlet" in dv.formula1 and "outfall" in dv.formula1:
            found = True
            for t in ("inlet", "manhole", "bend", "junction", "splitter", "outfall"):
                assert t in dv.formula1
    assert found, "Type dropdown not found"


def test_bladensburg_outfall_seeded(empty_wb):
    build_structures_sheet(empty_wb)
    ws = empty_wb["Structures"]
    outfalls = [ws.cell(row=r, column=1).value for r in range(2, 10)
                if ws.cell(row=r, column=2).value == "outfall"]
    assert "OUTFALL" in outfalls

from bburg_template_builder.sheets.lookups import (
    build_landuse_lookup_sheet,
    build_pipe_properties_sheet,
    build_kb_values_sheet,
)
from bburg_template_builder.seed_data import LANDUSE_SEED, PIPE_PROPERTIES, KB_VALUES


def test_landuse_lookup_sheet_created(empty_wb):
    build_landuse_lookup_sheet(empty_wb)
    assert "Landuse_Lookup" in empty_wb.sheetnames
    ws = empty_wb["Landuse_Lookup"]
    assert "Landuse_Lookup" in ws.tables
    landuses = [ws.cell(row=r, column=1).value for r in range(2, 2 + len(LANDUSE_SEED))]
    assert landuses == [l[0] for l in LANDUSE_SEED]


def test_pipe_properties_sheet_created(empty_wb):
    build_pipe_properties_sheet(empty_wb)
    assert "Pipe_Properties" in empty_wb.sheetnames
    ws = empty_wb["Pipe_Properties"]
    assert "Pipe_Properties" in ws.tables
    sizes = [ws.cell(row=r, column=1).value for r in range(2, 2 + len(PIPE_PROPERTIES))]
    assert sizes == [p[0] for p in PIPE_PROPERTIES]


def test_pipe_properties_hyd_radius_is_formula(empty_wb):
    build_pipe_properties_sheet(empty_wb)
    ws = empty_wb["Pipe_Properties"]
    assert ws.cell(row=2, column=4).value.startswith("=")


def test_kb_values_sheet_created(empty_wb):
    build_kb_values_sheet(empty_wb)
    assert "Kb_Values" in empty_wb.sheetnames
    ws = empty_wb["Kb_Values"]
    assert "Kb_Values" in ws.tables
    headers = [ws.cell(row=1, column=c).value for c in range(1, 6)]
    assert headers == ["Angle", "Inlet", "Manhole", "Bend", "Junction"]


def test_kb_values_junction_equals_bend(empty_wb):
    build_kb_values_sheet(empty_wb)
    ws = empty_wb["Kb_Values"]
    for r in range(2, 2 + len(KB_VALUES)):
        bend_val = ws.cell(row=r, column=4).value
        junction_val = ws.cell(row=r, column=5).value
        assert bend_val == junction_val, f"Row {r}: Bend={bend_val} but Junction={junction_val}"


def test_kb_values_has_all_91_angles(empty_wb):
    """After Task 5 expansion, KB_VALUES must cover angles 0..90 (91 rows)."""
    assert len(KB_VALUES) == 91
    assert KB_VALUES[0][0] == 0
    assert KB_VALUES[-1][0] == 90

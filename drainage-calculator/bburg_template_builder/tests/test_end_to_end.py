"""End-to-end tests for the full workbook build. Keeps a running list of required sheets."""


REQUIRED_SHEETS = [
    "Config",
    "NOAA14",
    "IDF_Lookup",
    "Landuse_Lookup",
    "Pipe_Properties",
    "Kb_Values",
    "DA_Catchments",
    "Structures",
    "Pipes",
    "Rationals-MCDOT",
    "Inlet Spacing_10-yr",
    "Inlet Spacing_2-yr",
    "10 Yr Pipe Capacity",
    "25 Yr Pipe Capacity",
    "HGL",
    "HGL_Example",
]


def test_workbook_builds_without_errors(built_wb):
    # Just constructing the workbook should not raise.
    assert built_wb is not None


def test_workbook_has_all_required_sheets(built_wb):
    actual = set(built_wb.sheetnames)
    missing = [s for s in REQUIRED_SHEETS if s not in actual]
    assert not missing, f"Missing sheets: {missing}"


def test_workbook_has_no_extra_sheets(built_wb):
    # Guard against accidentally re-adding legacy sheets.
    forbidden = {"10 Yr MoCo HGL", "25 Yr SHA HGL", "HGL 25-yr",
                 "SHA Intensity", "MoCoIntensity", "Intensity",
                 "25 Yr SHA Pipe Capacity", "TABLES", "Kb Values MoCo"}
    overlap = forbidden & set(built_wb.sheetnames)
    assert not overlap, f"Legacy sheets must not be emitted: {overlap}"

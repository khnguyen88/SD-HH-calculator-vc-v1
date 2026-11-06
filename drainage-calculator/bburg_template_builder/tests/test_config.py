import pytest
from openpyxl.workbook.defined_name import DefinedName
from bburg_template_builder.sheets.config import build_config_sheet


EXPECTED_NAMED_RANGES = {
    "County_Selected", "Storm_Primary", "HGL_Method",
    "Project_Name", "Project_Number", "Designer", "Checker", "Date_Computed",
    "Manning_n_RCP", "Manning_n_HDPE", "Gravity_g", "Rim_Freeboard", "Crown_Freeboard",
}


def test_config_sheet_created(empty_wb):
    build_config_sheet(empty_wb)
    assert "Config" in empty_wb.sheetnames


def test_all_named_ranges_defined(empty_wb):
    build_config_sheet(empty_wb)
    actual = set(empty_wb.defined_names)
    missing = EXPECTED_NAMED_RANGES - actual
    assert not missing, f"Missing named ranges: {missing}"


def test_county_default_is_prince_georges(empty_wb):
    build_config_sheet(empty_wb)
    dn = empty_wb.defined_names["County_Selected"]
    sheet, coord = _parse_name_ref(dn)
    cell = empty_wb[sheet][coord]
    assert cell.value == "Prince George's"


def test_hgl_method_default_is_hec22(empty_wb):
    build_config_sheet(empty_wb)
    dn = empty_wb.defined_names["HGL_Method"]
    sheet, coord = _parse_name_ref(dn)
    cell = empty_wb[sheet][coord]
    assert cell.value == "HEC-22 EGL (d/s crown floor)"


def test_gravity_g_is_32_2(empty_wb):
    build_config_sheet(empty_wb)
    dn = empty_wb.defined_names["Gravity_g"]
    sheet, coord = _parse_name_ref(dn)
    cell = empty_wb[sheet][coord]
    assert cell.value == 32.2


def _parse_name_ref(dn: DefinedName) -> tuple[str, str]:
    """Parse a DefinedName like `Config!$B$3` into (sheet_name, cell_coord)."""
    attr = dn.attr_text
    sheet_part, coord = attr.split("!")
    sheet = sheet_part.strip("'")
    coord = coord.replace("$", "")
    return sheet, coord

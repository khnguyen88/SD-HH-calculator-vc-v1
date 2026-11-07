"""Config sheet - scalar inputs that drive the workbook via named ranges."""
from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


# (name, default_value, note). Values live on Config!$B$<row>, names on $A$<row>.
CONFIG_ROWS: tuple[tuple[str, object, str], ...] = (
    ("County_Selected",    "Prince George's",                 "Dropdown: NOAA14[County]"),
    ("Storm_Primary",      "10yr",                             "Dropdown: 10yr or 25yr (storms with Pipe Capacity sheets)"),
    ("HGL_Method",         "HEC-22 EGL (d/s crown floor)",    "HEC-22 (default) or Legacy both-end crown floor"),
    ("Project_Name",       "",                                 ""),
    ("Project_Number",     "",                                 ""),
    ("Designer",           "",                                 ""),
    ("Checker",            "",                                 ""),
    ("Date_Computed",      "",                                 ""),
    ("Manning_n_RCP",      0.013,                              "Manning's n for RCP (default)"),
    ("Manning_n_HDPE",     0.012,                              "Manning's n for HDPE (default)"),
    ("Manning_n_CMP",      0.024,                              "Manning's n for CMP"),
    ("Manning_n_PVC",      0.011,                              "Manning's n for PVC"),
    ("Manning_n_DIP",      0.013,                              "Manning's n for DIP"),
    ("Manning_n_Other",    0.013,                              "Manning's n for Other pipe material (user override)"),
    ("Gravity_g",          32.2,                               "ft/s^2"),
    ("Rim_Freeboard",      1.0,                                "ft (HGL check: HGL < Rim - freeboard)"),
    ("Crown_Freeboard",    1.0,                                "ft (HGL check: HGL < Crown + freeboard)"),
)

STORM_LIST = ("1yr", "2yr", "5yr", "10yr", "25yr", "50yr", "100yr", "500yr")
STORM_PRIMARY_LIST = ("10yr", "25yr")
HGL_METHOD_LIST = ("HEC-22 EGL (d/s crown floor)", "Legacy both-end crown floor")


def build_config_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Config")
    ws["A1"] = "Config name"
    ws["B1"] = "Value"
    ws["C1"] = "Notes"

    for idx, (name, value, note) in enumerate(CONFIG_ROWS):
        row = idx + 2  # headers in row 1, data from row 2
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=value)
        ws.cell(row=row, column=3, value=note)

        ref = f"Config!$B${row}"
        wb.defined_names[name] = DefinedName(name=name, attr_text=ref)

    # Data validation dropdowns.
    # County dropdown: helper range on Config!E2:E{N} lists every MD county + DC.
    # Keeps the dropdown-source visible and inspectable on the Config sheet itself.
    from bburg_template_builder.seed_data import NOAA14_SEED, NOAA14_BLANK_COUNTIES
    counties_for_dropdown = list(NOAA14_SEED.keys()) + list(NOAA14_BLANK_COUNTIES)
    for i, c in enumerate(counties_for_dropdown):
        ws.cell(row=2 + i, column=5, value=c)
    last_county_row = 1 + len(counties_for_dropdown)
    dv_county = DataValidation(type="list",
                               formula1=f"=Config!$E$2:$E${last_county_row}",
                               allow_blank=False)
    dv_county.add("B2")
    ws.add_data_validation(dv_county)

    dv_storm = DataValidation(type="list",
                              formula1=f'"{",".join(STORM_PRIMARY_LIST)}"',
                              allow_blank=False)
    dv_storm.add("B3")
    ws.add_data_validation(dv_storm)

    dv_method = DataValidation(type="list",
                               formula1=f'"{",".join(HGL_METHOD_LIST)}"',
                               allow_blank=False)
    dv_method.add("B4")
    ws.add_data_validation(dv_method)

    # Column widths
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 60
    ws.column_dimensions["E"].width = 22

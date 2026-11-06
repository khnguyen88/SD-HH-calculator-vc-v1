"""Builds the full bburg-p-c-template workbook. Called by build_bburg_template.py."""
from openpyxl import Workbook

from bburg_template_builder.sheets.config import build_config_sheet


def build_workbook() -> Workbook:
    """Construct the template workbook. Each sheet module is called in dependency order.

    Dependency order:
      1. Config (named ranges)
      2. NOAA14, Landuse_Lookup, Pipe_Properties, Kb_Values (lookup tables, no deps)
      3. IDF_Lookup (depends on NOAA14 + Config)
      4. DA_Catchments, Structures, Pipes (data tables; dropdowns reference lookups)
      5. Rationals-MCDOT (view of DA_Catchments)
      6. Inlet Spacing_10-yr, Inlet Spacing_2-yr (reads DA_Catchments)
      7. 10 Yr Pipe Capacity, 25 Yr Pipe Capacity (reads DA_Catchments + IDF_Lookup + Pipes)
      8. HGL, HGL_Example (reads everything)
    """
    wb = Workbook()
    default = wb.active
    if default is not None:
        wb.remove(default)

    build_config_sheet(wb)
    return wb

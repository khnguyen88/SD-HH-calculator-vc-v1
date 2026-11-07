# bburg-p-c.xlsx Reusable Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable PG/MoCo/DC storm-drain Excel template that computes HGL/EGL from a user-specified tailwater, supports multiple DAs per inlet via a long-table source of truth, uses VLOOKUP/SUMIFS/XLOOKUP throughout (no hard-coded cell refs), and eliminates all `#REF!` errors.

**Architecture:** Python builder script using `openpyxl` produces `docs/bburg-p-c-template.xlsx` from code. Builder is organized as a package (`drainage-calculator/bburg_template_builder/`) with one module per sheet, a shared `seed_data` module, and a `reference_calcs` module with Python implementations of hydraulic calcs (used both to seed Excel formulas and to golden-test their outputs). The current broken workbook is preserved as `docs/bburg-p-c-legacy.xlsx`.

**Tech Stack:** Python 3.11, openpyxl 3.1.5 (already installed), pytest 9.2.0 (already installed). No other new deps.

**Spec:** `docs/superpowers/specs/2026-11-06-bburg-xlsx-redesign-design.md` — read before starting.

---

## File structure

```
drainage-calculator/
├── build_bburg_template.py                       # entry script: `python drainage-calculator/build_bburg_template.py`
└── bburg_template_builder/                       # Python package
    ├── __init__.py
    ├── seed_data.py                              # NOAA14, Kb, Landuse, Pipe_Properties, Bladensburg example
    ├── reference_calcs.py                        # Python reference implementations used for golden tests
    ├── workbook.py                               # orchestrates all sheet modules
    ├── sheets/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── noaa14.py
    │   ├── idf_lookup.py
    │   ├── lookups.py                            # landuse, pipe_properties, kb_values (small tables, one module)
    │   ├── da_catchments.py
    │   ├── structures.py
    │   ├── pipes.py
    │   ├── rationals_mcdot.py
    │   ├── inlet_spacing.py                      # builds both _10-yr and _2-yr
    │   ├── pipe_capacity.py                      # builds both 10-yr and 25-yr
    │   ├── hgl.py
    │   └── hgl_example.py
    └── tests/
        ├── __init__.py
        ├── conftest.py                           # shared pytest fixtures
        ├── test_reference_calcs.py
        ├── test_config.py
        ├── test_noaa14.py
        ├── test_idf_lookup.py
        ├── test_lookups.py
        ├── test_da_catchments.py
        ├── test_structures.py
        ├── test_pipes.py
        ├── test_rationals_mcdot.py
        ├── test_inlet_spacing.py
        ├── test_pipe_capacity.py
        ├── test_hgl.py
        ├── test_hgl_example.py
        └── test_end_to_end.py

docs/
├── bburg-p-c-legacy.xlsx                         # renamed from bburg-p-c.xlsx
├── bburg-p-c-template.xlsx                       # built output
└── bburg-xlsx-user-guide.md                      # new
```

## Testing approach

- **Unit tests per sheet module** — build the sheet into a fresh `openpyxl.Workbook()`, re-read it, assert on sheet existence, Excel Table presence, named ranges, data validation sources, and **formula strings** (openpyxl does NOT evaluate formulas, so tests check the formula text, not the computed value).
- **Python reference calcs** — `reference_calcs.py` implements `interpolate_pl()`, `manning_sf_full()`, and the two-method HGL walk. Tests verify this Python reference matches hand-calculated values. The Excel formulas are designed to produce identical results when Excel evaluates them.
- **Formula-shape tests** — assert that formulas reference the correct table/column names via regex (e.g., `r"SUMIFS\(DA_Catchments\[Area_SF\], DA_Catchments\[Inlet_ID\]"`). This catches rewiring regressions.
- **Manual golden verification** (one-time, at the end) — open the built xlsx in Excel 365 and confirm: no `#REF!`, no `#NAME?`, dropdowns populated, Bladensburg example values match hand-calc.

---

## Task 0: Setup — rename legacy, package skeleton, first failing test

**Files:**
- Rename: `docs/bburg-p-c.xlsx` → `docs/bburg-p-c-legacy.xlsx`
- Create: `drainage-calculator/build_bburg_template.py`
- Create: `drainage-calculator/bburg_template_builder/__init__.py` (empty)
- Create: `drainage-calculator/bburg_template_builder/workbook.py`
- Create: `drainage-calculator/bburg_template_builder/sheets/__init__.py` (empty)
- Create: `drainage-calculator/bburg_template_builder/tests/__init__.py` (empty)
- Create: `drainage-calculator/bburg_template_builder/tests/conftest.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_end_to_end.py`

- [ ] **Step 1: Rename the legacy workbook**

```bash
git mv docs/bburg-p-c.xlsx docs/bburg-p-c-legacy.xlsx
```

- [ ] **Step 2: Create the entry script**

Create `drainage-calculator/build_bburg_template.py`:

```python
"""Entry point for the bburg-p-c template builder.

Run from repo root: `python drainage-calculator/build_bburg_template.py`
Output: docs/bburg-p-c-template.xlsx
"""
import sys
from pathlib import Path

# Make the sibling package importable when run as a script
sys.path.insert(0, str(Path(__file__).parent))

from bburg_template_builder.workbook import build_workbook

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "bburg-p-c-template.xlsx"


def main() -> None:
    wb = build_workbook()
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create the workbook orchestrator (stub)**

Create `drainage-calculator/bburg_template_builder/workbook.py`:

```python
"""Builds the full bburg-p-c-template workbook. Called by build_bburg_template.py."""
from openpyxl import Workbook


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
    # Remove default "Sheet"; sheet modules create what they need.
    default = wb.active
    if default is not None:
        wb.remove(default)
    # Sheet modules will be wired in subsequent tasks.
    return wb
```

- [ ] **Step 4: Create the pytest conftest**

Create `drainage-calculator/bburg_template_builder/tests/conftest.py`:

```python
"""Shared pytest fixtures for the template builder tests."""
import pytest
from openpyxl import Workbook


@pytest.fixture
def empty_wb() -> Workbook:
    """A fresh workbook with the default Sheet removed, ready for sheet modules to populate."""
    wb = Workbook()
    default = wb.active
    if default is not None:
        wb.remove(default)
    return wb


@pytest.fixture
def built_wb():
    """Builds the full template workbook in-memory. Use for integration tests."""
    from bburg_template_builder.workbook import build_workbook
    return build_workbook()
```

- [ ] **Step 5: Write the first failing end-to-end test**

Create `drainage-calculator/bburg_template_builder/tests/test_end_to_end.py`:

```python
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
```

- [ ] **Step 6: Run tests to confirm the end-to-end test fails on missing sheets**

Run from repo root: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_end_to_end.py -v`

Expected: `test_workbook_builds_without_errors` PASSES. `test_workbook_has_all_required_sheets` FAILS with `Missing sheets: ['Config', 'NOAA14', ...]`. `test_workbook_has_no_extra_sheets` PASSES (no legacy sheets emitted yet).

This is the "failing test" that drives the rest of the plan — each subsequent task's sheet module should remove one entry from the missing list.

- [ ] **Step 7: Commit**

```bash
git add docs/bburg-p-c-legacy.xlsx drainage-calculator/build_bburg_template.py drainage-calculator/bburg_template_builder/
git commit -m "feat(bburg-template): scaffold builder package and end-to-end test harness"
```

---

## Task 1: Seed data module + Python reference calcs

**Files:**
- Create: `drainage-calculator/bburg_template_builder/seed_data.py`
- Create: `drainage-calculator/bburg_template_builder/reference_calcs.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_reference_calcs.py`

- [ ] **Step 1: Create the seed_data module**

Create `drainage-calculator/bburg_template_builder/seed_data.py`:

```python
"""Seed data for the bburg template. All values that aren't formulas live here.

NOAA14 depths are copied verbatim from
drainage-calculator/storm-drain-design-calculator-dev.html lines 1020-1134.
If you update NOAA14 there, update here too (one authoritative source still held in HTML).
"""
from typing import Final

# --- NOAA14 Atlas depth data (inches). Only MoCo, PG, DC are seeded now. ---
# Other MD counties get blank rows (builder fills the structure; user can type values).
NOAA14_STORMS: Final[tuple[str, ...]] = ("1yr", "2yr", "5yr", "10yr", "25yr", "50yr", "100yr", "500yr")
NOAA14_DURATIONS_MIN: Final[tuple[int, ...]] = (5, 10, 15, 30, 60)  # columns d5..d60

NOAA14_SEED: Final[dict[str, dict]] = {
    "Montgomery": {
        "lat": 39.0431, "lon": -77.0532,
        "1yr":   {5: 4.16,  10: 3.33, 15: 2.78, 30: 1.90,  60: 1.19},
        "2yr":   {5: 4.99,  10: 3.99, 15: 3.34, 30: 2.31,  60: 1.45},
        "5yr":   {5: 5.94,  10: 4.76, 15: 4.01, 30: 2.85,  60: 1.83},
        "10yr":  {5: 6.64,  10: 5.31, 15: 4.48, 30: 3.24,  60: 2.11},
        "25yr":  {5: 7.51,  10: 5.99, 15: 5.06, 30: 3.75,  60: 2.50},
        "50yr":  {5: 8.17,  10: 6.51, 15: 5.49, 30: 4.14,  60: 2.80},
        "100yr": {5: 8.82,  10: 7.01, 15: 5.91, 30: 4.52,  60: 3.12},
        "500yr": {5: 10.20, 10: 8.11, 15: 6.80, 30: 5.41,  60: 3.88},
    },
    "Prince George's": {
        "lat": 38.9428, "lon": -76.9329,
        "1yr":   {5: 4.20,  10: 3.35, 15: 2.79, 30: 1.91,  60: 1.19},
        "2yr":   {5: 5.02,  10: 4.01, 15: 3.36, 30: 2.32,  60: 1.46},
        "5yr":   {5: 5.98,  10: 4.79, 15: 4.04, 30: 2.87,  60: 1.84},
        "10yr":  {5: 6.68,  10: 5.34, 15: 4.50, 30: 3.26,  60: 2.12},
        "25yr":  {5: 7.56,  10: 6.02, 15: 5.09, 30: 3.77,  60: 2.51},
        "50yr":  {5: 8.22,  10: 6.55, 15: 5.52, 30: 4.16,  60: 2.82},
        "100yr": {5: 8.87,  10: 7.04, 15: 5.94, 30: 4.54,  60: 3.13},
        "500yr": {5: 10.30, 10: 8.12, 15: 6.82, 30: 5.42,  60: 3.89},
    },
    "DC": {
        "lat": 38.9072, "lon": -77.0369,
        "1yr":   {5: 4.25,  10: 3.40, 15: 2.83, 30: 1.94,  60: 1.21},
        "2yr":   {5: 5.10,  10: 4.07, 15: 3.42, 30: 2.36,  60: 1.48},
        "5yr":   {5: 6.06,  10: 4.85, 15: 4.08, 30: 2.90,  60: 1.86},
        "10yr":  {5: 6.77,  10: 5.41, 15: 4.56, 30: 3.30,  60: 2.15},
        "25yr":  {5: 7.67,  10: 6.12, 15: 5.16, 30: 3.82,  60: 2.55},
        "50yr":  {5: 8.34,  10: 6.66, 15: 5.60, 30: 4.22,  60: 2.86},
        "100yr": {5: 9.00,  10: 7.14, 15: 6.00, 30: 4.62,  60: 3.18},
        "500yr": {5: 10.44, 10: 8.28, 15: 6.92, 30: 5.52,  60: 3.96},
    },
}

# Other MD counties shipped with blank rows (user can type NOAA14 values per project).
NOAA14_BLANK_COUNTIES: Final[tuple[str, ...]] = (
    "Allegany", "Anne Arundel", "Baltimore City", "Baltimore County",
    "Calvert", "Caroline", "Carroll", "Cecil", "Charles", "Dorchester",
    "Frederick", "Garrett", "Harford", "Howard", "Kent",
    "Queen Anne's", "Saint Mary's", "Somerset",
    "Talbot", "Washington", "Wicomico", "Worcester",
)

# --- Kb values (MCDrainage, verified against existing Kb Values MoCo sheet rows 2..92) ---
# Columns: Angle (deg), Inlet, Manhole, Bend, Junction (= Bend per MCDrainage / HTML calc mapping)
KB_VALUES: Final[tuple[tuple[int, float, float, float, float], ...]] = tuple(
    # Full table 0..90 degrees. Values 0..12 from existing xlsx inspection; 13..90
    # continue the MCDrainage curve. Engineer executing Task 5 pulls the remaining
    # values from docs/MCDrainageDesignCriteria10thRevised1Final.pdf Table (section on
    # Bend/Manhole Kb). Seed rows 0..12 below; add rows 13..90 before writing the sheet.
    (angle, inlet, manhole, bend, bend) for (angle, inlet, manhole, bend) in [
        (0,  0.50, 0.15, 0.01),
        (1,  0.51, 0.16, 0.01),
        (2,  0.52, 0.18, 0.02),
        (3,  0.53, 0.19, 0.02),
        (4,  0.54, 0.20, 0.03),
        (5,  0.54, 0.22, 0.03),
        (6,  0.55, 0.22, 0.03),
        (7,  0.56, 0.24, 0.04),
        (8,  0.57, 0.26, 0.05),
        (9,  0.58, 0.27, 0.05),
        (10, 0.59, 0.28, 0.06),
        (11, 0.60, 0.30, 0.06),
        (12, 0.61, 0.31, 0.07),
    ]
)
# NOTE for Task 5 implementer: append rows 13..90 by reading
# docs/MCDrainageDesignCriteria10thRevised1Final.pdf Appendix table before writing the sheet.
# Keep the (Angle, Inlet, Manhole, Bend, Junction) shape; Junction==Bend.

# --- Landuse_Lookup seed (MCDOT / MDOT SHA canonical set) ---
LANDUSE_SEED: Final[tuple[tuple[str, float, float, str], ...]] = (
    # (Landuse, C_2-10, C_25, Description)
    ("Impervious",      0.90, 0.95, "Paved surfaces, rooftops, concrete"),
    ("Open Space",      0.24, 0.30, "Grassed areas, lawns, soil type D"),
    ("Woods",           0.30, 0.40, "Wooded areas"),
    ("Residential",     0.50, 0.60, "Single-family residential, mixed cover"),
    ("Commercial",      0.75, 0.85, "Commercial lots, parking plus landscaping"),
    ("Industrial",      0.80, 0.90, "Industrial lots"),
    ("Pasture/Meadow",  0.30, 0.40, "Ungrazed pasture, meadow"),
    ("Cultivated",      0.35, 0.45, "Row crops"),
    ("---",             0.00, 0.00, "Placeholder (do not use)"),
)

# --- Pipe_Properties seed (preserved from existing Pipe Properties sheet rows 2..13) ---
PIPE_PROPERTIES: Final[tuple[tuple[float, float, float], ...]] = (
    # (Size_in, Area_ft2, Perimeter_ft)
    (15,     1.23,  3.93),
    (18,     1.77,  4.71),
    (21,     2.41,  5.50),
    (24,     3.14,  6.28),
    (27,     3.97,  7.07),
    (30,     4.91,  7.85),
    (33,     5.94,  8.63),
    (36,     7.07,  9.43),
    (42,     9.62, 11.00),
    (45,    11.04, 11.78),
    (48,    12.57, 12.57),
    (60,    19.63, 15.71),
)

# --- Partial-flow table (preserved from TABLES sheet, columns A..C) ---
# (y/do, A/do^2, AR^(2/3)/do^(8/3))
PARTIAL_FLOW_SEED: Final[tuple[tuple[float, float, float], ...]] = (
    (0.01, 0.0013, 0.0000),
    (0.02, 0.0037, 0.0002),
    (0.05, 0.0147, 0.0015),
    (0.10, 0.0409, 0.0065),
    (0.20, 0.1118, 0.0311),
    (0.30, 0.1982, 0.0776),
    (0.40, 0.2934, 0.1434),
    (0.50, 0.3927, 0.2219),
    (0.60, 0.4920, 0.3042),
    (0.70, 0.5872, 0.3804),
    (0.80, 0.6736, 0.4400),
    (0.90, 0.7445, 0.4620),
    (0.95, 0.7707, 0.4551),
    (1.00, 0.7854, 0.3117),
)
# NOTE: full 0.01..1.00 by 0.01 lives in the existing TABLES sheet (rows 2..101).
# Task 5 implementer copies the full list from the legacy workbook before writing.

# --- Pipe material -> Manning's n defaults ---
MATERIAL_MANNING: Final[dict[str, float]] = {
    "RCP":   0.013,
    "HDPE":  0.012,
    "CMP":   0.024,
    "PVC":   0.011,
    "DIP":   0.013,
    "Other": 0.013,
}

# --- Default seed sizes (empty row counts in the shipped template) ---
DEFAULT_ROW_COUNTS: Final[dict[str, int]] = {
    "DA_Catchments": 100,
    "Structures":    100,
    "Pipes":         200,
}

# --- Bladensburg SD-1 example data (ships pre-populated so the template opens with a working example) ---
# Keep tiny for now; Task 6/7/8 implementer may extend from the legacy workbook if useful.
BLADENSBURG_DA_CATCHMENTS: Final[tuple[dict, ...]] = (
    {"Inlet_ID": "EX-I-1", "DA_ID": "DA-1a", "Soil": "D", "Slope": "2-7%", "Landuse": "Impervious",  "Area_SF": 2209.54},
    {"Inlet_ID": "EX-I-1", "DA_ID": "DA-1b", "Soil": "D", "Slope": "2-7%", "Landuse": "Open Space",  "Area_SF":  184.74},
    {"Inlet_ID": "EX-I-2", "DA_ID": "DA-2a", "Soil": "D", "Slope": "2-7%", "Landuse": "Impervious",  "Area_SF": 45469.71},
    {"Inlet_ID": "EX-I-2", "DA_ID": "DA-2b", "Soil": "D", "Slope": "2-7%", "Landuse": "Open Space",  "Area_SF": 42247.93},
)

BLADENSBURG_STRUCTURES: Final[tuple[dict, ...]] = (
    {"Structure_ID": "EX-I-1",  "Type": "inlet",   "Description": "Existing inlet 1",  "Rim_Elev": 70.00, "Inv_In_Elev": 65.00, "Inv_Out_Elev": 64.90, "Angle_deg": 0},
    {"Structure_ID": "EX-I-2",  "Type": "inlet",   "Description": "Existing inlet 2",  "Rim_Elev": 69.00, "Inv_In_Elev": 64.00, "Inv_Out_Elev": 63.90, "Angle_deg": 0},
    {"Structure_ID": "OUTFALL", "Type": "outfall", "Description": "Free outfall",      "Rim_Elev": 65.00, "Inv_In_Elev": 60.00, "Inv_Out_Elev": 60.00, "Angle_deg": 0},
)

BLADENSBURG_PIPES: Final[tuple[dict, ...]] = (
    {"Pipe_ID": "P-1", "From_Structure": "EX-I-1", "To_Structure": "EX-I-2",  "Length_ft": 100, "Size_in": 15, "Material": "RCP", "Slope_ftft": 0.009},
    {"Pipe_ID": "P-2", "From_Structure": "EX-I-2", "To_Structure": "OUTFALL", "Length_ft":  80, "Size_in": 18, "Material": "RCP", "Slope_ftft": 0.049},
)
```

- [ ] **Step 2: Create the reference_calcs module**

Create `drainage-calculator/bburg_template_builder/reference_calcs.py`:

```python
"""Python reference implementations of hydraulic calcs used by the template.

Purpose: these functions compute the same quantities that the Excel formulas on
IDF_Lookup, Pipe Capacity, and HGL sheets compute. Tests verify this Python
reference against hand-calculated values; the Excel formulas are designed to
produce identical results when Excel evaluates them.

If Excel vs reference values diverge on any sheet, one of them has a bug.
"""
from __future__ import annotations
import math
from typing import Literal


GRAVITY_FT_S2 = 32.2


def interpolate_pl(
    tc_min: float,
    depths_by_duration_min: dict[int, float],
) -> float:
    """Power-law interpolate a rainfall intensity (in/hr) from NOAA14 depths.

    Mirrors the HTML calculator's interpolatePL() function (dev HTML line 1178+).
    Given point depths at durations {5, 10, 15, 30, 60} min, fit i = 60*a*t^(b-1)
    between the two bracketing durations, where t is in minutes.
    """
    durations = sorted(depths_by_duration_min.keys())
    if tc_min <= durations[0]:
        d = depths_by_duration_min[durations[0]]
        return 60.0 * d / durations[0]
    if tc_min >= durations[-1]:
        d = depths_by_duration_min[durations[-1]]
        return 60.0 * d / durations[-1]
    # Find bracketing durations
    t_lo, t_hi = durations[0], durations[1]
    for i in range(len(durations) - 1):
        if durations[i] <= tc_min <= durations[i + 1]:
            t_lo, t_hi = durations[i], durations[i + 1]
            break
    d_lo = depths_by_duration_min[t_lo]
    d_hi = depths_by_duration_min[t_hi]
    # Power-law fit: d = a * t^b, so b = ln(d_hi/d_lo) / ln(t_hi/t_lo), a = d_lo / t_lo^b
    b = math.log(d_hi / d_lo) / math.log(t_hi / t_lo)
    a = d_lo / (t_lo ** b)
    depth_at_tc = a * (tc_min ** b)
    return 60.0 * depth_at_tc / tc_min


def manning_sf_full(q_cfs: float, n: float, diameter_in: float) -> float:
    """Full-flow Manning's friction slope for a circular pipe (ft/ft).

    Sf = (Q * n / (1.486 * A_full * R_full^(2/3)))^2
    with A_full = pi/4 * (D/12)^2 and R_full = D/48.
    """
    d_ft = diameter_in / 12.0
    area_full = math.pi * d_ft ** 2 / 4.0
    r_full = d_ft / 4.0
    conveyance = 1.486 * area_full * (r_full ** (2.0 / 3.0))
    return (q_cfs * n / conveyance) ** 2


def velocity_head(v_fps: float) -> float:
    """V^2 / (2g)."""
    return v_fps ** 2 / (2.0 * GRAVITY_FT_S2)


HglMethod = Literal["hec22", "legacy"]


def hgl_walk_step(
    hgl_dn_raw: float,
    crown_dn: float,
    crown_up: float,
    hf: float,
    method: HglMethod,
) -> tuple[float, float]:
    """Compute (HGL_dn_final, HGL_up_final) for a single pipe step.

    HEC-22: HGL_dn = max(HGL_dn_raw, Crown_dn); HGL_up = HGL_dn + Hf (no u/s floor).
    Legacy: HGL_dn = max(HGL_dn_raw, Crown_dn); HGL_up = max(HGL_dn + Hf, Crown_up).
    """
    hgl_dn = max(hgl_dn_raw, crown_dn)
    hgl_up_raw = hgl_dn + hf
    if method == "legacy":
        hgl_up = max(hgl_up_raw, crown_up)
    else:
        hgl_up = hgl_up_raw
    return hgl_dn, hgl_up
```

- [ ] **Step 3: Write failing tests for reference_calcs**

Create `drainage-calculator/bburg_template_builder/tests/test_reference_calcs.py`:

```python
import math
import pytest
from bburg_template_builder.reference_calcs import (
    interpolate_pl, manning_sf_full, velocity_head, hgl_walk_step
)
from bburg_template_builder.seed_data import NOAA14_SEED


class TestInterpolatePL:
    def test_endpoint_5_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=5 min, i = 60 * 6.64 / 5 = 79.68 in/hr
        assert interpolate_pl(5.0, depths) == pytest.approx(79.68, rel=1e-3)

    def test_endpoint_60_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=60 min, i = 60 * 2.11 / 60 = 2.11 in/hr
        assert interpolate_pl(60.0, depths) == pytest.approx(2.11, rel=1e-3)

    def test_mid_10_min_montgomery_10yr(self):
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        # At Tc=10 min exactly, intensity = 60*5.31/10 = 31.86 in/hr (uses 5-10 bracket, t=10)
        assert interpolate_pl(10.0, depths) == pytest.approx(31.86, rel=1e-3)

    def test_mid_7_min_montgomery_10yr(self):
        # Power-law between 5min (6.64 in) and 10min (5.31 in):
        # b = ln(5.31/6.64)/ln(10/5) = -0.322; a = 6.64/5^b = 6.64*5^0.322 = 11.07
        # At Tc=7: depth = 11.07 * 7^(-0.322) = 6.115 in; i = 60*6.115/7 = 52.42 in/hr
        depths = {d: NOAA14_SEED["Montgomery"]["10yr"][d] for d in (5, 10, 15, 30, 60)}
        assert interpolate_pl(7.0, depths) == pytest.approx(52.42, rel=5e-3)


class TestManningSfFull:
    def test_24in_rcp_9p5_cfs(self):
        # D=24in -> d_ft=2, A=pi*1 = 3.1416, R=0.5
        # conveyance = 1.486 * 3.1416 * 0.5^(2/3) = 1.486 * 3.1416 * 0.6300 = 2.942
        # Sf = (9.5*0.013/2.942)^2 = (0.04197)^2 = 0.00176
        assert manning_sf_full(9.5, 0.013, 24) == pytest.approx(0.00176, rel=1e-2)

    def test_zero_q_gives_zero_sf(self):
        assert manning_sf_full(0.0, 0.013, 24) == 0.0


class TestVelocityHead:
    def test_known_value(self):
        # V=3 fps -> Vh = 9/64.4 = 0.1398
        assert velocity_head(3.0) == pytest.approx(0.1398, rel=1e-3)


class TestHglWalkStep:
    def test_hec22_pressurized(self):
        # HGL_dn_raw=97, Crown_dn=96, Crown_up=96.5, Hf=0.142
        # HGL_dn = max(97, 96) = 97; HGL_up = 97 + 0.142 = 97.142 (no u/s floor)
        hgl_dn, hgl_up = hgl_walk_step(97.0, 96.0, 96.5, 0.142, "hec22")
        assert hgl_dn == pytest.approx(97.0, abs=1e-4)
        assert hgl_up == pytest.approx(97.142, abs=1e-4)

    def test_hec22_gravity_ds_crown_floor(self):
        # HGL_dn_raw=93 (below crown 96), Hf=0.05
        # HGL_dn = max(93, 96) = 96; HGL_up = 96 + 0.05 = 96.05 (no u/s floor)
        hgl_dn, hgl_up = hgl_walk_step(93.0, 96.0, 97.0, 0.05, "hec22")
        assert hgl_dn == pytest.approx(96.0, abs=1e-4)
        assert hgl_up == pytest.approx(96.05, abs=1e-4)

    def test_legacy_gravity_both_ends_crown_floor(self):
        # Same inputs as above, but Legacy pins HGL_up at Crown_up=97.0 (since 96.05 < 97.0)
        hgl_dn, hgl_up = hgl_walk_step(93.0, 96.0, 97.0, 0.05, "legacy")
        assert hgl_dn == pytest.approx(96.0, abs=1e-4)
        assert hgl_up == pytest.approx(97.0, abs=1e-4)

    def test_methods_agree_when_pressurized(self):
        a = hgl_walk_step(100.0, 96.0, 96.5, 0.2, "hec22")
        b = hgl_walk_step(100.0, 96.0, 96.5, 0.2, "legacy")
        assert a == b
```

- [ ] **Step 4: Run tests to verify reference_calcs passes**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_reference_calcs.py -v`

Expected: all tests PASS. If any fail, fix `reference_calcs.py` before continuing — these functions are the golden-truth for every subsequent task.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/seed_data.py \
        drainage-calculator/bburg_template_builder/reference_calcs.py \
        drainage-calculator/bburg_template_builder/tests/test_reference_calcs.py
git commit -m "feat(bburg-template): seed data and Python reference hydraulic calcs"
```

---

## Task 2: Config sheet with named ranges

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/config.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_config.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py` (wire it in)

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_config.py`:

```python
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
    # DefinedName.attr_text is the "Config!$B$3" style ref; read the cell value.
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
    attr = dn.attr_text  # e.g. "Config!$B$3"
    sheet_part, coord = attr.split("!")
    sheet = sheet_part.strip("'")
    coord = coord.replace("$", "")
    return sheet, coord
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: bburg_template_builder.sheets.config`.

- [ ] **Step 2: Create the config sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/config.py`:

```python
"""Config sheet — scalar inputs that drive the workbook via named ranges."""
from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


# (name, default_value, note). Values live on Config!$B$<row>, names on $A$<row>.
CONFIG_ROWS: tuple[tuple[str, object, str], ...] = (
    ("County_Selected",    "Prince George's",                 "Dropdown: NOAA14[County]"),
    ("Storm_Primary",      "10yr",                             "Dropdown: 1yr/2yr/5yr/10yr/25yr/50yr/100yr/500yr"),
    ("HGL_Method",         "HEC-22 EGL (d/s crown floor)",    "HEC-22 (default) or Legacy both-end crown floor"),
    ("Project_Name",       "",                                 ""),
    ("Project_Number",     "",                                 ""),
    ("Designer",           "",                                 ""),
    ("Checker",            "",                                 ""),
    ("Date_Computed",      "",                                 ""),
    ("Manning_n_RCP",      0.013,                              "Manning's n for RCP (default)"),
    ("Manning_n_HDPE",     0.012,                              "Manning's n for HDPE (default)"),
    ("Gravity_g",          32.2,                               "ft/s^2"),
    ("Rim_Freeboard",      1.0,                                "ft (HGL check: HGL < Rim - freeboard)"),
    ("Crown_Freeboard",    1.0,                                "ft (HGL check: HGL < Crown + freeboard)"),
)

STORM_LIST = ("1yr", "2yr", "5yr", "10yr", "25yr", "50yr", "100yr", "500yr")
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

        # Define a workbook-scoped named range pointing to the value cell.
        ref = f"Config!$B${row}"
        wb.defined_names[name] = DefinedName(name=name, attr_text=ref)

    # Data validation dropdowns for the three dropdown fields.
    # County_Selected (row 2): sourced from NOAA14[County] once NOAA14 is built; use named range later.
    # We seed with a static list for now; Task 3 (NOAA14) replaces with table-column reference.
    dv_county = DataValidation(type="list",
                               formula1='"Montgomery,Prince George\'s,DC"',
                               allow_blank=False)
    dv_county.add("B2")
    ws.add_data_validation(dv_county)

    dv_storm = DataValidation(type="list",
                              formula1=f'"{",".join(STORM_LIST)}"',
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
```

- [ ] **Step 3: Wire into workbook.py**

Modify `drainage-calculator/bburg_template_builder/workbook.py`:

```python
"""Builds the full bburg-p-c-template workbook. Called by build_bburg_template.py."""
from openpyxl import Workbook

from bburg_template_builder.sheets.config import build_config_sheet


def build_workbook() -> Workbook:
    wb = Workbook()
    default = wb.active
    if default is not None:
        wb.remove(default)

    build_config_sheet(wb)
    return wb
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_config.py drainage-calculator/bburg_template_builder/tests/test_end_to_end.py -v`

Expected: `test_config.py` all PASS. `test_end_to_end::test_workbook_has_all_required_sheets` still FAILS but the missing list is one shorter.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/config.py \
        drainage-calculator/bburg_template_builder/tests/test_config.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Config sheet with named ranges and dropdowns"
```

---

## Task 3: NOAA14 sheet (Excel Table with MoCo/PG/DC seeded)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/noaa14.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_noaa14.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`
- Modify: `drainage-calculator/bburg_template_builder/sheets/config.py` (point County dropdown at NOAA14 column)

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_noaa14.py`:

```python
import pytest
from bburg_template_builder.sheets.noaa14 import build_noaa14_sheet
from bburg_template_builder.seed_data import NOAA14_SEED, NOAA14_BLANK_COUNTIES, NOAA14_STORMS


EXPECTED_COLUMNS = ["County", "lat", "lon", "Storm", "d5", "d10", "d15", "d30", "d60"]


def test_noaa14_sheet_created(empty_wb):
    build_noaa14_sheet(empty_wb)
    assert "NOAA14" in empty_wb.sheetnames


def test_headers_present(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(EXPECTED_COLUMNS) + 1)]
    assert actual == EXPECTED_COLUMNS


def test_one_row_per_county_per_storm(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    counties = len(NOAA14_SEED) + len(NOAA14_BLANK_COUNTIES)
    storms = len(NOAA14_STORMS)
    expected_data_rows = counties * storms
    # Row 1 is header; data starts row 2.
    last_row_with_county = max(
        r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value
    )
    assert last_row_with_county - 1 == expected_data_rows


def test_table_registered(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    assert "NOAA14" in ws.tables, f"Tables on sheet: {list(ws.tables.keys())}"


def test_montgomery_10yr_values_match_seed(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    # Find the Montgomery / 10yr row
    seed = NOAA14_SEED["Montgomery"]["10yr"]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "Montgomery" and ws.cell(row=r, column=4).value == "10yr":
            assert ws.cell(row=r, column=5).value == seed[5]   # d5
            assert ws.cell(row=r, column=6).value == seed[10]  # d10
            assert ws.cell(row=r, column=7).value == seed[15]  # d15
            assert ws.cell(row=r, column=8).value == seed[30]  # d30
            assert ws.cell(row=r, column=9).value == seed[60]  # d60
            return
    pytest.fail("Montgomery / 10yr row not found")


def test_blank_counties_have_blank_depths(empty_wb):
    build_noaa14_sheet(empty_wb)
    ws = empty_wb["NOAA14"]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "Allegany":
            # Depth columns (5..9) should be None / blank
            for c in range(5, 10):
                assert ws.cell(row=r, column=c).value in (None, "")
            return
    pytest.fail("Allegany (a blank county) row not found")
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_noaa14.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 2: Create the NOAA14 sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/noaa14.py`:

```python
"""NOAA14 sheet - Atlas 14 depth table for all MD counties + DC."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import (
    NOAA14_SEED, NOAA14_BLANK_COUNTIES, NOAA14_STORMS, NOAA14_DURATIONS_MIN,
)


def build_noaa14_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("NOAA14")

    headers = ["County", "lat", "lon", "Storm"] + [f"d{d}" for d in NOAA14_DURATIONS_MIN]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)

    row = 2
    # Seeded counties
    for county, data in NOAA14_SEED.items():
        for storm in NOAA14_STORMS:
            ws.cell(row=row, column=1, value=county)
            ws.cell(row=row, column=2, value=data["lat"])
            ws.cell(row=row, column=3, value=data["lon"])
            ws.cell(row=row, column=4, value=storm)
            depths = data[storm]
            for i, d in enumerate(NOAA14_DURATIONS_MIN):
                ws.cell(row=row, column=5 + i, value=depths[d])
            row += 1

    # Blank counties (county name + storm name, no depths)
    for county in NOAA14_BLANK_COUNTIES:
        for storm in NOAA14_STORMS:
            ws.cell(row=row, column=1, value=county)
            ws.cell(row=row, column=4, value=storm)
            row += 1

    last_row = row - 1
    last_col_letter = chr(ord("A") + len(headers) - 1)
    table_ref = f"A1:{last_col_letter}{last_row}"
    table = Table(displayName="NOAA14", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True,
    )
    ws.add_table(table)

    # Column widths
    ws.column_dimensions["A"].width = 20
    for col in ("B", "C", "D"):
        ws.column_dimensions[col].width = 10
    for col in ("E", "F", "G", "H", "I"):
        ws.column_dimensions[col].width = 8
```

- [ ] **Step 3: Update workbook.py to call it**

Modify `drainage-calculator/bburg_template_builder/workbook.py` — add import and call:

```python
from bburg_template_builder.sheets.noaa14 import build_noaa14_sheet
# ... after build_config_sheet(wb):
build_noaa14_sheet(wb)
```

- [ ] **Step 4: Update Config's County dropdown to source from NOAA14 table**

Modify `drainage-calculator/bburg_template_builder/sheets/config.py` — replace the static county dropdown with one sourced from the NOAA14 table. Change the block:

```python
dv_county = DataValidation(type="list",
                           formula1='"Montgomery,Prince George\'s,DC"',
                           allow_blank=False)
```

to:

```python
# County dropdown sources from the NOAA14[County] column via INDIRECT.
# Unique counties are reproduced in a helper range Config!E2:E27; dropdown points there.
_counties_for_dropdown = ["Montgomery", "Prince George's", "DC"] + [
    c for c in __import__("bburg_template_builder.seed_data", fromlist=["NOAA14_BLANK_COUNTIES"]).NOAA14_BLANK_COUNTIES
]
for i, c in enumerate(_counties_for_dropdown):
    ws.cell(row=2 + i, column=5, value=c)
dv_county = DataValidation(type="list",
                           formula1=f"=Config!$E$2:$E${1 + len(_counties_for_dropdown)}",
                           allow_blank=False)
```

(This keeps the dropdown driven by a visible range on the Config sheet. Hiding column E behind print-area / column_dimensions.hidden is optional; leave visible for template inspectability.)

- [ ] **Step 5: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_noaa14.py drainage-calculator/bburg_template_builder/tests/test_config.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/noaa14.py \
        drainage-calculator/bburg_template_builder/tests/test_noaa14.py \
        drainage-calculator/bburg_template_builder/workbook.py \
        drainage-calculator/bburg_template_builder/sheets/config.py
git commit -m "feat(bburg-template): NOAA14 Excel Table; wire County dropdown to county list"
```

---

## Task 4: IDF_Lookup sheet with power-law interpolation

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/idf_lookup.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_idf_lookup.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_idf_lookup.py`:

```python
import re
import pytest
from bburg_template_builder.sheets.idf_lookup import build_idf_lookup_sheet


def test_idf_sheet_created(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    assert "IDF_Lookup" in empty_wb.sheetnames


def test_tc_column_5_to_60_at_0p1_increments(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    # Headers row 1; Tc values start row 2. 5.0 -> 60.0 at 0.1 increments = 551 rows.
    assert ws.cell(row=2, column=1).value == 5.0
    assert ws.cell(row=552, column=1).value == pytest.approx(60.0, abs=1e-6)


def test_headers(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    expected = ["Tc_min", "i_1yr", "i_2yr", "i_5yr", "i_10yr", "i_25yr", "i_50yr", "i_100yr", "i_500yr"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_table_registered(empty_wb):
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    assert "IDF_Lookup" in ws.tables


def test_formula_uses_county_selected_and_noaa14(empty_wb):
    """The intensity formula must dereference County_Selected and lookup NOAA14 depths."""
    build_idf_lookup_sheet(empty_wb)
    ws = empty_wb["IDF_Lookup"]
    # Check a mid-row (not an exact-duration boundary): row for Tc = 7.0 min
    # Row = 2 + (7.0 - 5.0) / 0.1 = 2 + 20 = 22
    formula = ws.cell(row=22, column=5).value  # i_10yr column
    assert formula.startswith("=") or formula.startswith("=_xlfn.")
    assert "County_Selected" in formula
    assert "NOAA14" in formula
    assert "10yr" in formula
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_idf_lookup.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 2: Create the IDF_Lookup sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/idf_lookup.py`:

```python
"""IDF_Lookup sheet - computes rainfall intensity at any Tc via power-law interp of NOAA14.

Formula model (per spec §5.3): for a given (County_Selected, storm, Tc), find the two
bracketing durations in {5,10,15,30,60} min, fit i = 60*a*t^(b-1) between them,
and return intensity at Tc.

We implement this as a per-cell formula using SUMPRODUCT/XLOOKUP to pull the NOAA14 depth
for (county, storm, duration). Tc values in column A are fixed (5.0 to 60.0 by 0.1).
"""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import NOAA14_STORMS, NOAA14_DURATIONS_MIN


# Durations (min) for which NOAA14 has explicit depths. Must be sorted ascending.
DURATIONS = list(NOAA14_DURATIONS_MIN)  # [5, 10, 15, 30, 60]


def _depth_lookup_formula(county_ref: str, storm_literal: str, duration: int) -> str:
    """Return the SUMIFS-based formula for NOAA14 depth lookup at (county, storm, duration)."""
    depth_col = f"d{duration}"
    return (
        f'SUMIFS(NOAA14[{depth_col}],'
        f'NOAA14[County],{county_ref},'
        f'NOAA14[Storm],"{storm_literal}")'
    )


def _intensity_formula_for_tc_cell(tc_cell_ref: str, storm: str) -> str:
    """Build the intensity formula for a specific Tc cell and storm.

    Uses nested IFS to pick the correct bracketing duration pair:
      Tc <= 5:       i = 60 * d5 / 5
      5 < Tc <= 10:  fit (5, d5)-(10, d10) at Tc
      10 < Tc <= 15: fit (10, d10)-(15, d15) at Tc
      15 < Tc <= 30: fit (15, d15)-(30, d30) at Tc
      30 < Tc <= 60: fit (30, d30)-(60, d60) at Tc
      Tc > 60:       i = 60 * d60 / 60 = d60 (extrapolated flat)

    Power-law fit between (t_lo, d_lo) and (t_hi, d_hi) at Tc:
      b = LN(d_hi/d_lo) / LN(t_hi/t_lo)
      a = d_lo / t_lo^b
      depth(Tc) = a * Tc^b
      i = 60 * depth(Tc) / Tc
    """
    county = "County_Selected"
    # Pre-compute the five depth lookups as inline formula fragments.
    d_lookups = {d: _depth_lookup_formula(county, storm, d) for d in DURATIONS}

    def pl_i(t_lo, t_hi):
        """Power-law intensity between duration t_lo and t_hi, evaluated at Tc."""
        d_lo_frag = d_lookups[t_lo]
        d_hi_frag = d_lookups[t_hi]
        # 60 * d_lo * (Tc / t_lo) ^ b, where b = LN(d_hi/d_lo)/LN(t_hi/t_lo)
        # Simplified: i = 60/Tc * d_lo * (Tc/t_lo)^b
        b_expr = f"LN(({d_hi_frag})/({d_lo_frag}))/LN({t_hi}/{t_lo})"
        depth_tc = f"({d_lo_frag})*({tc_cell_ref}/{t_lo})^({b_expr})"
        return f"60*({depth_tc})/{tc_cell_ref}"

    # Endpoints
    i_at_or_below_5 = f"60*({d_lookups[5]})/5"
    i_above_60 = d_lookups[60]  # flat extrapolation

    # IFS to pick the right bracket
    return (
        f"=IFS("
        f"{tc_cell_ref}<=5,{i_at_or_below_5},"
        f"{tc_cell_ref}<=10,{pl_i(5, 10)},"
        f"{tc_cell_ref}<=15,{pl_i(10, 15)},"
        f"{tc_cell_ref}<=30,{pl_i(15, 30)},"
        f"{tc_cell_ref}<=60,{pl_i(30, 60)},"
        f"TRUE,{i_above_60}"
        f")"
    )


def build_idf_lookup_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("IDF_Lookup")

    headers = ["Tc_min"] + [f"i_{s}" for s in NOAA14_STORMS]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)

    # Tc from 5.0 to 60.0 inclusive at 0.1 increments => 551 rows
    tc_values = [round(5.0 + 0.1 * i, 1) for i in range(0, 551)]
    for i, tc in enumerate(tc_values):
        row = 2 + i
        ws.cell(row=row, column=1, value=tc)
        tc_cell_ref = f"$A{row}"
        for c, storm in enumerate(NOAA14_STORMS, start=2):
            ws.cell(row=row, column=c, value=_intensity_formula_for_tc_cell(tc_cell_ref, storm))

    last_col_letter = chr(ord("A") + len(headers) - 1)
    table_ref = f"A1:{last_col_letter}{1 + len(tc_values)}"
    table = Table(displayName="IDF_Lookup", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    ws.column_dimensions["A"].width = 10
    for i in range(2, len(headers) + 1):
        col_letter = chr(ord("A") + i - 1)
        ws.column_dimensions[col_letter].width = 10
```

- [ ] **Step 3: Wire into workbook.py**

Modify `drainage-calculator/bburg_template_builder/workbook.py`:

```python
from bburg_template_builder.sheets.idf_lookup import build_idf_lookup_sheet
# ... after build_noaa14_sheet(wb):
build_idf_lookup_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_idf_lookup.py -v`

Expected: all PASS.

- [ ] **Step 5: Manual Excel check (first time; takes 60 seconds)**

Run: `python drainage-calculator/build_bburg_template.py`
Open `docs/bburg-p-c-template.xlsx` in Excel 365. Navigate to IDF_Lookup. At Tc=5.0 (row 2), i_10yr should show ≈ **79.68 in/hr** (Prince George's 10-yr at 5 min is 6.68 in; `60 * 6.68 / 5 = 80.16`). Wait — default county is Prince George's (6.68 at 5 min) so the expected value is `80.16`.

Cross-check against `reference_calcs.interpolate_pl` for PG 10-yr at Tc=5: should equal 80.16. If Excel shows a different number, inspect the formula and compare against the fragment in `_intensity_formula_for_tc_cell`.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/idf_lookup.py \
        drainage-calculator/bburg_template_builder/tests/test_idf_lookup.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): IDF_Lookup sheet with power-law Tc interpolation"
```

---

## Task 5: Landuse_Lookup, Pipe_Properties, Kb_Values (three small lookup tables)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/lookups.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_lookups.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`
- Modify: `drainage-calculator/bburg_template_builder/seed_data.py` — expand `KB_VALUES` rows 13..90 from MCDrainage PDF

- [ ] **Step 1: Expand KB_VALUES in seed_data.py from the legacy workbook**

The legacy `Kb Values MoCo` sheet holds angles 0..90 with (Inlet, Manhole, Bend) values. Extract them with this snippet and paste the output into `seed_data.py`:

```bash
python -c "
import openpyxl
wb = openpyxl.load_workbook('docs/bburg-p-c-legacy.xlsx', data_only=True)
ws = wb['Kb Values MoCo']
print('KB_VALUES = (')
for r in range(2, ws.max_row + 1):
    angle = ws.cell(row=r, column=1).value
    inlet = ws.cell(row=r, column=2).value
    manhole = ws.cell(row=r, column=3).value
    bend = ws.cell(row=r, column=4).value
    if angle is None:
        continue
    # Junction column = Bend per MCDrainage / HTML calc mapping (spec §5.9)
    print(f'    ({angle}, {inlet}, {manhole}, {bend}, {bend}),')
print(')')
"
```

Open `drainage-calculator/bburg_template_builder/seed_data.py` and replace the short 13-row `KB_VALUES` placeholder with the full output of the snippet above (keep the `Final[tuple[tuple[int, float, float, float, float], ...]]` type annotation). Each tuple is `(Angle, Inlet, Manhole, Bend, Junction)` with `Junction == Bend`.

Spot-check against the MCDrainage PDF (`docs/MCDrainageDesignCriteria10thRevised1Final.pdf`) for 2-3 rows — if any legacy value disagrees with the PDF, trust the PDF and open a follow-up ticket.

- [ ] **Step 2: Write the failing tests**

Create `drainage-calculator/bburg_template_builder/tests/test_lookups.py`:

```python
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
    # Each landuse row present
    landuses = [ws.cell(row=r, column=1).value for r in range(2, 2 + len(LANDUSE_SEED))]
    assert landuses == [l[0] for l in LANDUSE_SEED]


def test_pipe_properties_sheet_created(empty_wb):
    build_pipe_properties_sheet(empty_wb)
    assert "Pipe_Properties" in empty_wb.sheetnames
    ws = empty_wb["Pipe_Properties"]
    assert "Pipe_Properties" in ws.tables
    # Size column has 12 entries
    sizes = [ws.cell(row=r, column=1).value for r in range(2, 2 + len(PIPE_PROPERTIES))]
    assert sizes == [p[0] for p in PIPE_PROPERTIES]


def test_pipe_properties_hyd_radius_is_formula(empty_wb):
    build_pipe_properties_sheet(empty_wb)
    ws = empty_wb["Pipe_Properties"]
    # Hyd Radius = Area / Perimeter; must be a formula (not a baked number)
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
    # Spec §5.9: Junction column = Bend column (MCDrainage mapping)
    for r in range(2, 2 + len(KB_VALUES)):
        bend_val = ws.cell(row=r, column=4).value
        junction_val = ws.cell(row=r, column=5).value
        assert bend_val == junction_val, f"Row {r}: Bend={bend_val} but Junction={junction_val}"
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_lookups.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the lookups module**

Create `drainage-calculator/bburg_template_builder/sheets/lookups.py`:

```python
"""Small lookup tables: Landuse_Lookup, Pipe_Properties, Kb_Values."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from bburg_template_builder.seed_data import (
    LANDUSE_SEED, PIPE_PROPERTIES, KB_VALUES, PARTIAL_FLOW_SEED,
)


def _add_table(ws, name: str, ref: str) -> None:
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)


def build_landuse_lookup_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Landuse_Lookup")
    headers = ["Landuse", "C_2-10", "C_25", "Description"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (landuse, c_2_10, c_25, desc) in enumerate(LANDUSE_SEED):
        row = 2 + i
        ws.cell(row=row, column=1, value=landuse)
        ws.cell(row=row, column=2, value=c_2_10)
        ws.cell(row=row, column=3, value=c_25)
        ws.cell(row=row, column=4, value=desc)
    last_row = 1 + len(LANDUSE_SEED)
    _add_table(ws, "Landuse_Lookup", f"A1:D{last_row}")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 42


def build_pipe_properties_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Pipe_Properties")
    headers = ["Size", "Area", "Perimeter", "Hyd Radius"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (size, area, perim) in enumerate(PIPE_PROPERTIES):
        row = 2 + i
        ws.cell(row=row, column=1, value=size)
        ws.cell(row=row, column=2, value=area)
        ws.cell(row=row, column=3, value=perim)
        ws.cell(row=row, column=4, value=f"=B{row}/C{row}")  # Hyd Radius = Area / Perimeter
    last_row = 1 + len(PIPE_PROPERTIES)
    _add_table(ws, "Pipe_Properties", f"A1:D{last_row}")
    for col in ("A", "B", "C", "D"):
        ws.column_dimensions[col].width = 11

    # PartialFlow table below Pipe_Properties with a 2-row gap
    pf_start = last_row + 3
    ws.cell(row=pf_start, column=1, value="y_over_do")
    ws.cell(row=pf_start, column=2, value="A_over_do2")
    ws.cell(row=pf_start, column=3, value="AR23_over_do83")
    for i, (y, a, ar) in enumerate(PARTIAL_FLOW_SEED):
        row = pf_start + 1 + i
        ws.cell(row=row, column=1, value=y)
        ws.cell(row=row, column=2, value=a)
        ws.cell(row=row, column=3, value=ar)
    pf_last_row = pf_start + len(PARTIAL_FLOW_SEED)
    _add_table(ws, "PartialFlow", f"A{pf_start}:C{pf_last_row}")


def build_kb_values_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Kb_Values")
    headers = ["Angle", "Inlet", "Manhole", "Bend", "Junction"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for i, (angle, inlet, manhole, bend, junction) in enumerate(KB_VALUES):
        row = 2 + i
        ws.cell(row=row, column=1, value=angle)
        ws.cell(row=row, column=2, value=inlet)
        ws.cell(row=row, column=3, value=manhole)
        ws.cell(row=row, column=4, value=bend)
        ws.cell(row=row, column=5, value=junction)
    last_row = 1 + len(KB_VALUES)
    _add_table(ws, "Kb_Values", f"A1:E{last_row}")
    for col in ("A", "B", "C", "D", "E"):
        ws.column_dimensions[col].width = 10
```

- [ ] **Step 4: Wire into workbook.py**

Modify `drainage-calculator/bburg_template_builder/workbook.py`:

```python
from bburg_template_builder.sheets.lookups import (
    build_landuse_lookup_sheet, build_pipe_properties_sheet, build_kb_values_sheet,
)
# ... after build_idf_lookup_sheet(wb):
build_landuse_lookup_sheet(wb)
build_pipe_properties_sheet(wb)
build_kb_values_sheet(wb)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_lookups.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/seed_data.py \
        drainage-calculator/bburg_template_builder/sheets/lookups.py \
        drainage-calculator/bburg_template_builder/tests/test_lookups.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Landuse_Lookup, Pipe_Properties, Kb_Values lookup tables"
```

---

## Task 6: DA_Catchments table (long-form source of truth, 100 default rows + Bladensburg seed)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/da_catchments.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_da_catchments.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_da_catchments.py`:

```python
import pytest
from bburg_template_builder.sheets.da_catchments import build_da_catchments_sheet
from bburg_template_builder.seed_data import BLADENSBURG_DA_CATCHMENTS, DEFAULT_ROW_COUNTS


def test_sheet_created(empty_wb):
    build_da_catchments_sheet(empty_wb)
    assert "DA_Catchments" in empty_wb.sheetnames


def test_headers(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    expected = ["Inlet_ID", "DA_ID", "Soil", "Slope", "Landuse",
                "Area_SF", "C_2-10", "C_25", "Notes"]
    actual = [ws.cell(row=1, column=c).value for c in range(1, len(expected) + 1)]
    assert actual == expected


def test_default_row_count(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    # Table ref spans 100 data rows; seed Bladensburg rows go at the top,
    # remainder are empty. Total data rows = max(100, len(seed)).
    expected_data_rows = max(DEFAULT_ROW_COUNTS["DA_Catchments"], len(BLADENSBURG_DA_CATCHMENTS))
    table = ws.tables["DA_Catchments"]
    # Parse ref like "A1:I101"
    end_cell = table.ref.split(":")[1]
    import re
    match = re.match(r"([A-Z]+)(\d+)", end_cell)
    assert match
    last_row = int(match.group(2))
    assert last_row - 1 == expected_data_rows


def test_bladensburg_seed_at_top(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    for i, seed in enumerate(BLADENSBURG_DA_CATCHMENTS):
        row = 2 + i
        assert ws.cell(row=row, column=1).value == seed["Inlet_ID"]
        assert ws.cell(row=row, column=2).value == seed["DA_ID"]
        assert ws.cell(row=row, column=6).value == seed["Area_SF"]


def test_c_values_are_xlookup_formulas(empty_wb):
    """C_2-10 and C_25 must XLOOKUP into Landuse_Lookup by default, with user override allowed."""
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    # First data row
    c_2_10_formula = ws.cell(row=2, column=7).value
    c_25_formula = ws.cell(row=2, column=8).value
    assert "Landuse_Lookup" in str(c_2_10_formula)
    assert "Landuse_Lookup" in str(c_25_formula)


def test_soil_dropdown_present(empty_wb):
    build_da_catchments_sheet(empty_wb)
    ws = empty_wb["DA_Catchments"]
    # Soil column is column C; data validation should be registered
    soil_dvs = [dv for dv in ws.data_validations.dataValidation
                if any("C" in rng.coord.split(":")[0] for rng in dv.sqref.ranges)]
    assert soil_dvs, "No data validation found on Soil column (C)"
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_da_catchments.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 2: Create the DA_Catchments sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/da_catchments.py`:

```python
"""DA_Catchments sheet - long-form source of truth for Rational Method.

One row per (Inlet_ID, DA_ID, Soil, Slope, Landuse, Area). Inlets with N drainage
subareas appear as N rows with the same Inlet_ID. Downstream sheets read via
SUMIFS/SUMPRODUCT by Inlet_ID - never by hard-coded cell address.
"""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import (
    BLADENSBURG_DA_CATCHMENTS, DEFAULT_ROW_COUNTS, LANDUSE_SEED,
)


HEADERS = ["Inlet_ID", "DA_ID", "Soil", "Slope", "Landuse",
           "Area_SF", "C_2-10", "C_25", "Notes"]

SOIL_LIST = ("A", "B", "C", "D", "---")
SLOPE_LIST = ("0-2%", "2-7%", "7%+", "---")


def build_da_catchments_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("DA_Catchments")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    # Write Bladensburg seed rows first
    for i, seed in enumerate(BLADENSBURG_DA_CATCHMENTS):
        row = 2 + i
        ws.cell(row=row, column=1, value=seed["Inlet_ID"])
        ws.cell(row=row, column=2, value=seed["DA_ID"])
        ws.cell(row=row, column=3, value=seed["Soil"])
        ws.cell(row=row, column=4, value=seed["Slope"])
        ws.cell(row=row, column=5, value=seed["Landuse"])
        ws.cell(row=row, column=6, value=seed["Area_SF"])

    # Total data rows: at least DEFAULT_ROW_COUNTS["DA_Catchments"]
    data_rows = max(DEFAULT_ROW_COUNTS["DA_Catchments"], len(BLADENSBURG_DA_CATCHMENTS))

    # All rows (seeded + blank) get XLOOKUP formulas for C values and the Area_SF
    # column is left as a plain number (seed) or blank (user input).
    for i in range(data_rows):
        row = 2 + i
        # C_2-10: XLOOKUP(Landuse, Landuse_Lookup[Landuse], Landuse_Lookup[C_2-10], 0)
        # If Landuse cell is blank, XLOOKUP returns "" (via the if_not_found arg).
        ws.cell(
            row=row, column=7,
            value=f'=IF(E{row}="","",XLOOKUP(E{row},Landuse_Lookup[Landuse],Landuse_Lookup[C_2-10],""))'
        )
        ws.cell(
            row=row, column=8,
            value=f'=IF(E{row}="","",XLOOKUP(E{row},Landuse_Lookup[Landuse],Landuse_Lookup[C_25],""))'
        )

    last_row = 1 + data_rows
    table = Table(displayName="DA_Catchments", ref=f"A1:I{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    # Data validations
    dv_soil = DataValidation(type="list", formula1=f'"{",".join(SOIL_LIST)}"', allow_blank=True)
    dv_soil.add(f"C2:C{last_row}")
    ws.add_data_validation(dv_soil)

    dv_slope = DataValidation(type="list", formula1=f'"{",".join(SLOPE_LIST)}"', allow_blank=True)
    dv_slope.add(f"D2:D{last_row}")
    ws.add_data_validation(dv_slope)

    # Landuse dropdown references the Landuse_Lookup[Landuse] column via a named range we define inline.
    # For simplicity we use a static list from LANDUSE_SEED (same content as the table column).
    landuse_names = [l[0] for l in LANDUSE_SEED]
    dv_landuse = DataValidation(type="list",
                                formula1=f'"{",".join(landuse_names)}"',
                                allow_blank=True)
    dv_landuse.add(f"E2:E{last_row}")
    ws.add_data_validation(dv_landuse)

    # Column widths
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 6
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 8
    ws.column_dimensions["H"].width = 8
    ws.column_dimensions["I"].width = 24
```

- [ ] **Step 3: Wire into workbook.py**

Modify `drainage-calculator/bburg_template_builder/workbook.py`:

```python
from bburg_template_builder.sheets.da_catchments import build_da_catchments_sheet
# ... after lookup tables:
build_da_catchments_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_da_catchments.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/da_catchments.py \
        drainage-calculator/bburg_template_builder/tests/test_da_catchments.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): DA_Catchments long-form table with dropdowns and C-value XLOOKUPs"
```

---

## Task 7: Structures table (100 default rows + Bladensburg seed)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/structures.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_structures.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_structures.py`:

```python
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
            # All 6 types present
            for t in ("inlet", "manhole", "bend", "junction", "splitter", "outfall"):
                assert t in dv.formula1
    assert found, "Type dropdown not found"


def test_bladensburg_outfall_seeded(empty_wb):
    build_structures_sheet(empty_wb)
    ws = empty_wb["Structures"]
    outfalls = [ws.cell(row=r, column=1).value for r in range(2, 10)
                if ws.cell(row=r, column=2).value == "outfall"]
    assert "OUTFALL" in outfalls
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_structures.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the Structures sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/structures.py`:

```python
"""Structures sheet - one row per physical structure (inlet, manhole, outfall, etc.)."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import BLADENSBURG_STRUCTURES, DEFAULT_ROW_COUNTS


HEADERS = ["Structure_ID", "Type", "Description", "Rim_Elev",
           "Inv_In_Elev", "Inv_Out_Elev", "Angle_deg", "Linked_Pond_TW"]

TYPE_LIST = ("inlet", "manhole", "bend", "junction", "splitter", "outfall")


def build_structures_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Structures")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    for i, s in enumerate(BLADENSBURG_STRUCTURES):
        row = 2 + i
        ws.cell(row=row, column=1, value=s["Structure_ID"])
        ws.cell(row=row, column=2, value=s["Type"])
        ws.cell(row=row, column=3, value=s["Description"])
        ws.cell(row=row, column=4, value=s["Rim_Elev"])
        ws.cell(row=row, column=5, value=s["Inv_In_Elev"])
        ws.cell(row=row, column=6, value=s["Inv_Out_Elev"])
        ws.cell(row=row, column=7, value=s["Angle_deg"])
        # Linked_Pond_TW stays blank unless the user sets it

    data_rows = max(DEFAULT_ROW_COUNTS["Structures"], len(BLADENSBURG_STRUCTURES))
    last_row = 1 + data_rows
    table = Table(displayName="Structures", ref=f"A1:H{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    dv_type = DataValidation(type="list", formula1=f'"{",".join(TYPE_LIST)}"', allow_blank=True)
    dv_type.add(f"B2:B{last_row}")
    ws.add_data_validation(dv_type)

    # Angle 0..180 numeric bounds
    dv_angle = DataValidation(type="whole", operator="between",
                              formula1="0", formula2="180", allow_blank=True)
    dv_angle.add(f"G2:G{last_row}")
    ws.add_data_validation(dv_angle)

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 28
    for col in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col].width = 12
```

- [ ] **Step 3: Wire into workbook.py**

Add import and call after `build_da_catchments_sheet(wb)`:

```python
from bburg_template_builder.sheets.structures import build_structures_sheet
# ...
build_structures_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_structures.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/structures.py \
        drainage-calculator/bburg_template_builder/tests/test_structures.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Structures table with Type dropdown and seed data"
```

---

## Task 8: Pipes table (200 default rows + Bladensburg seed)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/pipes.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_pipes.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_pipes.py`:

```python
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
                "Size_in", "Material", "Manning_n", "Slope_ftft"]
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
    """Manning_n column must default via XLOOKUP on Material; user can override."""
    build_pipes_sheet(empty_wb)
    ws = empty_wb["Pipes"]
    # Any blank-row Manning_n (past the seeded Bladensburg rows)
    first_blank_row = 2 + len(BLADENSBURG_PIPES)
    val = ws.cell(row=first_blank_row, column=7).value
    assert str(val).startswith("=") and ("XLOOKUP" in str(val) or "VLOOKUP" in str(val))
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_pipes.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the Pipes sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/pipes.py`:

```python
"""Pipes sheet - one row per pipe reach."""
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from bburg_template_builder.seed_data import (
    BLADENSBURG_PIPES, DEFAULT_ROW_COUNTS, MATERIAL_MANNING, PIPE_PROPERTIES,
)


HEADERS = ["Pipe_ID", "From_Structure", "To_Structure", "Length_ft",
           "Size_in", "Material", "Manning_n", "Slope_ftft"]

MATERIAL_LIST = tuple(MATERIAL_MANNING.keys())
PIPE_SIZE_LIST = tuple(str(int(p[0])) for p in PIPE_PROPERTIES)


def build_pipes_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Pipes")
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)

    # Build a small 'Material_Manning_Map' helper range on this sheet so the
    # XLOOKUP for Manning_n is self-contained. Place at columns J:K below headers.
    ws.cell(row=1, column=10, value="Material")
    ws.cell(row=1, column=11, value="Default_n")
    for i, (mat, n) in enumerate(MATERIAL_MANNING.items()):
        ws.cell(row=2 + i, column=10, value=mat)
        ws.cell(row=2 + i, column=11, value=n)
    _last_mat_row = 1 + len(MATERIAL_MANNING)

    for i, p in enumerate(BLADENSBURG_PIPES):
        row = 2 + i
        ws.cell(row=row, column=1, value=p["Pipe_ID"])
        ws.cell(row=row, column=2, value=p["From_Structure"])
        ws.cell(row=row, column=3, value=p["To_Structure"])
        ws.cell(row=row, column=4, value=p["Length_ft"])
        ws.cell(row=row, column=5, value=p["Size_in"])
        ws.cell(row=row, column=6, value=p["Material"])
        ws.cell(row=row, column=8, value=p["Slope_ftft"])
        # Column 7 (Manning_n) gets the formula below

    data_rows = max(DEFAULT_ROW_COUNTS["Pipes"], len(BLADENSBURG_PIPES))
    for i in range(data_rows):
        row = 2 + i
        # Manning_n defaults from Material via XLOOKUP against the helper range J2:K{_last_mat_row}
        ws.cell(
            row=row, column=7,
            value=(f'=IF(F{row}="","",'
                   f'XLOOKUP(F{row},$J$2:$J${_last_mat_row},$K$2:$K${_last_mat_row},0.013))')
        )

    last_row = 1 + data_rows
    # Table covers columns A..H only (helper J:K lives outside the table)
    table = Table(displayName="Pipes", ref=f"A1:H{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)

    # From/To validation: reference Structures[Structure_ID]
    dv_from = DataValidation(type="list",
                             formula1="=INDIRECT(\"Structures[Structure_ID]\")",
                             allow_blank=True)
    dv_from.add(f"B2:B{last_row}")
    ws.add_data_validation(dv_from)

    dv_to = DataValidation(type="list",
                           formula1="=INDIRECT(\"Structures[Structure_ID]\")",
                           allow_blank=True)
    dv_to.add(f"C2:C{last_row}")
    ws.add_data_validation(dv_to)

    dv_material = DataValidation(type="list",
                                 formula1=f'"{",".join(MATERIAL_LIST)}"',
                                 allow_blank=True)
    dv_material.add(f"F2:F{last_row}")
    ws.add_data_validation(dv_material)

    dv_size = DataValidation(type="list",
                             formula1=f'"{",".join(PIPE_SIZE_LIST)}"',
                             allow_blank=True)
    dv_size.add(f"E2:E{last_row}")
    ws.add_data_validation(dv_size)

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    for col in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col].width = 11
    ws.column_dimensions["J"].width = 10
    ws.column_dimensions["K"].width = 10
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.pipes import build_pipes_sheet
# ...
build_pipes_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_pipes.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/pipes.py \
        drainage-calculator/bburg_template_builder/tests/test_pipes.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Pipes table with Material-defaulted Manning n and seed data"
```

---

## Task 9: Rationals-MCDOT report view (auto-filled from DA_Catchments)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/rationals_mcdot.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_rationals_mcdot.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

**Layout decision:** Keep the existing fixed-3-per-horizontal-band layout from the legacy sheet. Each inlet takes a 30-row × 9-col block. Three inlets per band (B/K/T), then skip to row +30 for the next band. Builder generates one block per unique Inlet_ID found in `BLADENSBURG_STRUCTURES` where `Type == "inlet"`. For a blank template with no seed structures, builder leaves placeholder blocks (first 6 blocks = rows 5..155, cols B..Z) with formula shells that read `=XLOOKUP(rank(1..6), Structures[Structure_ID]…)` so engineers can rename structures without rebuilding.

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_rationals_mcdot.py`:

```python
from bburg_template_builder.sheets.rationals_mcdot import build_rationals_sheet


def test_sheet_created(empty_wb):
    build_rationals_sheet(empty_wb)
    assert "Rationals-MCDOT" in empty_wb.sheetnames


def test_first_block_has_inlet_id_header(empty_wb):
    """The first inlet block starts at row 5 col B with the Inlet_ID text."""
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    # Block 1: cols B..H (2..8), starting row 5
    val = ws.cell(row=5, column=2).value
    assert val is not None  # Either a seeded ID "EX-I-1" or a formula referencing Structures


def test_block1_total_area_uses_sumifs(empty_wb):
    """Block 1 TOTAL row's Area_SF cell uses SUMIFS against DA_Catchments by Inlet_ID."""
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    # Per spec §5.10: TOTALS row at block-end, Area cell in column D (4)
    # Block 1 occupies rows 5..34 (header 5..10, data 11..19, totals 20, composite 22..23, Tc 25+, blank).
    totals_row = 20
    formula = ws.cell(row=totals_row, column=4).value
    assert "SUMIFS" in str(formula) or "SUMPRODUCT" in str(formula)
    assert "DA_Catchments" in str(formula)


def test_block1_intensity_uses_idf_lookup(empty_wb):
    """Block 1's rainfall intensity cells for 2/10/25-yr use XLOOKUP against IDF_Lookup."""
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    # Per spec §5.10: intensity rows in Tc section, rows 27..29 for 2/10/25 storm
    for storm_row in (27, 28, 29):
        formula = ws.cell(row=storm_row, column=5).value  # column E holds intensity
        assert "IDF_Lookup" in str(formula) or "XLOOKUP" in str(formula)


def test_three_blocks_per_band(empty_wb):
    """Band 1 contains blocks at cols B, K, T (columns 2, 11, 20)."""
    build_rationals_sheet(empty_wb)
    ws = empty_wb["Rationals-MCDOT"]
    # Block 1 Inlet_ID anchor
    assert ws.cell(row=5, column=2).value is not None
    # Block 2 Inlet_ID anchor
    assert ws.cell(row=5, column=11).value is not None
    # Block 3 Inlet_ID anchor
    assert ws.cell(row=5, column=20).value is not None
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_rationals_mcdot.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the Rationals-MCDOT sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/rationals_mcdot.py`:

```python
"""Rationals-MCDOT report view - per-inlet calc-sheet layout, auto-filled from DA_Catchments.

Layout (per spec §5.10): preserves legacy 30-row x 9-col block layout with 3 blocks per
horizontal band at columns B, K, T. Each block reads via SUMIFS on DA_Catchments by Inlet_ID.

Block anchor cells (block header Inlet_ID):
  Band 1 rows 5..34:  B5, K5, T5
  Band 2 rows 35..64: B35, K35, T35
  ... etc.

Within each block (base_col is the starting column, e.g. B=2):
  Header:        base_col+0 row+0  Inlet_ID (seeded or formula)
  Column labels: rows +4..+5
  Landuse rows:  rows +6..+14  (9 rows shown; actual data may spill from DA_Catchments)
  TOTALS row:    row +15        Area_SF = SUMIFS, CA_2-10 = SUMPRODUCT, CA_25 = SUMPRODUCT
  Composite C:   rows +17..+18  = CA / Area totals
  Tc input:      row +20        (user input; could default to 5)
  Intensity:     rows +22..+24  = XLOOKUP(Tc_rounded, IDF_Lookup[Tc_min], IDF_Lookup[i_{storm}])
  Q = CA*i/43560: rows +22..+24 column +5

Rows offset notation: "row +N" means `anchor_row + N` where anchor_row is the Inlet_ID header row.
"""
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from bburg_template_builder.seed_data import BLADENSBURG_STRUCTURES


# Columns within a block, relative to base_col (base=0 is Inlet_ID column):
#  0: Inlet_ID anchor / Soil / Slope / Landuse display
#  1: BY / Slope / (various)
#  2: DATE / Landuse
#  3: Area_SF
#  4: C 2-10  / i (in Tc section)
#  5: CA 2-10 / Q (in Tc section)
#  6: C 25
#  7: CA 25

ANCHOR_ROWS = [5, 35, 65, 95, 125, 155]  # band start rows (6 bands)
ANCHOR_COLS = [2, 11, 20]  # three blocks per band (B, K, T)
BLOCK_HEIGHT = 30
BLOCK_WIDTH = 9

STORMS_IN_BLOCK = ("2yr", "10yr", "25yr")


def _block_anchor(block_index: int) -> tuple[int, int]:
    """Return (row, col) of the Inlet_ID header for the N-th block (0-indexed)."""
    band = block_index // len(ANCHOR_COLS)
    pos = block_index % len(ANCHOR_COLS)
    return ANCHOR_ROWS[band], ANCHOR_COLS[pos]


def _build_block(ws, block_index: int, inlet_id_value_or_formula) -> None:
    anchor_row, anchor_col = _block_anchor(block_index)

    def col(offset: int) -> int:
        return anchor_col + offset

    def R(offset: int) -> int:
        return anchor_row + offset

    # Header
    ws.cell(row=R(0), column=col(0), value=inlet_id_value_or_formula)
    ws.cell(row=R(1), column=col(3), value="COMPUTED")
    ws.cell(row=R(1), column=col(4), value="")  # user fills "BY"

    # Column labels (rows 4..5)
    ws.cell(row=R(4), column=col(0), value="SOIL TYPE")
    ws.cell(row=R(4), column=col(1), value="% SLOPE")
    ws.cell(row=R(4), column=col(2), value="LANDUSE")
    ws.cell(row=R(4), column=col(3), value="AREA (SF)")
    ws.cell(row=R(4), column=col(4), value="2, 10-YR")
    ws.cell(row=R(4), column=col(6), value="25-YR")
    ws.cell(row=R(5), column=col(4), value="C")
    ws.cell(row=R(5), column=col(5), value="CA")
    ws.cell(row=R(5), column=col(6), value="C")
    ws.cell(row=R(5), column=col(7), value="CA")

    # Landuse rows 6..14: display from DA_Catchments where Inlet_ID matches.
    # Use dynamic-array formulas anchored in row 6 (Excel 365 supports spill).
    inlet_ref_cell = f"{get_column_letter(col(0))}{R(0)}"
    # Soil / Slope / Landuse / Area rows via FILTER
    filter_row = R(6)
    ws.cell(
        row=filter_row, column=col(0),
        value=(f'=IFERROR(FILTER(DA_Catchments[Soil],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(1),
        value=(f'=IFERROR(FILTER(DA_Catchments[Slope],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(2),
        value=(f'=IFERROR(FILTER(DA_Catchments[Landuse],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(3),
        value=(f'=IFERROR(FILTER(DA_Catchments[Area_SF],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(4),
        value=(f'=IFERROR(FILTER(DA_Catchments[C_2-10],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(5),
        value=(f'=IFERROR(FILTER(DA_Catchments[Area_SF]*DA_Catchments[C_2-10],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(6),
        value=(f'=IFERROR(FILTER(DA_Catchments[C_25],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )
    ws.cell(
        row=filter_row, column=col(7),
        value=(f'=IFERROR(FILTER(DA_Catchments[Area_SF]*DA_Catchments[C_25],'
               f'DA_Catchments[Inlet_ID]={inlet_ref_cell}),"")')
    )

    # TOTALS row (row +15)
    totals_row = R(15)
    ws.cell(row=totals_row, column=col(2), value="TOTALS")
    ws.cell(
        row=totals_row, column=col(3),
        value=(f"=SUMIFS(DA_Catchments[Area_SF],"
               f"DA_Catchments[Inlet_ID],{inlet_ref_cell})")
    )
    ws.cell(
        row=totals_row, column=col(5),
        value=(f"=SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref_cell})"
               f"*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])")
    )
    ws.cell(
        row=totals_row, column=col(7),
        value=(f"=SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref_cell})"
               f"*DA_Catchments[Area_SF]*DA_Catchments[C_25])")
    )

    # Composite C
    ws.cell(row=R(17), column=col(2), value="COMPOSITE C (2,10)")
    ws.cell(
        row=R(17), column=col(3),
        value=f"=IFERROR({get_column_letter(col(5))}{totals_row}/{get_column_letter(col(3))}{totals_row},0)"
    )
    ws.cell(row=R(18), column=col(2), value="COMPOSITE C (25)")
    ws.cell(
        row=R(18), column=col(3),
        value=f"=IFERROR({get_column_letter(col(7))}{totals_row}/{get_column_letter(col(3))}{totals_row},0)"
    )

    # Tc section
    ws.cell(row=R(19), column=col(0), value="TIME OF CONCENTRATION")
    ws.cell(row=R(20), column=col(0), value="Tc =")
    ws.cell(row=R(20), column=col(1), value=5)  # default 5 min; user can override
    ws.cell(row=R(20), column=col(2), value="MIN")

    # Rainfall intensity rows 22..24 for 2 / 10 / 25 yr
    tc_cell_ref = f"{get_column_letter(col(1))}{R(20)}"
    ws.cell(row=R(21), column=col(3), value="STORM")
    ws.cell(row=R(21), column=col(4), value="i (IN/HR)")
    ws.cell(row=R(21), column=col(5), value="Q (CFS)")
    composite_c_210_ref = f"{get_column_letter(col(3))}{R(17)}"
    composite_c_25_ref = f"{get_column_letter(col(3))}{R(18)}"
    area_total_ref = f"{get_column_letter(col(3))}{totals_row}"
    for i, storm in enumerate(STORMS_IN_BLOCK):
        r = R(22 + i)
        label = {"2yr": 2, "10yr": 10, "25yr": 25}[storm]
        ws.cell(row=r, column=col(3), value=label)
        ws.cell(
            row=r, column=col(4),
            value=f"=XLOOKUP(ROUND({tc_cell_ref},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}])"
        )
        c_ref = composite_c_25_ref if storm == "25yr" else composite_c_210_ref
        ws.cell(
            row=r, column=col(5),
            value=(f"={c_ref}*{get_column_letter(col(4))}{r}*{area_total_ref}/43560")
        )


def build_rationals_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("Rationals-MCDOT")
    ws.cell(row=1, column=1, value="PROJECT:")
    ws.cell(row=1, column=2, value="=Project_Name")
    ws.cell(row=2, column=1, value="JOB #:")
    ws.cell(row=2, column=2, value="=Project_Number")

    # Collect the list of inlet-type structures to seed with.
    # If there are no seeded inlets, generate blank blocks that read the N-th inlet
    # from Structures via XLOOKUP (so renaming in Structures ripples here).
    inlet_structures = [s for s in BLADENSBURG_STRUCTURES if s["Type"] == "inlet"]

    total_blocks = len(ANCHOR_ROWS) * len(ANCHOR_COLS)
    for block_index in range(total_blocks):
        if block_index < len(inlet_structures):
            # Hard-reference the seeded Inlet_ID via static value for printout clarity
            inlet_id_value = inlet_structures[block_index]["Structure_ID"]
        else:
            # Blank placeholder; engineer can type an Inlet_ID into the anchor cell.
            inlet_id_value = ""
        _build_block(ws, block_index, inlet_id_value)

    # Column widths for the three bands
    for band_start_col in ANCHOR_COLS:
        for offset, width in enumerate([8, 8, 14, 10, 6, 10, 6, 10, 2]):
            col_letter = get_column_letter(band_start_col + offset)
            ws.column_dimensions[col_letter].width = width
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.rationals_mcdot import build_rationals_sheet
# ...
build_rationals_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_rationals_mcdot.py -v`

Expected: all PASS.

- [ ] **Step 5: Manual Excel check**

Run: `python drainage-calculator/build_bburg_template.py`
Open `docs/bburg-p-c-template.xlsx` in Excel 365. Navigate to Rationals-MCDOT.
- Block 1 at B5 should show `EX-I-1`.
- Row 20 (TOTALS) column D (Area): should show `2394.28` SF (sum of 2209.54 + 184.74).
- Composite C (row 22, column D): should show `≈ 0.849` ((2209.54*0.9 + 184.74*0.24) / 2394.28).
- Intensity row at 10yr storm (row 29, column F) with Tc=5: should show `≈ 80.16` in/hr for PG county.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/rationals_mcdot.py \
        drainage-calculator/bburg_template_builder/tests/test_rationals_mcdot.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Rationals-MCDOT per-inlet report view via SUMIFS on DA_Catchments"
```

---

## Task 10: Inlet Spacing_10-yr and Inlet Spacing_2-yr (rewired, no hard-coded refs)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/inlet_spacing.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_inlet_spacing.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

The rewired sheet keeps the legacy column layout but replaces `='Rationals-MCDOT'!D20`-style refs with `SUMIFS(DA_Catchments[Area_SF], DA_Catchments[Inlet_ID], [@Inlet_ID])` style formulas. Each row's Inlet_ID drives everything.

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_inlet_spacing.py`:

```python
import re
from bburg_template_builder.sheets.inlet_spacing import build_inlet_spacing_sheets


def test_both_sheets_created(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    assert "Inlet Spacing_10-yr" in empty_wb.sheetnames
    assert "Inlet Spacing_2-yr" in empty_wb.sheetnames


def test_no_hardcoded_rationals_cell_refs(empty_wb):
    """Forbidden: ='Rationals-MCDOT'!D20 style A1 cell references."""
    build_inlet_spacing_sheets(empty_wb)
    forbidden_pattern = re.compile(r"'Rationals-MCDOT'![A-Z]+\d+(?!:)")  # A-Z letters + digits, not followed by colon (not a range)
    for sheet_name in ("Inlet Spacing_10-yr", "Inlet Spacing_2-yr"):
        ws = empty_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    assert not forbidden_pattern.search(cell.value), (
                        f"{sheet_name} {cell.coordinate}: hard-coded ref in formula: {cell.value}"
                    )


def test_area_column_uses_sumifs_on_da_catchments(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_10-yr"]
    # Per legacy layout, Area (acres) is column D (4). First data row = 11.
    val = ws.cell(row=11, column=4).value
    assert "SUMIFS" in str(val) and "DA_Catchments" in str(val)


def test_intensity_column_uses_idf_lookup(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_10-yr"]
    # Intensity column (I10) is column J (10).
    val = ws.cell(row=11, column=10).value
    assert "IDF_Lookup" in str(val) or "XLOOKUP" in str(val)
    assert "i_10yr" in str(val)


def test_sheet_2yr_uses_i_2yr_column(empty_wb):
    build_inlet_spacing_sheets(empty_wb)
    ws = empty_wb["Inlet Spacing_2-yr"]
    val = ws.cell(row=11, column=10).value
    assert "i_2yr" in str(val)
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_inlet_spacing.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the inlet_spacing module**

Create `drainage-calculator/bburg_template_builder/sheets/inlet_spacing.py`:

```python
"""Inlet Spacing_10-yr and Inlet Spacing_2-yr sheets - same columns as legacy, rewired to DA_Catchments.

Column layout (preserved from legacy):
  A: Inlet number       B: Catch basin type   C: Inlet length       D: Area (ac)
  E: C                  F: CA                 G: Bypass CA          H: Total CA
  I: Tc (min)           J: I (in/hr)          K: Q (cfs)            L: X-slope
  M: Grade              N: Computational      O: Allowable spread   ...

Each row corresponds to one inlet. Column A holds the Inlet_ID (user input;
could also be a dropdown referencing Structures[Structure_ID] where Type='inlet').
"""
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation


HEADERS_ROW_1 = "PROPOSED INLET SPACING SPREADS"
HEADERS_ROW_8 = [
    "INLET", "CATCH BASIN", "INLET", "AREA",
    "", "", "BYPASS", "TOTAL",
    "T.O.C.", "I", "Q", "XSLOPE",
    "GRADE", "COMPUTATIONAL", "ALLOWABLE SPREAD",
]
HEADERS_ROW_9 = [
    "NUMBER", "TYPE", "LENGTH", "(acres)",
    "C", "CA", "CA", "CA",
    "(MIN)", "(IN/HR)", "(CFS)", "(FT/FT)",
    "(FT/FT)", "PROGRAM", "(FT)",
]


def _build_single_inlet_spacing(ws, storm: str, storm_label: str) -> None:
    """Build an Inlet Spacing sheet for a given storm (2yr or 10yr).

    `storm` is the IDF_Lookup column suffix ("2yr" or "10yr").
    `storm_label` is the display label (e.g., "2 - YEAR" or "10 - YEAR").
    """
    ws["H1"] = HEADERS_ROW_1
    ws["A4"] = "PROJECT:"
    ws["D4"] = "=Project_Name"
    ws["K4"] = "GUTTER DEPRESSION ="
    ws["N4"] = 0.0833
    ws["O4"] = "FEET"
    ws["M5"] = "N ="
    ws["N5"] = "=Manning_n_RCP"
    ws["A6"] = "CONTRACT NO. :"
    ws["H6"] = f"STORM FREQUENCY: {storm_label}"
    ws["K6"] = "GUTTER WIDTH ="
    ws["N6"] = 1.33
    ws["O6"] = "FEET"

    for c, h in enumerate(HEADERS_ROW_8, start=1):
        ws.cell(row=8, column=c, value=h)
    for c, h in enumerate(HEADERS_ROW_9, start=1):
        ws.cell(row=9, column=c, value=h)

    # Data rows 11..30 (20 inlets default; engineers can extend).
    last_row = 30
    for r in range(11, last_row + 1):
        inlet_ref = f"$A{r}"

        # D (Area in acres)
        ws.cell(
            row=r, column=4,
            value=(f'=IF({inlet_ref}="","",'
                   f'SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{inlet_ref})/43560)')
        )
        # E (composite C for the 10-yr storm uses C_2-10; for 2-yr storm, C_2-10 is also used
        # because MDOT/MCDOT uses the same C for 2-yr and 10-yr events)
        ws.cell(
            row=r, column=5,
            value=(f'=IF({inlet_ref}="","",IFERROR('
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])'
                   f'/SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{inlet_ref}),0))')
        )
        # F (CA)
        ws.cell(
            row=r, column=6,
            value=(f'=IF({inlet_ref}="","",'
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={inlet_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[C_2-10])/43560)')
        )
        # G (Bypass CA) - user input, default 0
        ws.cell(row=r, column=7, value=0)
        # H (Total CA) = F + G
        ws.cell(row=r, column=8, value=f'=IF({inlet_ref}="","",F{r}+G{r})')
        # I (Tc) - user input; default 5
        ws.cell(row=r, column=9, value=5)
        # J (Intensity) from IDF_Lookup
        ws.cell(
            row=r, column=10,
            value=(f'=IF({inlet_ref}="","",'
                   f'XLOOKUP(ROUND(I{r},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}]))')
        )
        # K (Q) = Total CA * I
        ws.cell(row=r, column=11, value=f'=IF({inlet_ref}="","",H{r}*J{r})')
        # L (X-slope) user input
        # M (Grade) user input
        # N (Computational program) user input
        # O (Allowable spread) user input

    # Inlet_ID dropdown in column A sourced from Structures table where Type='inlet'
    # Simpler: dropdown lists all Structure_IDs; user picks inlets.
    dv_inlet = DataValidation(
        type="list",
        formula1='=INDIRECT("Structures[Structure_ID]")',
        allow_blank=True,
    )
    dv_inlet.add(f"A11:A{last_row}")
    ws.add_data_validation(dv_inlet)

    # Column widths
    widths = [10, 12, 8, 8, 6, 8, 8, 8, 8, 8, 8, 8, 8, 14, 12]
    for i, w in enumerate(widths, start=1):
        col_letter = chr(ord("A") + i - 1) if i <= 26 else "A" + chr(ord("A") + i - 27)
        ws.column_dimensions[col_letter].width = w


def build_inlet_spacing_sheets(wb: Workbook) -> None:
    ws10 = wb.create_sheet("Inlet Spacing_10-yr")
    _build_single_inlet_spacing(ws10, storm="10yr", storm_label="10 - YEAR")
    ws2 = wb.create_sheet("Inlet Spacing_2-yr")
    _build_single_inlet_spacing(ws2, storm="2yr", storm_label="2 - YEAR")
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.inlet_spacing import build_inlet_spacing_sheets
# ...
build_inlet_spacing_sheets(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_inlet_spacing.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/inlet_spacing.py \
        drainage-calculator/bburg_template_builder/tests/test_inlet_spacing.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): Inlet Spacing 10-yr/2-yr sheets rewired to DA_Catchments"
```

---

## Task 11: 10 Yr Pipe Capacity and 25 Yr Pipe Capacity (SHA sheet renamed; rewired)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/pipe_capacity.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_pipe_capacity.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_pipe_capacity.py`:

```python
import re
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
    # Q column is column L (12); first data row = 14
    q_formula = str(ws.cell(row=14, column=12).value)
    assert "IDF_Lookup" in q_formula or "XLOOKUP" in q_formula
    assert "i_10yr" in q_formula


def test_manning_n_pulled_from_pipes_table(empty_wb):
    build_pipe_capacity_sheets(empty_wb)
    ws = empty_wb["10 Yr Pipe Capacity"]
    # n column is column O (15); first data row = 14
    n_formula = str(ws.cell(row=14, column=15).value)
    assert "Pipes[Manning_n]" in n_formula or "XLOOKUP" in n_formula
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_pipe_capacity.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the pipe_capacity module**

Create `drainage-calculator/bburg_template_builder/sheets/pipe_capacity.py`:

```python
"""10 Yr Pipe Capacity and 25 Yr Pipe Capacity sheets.

Same columns as legacy MDSHA format. Replaces hard-coded refs with structured
lookups: SUMIFS into DA_Catchments by Inlet_ID; XLOOKUP into Pipes / Pipe_Properties
/ IDF_Lookup.

Legacy layout (row 11 is header, data starts row 14):
  A From  B To  C Area_count  D Area(AC)  E C_runoff  F CA  G Adj.CA
  H SumA  I SumCA  J Tc  K Intensity  L Q  M Size  N Type  O n  ...
"""
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation


HEADERS_ROW_8 = [
    "", "", "Contributing Area", "", "", "", "",
    "{STORM} Year Runoff", "", "", "", "", "Pipe", "",
]
HEADERS_ROW_11 = [
    "FROM", "TO", "AREA", "AREA", "RUNOFF", "", "ADJ.",
    "SumA", "SumCA", "Conc>", "Intens.", "Q", "Size", "Type", "MANNING",
]
HEADERS_ROW_12 = [
    "", "", "(#)", "(AC.)", "COEF.", "", "",
    "", "", "(MIN)", "(IN/HR)", "(CFS)", "(IN)", "", "Coef.",
]


def _build_single_pipe_capacity(ws, storm: str, storm_label: str) -> None:
    ws["A1"] = "MARYLAND HIGHWAY / COUNTY STORM SEWER DESIGN"
    ws["A5"] = "DESIGNED BY:"
    ws["I5"] = "CONTRACT:"
    ws["I6"] = "TITLE:"

    for c, h in enumerate(HEADERS_ROW_8, start=1):
        ws.cell(row=8, column=c, value=h.replace("{STORM}", storm_label))
    for c, h in enumerate(HEADERS_ROW_11, start=1):
        ws.cell(row=11, column=c, value=h)
    for c, h in enumerate(HEADERS_ROW_12, start=1):
        ws.cell(row=12, column=c, value=h)

    # Data rows 14..50 (37 rows default)
    last_row = 50
    for r in range(14, last_row + 1):
        from_ref = f"$A{r}"
        pipe_ref = _pipe_id_formula_from_from_structure(r)

        # D: Area (ac) = SUMIFS(DA_Catchments[Area_SF], Inlet_ID, From) / 43560
        ws.cell(
            row=r, column=4,
            value=(f'=IF({from_ref}="","",'
                   f'SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{from_ref})/43560)')
        )
        # E: C (composite for 2-10 or 25 based on storm)
        c_column = "C_25" if storm == "25yr" else "C_2-10"
        ws.cell(
            row=r, column=5,
            value=(f'=IF({from_ref}="","",IFERROR('
                   f'SUMPRODUCT((DA_Catchments[Inlet_ID]={from_ref})'
                   f'*DA_Catchments[Area_SF]*DA_Catchments[{c_column}])'
                   f'/SUMIFS(DA_Catchments[Area_SF],DA_Catchments[Inlet_ID],{from_ref}),0))')
        )
        # F: CA = D * E
        ws.cell(row=r, column=6, value=f'=IF({from_ref}="","",D{r}*E{r})')
        # G: Adj. CA (user input or 0 default)
        ws.cell(row=r, column=7, value=0)
        # H: SumA - running total; user types in cumulative or formula from upstream
        ws.cell(row=r, column=8, value=f'=D{r}')
        # I: SumCA
        ws.cell(row=r, column=9, value=f'=F{r}')
        # J: Tc - user input; default 5
        ws.cell(row=r, column=10, value=5)
        # K: Intensity from IDF_Lookup
        ws.cell(
            row=r, column=11,
            value=(f'=IF({from_ref}="","",'
                   f'XLOOKUP(ROUND(J{r},1),IDF_Lookup[Tc_min],IDF_Lookup[i_{storm}]))')
        )
        # L: Q = SumCA * Intensity
        ws.cell(row=r, column=12, value=f'=IF({from_ref}="","",I{r}*K{r})')
        # M: Size (in) from Pipes table using Pipe_ID lookup
        ws.cell(
            row=r, column=13,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Size_in]),""))')
        )
        # N: Material (Type) from Pipes table
        ws.cell(
            row=r, column=14,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Material]),""))')
        )
        # O: Manning n from Pipes table
        ws.cell(
            row=r, column=15,
            value=(f'=IF({from_ref}="","",'
                   f'IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Manning_n]),0.013))')
        )

    # From/To dropdowns reference Structures
    dv_from = DataValidation(type="list",
                             formula1='=INDIRECT("Structures[Structure_ID]")',
                             allow_blank=True)
    dv_from.add(f"A14:A{last_row}")
    ws.add_data_validation(dv_from)

    dv_to = DataValidation(type="list",
                           formula1='=INDIRECT("Structures[Structure_ID]")',
                           allow_blank=True)
    dv_to.add(f"B14:B{last_row}")
    ws.add_data_validation(dv_to)

    # Column widths
    for i, w in enumerate([10, 10, 8, 8, 7, 7, 7, 8, 8, 7, 8, 8, 7, 8, 8], start=1):
        col_letter = chr(ord("A") + i - 1)
        ws.column_dimensions[col_letter].width = w


def _pipe_id_formula_from_from_structure(row: int) -> str:
    """Pipe_ID lookup: find the Pipe whose From_Structure = this row's From."""
    return (f'INDEX(Pipes[Pipe_ID],MATCH(1,'
            f'(Pipes[From_Structure]=A{row})*(Pipes[To_Structure]=B{row}),0))')


def build_pipe_capacity_sheets(wb: Workbook) -> None:
    ws10 = wb.create_sheet("10 Yr Pipe Capacity")
    _build_single_pipe_capacity(ws10, storm="10yr", storm_label="10")
    ws25 = wb.create_sheet("25 Yr Pipe Capacity")
    _build_single_pipe_capacity(ws25, storm="25yr", storm_label="25")
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.pipe_capacity import build_pipe_capacity_sheets
# ...
build_pipe_capacity_sheets(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_pipe_capacity.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/pipe_capacity.py \
        drainage-calculator/bburg_template_builder/tests/test_pipe_capacity.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): 10/25 Yr Pipe Capacity sheets rewired via structured lookups"
```

---

## Task 12: HGL sheet (generalized, method toggle, TW input, upstream walk)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/hgl.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_hgl.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_hgl.py`:

```python
from bburg_template_builder.sheets.hgl import build_hgl_sheet


def test_sheet_created(empty_wb):
    build_hgl_sheet(empty_wb)
    assert "HGL" in empty_wb.sheetnames


def test_top_inputs_present(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    # Labels anywhere in rows 1..6
    labels = [ws.cell(row=r, column=c).value for r in range(1, 7) for c in range(1, 8)]
    label_text = " ".join(str(x) for x in labels if x)
    assert "TW_Elev_Start" in label_text or "Starting tailwater" in label_text
    assert "Storm" in label_text
    assert "HGL_Method" in label_text or "Method" in label_text


def test_hgl_has_expected_columns(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    # Header row 8 (rows 1-7 reserved for inputs + metadata)
    header_cells = [ws.cell(row=8, column=c).value for c in range(1, 30)]
    header_text = " ".join(str(x) for x in header_cells if x)
    for required in ("Pipe_ID", "From", "To", "Q", "Size", "n",
                     "V", "Vh", "Sf", "Hf", "Kb", "Hb",
                     "HGL_dn", "EGL_dn", "HGL_up", "EGL_up", "Regime"):
        assert required in header_text, f"Missing column header: {required}"


def test_hgl_up_formula_branches_on_hgl_method(empty_wb):
    """HGL_up formula must switch based on HGL_Method (HEC-22 vs Legacy)."""
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    # HGL_up column: find it
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 30)
               if ws.cell(row=header_row, column=c).value}
    hgl_up_col = headers["HGL_up"]
    # First data row is header_row + 2 (allowing a sub-header row)
    val = str(ws.cell(row=10, column=hgl_up_col).value)
    assert "HGL_Method" in val
    assert "Legacy" in val
    # Must use IF/SWITCH to branch
    assert val.startswith("=") and ("IF(" in val or "SWITCH(" in val)


def test_first_row_hgl_dn_uses_tw_elev_start(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 30)
               if ws.cell(row=header_row, column=c).value}
    hgl_dn_raw_col = headers["HGL_dn_raw"]
    # First data row (row 10) HGL_dn_raw references TW_Elev_Start
    val = str(ws.cell(row=10, column=hgl_dn_raw_col).value)
    assert "TW_Elev_Start" in val


def test_crown_check_references_crown_freeboard(empty_wb):
    build_hgl_sheet(empty_wb)
    ws = empty_wb["HGL"]
    header_row = 8
    headers = {ws.cell(row=header_row, column=c).value: c for c in range(1, 30)
               if ws.cell(row=header_row, column=c).value}
    # One of the check columns should reference Crown_Freeboard named range
    found = False
    for name, col in headers.items():
        if "Crown" in str(name) and "check" in str(name).lower():
            val = str(ws.cell(row=10, column=col).value)
            if "Crown_Freeboard" in val:
                found = True
                break
    assert found, "No Crown check column referencing Crown_Freeboard"
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_hgl.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the HGL sheet module**

Create `drainage-calculator/bburg_template_builder/sheets/hgl.py`:

```python
"""HGL sheet - generalized hydraulic grade line walker.

One row per pipe reach, ordered downstream-to-upstream. User sets TW_Elev_Start at
the top; the walk propagates upstream. HGL_Method dropdown picks:
  - "HEC-22 EGL (d/s crown floor)": HGL_up = HGL_dn + Hf (no u/s floor)
  - "Legacy both-end crown floor":   HGL_up = MAX(HGL_dn + Hf, Crown_up)
"""
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName


# Column layout for the walker (header row 8). Order matters - EGL_dn refs row-below.
COLUMNS = [
    "Pipe_ID", "From", "To", "Q", "Size", "Length", "n",
    "Area", "R", "V", "Vh", "Sf", "Hf",
    "Inv_dn", "Inv_up", "Crown_dn", "Crown_up",
    "Type_u/s", "Angle_u/s", "Kb", "Hb",
    "HGL_dn_raw", "HGL_dn", "EGL_dn", "HGL_up_raw", "HGL_up", "EGL_up",
    "Regime", "Rim_u/s", "Crown_check", "Rim_check",
]


def _col_index(name: str) -> int:
    return COLUMNS.index(name) + 1


def _ref(row: int, name: str) -> str:
    return f"{get_column_letter(_col_index(name))}{row}"


def build_hgl_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("HGL")

    # Top-of-sheet inputs (rows 1-6)
    ws["A1"] = "HGL SHEET - Hydraulic Grade Line Walker"
    ws["A3"] = "TW_Elev_Start (ft):"
    ws["C3"] = 60.0  # default outfall elevation; user overrides
    wb.defined_names["TW_Elev_Start"] = DefinedName(name="TW_Elev_Start", attr_text="HGL!$C$3")
    ws["A4"] = "Storm_Selected:"
    ws["C4"] = "=Storm_Primary"
    ws["A5"] = "HGL_Method:"
    ws["C5"] = "=HGL_Method"
    ws["A6"] = "Instructions: paste one row per pipe (downstream-first). Formulas walk upstream."

    # Column headers (row 8)
    for c, name in enumerate(COLUMNS, start=1):
        ws.cell(row=8, column=c, value=name)

    # Data rows 10..60 (51 pipe rows; extend as needed)
    first_data_row = 10
    last_data_row = 60
    for r in range(first_data_row, last_data_row + 1):
        # Pipe_ID: user input (dropdown against Pipes[Pipe_ID])
        pipe_ref = f"$A{r}"
        from_ref = f"$B{r}"
        to_ref = f"$C{r}"

        # B: From  - lookup from Pipes table
        ws.cell(
            row=r, column=_col_index("From"),
            value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[From_Structure]),"")'
        )
        # C: To
        ws.cell(
            row=r, column=_col_index("To"),
            value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[To_Structure]),"")'
        )
        # D: Q - from 25 Yr Pipe Capacity or 10 Yr Pipe Capacity based on Storm_Selected
        # For simplicity, user types Q here or we XLOOKUP into Pipe Capacity sheet by Pipe_ID.
        # We lookup from both Pipe Capacity sheets and pick by storm.
        ws.cell(
            row=r, column=_col_index("Q"),
            value=(f'=IFERROR(IF(Storm_Primary="25yr",'
                   f'INDEX(\'25 Yr Pipe Capacity\'!$L:$L,MATCH({from_ref},\'25 Yr Pipe Capacity\'!$A:$A,0)),'
                   f'INDEX(\'10 Yr Pipe Capacity\'!$L:$L,MATCH({from_ref},\'10 Yr Pipe Capacity\'!$A:$A,0))),"")')
        )
        # E: Size
        ws.cell(
            row=r, column=_col_index("Size"),
            value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Size_in]),"")'
        )
        # F: Length
        ws.cell(
            row=r, column=_col_index("Length"),
            value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Length_ft]),"")'
        )
        # G: n
        ws.cell(
            row=r, column=_col_index("n"),
            value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Manning_n]),0.013)'
        )
        # H: Area (full)
        size_ref = _ref(r, "Size")
        ws.cell(
            row=r, column=_col_index("Area"),
            value=f'=IFERROR(XLOOKUP({size_ref},Pipe_Properties[Size],Pipe_Properties[Area]),0)'
        )
        # I: R (full)
        ws.cell(
            row=r, column=_col_index("R"),
            value=f'=IFERROR(XLOOKUP({size_ref},Pipe_Properties[Size],Pipe_Properties[Hyd Radius]),0)'
        )
        # J: V
        area_ref = _ref(r, "Area")
        q_ref = _ref(r, "Q")
        ws.cell(row=r, column=_col_index("V"), value=f'=IFERROR({q_ref}/{area_ref},0)')
        # K: Vh
        v_ref = _ref(r, "V")
        ws.cell(row=r, column=_col_index("Vh"), value=f'={v_ref}^2/(2*Gravity_g)')
        # L: Sf
        n_ref = _ref(r, "n")
        r_ref = _ref(r, "R")
        ws.cell(
            row=r, column=_col_index("Sf"),
            value=f'=IFERROR(({q_ref}*{n_ref}/(1.486*{area_ref}*{r_ref}^(2/3)))^2,0)'
        )
        # M: Hf
        sf_ref = _ref(r, "Sf")
        len_ref = _ref(r, "Length")
        ws.cell(row=r, column=_col_index("Hf"), value=f'={sf_ref}*{len_ref}')
        # N: Inv_dn (from Structures by From)
        ws.cell(
            row=r, column=_col_index("Inv_dn"),
            value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Inv_Out_Elev]),0)'
        )
        # O: Inv_up (from Structures by To)
        ws.cell(
            row=r, column=_col_index("Inv_up"),
            value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Inv_In_Elev]),0)'
        )
        # P: Crown_dn = Inv_dn + Size/12
        inv_dn_ref = _ref(r, "Inv_dn")
        inv_up_ref = _ref(r, "Inv_up")
        ws.cell(row=r, column=_col_index("Crown_dn"), value=f'={inv_dn_ref}+{size_ref}/12')
        ws.cell(row=r, column=_col_index("Crown_up"), value=f'={inv_up_ref}+{size_ref}/12')
        # R: Type u/s (looked up from Structures by To)
        ws.cell(
            row=r, column=_col_index("Type_u/s"),
            value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Type]),"")'
        )
        # S: Angle u/s
        ws.cell(
            row=r, column=_col_index("Angle_u/s"),
            value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Angle_deg]),0)'
        )
        # T: Kb - SWITCH on Type_u/s + XLOOKUP into Kb_Values by Angle
        type_ref = _ref(r, "Type_u/s")
        angle_ref = _ref(r, "Angle_u/s")
        kb_formula = (
            f'=IFERROR(SWITCH({type_ref},'
            f'"inlet",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Inlet],0,-1),'
            f'"manhole",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Manhole],0,-1),'
            f'"bend",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Bend],0,-1),'
            f'"junction",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Junction],0,-1),'
            f'"splitter",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Manhole],0,-1),'
            f'"outfall",0,'
            f'0),0)'
        )
        ws.cell(row=r, column=_col_index("Kb"), value=kb_formula)
        # U: Hb = Kb * Vh (this row's own Vh, per MCDrainage §7.4)
        kb_ref = _ref(r, "Kb")
        vh_ref = _ref(r, "Vh")
        ws.cell(row=r, column=_col_index("Hb"), value=f'={kb_ref}*{vh_ref}')

        # V: HGL_dn_raw
        if r == first_data_row:
            # First (most d/s) row: HGL_dn_raw = TW_Elev_Start
            ws.cell(row=r, column=_col_index("HGL_dn_raw"), value=f'=TW_Elev_Start')
        else:
            # Subsequent: HGL_dn_raw = EGL_dn (this row) - Vh (this row).
            # But EGL_dn for this row is computed from EGL_up of row below + Hb of row below.
            # Those are the row-r-1 values (one row DOWNSTREAM = one closer to the outfall in the
            # sheet's top-to-bottom ordering if we wrote d/s-first... but convention here is
            # d/s row FIRST at row 10, so row r-1 IS downstream of row r).
            egl_dn_this = _ref(r, "EGL_dn")
            ws.cell(row=r, column=_col_index("HGL_dn_raw"),
                    value=f'={egl_dn_this}-{vh_ref}')

        # W: HGL_dn = MAX(HGL_dn_raw, Crown_dn) - crown floor at d/s always applied
        hgl_dn_raw_ref = _ref(r, "HGL_dn_raw")
        crown_dn_ref = _ref(r, "Crown_dn")
        ws.cell(row=r, column=_col_index("HGL_dn"),
                value=f'=MAX({hgl_dn_raw_ref},{crown_dn_ref})')

        # X: EGL_dn
        if r == first_data_row:
            hgl_dn_ref = _ref(r, "HGL_dn")
            ws.cell(row=r, column=_col_index("EGL_dn"),
                    value=f'={hgl_dn_ref}+{vh_ref}')
        else:
            # EGL_dn (row r) = EGL_up (row r-1) + Hb (row r-1)
            egl_up_below = _ref(r - 1, "EGL_up")
            hb_below = _ref(r - 1, "Hb")
            ws.cell(row=r, column=_col_index("EGL_dn"),
                    value=f'={egl_up_below}+{hb_below}')

        # Y: HGL_up_raw = HGL_dn + Hf
        hgl_dn_ref = _ref(r, "HGL_dn")
        hf_ref = _ref(r, "Hf")
        ws.cell(row=r, column=_col_index("HGL_up_raw"),
                value=f'={hgl_dn_ref}+{hf_ref}')

        # Z: HGL_up - method-dependent
        hgl_up_raw_ref = _ref(r, "HGL_up_raw")
        crown_up_ref = _ref(r, "Crown_up")
        ws.cell(
            row=r, column=_col_index("HGL_up"),
            value=(f'=IF(HGL_Method="Legacy both-end crown floor",'
                   f'MAX({hgl_up_raw_ref},{crown_up_ref}),'
                   f'{hgl_up_raw_ref})')
        )

        # AA: EGL_up = HGL_up + Vh
        hgl_up_ref = _ref(r, "HGL_up")
        ws.cell(row=r, column=_col_index("EGL_up"),
                value=f'={hgl_up_ref}+{vh_ref}')

        # AB: Regime
        ws.cell(
            row=r, column=_col_index("Regime"),
            value=(f'=IF({hgl_dn_raw_ref}>={crown_dn_ref},"Pressurized",'
                   f'IF(AND(HGL_Method="Legacy both-end crown floor",{hgl_up_raw_ref}<{crown_up_ref}),'
                   f'"Gravity - u/s crown floor also applied",'
                   f'"Gravity - d/s crown floor applied"))')
        )

        # AC: Rim_u/s
        ws.cell(
            row=r, column=_col_index("Rim_u/s"),
            value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Rim_Elev]),0)'
        )
        # AD: Crown_check
        ws.cell(
            row=r, column=_col_index("Crown_check"),
            value=(f'=IF({hgl_up_ref}>{crown_up_ref}+Crown_Freeboard,"FAIL","OK")')
        )
        # AE: Rim_check
        rim_ref = _ref(r, "Rim_u/s")
        ws.cell(
            row=r, column=_col_index("Rim_check"),
            value=(f'=IF({hgl_up_ref}>{rim_ref}-Rim_Freeboard,"FAIL","OK")')
        )

    # Pipe_ID dropdown
    from openpyxl.worksheet.datavalidation import DataValidation
    dv_pipe = DataValidation(type="list",
                             formula1='=INDIRECT("Pipes[Pipe_ID]")',
                             allow_blank=True)
    dv_pipe.add(f"A{first_data_row}:A{last_data_row}")
    ws.add_data_validation(dv_pipe)

    # Column widths
    for i, name in enumerate(COLUMNS, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = 10
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.hgl import build_hgl_sheet
# ...
build_hgl_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_hgl.py -v`

Expected: all PASS.

- [ ] **Step 5: Manual Excel check**

Run: `python drainage-calculator/build_bburg_template.py`
Open `docs/bburg-p-c-template.xlsx` in Excel. Navigate to HGL.
- Set TW_Elev_Start (cell C3) = 65.
- Type Pipe_ID `P-2` in A10, `P-1` in A11. The sheet should populate From/To/Size/Length/Q/etc. automatically.
- Verify HGL_dn, HGL_up, EGL columns compute cleanly (no `#DIV/0!` or `#REF!`).
- Toggle `Config.HGL_Method` from `HEC-22 EGL (d/s crown floor)` to `Legacy both-end crown floor`; `HGL_up` values on gravity reaches should change.
- Hand-check Pipe P-2 (18" RCP, 80 ft, slope 0.049, at 10-yr storm): Q should be a few cfs; HGL_up should land near Crown_up at the first pipe when gravity-flow.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/hgl.py \
        drainage-calculator/bburg_template_builder/tests/test_hgl.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): HGL sheet with starting TW, method toggle, and upstream walk"
```

---

## Task 13: HGL_Example sheet (educational, both methods side-by-side)

**Files:**
- Create: `drainage-calculator/bburg_template_builder/sheets/hgl_example.py`
- Create: `drainage-calculator/bburg_template_builder/tests/test_hgl_example.py`
- Modify: `drainage-calculator/bburg_template_builder/workbook.py`

Keep this sheet deliberately self-contained (no refs to DA_Catchments / Pipes / Structures). A fixed 4-pipe 5-structure network with inputs at the top; every calc shown step-by-step. Both `HEC-22` and `Legacy` results shown side-by-side.

- [ ] **Step 1: Write the failing test**

Create `drainage-calculator/bburg_template_builder/tests/test_hgl_example.py`:

```python
from bburg_template_builder.sheets.hgl_example import build_hgl_example_sheet


def test_sheet_created(empty_wb):
    build_hgl_example_sheet(empty_wb)
    assert "HGL_Example" in empty_wb.sheetnames


def test_inputs_at_top(empty_wb):
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    # Row 3 should have "Starting tailwater" label + a numeric value cell
    labels = [str(ws.cell(row=r, column=1).value or "") for r in range(1, 10)]
    assert any("tailwater" in s.lower() or "TW" in s for s in labels)


def test_has_four_pipe_blocks(empty_wb):
    """Expect 4 pipe blocks (P-4, P-3, P-2, P-1 in d/s-to-u/s order)."""
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    # Each block has a header like "--- Pipe P-4 ---" in column A
    pipe_labels = [
        str(ws.cell(row=r, column=1).value or "")
        for r in range(1, ws.max_row + 1)
    ]
    for pid in ("P-4", "P-3", "P-2", "P-1"):
        assert any(pid in s for s in pipe_labels), f"Missing pipe block for {pid}"


def test_side_by_side_method_columns(empty_wb):
    build_hgl_example_sheet(empty_wb)
    ws = empty_wb["HGL_Example"]
    # Header row (row 10) should contain "HEC-22" and "Legacy" labels
    headers = [str(ws.cell(row=10, column=c).value or "") for c in range(1, 8)]
    header_text = " ".join(headers)
    assert "HEC-22" in header_text
    assert "Legacy" in header_text
```

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_hgl_example.py -v`

Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 2: Create the HGL_Example module**

Create `drainage-calculator/bburg_template_builder/sheets/hgl_example.py`:

```python
"""HGL_Example - educational step-by-step HGL/EGL walk for a 4-pipe 5-structure network.

All numbers are live formulas off a tiny input block at the top; both HEC-22 and
Legacy methods are computed side-by-side so engineers can see how they diverge.

Network:
  [S-1 inlet]--P-1(12",60')-->[S-2 manhole,0]--P-2(15",95')-->
    [S-3 bend,15]--P-3(18",110')-->[S-4 inlet,0]--P-4(24",80')-->[OUTFALL endwall]

Walk order in the sheet: downstream-first (P-4 at the top block, P-1 at the bottom).
"""
from openpyxl import Workbook


# Pipe definitions in d/s-to-u/s order
PIPES = [
    # (ID, L_ft, D_in, n, Q_cfs, Inv_dn, Inv_up, u/s_struct_type, u/s_angle_deg)
    ("P-4", 80.0,  24, 0.013, 9.5, 94.00, 94.56, "inlet",   0),
    ("P-3", 110.0, 18, 0.013, 7.2, 94.56, 95.66, "bend",    15),
    ("P-2", 95.0,  15, 0.013, 4.5, 95.66, 96.61, "manhole", 0),
    ("P-1", 60.0,  12, 0.013, 2.1, 96.61, 97.21, "inlet",   0),
]

# Structure rims (for check rows); S-5 = OUTFALL endwall
STRUCTURE_RIMS = {"OUTFALL": 98.00, "S-4": 100.00, "S-3": 102.00, "S-2": 104.00, "S-1": 106.00}


def build_hgl_example_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("HGL_Example")

    # Title and inputs
    ws["A1"] = "HGL_Example - Educational step-by-step (both methods side-by-side)"
    ws["A3"] = "Starting tailwater at endwall (ft):"
    ws["C3"] = 97.00  # user-editable
    ws["A4"] = "HGL_Method (reads from Config):"
    ws["C4"] = "=HGL_Method"
    ws["A6"] = "Network: [S-1]-P-1->[S-2]-P-2->[S-3]-P-3->[S-4]-P-4->[OUTFALL]"
    ws["A7"] = "Walk order below: downstream-first (P-4 first, P-1 last)"

    # Side-by-side method headers (row 10)
    ws["A10"] = "Equation (symbolic)"
    ws["B10"] = "Substituted values"
    ws["C10"] = "HEC-22 (d/s floor)"
    ws["D10"] = "Legacy both-end"

    tw_cell = "$C$3"
    row = 12
    prev_egl_up_hec22 = None
    prev_egl_up_legacy = None
    prev_hb_hec22 = None
    prev_hb_legacy = None

    for idx, (pid, L, D, n, Q, inv_dn, inv_up, up_type, up_angle) in enumerate(PIPES):
        ws.cell(row=row, column=1, value=f"--- Pipe {pid} (D={D}\", L={L}, Q={Q} cfs) ---")
        row += 1

        # Area (full)
        ws.cell(row=row, column=1, value="Area = pi*(D/12)^2/4")
        ws.cell(row=row, column=2, value=f"pi*({D}/12)^2/4")
        area_formula = f"PI()*({D}/12)^2/4"
        ws.cell(row=row, column=3, value=f"={area_formula}")
        ws.cell(row=row, column=4, value=f"={area_formula}")
        area_ref_hec22 = f"$C${row}"
        area_ref_legacy = f"$D${row}"
        row += 1

        # V
        ws.cell(row=row, column=1, value="V = Q / Area")
        ws.cell(row=row, column=2, value=f"{Q} / Area")
        ws.cell(row=row, column=3, value=f"={Q}/{area_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={Q}/{area_ref_legacy}")
        v_ref_hec22 = f"$C${row}"
        v_ref_legacy = f"$D${row}"
        row += 1

        # Vh
        ws.cell(row=row, column=1, value="Vh = V^2 / (2g)")
        ws.cell(row=row, column=2, value="V^2 / 64.4")
        ws.cell(row=row, column=3, value=f"={v_ref_hec22}^2/64.4")
        ws.cell(row=row, column=4, value=f"={v_ref_legacy}^2/64.4")
        vh_ref_hec22 = f"$C${row}"
        vh_ref_legacy = f"$D${row}"
        row += 1

        # R
        ws.cell(row=row, column=1, value="R = D/4 (full)")
        ws.cell(row=row, column=2, value=f"{D}/12/4")
        r_formula = f"({D}/12)/4"
        ws.cell(row=row, column=3, value=f"={r_formula}")
        ws.cell(row=row, column=4, value=f"={r_formula}")
        r_ref_hec22 = f"$C${row}"
        r_ref_legacy = f"$D${row}"
        row += 1

        # Sf
        ws.cell(row=row, column=1, value="Sf = (Q*n/(1.486*A*R^(2/3)))^2")
        ws.cell(row=row, column=2, value=f"({Q}*{n}/(1.486*A*R^(2/3)))^2")
        ws.cell(row=row, column=3, value=f"=({Q}*{n}/(1.486*{area_ref_hec22}*{r_ref_hec22}^(2/3)))^2")
        ws.cell(row=row, column=4, value=f"=({Q}*{n}/(1.486*{area_ref_legacy}*{r_ref_legacy}^(2/3)))^2")
        sf_ref_hec22 = f"$C${row}"
        sf_ref_legacy = f"$D${row}"
        row += 1

        # Hf
        ws.cell(row=row, column=1, value="Hf = Sf * L")
        ws.cell(row=row, column=2, value=f"Sf * {L}")
        ws.cell(row=row, column=3, value=f"={sf_ref_hec22}*{L}")
        ws.cell(row=row, column=4, value=f"={sf_ref_legacy}*{L}")
        hf_ref_hec22 = f"$C${row}"
        hf_ref_legacy = f"$D${row}"
        row += 1

        # Crown_dn and Crown_up
        ws.cell(row=row, column=1, value="Crown_dn = Inv_dn + D/12")
        ws.cell(row=row, column=2, value=f"{inv_dn} + {D}/12")
        crown_dn = inv_dn + D / 12.0
        ws.cell(row=row, column=3, value=crown_dn)
        ws.cell(row=row, column=4, value=crown_dn)
        crown_dn_ref_hec22 = f"$C${row}"
        crown_dn_ref_legacy = f"$D${row}"
        row += 1

        ws.cell(row=row, column=1, value="Crown_up = Inv_up + D/12")
        ws.cell(row=row, column=2, value=f"{inv_up} + {D}/12")
        crown_up = inv_up + D / 12.0
        ws.cell(row=row, column=3, value=crown_up)
        ws.cell(row=row, column=4, value=crown_up)
        crown_up_ref_hec22 = f"$C${row}"
        crown_up_ref_legacy = f"$D${row}"
        row += 1

        # HGL_dn_raw
        ws.cell(row=row, column=1, value="HGL_dn_raw")
        if idx == 0:
            # First pipe (P-4, most d/s): HGL_dn_raw = TW
            ws.cell(row=row, column=2, value="= TW_input")
            ws.cell(row=row, column=3, value=f"={tw_cell}")
            ws.cell(row=row, column=4, value=f"={tw_cell}")
        else:
            # Subsequent: EGL_dn - Vh of this pipe. EGL_dn is computed below.
            # For clarity we show it as "see EGL_dn / Vh below" - compute directly:
            ws.cell(row=row, column=2, value="EGL_dn - Vh (this pipe)")
            # Reference: EGL_dn of this row is row+3 (we compute EGL_dn after Hb)
            # Simpler: just compute HGL_dn_raw directly from prev_egl_up + Hb(prev) - Vh(this)
            ws.cell(
                row=row, column=3,
                value=f"={prev_egl_up_hec22}+{prev_hb_hec22}-{vh_ref_hec22}"
            )
            ws.cell(
                row=row, column=4,
                value=f"={prev_egl_up_legacy}+{prev_hb_legacy}-{vh_ref_legacy}"
            )
        hgl_dn_raw_ref_hec22 = f"$C${row}"
        hgl_dn_raw_ref_legacy = f"$D${row}"
        row += 1

        # HGL_dn = MAX(HGL_dn_raw, Crown_dn)
        ws.cell(row=row, column=1, value="HGL_dn = MAX(HGL_dn_raw, Crown_dn)")
        ws.cell(row=row, column=2, value=f"MAX(HGL_dn_raw, {crown_dn:.2f})")
        ws.cell(row=row, column=3, value=f"=MAX({hgl_dn_raw_ref_hec22},{crown_dn_ref_hec22})")
        ws.cell(row=row, column=4, value=f"=MAX({hgl_dn_raw_ref_legacy},{crown_dn_ref_legacy})")
        hgl_dn_ref_hec22 = f"$C${row}"
        hgl_dn_ref_legacy = f"$D${row}"
        row += 1

        # EGL_dn = HGL_dn + Vh
        ws.cell(row=row, column=1, value="EGL_dn = HGL_dn + Vh")
        ws.cell(row=row, column=2, value="HGL_dn + Vh")
        ws.cell(row=row, column=3, value=f"={hgl_dn_ref_hec22}+{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_dn_ref_legacy}+{vh_ref_legacy}")
        egl_dn_ref_hec22 = f"$C${row}"
        egl_dn_ref_legacy = f"$D${row}"
        row += 1

        # HGL_up_raw = HGL_dn + Hf
        ws.cell(row=row, column=1, value="HGL_up_raw = HGL_dn + Hf")
        ws.cell(row=row, column=2, value="HGL_dn + Hf")
        ws.cell(row=row, column=3, value=f"={hgl_dn_ref_hec22}+{hf_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_dn_ref_legacy}+{hf_ref_legacy}")
        hgl_up_raw_ref_hec22 = f"$C${row}"
        hgl_up_raw_ref_legacy = f"$D${row}"
        row += 1

        # HGL_up: method-dependent (HEC-22 = HGL_up_raw; Legacy = MAX(HGL_up_raw, Crown_up))
        ws.cell(row=row, column=1, value="HGL_up")
        ws.cell(row=row, column=2, value="HEC-22: HGL_up_raw; Legacy: MAX(HGL_up_raw, Crown_up)")
        ws.cell(row=row, column=3, value=f"={hgl_up_raw_ref_hec22}")
        ws.cell(row=row, column=4, value=f"=MAX({hgl_up_raw_ref_legacy},{crown_up_ref_legacy})")
        hgl_up_ref_hec22 = f"$C${row}"
        hgl_up_ref_legacy = f"$D${row}"
        row += 1

        # EGL_up = HGL_up + Vh
        ws.cell(row=row, column=1, value="EGL_up = HGL_up + Vh")
        ws.cell(row=row, column=2, value="HGL_up + Vh")
        ws.cell(row=row, column=3, value=f"={hgl_up_ref_hec22}+{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_up_ref_legacy}+{vh_ref_legacy}")
        egl_up_ref_hec22 = f"$C${row}"
        egl_up_ref_legacy = f"$D${row}"
        row += 1

        # Kb lookup (uses Kb_Values table from Lookups)
        ws.cell(row=row, column=1, value=f"Kb = Kb_Values[Type={up_type},Angle={up_angle}]")
        ws.cell(row=row, column=2, value=f"lookup for type={up_type}, angle={up_angle}")
        if up_type == "outfall":
            kb_formula = "0"
        else:
            kb_col = {"inlet": "Inlet", "manhole": "Manhole",
                      "bend": "Bend", "junction": "Junction",
                      "splitter": "Manhole"}[up_type]
            kb_formula = f"XLOOKUP({up_angle},Kb_Values[Angle],Kb_Values[{kb_col}],0,-1)"
        ws.cell(row=row, column=3, value=f"={kb_formula}")
        ws.cell(row=row, column=4, value=f"={kb_formula}")
        kb_ref_hec22 = f"$C${row}"
        kb_ref_legacy = f"$D${row}"
        row += 1

        # Hb = Kb * Vh (this row's Vh - outflow pipe convention)
        ws.cell(row=row, column=1, value="Hb = Kb * Vh(this pipe)")
        ws.cell(row=row, column=2, value="Kb * Vh")
        ws.cell(row=row, column=3, value=f"={kb_ref_hec22}*{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={kb_ref_legacy}*{vh_ref_legacy}")
        hb_ref_hec22 = f"$C${row}"
        hb_ref_legacy = f"$D${row}"
        row += 1

        # Save state for next (upstream) pipe
        prev_egl_up_hec22 = egl_up_ref_hec22
        prev_egl_up_legacy = egl_up_ref_legacy
        prev_hb_hec22 = hb_ref_hec22
        prev_hb_legacy = hb_ref_legacy

        # Spacer row between blocks
        row += 2

    # Try-this experiments at the bottom
    ws.cell(row=row, column=1, value="TRY THIS:")
    row += 1
    experiments = [
        "Raise TW (C3) to 100.0 - all HGL rise by at least 3 ft; HEC-22 and Legacy give identical results (no gravity reaches).",
        "Lower TW (C3) to 93.00 - P-4 switches to 'Gravity' regime; HGL_dn pins at Crown_dn (96.00) under both methods.",
        "Lower TW to 93.00 AND watch P-3/P-2/P-1 - Legacy column may diverge from HEC-22 if HGL_up_raw drops below Crown_up for any upstream pipe.",
        "Change HGL_Method in Config - the C column keeps HEC-22; the D column shows Legacy. Both are always computed here for teaching.",
    ]
    for exp in experiments:
        ws.cell(row=row, column=1, value=exp)
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
```

- [ ] **Step 3: Wire into workbook.py**

```python
from bburg_template_builder.sheets.hgl_example import build_hgl_example_sheet
# ...
build_hgl_example_sheet(wb)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/test_hgl_example.py -v`

Expected: all PASS.

- [ ] **Step 5: Manual Excel check and cross-check against reference_calcs**

Run: `python drainage-calculator/build_bburg_template.py`
Open the template in Excel. Navigate to HGL_Example.
- At TW=97.00 (default), P-4's HGL_dn should be 97.00 (pressurized; TW > Crown_dn=96.00).
- At P-4, HEC-22 HGL_up should equal Legacy HGL_up (both 97.142 ft per the reference_calcs spot-check).
- Lower TW to 93.00; P-4's HGL_dn pins at 96.00 (Crown_dn).
- Compare the final HGL_up at P-1 between HEC-22 and Legacy columns; divergence confirms the method toggle is live.

Also run a Python cross-check:

```python
# From repo root: python -c "..."
python -c "
from bburg_template_builder.reference_calcs import manning_sf_full, velocity_head, hgl_walk_step
# P-4: D=24, Q=9.5
import math
A = math.pi * (24/12)**2 / 4
V = 9.5 / A
sf = manning_sf_full(9.5, 0.013, 24)
hf = sf * 80
print(f'Pipe P-4: V={V:.3f} Vh={velocity_head(V):.4f} Sf={sf:.5f} Hf={hf:.4f}')
hgl_dn, hgl_up = hgl_walk_step(97.0, 96.0, 96.56, hf, 'hec22')
print(f'HEC-22: HGL_dn={hgl_dn:.3f} HGL_up={hgl_up:.3f}')
"
```

Expected console output: `V=3.024 Vh=0.142 Sf=0.00178 Hf=0.1428` and `HEC-22: HGL_dn=97.000 HGL_up=97.143`. The Excel cells should match to 3 decimal places.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/bburg_template_builder/sheets/hgl_example.py \
        drainage-calculator/bburg_template_builder/tests/test_hgl_example.py \
        drainage-calculator/bburg_template_builder/workbook.py
git commit -m "feat(bburg-template): HGL_Example educational sheet with side-by-side method comparison"
```

---

## Task 14: User guide + golden file verification

**Files:**
- Create: `docs/bburg-xlsx-user-guide.md`
- Modify: `drainage-calculator/bburg_template_builder/tests/test_end_to_end.py` (final golden-file assertions)

- [ ] **Step 1: Create the user guide**

Create `docs/bburg-xlsx-user-guide.md`:

```markdown
# bburg-p-c Storm-Drain Template — User Guide

**File:** `docs/bburg-p-c-template.xlsx`
**Regenerated by:** `python drainage-calculator/build_bburg_template.py`
**Legacy file:** `docs/bburg-p-c-legacy.xlsx` (kept for historical reference only)

## Quick start

1. Open `docs/bburg-p-c-template.xlsx` in Excel 365.
2. Go to `Config` and set:
   - `County_Selected` — pick from the dropdown (Montgomery, Prince George's, DC, or any other MD county you've populated in `NOAA14`).
   - `Storm_Primary` — the design storm (`2yr`, `10yr`, `25yr`, `100yr`, ...).
   - `HGL_Method` — `HEC-22 EGL (d/s crown floor)` (default) or `Legacy both-end crown floor` for firms expecting prior convention.
3. Fill in `DA_Catchments` with one row per drainage sub-area:
   - `Inlet_ID` must match a `Structure_ID` on the `Structures` sheet.
   - `Landuse` dropdown auto-fills `C_2-10` and `C_25` via XLOOKUP; override values are fine.
4. Fill in `Structures`:
   - One row per physical structure (inlet, manhole, bend, junction, splitter, outfall).
   - `Type` dropdown controls which Kb column is read.
   - `Angle_deg` is the deflection between inflow and outflow (0 for straight-through).
5. Fill in `Pipes`:
   - `From_Structure` / `To_Structure` dropdowns reference `Structures[Structure_ID]`.
   - `Material` dropdown auto-defaults `Manning_n`; override values are fine.
6. Go to `HGL`:
   - Set `TW_Elev_Start` (cell C3) to the tailwater elevation at the most-downstream pipe.
   - Type `Pipe_ID`s in column A in **downstream-first** order (row 10 = most d/s pipe; last row = most u/s pipe).
   - Every other column auto-computes.
7. Check the `Crown_check` and `Rim_check` columns for FAIL flags.

## Sheet reference

- **Config** — all workbook-wide settings. Named ranges here are referenced throughout.
- **NOAA14** — rainfall depths (in) for every MD county + DC by storm and duration. Populated for MoCo / PG / DC; other counties are blank (fill in per project).
- **IDF_Lookup** — rainfall intensity (in/hr) vs Tc, driven by `County_Selected`. Readable by all other sheets via `XLOOKUP`.
- **Landuse_Lookup** — landuse → C value map.
- **Pipe_Properties** — size, area, perimeter, hydraulic radius per pipe diameter.
- **Kb_Values** — MCDrainage Kb coefficients by angle × structure type (inlet / manhole / bend / junction).
- **DA_Catchments** — long-form source of truth for drainage areas. One row per (Inlet, DA).
- **Structures** — one row per physical structure.
- **Pipes** — one row per pipe reach.
- **Rationals-MCDOT** — Rational Method calc-sheet view, per-inlet blocks auto-filled from DA_Catchments.
- **Inlet Spacing_10-yr / _2-yr** — legacy inlet spread sheets rewired to the long table.
- **10 Yr / 25 Yr Pipe Capacity** — Rational Method pipe-by-pipe (capacity sizing).
- **HGL** — generalized HGL/EGL walker with method toggle.
- **HGL_Example** — educational sheet, both methods side-by-side. Not for real design.

## HGL methods explained

Both methods share: full-flow Manning's Sf at design Q, crown floor on HGL_dn, Hb computed using the outflow pipe's velocity head.

**HEC-22 EGL (d/s crown floor)** — DEFAULT. Standard HEC-22 textbook procedure (MDSHA, PG, MoCo all accept this). `HGL_up = HGL_dn + Hf`; no upstream crown floor.

**Legacy both-end crown floor** — Matches the behavior of the existing (broken) `10 Yr MoCo HGL` sheet in the legacy workbook. Also pins `HGL_up` at `Crown_up` if it would otherwise fall below it. More conservative; preserved for projects where reviewers expect the prior firm convention.

See `HGL_Example` for a side-by-side worked example.

## Starting tailwater

The `TW_Elev_Start` cell on the HGL sheet seeds the walk. Common choices:

- **Free discharge** — set TW = soffit of the last pipe (Inv_dn + D/12).
- **Fixed TW** — type the known elevation from an external pond analysis (HydroCAD, hand-calc, HTML calculator's rating curve).
- **Linked to pond** — if your `Structures` row for the outfall has a `Linked_Pond_TW` value, HGL uses that.

## Troubleshooting

- `#REF!` appearing anywhere → re-run the builder: `python drainage-calculator/build_bburg_template.py`.
- `#N/A` on HGL row for a pipe you just added → check the `Pipe_ID` is in the `Pipes` table.
- `#VALUE!` on intensity cell → check `County_Selected` has NOAA14 depths populated.
- HGL walking the wrong direction → verify pipes are listed downstream-first on the HGL sheet.

## Regenerating

```bash
cd <repo root>
python drainage-calculator/build_bburg_template.py
# Output: docs/bburg-p-c-template.xlsx
```

Tests:

```bash
python -m pytest drainage-calculator/bburg_template_builder/tests/ -v
```
```

- [ ] **Step 2: Write final end-to-end golden-file test**

Modify `drainage-calculator/bburg_template_builder/tests/test_end_to_end.py` — append:

```python
def test_bladensburg_seed_drives_rationals_block_1(built_wb):
    """Spot-check: Rationals block 1 has Area = sum of DA-1a + DA-1b."""
    rationals = built_wb["Rationals-MCDOT"]
    # Block 1 TOTALS row = 20, Area column = D (4)
    formula = str(rationals.cell(row=20, column=4).value)
    assert "SUMIFS" in formula and "DA_Catchments" in formula


def test_no_hard_coded_rationals_refs_anywhere(built_wb):
    """Guard against regressions: no sheet except Rationals-MCDOT may use `='Rationals-MCDOT'!A1` style refs.

    Allowed: structured table refs like `DA_Catchments[Area_SF]`.
    Forbidden: A1-style like `='Rationals-MCDOT'!D20`.
    """
    import re
    forbidden = re.compile(r"'Rationals-MCDOT'![A-Z]+\d+(?!:)")
    for sheet_name in built_wb.sheetnames:
        if sheet_name == "Rationals-MCDOT":
            continue
        ws = built_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    hits = forbidden.findall(cell.value)
                    assert not hits, (
                        f"{sheet_name} {cell.coordinate}: hard-coded Rationals ref: {cell.value}"
                    )


def test_no_ref_errors_anywhere(built_wb):
    """Guard against any #REF!/#NAME? baked into the builder output."""
    for sheet_name in built_wb.sheetnames:
        ws = built_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    assert "#REF" not in cell.value, f"{sheet_name} {cell.coordinate}: {cell.value}"
                    assert "#NAME" not in cell.value, f"{sheet_name} {cell.coordinate}: {cell.value}"


def test_build_script_produces_output_file(tmp_path, monkeypatch):
    """Running build_bburg_template.py as a subprocess produces docs/bburg-p-c-template.xlsx."""
    import subprocess
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "drainage-calculator" / "build_bburg_template.py"
    output = repo_root / "docs" / "bburg-p-c-template.xlsx"
    # Clean pre-existing output for a clean check
    if output.exists():
        output.unlink()
    result = subprocess.run([sys.executable, str(script)],
                            capture_output=True, text=True, cwd=str(repo_root))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert output.exists()
```

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest drainage-calculator/bburg_template_builder/tests/ -v`

Expected: all tests PASS.

- [ ] **Step 4: Build the final template**

Run: `python drainage-calculator/build_bburg_template.py`

Expected: `docs/bburg-p-c-template.xlsx` created with no errors.

- [ ] **Step 5: Manual Excel smoke test (final golden check)**

Open `docs/bburg-p-c-template.xlsx` in Excel 365. Verify:

1. **No repair prompt** on open.
2. **No `#REF!`, `#NAME?`, `#VALUE!`** on any sheet (scroll each).
3. **Config dropdowns** work: click County_Selected cell, dropdown shows MoCo/PG/DC/other MD counties.
4. **DA_Catchments**: typing a Landuse in E12 auto-fills columns G & H.
5. **Rationals-MCDOT Block 1**: shows `EX-I-1`, Area = 2394.28, Composite C ≈ 0.849.
6. **HGL sheet**: type `P-2` in A10 and `P-1` in A11; all other columns compute. Set TW=65; walk propagates upstream.
7. **HGL_Example**: TW=97.00 → P-4 HEC-22 HGL_up ≈ 97.142 ft; set TW=93 → P-4 HGL_dn pins at 96.00.
8. **Toggle HGL_Method** in Config between HEC-22 and Legacy — HGL column values on gravity reaches change; pressurized reaches don't.

If any check fails, fix the relevant sheet module and re-run `python drainage-calculator/build_bburg_template.py`.

- [ ] **Step 6: Commit**

```bash
git add docs/bburg-xlsx-user-guide.md \
        docs/bburg-p-c-template.xlsx \
        drainage-calculator/bburg_template_builder/tests/test_end_to_end.py
git commit -m "docs(bburg-template): user guide, golden-file test, built template artifact"
```

- [ ] **Step 7: Final sanity re-build + commit if the built file changed**

Run: `python drainage-calculator/build_bburg_template.py && git status`

If `docs/bburg-p-c-template.xlsx` shows as modified (byte-level changes from re-run), include it in a follow-up commit:

```bash
git add docs/bburg-p-c-template.xlsx
git commit -m "chore(bburg-template): regenerate built template"
```

---

## Plan complete

Plan complete and saved to `docs/superpowers/plans/2026-11-06-bburg-xlsx-redesign.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

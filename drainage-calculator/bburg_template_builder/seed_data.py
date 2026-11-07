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

# --- Kb values (MCDrainage). Full table angles 0..90 extracted from
# docs/bburg-p-c-legacy.xlsx (sheet 'Kb Values MoCo', rows 2..92). ---
# Shape: (Angle, Inlet, Manhole, Bend, Junction). Junction == Bend per MCDrainage / HTML calc.
KB_VALUES: Final[tuple[tuple[int, float, float, float, float], ...]] = tuple(
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
        (13, 0.62, 0.34, 0.07),
        (14, 0.62, 0.34, 0.07),
        (15, 0.63, 0.35, 0.08),
        (16, 0.64, 0.36, 0.08),
        (17, 0.65, 0.38, 0.09),
        (18, 0.66, 0.39, 0.09),
        (19, 0.67, 0.40, 0.09),
        (20, 0.68, 0.42, 0.10),
        (21, 0.69, 0.43, 0.10),
        (22, 0.70, 0.44, 0.11),
        (23, 0.71, 0.46, 0.11),
        (24, 0.73, 0.47, 0.11),
        (25, 0.74, 0.48, 0.12),
        (26, 0.76, 0.50, 0.12),
        (27, 0.78, 0.51, 0.13),
        (28, 0.80, 0.52, 0.13),
        (29, 0.82, 0.54, 0.13),
        (30, 0.83, 0.55, 0.14),
        (31, 0.85, 0.56, 0.14),
        (32, 0.87, 0.58, 0.14),
        (33, 0.89, 0.59, 0.14),
        (34, 0.90, 0.60, 0.14),
        (35, 0.92, 0.62, 0.15),
        (36, 0.94, 0.63, 0.15),
        (37, 0.96, 0.64, 0.16),
        (38, 0.98, 0.66, 0.16),
        (39, 0.99, 0.67, 0.16),
        (40, 1.01, 0.68, 0.17),
        (41, 1.03, 0.70, 0.17),
        (42, 1.05, 0.71, 0.17),
        (43, 1.06, 0.72, 0.17),
        (44, 1.08, 0.74, 0.18),
        (45, 1.10, 0.75, 0.18),
        (46, 1.11, 0.76, 0.18),
        (47, 1.12, 0.76, 0.19),
        (48, 1.13, 0.77, 0.19),
        (49, 1.14, 0.78, 0.19),
        (50, 1.15, 0.78, 0.19),
        (51, 1.16, 0.79, 0.19),
        (52, 1.17, 0.80, 0.19),
        (53, 1.18, 0.80, 0.19),
        (54, 1.19, 0.81, 0.20),
        (55, 1.20, 0.82, 0.20),
        (56, 1.21, 0.82, 0.20),
        (57, 1.22, 0.83, 0.20),
        (58, 1.23, 0.84, 0.20),
        (59, 1.24, 0.84, 0.20),
        (60, 1.25, 0.85, 0.20),
        (61, 1.26, 0.85, 0.20),
        (62, 1.27, 0.86, 0.20),
        (63, 1.27, 0.86, 0.20),
        (64, 1.28, 0.87, 0.20),
        (65, 1.29, 0.87, 0.20),
        (66, 1.30, 0.88, 0.21),
        (67, 1.31, 0.88, 0.21),
        (68, 1.32, 0.89, 0.21),
        (69, 1.32, 0.89, 0.21),
        (70, 1.33, 0.90, 0.21),
        (71, 1.34, 0.91, 0.21),
        (72, 1.35, 0.91, 0.21),
        (73, 1.36, 0.91, 0.21),
        (74, 1.37, 0.92, 0.22),
        (75, 1.37, 0.92, 0.22),
        (76, 1.38, 0.93, 0.22),
        (77, 1.39, 0.93, 0.22),
        (78, 1.40, 0.94, 0.22),
        (79, 1.41, 0.94, 0.22),
        (80, 1.42, 0.95, 0.23),
        (81, 1.42, 0.95, 0.23),
        (82, 1.43, 0.96, 0.23),
        (83, 1.44, 0.96, 0.23),
        (84, 1.45, 0.97, 0.24),
        (85, 1.46, 0.97, 0.24),
        (86, 1.47, 0.98, 0.24),
        (87, 1.47, 0.98, 0.24),
        (88, 1.49, 0.99, 0.25),
        (89, 1.49, 0.99, 0.25),
        (90, 1.50, 1.00, 0.25),
    ]
)

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
# Values transcribed from docs/bburg-p-c-legacy.xlsx (10-yr MoCo design):
#   DA_Catchments  <- 'Inlet Spacing_10-yr' cols D (area, ac) and E (composite C)
#   Structures     <- '10 Yr Pipe Capacity' P/Q (inverts), R (rim of FROM structure);
#                     bend angles from ' 10 Yr MoCo HGL' T (0, 9, 4 deg)
#   Pipes          <- '10 Yr Pipe Capacity' rows 14-27 (S length, T slope, M size, L design Q)
# The legacy workbook has no 25-yr composite C, so C_25 mirrors C_2-10.
BLADENSBURG_DA_CATCHMENTS: Final[tuple[dict, ...]] = (
    {"Inlet_ID": "EX-I-1", "DA_ID": "DA-EX-I-1", "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF":  2394.28, "C_2_10": 0.849075, "C_25": 0.849075},
    {"Inlet_ID": "EX-I-2", "DA_ID": "DA-EX-I-2", "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF": 87717.64, "C_2_10": 0.582121, "C_25": 0.582121},
    {"Inlet_ID": "I-1",    "DA_ID": "DA-I-1",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF":  8098.19, "C_2_10": 0.768553, "C_25": 0.768553},
    {"Inlet_ID": "I-2",    "DA_ID": "DA-I-2",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF":  9336.52, "C_2_10": 0.840410, "C_25": 0.840410},
    {"Inlet_ID": "I-3",    "DA_ID": "DA-I-3",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF": 14440.27, "C_2_10": 0.558810, "C_25": 0.558810},
    {"Inlet_ID": "I-4",    "DA_ID": "DA-I-4",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF":  3359.35, "C_2_10": 0.869775, "C_25": 0.869775},
    {"Inlet_ID": "I-5",    "DA_ID": "DA-I-5",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF": 28993.14, "C_2_10": 0.654185, "C_25": 0.654185},
    {"Inlet_ID": "I-6",    "DA_ID": "DA-I-6",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF": 11222.62, "C_2_10": 0.608173, "C_25": 0.608173},
    {"Inlet_ID": "I-7",    "DA_ID": "DA-I-7",    "Soil": "---", "Slope": "---", "Landuse": "---", "Area_SF": 107173.37, "C_2_10": 0.577885, "C_25": 0.577885},
)

BLADENSBURG_STRUCTURES: Final[tuple[dict, ...]] = (
    {"Structure_ID": "I-3",       "Type": "inlet",   "Description": "Inlet I-3",             "Rim_Elev": 313.12, "Inv_In_Elev": 70.0000, "Inv_Out_Elev": 70.0000, "Angle_deg": 0},
    {"Structure_ID": "MH-3",      "Type": "manhole", "Description": "Manhole MH-3",          "Rim_Elev": 300.00, "Inv_In_Elev": 69.7700, "Inv_Out_Elev": 69.6700, "Angle_deg": 0},
    {"Structure_ID": "MH-2",      "Type": "manhole", "Description": "Manhole MH-2",          "Rim_Elev": 300.00, "Inv_In_Elev": 69.1100, "Inv_Out_Elev": 69.0100, "Angle_deg": 0},
    {"Structure_ID": "I-1",       "Type": "inlet",   "Description": "Inlet I-1",             "Rim_Elev": 314.19, "Inv_In_Elev": 68.5100, "Inv_Out_Elev": 68.5100, "Angle_deg": 0},
    {"Structure_ID": "I-2",       "Type": "inlet",   "Description": "Inlet I-2",             "Rim_Elev": 313.18, "Inv_In_Elev": 68.3000, "Inv_Out_Elev": 68.2000, "Angle_deg": 9},
    {"Structure_ID": "EX-I-2",    "Type": "inlet",   "Description": "Existing inlet EX-I-2", "Rim_Elev": 313.18, "Inv_In_Elev": 67.4600, "Inv_Out_Elev": 67.4600, "Angle_deg": 0},
    {"Structure_ID": "MH-1",      "Type": "manhole", "Description": "Manhole MH-1",          "Rim_Elev": 315.21, "Inv_In_Elev": 67.4000, "Inv_Out_Elev": 67.3000, "Angle_deg": 0},
    {"Structure_ID": "EX-I-1",    "Type": "inlet",   "Description": "Existing inlet EX-I-1", "Rim_Elev": 312.48, "Inv_In_Elev": 67.1000, "Inv_Out_Elev": 67.0000, "Angle_deg": 0},
    {"Structure_ID": "I-7",       "Type": "inlet",   "Description": "Inlet I-7",             "Rim_Elev": 312.08, "Inv_In_Elev": 67.1000, "Inv_Out_Elev": 67.1000, "Angle_deg": 0},
    {"Structure_ID": "CULVERT-A", "Type": "outfall", "Description": "Outfall culvert A",     "Rim_Elev":  68.87, "Inv_In_Elev": 66.8700, "Inv_Out_Elev": 66.8700, "Angle_deg": 0},
    {"Structure_ID": "I-6",       "Type": "inlet",   "Description": "Inlet I-6",             "Rim_Elev": 313.37, "Inv_In_Elev": 72.4100, "Inv_Out_Elev": 72.4100, "Angle_deg": 0},
    {"Structure_ID": "I-5",       "Type": "inlet",   "Description": "Inlet I-5",             "Rim_Elev": 313.37, "Inv_In_Elev": 72.0900, "Inv_Out_Elev": 71.9900, "Angle_deg": 0},
    {"Structure_ID": "I-4",       "Type": "inlet",   "Description": "Inlet I-4",             "Rim_Elev": 308.27, "Inv_In_Elev": 71.4100, "Inv_Out_Elev": 71.3677, "Angle_deg": 4},
    {"Structure_ID": "CULVERT-B", "Type": "outfall", "Description": "Outfall culvert B",     "Rim_Elev":  72.54, "Inv_In_Elev": 71.0400, "Inv_Out_Elev": 71.0400, "Angle_deg": 0},
)

BLADENSBURG_PIPES: Final[tuple[dict, ...]] = (
    {"Pipe_ID": "p1",  "From_Structure": "I-3",       "To_Structure": "MH-3",      "Length_ft": 23.41, "Size_in": 12, "Material": "RCP", "Slope_ftft": 0.009824, "Design_Q_cfs": 0.989219, "Chain": "A"},
    {"Pipe_ID": "p2",  "From_Structure": "MH-3",      "To_Structure": "MH-2",      "Length_ft": 56.27, "Size_in": 12, "Material": "RCP", "Slope_ftft": 0.009952, "Design_Q_cfs": 0.995147, "Chain": "A"},
    {"Pipe_ID": "p3",  "From_Structure": "MH-2",      "To_Structure": "I-2",       "Length_ft": 71.21, "Size_in": 12, "Material": "RCP", "Slope_ftft": 0.009971, "Design_Q_cfs": 1.007003, "Chain": "A"},
    {"Pipe_ID": "p4",  "From_Structure": "I-1",       "To_Structure": "I-2",       "Length_ft": 21.53, "Size_in": 12, "Material": "RCP", "Slope_ftft": 0.009754, "Design_Q_cfs": 0.953061, "Chain": "A"},
    {"Pipe_ID": "p5",  "From_Structure": "I-2",       "To_Structure": "MH-1",      "Length_ft": 80.02, "Size_in": 15, "Material": "RCP", "Slope_ftft": 0.009998, "Design_Q_cfs": 3.395725, "Chain": "A"},
    {"Pipe_ID": "p6",  "From_Structure": "EX-I-2",    "To_Structure": "MH-1",      "Length_ft":  5.92, "Size_in": 21, "Material": "RCP", "Slope_ftft": 0.010135, "Design_Q_cfs": 6.259696, "Chain": "A"},
    {"Pipe_ID": "p7",  "From_Structure": "MH-1",      "To_Structure": "EX-I-1",    "Length_ft": 19.61, "Size_in": 24, "Material": "RCP", "Slope_ftft": 0.010199, "Design_Q_cfs": 8.973837, "Chain": "A"},
    {"Pipe_ID": "p8",  "From_Structure": "EX-I-1",    "To_Structure": "CULVERT-A", "Length_ft": 14.36, "Size_in": 24, "Material": "RCP", "Slope_ftft": 0.010000, "Design_Q_cfs": 11.261105, "Chain": "A"},
    {"Pipe_ID": "p9",  "From_Structure": "I-7",       "To_Structure": "CULVERT-A", "Length_ft": 23.2878, "Size_in": 24, "Material": "RCP", "Slope_ftft": 0.009876, "Design_Q_cfs": 7.592448, "Chain": "A"},
    {"Pipe_ID": "p10", "From_Structure": "I-6",       "To_Structure": "I-5",       "Length_ft": 32.03, "Size_in": 12, "Material": "RCP", "Slope_ftft": 0.009991, "Design_Q_cfs": 0.836709, "Chain": "B"},
    {"Pipe_ID": "p11", "From_Structure": "I-5",       "To_Structure": "I-4",       "Length_ft": 29.56, "Size_in": 18, "Material": "RCP", "Slope_ftft": 0.019621, "Design_Q_cfs": 3.860538, "Chain": "B"},
    {"Pipe_ID": "p12", "From_Structure": "I-4",       "To_Structure": "CULVERT-B", "Length_ft": 32.31, "Size_in": 18, "Material": "RCP", "Slope_ftft": 0.010142, "Design_Q_cfs": 4.396757, "Chain": "B"},
)

# Downstream-first walk order for the HGL sheet: both CULVERT-A reaches first, then the
# trunk back upstream, then the Chain B branch.
BLADENSBURG_HGL_ORDER: Final[tuple[str, ...]] = (
    "p8", "p9", "p7", "p6", "p5", "p4", "p3", "p2", "p1",
    "p12", "p11", "p10",
)

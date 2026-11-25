# MCDOT INLET COMPS-DESIGN

## Purpose

MCDOT submittal form that presents inlet hydraulics computations — drainage area, A×C products, incremental intensity, incremental Q, and adjusted captured flow — for each inlet row in the project.

## Headers & ranges

Occupied range: rows 1–30, columns A–U (30 rows × 21 cols). One Table object: **Table2** at `A3:U26`. Row 3 is the Table2 header row. Data rows run from row 4 through row 26 (23 data rows). Rows 27–30 hold footer labels: D27 concatenates the project storm title + " INLET COMPUTATIONS" and D29 echoes `STORM DRAIN COMPS`!A1 (project name).

## Inputs

- `A4:A26` — From-structure ID (user-typed row key). Columns B–F reference this via Table2 structured refs and INDEX/MATCH into STORM DRAIN COMPS Table4.
- `J4:J26` — Lateral or additional inlet ID (user-typed); used by column G lookups against column I within the same table.
- `O4:O26` — Inlet efficiency or capture fraction (user-typed); used by column P to compute uncaptured flow.

No dropdown sources on this sheet.

## Formulas

### Columns B–F: Area, A×C, and intensity pulls from C_FACTOR and STORM DRAIN COMPS

- `B4` Drainage area (ac) → `INDEX(C_FACTOR!$D$6:$D$88, MATCH($A4, C_FACTOR!$B$6:$B$88, 0))` with ISNA guard — pulls incremental drainage area from C_FACTOR col D keyed on From-structure ID; engineering-methodology.md §1 `A` term
- `C4` A×C Increm → `INDEX('STORM DRAIN COMPS'!$F$10:$F$97, MATCH(Table2[Column1], Table4[Column1], 0))` — incremental A×C product from SDC col F; §1 `A×C` incremental
- `D4` Tc (min) → `INDEX('STORM DRAIN COMPS'!$E$10:$E$97, ...)` — Tc to inlet from SDC col E; §2 time-of-concentration
- `E4` Rain Inten Increm (in/hr) → `INDEX('STORM DRAIN COMPS'!$G$10:$G$97, ...)` — incremental rainfall intensity from SDC col G (IDF lookup for inlet Tc); §1 `i` term
- `F4` Q Increm (cfs) → `INDEX('STORM DRAIN COMPS'!$H$10:$H$97, ...)` — incremental peak flow from SDC col H; §1 `Q = C × i × A` incremental

### Column G: Lateral flow lookup (within-table)

- `G4` Lateral Q (cfs) → `IFERROR(INDEX($I$4:$I$26, MATCH($A4, $J$4:$J$26, 0)), 0)` — looks up column I (another incremental Q slot) against column J (lateral inlet ID) within the same table; routes lateral inflow contributions to the main-line inlet row

### Column H: Combined incremental flow

- `H4` A×C + Lateral → `Table2[Column10] + Table2[Column9]` — sum of the SDC-derived A×C (col C) and the lateral flow (col G); produces combined incremental flow for this inlet

### Column I: Adjusted flow after capture

- `I4` Captured Q (cfs) → `Table2[Column11] - (Table2[Column192] * Table2[Column11])` — applies inlet efficiency (col O via Column192 structured ref) to reduce incremental Q: `Q_captured = Q_increm × (1 − efficiency)`

### Column P: Bypassed (uncaptured) flow

- `P4` Bypassed Q (cfs) → `IF(O4="", "", (1 - O4) * F4)` — flow that bypasses the inlet and continues downstream: `Q_bypass = Q_increm × (1 − efficiency)`

Columns J–N and Q–U are user-typed fields (inlet geometry or supplementary design data) with no formulas per `pass_a.json`.

## Outputs

No other sheet reads from MCDOT INLET COMPS-DESIGN per `pass_a.json` cross_sheet_refs. This is a leaf-node submittal form.

## Dependencies

| Source sheet | Columns pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS (via Table4) | F (A×C Increm), E (Tc), G (Rain Inten Increm), H (Q Increm) | From-structure ID (col A) via Table2/Table4 structured refs |
| C_FACTOR | D (drainage area) | From-structure ID (col A) via INDEX/MATCH |

Note: despite the task guidance mentioning INLET SPACING as a source, `pass_a.json` cross_sheet_refs shows only `C_FACTOR` and `STORM DRAIN COMPS` — INLET SPACING is not read by this sheet.

## Issues found

None — MCDOT INLET COMPS-DESIGN has 0 `#REF!` errors per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

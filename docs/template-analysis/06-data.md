# DATA

## Purpose

Static source-data sheet holding IDF intensity tables for three jurisdictions, Kb junction-loss lookup table, and dropdown-source lists consumed by data-validation rules across the workbook.

## Headers & ranges

Occupied range: `A1:Z159`. No Table objects — plain cells. Rows 1–7 hold labels and dropdown source lists. Row 8 is a combined header/first-data row for the IDF blocks. Data rows: 8–63 (IDF, 56 Tc increments from 5 min to 60 min). Rows 64–159 hold the Kb lookup table (96 rows, angle × structure-type matrix; consumed by `STORM DRAIN COMPS` column AE formula).

## Inputs

All cells on this sheet are static user-typed reference data — no formulas (formula_count = 0 per `pass_a.json`).

### Dropdown source lists (rows 1–7)

- `C1:C4` — Jurisdiction selector source: `"Select Jurisdiction"`, `"Montgomery County"`, `"Prince George's County"`, `"District of Columbia"`. Bound to workbook defined names `Select_County` and `SelectCounty` (duplicate — see Issues).
- `A1:A4` — Structure type dropdown source (used by workbook-scoped data validation on STORM DRAIN COMPS column AA).
- `S13:S18` — Inlet type selector source: `"SELECT INLET TYPE"`, `"GRATE"`, `"CURB OPENING"`, `"COMBINATION"`, and two additional values. Bound to defined name `SELECT_INLET_TYPE`.
- `V13:V15` — Grade/sump selector source: `"SELECT AT GRADE OR IN SUMP"`, `"AT GRADE"`, `"IN SUMP"`. Bound to defined name `SELECT_AT_GRADE_OR_IN_SUMP`.

### IDF tables

**Montgomery County (MoCo) — columns C–H, rows 8–63:**
- `A8:A63` — Tc values (min), 5 through 60 (integer increments).
- `C8:H63` — Rainfall intensity i (in/hr) for return periods 2, 5, 10, 25, 50, 100 yr.
- Row 7 (or 8) holds the return-period header; `StormFrequency` defined name resolves to this header row for the MATCH lookup used in STORM DRAIN COMPS column G and L.

**Prince George's County (PG) — columns J–Q, rows 8–63:**
- `J8:J63` — Tc values (min) for PG block.
- `L8:Q63` — PG IDF intensities for the same six return periods.

**District of Columbia (DC) — columns S–X, rows 8–63:**
- `S8:S63` (or similar) — Tc values for DC block.
- `U8:X63` — DC IDF intensities. `StormFrequencyDC` defined name resolves to the DC return-period header row (`T7:X7` per pass_a.json guidance).

### Kb lookup table (rows 64–159)

- `A64:A159` — Pipe entry angle (degrees; 0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 180, and interpolation rows).
- `A64:D64` — Header row listing structure types (Inlet, Manhole, Junction, Bend / Flow Splitter, Outfall).
- `A65:D159` — Kb coefficient values per angle × structure-type combination. Consumed by `STORM DRAIN COMPS`!AE via `INDEX(DATA!$A$68:$D$159, MATCH(angle, DATA!$A$68:$A$159, 0), MATCH(type, DATA!$A$68:$D$68, 0))`.

## Formulas

No formulas — DATA is static reference data.

## Outputs

| Consumer sheet | Data used | Lookup mechanism |
|---|---|---|
| STORM DRAIN COMPS col G, L | MoCo / PG / DC IDF intensity | INDEX/MATCH on Tc (col A) and return period (row 7 header) keyed by jurisdiction from `Select_County` |
| HGL(25YEAR) col T | 25-year IDF intensity | Same INDEX/MATCH into the 25-year column |
| STORM DRAIN COMPS col AE | Kb coefficient | INDEX/MATCH on controlling angle (col A) × structure type (row 64 header) |
| INLET SPACING col J | IDF intensity | Same INDEX/MATCH pattern as STORM DRAIN COMPS |
| All sheets with jurisdiction/storm dropdowns | `C1:C4`, `A1:A4`, `S13:S18`, `V13:V15` | Excel data-validation list references via defined names |

## Dependencies

None — DATA reads no other sheet. It is a pure source.

## Issues found

1. **Low** — Duplicate defined names `Select_County` and `SelectCounty` both resolve to `DATA!$C$1:$C$4`. All live formulas reference `Select_County`; `SelectCounty` is an unused alias.
2. **Medium** — 25 broken defined names (`\0`, `\c`, `\e`, `\p`, `\r`, `_DUR1` through `_DUR18`, `_INT1`, `_INT2`) resolve to `#REF!`. These are orphans from the legacy template predecessor. No formula in the current workbook references any of them, so they cause no functional breakage — only namespace clutter.

## Fix plan

1. Issue 1 → **R4** (delete `SelectCounty`; keep `Select_County`). Implemented in Task 13 via `repair.py`.
2. Issue 2 → **R3** (remove all 25 orphan defined names). Implemented in Task 13 via `repair.py`.

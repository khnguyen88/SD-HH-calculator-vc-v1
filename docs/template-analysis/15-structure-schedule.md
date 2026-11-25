# STRUCTURE SCHEDULE

## Purpose

Hand-maintained printable tabulation of the drainage structure inventory for drawing submission; auto-populates structure IDs from C_FACTOR so the schedule label column stays in sync with the inlet row IDs.

## Headers & ranges

Occupied range: rows 1–52, 19 columns. No Table objects — plain cells. Row 1 is the sheet title. Row 2 is the column-header row. Data rows: 3–52 (50 structure rows). Per MCDOT §4.2.4(h), each row documents one drainage structure.

## Inputs

User-typed cells (all columns except B which is formula-driven for the first 6 rows):
- `C3:C52` — Structure type (e.g., Inlet, Manhole, Junction Box, Headwall)
- `D3:D52` — Agency and standard number (e.g., MCDOT Std. No. 400.03)
- `E3:E52` — Station
- `F3:F52` — Location description (e.g., "Back of curb, NW corner…")
- `G3:G52` — Structure size (e.g., 4'×4', 6'×6', or pipe diameter)
- `H3:H52` — Top elevation (rim or grate elevation, ft)
- `I3:I52` through the remaining columns — Invert elevations, slot elevation, modification notes, pre-cast standard number, supplier, and remarks (exact column semantics are user-maintained per plan set convention)

Dropdown sources: none on this sheet.

Workbook-scoped named ranges read: none.

## Formulas

6 formulas in column B, rows 3–8 — direct reference pulls from C_FACTOR:

- `B3` → `=C_FACTOR!B9` — Structure Row ID (from C_FACTOR inlet ID column B, row 9)
- `B4` → `=C_FACTOR!B10`
- `B5` → `=C_FACTOR!B11`
- `B6` → `=C_FACTOR!B12`
- `B7` → `=C_FACTOR!B13`
- `B8` → `=C_FACTOR!B14`

Rows 9–52 in column B are user-typed (no formula). The six formula rows correspond to the template's pre-populated sample structures. Additional structures below row 8 require the user to either extend the formula pattern or type the ID manually.

## Outputs

No other sheet reads from STRUCTURE SCHEDULE. It is a terminal printable report.

## Dependencies

| Source sheet | Data pulled | Mechanism |
|---|---|---|
| C_FACTOR | B (Row ID / inlet label), rows 9–14 | Positional direct reference (`=C_FACTOR!BN`) |

## Issues found

None — STRUCTURE SCHEDULE has 0 `#REF!` errors per `pass_a.json`.

**Note:** Only the first 6 data rows auto-populate the structure ID from C_FACTOR. Rows 9+ require manual ID entry or manual formula extension by the user. This is by design for the sample template but may cause label drift if rows are added without extending column B formulas.

## Fix plan

None. No repairs needed for this sheet.

# C_FACTOR

## Purpose

Lookup table of sub-basin drainage area, weighted runoff coefficient, and time of concentration for every inlet row ID in the project; feeds the Rational Method columns on STORM DRAIN COMPS and INLET SPACING.

## Headers & ranges

Occupied range: `B6:V88` (data rows 6–88, 83 basin rows). No Table objects — plain cells. Row 6 is the first data row (no separate header row for user data; column labels are above in rows 1–5, project-specific text). Columns A and beyond column V carry auxiliary or notes content that is not part of any downstream lookup.

## Inputs

User-typed cells (raw data entry):
- `B6:B88` — Inlet Row ID (lookup key; consumed by STORM DRAIN COMPS and INLET SPACING via `VLOOKUP(..., C_FACTOR!$B$6:$V$88, col, FALSE)`)
- `C6:C88` — Drainage area (sf, square feet; raw surveyed or CAD-measured area)
- `E6:E88` through `L6:L88` — Sub-area breakdowns by land use type (sf per category; feeds the weighted C computation in column M)
- `N6:N88` — Impervious area (sf, used for `O` and `R` computations)
- `V6:V88` — Time of concentration Tc (min, user-entered or computed externally; col 21 of the lookup range)
- `AA3`, `AA4` — Composite C weights for pervious and impervious portions respectively (constants referenced in column R formula)

Dropdown sources: none on this sheet.

Workbook-scoped named ranges read: none.

## Formulas

365 formulas across columns D, M, O, P, R — repeated for every 10th row of the data block (rows 6, 16, 26, … 86; the pattern suggests every Nth row is formula-driven while intermediate rows are purely user-typed or blank).

### Column D: Drainage area (acres)

- `D6` → `=IF(C6/43560 = 0, "", C6/43560)` — converts sf to acres; blanks when zero (engineering-methodology.md §1 `A` term for Rational Method)

### Column O: Impervious area (acres)

- `O6` → `=IF(N6/43560 = 0, "", N6/43560)` — converts impervious sf to acres

### Column P: Pervious area (acres)

- `P6` → `=IFERROR(D6-O6, "")` — total area minus impervious area

### Column M: Weighted runoff coefficient C (computed)

- `M6` → `=IF(R6="", IF(D6="","", IF(D6=0, 0, ((E6*$V$9)+(F6*$V$10)+(G6*$V$12)+(H6*$V$13)+(I6*$V$15)+(J6*$V$16)+(K6*$V$18)+(L6*$V$19))/D6)), R6)` — area-weighted C per land-use sub-area; if column R holds a user override it takes precedence. Implements `C = ΣCᵢAᵢ / ΣAᵢ` (engineering-methodology.md §1 weighted runoff coefficient). Constants `$V$9`, `$V$10`, … are per-land-use C values stored as named constants in column V of the header rows.

### Column R: Override / composite C (user override)

- `R6` → `=IFERROR(($AA$3*(O6)+$AA$4*(P6))/(D6), "")` — simple two-zone composite C (impervious weight × impervious area + pervious weight × pervious area, normalised by total area). Used when the sub-area breakdown columns are not filled in; column M prefers R if non-blank.

## Outputs

| Consumer sheet | Columns pulled | Lookup key | VLOOKUP col index |
|---|---|---|---|
| STORM DRAIN COMPS | D (drainage area, acres) | B (Row ID) | 3 |
| STORM DRAIN COMPS | M or R (C runoff coefficient) | B (Row ID) | 17 |
| STORM DRAIN COMPS | V (Tc, min) | B (Row ID) | 21 |
| INLET SPACING | Same three columns | B (Row ID) | 3, 17, 21 |
| STRUCTURE SCHEDULE | B (Row ID string) | positional (B9:B14 → SS B3:B8) | direct reference |

## Dependencies

None — C_FACTOR reads no other sheet. It is a pure user-input / computed-from-inputs source.

## Issues found

None — C_FACTOR has 0 `#REF!` errors and no broken cross-sheet references per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

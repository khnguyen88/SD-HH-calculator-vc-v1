# PIPE SCHEDULE

## Purpose

Hand-maintained printable tabulation of the pipe inventory for drawing submission; auto-populates pipe ID, to-node, diameter, and length from STORM DRAIN COMPS so the schedule stays in sync with the design data.

## Headers & ranges

Occupied range: rows 1–55, 27 columns. No Table objects — plain cells. Row 1 is the sheet title. Row 2 is the column-header row. Data rows: 3–55 (53 pipe rows, mapping to STORM DRAIN COMPS rows 10–62 one-to-one by positional offset).

## Inputs

User-typed cells (all columns except B, C, D, G which are formula-driven):
- `E3:E55` — Pipe material / type (e.g., RCP Class III)
- `F3:F55` — Pipe class or gauge
- `H3:H55` through the remaining columns — additional schedule fields (total cumulative length, slope, invert elevations, remarks, drawing reference — exact column semantics are user-maintained per plan set convention)

Dropdown sources: none on this sheet.

Workbook-scoped named ranges read: none.

## Formulas

52 formulas in columns B, C, D, G — four direct-reference pulls per data row, offset-linked to STORM DRAIN COMPS:

- `B3` → `='STORM DRAIN COMPS'!A10` — From-node Row ID (pipe label)
- `C3` → `='STORM DRAIN COMPS'!B10` — To-node ID
- `D3` → `='STORM DRAIN COMPS'!N10` — Pipe diameter (in)
- `G3` → `='STORM DRAIN COMPS'!O10` — Pipe length (ft)

Each subsequent data row steps the source reference by one row (B4 ← SDC!A11, B5 ← SDC!A12, …). This is a fixed positional offset — not a lookup — so the row order on this sheet must match the row order on STORM DRAIN COMPS. Per MCDOT §4.3.3(r) / MDSHA requirements, the schedule must list all pipe segments with size, type, class, and length.

## Outputs

No other sheet reads from PIPE SCHEDULE. It is a terminal printable report.

## Dependencies

| Source sheet | Data pulled | Mechanism |
|---|---|---|
| STORM DRAIN COMPS | A (From-node), B (To-node), N (diameter), O (length) | Positional direct reference (`='STORM DRAIN COMPS'!AN`) |

## Issues found

None — PIPE SCHEDULE has 0 `#REF!` errors per `pass_a.json`. The 52 formulas are clean direct references; the remaining columns are user-typed.

**Note on formula count discrepancy from task guidance:** The task brief stated "formula_count is 0 or very low" with an expectation of a hand-maintained sheet. In practice pass_a.json reports 52 formulas — four per row for 13 rows (rows 3–55 have formulas only in the rows where entries exist, suggesting the template ships pre-populated for a sample run of about 13 pipes). The auto-populated columns (B, C, D, G) reduce transcription error and are intentional.

## Fix plan

None. No repairs needed for this sheet.

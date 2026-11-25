# EQUATIONS + INSTRUCTIONS

## Purpose

Static reference sheet carrying the governing equations and workbook usage instructions for the engineer; provides no computed values.

## Headers & ranges

Occupied range: rows 1–47, 24 columns. No Table objects — plain cells. The sheet is entirely text / numeric constants. Row 1 is the sheet title. Content is organized into labelled blocks covering the Rational Method, Manning's equation, friction slope, structure loss (Kb method), HGL propagation, and workbook entry instructions.

## Inputs

No user-typed input cells — this sheet is read-only reference material.

Dropdown sources: none.

Workbook-scoped named ranges read: none.

## Formulas

No formulas — EQUATIONS + INSTRUCTIONS is static reference text (formula_count = 0 per `pass_a.json`).

## Outputs

No other sheet reads from EQUATIONS + INSTRUCTIONS. It is informational only.

## Dependencies

None — this sheet reads no other sheet.

## Issues found

1. **Watch** — The instructions do not warn users that the From/To columns (STORM DRAIN COMPS columns A and B) must describe an **acyclic** (loop-free) pipe network. The HGL propagation chain on STORM DRAIN COMPS uses lateral array formulas of the form `MAX(IF($B$10:$B$98 = $A10, ...))` and the Hx chain uses similar self-referential MAX/IF lookups. These are resolved by Excel's natural evaluation order when the graph is a directed acyclic tree; a loop in the From/To data produces a circular reference error (or silent 0) because `iterate = False` on the workbook's `calcProps`. There is no on-sheet guard or user-visible explanation.

## Fix plan

Issue 1 → **R5** (Task 13). `repair.py` will insert a note in the EQUATIONS + INSTRUCTIONS sheet — in the workbook entry instructions block — stating that the From/To columns must describe an acyclic network and that a loop will cause Excel to report a circular reference rather than iteratively converging. The note also documents that `iterate = False` is intentional: enabling iterative calculation would mask a data-entry error as apparent convergence.

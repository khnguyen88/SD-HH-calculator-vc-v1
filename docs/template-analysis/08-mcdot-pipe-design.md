# MCDOT PIPE COMPS-DESIGN

## Purpose

MCDOT submittal form that presents the Rational Method pipe design computations — drainage area, runoff coefficients, time of concentration, rainfall intensity, peak flow, pipe sizing, friction slope, velocity, and travel time — for each pipe run in the project.

## Headers & ranges

Occupied range: rows 1–36, columns A–P (36 rows × 16 cols). One Table object: **Table22** at `A4:O32`. Row 1 contains the dynamic project/storm title (CONCATENATE of `STORM DRAIN COMPS`!$H$3 + " PIPE COMPUTATIONS"). Row 3 contains units-label text. Row 4 contains the structured-reference column labels (Table22 header row). Data rows start at row 5 (28 data rows through row 32).

## Inputs

- `A5:A32` — From-structure ID (user-typed row key). Every formula in columns B–O reads this value via `INDEX/MATCH($An, 'STORM DRAIN COMPS'!$A$10:$A$97, 0)`.

No dropdown sources on this sheet.

## Formulas

All data columns use the same guard-wrapped pattern: `IF($An="","", IF($Bn="","", INDEX('STORM DRAIN COMPS'!$<col>$10:$<col>$97, MATCH($An, 'STORM DRAIN COMPS'!$A$10:$A$97, 0))))`. Column B omits the `$Bn` guard. All keyed on `$A` (From-structure ID) against SDC `$A$10:$A$97`.

- `B5` To Str → SDC `$B` (To-structure ID)
- `C5` Area Increm (ac) → SDC `$C` (incremental drainage area); engineering-methodology.md §1 `A` term
- `D5` Area Total (ac) → SDC `$I` (accumulated drainage area ΣA); §1 accumulated `A` term
- `E5` C (runoff coef) → SDC `$D` (runoff coefficient C); §1 `C` term
- `F5` A×C Increm → SDC `$F` (A×C incremental product); §1 `A×C` incremental
- `G5` A×C Total → SDC `$J` (accumulated A×C); §1 accumulated `A×C` term
- `H5` Tc (min) → SDC `$E` (Tc to inlet, min); §2 time-of-concentration
- `I5` Rain Inten (in/hr) → SDC `$L` (design intensity keyed on accumulated Tc); §1 `i` term
- `J5` Q Total (cfs) → SDC `$M` (total peak flow Q = ΣAC × i); §1 `Q = C × i × A`
- `K5` Pipe Size (in) → SDC `$N` (pipe diameter, user-typed in SDC)
- `L5` Friction Slope (%) → SDC `$Y` (Sf, ft/ft, as percentage); §4 `Sf = (Q×n / (1.486×A×R^(2/3)))²`
- `M5` Flow Velocity (fps) → SDC `$W` (design velocity, user-typed in SDC)
- `N5` Pipe Length (ft) → SDC `$O` (pipe length, user-typed in SDC)
- `O5` Time in Pipe (min) → SDC `$K` (travel time in pipe, min); §2 pipe Tt = L/V/60

## Outputs

No other sheet reads from MCDOT PIPE COMPS-DESIGN per `pass_a.json` cross_sheet_refs. This is a leaf-node submittal form.

## Dependencies

| Source sheet | Columns pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | B, C, I, D, F, J, E, L, M, N, Y, W, O, K | From-structure ID (col A) via INDEX/MATCH |

## Issues found

None — MCDOT PIPE COMPS-DESIGN has 0 `#REF!` errors per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

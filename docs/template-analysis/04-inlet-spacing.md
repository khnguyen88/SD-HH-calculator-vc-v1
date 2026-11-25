# INLET SPACING

## Purpose

Computes inlet capture hydraulics (spread, capture ratio, bypass flow) for each catch basin using HEC-22 Chapter 4 on-grade and sump methods, feeding bypass carryover flow into downstream inlets.

## Headers & ranges

Occupied range: rows 1–109, columns A through BR (max_col = 70, i.e., column BR). No Table objects — plain cells. The sheet data section uses rows 11–38 (rows with formulas; openpyxl reports max_row = 109 but rows 39 and above appear to be blank or static). Header rows: rows 8–10 (confirmed by layout context — row 8 carries the top-level column headers). The sheet has a single section of inlet data; a second "PROPOSED CONDITIONS" section noted in some project templates was not confirmed by formula inspection of `pass_a.json` (formula rows are 7, 11–38, 40 only).

Row 7 contains a date formula: `R7 = TODAY()`.

## Inputs

User-typed cells within the data rows:
- `A11:A38` — Inlet Number / ID (project-assigned label; also the lookup key for bypass routing)
- `B11:B38` — Catch Basin Type (inlet type string, e.g. "Type C", "Type M"; determines capture formula branch)
- `C11:C38` — Inlet Length (ft, curb opening or grate length)
- `L11:L38` — Gutter spread length or design parameter (user-typed; used in U, V, W formulas)
- `M11:M38` — Longitudinal gutter slope (ft/ft; used in spread and capture formulas)
- `N11:N38` — Gutter cross-slope or width parameter (user-typed)
- `P11:P38` — Gutter width or pavement width (ft; used in spread formula U11)
- `Q11:Q38` — Carryover flow percentage or bypass fraction (%; used in R11 to compute bypass Q)
- `S11:S38` — Downstream inlet ID that this row's bypass flow routes to (user-typed for most rows; a few rows have formula copies: `S13 = A11`, `S18 = A17`, `S19 = A11`)
- `T11:T38` — Additional inlet geometry parameter (user-typed)
- `AC11:AC38` — user input
- `AD11:AD38` — user input

Header-row inputs:
- `N4` — gutter-related design parameter (referenced as `$N$4` in U11, V11, W11, AA11)
- `N5` — Manning's n for gutter (referenced as `$N$5` in W11, Y11, Z11, AA11)
- `N6` — cross-slope or gutter parameter (referenced as `$N$6` in U11, V11, W11)
- `Q4` — jurisdiction selector (referenced as `$Q$4` in J11 for IDF lookup branch)
- `H6` — design storm return period (referenced as `$H$6` in J11 for IDF column selection)

Dropdown sources: jurisdiction via `$Q$4`; return period via `$H$6` (both user-typed header cells, not named-range dropdowns confirmed in this sheet).

## Formulas

### Columns D–E: Drainage area and runoff coefficient (engineering-methodology.md §1)

- `D11` Area (acres) → `VLOOKUP('INLET SPACING'!A11, C_FACTOR!$B$6:$V$88, 3, FALSE)` — sub-basin area from C_FACTOR by Inlet ID
- `E11` Runoff coefficient C → `VLOOKUP(A11, C_FACTOR!$B$6:$V$88, 17, FALSE)` — C from C_FACTOR

### Columns F–H: Rational Method flow accumulation (engineering-methodology.md §1)

- `F11` CA incremental → `D11 * E11` — `A × C` product per §1
- `G11` Bypass CA (carryover from upstream) → `IF(A11="", "", SUMIF($S:$S, A11, $R:$R))` — sums the bypass flow `R` column for all rows whose target inlet `S` column equals this inlet's ID; implements carryover routing between inlets
- `H11` Total CA → `F11 + G11` — cumulative weighted drainage area including bypass from upstream inlets

### Column I: Time of concentration (engineering-methodology.md §2)

- `I11` Tc (min) → `VLOOKUP('INLET SPACING'!A11, C_FACTOR!$B$6:$V$88, 21, FALSE)` — overland/inlet Tc from C_FACTOR

### Column J: Rainfall intensity (engineering-methodology.md §1)

- `J11` I10 (in/hr) → multi-jurisdiction `INDEX/MATCH` into `DATA` IDF block keyed on Tc (I11) and storm frequency (H6), with branches for DC, MoCo, and PG County, interpolating for non-integer Tc — same pattern as STORM DRAIN COMPS column G

### Column K: Design peak flow (engineering-methodology.md §1)

- `K11` Q10 (cfs) → `H11 * J11` — Q = ΣAC × i (§1; Cf defaults to 1.0 via H11 accumulated)

### Column R: Bypass / carryover flow

- `R11` Bypass Q (cfs) → `H11 * (1 - (Q11/100))` — portion of total Q not captured by this inlet; `Q11` holds the capture percentage. This is the value routed downstream via column S / SUMIF in column G.

### Columns U–AB: Spread and capture hydraulics (HEC-22 Chapter 4)

These columns implement inlet-on-grade and sump capture hydraulics per HEC-22 Chapter 4 (FHWA HIF-24-006, 4th ed., 2024). The project rulebook (`engineering-methodology.md`) does not fully specify inlet spread hydraulics — HEC-22 Ch. 4 is the upstream source. Column descriptions below are based on formula inspection; detailed equation citations belong in the project's hydraulic design notes.

- `U11` Computed spread T (ft) → `L11 + 0.25*(1-(1-$N$6/P11)^2.67)` — spread at inlet based on gutter geometry and cross-slope parameters (HEC-22 Ch. 4 spread equations)
- `V11` V/T ratio parameter → `($N$4 + L11*$N$6) / $N$6`
- `W11` Interception flow ratio Rf → `($N$4/($N$4+$N$6*L11)) * (0.56/$N$5 * V11^1.667 * M11^0.5 * $N$6^2.667) / K11` — frontal-flow interception ratio (HEC-22 Ch. 4, curb-opening on-grade)
- `X11` Adjusted spread length → `L11 + ($N$4/$N$6)*W11`
- `Y11` Capture ratio for C ≥ 15" inlet → `IF(C11>=15, 0.54*K11^0.42*M11^0.3*(1/($N$5*X11))^0.6, Z11)` — applies larger-inlet equation branch (HEC-22 Ch. 4)
- `Z11` Base capture ratio → `0.58*K11^0.42*M11^0.3*(1/($N$5*X11))^0.6` — standard on-grade capture formula
- `AA11` Effective capture ratio → `IF($N$4=0, 0.6*K11^0.42*M11^0.3*(1/($N$5*X11))^0.6, Y11)` — selects sump vs. on-grade formula branch based on $N$4 (longitudinal slope indicator)
- `AB11` Capture efficiency E → `IF(C11>AA11, 1, 1-(1-C11/AA11)^1.8)` — HEC-22 curb-opening efficiency equation; clamps to 1.0 when inlet length exceeds required length

### Columns AE–BR: Per-inlet bypass routing matrix

This block routes bypass flow from each inlet row to each downstream inlet. Each pair of columns (odd = EXACT check, even = ISERR guard) represents one downstream target inlet:

- `AE11` → `IF(EXACT($A$11, $S11), $R11, 0)` — returns R11 (bypass Q) if this row's target inlet S equals inlet A11; zero otherwise
- `AF11` → `IF(ISERR(AE11), 0, AE11)` — guards against errors in AE11
- `AG11` → `IF(EXACT($A$13, $S11), $R11, 0)` — same pattern for inlet A13
- `AH11` → `IF(ISERR(AG11), 0, AG11)`
- `AI11` → `IF(EXACT($A$15, $S11), $R11, 0)` — inlet A15
- `AJ11` → `IF(ISERR(AI11), 0, AI11)`
- `AK11` → `IF(EXACT(#REF!, $S11), $R11, 0)` — **BROKEN**: the target-inlet reference is lost (see Issues)
- `AL11` → `IF(ISERR(AK11), 0, AK11)` — guards AK11
- `AM11` → `IF(EXACT($A$17, $S11), $R11, 0)` — inlet A17
- ... (pattern continues through BQ/BR for inlets at rows $A$18 through $A$38)

The pattern for the working columns: each odd column (AE, AG, AI, AM, AO, …) tests whether a data row's bypass-target (`$Sxx`) equals a specific inlet ID (`$A$NN`), returning the bypass flow `$Rxx` if so. The even column is always `ISERR(previous)` — a safety wrapper. Column G's `SUMIF($S:$S, A11, $R:$R)` aggregates the results without needing the matrix columns directly; this matrix appears to be a legacy explicit routing table, possibly for printing or audit purposes.

### AK investigation — downstream reference search

Searched all 16 sheets in `pass_a.json` for any formula referencing `'INLET SPACING'` with `AK` in the formula body. **No downstream sheet references INLET SPACING column AK.** Additionally, column AL (the ISERR wrapper for AK) is also not referenced by any external sheet. The bypass routing matrix columns AE–BR are entirely internal to INLET SPACING — no print sheet or design form pulls from them. The SUMIF in column G drives the external bypass accounting, not this matrix.

The AK target was `$A$16` based on pattern analysis: AE→$A$11, AG→$A$13, AI→$A$15, (AK→#REF!), AM→$A$17. The sequence implies AK was targeting `$A$16`. Row 16 is present in the formula data (formulas exist on row 16), which means `$A$16` is a valid cell that likely held an inlet ID at the time the template was originally authored. At some point the reference was invalidated — likely a row insert/delete operation that shifted the target out of range. Because `$A$16` is a data-entry cell (column A is user-typed, no formula found in `pass_a.json` for A16) and the bypass matrix is not consumed downstream, the safest repair is deletion.

## Outputs

| Consumer sheet | Data pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | Project title (C4) linked to A1 | Direct cell reference (`='INLET SPACING'!C4`) |

No hydraulic result column of INLET SPACING is read by any downstream sheet. The sheet is self-contained for inlet-spacing design; results are transferred to design forms manually or via the printable SHA (2-YR)SPREAD 61.1-491 sheet (which independently looks up STORM DRAIN COMPS for pipe data, not INLET SPACING for capture results).

## Dependencies

| Source sheet | Data pulled | Lookup key |
|---|---|---|
| C_FACTOR | Area (col 3), C (col 17), Tc (col 21) | Inlet ID (col A) via VLOOKUP |
| DATA | IDF intensity (MoCo, PG, DC blocks) | Tc, return period via INDEX/MATCH |

## Issues found

1. **High — `INLET SPACING` column AK rows 11–38 (24 formulas):** All 24 formulas are of the form `=IF(EXACT(#REF!, $Sxx), $Rxx, 0)`. The first argument to `EXACT` is a lost cell reference, originally `$A$16` based on the surrounding sequence pattern (AE→$A$11, AG→$A$13, AI→$A$15, AK→#REF!, AM→$A$17). The reference was invalidated by a row insert or delete that removed the original anchor. Column AL (the ISERR wrapper for AK) propagates the error but suppresses it to 0. No downstream sheet reads AK or AL. Confirmed in `pass_a.json`: `ref_error_count: 24`.

## Fix plan

**R2** (addressed by Task 12 in the implementation plan; spec §5.2):

AK investigation result: **no downstream dependency recovered.** No sheet in the workbook references `'INLET SPACING'!AK` or `'INLET SPACING'!AL`. The bypass routing matrix (columns AE–BR) is internal to INLET SPACING and is not consumed by any consumer sheet or printable report.

R2 clears AK column rows 11–96 (no downstream dependency recovered). The existing repair.py default implementation (clear AK) is correct and requires no revision.

The ISERR wrappers in column AL will remain as harmless zero-valued cells after AK is cleared; they may optionally be cleared as well since they serve no purpose with an empty AK column.

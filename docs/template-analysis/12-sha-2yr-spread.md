# SHA (2-YR)SPREAD 61.1-491

## Purpose

MDSHA 61.1-491 submittal form that presents 2-year storm inlet-spread computations — incremental drainage area, runoff coefficient, A×C flow, bypass from upstream inlets, 2-year rainfall intensity, 2-year peak flow — for each inlet row in the project.

## Headers & ranges

Occupied range: rows 1–42, columns A–S (42 rows × 19 cols). No Table objects — plain cells. Header rows precede row 7 (content varies; no formula rows above row 7 per `pass_a.json`). Data rows run from row 7 through row 42 (36 inlet rows). All rows follow a single-row-per-inlet pattern (no paired rows).

## Inputs

- `A7:A42` — From-structure ID (user-typed row key).
- `J7:N42` — User-typed columns (no formulas; likely inlet geometry: gutter spread width, longitudinal slope, or cross-slope inputs per MDSHA 61.1-491 form layout).
- `O7:O42` — Inlet efficiency or capture fraction (user-typed); used by column P to compute uncaptured/bypassed flow.
- `Q7:Q42` — Lateral inlet ID (user-typed); used by column E to look up upstream bypass contribution from column P within the same range.
- `R7:R42`, `S7:S42` — User-typed supplementary fields (no formulas).

No dropdown sources on this sheet.

## Formulas

### Columns B–C: Drainage area and runoff coefficient from C_FACTOR

- `B7` Drainage area (ac) → `INDEX(C_FACTOR!$D$6:$D$88, MATCH($A7, C_FACTOR!$B$6:$B$88, 0))` with ISNA guard — incremental area from C_FACTOR col D; engineering-methodology.md §1 `A` term
- `C7` C (runoff coef) → `INDEX(C_FACTOR!$M$6:$M$88, MATCH($A7, C_FACTOR!$B$6:$B$88, 0))` with ISNA guard — runoff coefficient from C_FACTOR col M; §1 `C` term

### Column D: A×C incremental from STORM DRAIN COMPS

- `D7` A×C Increm → `INDEX('STORM DRAIN COMPS'!$F$10:$F$97, MATCH($A7, 'STORM DRAIN COMPS'!$A$10:$A$97, 0))` — incremental A×C from SDC col F; §1 `A×C` incremental

### Column E: Bypass from upstream inlet (within-sheet lookup)

- `E7` Upstream bypass Q (cfs) → `IFERROR(INDEX($P$7:$P$42, MATCH($A7, $Q$7:$Q$42, 0)), 0)` — looks up column P (bypassed flow) against column Q (lateral inlet IDs) within the same data range; routes bypass flow from an upstream inlet to the current row

### Column F: Combined A×C + bypass flow

- `F7` Combined flow (cfs) → `IFERROR(D7 + E7, D7)` — sum of local A×C incremental and any upstream bypass; falls back to D7 alone if E7 is an error

### Column G: Tc to inlet

- `G7` Tc (min) → `INDEX('STORM DRAIN COMPS'!$E$10:$E$97, MATCH($A7, 'STORM DRAIN COMPS'!$A$10:$A$97, 0))` — Tc to inlet from SDC col E; §2 time-of-concentration

### Column H: 2-year rainfall intensity

- `H7` i₂ (in/hr) → `IF('STORM DRAIN COMPS'!$T$3="Montgomery County", INDEX(DATA!$C$8:$C$63, MATCH(ROUNDDOWN($G7,0), DATA!$A$8:$A$63, 0)), IF('STORM DRAIN COMPS'!$T$3="Prince George's County", INDEX(DATA!$L$8:$L$48, MATCH(ROUNDDOWN($D9, 0), DATA!$J$8:$J$48, 0))))` — looks up 2-year IDF intensity from DATA keyed on integer Tc; jurisdiction-switched via SDC T3 dropdown; §1 `i` term for 2-year return period

### Column I: 2-year peak flow

- `I7` Q₂ (cfs) → `IF(F7="","", IF(H7="","", H7 * F7))` — 2-year peak flow: `Q₂ = i₂ × ΣAC`; §1 `Q = C × i × A`

### Column P: Bypassed (uncaptured) flow

- `P7` Bypass Q (cfs) → `IF(F7="","", IF(O7="","", (1 - O7) * F7))` — flow passing the inlet: `Q_bypass = Q_combined × (1 − efficiency)`; feeds back into column E for downstream inlets

## Outputs

No other sheet reads from SHA (2-YR)SPREAD 61.1-491 per `pass_a.json` cross_sheet_refs. This is a leaf-node submittal form.

## Dependencies

| Source sheet | Columns pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | F (A×C Increm), E (Tc), T3 (jurisdiction flag) | From-structure ID (col A) via INDEX/MATCH |
| C_FACTOR | D (drainage area), M (runoff coef C) | From-structure ID (col A) via INDEX/MATCH |
| DATA | 2-year IDF intensity columns (MoCo: C8:C63; PG: L8:L48) | Integer Tc via MATCH(ROUNDDOWN(G, 0), ...) |

## Issues found

None — SHA (2-YR)SPREAD 61.1-491 has 0 `#REF!` errors per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

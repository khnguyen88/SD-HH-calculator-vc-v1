# SHA (25-YR)HGL 61.1-493

## Purpose

MDSHA 61.1-493 submittal form that presents the 25-year hydraulic grade line computations, using a paired-row layout analogous to MCDOT HGL-DESIGN but keyed on HGL(25YEAR) rather than HGL.

## Headers & ranges

Occupied range: rows 1–44, columns A–Q (44 rows × 17 cols). No Table objects — plain cells. Header rows precede row 9. Data begins at row 9.

**Paired-row pattern**: each pipe run uses two consecutive rows keyed on the same From-structure ID in `$A` of the odd row.
- Odd row (e.g. row 9) = pipe header row: pipe geometry, 25-year Q, friction slope (recomputed), and HGL at the upstream invert from HGL(25YEAR) col K.
- Even row (e.g. row 10) = structure-side data row: Kb from SDC col AE, HGL at the downstream invert from HGL(25YEAR) col G; the `$A` anchor is the odd row's key (e.g. `$A9`).

Pattern repeats: row 9/10, row 11/12, … through row 43/44 (18 pipe pairs).

## Inputs

- `A9, A11, A13, …` — From-structure ID (user-typed, odd rows only). Even rows inherit the odd row's `$A` reference.

No dropdown sources on this sheet.

## Formulas

### Odd rows (pipe header row): columns B–M and P

All keyed on `$An` (odd-row anchor) via `INDEX/MATCH($An, 'STORM DRAIN COMPS'!$A$10:$A$97, 0)`:

- `B` (odd) To Str → SDC `$B` (To-structure ID)
- `C` (odd) A×C Total → SDC `$J` (accumulated A×C); engineering-methodology.md §1
- `D` (odd) Time in Pipe (min) → SDC `$K` (travel time in pipe); §2
- `E` (odd) Rain Inten 25-yr (in/hr) → `IF(SDC!T3="Montgomery County", INDEX(DATA!$F$8:$F$63, MATCH(ROUNDDOWN($Dn, 0), DATA!$A$8:$A$63, 0)), IF(SDC!T3="Prince George's County", INDEX(DATA!$O$8:$O$48, MATCH(ROUNDDOWN($Dn, 0), DATA!$J$8:$J$48, 0))))` — 25-year IDF intensity from DATA keyed on integer Tc; jurisdiction-switched via SDC T3; §1 `i` term for 25-year return period
- `F` (odd) Q Total 25-yr (cfs) → `E × C` — 25-year peak flow computed on this form: `Q₂₅ = i₂₅ × ΣAC`; §1
- `G` (odd) Pipe Size (in) → SDC `$N` (pipe diameter)
- `H` (odd) Manning n → SDC `$S` (Manning's n)
- `I` (odd) Sf (recomputed) → `ROUND(((4^(5/3) × F × H) / (π × 1.486 × (G/12)^(8/3)))^2, 6)` — recomputes 25-year friction slope from this form's F and H; §4 Manning inversion
- `J` (odd) Actual Slope (ft/ft) → SDC `$Z` (actual pipe slope)
- `K` (odd) Full-flow Velocity Vf (fps) → SDC `$V` (full-flow velocity, computed in SDC via Manning); §3
- `L` (odd) Pipe Length (ft) → SDC `$O` (pipe length)
- `M` (odd) Normal Depth 25-yr (ft) → SDC `$AI` (SHA 25-year normal depth from Flowmaster, user-typed in SDC); §4 partial-flow
- `P` (odd) HGL at U/S Invert (ft) → `INDEX('HGL(25YEAR)'!$K$7:$K$99, MATCH($An, 'HGL(25YEAR)'!$A$7:$A$99, 0))` — HGL at the upstream invert from HGL(25YEAR) col K; §6 HGL propagation

### Even rows (structure-side data row): columns B, N, P

- `B` (even) → `= B<odd>` — echoes To-structure ID
- `N` (even) Kb → `INDEX('STORM DRAIN COMPS'!$AE$10:$AE$97, MATCH($A<odd>, SDC!$A..., 0))` — structure loss coefficient from SDC col AE; §5 Kb lookup
- `P` (even) HGL at D/S Invert (ft) → `INDEX('HGL(25YEAR)'!$G$7:$G$99, MATCH($A<odd>, 'HGL(25YEAR)'!$A$7:$A$99, 0))` — HGL at the downstream invert from HGL(25YEAR) col G; §6

## Outputs

No other sheet reads from SHA (25-YR)HGL 61.1-493 per `pass_a.json` cross_sheet_refs. This is a leaf-node submittal form.

## Dependencies

| Source sheet | Columns pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | B, J (A×C Total), K (Tt), N (pipe size), S (Manning n), Z (actual slope), V (full-flow vel), O (length), AI (25-yr normal depth), AE (Kb) | From-structure ID (odd row col A) via INDEX/MATCH |
| HGL(25YEAR) | K (HGL at U/S invert) and G (HGL at D/S invert) | From-structure ID (odd row col A) via INDEX/MATCH |
| DATA | 25-year IDF intensity (MoCo: F8:F63; PG: O8:O48) | Integer Tc via MATCH(ROUNDDOWN(D, 0), ...) |

## Issues found

**Downstream-of-R1 — partial exposure only.** This form reads from HGL(25YEAR) columns K and G exclusively. Per `pass_a.json`, HGL(25YEAR) has 680 `#REF!` errors confined to columns A–F, H, and L. Columns G and K are intact. Therefore:

- The HGL values (column P, both odd and even rows) currently populate correctly from the working HGL(25YEAR) cols G and K.
- The broken HGL(25YEAR) columns (A, B, C, D, E, F, H, L) are **not read by this form**, so the form is not directly impaired by the R1-scope damage.
- However, the correctness of HGL(25YEAR) cols G and K depends on the upstream chain within that sheet. If the broken columns include intermediate computations that feed G or K, then G and K values may themselves be wrong even though they are not `#REF!`. This should be verified once R1 (Task 11) rebuilds the broken HGL(25YEAR) columns.

The 25-year intensity column E on this form is computed entirely on this sheet from DATA (intact) and SDC K (intact), so row-keyed intensity is unaffected.

## Fix plan

No direct fix is required on this sheet. After R1 rebuilds HGL(25YEAR) columns A–F, H, L, re-verify that HGL(25YEAR) cols G and K update correctly so the P-column values on this form are consistent with the repaired chain. No formula changes on this sheet are anticipated.

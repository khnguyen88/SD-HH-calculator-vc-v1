# MCDOT HGL-DESIGN

## Purpose

MCDOT submittal form that presents the 10-year hydraulic grade line computations, using a paired-row layout where each pipe run occupies two rows: an odd pipe-data row and an even structure-data row.

## Headers & ranges

Occupied range: rows 1–38, columns A–P (38 rows × 16 cols). No Table objects — plain cells. Row 1 contains dynamic title cells: C1 = CONCATENATE(SDC H3 + " RUNOFF"); G1 = CONCATENATE("PIPE - " + SDC H3 + " STORM"). Data begins at row 3.

**Paired-row pattern**: each pipe run uses two consecutive rows keyed on the same From-structure ID in `$A` of the odd row.
- Odd row (e.g. row 3) = pipe header row: contains pipe geometry and HGL at the upstream crown.
- Even row (e.g. row 4) = structure-side data row: contains Kb and HGL at the downstream invert; the `$A` anchor remains the odd row's key (e.g. `$A3`).

Pattern repeats: row 3/4, row 5/6, row 7/8, … through row 37/38 (18 pipe pairs).

## Inputs

- `A3, A5, A7, …` — From-structure ID (user-typed, odd rows only). Even rows have no key column of their own; they inherit the odd row's `$A` reference.

No dropdown sources on this sheet.

## Formulas

### Odd rows (pipe header row): columns B–M and P

All keyed on `$An` (odd-row anchor) via `INDEX/MATCH($An, 'STORM DRAIN COMPS'!$A$10:$A$97, 0)`:

- `B` (odd) To Str → SDC `$B` (To-structure ID)
- `C` (odd) A×C Total → SDC `$J` (accumulated A×C); engineering-methodology.md §1
- `D` (odd) Time in Pipe (min) → SDC `$K` (travel time in pipe); §2
- `E` (odd) Rain Inten (in/hr) → SDC `$L` (design intensity for accumulated Tc); §1 `i` term
- `F` (odd, row 3) Q Total (cfs) → SDC `$M` (total peak flow); §1 `Q = ΣAC × i`. Note: row 5 and beyond compute `F = E × C` locally (`IF(A5="","",IF(C5="","",E5*C5))`) rather than pulling SDC M directly.
- `G` (odd) Pipe Size (in) → SDC `$N` (pipe diameter)
- `H` (odd) Manning n → SDC `$S` (Manning's n)
- `I` (odd) Sf (recomputed) → `ROUND(((4^(5/3) × F × H) / (π × 1.486 × (G/12)^(8/3)))^2, 6)` — recomputes friction slope from the form's own F (Q) and H (n) values; §4 Manning inversion `Sf = (Q×n / (1.486×A×R^(2/3)))²`
- `J` (odd) Actual Slope (ft/ft) → SDC `$Z` (actual pipe slope = (U/S invert − D/S invert) / L)
- `K` (odd) Flow Velocity (fps) → SDC `$W` (design velocity, user-typed in SDC)
- `L` (odd) Pipe Length (ft) → SDC `$O` (pipe length)
- `M` (odd) Normal Depth (ft) → SDC `$AH` (design storm normal depth from Flowmaster, user-typed in SDC)
- `P` (odd) HGL at U/S Invert (ft) → `INDEX(HGL!$K$7:$K$99, MATCH($An, HGL!$A$7:$A$99, 0))` — HGL at the high (upstream) invert from HGL col K; §6 HGL propagation

### Even rows (structure-side data row): columns B, N, P

- `B` (even) → `= B<odd>` — echoes the To-structure ID from the pipe row above
- `N` (even) Kb → `INDEX('STORM DRAIN COMPS'!$AE$10:$AE$97, MATCH($A<odd>, SDC!$A..., 0))` — structure loss coefficient from SDC col AE; §5 Kb lookup
- `P` (even) HGL at D/S Invert (ft) → `INDEX(HGL!$G$7:$G$99, MATCH($A<odd>, HGL!$A$7:$A$99, 0))` — HGL at the downstream invert from HGL col G; §6 HGL propagation

Columns C–M on even rows contain no formulas (structural spacing only).

## Outputs

No other sheet reads from MCDOT HGL-DESIGN per `pass_a.json` cross_sheet_refs. This is a leaf-node submittal form.

## Dependencies

| Source sheet | Columns pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | B (To Str), J (A×C Total), K (Tt), L (intensity), M (Q Total), N (pipe size), S (Manning n), Z (actual slope), W (velocity), O (length), AH (normal depth), AE (Kb) | From-structure ID (odd row col A) via INDEX/MATCH |
| HGL | K (HGL at U/S invert) and G (HGL at D/S invert) | From-structure ID (odd row col A) via INDEX/MATCH |

## Issues found

None — MCDOT HGL-DESIGN has 0 `#REF!` errors per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

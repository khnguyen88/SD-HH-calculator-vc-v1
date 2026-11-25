# HGL

## Purpose

Computes the 10-year hydraulic grade line from outfall to headwater by chaining friction loss and structure loss up each pipe run, with a crown floor to enforce the legacy both-end crown-pinning convention.

## Headers & ranges

Occupied range: `A5:O91`. No Table objects — plain cells. Header rows: row 5 (column labels) and row 6 (sub-labels / units). Data rows: 7–91 (85 pipe rows mirroring STORM DRAIN COMPS rows 10–98 one-to-one).

## Inputs

This sheet contains no user-typed cells. All data are computed from STORM DRAIN COMPS.

Row-sequence input: columns A and B in each row pull directly from `STORM DRAIN COMPS`!A and B, so the pipe-run order matches the hub sheet row-for-row (not looked up — positionally synced for rows 7–91 vs. hub rows 10–98).

## Formulas

### Columns A–B: Pipe identification (direct pull)

- `A7` From-node → `IF('STORM DRAIN COMPS'!A10="", "", 'STORM DRAIN COMPS'!A10)` — passes through the Row ID; subsequent rows step through A11, A12, … in a fixed offset pattern
- `B7` To-node → same pattern from STORM DRAIN COMPS column B

### Columns C–F: Pipe invert and crown elevations

- `C7` U/S Invert (ft) → `XLOOKUP(1, ('STORM DRAIN COMPS'!$A:$A=$A7)*('STORM DRAIN COMPS'!$B:$B=$B7), 'STORM DRAIN COMPS'!$P:$P)` — upstream invert from hub column P, keyed on (From, To) pair
- `D7` U/S Crown (ft) → `C7 + ('STORM DRAIN COMPS'!N10 / 12)` — upstream crown = U/S invert + pipe diameter converted to feet; enforces `Crown_in` geometry per `user-design-criteria.md` "Crown matching at junctions"
- `E7` D/S Invert (ft) → same XLOOKUP keyed on (A7, B7) pulling hub column Q
- `F7` D/S Crown (ft) → `E7 + 'STORM DRAIN COMPS'!N10/12` — downstream crown = D/S invert + D/12; serves as the crown floor in column G

### Column G: HGL at D/S end — HGL propagation with crown floor (engineering-methodology.md §6)

- `G7` HGL at D/S Invert (ft) → `IFERROR(IF(A7="", "", MAX(F7, Q7, MAX(IF($A$7:$A$91=$B7, $M$7:$M$91)))), "")` — resolves to the maximum of:
  1. `F7` — D/S crown floor (legacy both-end crown-pin method; ensures HGL ≥ crown at pipe outlet)
  2. `Q7` — HGL from column Q (10-year tailwater / outfall HGL input, user-typed in col Q for force-elevation nodes)
  3. `MAX(IF($A$7:$A$91=$B7, $M$7:$M$91))` — the HGL in-structure value (column M) of whatever pipe row has this pipe's To-node as its own From-node; this implements the recursive downstream-to-upstream HGL chain (§6 `downstream elevation`)

### Column H: Pipe length

- `H7` Length (ft) → `XLOOKUP(1, (A=$A7)*(B=$B7), 'STORM DRAIN COMPS'!$O:$O)` — pipe length from hub column O

### Column I: Friction slope (engineering-methodology.md §4)

- `I7` Sf (ft/ft) → `XLOOKUP(1, (A=$A7)*(B=$B7), 'STORM DRAIN COMPS'!$Y:$Y)` — friction slope from hub column Y, computed on STORM DRAIN COMPS per §4 `Sf = (Q×n / (1.486×A×R^(2/3)))²`

### Column J: Pipe friction loss (engineering-methodology.md §4)

- `J7` Hf (ft) → `H7 * I7` — total friction head loss = Sf × L (§4 `Hf = Sf × L`)

### Column K: HGL at U/S end (engineering-methodology.md §6)

- `K7` HGL at U/S Invert (ft) → `IFERROR(IF(A7="", "", MAX(D7, J7+G7)), "")` — maximum of:
  1. `D7` — U/S crown floor (crown-pin at the upstream end of the pipe)
  2. `J7 + G7` — downstream HGL + friction loss (§6 `upstream elevation = downstream elevation + Hf`)
  This is the "High Invert" HGL; it has not yet had structure loss added.

### Column L: Structure loss (engineering-methodology.md §5)

- `L7` Hb (ft) → `XLOOKUP(1, (A=$A7)*(B=$B7), 'STORM DRAIN COMPS'!$AF:$AF)` — structure loss from hub column AF, computed on STORM DRAIN COMPS per §5 controlling-angle method (MCDOT §4.3.2.3; `Hb = Kb × Vout²/2g`)

### Column M: HGL in From-structure (engineering-methodology.md §6)

- `M7` HGL in From Str (ft) → `IFERROR(IF(L7="-", "", IF(L7="", K7, K7+L7)), "")` — adds structure loss to the upstream pipe HGL: `HGL_structure = HGL_at_U/S_crown + Hb` (§6 `elevation = downstream elevation + Hf + Hb`). When L7 is blank (no structure loss applicable, e.g. outfall), M7 equals K7.

### Column N: Top/opening elevation

- `N7` Top/Opening Elev (ft) → `XLOOKUP(1, (A=$A7)*(B=$B7), 'STORM DRAIN COMPS'!$AB:$AB)` — rim or grate elevation from hub column AB

### Column O: Freeboard

- `O7` Freeboard (ft) → `N7 - K7` — rim minus HGL at the high invert; negative means HGL exceeds rim elevation. The `user-design-criteria.md` HGL check requires HGL ≤ rim − 1 ft (1 ft minimum freeboard). This column provides the engineer's check value; no formula auto-flags the threshold.

## Outputs

| Consumer sheet | Columns pulled | Lookup key |
|---|---|---|
| MCDOT HGL-DESIGN | K (HGL at U/S, col P odd rows) and G (HGL at D/S, col P even rows) | A (From-node) via INDEX/MATCH |

## Dependencies

| Source sheet | Data pulled | Lookup key |
|---|---|---|
| STORM DRAIN COMPS | P (U/S invert), Q (D/S invert), N (diameter), O (length), Y (Sf), AF (Hb), AB (rim elev) | (A, B) pipe-pair via XLOOKUP(1, array*array, …) |

## Issues found

None — HGL has 0 `#REF!` errors and no broken cross-sheet references per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

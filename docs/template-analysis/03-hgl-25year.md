# HGL(25YEAR)

## Purpose

Intended to compute a 25-year hydraulic grade line using the same chain as the 10-year HGL sheet; currently non-functional due to 680 `#REF!` formulas caused by lost OFFSET anchors.

## Headers & ranges

Occupied range: `A1:V91`. No Table objects — plain cells. Header rows: rows 5–6 (mirror the 10-year HGL sheet's layout). Data rows: 7–91 (85 pipe rows). Cell A1 links the project title from `STORM DRAIN COMPS'!A1`.

Columns A–O are the intended working columns (matching the 10-year HGL layout). Columns P–V are auxiliary columns unique to this sheet that pull 25-year-specific data via working `INDEX/MATCH` formulas:

| Col | Content |
|---|---|
| O | Tailwater / 10-year chain HGL input (pulls from `HGL'!Q7` — the 10-year outfall HGL) |
| Q | Pipe diameter (in) — `INDEX('STORM DRAIN COMPS'!$N$10:$N$97, MATCH($A7, ...))` |
| R | Accumulated A×C (J col on SDC) — `INDEX('STORM DRAIN COMPS'!$J$10:$J$97, ...)` |
| S | Pipe Tc (K col on SDC) — `INDEX('STORM DRAIN COMPS'!$K$10:$K$97, ...)` |
| T | 25-year intensity (in/hr) — `INDEX(DATA!$F$8:$F$63, ...)` for MoCo or `DATA!$O$8:$O$48` for PG County, keyed on ROUNDDOWN(S, 0) |
| U | 25-year Q = T × R — `T7 * R7` |
| V | Manning's n — `INDEX('STORM DRAIN COMPS'!$S$10:$S$97, ...)` |

## Inputs

User-typed cells: none in the working rows. The sheet computes entirely from STORM DRAIN COMPS and the HGL sheet.

Force-elevation nodes (outfall HGL) are inherited from column O, which pulls `HGL!Q7` for each row — this means the 25-year sheet uses the same tailwater as the 10-year sheet. If the 25-year outfall condition differs, column O would need a separate user-entry mechanism (not currently provided).

## Formulas

### Columns A–N (rows 7–91): BROKEN — 680 #REF! errors

Every formula in columns A–N of rows 7–91 uses `OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0)`. The OFFSET anchor cell was deleted or the named range it pointed to was removed at some point. Example broken formulas:

- `A7` → `=IF(OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0)="", "", OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0))`
- `C7` (U/S Invert) → `=IF(OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0)="", "", OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0))`
- `D7` (U/S Crown) → `=IF(C7="", "", C7 + OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0))`
- `L7` (Structure loss) → `=IF(OFFSET('STORM DRAIN COMPS'!#REF!, ...) = "-", 0, OFFSET('STORM DRAIN COMPS'!#REF!, ...))`

The OFFSET approach was the predecessor pattern before the 10-year HGL sheet was migrated to the cleaner `XLOOKUP(1, (A=$A7)*(B=$B7), …)` array-formula pattern. The 25-year sheet was never updated to match.

### Columns G, J, K, M: HGL chain formulas (structurally intact but starved of inputs)

These four columns use intra-sheet references only and are structurally correct — they cannot produce valid output because columns A–F and H–I feed them broken values:

- `G7` → `MAX(F7, O7, MAX(IF($A$7:$A$91=$B7, $M$7:$M$91)))` — same crown-floor + downstream chain logic as HGL (engineering-methodology.md §6)
- `J7` → `H7 * I7` — Hf = Sf × L (engineering-methodology.md §4)
- `K7` → `MAX(D7, J7+G7)` — upstream HGL floored at U/S crown (§6)
- `M7` → `IF(L7="", K7, K7+L7)` — HGL in structure = K7 + Hb (§6)

### Columns Q–V: 25-year auxiliary data (working)

These columns are functional and use `INDEX/MATCH` against STORM DRAIN COMPS rows 10–97:

- `I7` Friction slope Sf → `ROUND(((4^(5/3)*U7*V7)/(PI()*1.486*(Q7/12)^(8/3)))^2, 6)` — recomputes Sf using 25-year Q (column U) and Manning's n (column V) per engineering-methodology.md §4. This is the key difference from the 10-year sheet: Sf is recomputed here from 25-year flow, not looked up from the SDC Y column (which holds 10-year Sf).

### Critical gap: no 25-year friction slope on STORM DRAIN COMPS

STORM DRAIN COMPS column Y holds the **10-year** design-storm Sf. Column AI holds the "SHA 25-Year Normal Depth (ft)" — a depth value from Flowmaster output — not a friction slope. After R1 rebuilds this sheet using the 10-year XLOOKUP pattern, the repaired column I will recompute Sf from 25-year Q (column U) and Manning's n (column V), which is what the intact I7 formula above already does. This is the correct approach.

**Engineering note for the repaired sheet:** The rebuilt sheet will compute 25-year friction slope from 25-year Q using Manning's equation (same pipe geometry, different Q). This is methodologically correct. The existing intact I7 formula already implements this correctly and should be used as the template for the XLOOKUP rebuild. After R1, a header note on the sheet will instruct the engineer that:
- Column I computes 25-year Sf from 25-year Q (column U) derived from 25-year intensity (column T).
- If Flowmaster or another hydraulic model produces a materially different 25-year Sf for any run, the engineer may manually override column I for that row and document the deviation in the project record.

## Outputs

| Consumer sheet | Columns pulled | Lookup key |
|---|---|---|
| SHA (25-YR)HGL 61.1-493 | K (HGL at U/S) | A (From-node) via `INDEX('HGL(25YEAR)'!$K$7:$K$99, MATCH($A9, 'HGL(25YEAR)'!$A$7:$A$99, 0))` |

## Dependencies

| Source sheet | Data pulled | Status |
|---|---|---|
| STORM DRAIN COMPS | P, Q, N, O, AF, AB (intended via OFFSET; broken) | BROKEN — all 680 OFFSET references resolve to #REF! |
| STORM DRAIN COMPS | N, J, K, S (via working INDEX/MATCH in cols Q–V) | Working |
| HGL | Q column (10-yr tailwater for outfall rows) | Working — `HGL!Q7` direct reference |
| DATA | 25-yr IDF intensity | Working — INDEX/MATCH in col T |

## Issues found

1. **Critical — `HGL(25YEAR)` rows 7–91, columns A–N (680 formulas):** Every cell uses `OFFSET('STORM DRAIN COMPS'!#REF!, (ROW()-7), 0)`. The OFFSET anchor cell was deleted. The entire working portion of the sheet emits `#REF!` and the downstream consumer `SHA (25-YR)HGL 61.1-493` currently reads invalid data from column K. Confirmed in `pass_a.json`: `ref_error_count: 680`.

## Fix plan

**R1** (addressed by Task 11 in the implementation plan; spec §5.2):

Delete the broken OFFSET formulas in `HGL(25YEAR)` rows 7–91, columns A–N. Rebuild each column by mirroring the 10-year HGL sheet's `XLOOKUP(1, ('STORM DRAIN COMPS'!$A:$A=$A7)*('STORM DRAIN COMPS'!$B:$B=$B7), 'STORM DRAIN COMPS'!<col>:<col>)` pattern for all columns that pull directly from STORM DRAIN COMPS.

Column I (friction slope) is the one difference: rather than looking up the 10-year Sf from SDC column Y, it recomputes Sf from 25-year Q using the formula already present in the working portion of the sheet: `ROUND(((4^(5/3)*U7*V7)/(PI()*1.486*(Q7/12)^(8/3)))^2, 6)`. This is the correct approach and requires no source-sheet change.

The header layout stays identical to the current sheet. The repaired sheet will produce the same output shape as the 10-year HGL sheet when a project is populated, enabling `SHA (25-YR)HGL 61.1-493` to read valid values from column K.

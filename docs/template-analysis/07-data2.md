# DATA2

## Purpose

Static partial-flow depth lookup table for circular pipe; maps the dimensionless normal-depth parameter AR^(2/3)/D^(8/3) to depth and area ratios, enabling STORM DRAIN COMPS to compute normal depth without an external hydraulics solver.

## Headers & ranges

Occupied range: `A1:D101`. No Table objects — plain cells. Row 1 is a header row. Data rows: 2–101 (100 interpolation entries). Column layout is four columns A–D; columns E–L (12-col max per pass_a.json) are blank.

## Inputs

All cells on this sheet are static lookup table values — no formulas (formula_count = 0 per `pass_a.json`).

Column schema:
- `A2:A101` — Dimensionless parameter AR^(2/3)/D^(8/3) (monotonically increasing; VLOOKUP index column). This is the value computed on STORM DRAIN COMPS column AY as `((Qfull × Q_design) / (1.49 × S^0.5)) / (D/12)^2.667`.
- `B2:B101` — Y/D ratio (normal depth ÷ diameter; dimensionless). Pulled by STORM DRAIN COMPS column AZ as VLOOKUP col 2.
- `C2:C101` — A/D² ratio (flow area ÷ diameter²; dimensionless). Pulled by STORM DRAIN COMPS column BB as VLOOKUP col 3.
- `D2:D101` — Fourth ratio column (exact semantic TBD from physical workbook inspection; likely a velocity or top-width ratio used for future expansion). No live formula currently references VLOOKUP col 4.

## Formulas

No formulas — DATA2 is a static lookup table.

## Outputs

| Consumer sheet | Columns pulled | Lookup key | VLOOKUP col index |
|---|---|---|---|
| STORM DRAIN COMPS col AZ | B (Y/D ratio) | A (AR^(2/3)/D^(8/3)) via `VLOOKUP(AY10, DATA2!$A$2:$D$101, 2)` | 2 |
| STORM DRAIN COMPS col BB | C (A/D² ratio) | Same AY parameter | 3 |

STORM DRAIN COMPS then derives:
- `BA` normal depth (ft) = `AZ × (D/12)` (Y/D × diameter)
- `BC` flow area (sf) = `BB × (D/12)²` (A/D² × diameter²)
- `BD` velocity at normal depth (fps) = `AV / BC` (Q / A)

## Dependencies

None — DATA2 reads no other sheet.

## Issues found

None — DATA2 has 0 `#REF!` errors and no broken cross-sheet references per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

---

**Governing method note.** The partial-flow normal-depth computation via this table replaces a Flowmaster or iterative solver call. The engineering-methodology.md rulebook documents Manning full-flow (§3) and friction slope (§4) for the full-pipe case; this table supports the sub-full normal-depth branch that runs in parallel on STORM DRAIN COMPS columns AT–BD. The standard reference for circular-section partial-flow hydraulic elements is Chaudhry, *Open-Channel Hydraulics*, or equivalent texts; no explicit citation for this table appears in the current engineering-methodology.md.

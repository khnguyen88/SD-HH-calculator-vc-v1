# Spec 7b — Per-Shape Partial-Flow Lookups + Rectangular Calc

- **Date:** 2026-11-28
- **Status:** Finalized (design + plan combined). Ready for execution in a future session.
- **Follow-up to:** Spec 7 Path A (pipe shape columns shipped 2026-11-28).

## Problem

Spec 7 shipped shape-aware full-flow and friction-slope formulas for all three shapes (circular, elliptical, rectangular) + multi-barrel. **Partial flow** (y/d, V at partial depth) for non-circular shapes currently uses an equivalent-D approximation through DATA2 (circular table). Accuracy:

- **Circular:** exact (DATA2 lookup).
- **Elliptical, small standard sizes (≤36" rise):** ~1% error vs MDSHA Table 4-6 published equivalent-D. Acceptable for most MDSHA/MCDOT designs.
- **Elliptical, larger sizes:** error grows (~3–5% at 60"+ rise). HDS-5 Chart 24 per-shape tables more accurate.
- **Rectangular:** equivalent-D approximation via DATA2 is an engineering hack. Rectangular partial flow is implicit — proper solve needs iteration or a dedicated table.

**User's ask (from the Spec 7 session):** "do both equivalent-D and per-shape lookup, compare on small sizes, decide. Refer to HEC-22 or other approved standards."

JS-side `calcPipeRow()` in the calculator app also currently uses the circular/elliptical equivalent-D path; no rectangular JS calc exists. Pipes with `shape:"rectangular"` in state get wrong Qfull/V in the UI (xlsx formulas are correct; UI is approximation-only).

## Goal

1. Add per-shape partial-flow lookup tables to the xlsx template for elliptical (HDS-5 Chart 24) and rectangular (HDS-5 Chart 10 or equivalent).
2. Add a Config toggle (`partialFlowMethod`) to pick equivalent-D (default, matches Spec 7) vs per-shape lookup.
3. Add a comparison worksheet (or Config section) that shows side-by-side values for the same input so users can visually verify the two methods agree within tolerance.
4. Add JS-side `calcPipeRow` branch for rectangular (closed-form Manning + partial-flow solve via Newton-Raphson or equivalent-D).
5. Document in `EQUATIONS + INSTRUCTIONS` which method applies to which shape + when to flip the toggle.

## Approved standards (references for digitization)

- **HDS-5 (FHWA Hydraulic Design of Highway Culverts, 2012):**
  - Chart 24 — Partial-flow for horizontal elliptical concrete pipe (per standard ASCE size: 14×23, 18×29, 22×34, 26×38, 30×44, 34×50, 38×57, 42×62, 46×68, 50×76, 54×83, 58×90, 62×97, 68×106, 72×113, 77×121). Values: y/rise → A/A_full, R/R_full.
  - Chart 10 — Hydraulic elements for rectangular channels. For partial flow: y/B → A/B², R/B.
- **HEC-22 §7.4** — HGL walking already covered.
- **MDSHA Drainage Manual Table 4-6** — equivalent circular D per elliptical SPAN×RISE. Already referenced for comparison.
- **AASHTO Highway Drainage Guidelines Ch. 7** — alternative source for elliptical partial-flow.

Digitize **values** (not nomographs) into DATA3 sheet with one column set per standard shape.

## Design

### New sheet: `DATA3` (partial-flow lookup tables)

Columns layout — per-shape block of 3 cols (y/d, A/A_full, R/R_full):

| Block | Shape | Col set | Rows |
|---|---|---|---|
| A–C | Rectangular, aspect 1:1 (square) | y/B, A/B², R/B | 2–102 (y/B from 0.01 to 1.00 in 0.01 step) |
| E–G | Rectangular, aspect 2:1 (W=2H) | y/H, A/BH, R/H | 2–102 |
| I–K | Rectangular, aspect 3:1 (W=3H) | y/H, A/BH, R/H | 2–102 |
| M–O | Elliptical 18×29 | y/rise, A/A_full, R/R_full | 2–102 (from HDS-5 Chart 24) |
| Q–S | Elliptical 24×38 | same | 2–102 |
| ... | (one per standard size in HDS-5 Chart 24) | | |

Alternative compact layout: one SHARED y/d column, then per-shape pairs of (A/A_full, R/R_full). Decide during implementation based on readability.

**Source:** digitize Chart 24 values from the PDF in `docs/hif24006.pdf` or `docs/hif24006-hec22_v4.pdf` (these are the HDS-5 / HEC-22 documents already in the repo). If not found, use HDS-5 PDFs from the FHWA website.

### Config toggle: `partialFlowMethod`

Add to Config sheet (row 8 — currently unused):

| Cell | Named range | Values | Default |
|---|---|---|---|
| `B8` | `partialFlowMethod` | `equivalent-d` \| `per-shape-lookup` | `equivalent-d` |

Citations: HDS-5 Chart 24 (elliptical), HDS-5 Chart 10 (rectangular), MDSHA Table 4-6 (equivalent-D source).

### SDC partial-flow block (AY..BF) rewrite

Current (Spec 7 Path A):
- AY: Q per barrel = M/Q
- AZ: effective D = BK (shape-aware)
- BB: dimensionless Manning param
- BC, BE: VLOOKUP DATA2 cols 2 and 3 (partial-flow A/D² and y/D)
- BD, BF: physical y and A

New (Spec 7b):
- AY, AZ, BB unchanged (per-barrel Q + Manning param stays).
- BC/BE: branch on `partialFlowMethod`:
  - If `equivalent-d`: VLOOKUP DATA2 (current behavior).
  - If `per-shape-lookup`:
    - Circular: VLOOKUP DATA2 (identical to equivalent-d — circular IS its own per-shape lookup).
    - Elliptical: find closest standard shape block in DATA3 by (span × rise), VLOOKUP there. If size not in standard set: fall back to equivalent-D with a disclosure toast.
    - Rectangular: by aspect ratio (W/H), pick DATA3 block, VLOOKUP.

### Comparison section on Config

Add a block on `Config!E8:J20` (or similar unused area):

| Pipe # | Shape | W×H | y_eqD (from DATA2) | y_lookup (from DATA3) | Δ (%) |
|---|---|---|---|---|---|

Populated for every row 10..98 of SDC that has non-circular shape. User can visually compare.

### JS-side `calcPipeRow` rectangular branch

Current `calcPipeRow` logic:
- `pipeGeometry(pipe)` returns `{areaSf, equivDiamIn}`. Elliptical uses Table 4-6 lookup (equivalent-D). Rectangular not supported.
- Manning calcs use `pipeGeometry.equivDiamIn`.

Changes:
- Extend `pipeGeometry` to handle `shape === "rectangular"`:
  - `areaSf = (p.size * p.width) / 144`
  - `equivDiamIn = 2 * p.size * p.width / (p.size + p.width)` (hydraulic diameter)
- Partial flow for rectangular — add Newton-Raphson solver inline OR reuse the DATA3-based equivalent-D approximation. For MVP, use equivalent-D (matches current xlsx behavior when toggle = equivalent-d).
- Multi-barrel: divide `designQ` by `p.barrelCount` before Manning solve.

## Non-goals (Spec 7c+)

- Visualizer HGL walk — already uses `equivDiamIn` which is shape-aware if pipeGeometry handles rectangular.
- Non-standard elliptical sizes (outside HDS-5 Chart 24 list) — toast + fall back to equivalent-D.
- Rectangular flow at supercritical regime — assume subcritical for storm drain.

## Plan

### Phase A — DATA3 sheet + Config toggle (xlsx side)

**Task 1:** Digitize HDS-5 Chart 24 elliptical partial-flow tables. Choose 5–8 standard sizes to start (smallest 18×29 + largest 77×121 + 2–3 intermediate). Source from `docs/hif24006.pdf` if it contains the chart tabulation, otherwise manually digitize from the published chart.
- Output: `docs/template-analysis/hds5_chart24_elliptical.csv` with columns: `size, y_over_rise, a_over_afull, r_over_rfull`.

**Task 2:** Digitize rectangular partial-flow tables. HDS-5 Chart 10 or AASHTO equivalent. Standard aspect ratios: 1:1 (square), 2:1, 3:1, 4:1.
- Output: `docs/template-analysis/rectangular_partial_flow.csv`.

**Task 3:** Add `add_data3_sheet(wb)` edit function in `build_golden.py`. Reads the CSVs, writes DATA3 sheet with one block per shape. Place after `add_pipe_shape_columns` in `main()`.
- Add pytest: `test_data3_sheet.py` asserts rows, headers, representative values from the published charts (e.g., y/d=0.5 on circular gives A/d²≈0.3927 — verify against DATA2 for cross-check).

**Task 4:** Add `partialFlowMethod` toggle to Config sheet in `add_config_sheet()`. Default `equivalent-d`. Add data validation dropdown. Add named range.
- Pytest: assert `Config!B8` value and named range presence.

**Task 5:** Rewrite SDC!BC and SDC!BE formulas in `add_pipe_shape_columns` to branch on `partialFlowMethod`. `equivalent-d` branch keeps current DATA2 VLOOKUP; `per-shape-lookup` branch does the shape-aware lookup into DATA3.
- Elliptical shape lookup needs size matching: `IF(O=18 and P=29, VLOOKUP into DATA3 M:O, ...)` — use a helper column (BL?) for size-to-block-index mapping.
- Rectangular lookup uses aspect ratio W/H.
- Pytest: assert BC formula contains `partialFlowMethod` branch.

**Task 6:** Add comparison block on Config (E8:J20 area). Per-row formula: for SDC rows 10..98 with non-circular shape, compute both methods and report Δ%. 
- Pytest: assert the comparison block headers are present.

### Phase B — JS-side rectangular calc (calculator app)

**Task 7:** Extend `pipeGeometry(pipe)` in `storm-drain-design-calculator-dev.html` to handle `shape === "rectangular"`:
- Validate `pipe.width > 0 && pipe.size > 0` (height is in pipe.size).
- Return `{areaSf: width*size/144, equivDiamIn: 2*width*size/(width+size)}`.
- No new test — existing pipe-geometry tests should pick up the new branch.

**Task 8:** Verify multi-barrel flows through `calcPipeRow` correctly. Current code uses `pipe.n`, `pipe.size`, etc. — no divide-by-N. Add:
- `const N = Math.max(1, Number(pipe.barrelCount) || 1);`
- `const qPerBarrel = designQ / N;` — use in friction slope + partial flow.
- `const QfullTotal = N * QfullPerBarrel;`
- Pytest/visualizer test: compare xlsx T vs JS Qfull for a 2-barrel case; should match.

**Task 9:** UI: pipe table "Width (in)" input currently shows dimmed "—" for circular. Make rectangular's rendering identical to elliptical (both use the width input). No circular-only dimming logic to touch.

### Phase C — Validation + deploy

**Task 10:** Comparison sanity check: for each standard HDS-5 elliptical size, compute equivalent-D (sqrt(W*H)) and look up DATA2 at y/D=0.5, 0.75. Compare to Chart 24 published y/rise=0.5, 0.75 A/A_full. Report Δ% per size.
- Output: `docs/template-analysis/partialflow_comparison_report.md`.
- Decision point: if average Δ ≤ 2%, default partialFlowMethod stays `equivalent-d` (simpler, matches calculator JS). If Δ > 5%, default to `per-shape-lookup`. Document decision in the report.

**Task 11:** Update `EQUATIONS + INSTRUCTIONS` with disclosure:
> Partial-flow method (Config!B8): default `equivalent-d` uses the circular partial-flow table via shape-equivalent diameter — accurate for small elliptical (≤36" rise) and reasonable for rectangular. Flip to `per-shape-lookup` for larger elliptical pipes or when reviewer requires HDS-5 Chart 24 compliance. See Config comparison block for per-pipe Δ.

**Task 12:** Rebuild + full pytest + viz npm test. Merge to main, redeploy via gh-pages worktree.

## Risks

1. **CSV digitization accuracy:** manual chart reading introduces human error. Mitigation: cross-check at y/d=0.5 and y/d=1.0 (full) against known analytical values. For elliptical at y/rise=1.0, A should be π·span·rise/4. For rectangular at y/B=1.0, A=B² (square) or B·H.
2. **Non-standard elliptical sizes:** user may enter 25×40 (non-ASCE). Reader should fall back to equivalent-D with a toast. Document in EQUATIONS.
3. **Config!B8 named range** — must not collide with existing named ranges. Current taken: junctionAngleRule (B3), hglCrownCeilingRule (B4), hglMethod (B5), projectName/exportTimestamp/templateShape/contractVersion (B1/B2/B6/B7). B8 is free.
4. **File size:** DATA3 adds ~30 KB (8 shapes × 100 rows × 3 cols). Negligible for the xlsx; negligible for base64-inlined golden.

## Deliverables

1. `docs/template-analysis/hds5_chart24_elliptical.csv`
2. `docs/template-analysis/rectangular_partial_flow.csv`
3. `build_golden.py` — `add_data3_sheet` + updated `add_config_sheet` + updated `add_pipe_shape_columns`
4. `test_data3_sheet.py`
5. `partialflow_comparison_report.md`
6. Calculator dev HTML — rectangular branch in `pipeGeometry`, multi-barrel in `calcPipeRow`
7. Visualizer — no changes needed (consumes `pipeGeometry` output transparently)

## Estimate

- Phase A: 4–6 hours (digitization is the slow part)
- Phase B: 1–2 hours
- Phase C: 1 hour

Total ~1 day of focused work.

## Open question (for the future session)

If HDS-5 Chart 24 digitization proves hard (PDF doesn't contain tabular data, just the chart image), options:
- Use closed-form elliptical hydraulics (Ramanujan perimeter approximation + numerical integration of partial area) → ~10 Python lines; more accurate than chart-reading.
- Skip Phase A Task 1 and 2; ship Phase B (JS rectangular calc) only. Keep Spec 7's equivalent-D as the partial-flow method for all shapes.

Recommend: start with the closed-form elliptical option and skip the CSV digitization. Rectangular is closed-form by construction (open-channel Manning). This simplifies the whole spec.

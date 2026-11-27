# WIP Template Audit, Repair, and Rulebook Refresh

- **Date:** 2026-11-25
- **Status:** Complete — all 19 plan tasks shipped on `main` as of 2026-11-25 (commits `2e295b5` → `c2eb419`). 17/17 pytest tests pass; repaired xlsx has 0 `#REF!`, 0 broken names, 0 duplicate ranges. Manual Excel verification (T14 Step 3) deferred to user.
- **Next step:** **Spec 2 — Golden rulebook-aligned template.** Brainstorm a new xlsx built from a reproducible builder script, honoring the U1–U7 rulebook refresh landed here (MDSHA/MCDOT vs PG County junction rule, dcv4552 PG DPIE checklist criteria, small-area Tc lookup, weighted composite C). Slot in a `Config` sheet carrying `junctionAngleRule` (default `"smaller-loss"`) and `hglCrownCeilingRule` (default `"crown-plus-1ft"`) for Spec 3 to consume.
- **Author:** Khiem Hoang Nguyen (via Claude brainstorming)
- **Scope:** Spec 1 of 3. Follow-on specs (not written yet):
  - Spec 2 — Golden rulebook-aligned template (new xlsx produced by a reproducible builder).
  - Spec 3 — Calculator + visualizer two-template compatibility (import legacy + golden; implement the `junctionAngleRule` toggle).

## 1. Goal

Treat `docs/template_wip_new.xlsx` as the new "legacy" reference template for PG / MoCo / DC storm-drain design. Before using it as the basis for any downstream work:

1. Produce a per-tab analysis so every formula, dependency, and intent is captured in version-controlled markdown.
2. Repair the clearly broken formulas and workbook-name leftovers in place — without changing the sheet layout or user-facing look of the workbook.
3. Refresh the project rulebook (`engineering-methodology.md`, `storm-drain-calculator-spec.md`, `user-design-criteria.md`) to upgrade citations and document a jurisdiction toggle that Spec 3 will implement.

This spec produces **documentation + a repaired xlsx + a reproducible repair script**. No calculator code changes. The HTML calculator and visualizer are untouched.

## 2. Non-goals

- Changing the WIP template's sheet layout, column order, header labels, print layout, or visual styling.
- Designing the new golden rulebook-aligned template. That is Spec 2.
- Implementing the `junctionAngleRule` toggle in the calculator or visualizer. Spec 3 does that. Spec 1 only documents the setting name, defaults, and intent so Spec 3 can build against a known contract.
- Changing any computation in `drainage-calculator/storm-drain-design-calculator-dev.html`.
- Preserving the current broken HGL(25YEAR) formulas as-is. That sheet is dead; it gets rebuilt from the 10-year sheet's XLOOKUP pattern.

## 3. Context — what the WIP template looks like today

16 sheets. 3 real problems, 2 light issues, 1 watch-item. Verified via `openpyxl` scan on 2026-11-25:

| # | Severity | Where | What |
|---|---|---|---|
| 1 | Critical | `HGL(25YEAR)` | 680 `#REF!` formulas. Every data cell uses `OFFSET('STORM DRAIN COMPS'!#REF!,…)` — the OFFSET anchor was lost. Entire sheet is non-functional. The 10-year `HGL` sheet was migrated to clean `XLOOKUP(1, (A=$A7)*(B=$B7), …)` but the 25-year twin was never updated. |
| 2 | High | `INLET SPACING` AK column | 24 formulas of form `=IF(EXACT(#REF!, $S11), $R11, 0)` — looks like a dropped bypass/carryover lookup target. |
| 3 | Medium | Workbook names | 25 defined names resolve to `#REF!` (`\0 \c \e \p \r`, `_DUR1…_DUR18`, `_INT1 _INT2`) — orphans from the legacy template. No formula references them, so they are clutter, not breakage. |
| 4 | Low | Workbook names | `Select_County` and `SelectCounty` are duplicates (same range `DATA!$C$1:$C$4`). |
| 5 | High | Workbook calc props | `iterate = False` in the raw WIP. The HGL / Hx / cumulative-time chains depend on each row's From/To matching other rows (lateral array formulas like `MAX(IF($B$10:$B$98=$A10, $AQ$10:$AQ$98))`). Excel's static analyzer flags these as potentially circular even on correct acyclic networks, so with `iterate=False` the dependent cells (HGL columns G/K/M) open blank until a manual recompute. R5 flips `iterate` to True; R5-note warns users that this is a safeguard, not a license to enter loops. |

No real external workbook links remain (the `[filename.xlsx]…` issue from the legacy predecessor is already fixed). No formulas reference any of the 25 broken defined names.

**Core logic is sound.** `STORM DRAIN COMPS` is the single source of truth (Table4 at `A10:AR98`); `INLET SPACING`, `HGL`, `HGL(25YEAR)`, and the printable report sheets (`MCDOT PIPE COMPS-DESIGN`, `MCDOT INLET COMPS-DESIGN`, `MCDOT HGL-DESIGN`, `SHA SD-61.1-420-DESIGN`, `SHA (2-YR)SPREAD 61.1-491`, `SHA (25-YR)HGL 61.1-493`) all derive from it through `INDEX/MATCH` or `XLOOKUP`. Rational Method, pipe hydraulics (Manning full-flow, friction slope), Hx (junction loss) chain, structure loss, and the normal-depth `AT:BD` block are all computed on `STORM DRAIN COMPS`.

## 4. Rulebook — the audit criterion

Three documents define what the template "should" do:

- `docs/engineering-methodology.md` — governing equations (Rational, TR-55, Manning full-flow, friction loss, controlling-angle structure loss, HGL propagation, flow splitter, outlet structure).
- `drainage-calculator/storm-drain-calculator-spec.md` — the calculator's as-built contract (column semantics, dropdown values, HGL method toggle, export rules).
- `docs/user-design-criteria.md` — firm/reviewer conventions (pipe slope ≥ 1% < 24", ≥ 0.5% ≥ 24"; min 9" cover below subbase; `Crown_in ≥ Crown_out` at junctions).

Every formula noted in the per-tab analysis must cite the specific equation or rule it implements, by document and section.

## 5. Deliverables

### 5.1 Per-tab analysis (Section 1)

16 markdown files plus an index/README, under a new directory `docs/template-analysis/`:

```
docs/template-analysis/
  README.md                      ← overview + dependency diagram
  01-storm-drain-comps.md
  02-hgl.md
  03-hgl-25year.md
  04-inlet-spacing.md
  05-c-factor.md
  06-data.md
  07-data2.md
  08-mcdot-pipe-design.md
  09-mcdot-inlet-design.md
  10-mcdot-hgl-design.md
  11-sha-sd-420.md
  12-sha-2yr-spread.md
  13-sha-25yr-hgl.md
  14-pipe-schedule.md
  15-structure-schedule.md
  16-equations-instructions.md
```

**`README.md`** contains:
- One-paragraph purpose of the WIP template.
- A dependency diagram (ASCII or Mermaid) showing which sheets read from which.
- A roles table grouping the 16 sheets: working engine (4), data sources (6), printable reports (6).
- Links to each per-tab doc.

**Each per-tab doc** follows this fixed structure:

```markdown
# <SHEET NAME>

## Purpose
One sentence — why this sheet exists.

## Headers & ranges
The occupied range (e.g., A10:AR98), table objects (Table4, etc.), header rows.

## Inputs
User-typed cells, dropdown sources, named ranges read.

## Formulas
Grouped by column or by role. Each formula is cited to the rulebook:
- `T10 = Qfull` (engineering-methodology.md §3 Manning full-flow)
- `Y10 = Sf`    (engineering-methodology.md §4 friction slope)
- …

## Outputs
Which other sheets read from this one, and by which lookup key.

## Dependencies
Which sheets this one reads, and by which key.

## Issues found
Enumerated — severity, cell, description.

## Fix plan
Per-issue, what will be changed. Points to the Section 5.2 repair matrix.
```

The analysis is produced in two passes:
- **Pass A (automated extraction):** a helper Python script reads the xlsx with `openpyxl`, dumps sheet dimensions, Table definitions, defined-name usage, formula cell contents, `#REF!` counts, and cross-sheet reference graph into a structured JSON. Checked into git for diff reference.
- **Pass B (human-reviewed write-up):** 16 markdowns authored from the JSON, each with the fixed structure above. The Issues section lists everything that Section 5.2 will later repair, plus anything that is merely odd or non-obvious and needs documenting (not every oddity gets a repair).

### 5.2 Template repairs (Section 2)

Apply the five repairs below in place to `docs/template_wip_new.xlsx`, after preserving a backup copy as `docs/template_wip_new_pre-repair.xlsx`.

| ID | Target | Approach |
|---|---|---|
| **R1 — HGL(25YEAR) partial rebuild** | Rows 7–91, columns **A, B, C, D, E, F, H, L only** | Rebuild only the broken OFFSET-pattern columns. **Preserve** every intact column on this sheet: G (HGL chain MAX), I (25-year Sf computed on-sheet from columns U and V), J (Hf = H × I), K (upstream HGL with crown floor), M (HGL in From Str = K + Hb), O (10-year tailwater pull from `HGL!Q`), Q (pipe diameter from SDC N), R (A×C total from SDC J), S (pipe Tc from SDC K), T (25-year intensity from DATA), U (25-year Q = T × R), V (Manning n from SDC S). The sheet already implements correct 25-year flow and friction-slope computation; the broken cells are only the From/To/invert/crown/length/structure-loss lookups that lost their OFFSET anchor. Repaired broken columns use the same XLOOKUP pattern as the clean 10-year HGL sheet (`XLOOKUP(1, (SDC!$A:$A=$A7)*(SDC!$B:$B=$B7), SDC!<col>:<col>)`): A/B get From/To direct refs; C ← SDC $P (U/S invert); D = C + SDC N/12; E ← SDC $Q (D/S invert); F = E + SDC N/12; H ← SDC $O (pipe length); L ← SDC $AF (Hb) with the existing `"-"` guard. Row count matches HGL (rows 7–91). Header layout stays identical. |
| **R2 — INLET SPACING AK column** | `AK11:AK96` | Confirmed by the 04-inlet-spacing.md analysis: no sheet outside INLET SPACING references column AK or AL, so no downstream dependency to preserve. R2 clears the 24 AK formulas (sets them to None) and documents the finding in the analysis doc. |
| **R3 — Orphan defined names** | Workbook-scoped names: `\0 \c \e \p \r`, `_DUR1…_DUR18`, `_INT1 _INT2` | Remove. Verified during this spec — zero formula references them. |
| **R4 — Duplicate defined name** | `SelectCounty` | Delete. Keep `Select_County`. Verified — zero formulas reference `SelectCounty` (grep over all formula bodies in the current workbook). |
| **R5 — Iterative calc setting** | Workbook `calcProps` | Set `iterate = True` (iterateCount=100, iterateDelta=0.001). Correction vs the original Spec-1 R5 decision: empirical testing revealed that the HGL walking formulas (G/K/M on the HGL sheet, and the array-IF Tc aggregation on `STORM DRAIN COMPS!K`) use whole-column `IF(array)` patterns that Excel's static analyzer conservatively flags as potentially circular even on a correctly built acyclic network. With `iterate=False`, those cells open blank until a manual recompute — a severe usability bug. Add a note in the user-facing `EQUATIONS + INSTRUCTIONS` sheet explaining that From/To columns must still describe an acyclic pipe network; iterative calc being ON does NOT mean loops are OK (a genuine loop converges to an arbitrary value after a few iterations and masks the data-entry error). |

**Tooling.** All repairs land through one Python script, `docs/template-analysis/repair.py`, using `openpyxl`. The script:

1. Opens `docs/template_wip_new_pre-repair.xlsx` (the backup copy).
2. Writes the repaired file to `docs/template_wip_new.xlsx`.
3. Applies R1 → R4 deterministically. R5 is a documentation update inside `EQUATIONS + INSTRUCTIONS`, applied by the same script so the two stay in sync.
4. Exits with a non-zero code if any step fails (don't produce a partial file).

The script is checked into git. Re-running it reproduces the repaired workbook byte-for-byte modulo openpyxl's own output canonicalization — good enough for human diff review.

**Verification** after running `repair.py`:

1. Automated: re-run the `openpyxl` scan from Section 3 and confirm 0 `#REF!` formulas, 0 broken defined names, 0 external links, 0 duplicate names.
2. Manual: open `docs/template_wip_new.xlsx` in Excel for Microsoft 365, confirm no formula errors on `fullCalcOnLoad`, confirm `HGL(25YEAR)` populates the same shape of output as `HGL` when the sheet is left empty (both blank) and when a small 3-pipe sample project is populated end-to-end.
3. Manual: load the repaired template in Excel and populate a small 3-pipe sample (user's choice of structure IDs and inverts). Confirm the Rational columns, Manning full-flow, friction slope, Hx chain, INLET SPACING, 10-year HGL, and 25-year HGL all compute without `#VALUE!`, `#REF!`, or `#N/A`. `docs/template_wip_new_pre-repair.xlsx` carries a pre-populated sample (rows 10–21: I-3 → MH-4 → MH-3 → I-2 chain) that can be copied as a starting point.

### 5.3 Rulebook refresh (Section 3)

Four documentation updates. Zero code changes.

| Update | File | Change |
|---|---|---|
| **U1 — Junction-loss citation (primary)** | `docs/engineering-methodology.md` §5 "Structure Loss — Controlling-Angle Method" | Promote the MDSHA Drainage Manual, Ch. 5 "Storm Drain Systems" p. 5-26 (Sept 2023), Fig 5-8 and the surrounding procedure, to the primary state-wide upstream source. Name MCDOT §4.3.2.3 (p. 46, Revised Final, June 2014) as MoCo's adoption of that same procedure — the two documents share the rule verbatim: "If Lυ₁ is greater, υ₂ is the controlling angle" and "If Lυ₂ is greater, υ₁ is the controlling angle". Preserve the HEC-22 4th edition flow-weighted alternative disclosure already in the section. |
| **U2 — Junction-loss citation (mirror)** | `drainage-calculator/storm-drain-calculator-spec.md` §1.4 | Mirror the U1 citation change. Keep the one-sentence summary of the rule. |
| **U3 — PG County jurisdictional divergence** | `docs/engineering-methodology.md` §5.2 (new paragraph after the controlling-angle worked example) | Add: "The PG County Stormwater Management Design Manual, Chapter 8 'Storm Drain Design Criteria' (p. 8-27, Issue Date September 30, 2014) **states the opposite rule** in a numbered procedure: *'If H₂ is greater, Θ₂ is the controlling angle. If H₁ is greater, Θ₁ is the controlling angle'* — i.e., the *larger* hypothesized loss's angle controls. Appendix 8-15, Sample Headloss Calculation (DRAFT, July 26 2014) applies the Ch. 8 rule in its worked Example 2 (K₂ = 1.39 used because H₂ > H₁). Both agencies cite the same upstream MSHA form 61.1-408.0/408.1 Kb table; the divergence is in the *procedure*, not the coefficients. This is a real jurisdictional difference — not a transcription error — and must be honored per the agency reviewing the project. The tool defaults to the MDSHA / MCDOT rule and provides a project-level `junctionAngleRule` toggle (Spec 3) so PG-reviewed projects can select the PG Ch. 8 rule." |
| **U4 — Pipe-slope cross-reference** | `docs/user-design-criteria.md` "Pipe slope (longitudinal)" | Add a parenthetical cross-reference to MCDOT §4.3.3(k): "15 and 18 inch diameter pipe are to be designed on an actual slope of 1 percent or greater." Our `< 24"` threshold is slightly more conservative (catches 21" too) and this is intentional — reviewers and users should know the state rule it generalizes. |
| **U5 — Jurisdiction-toggle intent** | `docs/engineering-methodology.md` §5.2 (new subsection "Jurisdiction toggle (Spec 3)") and `storm-drain-calculator-spec.md` §1.4 (matching note) | Document, for Spec 3 to build against, the `junctionAngleRule` project-level setting. Values: `"smaller-loss"` (MDSHA Ch. 5 / MCDOT §4.3.2.3 — default), `"larger-loss"` (PG County SWM Ch. 8, p. 8-27). Scope: a single project-level value — never per-structure. Mixing rules inside one project would not pass review. Default: `"smaller-loss"` regardless of selected county. No county-driven implicit default — a county change must not silently change hydraulics; the toggle stays explicit and auditable. xlsx placement: the golden template's new `Config` sheet (Spec 2); the WIP legacy template has no home for it, so legacy-template imports default to `"smaller-loss"`. Formulas affected: only the 2-inflow junction branch of `computeStructureCalc`. All other inflow counts (0, 1, >2) are unaffected. The toggle is **not optional** — both rules are codified in current, in-force agency design criteria, and PG-reviewed projects must be able to compute with PG's rule. |
| **U7 — Small-area Tc lookup + weighted C** | `docs/user-design-criteria.md` (new "Time of concentration" and "Weighted runoff coefficient" sections) | Both MoCo and PG County allow a C-factor lookup for Tc on drainage areas ≤ 2 acres, and both require area-weighted composite C across subareas. Add: (a) **Tc for small areas** — MCDOT §3.2.1 Table 3-3 "Small Drainage Area Time of Concentration": for A ≤ 2.0 acres, Tc is selected from a lookup keyed on the composite C-factor: C ≥ 0.80 → Tc = 5 min; 0.65 ≤ C ≤ 0.79 → Tc = 7 min; 0.40 ≤ C ≤ 0.64 → Tc = 10 min; C ≤ 0.39 → Tc = 15 min. For A > 2 acres, Tc is computed via TR-55 segmental or an equivalent segment-based method (`Tc = Tt + (L − 100) / (60 V)` per MCDOT Eq. 3-1 for the trailing travel-time segment). PG SWM Ch. 8 §8.2.2 carries the same two-track approach. (b) **Weighted composite C** — MCDOT §3.4: `C_weighted = Σ(Cx × Ax) / A_total` across land-use subareas; PG SWM Ch. 8 §8.2.1: "C factors for development shall represent a weighted average based upon the proportion of the surface area covered by impervious materials, lawns, or woods." The WIP template's `C_FACTOR` sheet already implements the weighted-C computation (column M) and a Table 3-3 lookup for Tc (column I) per catchment. Calculator-side disclosure: the HTML calculator's Drainage Area tab takes C and Tc as direct user inputs today; document that for small areas the user may enter Tc per Table 3-3 (and the composite C per §3.4), and flag that a future Spec may auto-populate either from a land-use breakdown. |
| **U6 — PG DPIE checklist criteria** | `docs/user-design-criteria.md` (new sections) | Pull calculator-relevant engineering criteria from the *PG County DPIE Storm Drain & Paving Design Review Checklist* (`docs/dcv4552_design-review-checklist-storm-drain-and-paving-pdf.pdf`, Last Edited June 27, 2013). Add these new sections and items: (a) **Minimum pipe size** — PG C-19: 15" for main-line public systems, with ESD/SWM diversions permitted smaller. (b) **Minimum pipe cover** — PG G-8: 1 ft above crown for RCP, 2 ft for flexible pipes (distinct from the existing "9 inch below subbase" structural rule). (c) **Minimum structure drop** — PG G-9: 0.1 ft min drop through a structure; also cite MCDOT §4.2.4(a) "1% or 0.1 ft, whichever greater". (d) **Max access spacing** — PG C-20: 400 ft between manholes/access; cross-reference MCDOT Table 4-5 which varies with pipe size (400 ft for 15–24", 500 ft for 27–42", 600 ft for ≥48"). (e) **Pipe-entering-flat-wall angle** — PG C-21: ≤ 45°. (f) **Last pipe reach to outfall** — PG H-6: slope ≤ 1% (use drop structures if needed to achieve). (g) **Open-channel erosion velocity** — PG L-4: rip-rap or concrete required if channel velocity > 5 fps (cut) or > 4 fps (fill). (h) **HGL clearance — jurisdictional divergence disclosure.** MCDOT §4.3.1 caps the 10-year HGL at BOTH crown + 1 ft AND rim − 1 ft. PG C I-2 only caps at rim − 12", with no explicit crown ceiling (pipes may surcharge within the structure). Our calculator currently enforces the MCDOT crown + 1 ft rule; disclose the PG difference analogous to the `junctionAngleRule` disclosure, flagged as a future Spec 3 toggle (`hglCrownCeilingRule` — `"crown-plus-1ft"` default, `"rim-only"` for PG). Also add supporting PG citations on existing rules already in the file: PG G-6 on pipe slope (matches our rule verbatim), PG G-10 on crown matching (matches our rule verbatim), PG I-2 on rim clearance (matches our rim − 1 ft). Items explicitly out of scope: plan-drafting checks (A/B sections), roadway geometry (D), easements (E), paving sections (O/P/Q/R) — the calculator does not model these. |

> **U7 correction (landed in Spec 3 pre-work):** the WIP `C_FACTOR` sheet does **not** hold a Table 3-3 Tc lookup on column I — column I is "Imp. Area (Ac)" (consumed by composite-C on column M). Spec 2 Edit 5 places the Table 3-3 lookup on column **W** (golden template only; blank in legacy WIP). See `docs/template-analysis/05-c-factor.md` for the empirically verified column-by-column breakdown.

## 6. Dependency diagram of the WIP template

```
                    DATA (IDF curves, dropdowns)
                       |                  |
                       v                  v
                 INLET SPACING     STORM DRAIN COMPS  <----- C_FACTOR
                                   (Table4 A10:AR98)         (runoff coef)
                                         |
                       +-----------------+------------------+
                       |                 |                  |
                       v                 v                  v
                     HGL (10yr)   HGL(25YEAR)       MCDOT PIPE COMPS-DESIGN
                     (XLOOKUP)    (OFFSET #REF!)    MCDOT INLET COMPS-DESIGN
                                                    MCDOT HGL-DESIGN
                                                    SHA SD-61.1-420-DESIGN
                                                    SHA (2-YR)SPREAD 61.1-491
                                                    SHA (25-YR)HGL 61.1-493
                                                           |
                                                           v
                                                    DATA2 (Y/D lookup for
                                                    normal-depth)

                     PIPE SCHEDULE       (hand-maintained inventory, no formulas in)
                     STRUCTURE SCHEDULE  (hand-maintained inventory, no formulas in)
                     EQUATIONS + INSTRUCTIONS (reference text only)
```

`STORM DRAIN COMPS` is the hub. Every HGL and printable report derives from it.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| R1 rebuild of HGL(25YEAR) picks the wrong 25-year column from `STORM DRAIN COMPS`. The sheet has AH ("Design Storm Normal Depth") and AI ("SHA 25-Year Normal Depth") — mixing them would produce wrong friction slope. | The per-tab analysis in Section 5.1 enumerates every `STORM DRAIN COMPS` column by row-8 header text and documents which column feeds which downstream sheet. The repair script references columns by header-text match, not by letter, so a column insertion in the source cannot silently retarget the formula. |
| R2 reconstruction guesses wrong at what AK was supposed to compute. | Per-tab analysis documents AK's intent *before* repair runs. If intent cannot be recovered from surrounding context + the pre-repair snapshot `docs/template_wip_new_pre-repair.xlsx`, the column is deleted (option b in the repair matrix) rather than fabricated. |
| Removing orphan defined names breaks a feature that references them in a way the openpyxl scan missed (e.g., a chart series, data validation source, hidden sheet reference). | The repair script runs a final `openpyxl` round-trip pass that flags any workbook element referencing a removed name. If anything is flagged, the removal is reverted for that name and the exception is logged in the analysis doc. |
| Excel for Microsoft 365 rejects the `openpyxl`-written workbook (openpyxl occasionally emits structure Excel repairs on open). | Verification step 2 opens the file in Excel; if Excel reports "we found a problem" and repairs the workbook, the delta is diffed against the openpyxl output and the script updated to match Excel's expected layout. |
| Rulebook citation changes contradict something already committed elsewhere in `docs/` (e.g., the HGL-method-toggle design doc, the 2026-11-06 bburg-xlsx-redesign design doc). | Spec implementation includes a `grep` sweep of `docs/` for references to the controlling-angle citation; any prior write-up gets a one-line update pointing to the refreshed engineering-methodology.md section. |

## 8. Out of scope (summary)

- All code changes to `drainage-calculator/storm-drain-design-calculator-dev.html`.
- The `junctionAngleRule` toggle's UI, data-model field, computation branch, xlsx read/write, and visualizer parity (Spec 3).
- The golden rulebook-aligned new template and its builder script (Spec 2).
- Any change to inlet spread hydraulics beyond repairing the INLET SPACING AK column.
- Pond outlet rating curves in xlsx. Tailwater remains a user-typed elevation per storm.

## 9. Acceptance checklist

Spec 1 is done when:

- [ ] `docs/template-analysis/README.md` + 16 per-tab docs exist and cover every sheet in `template_wip_new.xlsx` using the fixed structure in §5.1.
- [ ] `docs/template_wip_new_pre-repair.xlsx` is committed as the backup.
- [ ] `docs/template_wip_new.xlsx` passes the `openpyxl` scan with 0 `#REF!` formulas, 0 broken defined names, 0 external links, 0 duplicate names.
- [ ] `docs/template_wip_new.xlsx` opens cleanly in Excel for Microsoft 365 and computes the 3-pipe sample project end-to-end without errors on any sheet.
- [ ] `docs/template-analysis/repair.py` is committed and re-runs without manual intervention.
- [ ] `docs/engineering-methodology.md`, `drainage-calculator/storm-drain-calculator-spec.md`, and `docs/user-design-criteria.md` reflect updates U1–U7.
- [ ] No change to any file under `drainage-calculator/` other than the `storm-drain-calculator-spec.md` citation refresh.
- [ ] The repo CLAUDE.md remains under 200 lines (per the standing project constraint).

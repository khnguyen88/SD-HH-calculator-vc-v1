# Golden Rulebook-Aligned Template

- **Date:** 2026-11-25
- **Status:** Design approved; awaiting user review before implementation plan.
- **Author:** Khiem Hoang Nguyen (via Claude brainstorming)
- **Scope:** Spec 2 of 3. Follows Spec 1 (`2026-11-25-template-wip-audit-design.md`). Precedes Spec 3 — Calculator + visualizer two-template compatibility.

## 1. Goal

Produce `docs/template_golden.xlsx` by applying a small set of structured edits to the Spec-1 repaired `docs/template_wip_new.xlsx`. The golden template honors the U1–U7 rulebook refresh landed in Spec 1 and exposes three project-level toggles on a new `Config` sheet that Spec 3's calculator + visualizer will read when importing xlsx projects:

- `junctionAngleRule` — `smaller-loss` (default, MDSHA Ch. 5 / MCDOT §4.3.2.3) or `larger-loss` (PG County SWM Ch. 8 p. 8-27).
- `hglCrownCeilingRule` — `crown-plus-1ft` (default, MCDOT §4.3.1) or `rim-only` (PG C I-2).
- `hglMethod` — `HEC-22 EGL (d/s crown floor)` (default, mirrors the HTML-calculator toggle landed 2026-11-09) or `legacy both-end crown floor`.

High fidelity to WIP: same 16 sheets, same column letters, same print layouts. Reviewers see "the same template with three new settings and tighter citations."

## 2. Non-goals

- No calculator or visualizer code changes. Spec 3 reads the Config toggles; Spec 2 ships the contract.
- No rewrite of HGL-walking logic. `hglMethod` is **label-only in xlsx** for Spec 2 — Config stores it, the HGL sheets show it on the printed area for audit, but xlsx HGL computation continues using the WIP's existing method until Spec 3. `junctionAngleRule` and `hglCrownCeilingRule` **do** drive xlsx formulas; `hglMethod` doesn't yet.
- No sheet-layout changes, no print-layout changes, no sample data. Builder ships an empty golden template.
- No new per-tab template-analysis docs for `Config` — `EQUATIONS + INSTRUCTIONS` carries the on-sheet disclosure; §3.1 of this spec is the source-of-truth schema.

## 3. Deliverables

1. `docs/template-analysis/build_golden.py` — builder script (flat module, function-per-edit, `main(src, dst)` CLI; mirrors Spec-1's `repair.py`).
2. `docs/template-analysis/test_build_golden.py` — pytest suite (one class per edit + a workbook-wide invariants class). Extends the shared `conftest.py` fixture established in Spec 1.
3. `docs/template_golden.xlsx` — generated output, committed to git.
4. `docs/template-analysis/calculator-import-contract.md` — the Spec 3 read/write contract for both the latest sample template (`template_wip_new.xlsx`) and the golden template.
5. `docs/template-analysis/README.md` — append `build_golden.py` under the **Scripts** section; update sheet-count note from 16 to "16 (WIP) / 17 with `Config` (golden)."

## 4. Config sheet schema

New sheet named `Config`, placed **last** in the tab order (after `EQUATIONS + INSTRUCTIONS`) so no existing print-sheet tab index shifts. Sheet tab color: amber.

Layout (fixed cells; builder writes them literally):

| Cell | Content |
|---|---|
| `A1` | `Project-level design-rule toggles — DO NOT DELETE. Read by Spec 3 calculator/visualizer import.` (merged `A1:C1`, bold) |
| `A3` | `junctionAngleRule` |
| `B3` | `smaller-loss` *(default)* |
| `C3` | `MDSHA Drainage Manual Ch. 5 "Storm Drain Systems" (Sept 2023); MCDOT §4.3.2.3 (June 2014). PG County SWM Ch. 8 p. 8-27 (Sept 30 2014) states the opposite rule — set to "larger-loss" for PG-reviewed projects. The WIP template's prior default behavior matches "larger-loss"; the golden default is "smaller-loss" (MDSHA primary source).` |
| `A4` | `hglCrownCeilingRule` |
| `B4` | `crown-plus-1ft` *(default)* |
| `C4` | `MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft. PG C I-2 caps only at Rim − 12" (no explicit crown ceiling) — set to "rim-only" for PG-reviewed projects.` |
| `A5` | `hglMethod` |
| `B5` | `HEC-22 EGL (d/s crown floor)` *(default)* |
| `C5` | `HTML calculator toggle landed 2026-11-09 (HEC-22 vs legacy both-end crown floor). Label-only in Spec 2; Spec 3 wires xlsx HGL computation to this toggle.` |
| `E3:E4` | `smaller-loss`, `larger-loss` (hidden helper; backs B3 data validation) |
| `F3:F4` | `crown-plus-1ft`, `rim-only` |
| `G3:G4` | `HEC-22 EGL (d/s crown floor)`, `legacy both-end crown floor` |

**Data validation.** `B3`/`B4`/`B5` carry `DataValidation(type='list')` sourced from `$E$3:$E$4` / `$F$3:$F$4` / `$G$3:$G$4`. Invalid-input alert set to `stop` (reviewer protection).

**Workbook-scoped named ranges** (via `openpyxl.workbook.defined_name`):

| Name | Refers to |
|---|---|
| `junctionAngleRule` | `=Config!$B$3` |
| `hglCrownCeilingRule` | `=Config!$B$4` |
| `hglMethod` | `=Config!$B$5` |

Naming is JS-friendly camelCase (not display labels) — Spec 3's calculator parses these as object keys.

**Styling.** Row 1 bold, merged `A1:C1`. Row 2 blank spacer. Column A bold, right-aligned. Column B monospace, light-yellow fill (editable signal). Column C wrap-text, italic, gray (informational, not editable). Columns E:G hidden. Column widths: `A=22`, `B=38`, `C=70`, `E:G=24`.

## 5. Edit catalog

Six top-level functions in `build_golden.py`, applied in order. All are idempotent — re-running on an already-built file reproduces the output.

### 5.1 `add_config_sheet(wb)`

Creates the `Config` sheet per §4. If `Config` already exists, replace in place (idempotency). Must run **first**; subsequent edits reference the named ranges.

### 5.2 `rewire_junction_angle_rule(wb)`

Rewrites the controlling-angle formula on `STORM DRAIN COMPS`, column `AD`, rows 10–98.

**Current (WIP, PG-style "larger-loss" by default):**

```excel
AD10 = MAX(IF($AQ$10:$AQ$98 = $AR10, $R$10:$R$98))
```

where `AR10 = MAX(IF($B$10:$B$98=$A10, $AQ$10:$AQ$98))` picks the max hypothesized Lv, and column `R` (inflow-pipe angle per `01-storm-drain-comps.md`) is picked by matching that max Lv.

**New (toggle-aware, default = smaller-loss = MDSHA):**

Introduce a helper column `AR_min` carrying the MIN of positive Lv entering this structure. Location: `AJ` if the builder's pre-flight scan finds `AJ` unreferenced by any formula; otherwise a new column after `BD` (first free slot — likely `BE`). The builder's §6 R2 scan is authoritative.

```excel
AR_min10 = MIN(IF(($B$10:$B$98=$A10)*($AQ$10:$AQ$98>0), $AQ$10:$AQ$98))

AD10 =
  IF( junctionAngleRule = "smaller-loss",
      MAX(IF(($B$10:$B$98=$A10)*($AQ$10:$AQ$98=AR_min10), $R$10:$R$98)),
      MAX(IF($AQ$10:$AQ$98=$AR10, $R$10:$R$98)) )
```

The outer `MAX(...)` in each branch collapses the ambiguous case where two inflows tie on Lv — picks the larger angle, a stable tiebreak. Rows 10–98 get the same template with row index substitutions.

**Behavior change.** Default flips from the WIP's PG-style (`MAX` of Lv's angle) to MDSHA-style (`MIN` of Lv's angle). Matches Spec 1 U1's primary-source decision. Existing projects that need the old answer flip `Config!B3` to `larger-loss`. The commit message flags this as an intentional behavior change.

### 5.3 `add_hgl_crown_ceiling_checks(wb)`

Adds three columns to `HGL` and `HGL(25YEAR)`, immediately after each sheet's existing last used column (determined at build time by scanning the header row):

| New column | Formula (per data row) | Meaning |
|---|---|---|
| `Crown+1ft Check` | `=IF(<HGL>−<Crown_up> > 1, "FAIL", "OK")` | MCDOT clearance (always computed) |
| `Rim−1ft Check` | `=IF(<Rim>−<HGL> < 1, "FAIL", "OK")` | Common clearance both agencies share (always computed) |
| `Clearance Governing` | `=IF(hglCrownCeilingRule="crown-plus-1ft", IF(OR(<CrownCheck>="FAIL",<RimCheck>="FAIL"),"FAIL","OK"), <RimCheck>)` | Which rule governs the project |

Cell addresses for `<HGL>`, `<Crown_up>`, `<Rim>` are resolved at build time by header-text match against `02-hgl.md` / `03-hgl-25year.md` conventions. If header text drifts on later WIP revs, the edit emits a deterministic warning. **Print area** on both sheets is extended via `ws.print_area` update to cover the three new columns.

### 5.4 `annotate_hgl_method(wb)`

On both HGL sheets, write to the first empty cell to the right of the header-row project-metadata block (typically row 2 or 3, col ~`H`):

```excel
="HGL method: " & hglMethod
```

Bold, italic, right-aligned. Appears on every printed copy as a top-of-sheet audit stamp.

### 5.5 `add_u7_small_area_tc_lookup(wb)`

On `C_FACTOR`, for data rows 6–88:

1. **Inspect `I6:I88`.** Blank → add the formula. Pre-existing formula referencing `D`/`M` → treat as "already there," skip silently. Anything else (constant, text, unrelated formula) → skip and append the row index to a warning summary printed by `main`.
2. **Lookup formula (MCDOT Table 3-3):**

```excel
I6 =
  IF( D6="", "",
    IF( D6>2, "",
      IF( M6>=0.80, 5,
        IF( M6>=0.65, 7,
          IF( M6>=0.40, 10, 15 )))))
```

- `D6` — total area in acres (existing).
- `M6` — composite C (existing; already prefers user override `R` via `IFERROR` chain).
- Returns a number for A ≤ 2 acres, blank otherwise.

Column `V` (user-typed Tc) remains the authoritative Tc that `STORM DRAIN COMPS!E` reads via `VLOOKUP(..., col 21)`. Column `I` is **advisory**: engineer sees the Table-3-3 suggestion and types the chosen Tc in `V`. Spec 2 does **not** rewire `STORM DRAIN COMPS!E` to prefer `I` — that's a product decision for later.

Column `I` header row gets `"Tc (Table 3-3, small-area)"`.

### 5.6 `annotate_equations_sheet(wb)`

Append to `EQUATIONS + INSTRUCTIONS`:

```
=== Design-Rule Toggles (Config sheet) ===
• junctionAngleRule = {live cell: =junctionAngleRule}
  Controlling-angle procedure at 2-inflow junctions.
  MDSHA Ch. 5 / MCDOT §4.3.2.3: smaller Lv's angle controls  [smaller-loss, default]
  PG SWM Ch. 8 p. 8-27 (Sept 30 2014): larger H's angle controls  [larger-loss]
  Set on Config!B3. Affects STORM DRAIN COMPS!AD (controlling angle) and all downstream Hb.

• hglCrownCeilingRule = {live cell: =hglCrownCeilingRule}
  HGL vertical-clearance ceiling.
  MCDOT §4.3.1: HGL ≤ Crown + 1 ft AND HGL ≤ Rim − 1 ft  [crown-plus-1ft, default]
  PG C I-2: HGL ≤ Rim − 12" only (pipes may surcharge within the structure)  [rim-only]
  Set on Config!B4. Affects HGL and HGL(25YEAR) "Clearance Governing" column.

• hglMethod = {live cell: =hglMethod}
  HGL-walk method.
  HEC-22 EGL (d/s crown floor) — HEC-22 §7.4 standard  [HEC-22, default]
  Legacy both-end crown floor — firm historical convention  [legacy]
  Set on Config!B5. Label-only in this template; Spec 3 wires xlsx HGL computation.

=== Citation refresh (Spec 1 U1-U7) ===
• Junction-loss primary source — MDSHA Drainage Manual Ch. 5 p. 5-26 (Sept 2023), Fig 5-8
  (mirrored by MCDOT §4.3.2.3 p. 46, Revised Final June 2014).
• Pipe slope — MCDOT §4.3.3(k) (15" and 18" ≥ 1.0%); our rule < 24" ≥ 1.0% is a touch
  more conservative (catches 21" too) — intentional.
• Time of concentration for small areas (≤ 2 acres) — MCDOT §3.2.1 Table 3-3:
  C ≥ 0.80 → 5 min; 0.65–0.79 → 7; 0.40–0.64 → 10; ≤ 0.39 → 15.
• Composite C — MCDOT §3.4 area-weighted; PG SWM Ch. 8 §8.2.1 same intent.
• PG DPIE checklist items affecting calculator-visible rules: C-19 (15" min pipe),
  G-8 (min cover: 1 ft RCP, 2 ft flexible), G-9 (0.1 ft min drop through structure),
  C-20 (400 ft max access spacing; MCDOT Tbl 4-5 varies by size), C-21 (≤ 45° pipe-to-
  flat-wall), H-6 (last reach to outfall ≤ 1%), L-4 (channel armoring v > 5 fps cut /
  4 fps fill), I-2 (HGL ≤ Rim − 1 ft; the crown-ceiling toggle disclosure).
```

The `{live cell: =<name>}` entries are *actual* `=junctionAngleRule` / `=hglCrownCeilingRule` / `=hglMethod` formulas in adjacent cells — engineers see the live value without flipping to `Config`. Idempotent: scan for the "Design-Rule Toggles (Config sheet)" header before appending; if present, replace the block in place.

## 6. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Spec-1 U7 asserted `C_FACTOR!I` already holds a Table 3-3 Tc lookup; `05-c-factor.md` lists only D/M/O/P/R as formula-bearing. If `I` actually contains user-typed data, Edit 5 would overwrite it. | Edit 5 inspects every `I6:I88`: blank → add formula; pre-existing formula referencing D/M → leave untouched; anything else → skip that row and log. Test accepts either outcome as pass. |
| R2 | `AJ` column on `STORM DRAIN COMPS` is documented as pass-through `Table4[Column43]` with semantic TBD. If something reads `AJ`, Edit 2's helper clobbers it. | Builder scans `A10:BD98` for formula references to `$AJ` or `AJ10:AJ98`; if any exist, fall back to the first free column after `BD` (likely `BE`). Test doesn't hard-code the letter — asserts the helper cell exists at the chosen column. |
| R3 | Flipping the default `junctionAngleRule` from WIP's PG-style `MAX` to MDSHA-style `smaller-loss` is a real behavior change. | (a) Config `C3` citation explicitly spells out the prior behavior and how to restore it; (b) `test_wip_has_max_pattern_originally` fails loudly if the WIP's AD formula is ever revised upstream; (c) commit message flags the default flip as **behavior change**. |
| R4 | Three new columns on `HGL` / `HGL(25YEAR)` could push past the print area; reviewers wouldn't see the clearance verdict on hard copies. | Edit 3 extends `ws.print_area`. `test_print_area_extended` asserts it. Manual verification step 2 prints a sample page. |
| R5 | `Config` sheet added last (tab index 17); any external script hard-coding "16 sheets" breaks silently. | `test_sheet_count_and_order_unchanged_plus_config` enforces the 17-sheet invariant. README updated in Deliverable 5. Import contract reads by name, not index. |
| R6 | Three new named ranges collide with an existing defined name. | Builder checks `wb.defined_names` first; on collision, raises with the colliding name. Spec-1 cleaned the namespace (25 orphans + 1 dup removed) — defensive only. |
| R7 | Builder "mutates WIP in place" implicitly picks up future WIP tweaks; a WIP change could invisibly alter golden output. | `wip_source` fixture asserts the source file's SHA-256 against a hash pinned in `conftest.py`. When WIP is intentionally changed, the hash is updated in the same commit, forcing a review of whether golden still builds correctly. |

## 7. Calculator import contract (Deliverable 4)

File: `docs/template-analysis/calculator-import-contract.md`. Defines the exact read/write path Spec 3's calculator and visualizer will follow for **both** xlsx shapes — the latest sample template (`template_wip_new.xlsx`, no `Config`) and the golden template (`template_golden.xlsx`, with `Config`).

**Shape detection.** Calculator reads `wb.defined_names`. If `junctionAngleRule` exists → golden (honors Config toggles). Else → legacy WIP (uses the three toggle defaults: `smaller-loss`, `crown-plus-1ft`, `HEC-22 EGL (d/s crown floor)`). One branch, no heuristic sniffing.

**Toggle values (golden only).**
- `junctionAngleRule` → `smaller-loss | larger-loss` (default `smaller-loss`).
- `hglCrownCeilingRule` → `crown-plus-1ft | rim-only` (default `crown-plus-1ft`).
- `hglMethod` → `HEC-22 EGL (d/s crown floor) | legacy both-end crown floor` (default `HEC-22 EGL (d/s crown floor)`).

**Pipe-row read path** (both shapes — identical, Spec 2 doesn't restructure `STORM DRAIN COMPS`):

| Source | Target field |
|---|---|
| `STORM DRAIN COMPS!Table4` rows 10–98, column `A` | `fromId` |
| col `B` | `toId` |
| col `N` | `pipeDiameterIn` |
| col `O` | `pipeLengthFt` |
| col `P`, `Q` | `invertUsFt`, `invertDsFt` |
| col `R` (fallback `S`) | `manningN` |
| col `AA` | `structureType` |
| col `AB` | `rimElevFt` |
| col `AG`, `AH` | `inflowAngle1Deg`, `inflowAngle2Deg` |
| col `AK` | `lateralFlowCfs` |
| `STORM DRAIN COMPS!T3` | `jurisdiction` |
| `STORM DRAIN COMPS!H3` | `designStormYr` |

**Drainage-area read path** (both shapes):

| Source | Target field |
|---|---|
| `C_FACTOR!B6:B88` | `rowId` (join key) |
| col `C` | `areaSf` |
| col `M` (fallback `R`) | `compositeC` |
| col `V` | `tcMin` (authoritative) |

Golden's new `I` column (Table 3-3 Tc lookup) is **advisory — calculator does not read `I`.** Documented explicitly so Spec 3 never silently prefers it over `V`.

**HGL sheets are not read on import** — calculator computes HGL itself from the imported pipe rows. HGL / HGL(25YEAR) are review artifacts, not persistence.

**Sheets the calculator ignores on import:** all six print-report sheets, `PIPE SCHEDULE`, `STRUCTURE SCHEDULE`, `DATA`, `DATA2`, `EQUATIONS + INSTRUCTIONS`, `INLET SPACING` (intentional — inlet-spread stays in xlsx).

**Export (Spec 3 reverse direction, documented here so read/write stay co-located):** calculator writes back into `STORM DRAIN COMPS` + `C_FACTOR` input columns only (A, B, N, O, P, Q, R, S, AA, AB, AG, AH, AK; C, V) plus the three `Config` named ranges if present. All formula-driven columns are left untouched — reopening the file in Excel recomputes them.

**Versioning.** Contract doc carries `Contract-Version: 1` header. Spec 3 and the calculator both read this; any future shape change bumps the version.

## 8. Testing / verification plan

One pytest file: `docs/template-analysis/test_build_golden.py`. Shared `conftest.py` fixture extended from Spec 1.

**Fixtures.**
- `wip_source` (session) — path to `docs/template_wip_new.xlsx`; asserts SHA-256 against pinned hash in `conftest.py`.
- `golden_built` (session) — runs `build_golden.main(wip_source, tmp_golden_path)` once; returns the loaded workbook.
- `golden_built_twice` (session) — runs builder on its own output; returns both for idempotency diff.

**Test classes.**

- `TestConfigSheet`: exists-and-last, three named ranges, defaults, data validation lists, tab color.
- `TestJunctionAngleFormula`: `AD10` references `junctionAngleRule`, formula applied rows 10–98, helper column populated at builder-chosen location, chosen helper cell was empty in WIP, control test — WIP's AD contained `MAX` before edit.
- `TestHglClearanceChecks`: three new columns on each HGL sheet by header match, governing column references `hglCrownCeilingRule`, `print_area` extended, no existing formula overwritten.
- `TestHglMethodAnnotation`: annotation cell present on both HGL sheets, inside print area.
- `TestCFactorSmallAreaTc`: `I6:I88` either has builder formula or pre-existing formula preserved, header set, column `V` untouched.
- `TestEquationsInstructionsAnnotation`: toggles section header present, citations section header present, live-toggle references present as formulas.
- `TestWorkbookInvariants`: 0 `#REF!`, 0 broken names, 16 original sheets in order + `Config` last, every WIP formula still present or explicitly replaced by a known edit (drift catcher), builder is idempotent (second-run matches first).

**Manual verification** (deferred to user, same model as Spec 1 T14):

1. Open `docs/template_golden.xlsx` in Excel for Microsoft 365 — no repair prompts.
2. On `Config`, flip `junctionAngleRule` to `larger-loss`. On `STORM DRAIN COMPS` with a 2-inflow structure populated, observe `AD` value change. Flip back.
3. On `Config`, flip `hglCrownCeilingRule` to `rim-only`. On `HGL`, observe `Clearance Governing` change on a row where `Crown+1ft Check = FAIL` but `Rim−1ft Check = OK`. Flip back.
4. On `Config`, flip `hglMethod`. Confirm top-of-sheet annotation updates on `HGL`. Confirm HGL numbers themselves do **not** change (label-only in Spec 2).
5. Populate the 3-pipe sample from `docs/bburg-xlsx-user-guide.md`; confirm all sheets compute cleanly.

## 9. Acceptance checklist

Spec 2 is done when:

- [ ] `docs/template-analysis/build_golden.py` exists, documented, exposes `main(src, dst)` CLI.
- [ ] `docs/template-analysis/test_build_golden.py` exists; all tests pass.
- [ ] `docs/template-analysis/calculator-import-contract.md` exists and covers both the latest sample template (`template_wip_new.xlsx`) and the golden template (`template_golden.xlsx`).
- [ ] `docs/template_golden.xlsx` is committed and passes the `openpyxl` scan: 0 `#REF!`, 0 broken defined names, 0 external links, 17 sheets (original 16 + `Config` last), 3 new named ranges (`junctionAngleRule`, `hglCrownCeilingRule`, `hglMethod`).
- [ ] `docs/template-analysis/README.md` updated: `build_golden.py` listed under **Scripts**; sheet-count note updated to "16 (WIP) / 17 with Config (golden)."
- [ ] Manual Excel verification completed OR deferred to user with that status recorded on the acceptance commit.
- [ ] No change to any file under `drainage-calculator/`.
- [ ] `CLAUDE.md` remains under 200 lines (standing project constraint).
- [ ] Commit message for the default flip of `junctionAngleRule` flags it as an intentional **behavior change** so `git log` makes it findable.

## 10. Out of scope (summary)

- All code changes to `drainage-calculator/storm-drain-design-calculator-dev.html` and the visualizer (Spec 3).
- The xlsx HGL walking logic — `hglMethod` is label-only here; Spec 3 does the HGL-formula surgery.
- Any change to inlet-spread hydraulics in `INLET SPACING`.
- Pond outlet rating curves in xlsx. Tailwater remains a user-typed elevation per storm.
- Any new sheet layout or print-layout change.

# Three-Shape Bidirectional Calculator + Visualizer

- **Date:** 2026-11-26
- **Status:** Design approved; awaiting user review before implementation plan.
- **Author:** Khiem Hoang Nguyen (via Claude brainstorming)
- **Scope:** Spec 3 of 3. Follows Spec 1 (template WIP audit) and Spec 2 (golden template). Final spec in the storm-drain workbook sequence before the feature work (shape-column support, partial-flow explainer) in Spec 4+.

## 1. Goal

Make the HTML calculator and visualizer both read and write two template shapes:

- **Simple shape** — legacy WIP (`template_wip_new.xlsx`) and golden (`template_golden.xlsx`). Same read/write surface; golden adds `Config` toggles.
- **Robust shape** — a new native calculator export that uses the Simple shape's sheet layout as its base and appends four Robust-only sheets (outlet work, TR-55 segments, rainfall settings).

The Robust template visually matches the Simple template (fonts, borders, colors, print layout). Users see "the same Simple workbook with bonus tabs" when they open a Robust export.

Shape detection is automatic on import; export shape is chosen by a toggle in the UI.

Spec 3 also wires `hglMethod` to actual HGL formulas (Spec 2 left it label-only) and lands two small pre-work items: DATA2 cleanup and two doc corrections.

## 2. Non-goals

- **No pipe-shape column on STORM DRAIN COMPS.** Elliptical and rectangular pipe support (shape + rise/height columns, shape-branching hydraulics formulas, per-shape partial-flow tables) is deferred to Spec 4. Simple reader forces `shape="circular"`; Robust reader respects the native shape field.
- **No partial-flow explainer app.** Interactive teaching tool for circular-pipe partial flow deferred to its own spec after Spec 3 ships.
- **No new sample projects in the visualizer.** The two built-in samples (`project_visualizer_samples`) stay as JSON; Spec 3 doesn't touch them.
- **No rewrite of the Simple template's existing formulas** beyond the HGL method wiring (§7) and the DATA2 cleanup (§3).
- **No K-column XLOOKUP single-match fix on junctions.** Still mitigated by the disclosure note, not fixed. Documented as a carried limitation.

## 3. Pre-work (ships as one commit before Phase 1)

### 3.1 DATA2 cleanup — Conservative

Scope: clear content from `DATA2!D1:L101` on both `template_wip_new.xlsx` and `template_golden.xlsx`. Columns A–C untouched (values + headers preserved). VLOOKUP ranges on STORM DRAIN COMPS stay as `$A$2:$D$101` — all 178 formulas untouched.

Rationale verified empirically today (`docs/template-analysis/_scan_data2_deep.py`):

- 89 VLOOKUPs use `col_index=2` (reads B, `y/d₀`); 89 use `col_index=3` (reads C, `A/d₀²`).
- Zero formulas use `col_index=1` or `col_index=4`. Column D is never read — it's completely empty in both templates.
- Columns E–H duplicate the live `DATA!A68:D159` Kb table but with angle 0° missing (90 rows vs 91). No live reference.
- Columns J–L are the inverse of A–C (keyed on `y/d₀`). 99/100 rows match the reverse; row 82 has a transcription typo (`L82 = 0.0382`, should be `0.3082`). No live reference.

**Implementation.** `docs/template-analysis/cleanup_data2.py` — openpyxl script, loads WB, clears cells on D–L rows 1–101, saves. Idempotent.

**Repair script integration.** `repair.py` extended with a DATA2-cleanup pass so future repair runs apply the cleanup automatically. Keeps Spec 1's "repair produces correct file at WIP path" contract intact.

**Test.** `test_cleanup_data2.py` — asserts D–L empty in both outputs; A–C values unchanged against pre-cleanup snapshot; VLOOKUP formulas unchanged in string form.

### 3.2 Doc corrections

**`docs/template-analysis/01-storm-drain-comps.md`**: change column R label from "Manning's n" to "Angle Out of Pipe (Deg) - Whole #"; change column S label to "Manning Coeff / Manning's n". Verified empirically against `STORM DRAIN COMPS!R8` (`'Angle Out of Pipe (Deg) - Whole #'`) and `S8` (`'Manning Coeff'`).

**`docs/template-analysis/05-c-factor.md`**: strike the claim that column I holds a Table 3-3 Tc lookup. Correction: *"Column I is 'Imp. Area (Ac)' (consumed by composite-C on column M). The Table 3-3 Tc lookup lives on column W (added by Spec 2 Edit 5)."* Verified against `C_FACTOR!I5` (`'Imp. Area (Ac)'`) and `C_FACTOR!W6` (formula is the Tc lookup, present in golden only).

Same correction added to the Spec-1 U7 citation note if still live; brief grep to confirm location.

### 3.3 Verification scripts

Three underscore-prefixed Python scripts written during brainstorming stay in `docs/template-analysis/` as auxiliary verifications:
- `_scan_data2.py` — DATA2 structure + reference count
- `_scan_headers.py` — SDC col R/S + C_FACTOR col I/W header verification
- `_scan_data2_deep.py` — VLOOKUP col_index audit + Kb/reverse-table comparisons

Not test-wired. Useful for future audits.

### 3.4 Pre-work commit

```
docs(template): DATA2 cleanup + doc corrections (Spec 3 pre-work)

- Clear unused DATA2 columns D, E-H, J-L in WIP and golden.
  VLOOKUP ranges on SDC untouched; A-C preserved.
- Update repair.py to apply the cleanup on future runs.
- Correct 01-storm-drain-comps.md: col R is angle, col S is Manning's n.
- Correct 05-c-factor.md: col I is Imp. Area, col W holds Tc lookup.
```

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  USER                                                       │
│    ↕ export toggle (Simple | Robust)                        │
│    ↕ import (any shape)                                     │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  CALCULATOR (storm-drain-design-calculator-dev.html)        │
│                                                             │
│   importExcel(file) ──┐                                     │
│      │                └─ detectShape(wb) ──┬─ simple        │
│      │                                     ├─ robust        │
│      ▼                                     └─ unknown→toast │
│   state (unchanged internal model) ◄───────┘                │
│      │                                                      │
│   exportExcel(shape) ─┬─ buildSimpleWorkbook(state)         │
│      │                └─ buildRobustWorkbook(state)         │
│      ▼                                                      │
│    .xlsx file                                               │
└─────────────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  VISUALIZER (storm-drain-visualizer-dev.html)               │
│   same detectShape + simple/robust readers                  │
└─────────────────────────────────────────────────────────────┘
```

**Core idea.** Keep the calculator's internal `state` schema untouched. Shape detection and schema mapping happen at the xlsx boundary only. Two readers, two writers, one state.

**Shape detection rule** (single function, shared between calculator and visualizer):

```
1. wb.SheetNames contains "STORM DRAIN COMPS"?
     a. ALSO contains "Outlet Structures"? → "robust"
     b. Else                                → "simple"
2. Else                                     → "unknown" (toast error)
```

**Why sheet-presence over named-range detection.** Named ranges are easy to miss across readers (openpyxl vs SheetJS expose `defined_names` differently). The legacy WIP has no named ranges at all. Sheet-presence is reliable and the fallback cascade still routes correctly.

**Why Robust = Simple + extras.** The user's "structural + visual merge" decision: Robust exports include STORM DRAIN COMPS and everything Simple has, plus four Robust-only sheets. A Robust file can be opened and reviewed by anyone expecting a Simple template (they just see extra tabs). The Simple reader also works on a Robust file (reads the Simple sheets, ignores the extras).

## 5. Simple reader

Detects a Simple-shape xlsx, extracts rows into the calculator's existing `state` model, applies the three Config toggles (golden) or their defaults (legacy WIP).

### 5.1 Read surface

Per `calculator-import-contract.md` §3–§4, verified empirically today:

| Source | Calculator state field | Notes |
|---|---|---|
| `STORM DRAIN COMPS!A{r}` | pipe `fromId` | blank rows skipped |
| `STORM DRAIN COMPS!B{r}` | pipe `toId` | |
| `STORM DRAIN COMPS!N{r}` | pipe `size` | diameter in inches |
| `STORM DRAIN COMPS!O{r}` | pipe `length` | ft |
| `STORM DRAIN COMPS!P{r}` | pipe `upstreamInvert` | |
| `STORM DRAIN COMPS!Q{r}` | pipe `downstreamInvert` | |
| `STORM DRAIN COMPS!R{r}` | pipe `angle` | Deg — header is "Angle Out of Pipe (Deg) - Whole #" |
| `STORM DRAIN COMPS!S{r}` | pipe `n` | Manning coeff |
| `STORM DRAIN COMPS!AA{r}` | structure `type` | Inlet / Manhole / Bend / Junction / Flow Splitter / Outfall |
| `STORM DRAIN COMPS!AB{r}` | structure `rim` | |
| `STORM DRAIN COMPS!AG{r}` | optional 2-inflow junction angle 1 | used for junction-loss cross-check |
| `STORM DRAIN COMPS!AH{r}` | optional 2-inflow junction angle 2 | |
| `STORM DRAIN COMPS!AK{r}` | structure `capturedQ` override | user-typed lateral |
| `STORM DRAIN COMPS!T3` | `state.hydraulics.jurisdiction` | "MCDOT" / "MDSHA" / etc. |
| `STORM DRAIN COMPS!H3` | `state.rainfall.pipeStorm` | design frequency |
| `C_FACTOR!B{r}` | drainage area `structureId` (join key) | matches SDC col A |
| `C_FACTOR!C{r}` | drainage area `area` | acres |
| `C_FACTOR!M{r}` | drainage area `C` | composite C (prefers override on R via existing IFERROR) |
| `C_FACTOR!V{r}` | drainage area `tc` | minutes — authoritative |
| `Config!B3` (golden only) | `state.hydraulics.junctionAngleRule` | default: `smaller-loss` |
| `Config!B4` (golden only) | `state.hydraulics.hglCrownCeilingRule` | default: `crown-plus-1ft` |
| `Config!B5` (golden only) | `state.hydraulics.hglMethod` | default: `HEC-22 EGL (d/s crown floor)` |

All pipe-row data on `STORM DRAIN COMPS`, rows 10–98. Drainage data on `C_FACTOR`, rows 6–88. A row is considered blank when its key column is empty (`STORM DRAIN COMPS!A{r}` for pipe rows, `C_FACTOR!B{r}` for drainage rows) — such rows are skipped in the reader loop.

### 5.2 Structures-from-pipes derivation

Simple templates have no dedicated Junction Structure sheet — all structure data lives on STORM DRAIN COMPS columns AA/AB plus the From/To pipe endpoints. The reader materializes `state.structures` by:

1. Collect distinct `{fromId, toId}` IDs across all non-blank pipe rows → initial structure set.
2. For each structure, read its row-anchored metadata from the pipe row where `A{r} == structureId` (type on AA, rim on AB, captured override on AK).
3. For the outfall (the one toId with no outgoing row), type defaults to `outfall` if AA is blank.

### 5.3 Round-trip-loss semantics on Simple import

Fields in the calculator's internal model that Simple xlsx doesn't persist (cleared on Simple import):

- `state.outletStructures`, `state.outletDevices`, rating curves (no outlet work on Simple).
- `state.drainage[].tr55.segments` (Simple stores computed `tc` on `C_FACTOR!V`; loses segment detail).
- `state.rainfall.customNoaa` / `fetchedNoaa` (Simple keeps selected county + storm; loses custom NOAA).
- Splitter metadata beyond the structure-type column.

**Toast on Simple import.** *"Imported Simple template. Outlet structures, TR-55 segments, and custom NOAA data were not in the file."*

### 5.4 Error handling

- Unknown shape → toast: *"Couldn't detect template shape. This file should be a WIP template, golden template, or calculator export."*
- Shape detected but required column blank on all rows → specific toast naming the sheet.

## 6. Robust template structure

Robust = Simple's full sheet layout + four Robust-only sheets, all sharing Simple's cell styling (fonts, borders, column widths, print margins, freeze panes, header colors, number formats).

### 6.1 Sheet inventory

| # | Sheet | Source | Role |
|---|---|---|---|
| 1 | `STORM DRAIN COMPS` | **shared** | pipe + structure hydraulics (rows 10–98) |
| 2 | `HGL` | **shared** | hydraulic grade line walk |
| 3 | `HGL(25YEAR)` | **shared** | 25-yr check (when enabled) |
| 4 | `C_FACTOR` | **shared** | drainage area composite C + Tc (rows 6–88) |
| 5 | `INLET SPACING` | **shared** | HEC-22 inlet spread |
| 6 | `DATA` | **shared** | static lookups (live Kb table, Table 4-6, Manning n table) |
| 7 | `DATA2` | **shared** | partial-flow table (post-cleanup: A–C only) |
| 8 | `Config` | **shared, extended** | toggles + Robust metadata (see §6.2) |
| 9 | `EQUATIONS + INSTRUCTIONS` | **shared** | reference text |
| 10 | `MCDOT PIPE COMPS-DESIGN`, `MCDOT INLET COMPS-DESIGN`, `MCDOT HGL-DESIGN` | **shared** | MCDOT print sheets |
| 11 | `SHA SD-61.1-420-DESIGN`, `SHA (2-YR)SPREAD 61.1-491`, `SHA (25-YR)HGL 61.1-493` | **shared** | SHA print sheets |
| 12 | `PIPE SCHEDULE`, `STRUCTURE SCHEDULE` | **shared** | hand-maintained inventories |
| 13 | `TR-55 Segments` | **Robust-only** | per-drainage-area travel-time segments |
| 14 | `Outlet Structures` | **Robust-only** | BMP/SWM facility list |
| 15 | `Outlet Devices` | **Robust-only** | all devices, flat-tagged by facility |
| 16 | `Rating - <label>` | **Robust-only** | one sheet per outlet structure |
| 17 | `Rainfall Settings` | **Robust-only** | custom + fetched NOAA data |

### 6.2 Config sheet (extended)

| Cell | Named range | Value |
|---|---|---|
| `B1` | `projectName` | from `state.project` |
| `B2` | `exportTimestamp` | ISO 8601 at export time |
| `B3` | `junctionAngleRule` | `smaller-loss` \| `larger-loss` |
| `B4` | `hglCrownCeilingRule` | `crown-plus-1ft` \| `rim-only` |
| `B5` | `hglMethod` | `HEC-22 EGL (d/s crown floor)` \| `legacy both-end crown floor` |
| `B6` | `templateShape` | `simple` \| `robust` (self-describing) |
| `B7` | `contractVersion` | `2` (matches `calculator-import-contract.md`) |

Columns `C` (citations), `E:G` (dropdown helpers) unchanged from Spec 2. Row labels on column A, bold + right-aligned. Values on column B, light-yellow fill (editable).

### 6.3 Robust-only sheet layouts

Match the current calculator native export (`buildWorkbook()` in `storm-drain-design-calculator-dev.html`) but restyled to the Simple template's visual language:

- **`TR-55 Segments`** — 10 columns: Drainage Area / Order / Type / n / L / s / P2 / Surface / Area a / Pw. Flat table, tagged by Drainage Area ID. Header row 1, styled as Simple's row-8 header convention (dark background, white text, merged where applicable).
- **`Outlet Structures`** — 12 columns: Outlet Structure ID / Label / Description / Precision Mode / Start Elev / End Elev / Coarse Inc / Fine Inc / Fine Band / TW Mode / TW Fixed / TW Linked Structure ID. One row per facility.
- **`Outlet Devices`** — 17 columns: Device ID / Outlet Structure / Label / Type / Invert / Crest / Diameter / Diameter Unit / Length / Length Unit / Weir Shape / Notch Angle / Coefficient / Fine Override Enabled / Fine Increment Override / Fine Band Override / Notes. Flat, tagged by Outlet Structure.
- **`Rating - <label>`** — one per outlet facility. `2 + 6·nDevices + 1` columns: Stage / Tailwater / per-device {alpha, A, centroid, head, regime, Q} / Total Q. Formulas on Tailwater (when linked) and Total Q; values on per-device columns.

### 6.4 Styling strategy — build from golden as a base

`buildRobustWorkbook()` loads the embedded `template_golden.xlsx` bytes (base64), fills in the live rows on shared sheets, appends Robust-only sheets using golden's cell-style conventions, and writes the result.

**Why this over programmatic styling.** Preserves every detail of Simple's visual format (merged header rows, borders, fonts, number formats, print layout, freeze panes) with zero style-definition code. Any future Simple-template style update propagates to Robust automatically.

**File size cost.** `template_golden.xlsx` is ~250 KB; base64 adds ~33% → ~335 KB. Current built HTML is ~1.5 MB. New total ~1.85 MB. Acceptable for an offline single-file tool.

**Dev workflow.** `build.js` reads `docs/template_golden.xlsx`, base64-encodes it into a `TEMPLATE_GOLDEN_B64` constant at the top of the inlined script section, alongside SheetJS. Change the template → rebuild → new bytes embedded.

### 6.5 Robust-only sheet styling

The four Robust-only sheets use a shared SheetJS style object (defined once in the dev HTML, reused across sheets) that matches Simple's visual tokens:
- Header rows: Simple's row-6-to-8 header fill color (navy or dark gray — exact token read from golden at build time).
- Monospace numeric columns using the same font Simple uses on SDC columns.
- Thin borders, frozen top row.
- Print orientation landscape when column count > 10 (TR-55 Segments, Outlet Devices, Rating curves); portrait for Outlet Structures.

Exact style tokens get captured during Phase 2 implementation by reading the golden template's cell styles via openpyxl, then codified as a reusable `ROBUST_SHEET_STYLE` object in the dev HTML.

## 7. Simple writer + toggle UI

### 7.1 Writer approach

`buildSimpleWorkbook(state)` uses the same embed-golden-as-base pattern as Robust. Loads `TEMPLATE_GOLDEN_B64` as an array buffer, parses with SheetJS, fills the Simple write-surface columns, writes.

**Write surface — input columns only, never formula-driven cells:**
- `STORM DRAIN COMPS!A, B, N, O, P, Q, R, S, AA, AB, AG, AH, AK`
- `STORM DRAIN COMPS!T3` (jurisdiction) and `H3` (design storm)
- `C_FACTOR!B, C, V` (and `R` when the simple two-zone composite C override is in use)
- `Config!B1` (project name), `B2` (timestamp), `B3:B5` (three toggles), `B6` (`simple`), `B7` (contract version `2`)

Reader ignores HGL and print-sheet cells on both ends — Excel recomputes them from the inputs when the file opens, powered by the golden template's live formulas (iterate=True already wired by Spec 2).

### 7.2 Write-side lossiness (Robust state → Simple file)

Lost on Simple export:
- `state.outletStructures`, `state.outletDevices`, rating curves.
- `state.drainage[].tr55.segments` (computed `tc` is kept on `C_FACTOR!V`; segment detail lost).
- `state.rainfall.customNoaa` / `fetchedNoaa` (keeps selected county + storm; loses custom NOAA).
- Splitter metadata beyond the AA structure-type column.

**Toast on Simple export.** *"Exported Simple template. Outlet structures, TR-55 segments, custom NOAA data, and splitter settings are not stored in this format — export as Robust to preserve them."*

### 7.3 Toggle UI

Small radio-button toggle next to the existing "Export to Excel" button in the top bar:

```
┌──────────────────────────────────────────────────┐
│ Project: [________]          [Import] [Export]   │
│                              Shape: ●Simple ○Robust│
└──────────────────────────────────────────────────┘
```

**State.** Toggle choice persists in `state.exportShape` (`"simple"` or `"robust"`). Default `"robust"` for new sessions. On Import, the imported shape sets the toggle (imported a Simple file → toggle flips to Simple).

**Why not auto-choose by state content.** Explicit toggle lets users intentionally down-grade (sharing with a non-calculator colleague) or up-grade (started from WIP, added outlet work, export as Robust). Matches the user's explicit instruction: *"user can toggle the export, app auto-detects the import."*

**Localstorage snapshots.** Current quick-save (≤5 snapshots) stays unchanged — serializes `state` directly. The toggle is part of `state` so it round-trips.

**Mobile.** On narrow breakpoints, the toggle collapses into the existing hamburger menu as two tap targets: "Export shape: Simple" / "Export shape: Robust."

## 8. HGL method wiring on xlsx

### 8.1 Current state (what Spec 2 shipped)

- `Config!B5` holds the method name.
- HGL `P3` header stamp displays the method.
- HGL walking formulas (cols G/K/M) use a fixed "legacy both-end crown floor" calculation regardless of `Config!B5`.
- The native Robust export (shape #1 pre-rewrite) already honors the toggle in its `Junction Structure!Q` formula. Simple + Spec-2 golden do not.

### 8.2 Two method families

| `hglMethod` value | HGL formula approach |
|---|---|
| `HEC-22 EGL (d/s crown floor)` | Chain `HGL_upstream = HGL_downstream + Hf + Hb`, downstream floored at the downstream pipe crown. Standard MDSHA/HEC-22. |
| `legacy both-end crown floor` | Both-end crown pin: `HGL_i = MAX(chain_i, crown_i_upstream, crown_i_downstream)`. More conservative; matches pre-repair WIP behavior. |

### 8.3 Implementation

Replace HGL columns G (downstream HGL), K (walked upstream HGL), M (controlling HGL) with branching formulas keyed off the `hglMethod` named range.

**Pattern (row `r`, schematic):**

```
G{r} = IF(hglMethod = "legacy both-end crown floor",
          MAX(<chain-input>, <downstream-crown>, <upstream-crown>),
          MAX(<chain-input>, <downstream-crown>))
```

Where `hglMethod` is the workbook-scoped named range at `Config!$B$5`, and `<chain-input>`, `<downstream-crown>`, `<upstream-crown>` keep their Spec-2 XLOOKUP sources.

**Why `IF`-based branching rather than two separate sheets.** One HGL sheet stays the source of truth. The P3 stamp and the live formulas both read the same named range; changing the toggle in Excel recomputes HGL without switching sheets. iterate=True handles the recalc.

### 8.4 Named-range canonical form

All HGL formulas use the bare name `hglMethod` rather than the cell reference `Config!$B$5`. Safer against row shifts; more readable in Excel's formula inspector.

### 8.5 25-year HGL sheet (`HGL(25YEAR)`) — identical treatment

Same `IF(hglMethod = ...)` branching pattern applied to `HGL(25YEAR)` columns G/K/M. Both sheets honor the toggle identically.

### 8.6 Pre-existing Spec 2 toggles — unchanged

Spec 2 Edit 2 (`junctionAngleRule` on SDC AD / AE / AF) and Edit 3 (`hglCrownCeilingRule` on HGL V / W / X) already drive formulas. Spec 3 does not touch them.

### 8.7 Verification

1. Open Spec-3 golden template in Excel 365 — no repair prompts.
2. Flip `Config!B5`; confirm HGL col M values change on rows where upstream crown ≠ downstream crown.
3. Confirm the `P3` stamp updates in sync.
4. Export from calculator as Simple-shape → open → HGL populates on both toggle values.
5. Cross-check against `docs/template-analysis/hgl-reference-values.md` for `legacy both-end crown floor` (should match pre-repair cache baseline exactly).

## 9. Visualizer parity

### 9.1 Shared reader module

Extract Simple + Robust reader logic from the calculator into a plain JS module inlined into both HTML builds:

```
drainage-calculator/lib/xlsx-shape-reader.js
```

Exports:

```js
detectShape(wb)                   // → "simple" | "robust" | "unknown"
readSimpleWorkbook(wb)            // → state fragment (pipes, structures, drainage, config)
readRobustWorkbook(wb)            // → readSimple + outlet/tr55/rainfall extras
hglMethodFromLabel(label)         // → "hec22" | "legacy-both-crown"
```

`build.js` inlines this module into both `storm-drain-design-calculator-dev.html` and `storm-drain-visualizer-dev.html`. One source of truth; no copy-paste.

### 9.2 Visualizer state adapter

Visualizer's internal model is simpler than the calculator's (no splitter metadata, no TR-55, no outlet device detail — visualizes HGL, doesn't recompute flow). Reader returns a superset; visualizer's import glue picks the subset:

| Reader field | Visualizer use |
|---|---|
| `structures[]` (id, label, type, rim, startElev, crown, elevation, Hb, totalQ) | Nodes |
| `pipes[]` (fromId, toId, shape, size, n, slope, length, angle, designQ, usInvert, dsInvert, Hf) | Edges with profile geometry |
| `outfall.structureId, tailwaterElev` | HGL anchor |
| `drainageAreas[]`, `tr55Segments[]` | Not used |
| `config.hglMethod` | Drives visualizer's internal HGL walk |

### 9.3 HGL method handling in the visualizer

Visualizer walks HGL on its own (doesn't load Excel's eval engine). It already implements HEC-22 and legacy-both-crown walks. Reading `config.hglMethod` from Config!B5 (or the import-time default for legacy WIP) tells it which walk to use.

Mapping handled by `hglMethodFromLabel()` in the shared reader:
- `"HEC-22 EGL (d/s crown floor)"` → `hec22`
- `"legacy both-end crown floor"` → `legacy-both-crown`
- WIP (no Config, no named range) → default `hec22`

### 9.4 Sample projects

Unchanged. The two built-in samples (`project_visualizer_samples`) are JSON; Spec 3 doesn't touch them.

### 9.5 Error handling

Unknown shape toast: *"Couldn't read this xlsx. Use a calculator export, a golden template, or a legacy WIP file."*

Shape detected but incomplete (e.g., no pipes in `STORM DRAIN COMPS` A:B columns): specific toast naming the issue.

## 10. Testing

### 10.1 Automated (pytest)

Each extends the shared `conftest.py` fixture from Spec 1 + Spec 2.

- **`test_shape_detect.py`** — detectShape returns correct value for all four fixtures (legacy WIP, Spec-2 golden, Spec-3 golden, calculator Robust export).
- **`test_simple_reader.py`** — reads each Simple fixture, asserts state fields match expected values.
- **`test_robust_reader.py`** — reads a Robust export, asserts outlet/TR-55/rainfall extras also populate.
- **`test_simple_writer.py`** — builds Simple xlsx from a seeded state; reads back; round-trip equality on the write surface.
- **`test_robust_writer.py`** — same for Robust, plus Robust-only sheet population.
- **`test_hgl_method_formula_branches.py`** — formulas on HGL cols G/K/M contain both method branches.
- **`test_hgl_method_round_trip.py`** — flip Config!B5; HGL values change as expected.
- **`test_cleanup_data2.py`** — DATA2 pre-work verification.
- **`test_visualizer_reader_parity.py`** — visualizer's inlined reader produces the same state fragment as the calculator's.

### 10.2 Manual (Excel 365)

- Golden template opens without repair prompts.
- Flip each Config toggle; verify SDC/HGL recompute live.
- Open a Simple export; HGL + print sheets populate without manual refresh.
- Open a Robust export; HGL + print sheets populate; Robust-only sheets look stylistically consistent with Simple sheets.
- Compare HGL values against `hgl-reference-values.md` for `legacy both-end crown floor`.
- Round-trip: export Simple → edit in Excel → import → values round-trip to state.
- Round-trip: export Robust → edit in Excel → import → values + extras round-trip.

## 11. Implementation phases

| Phase | Deliverable | Ship gate |
|---|---|---|
| Pre-work | DATA2 cleanup + doc corrections (§3) | §3 tests pass |
| 1 | Simple reader on calculator (§5) | Imports legacy WIP and golden into correct state |
| 2 | Robust template rebuild — `buildRobustWorkbook` (§6) | Export → open in Excel → styled like Simple + Robust extras populate |
| 3 | Simple writer + toggle UI (§7) | Export → open → HGL+prints populate; lossy-export toast shown |
| 4 | HGL method wiring on xlsx (§8) | `Config!B5` flip changes HGL values in Excel |
| 5 | Visualizer parity — shared reader module (§9) | Visualizer imports both shapes |

Each phase = one PR, reviewed, merged, and deployed to gh-pages before the next phase starts.

## 12. Known limitations carried forward

- **Pipe shape column on STORM DRAIN COMPS.** Elliptical and rectangular pipe support deferred to Spec 4.
- **K-column XLOOKUP single-match at junctions.** Still mitigated by disclosure note, not fixed. Same as Spec 1 + Spec 2 state.
- **Partial-flow explainer app.** Deferred to its own spec.

## 13. Contract version

`docs/template-analysis/calculator-import-contract.md` bumps from `Contract-Version: 1` to `2`. Changes:

- **New §3a** — native-shape (Robust) pipe-row read path. Mirrors §3's table using Robust sheet names.
- **New §4a** — native-shape drainage-area read path. Mirrors §4.
- **Updated §1** — two-shape detection with an `unknown` fallback (sheet-presence rule, see §4 of this spec): returns `"simple"` for both legacy WIP and golden, `"robust"` for calculator-native Robust files, `"unknown"` otherwise.
- **Updated §7** — two write paths (Simple and Robust).

## 14. Success criteria

- Calculator imports any of: legacy WIP, golden (Spec-2 or Spec-3), calculator Robust export, calculator Simple export.
- Calculator exports either Simple (golden shape) or Robust (new Simple+extras shape) via the toggle.
- Robust export visually matches Simple export (fonts, borders, colors, print layout, header styling).
- Config!B5 (`hglMethod`) drives HGL computation in Excel for both shapes.
- Visualizer imports any of the above.
- All existing Spec-1 + Spec-2 pytest tests pass unchanged.
- Zero `#REF!` errors in any exported file.

## 15. Open items the implementation plan must resolve

1. **Exact style tokens for Robust-only sheets.** Inspect golden template cell styling (fonts, borders, number formats, header colors) via openpyxl and codify as a reusable SheetJS style object. Phase 2 work.
2. **`build.js` template embedding.** Node script reads `docs/template_golden.xlsx`, base64-encodes, injects into the dev HTML as `const TEMPLATE_GOLDEN_B64 = "...";`. Verified file-size impact (~335 KB) acceptable.
3. **Contract-Version bump.** Update `calculator-import-contract.md` per §13.

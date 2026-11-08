# HGL/EGL Visualizer — v1 Gap Closure Design

**Status:** approved design, pending implementation plan
**Date:** 2026-11-08
**Companion to:** `2026-11-07-hgl-egl-visualizer-design.md` (the shipped v1 spec)
**Source of gaps:** `docs/superpowers/plans/2026-11-07-hgl-egl-visualizer/plan.md` §"Known gaps and follow-up work"

## 0. Non-negotiable constraints

- Edit only `drainage-calculator/storm-drain-visualizer-dev.html`; rebuild with
  `node drainage-calculator/build-visualizer.js`.
- The built file stays one self-contained offline HTML (SheetJS inlined, no CDN,
  no external `src`/`href`). The built file stays untracked.
- No new runtime dependencies; browser-only vanilla JS + SVG.
- Keep the 43 existing visualizer tests green.
- Dark engineering aesthetic, monospace numerics, system fonts.
- One task = one commit; no LLM attribution trailers.

## 1. Scope

Close the seven gaps recorded in the v1 plan:

1. Splitter detection, warning banner, primary-path-only walk.
2. Missing Design Q warning.
3. Multi-outfall auto-detection and a "Walk from…" switcher.
4. TR-55 segment visualization on the profile.
5. Printable calc-sheets for the visualizer ledger.
6. Iso flow-direction arrows.
7. Selection glow.

One spec, one implementation plan. The work is additive; no renderer rewrite.

## 2. Decisions

| Question | Decision |
|---|---|
| Spec scope | All seven gaps, one spec |
| TR-55 treatment | **Callout cards** anchored to each structure (option C) |
| Warning delivery | **Inline amber banner** below the toolbar (option A) |
| Walk-from contents | **All structures**, grouped outfalls-first |
| Print scope | **Current walked path only**, expanded calc-sheets + header |
| Implementation shape | **Post-import analysis pass** producing `state.analysis` |

## 3. Data model changes

### 3.1 Pipe import additions

The main-app `Pipe Sizing` export already carries a `Split Role` column
(`"" | "primary" | "secondary"`). The XLSX importer adds:

```js
splitRole: String(pick(r["Split Role"], r.splitRole) || "").toLowerCase()
```

`Design Q (cfs)` changes from `num(..., 0)` to `pickNum(...)` so a blank cell is
preserved as `null` rather than a fake zero. Numeric `0` remains valid and is
not a warning.

### 3.2 Optional imported sheets / fields

XLSX reads two sheets it currently ignores:

`Drainage Area` → `imported.drainageAreas[]`

```js
{
  id: String(r["ID"] || ""),                 // DA id (NOT the linked structure)
  structureId: String(r["Structure"] || ""), // linked structure label
  areaAc: pickNum(r["Area A (ac)"]),
  C: pickNum(r["C"]),
  tc: pickNum(r["Tc (min)"])
}
```

`TR-55 Segments` → `imported.tr55Segments[]`

```js
{
  drainageAreaId: String(r["Drainage Area"] || ""),
  order: pickNum(r["Order"]),
  type: String(r["Type"] || "").toLowerCase(), // sheet | shallow | channel
  n: pickNum(r["n"]),
  L: pickNum(r["L (ft)"]),
  s: pickNum(r["s (ft/ft)"]),
  P2: pickNum(r["P2 (in)"]),
  surface: pick(r["Surface"]) || "",
  area: pickNum(r["Area a (sf)"]),
  wp: pickNum(r["Wetted Perimeter Pw (ft)"])
}
```

Both arrays default to `[]` when the sheet is absent. The JSON sidecar accepts
the same optional `drainageAreas` and `tr55Segments` arrays, and
`pipes[].splitRole`; the validator checks them only when present (wrong type =
validation error, absent = empty). The tweaked-JSON export copies all three
through unchanged; none are editable in the ledger.

File name is captured on import into `state.ui.fileName` for the print header.

### 3.3 Analysis pass

`analyzeImported(imported)` runs once at the end of both importers (after
auto-layout, before cursor reset) and stores a derived, read-only
`state.analysis`:

```js
{
  outfallIds: [],                    // every type:"outfall", import order
  defaultWalkStart: "OUTFALL"|null,  // first outfall; else lowest startElev/rim; else first structure
  splitterIds: [],                   // every type:"splitter"
  primaryPipeByStructureId: {},      // splitter id → splitRole:"primary" pipe id
  missingDesignQ: [],                // pipe ids whose designQ is null / non-finite
  tr55ByStructureId: {},             // structure id → [{ daId, tc, segments:[...] }]
  walkStarts: []                     // [{ id, label, type, group:"outfall"|"structure" }]
}
```

Rules:

- `defaultWalkStart` is the **first outfall in import order**, not the lowest
  elevation. The real fixture's true root is `OUTFALL` at 100.0; `BYPASS` at
  97.0 is a secondary branch, so "lowest" would pick wrong. Fallback when no
  outfall exists: structure with the lowest finite `startElev`, then `rim`,
  then first structure.
- `primaryPipeByStructureId` is built for splitter structures only: the pipe
  whose `splitRole === "primary"`, else the first outgoing pipe in import order.
- `missingDesignQ` includes `null`, `undefined`, and non-finite values.
- `tr55ByStructureId` joins `tr55Segments[].drainageAreaId` → `drainageAreas[]`
  by `id`, then attaches that DA's segments to `drainageAreas[].structureId`.
  A DA with no linked structure is dropped from the overlay.
- `analyzeImported(null)` returns `null`.
- Analysis runs on import only. Ledger overrides do not change network topology.

### 3.4 Walk start and boundary elevation

Walk start becomes UI state: `state.ui.walkStartId`, initialized to
`analysis.defaultWalkStart`. `state.imported.outfall` remains the imported
declaration, untouched by the switcher.

`buildLedger(path, resolvedState, ...)` resolves the start row from
`resolvedState.ui.walkStartId`, falling back to
`resolvedState.imported.outfall` when the analysis or UI field is absent. This
keeps the existing direct-unit tests (which pass plain state objects) working.

Boundary EGL for the walk start:

1. `type === "outfall"` → imported tailwater elevation
   (`imported.outfall.tailwaterElev`, already resolved from Outlet Structures
   when linked).
2. else `forceElev && startElev != null` → `startElev`.
3. else `crown != null` → `crown`.
4. else `rim != null` → `rim`.
5. else `0`.

The start ledger row's label and detail name the start structure and its
boundary reason (`tailwater`, `fixed elevation`, `crown boundary`, or
`rim boundary`).

## 4. Feature designs

### 4.1 Warning banner

A static `<div id="warningBanner">` sits directly below `.topbar`. It is
rendered from `state.analysis` after each import and is hidden when empty.

- One row per splitter: `Flow splitter S-2 — following primary path only`.
  If the splitter had no `primary` role, append
  `(no primary role; using first outgoing pipe)`.
- One aggregated row when `missingDesignQ.length > 0`:
  `No Design Q: P-3, P-8 — friction shown as 0.000 ft`.
- `details ▾` expands a per-item list (splitter downstream pipes, each missing-Q
  pipe). `×` dismisses for the current import via
  `state.ui.warningsDismissed`.
- Any new import resets `warningsDismissed` and re-renders the banner.
- Amber styling consistent with the override badge; no modal, never blocks.

### 4.2 Walk-from switcher

Toolbar `<select id="walkFromSelect">` appended to `.topbar`:

- `<optgroup label="Outfalls">` lists `analysis.walkStarts` with
  `group === "outfall"`.
- `<optgroup label="Structures">` lists the rest.
- Default selection is `ui.walkStartId`.
- On change: set `ui.walkStartId`, reset `state.cursor` to the new start,
  clear `state.ui.branchChoices.byStructureId`, re-render everything.

When only one outfall and no other structures exist, the control still renders
(no special casing).

### 4.3 Splitter primary path

In the ledger walk, when the outgoing element from a structure is a pipe and
that structure is a splitter, pick `analysis.primaryPipeByStructureId[id]`
before the imported `Outgoing Pipe ID` / first-outgoing fallback. The rest of
the ledger math is unchanged: Hf uses that pipe's design Q, Hb uses the full
inflow set. Only the primary branch is ever walked; the secondary path is not
selectable in v1.

### 4.4 Missing Design Q

No math changes: `frictionSlope` already returns 0 for non-finite Q. The banner
is the user-facing explanation. A pipe whose `designQ` is a finite `0` is not
warned.

### 4.5 TR-55 callout cards (profile view)

For each station whose structure has `analysis.tr55ByStructureId[id]`, draw an
SVG group (`data-kind="tr55-card"`, `data-id="<structureId>"`) above the rim:

- A title line: structure id and drainage-area id.
- One line per segment, formatted by type:
  - `sheet · n .24 · L 45 · s .01`
  - `shallow · paved · L 80 · s .02`
  - `channel · A 12 · L 120 · s .005`
- A total line `Tc = 19.4 min` from that DA's `tc` when finite; omitted
  otherwise.
- A leader line from the card down to the structure's rim point.
- Multiple DAs at one structure stack as separate blocks inside the same card.
- Cards use a small monospace font (9–10 px) on a dark panel with a thin
  border. If two cards would overlap horizontally, stack them upward rather
  than shrinking text.

A `TR-55` toggle next to the `ISO | PROFILE` control shows/hides cards.
`state.ui.showTr55` defaults to `true` when the import has any segments, else
`false`. Toggling re-renders the active view.

### 4.6 Iso flow arrows

Each pipe gets a triangle at its projected midpoint pointing from `fromId` to
`toId`:

- ~6 px long, ~4 px wide at the base.
- Same color as the pipe stroke (`#ffd60a` selected, `#8b949e` otherwise).
- `data-kind="flow-arrow"`, `data-id="<pipeId>"`.
- Pipes with identical endpoints or zero projected length are skipped.

Arrows render after the pipe lines and before structures, so symbols stay on top.

### 4.7 Selection glow

Selected pipe line and selected structure group receive
`style="filter:drop-shadow(0 0 4px #ffd60a)"` in addition to the existing gold
stroke. Uses CSS filter via the `style` attribute (SVG `filter` presentation
attributes require a URL reference and do not accept `drop-shadow()`).

### 4.8 Print the current path

A toolbar `print` button builds a hidden white `#printArea` and prints it using
the main app's `body.print-mode` pattern:

- Header block: `Storm Drain HGL/EGL Visualizer — Energy Ledger`, imported file
  name, HGL method, walk-start id, and date.
- One `.calc-sheet` per row of the current annotated ledger path, reusing the
  existing `csSection` / `csFormula` helpers.
- `@media print`: hide `.app`, show `#printArea`, page-break after each sheet
  except the last.
- Trigger: add `body.print-mode`, call `window.print()`, remove the class on
  `afterprint` (with a fallback timeout).
- No import → button no-ops with a short notice.
- Only the current path is printed; the network is not enumerated.

## 5. Error handling / degradation

- `analyzeImported(null)` → `null`; missing sheets → empty arrays.
- `buildLedger` falls back to `imported.outfall` when analysis / `walkStartId`
  are absent, preserving existing unit tests and old JSON sidecars.
- Splitter without a primary role → first outgoing pipe + banner note.
- Non-outfall walk start without elevation fields → crown → rim → 0.
- Missing Design Q → Hf = 0 (existing guard) + banner explanation.
- TR-55 DA with no linked structure → segments omitted, no banner.
- Print with no import → no-op.
- Walk start on a disconnected structure → a single start row, no crash.
- Prototype-pollution hardening stays in force for JSON override keys.

## 6. Testing strategy

New `analysis.test.js` (pure, via the jsdom harness):

- `defaultWalkStart` = first outfall; `outfallIds` lists all outfalls.
- Splitter `primaryPipeByStructureId` picks `splitRole: "primary"`; falls back
  to the first outgoing pipe when no role is set.
- `missingDesignQ` flags `null` and non-finite, not numeric `0`.
- TR-55 join maps DA → structure and preserves segment order.
- `analyzeImported(null)` returns `null`.

Extend `xlsx-import.test.js`:

- `Split Role` read into pipes.
- Blank `Design Q` preserved as `null`.
- `tr55Segments` / `drainageAreas` arrays are parsed and asserted; if the real
  fixture lacks those rows, the synthetic workbook below covers parsing.
- Two outfalls detected in the fixture (`OUTFALL`, `BYPASS`).
- A synthetic in-test workbook supplies splitter pipes and TR-55 rows the real
  fixture may not contain; the real fixture keeps its header-parity role.

New `gap-ui.test.js` (jsdom):

- Banner renders for splitter/missing-Q, dismisses, and resets on a new import.
- Walk-from select lists grouped starts and clears cursor + branch choices.
- Profile renders `tr55-card` groups; the toggle hides/shows them.
- Iso arrow count equals the number of non-degenerate pipes.
- Selected pipe and structure carry the drop-shadow style.
- Print builds one sheet per path row, sets `body.print-mode`, and calls a
  stubbed `window.print`.

Regression: all 43 existing tests stay green; drift and round-trip unchanged;
built file still self-contained (no placeholder, no external URLs).

## 7. Acceptance criteria

- Full suite passes, including the new tests.
- Built file rebuilds and remains self-contained.
- Importing the real main-app fixture shows no warning banner unless it
  actually contains a splitter or missing Design Q; warnings appear correctly
  when present.
- TR-55 callout cards appear on the profile for structures with segments; the
  toggle hides them.
- Iso view shows flow arrows; the selected element glows.
- The walk-from switcher lists outfalls first, then all structures, and
  reseeds the walk.
- Print produces a readable current-path calc-sheet package and does not print
  the UI chrome.

## 8. Non-goals

- Outlet rating curves / BMP devices.
- Two-way sync back into the main app.
- Walking secondary splitter branches (primary only in this pass).
- Printing the entire network.
- Shared `compute.js` refactor between main app and visualizer.
- Legacy-to-template `.xlsx` converter.
- Editing TR-55 segments or split roles in the visualizer ledger.

## 9. Affected code map (dev HTML blocks)

- `state`: add `analysis`, `ui.walkStartId`, `ui.warningsDismissed`,
  `ui.showTr55`, `ui.fileName`.
- `import`: XLSX/JSON field additions; call `analyzeImported`; default walk
  start; banner render.
- new `analysis` block: `analyzeImported`, `walkStartInfo`,
  `primaryOutPipeId`, `tr55BlocksForStructure`.
- `compute`: `buildLedger` walk-start resolution and splitter primary pipe.
- `views`: iso arrows + glow; profile TR-55 cards + toggle.
- `navigation`: `initialCursor` starts from `ui.walkStartId`.
- `ledger-render` or new `print` block: `buildPrintArea`, `printLedger`, print
  CSS.
- `bootstrap`: toolbar wiring for walk-from, TR-55 toggle, print.

## 10. Risks / notes

- Two outfalls exist in the real fixture; the default must stay the first
  outfall to preserve the drift test's root (`OUTFALL`), not the lowest
  (`BYPASS`).
- SVG callout cards can collide on dense networks; stacking upward is the
  specified fallback, not shrinking text.
- `designQ: null` must not leak into arithmetic as `NaN`; all consumers keep
  using `resolveField(...) || 0` / the `frictionSlope` guard.
- Printing relies on `window.print`; jsdom tests stub it.

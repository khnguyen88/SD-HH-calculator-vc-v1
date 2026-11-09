# Visualizer Sample Projects — Design Spec

**Date:** 2026-11-08
**App:** `visualizer/storm-drain-visualizer-dev.html` (~2 743 lines)
**Status:** approved design — Approach A (embedded samples + drift guard), confirmed in session

---

## Goal

Ship two built-in sample networks for the HGL/EGL visualizer so a user can see a
working profile with one click, and make the import file contract explicit in
the UI. This directly resolves the user confusion that prompted the work:
"none of the excel files i used worked."

---

## Background — what the visualizer import actually accepts

The visualizer file input accepts `.xlsx,.json` (dev file line 55). Exactly two
file shapes import successfully:

1. **XLSX exported by the main drainage calculator.** `importFromXlsxFile`
   (line 727) hard-requires sheets named exactly `Junction Structure` and
   `Pipe Sizing` and keys off the calculator's human-readable column headers
   (`Structure ID`, `From Structure`, `Size (in or SPANxRISE)`, `Length (ft)`,
   …). Anything else throws *"Not a storm-drain export"*. This is why the
   bburg legacy workbook and the bburg template fail: they are agency
   calculation sheets with unrelated sheet layouts. The xlsx path also needs
   SheetJS, which exists only in the **built** file.
2. **JSON in the visualizer's own schema** (`validateImportedJson`, line 574):
   `schemaVersion: 1`, `sourceApp` (string), `structures[]` (id, type; optional
   rim/startElev/crown/x/y), `pipes[]` (id, fromId, toId, shape, size, n,
   slope, length; optional designQ, splitRole), `outfall`
   (`structureId`, `tailwaterElev`), optional `config`, `kbTable`,
   `drainageAreas`, `tr55Segments`, `_overrides` sidecar.

The two samples below are objects in schema shape 2, loaded through the normal
import path — no new file format, no SheetJS dependency, works in dev and
built files.

---

## Sample 1 — "Calculator demo project"

A faithful mirror of the main calculator's built-in demo (`seedExample()`).
Structure ids use the demo's structureId labels. Drift is guarded by test
(see Testing) — if the calculator demo changes, the test fails and the sample
must be updated to match.

- **structures**
  - `OUTFALL` — type `outfall`, startElev 100.0
  - `BYPASS` — type `outfall`, startElev 97.0
  - `ST-J` — type `manhole`, rim 108.0, crown of its outgoing 30″ pipe
  - `ST-1` — type `inlet`, rim 110.0, crown of its outgoing 24″ pipe
  - `ST-2` — type `inlet`, rim 111.0, crown of its outgoing 18″ pipe
  - `SPLIT-1` — type `splitter`, rim 107.0, crown of its outgoing 24″ primary

  Non-outfall structures carry explicit `crown` values (upstream invert of the
  structure's outgoing pipe + diameter, the same definition the calculator
  exports as "Pipe Crown (ft)"). Exact values are pinned by the drift test —
  they are read off the demo's own computation, not hand-derived. Outfalls
  have no outgoing pipe and therefore no crown. Carrying crowns lets the user
  flip the demo sample to the Legacy both-crown method and see the pin rule
  work there too.
- **pipes** (all circular, n = 0.013)
  - `ST-1 → ST-J` — 24 in, slope 0.005, length 200, angle 30°
  - `ST-2 → ST-J` — 18 in, slope 0.006, length 160, angle 90°
  - `ST-J → SPLIT-1` — 30 in, slope 0.004, length 100, angle 0°
  - `SPLIT-1 → OUTFALL` — 24 in, slope 0.004, length 150, splitRole `primary`
  - `SPLIT-1 → BYPASS` — 18 in, slope 0.005, length 120, angle 45°, splitRole `secondary`
  - every pipe carries `designQ` equal to the demo project's computed flow for
    that pipe (exact values pinned by the drift test, not hand-guessed)
- **drainageAreas** — `DA-1` (1.4 ac, C 0.55 → ST-1), `DA-2` (0.9 ac, C 0.85 → ST-2)
- **tr55Segments** — DA-1's three segments (sheet: n 0.24, L 100, s 0.01, P2 3.6;
  shallow: L 1400, s 0.01, unpaved; channel: L 7300, s 0.005, n 0.05, area 27,
  wp 28.2) so the TR-55 callout cards render
- **outfall** — `OUTFALL`, tailwaterElev 100.0
- **config** — `{ stormLabel: "10-yr (demo)", units: "us-customary", hglMethod: "hec22" }`
- **sourceApp** — `"storm-drain-design-calculator"`
- no x/y coordinates — the existing auto-layout places the network

## Sample 2 — "bburg legacy (simplified)"

A 3-structure network with clean round numbers transcribed from the legacy
workbook's " 10 Yr MoCo HGL" sheet (the 15″ I-2→MH-1 row — 80 ft, S 0.010,
Q 3.40 — and the 24″ rows toward the CULVERT, rounded). This sample is the
showcase for the existing **Legacy both-crown** HGL method, which reproduces
the workbook's max(crown, HGL) rule (workbook column notes: Col. H = max of
U/S crown and computed HGL).

- **structures**
  - `CULVERT` — type `outfall`, startElev 67.0 (no crown — no outgoing pipe)
  - `MH-1` — type `manhole`, rim 70.5, crown 69.35
  - `I-1` — type `inlet`, rim 71.5, crown 69.40
- **pipes** (circular, n = 0.013, angle 0°)
  - `I-1 → MH-1` — 15 in, slope 0.010, length 80, designQ 3.4
  - `MH-1 → CULVERT` — 24 in, slope 0.010, length 35, designQ 9.0
- **outfall** — `CULVERT`, tailwaterElev 67.0
- **config** — `{ stormLabel: "10-yr MoCo", units: "us-customary", hglMethod: "legacy-both-crown" }`
- **sourceApp** — `"bburg-p-c-legacy (simplified)"`

Crown values are internally consistent with the pipe geometry (crown = pipe
invert at the structure + diameter): the 24″ outgoing pipe drops 0.35 ft over
35 ft from CULVERT's 67.0, so MH-1's crown is 67.35 + 2.0 = 69.35; the 15″
pipe drops 0.80 ft over 80 ft, so I-1's crown is 68.15 + 1.25 = 69.40. Under
Legacy both-crown the profile pins to these crowns (the visualizer's
equivalent of the workbook's Col. H = max(U/S crown, computed HGL) rule);
under HEC-22 the profile stays near the tailwater — a clean side-by-side
demonstration of the two methods.

---

## Implementation design

### Sample registry

Both samples live in one `SAMPLES` table in the dev file, keyed by id:

```js
const SAMPLES = {
  "calculator-demo": { label: "Calculator demo project", data: { … } },
  "bburg-simplified": { label: "bburg legacy (simplified)", data: { … } },
};
```

### Shared import path (refactor)

`importFromJsonFile(file)` currently does: read text → parse → validate →
assign state (lines 656–725). Split it:

- `importFromJsonFile(file)` keeps only read + `JSON.parse` + delegates.
- New `applyImportedJson(obj)` takes everything from `validateImportedJson(obj)`
  onward: validation error handling, `_overrides` sidecar handling, state
  assignment, `hglMethod` application from `config`, `analyzeImported`, walk /
  cursor / branch reset, warning reset.

Loading a sample calls `applyImportedJson(SAMPLES[key].data)` — samples cannot
bypass schema validation and receive identical walk-reset semantics to a file
import. `state.ui.fileName` is set to the sample label (e.g.
"Calculator demo project") so downstream UI shows a sensible name instead of
an empty file name.

### UI

- Topbar, beside the existing Import button: a **"Sample ▾"** button with a
  two-item menu (*Calculator demo project*, *bburg legacy (simplified)*),
  following the visualizer's existing button/menu styling. Selecting an entry
  replaces any loaded network — same semantics as a file import (no merge,
  no confirmation dialog; consistent with how file import already replaces
  state without prompting).
- One-line hint under the Import button:
  *"Accepts a storm-drain-design-calculator .xlsx export or a visualizer .json file."*

---

## Testing (`visualizer/visualizer-tests/`)

Harness: existing `_harness.js` boots the dev HTML in jsdom; tests grab
top-level functions via `window` (e.g. `window.applyImportedJson`,
`window.SAMPLES`, `window.validateImportedJson`).

1. **Schema validity** — both `SAMPLES[*].data` pass `validateImportedJson`
   with zero errors.
2. **Calculator sample load** — `applyImportedJson` yields 6 structures,
   5 pipes, 2 drainageAreas, 3 TR-55 segments, mode `explore`,
   `state.ui.hglMethod === "hec22"`, and a non-null walk start.
3. **bburg sample load** — 3 structures, 2 pipes,
   `state.ui.hglMethod === "legacy-both-crown"`, non-null walk start.
4. **Drift guard** — a node test loads `drainage-calculator/storm-drain-design-calculator-dev.html`
   in jsdom (same instrumentation technique as
   `visualizer-tests/fixtures/generate-fixture.js`), runs `seedExample()`,
   maps the resulting state into the visualizer JSON shape, and asserts
   equality with `SAMPLES["calculator-demo"].data` — structures (ids, types,
   rims, startElevs, crowns), pipes (from/to, size, n, slope, length, angle,
   splitRole, designQ from the demo's computed flows), drainageAreas, and
   TR-55 segments. Any mismatch fails with a field-level diff message.
5. **DOM** — the Sample button and both menu entries render; the import hint
   text is present.

---

## Scope

- Visualizer app only (`visualizer/storm-drain-visualizer-dev.html` + tests).
  No changes to the main calculator, the bburg workbook, or the accepted
  import formats.
- Samples replace state like an import; there is no sample editing or sample
  persistence feature.
- Deployment unchanged: build with `visualizer/build-visualizer.js`, gh-pages
  runbook as documented in `docs/deployment-runbook.md`.
- Out of scope: teaching the xlsx importer to read the bburg legacy workbook.

# Calculator → Visualizer Transfer: One-Click Handoff + HGL Method Honor

**Date:** 2026-11-09
**Status:** Approved design (user-approved in session 2026-11-09)
**Scope:** Calculator (payload builder + button) + Visualizer (xlsx method read + hash import)

## Problem

The calculator and the HGL/EGL visualizer already share data through an Excel
round-trip (calculator Export → visualizer Import), and v82.1 already imports
pipe inverts for true profile geometry and drop-aware HGL/EGL walks. Two gaps
remain:

1. The visualizer ignores the calculator's HGL method. The calculator exports a
   `HGL Method` row (`HEC-22` / `Conservative`) on its Rainfall Settings sheet,
   but the visualizer's xlsx importer never reads it, and its JSON
   `config.hglMethod` passthrough only fires for its own two method names.
2. The round-trip requires exporting a file, switching apps, and importing —
   users want one click.

## Goals

1. Importing a calculator export (xlsx or one-click payload) sets the
   visualizer's initial HGL method to match the calculator's; the user can
   still switch methods freely at any time (existing topbar select unchanged).
2. A one-click "Open in Visualizer" button in the calculator hands the current
   project to the visualizer with no file round-trip, working both on the
   deployed GitHub Pages site and when both built files are opened offline
   (file://).

## Non-goals

- No new visualizer profile rendering, HGL/EGL math, or drop-structure logic —
  v82.1 already covers pipe profiles and elevation-drop handling at structures.
- No 25-yr storm transfer; the visualizer walks one storm and displays the
  storm label only.
- No renaming of the visualizer's `legacy-both-crown` method.
- No third "conservative" method in the visualizer (see mapping below).

## Feature A — Visualizer honors the calculator's HGL Method on import

### Method mapping

| Calculator export value | Visualizer initial `state.ui.hglMethod` |
|---|---|
| `HEC-22` (or row absent) | `hec22` |
| `Conservative` | `legacy-both-crown` |

The user-selected mapping: the calculator's Conservative concept and the
visualizer's faithful bburg-legacy transcription are treated as the same
"conservative family," and the existing visualizer toggle is reused.

**Documented caveat (binding disclosure):** the calculator's Conservative pins
each structure's upstream HGL to its outgoing pipe's upstream crown only, while
the visualizer's `legacy-both-crown` floors the walk at pipe crowns at both
ends. For the same project the visualizer's HGL will sit at or above the
calculator's — both conservative, never below. This difference is accepted by
design; the spec records it so submittal reviewers are not surprised.

### Changes

1. **xlsx importer** (`importFromXlsxFile` in the visualizer dev file): after
   reading the structure/pipe sheets, also read the Rainfall Settings sheet's
   `HGL Method` row (label match is exact; the calculator writes `HEC-22` or
   `Conservative`). Map per the table above into the imported `config.hglMethod`
   (the config passthrough in `applyImportedJson` already applies it — visualizer
   dev line ~748). A missing row or unrecognized value leaves the visualizer's
   current method untouched (old exports behave exactly as today).
2. **JSON payload path:** no visualizer change needed — `applyImportedJson`
   already honors `config.hglMethod` values `hec22` /
   `legacy-both-crown`. The calculator's payload builder writes the mapped
   value (never the literal string `conservative`, which the visualizer would
   silently reject).

## Feature B — One-click "Open in Visualizer"

### UX

The calculator's existing toolbar Visualizer link becomes a button
"Open in Visualizer". Click:

```
CALCULATOR                                VISUALIZER
┌──────────────────────┐                 ┌──────────────────────────┐
│ Toolbar: [Open in     │  window.open    │ on load:                 │
│  Visualizer]          │────────────────>│  location.hash #data=?   │
│  1. build JSON payload│  #data=<encoded>│   yes → validateImported │
│     (visualizer       │                 │       Json → applyImport │
│      schema)          │                 │       edJson → banner    │
│  2. encode + open new │                 │       "Loaded from      │
│     tab with hash URL │                 │       calculator" →     │
└──────────────────────┘                 │       clear hash         │
  fallback (below)                        │   no  → normal startup   │
                                         └──────────────────────────┘
```

### Payload builder (calculator)

One new function, e.g. `buildVisualizerPayload()`, emitting the visualizer's
JSON import schema from current state + `computeStructureCalc` results. The
data set is exactly what the xlsx export columns already carry — the payload is
a second serialization of the same single source of truth, never a new
computation:

- `structures[]`: id, label, type, rim, startElev, crown, forceElev,
  capturedQ, totalQ, Hb, elevation (Upstream HGL), outPipeId
- `pipes[]`: id, fromId, toId, shape, size, n, slope, length, angle, designQ,
  usInvert, dsInvert, splitRole, Hf
- `outfall`: { structureId, tailwaterElev } — first outfall-type structure,
  startElev as tailwater (mirrors the visualizer's xlsx fallback order)
- `drainageAreas[]`, `tr55Segments[]`: same mapping as the xlsx export sheets
- `config`: { stormLabel (calculator's Pipe & HGL design storm label),
  units: "us-customary", hglMethod: mapped value }

Empty state (no structures): the button does nothing and explains why
(disabled or a toast), mirroring how Export behaves.

### Hash protocol

- Encode: `encodeURIComponent(JSON.stringify(payload))`, appended as
  `#data=<encoded>` to the visualizer URL. Plain JSON + built-ins only — no
  compression library (single-file/offline rule).
- Decode (visualizer, on load, before the first render): if
  `location.hash` starts with `#data=`, decode → `JSON.parse` →
  `validateImportedJson` → on success `applyImportedJson` with a
  fileName like `"(from calculator)"`, then `history.replaceState` to strip
  the hash so a refresh does not re-import. On any failure (garbage hash,
  validation error): show the existing import-error banner and start empty —
  never crash on a malformed hash.
- Size guard: if the encoded payload exceeds ~60,000 characters, skip the
  hash and go straight to the file-download fallback.

### URL resolution (deployed site vs offline)

1. Deployed site (page served over http(s), calculator at site root):
   open `visualizer.html` (relative).
2. Offline (file://): try sibling `visualizer.html`, then
   `../visualizer/storm-drain-visualizer.html` (the repo's local build
   layout). Because cross-tab load-failure detection is unreliable and a
   synchronous existence probe is not possible on file://, the button
   does not probe: **binding simplification** - offline it ALWAYS
   downloads the payload as `<project>-visualizer.json` alongside the
   `window.open` attempt, with a one-line notice: "If the visualizer
   didn't open, import the downloaded file." On the deployed site it
   only opens the tab (no download) unless the size guard trips.

### Fallbacks summary

| Condition | Behavior |
|---|---|
| Deployed site, payload ≤ 60k chars | open new tab with hash |
| Deployed site, payload > 60k chars | download JSON file + notice |
| file://, any payload | attempt sibling paths + always download JSON + notice |
| Hash invalid/garbage on visualizer load | import-error banner, start empty |
| Visualizer already open (hash lands on live page) | same import path; hash stripped after |

## Error handling

- Payload build throws (shouldn't — it reads the same values the export
  reads): the button shows the calculator's standard toast, no navigation.
- `window.open` blocked (popup blocker): fall back to download + notice.
- Visualizer-side validation failure of a hash payload: banner, empty start
  (same as a bad file import).

## Testing

Calculator suite (tests/run-tests.mjs, loads BUILT html):

1. `buildVisualizerPayload()` on the seed example passes the visualizer's
   `validateImportedJson` with zero errors (schema conformance).
2. **Drift guard:** for the seed example, the payload's imported values
   (structure rim/startElev/crown/Q's/HGL, pipe inverts/designQ/slope,
   outfall/tailwater, method mapping) match what the visualizer's xlsx
   importer produces from the calculator's exported workbook. This pins the
   two serializations to one truth (same pattern as the v82.0 sample drift
   guard).
3. Method mapping: hglMethod `hec22` → payload config `hec22`;
   `conservative` → `legacy-both-crown`.
4. Hash encoding round-trip: decode(encode(payload)) deep-equals payload;
   60k-char guard trips on an oversized synthetic payload.

Visualizer suite (visualizer/visualizer-tests, loads BUILT visualizer):

5. `#data=` hash import: valid payload loads through the shared path, sets
   fileName, clears the hash, renders.
6. Garbage hash (`#data=%ZZ-not-json`): no crash, empty start, error banner.
7. xlsx import with Rainfall Settings `HGL Method: Conservative` sets
   `state.ui.hglMethod` to `legacy-both-crown`; `HEC-22` sets `hec22`;
   missing row leaves current method untouched.
8. JSON config passthrough already covered by an existing test (extend only
   if needed).

All existing tests stay green (97 calculator / 120 visualizer). The test
suites load the BUILT files, so every task runs the respective build script
first.

## Architecture notes

- The payload builder lives in the calculator dev file next to
  `buildWorkbook` (both are serializations of `computeStructureCalc` results).
- The visualizer's hash-import branch reuses `applyImportedJson` — the same
  validated path as file import and samples (no bypassing of validation,
  per the established import rule).
- No new libraries, no network, no storage; both built files stay
  self-contained.

## Decisions (resolved in brainstorming, binding)

1. Reuse the visualizer's existing two-method toggle; Conservative maps to
   `legacy-both-crown` (user decision — no third visualizer method).
2. Transfer works on the deployed site AND offline file:// (user decision).
3. Mechanism: URL-hash payload with JSON-file download fallback
   (user decision).
4. The numeric difference between calculator-Conservative and
   legacy-both-crown is accepted and documented (caveat above).

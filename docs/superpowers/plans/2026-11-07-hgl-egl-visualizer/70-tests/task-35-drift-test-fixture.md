# Task 35: Drift test — parity with main app export

## Context

Check in a fixture `.xlsx` exported from the main app. Load it with the independent `xlsx`
npm package (not SheetJS from the dev file). Re-compute every pipe's Hf and every
structure's Hb locally. Assert `|local - exported| ≤ 0.001 ft` for Hf/Hb and `≤ 0.01 ft` for
end-to-end EGL.

This is the central guarantee: formula drift between the main app and the visualizer breaks
this test immediately. Implements spec §8.2.

**As built (deviates from the original draft):** the fixture is generated headlessly, not by
a manual browser export. The main app wraps its script in an IIFE, so `fixtures/generate-fixture.js`
injects `globalThis.__getApp = () => ({ state, buildWorkbook, seedExample })` after the first
`"use strict";`, boots the main dev HTML in jsdom (with a `ResizeObserver` stub and the Node
`xlsx` module as `window.XLSX`), calls the main app's own `seedExample()` + `buildWorkbook()`,
and writes `main-app-export.xlsx` with `bookSST: true`. This uses the main app's real code — no
re-implemented formulas — and the built-in demo network (2 drainage areas, 6 structures incl. a
splitter and two outfalls, 5 pipes), which is richer than the original hand-entered seed (whose
second inflow carried zero flow).

## Preconditions

- Prior tasks: task-08, task-09, task-10, task-11, task-12, task-31.

## Exact changes

- **Create** `visualizer/visualizer-tests/fixtures/generate-fixture.js` — headless
  generator described above (CommonJS; requires jsdom/xlsx from `../node_modules`).
- **Create** `visualizer/visualizer-tests/fixtures/main-app-export.xlsx` — run the
  generator; commit the binary (~190 KB, the test contract).
- **Create** `visualizer/visualizer-tests/fixtures/README.md` — documents headless
  regeneration, the `seedExample()` network, and the dev-only jsdom/xlsx dependency.
- **Create** `visualizer/visualizer-tests/drift.test.js` — 3 tests.

### Real export schema (the original draft's column names were wrong)

Sheets: `"Pipe Sizing"` and `"Junction Structure"` (read via
`XLSX.utils.sheet_to_json(ws, { defval: null })`).

- `Pipe Sizing`: `ID | From Structure | To Structure | Angle (deg) | Shape |
  Size (in or SPANxRISE) | n | US Invert (ft) | DS Invert (ft) | Slope (ft-ft) |
  Length (ft) | Design Q (cfs) | Area (sf) | Qfull (cfs) | Velocity (fps) | Status |
  Split Role | From|Role Key`
- `Junction Structure` (relevant): `Structure ID | Type | Force Fixed |
  Fixed-Start Elev (ft) | Pipe Crown (ft) | Rim-Grate Elev (ft) | Total Flow (cfs) |
  Outgoing Pipe ID | Hf (ft) | Kb | Hb (ft) | Vout (fps) | Upstream HGL (ft) | …`

Critical mapping facts:

- **Hf lives on the Junction Structure sheet**, one per non-outfall structure's outgoing pipe —
  not on the Pipe sheet.
- Recompute Hb with `Qtotal = "Total Flow (cfs)"` and `Aout` from the pipe named by
  `"Outgoing Pipe ID"`. The outgoing pipe's `Design Q (cfs)` is only the primary share for a
  splitter.
- A splitter's secondary pipe is not any structure's `"Outgoing Pipe ID"`, so its Hf is not
  exported and is skipped.
- The main app's `"Upstream HGL (ft)"` column stores the accumulated grade-line walk
  `downstream + Hf + Hb` that the visualizer reproduces as its EGL (`rows[last].after`).

### The 3 tests

Tolerances: `TOL_PIPE = 0.001`, `TOL_STRUCT = 0.001`, `TOL_EGL = 0.01`.

1. **Pipe Hf parity** — for each structure with an `"Outgoing Pipe ID"`, locally recompute
   `frictionLoss(frictionSlope(pipe.designQ, pipe.n, A, R), pipe.length)` and compare to
   the structure's `"Hf (ft)"`.
2. **Structure Hb parity** — for each non-outfall structure, build inflows from every pipe
   whose `toId === sid`, use `Qtotal = "Total Flow (cfs)"`, `Aout = pipeArea(outPipe)`, call
   `structureLoss`, skip `res.error`, compare `res.Hb` to `"Hb (ft)"`.
3. **End-to-end EGL parity** — seed the visualizer state from the fixture, then for each
   non-outfall structure reachable from the outfall via reverse BFS, call
   `buildLedger(path, state, KB_SEED, "hec22")` and compare the final `after` to
   `"Upstream HGL (ft)"`.

## Acceptance test

```powershell
node --test visualizer/visualizer-tests/drift.test.js
```

Expected: `pass 3 / fail 0`. Verified baseline with `seedExample()`: max |ΔHf| ≈ 2.8e-5,
|ΔHb| ≈ 4.9e-5, |ΔEGL| ≈ 3.6e-4.

## Done when

- `fixtures/main-app-export.xlsx` committed (small binary).
- `fixtures/README.md` and `fixtures/generate-fixture.js` committed.
- `drift.test.js` passes all 3 tests.
- Commit: `test(visualizer): task-35 drift test vs main-app fixture`.

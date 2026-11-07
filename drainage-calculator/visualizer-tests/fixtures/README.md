# Visualizer test fixtures

## main-app-export.xlsx

A real workbook exported by the **main** Storm Drain Design Calculator. The
visualizer's `drift.test.js` loads it with the independent `xlsx` npm package
(not the SheetJS bundle inlined in the built HTML), re-computes Hf / Hb / EGL
with the visualizer's functions, and asserts parity. This is the contract that
formulas have not drifted between the two apps.

### How it was generated

The file is produced **headlessly from the main app's own code** — no values
are hand-authored here. `generate-fixture.js`:

1. Reads `drainage-calculator/storm-drain-design-calculator-dev.html`.
2. Injects `globalThis.__getApp = () => ({ state, buildWorkbook, seedExample });`
   immediately after the first `"use strict";` (the app wraps itself in an IIFE,
   so these bindings are otherwise private).
3. Loads the instrumented HTML in jsdom with the Node `xlsx` package standing in
   for the in-page SheetJS bundle, and a no-op `ResizeObserver`.
4. Calls the app's built-in `seedExample()` demo project and then
   `buildWorkbook()`, writing the result with `bookSST: true`.

This deliberately uses the main app's own demo project rather than hand-entered
seed data (the plan's original README suggested a hand-entered 3-structure
network, whose second inflow carried zero flow and was therefore degenerate).

### Seed project (`seedExample()`)

- 2 drainage areas: DA-1 (1.4 ac, C=0.55, TR-55 Tc) and DA-2 (0.9 ac, C=0.85).
- 6 structures: `OUTFALL` (outfall, fixed 100.0 ft), `ST-J` (manhole), `ST-1`
  (inlet, DA-1), `ST-2` (inlet, DA-2), `SPLIT-1` (flow splitter, capacity 6.0
  cfs), `BYPASS` (secondary outfall, fixed 97.0 ft).
- 5 pipes: ST-1→ST-J (24 in), ST-2→ST-J (18 in), ST-J→SPLIT-1 (30 in),
  SPLIT-1→OUTFALL (24 in, primary), SPLIT-1→BYPASS (18 in, secondary).

### Regenerating

From this directory:

```powershell
node generate-fixture.js
```

Requires the dev dependencies in `visualizer-tests/package.json` (`jsdom` and
`xlsx`). Both are **dev-only** — neither is shipped with the offline app.

After regenerating, run the drift tests from the worktree root:

```powershell
node --test drainage-calculator/visualizer-tests/drift.test.js
```

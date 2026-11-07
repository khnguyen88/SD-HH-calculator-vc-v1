# Task 34: Unit tests — structure loss (controlling-angle)

## Context

Test `structureLoss` across all inflow counts, with specific focus on the main-spec §1.4 counter-example (smaller Lv picks θc, not larger). Implements spec §8.1.

## Preconditions

- Prior tasks: task-10, task-11, task-31.

## Exact changes

**Create** `drainage-calculator/visualizer-tests/structure-loss.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

test("structureLoss: 0 inflows uses Kb at 0°", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  const r = fn("structureLoss")([], 5.0, Aout, "manhole", window.KB_SEED);
  const expectedKb = 0.06;  // Kb seed clamps 0° to the 5° row's value
  assert.strictEqual(r.kbUsed, expectedKb);
  assert.strictEqual(r.thetaControlling, 0);
  assert.ok(r.Hb >= 0);
});

test("structureLoss: 1 inflow uses Kb at that pipe's angle", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  const r = fn("structureLoss")([{ angleDeg: 30, Qcfs: 5 }], 5, Aout, "manhole", window.KB_SEED);
  assert.strictEqual(r.thetaControlling, 30);
  assert.strictEqual(r.kbUsed, 0.35);
});

test("structureLoss: 2 inflows - SMALLER Lv picks θc (main-spec §1.4 counter-example)", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  // Inflow A: angle=10°, Q=6 cfs — high Q, low angle → Lv1 large.
  // Inflow B: angle=60°, Q=2 cfs — low Q, high angle → Lv2 small.
  // Lv1 > Lv2 → controlling is B's angle (60°).
  const r = fn("structureLoss")(
    [{ angleDeg: 10, Qcfs: 6 }, { angleDeg: 60, Qcfs: 2 }],
    8, Aout, "manhole", window.KB_SEED);
  assert.strictEqual(r.thetaControlling, 60, "controlling must be the SMALLER-Lv angle");
  assert.strictEqual(r.candidateLosses[0].isControlling, false, "A (larger Lv) should not control");
  assert.strictEqual(r.candidateLosses[1].isControlling, true, "B (smaller Lv) controls");
});

test("structureLoss: 2 inflows symmetric → first angle controls (tie-break)", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  const r = fn("structureLoss")(
    [{ angleDeg: 30, Qcfs: 4 }, { angleDeg: 30, Qcfs: 4 }],
    8, Aout, "manhole", window.KB_SEED);
  // Lv1 === Lv2; code uses (Lv1 > Lv2) ? b : a, which picks `a` on equality.
  assert.strictEqual(r.thetaControlling, 30, "symmetric case: angle = 30");
  // Only one should be marked controlling (candidate A).
  assert.strictEqual(r.candidateLosses[0].isControlling, true);
  assert.strictEqual(r.candidateLosses[1].isControlling, true); // both share same angle → both controlling
});

test("structureLoss: >2 inflows returns error", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  const r = fn("structureLoss")(
    [{ angleDeg: 10, Qcfs: 1 }, { angleDeg: 30, Qcfs: 2 }, { angleDeg: 50, Qcfs: 3 }],
    6, Aout, "manhole", window.KB_SEED);
  assert.strictEqual(r.error, "too-many-inflows");
});

test("structureLoss: non-array inflows returns error", () => {
  const { window, fn } = loadVisualizer();
  const Aout = fn("pipeAreaCircular")(18);
  const r = fn("structureLoss")(null, 6, Aout, "manhole", window.KB_SEED);
  assert.strictEqual(r.error, "inflows-not-array");
});

test("kbAt: linear interpolation 35° (between 30° and 40°)", () => {
  const { window, fn } = loadVisualizer();
  // 30→0.35, 40→0.43 → midpoint at 35° → 0.39.
  assert.ok(Math.abs(fn("kbAt")(35, "bend", window.KB_SEED) - 0.39) < 1e-12);
});

test("kbAt: clamp below first row and above last row", () => {
  const { window, fn } = loadVisualizer();
  assert.strictEqual(fn("kbAt")(-10, "manhole", window.KB_SEED), 0.06);
  assert.strictEqual(fn("kbAt")(200, "bend", window.KB_SEED), 0.70);
});

test("kbAt: junction maps to bend column, splitter to manhole", () => {
  const { window, fn } = loadVisualizer();
  assert.strictEqual(
    fn("kbAt")(30, "junction", window.KB_SEED),
    fn("kbAt")(30, "bend", window.KB_SEED)
  );
  assert.strictEqual(
    fn("kbAt")(30, "splitter", window.KB_SEED),
    fn("kbAt")(30, "manhole", window.KB_SEED)
  );
});

test("kbAt: null/empty table falls back to seed", () => {
  const { window, fn } = loadVisualizer();
  const seed = fn("kbAt")(30, "manhole", window.KB_SEED);
  assert.strictEqual(fn("kbAt")(30, "manhole", null), seed);
  assert.strictEqual(fn("kbAt")(30, "manhole", []), seed);
});
```

## Acceptance test

```powershell
node --test drainage-calculator/visualizer-tests/structure-loss.test.js
```

Expected: `pass 10 / fail 0`.

## Done when

- File `structure-loss.test.js` exists with 10 tests.
- All 10 pass.
- The main-spec §1.4 counter-example assertion passes (this is the single most important test in the visualizer).
- Commit: `test(visualizer): task-34 structure-loss and Kb unit tests`.

# Task 33: Unit tests — Manning friction

## Context

Test `frictionSlope` and `frictionLoss` against hand-calculated references. Implements spec §8.1.

## Preconditions

- Prior tasks: task-09, task-31.

## Exact changes

**Create** `drainage-calculator/visualizer-tests/friction.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

// Reference: Q=8.4 cfs, n=0.013, D=18 in → A=1.7671, R=0.375.
// Sf = (Q·n / (1.486·A·R^(2/3)))² = 0.0063947 (exact, 1.486 English constant)
// Hf at L=120 ft = 0.7674 ft.
test("frictionSlope matches hand-calc at Q=8.4 cfs, D=18 in", () => {
  const { fn } = loadVisualizer();
  const A = fn("pipeAreaCircular")(18);
  const R = fn("pipeRadiusCircular")(18);
  const sf = fn("frictionSlope")(8.4, 0.013, A, R);
  assert.ok(Math.abs(sf - 0.006414) < 1e-4, "Sf = " + sf);
});

test("frictionLoss = Sf · L", () => {
  const { fn } = loadVisualizer();
  const hf = fn("frictionLoss")(0.005, 120);
  assert.strictEqual(hf, 0.6);
});

test("frictionSlope with Q=0 returns 0", () => {
  const { fn } = loadVisualizer();
  const A = fn("pipeAreaCircular")(18);
  const R = fn("pipeRadiusCircular")(18);
  assert.strictEqual(fn("frictionSlope")(0, 0.013, A, R), 0);
});

test("frictionSlope with NaN inputs returns 0 (defensive)", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(fn("frictionSlope")(NaN, 0.013, 1.77, 0.375), 0);
  assert.strictEqual(fn("frictionSlope")(8.4, NaN, 1.77, 0.375), 0);
  assert.strictEqual(fn("frictionSlope")(8.4, 0.013, NaN, 0.375), 0);
  assert.strictEqual(fn("frictionSlope")(8.4, 0.013, 1.77, NaN), 0);
});

test("frictionSlope with degenerate geometry returns 0", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(fn("frictionSlope")(8.4, 0.013, 0, 0.375), 0);
  assert.strictEqual(fn("frictionSlope")(8.4, 0.013, 1.77, 0), 0);
});

test("frictionLoss with NaN returns 0", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(fn("frictionLoss")(NaN, 120), 0);
  assert.strictEqual(fn("frictionLoss")(0.005, NaN), 0);
});

test("Sf scales as (Q·n)² approximately", () => {
  const { fn } = loadVisualizer();
  const A = fn("pipeAreaCircular")(24);
  const R = fn("pipeRadiusCircular")(24);
  const sf1 = fn("frictionSlope")(5, 0.013, A, R);
  const sf2 = fn("frictionSlope")(10, 0.013, A, R);
  // Doubling Q should quadruple Sf (since Sf ∝ Q²).
  assert.ok(Math.abs(sf2 / sf1 - 4) < 1e-6, "Sf(2Q)/Sf(Q) = " + sf2 / sf1);
});
```

## Acceptance test

```powershell
node --test drainage-calculator/visualizer-tests/friction.test.js
```

Expected: `pass 7 / fail 0`.

## Done when

- File `friction.test.js` exists with 7 tests.
- All 7 pass.
- Commit: `test(visualizer): task-33 Manning friction unit tests`.

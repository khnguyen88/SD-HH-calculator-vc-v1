# Task 41: Kb interpolation unit tests

## Context

Spec §8.1 names eight specific `kbAt` assertions required in the automated test suite.
Task-10 provides `kbAt` and `KB_SEED` with a browser smoke test only. Tasks 32–34 cover
pipe geometry, friction, and structure loss but nothing covers the Kb lookup. This task
fills that gap with a dedicated node test file.

One note: KB_SEED has entries at 30° (0.35) and 40° (0.44), with no 35° row. The spec
§8.1 wording "between 35° and 40°" is slightly imprecise — the bracket that actually
contains 37.5° is [30°, 40°], not [35°, 40°]. The test below uses the correct bracket.

## Preconditions

- Prior tasks: task-10 (`kbAt`, `KB_SEED`), task-31 (harness, `npm install` done).

## Exact changes

**Create** `visualizer/visualizer-tests/kb-interpolation.test.js`:

```js
const test  = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

const EPS = 1e-9;

function setup() {
  const { window } = loadVisualizer();
  return { kbAt: window.kbAt, KB_SEED: window.KB_SEED };
}

test("kbAt: exact hit at table minimum (5°)", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(5, "manhole", KB_SEED), 0.06);
});

test("kbAt: exact hit at table maximum (90°)", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(90, "bend", KB_SEED), 0.70);
});

test("kbAt: linear interpolation at 37.5° between 30° (0.35) and 40° (0.44) = 0.4175", () => {
  const { kbAt, KB_SEED } = setup();
  // t = (37.5 - 30) / (40 - 30) = 0.75
  // result = 0.35 + 0.75 * (0.44 - 0.35) = 0.35 + 0.0675 = 0.4175
  const expected = 0.35 + 0.75 * (0.44 - 0.35);
  assert.ok(Math.abs(kbAt(37.5, "manhole", KB_SEED) - expected) < EPS,
    `expected ${expected}, got ${kbAt(37.5, "manhole", KB_SEED)}`);
});

test("kbAt: clamps to minimum at 0° (below table's 5° floor)", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(0, "manhole", KB_SEED), 0.06,
    "0° should clamp to the 5° row value");
});

test("kbAt: clamps to minimum at negative angle", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(-5, "inlet", KB_SEED), 0.06);
});

test("kbAt: clamps to maximum at 200°", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(200, "bend", KB_SEED), 0.70);
});

test("kbAt: junction maps to the bend column", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(30, "junction", KB_SEED), kbAt(30, "bend", KB_SEED));
});

test("kbAt: null kbTable falls back to KB_SEED", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(30, "manhole", null), kbAt(30, "manhole", KB_SEED));
});
```

## Acceptance test

```powershell
node --test visualizer/visualizer-tests/kb-interpolation.test.js
```

Expected output:

```
# tests 8
# suites 0
# pass 8
# fail 0
```

## Done when

- `kb-interpolation.test.js` created with 8 tests.
- All 8 pass.
- `node --test visualizer/visualizer-tests/` — no prior tests regressed.
- Commit: `test(visualizer): task-41 kbAt interpolation unit tests`.

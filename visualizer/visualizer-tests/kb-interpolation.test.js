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

test("kbAt: linear interpolation at 37.5° between 30° (0.35) and 40° (0.43) = 0.41", () => {
  const { kbAt, KB_SEED } = setup();
  const expected = 0.35 + 0.75 * (0.43 - 0.35); // = 0.41
  assert.ok(Math.abs(kbAt(37.5, "manhole", KB_SEED) - expected) < EPS,
    `expected ${expected}, got ${kbAt(37.5, "manhole", KB_SEED)}`);
});

test("kbAt: clamps to minimum at 0° (below table's 5° floor)", () => {
  const { kbAt, KB_SEED } = setup();
  assert.strictEqual(kbAt(0, "manhole", KB_SEED), 0.06);
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

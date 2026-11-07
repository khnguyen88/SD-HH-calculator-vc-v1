const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

const EPS = 1e-9;

test("pipeAreaCircular(18) ≈ π·(1.5)²/4", () => {
  const { fn } = loadVisualizer();
  const a = fn("pipeAreaCircular")(18);
  assert.ok(Math.abs(a - Math.PI * 2.25 / 4) < 1e-12, "got " + a);
});

test("pipeAreaCircular reproduces closed form for 12..96 in", () => {
  const { fn } = loadVisualizer();
  const pA = fn("pipeAreaCircular");
  for (const d of [12, 15, 18, 24, 30, 36, 48, 60, 72, 96]) {
    const expected = Math.PI * (d / 12) * (d / 12) / 4;
    assert.ok(Math.abs(pA(d) - expected) < EPS, `d=${d}: got ${pA(d)}, expected ${expected}`);
  }
});

test("pipeRadiusCircular = D/4", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(fn("pipeRadiusCircular")(18), 0.375);
  assert.strictEqual(fn("pipeRadiusCircular")(24), 0.5);
});

test("pipeAreaElliptical 38x24 = 6.3 sf per Table 4-6", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(fn("pipeAreaElliptical")("38x24"), 6.3);
});

test("elliptical hydraulic radius matches equivalent circular R", () => {
  const { fn } = loadVisualizer();
  const Rc = fn("pipeRadiusCircular")(30);
  const Re = fn("pipeRadiusElliptical")("38x24");
  assert.ok(Math.abs(Rc - Re) < EPS, "circular R30 and elliptical 38x24 should match");
});

test("pipeArea dispatches by shape", () => {
  const { fn } = loadVisualizer();
  const pA = fn("pipeArea");
  assert.ok(Math.abs(pA("circular", 18) - fn("pipeAreaCircular")(18)) < EPS, "circular dispatch");
  assert.strictEqual(pA("elliptical", "38x24"), 6.3, "elliptical dispatch");
});

test("pipeArea throws on unknown shape", () => {
  const { fn } = loadVisualizer();
  assert.throws(() => fn("pipeArea")("square", 12));
});

test("pipeAreaElliptical throws on unresolvable unknown size", () => {
  const { fn } = loadVisualizer();
  // normalizeSize() snaps parseable span×rise values to the nearest Table 4-6
  // row, so only an unparseable size returns null and triggers the throw.
  assert.throws(() => fn("pipeAreaElliptical")("bogus"));
});

test("TABLE_4_6 has 24 rows covering 15..144 in", () => {
  const { window } = loadVisualizer();
  const tbl = window.TABLE_4_6;
  assert.strictEqual(tbl.length, 24);
  assert.strictEqual(tbl[0].dia_in, 15);
  assert.strictEqual(tbl[tbl.length - 1].dia_in, 144);
});

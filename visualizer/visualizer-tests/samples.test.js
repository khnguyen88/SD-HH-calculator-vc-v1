/*
 * Built-in sample registry: both samples must be schema-valid visualizer
 * JSON (they load through the same validateImportedJson as file imports).
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

test("SAMPLES registry defines both samples", () => {
  const viz = loadVisualizer();
  const samples = viz.window.SAMPLES;
  assert.ok(samples, "window.SAMPLES must be exposed for tests");
  assert.deepStrictEqual(Object.keys(samples).sort(), ["bburg-simplified", "calculator-demo"]);
  assert.strictEqual(samples["calculator-demo"].label, "Calculator demo project");
  assert.strictEqual(samples["bburg-simplified"].label, "bburg legacy (simplified)");
  viz.dom.window.close();
});

test("both samples pass validateImportedJson with zero errors", () => {
  const viz = loadVisualizer();
  const validate = viz.fn("validateImportedJson");
  for (const key of Object.keys(viz.window.SAMPLES)) {
    const result = validate(viz.window.SAMPLES[key].data);
    assert.strictEqual(result.valid, true, key + ": " + result.errors.join("; "));
    // Cross-realm array: compare contents, not deep-strict against a Node [].
    assert.strictEqual(result.errors.length, 0);
  }
  viz.dom.window.close();
});

test("loadSample applies the calculator demo through the shared import path", () => {
  const viz = loadVisualizer();
  viz.fn("loadSample")("calculator-demo");
  const imp = viz.window.state.imported;
  assert.strictEqual(imp.structures.length, 6);
  assert.strictEqual(imp.pipes.length, 5);
  assert.strictEqual(imp.drainageAreas.length, 2);
  assert.strictEqual(imp.tr55Segments.length, 3);
  assert.strictEqual(viz.window.state.ui.mode, "explore");
  assert.strictEqual(viz.window.state.ui.hglMethod, "hec22");
  assert.notStrictEqual(viz.window.state.ui.walkStartId, null);
  assert.strictEqual(viz.window.state.ui.fileName, "Calculator demo project");
  assert.strictEqual(viz.document.getElementById("fileName").textContent, "Calculator demo project");
  viz.dom.window.close();
});

test("loadSample applies the bburg sample with legacy-both-crown preselected", () => {
  const viz = loadVisualizer();
  viz.fn("loadSample")("bburg-simplified");
  const imp = viz.window.state.imported;
  assert.strictEqual(imp.structures.length, 3);
  assert.strictEqual(imp.pipes.length, 2);
  assert.strictEqual(viz.window.state.ui.hglMethod, "legacy-both-crown");
  assert.notStrictEqual(viz.window.state.ui.walkStartId, null);
  viz.dom.window.close();
});

test("loadSample throws on an unknown key", () => {
  const viz = loadVisualizer();
  assert.throws(() => viz.fn("loadSample")("nope"), /Unknown sample/);
  viz.dom.window.close();
});

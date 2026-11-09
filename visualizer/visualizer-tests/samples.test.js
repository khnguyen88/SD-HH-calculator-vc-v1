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

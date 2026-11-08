const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

test("harness: loads dev HTML and finds the state object", () => {
  const { window } = loadVisualizer();
  assert.ok(window.state, "state missing");
  assert.ok(window.state.ui, "state.ui missing");
  assert.strictEqual(window.state.ui.view, "iso");
});

test("harness: el() function is defined", () => {
  const { fn } = loadVisualizer();
  assert.strictEqual(typeof fn("el"), "function");
});

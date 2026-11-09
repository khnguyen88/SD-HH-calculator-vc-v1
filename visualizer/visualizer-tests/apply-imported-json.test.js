/*
 * applyImportedJson is the shared apply path extracted from
 * importFromJsonFile: file imports AND built-in sample loads both go through
 * it, so samples can never bypass schema validation or walk-reset semantics.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

const VALID = {
  schemaVersion: 1,
  sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", startElev: 100 },
    { id: "A", type: "inlet", rim: 110, crown: 104 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

test("applyImportedJson applies a validated object and sets fileName", () => {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  assert.strictEqual(typeof apply, "function", "applyImportedJson must be a top-level function (window-exposed)");
  apply(VALID, "custom name");
  assert.strictEqual(viz.window.state.imported.structures.length, 2);
  assert.strictEqual(viz.window.state.imported.pipes.length, 1);
  assert.strictEqual(viz.window.state.ui.fileName, "custom name");
  assert.strictEqual(viz.window.state.ui.mode, "explore");
  assert.notStrictEqual(viz.window.state.ui.walkStartId, null, "walk start must be set after apply");
  viz.dom.window.close();
});

test("applyImportedJson defaults fileName to empty string", () => {
  const viz = loadVisualizer();
  viz.fn("applyImportedJson")(VALID);
  assert.strictEqual(viz.window.state.ui.fileName, "");
  viz.dom.window.close();
});

test("applyImportedJson throws on an invalid object", () => {
  const viz = loadVisualizer();
  const bad = { schemaVersion: 2, sourceApp: 7, structures: "no", pipes: [], outfall: null };
  assert.throws(() => viz.fn("applyImportedJson")(bad), /JSON validation failed/);
  viz.dom.window.close();
});

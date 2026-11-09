/*
 * Warnings: drop structures (internal drop > 0.5 ft) and slope-vs-invert
 * mismatches surface through the existing warning banner.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

function loadNetwork(pipes) {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    outfall: { structureId: "OUT", tailwaterElev: 89 },
    structures: [
      { id: "OUT", type: "outfall", rim: 89 },
      { id: "MH", type: "manhole", rim: 95 },
      { id: "UP", type: "manhole", rim: 105 },
    ],
    pipes,
  };
  apply(obj, "warn.json");   // applyImportedJson returns undefined and THROWS on failure
  assert.strictEqual(viz.window.state.imported.pipes.length, pipes.length, "network did not import");
  return viz;
}

const SLOPE_OK_PIPE = { id: "PB", fromId: "UP", toId: "MH", shape: "circular", size: 18, n: 0.013,
  slope: 0.005, length: 200, angle: 0, splitRole: "", designQ: 3.4, usInvert: 101, dsInvert: 100 };

test("drop banner fires at a 10-ft drop with correct text", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  const a = viz.window.state.analysis;
  assert.strictEqual(a.dropStructures.length, 1);
  const d = a.dropStructures[0];
  assert.strictEqual(d.id, "MH");
  assert.strictEqual(d.dropFt, 10);

  const renderAll = viz.fn("renderAll");
  renderAll();
  const banner = viz.window.document.getElementById("warningBanner");
  const text = banner.textContent;
  assert.ok(/Drop structure MH/.test(text), "banner names the structure: " + text);
  assert.ok(/10\.00 ft drop/.test(text), "banner states the drop: " + text);
  assert.ok(/100\.00/.test(text) && /90\.00/.test(text), "banner states both inverts: " + text);
  viz.dom.window.close();
});

test("drop banner stays silent at a 0.4-ft drop", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 100.4, dsInvert: 99.4 },
    { id: "PB", fromId: "UP", toId: "MH", shape: "circular", size: 18, n: 0.013,
      slope: 0.005, length: 200, angle: 0, splitRole: "", designQ: 3.4, usInvert: 101, dsInvert: 100 },
  ]);
  assert.strictEqual(viz.window.state.analysis.dropStructures.length, 0);
  viz.dom.window.close();
});

test("outfalls are never drop structures", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  // OUT is an outfall with an incoming pipe at dsInv 89 — must NOT be flagged.
  const ids = viz.window.state.analysis.dropStructures.map((d) => d.id);
  assert.ok(ids.indexOf("OUT") === -1);
  viz.dom.window.close();
});

test("slope banner fires when (usInv-dsInv)/L disagrees with declared slope", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    // computed = 1/200 = 0.005 vs declared 0.01 -> |diff| 0.005 > max(0.002, 0.002) -> flag
    Object.assign({}, SLOPE_OK_PIPE, { slope: 0.01 }),
  ]);
  const a = viz.window.state.analysis;
  assert.strictEqual(a.slopeMismatches.length, 1);
  assert.strictEqual(a.slopeMismatches[0].id, "PB");

  const renderAll = viz.fn("renderAll");
  renderAll();
  const text = viz.window.document.getElementById("warningBanner").textContent;
  assert.ok(/PB/.test(text), "banner names the pipe: " + text);
  viz.dom.window.close();
});

test("slope banner silent when consistent (computed 0.005 vs declared 0.005)", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  assert.strictEqual(viz.window.state.analysis.slopeMismatches.length, 0);
  viz.dom.window.close();
});

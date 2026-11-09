/*
 * One-click handoff from the calculator: #data=<encoded JSON> URL hash.
 * Valid payloads load through the shared applyImportedJson path; garbage
 * hashes must never crash the app (empty start + error surfaced + hash
 * stripped so a refresh does not retry).
 */
const test = require("node:test");
const assert = require("node:assert");
const { VirtualConsole } = require("jsdom");
const { loadVisualizer } = require("./_harness");

function samplePayload() {
  return {
    schemaVersion: 1,
    sourceApp: "storm-drain-design-calculator",
    structures: [
      { id: "A", type: "manhole", rim: 110, startElev: null, crown: 104 },
      { id: "OUT", type: "outfall", rim: null, startElev: 100, crown: null }
    ],
    pipes: [
      { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
        n: 0.013, slope: 0.005, length: 100, designQ: 2.5 }
    ],
    outfall: { structureId: "OUT", tailwaterElev: 100 },
    config: { stormLabel: "10-yr", units: "us-customary", hglMethod: "legacy-both-crown" }
  };
}

test("#data= hash loads through the shared import path at boot", () => {
  const payload = samplePayload();
  const url = "http://localhost/visualizer.html#data=" + encodeURIComponent(JSON.stringify(payload));
  const viz = loadVisualizer(null, { url });
  const w = viz.window;
  assert.ok(w.state.imported, "hash payload not imported");
  assert.strictEqual(w.state.imported.structures.length, 2);
  assert.strictEqual(w.state.ui.fileName, "(from calculator)");
  assert.strictEqual(w.document.getElementById("fileName").textContent, "(from calculator)");
  assert.strictEqual(w.location.hash, "", "hash must be stripped after import");
  assert.strictEqual(w.state.ui.hglMethod, "legacy-both-crown", "config.hglMethod must apply");
});

test("garbage #data= hash: no crash, empty start, error surfaced, hash stripped", () => {
  const vc = new VirtualConsole();
  const alerts = [];
  vc.on("jsdomError", (e) => {
    if (String(e.message || "").includes("window.alert")) alerts.push(String(e.message));
  });
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html#data=%ZZ-not-json", virtualConsole: vc });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null, "must start empty");
  assert.strictEqual(w.location.hash, "", "hash must be stripped");
  assert.strictEqual(w.state.ui.fileName, "");
  assert.ok(alerts.length > 0, "the import-error alert must fire");
});

test("importFromHash works when the visualizer is already open", () => {
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html" });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null);
  w.location.hash = "#data=" + encodeURIComponent(JSON.stringify(samplePayload()));
  assert.strictEqual(w.importFromHash(), true);
  assert.ok(w.state.imported, "payload imported on live page");
  assert.strictEqual(w.state.ui.hglMethod, "legacy-both-crown");
  assert.strictEqual(w.location.hash, "");
});

test("non-#data= hash is ignored (normal startup)", () => {
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html#section" });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null);
  assert.strictEqual(w.location.hash, "#section", "unrelated hash must be untouched");
});

test("#data= hash with schema-invalid payload surfaces the error and starts empty", () => {
  const vc = new VirtualConsole();
  const alerts = [];
  vc.on("jsdomError", (e) => {
    if (String(e.message || "").includes("window.alert")) alerts.push(String(e.message));
  });
  const bad = { schemaVersion: 1, sourceApp: "x", structures: "not-an-array" };
  const url = "http://localhost/visualizer.html#data=" + encodeURIComponent(JSON.stringify(bad));
  const viz = loadVisualizer(null, { url, virtualConsole: vc });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null, "invalid payload must not import");
  assert.strictEqual(w.location.hash, "");
  assert.ok(alerts.length > 0, "validation errors must surface");
});

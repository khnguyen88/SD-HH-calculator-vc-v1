/*
 * Pipe-end crown floors: when a pipe has end inverts, its HGL walk floor is
 * that end's invert + barrel height (its own soffit), not the neighboring
 * structure's outgoing-pipe crown. Per-end fallback keeps old behavior when
 * an invert is absent.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

// Drop network from the spec's motivating case:
//   OUT (outfall, tailwater 89) <-- PA (24", usInv 90, dsInv 89, L 100, Q 9) -- MH
//   MH <-- PB (18", usInv 101, dsInv 100, L 200, Q 3.4) -- UP (rim 105)
// Under old behavior PB's downstream floor = MH's structure crown (92);
// with inverts it is PB's own soffit: 100 + 1.5 = 101.5.
function loadDropNetwork(withInverts) {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const mkPipe = (id, fromId, toId, size, length, designQ, usInv, dsInv) => {
    const p = { id, fromId, toId, shape: "circular", size, n: 0.013, slope: 0.01, length, angle: 0, splitRole: "", designQ };
    if (withInverts) { p.usInvert = usInv; p.dsInvert = dsInv; }
    return p;
  };
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    outfall: { structureId: "OUT", tailwaterElev: 89 },
    structures: [
      { id: "OUT", type: "outfall", rim: 89, startElev: 89 },   // startElev = fixed tailwater
      { id: "MH", type: "manhole", rim: 95, crown: 92 },
      { id: "UP", type: "manhole", rim: 105 },
    ],
    pipes: [
      mkPipe("PA", "MH", "OUT", 24, 100, 9, 90, 89),
      mkPipe("PB", "UP", "MH", 18, 200, 3.4, 101, 100),
    ],
  };
  apply(obj, "drop.json");   // applyImportedJson returns undefined and THROWS on failure
  const st = viz.window.state;
  assert.strictEqual(st.imported.pipes.length, 2, "network did not import");
  return viz;
}

const PATH = ["OUT", "PA", "MH", "PB", "UP"];

function walkRows(viz, method) {
  viz.window.state.ui.hglMethod = method;
  const buildLedger = viz.fn("buildLedger");
  const rows = buildLedger(PATH, viz.window.state, viz.window.state.imported.kbTable, method);
  const annotate = viz.fn("annotateLedgerHgl");
  return annotate(rows, viz.window.state, method);
}

function hfRow(rows, id) {
  const r = rows.find((x) => x.kind === "hf" && x.id === id);
  assert.ok(r, "no hf row for " + id);
  return r;
}

test("pipeBarrelHeightFt: circular diameter/12, elliptical RISE/12, bad input null", () => {
  const viz = loadVisualizer();
  const h = viz.fn("pipeBarrelHeightFt");
  assert.strictEqual(h("circular", 24), 2);
  assert.strictEqual(h("circular", 18), 1.5);
  assert.strictEqual(h("elliptical", "38x24"), 2);
  assert.strictEqual(h("elliptical", "38X24"), 2);
  assert.strictEqual(h("circular", null), null);
  assert.strictEqual(h("elliptical", "garbage"), null);
  viz.dom.window.close();
});

test("with inverts: PB downstream floor is its own soffit 101.5, not MH crown 92", () => {
  const viz = loadDropNetwork(true);
  const rows = walkRows(viz, "hec22");
  const pb = hfRow(rows, "PB");
  assert.strictEqual(pb.hglDn, 101.5);
  // PA: ds floor = 89 + 2 = 91 (its own dsInvert soffit)
  const pa = hfRow(rows, "PA");
  assert.strictEqual(pa.hglDn, 91);
  viz.dom.window.close();
});

test("with inverts: hec22 hglUp = hglDn + Hf (101.5 + ~0.2104); legacy also pins at upstream soffit 102.5", () => {
  const viz = loadDropNetwork(true);

  const hec = walkRows(viz, "hec22");
  const pbHec = hfRow(hec, "PB");
  // Hf = Sf*L, Sf from full-flow Manning: (Q*n/(1.486*A*R^(2/3)))^2
  // A=1.767146, R=0.375 -> Hf ~ 0.2104
  assert.ok(Math.abs(pbHec.hgl - (101.5 + 0.21062)) < 0.01,
    "hec22 PB hglUp expected ~101.71, got " + pbHec.hgl);

  const legacy = walkRows(viz, "legacy-both-crown");
  const pbLegacy = hfRow(legacy, "PB");
  assert.strictEqual(pbLegacy.hglDn, 101.5);
  assert.strictEqual(pbLegacy.hgl, 102.5, "legacy upstream pin at usInvert 101 + 1.5");
  viz.dom.window.close();
});

test("without inverts: PB floor falls back to MH structure crown 92 (old behavior)", () => {
  const viz = loadDropNetwork(false);
  const rows = walkRows(viz, "hec22");
  const pb = hfRow(rows, "PB");
  assert.strictEqual(pb.hglDn, 92);
  viz.dom.window.close();
});

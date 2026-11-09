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

test("with inverts: hec22 hglUp = hglDn + Hf (101.5 + ~0.210); legacy also pins at upstream soffit 102.5", () => {
  const viz = loadDropNetwork(true);

  const hec = walkRows(viz, "hec22");
  const pbHec = hfRow(hec, "PB");
  // Hf = Sf*L, Sf from full-flow Manning: (Q*n/(1.486*A*R^(2/3)))^2
  // A=1.767146, R=0.375 -> Hf ~ 0.210
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

test("mixed ends: pipe with dsInvert only gets corrected dn floor and legacy up floor", () => {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    outfall: { structureId: "OUT", tailwaterElev: 89 },
    structures: [
      { id: "OUT", type: "outfall", rim: 89, startElev: 89 },
      { id: "MH", type: "manhole", rim: 95, crown: 92 },
      { id: "UP", type: "manhole", rim: 105 },
    ],
    pipes: [
      { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013, slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
      { id: "PB", fromId: "UP", toId: "MH", shape: "circular", size: 18, n: 0.013, slope: 0.01, length: 200, angle: 0, splitRole: "", designQ: 3.4, dsInvert: 100 },  // no usInvert
    ],
  };
  apply(obj, "mixed.json");   // throws on failure
  const rows = walkRows(viz, "hec22");
  const pb = hfRow(rows, "PB");
  assert.strictEqual(pb.hglDn, 101.5, "dn floor corrected from own dsInvert");
  // crownUp falls back to crownOf(UP): UP has no crown field -> null -> no legacy pin test here;
  // hec22 hglUp = hglDn + Hf regardless.
  assert.ok(Math.abs(pb.hgl - (101.5 + 0.21062)) < 0.01, "hec22 hglUp = hglDn + Hf: " + pb.hgl);
  viz.dom.window.close();
});

function profileRows(viz) {
  const buildLedger = viz.fn("buildLedger");
  const annotate = viz.fn("annotateLedgerHgl");
  const profileStations = viz.fn("profileStations");
  viz.window.state.ui.hglMethod = "hec22";
  const rows = annotate(buildLedger(PATH, viz.window.state, viz.window.state.imported.kbTable, "hec22"),
    viz.window.state, "hec22");
  return profileStations(rows, viz.window.state.imported, viz.window.state.overrides);
}

function stPoint(rows, id) {
  const r = rows.filter((x) => x.id === id);
  assert.ok(r.length > 0, "no station points for " + id);
  return r;
}

test("profile with inverts: stations carry true pipe-end inverts; drop draws as vertical step", () => {
  const viz = loadDropNetwork(true);
  const rows = profileRows(viz);

  // PA contributes points at BOTH ends: ds at station 0 (inv 89), us at station 100 (inv 90).
  const pa = stPoint(rows, "PA");
  const paDs = pa.find((p) => p.invert === 89);
  const paUs = pa.find((p) => p.invert === 90);
  assert.ok(paDs && paDs.station === 0, "PA ds point (inv 89) at station 0");
  assert.ok(paUs && Math.abs(paUs.station - 100) < 1e-9, "PA us point (inv 90) at station 100");
  assert.strictEqual(paUs.crown, 92, "PA us crown = 90 + 2");

  // PB: ds invert 100 at station 100, us invert 101 at station 300.
  const pb = stPoint(rows, "PB");
  const pbDs = pb.find((p) => p.invert === 100);
  const pbUs = pb.find((p) => p.invert === 101);
  assert.ok(pbDs && Math.abs(pbDs.station - 100) < 1e-9, "PB ds point (inv 100) at station 100");
  assert.ok(pbUs && Math.abs(pbUs.station - 300) < 1e-9, "PB us point (inv 101) at station 300");
  assert.strictEqual(pbDs.crown, 101.5, "PB ds crown = 100 + 1.5");

  // The 10-ft drop inside MH appears as the invert step at station 100: PA us 90 vs PB ds 100.
  assert.ok(paUs && pbDs && Math.abs(paUs.station - pbDs.station) < 1e-9,
    "drop renders as two points at the same station (90 vs 100)");
  viz.dom.window.close();
});

test("profile with inverts: structure stations use derived flowline (MH 90 from PA usInvert)", () => {
  const viz = loadDropNetwork(true);
  const rows = profileRows(viz);
  const mh = stPoint(rows, "MH");
  assert.ok(mh.some((p) => p.kind === "structure" && p.invert === 90),
    "MH structure station invert = min outgoing usInvert = 90");
  viz.dom.window.close();
});

test("profile with inverts: invert/size reads are override-aware (raw imported stays untouched)", () => {
  const viz = loadDropNetwork(true);
  // Same shape applyImportedJson builds when restoring user edits (see roundtrip.test.js).
  viz.window.state.overrides.byId.PB = { dsInvert: 99, size: 30 };
  const rows = profileRows(viz);
  const pb = stPoint(rows, "PB");
  const pbDs = pb.find((p) => p.kind === "pipe" && p.invert === 99);
  assert.ok(pbDs, "PB ds point must use overridden dsInvert 99, not the raw imported 100");
  assert.strictEqual(pbDs.crown, 101.5, "PB ds crown = overridden 99 + overridden size 30 barrel 2.5");
  assert.ok(!pb.some((p) => p.kind === "pipe" && p.invert === 100),
    "stale raw dsInvert 100 must not leak into the profile");
  assert.strictEqual(viz.window.state.imported.pipes.find((p) => p.id === "PB").dsInvert, 100,
    "imported baseline stays at the original 100");
  assert.strictEqual(viz.window.state.imported.pipes.find((p) => p.id === "PB").size, 18,
    "imported baseline size stays 18");
  viz.dom.window.close();
});

test("profile without inverts: fallback values match today's single-point-per-pipe behavior", () => {
  const viz = loadDropNetwork(false);
  const rows = profileRows(viz);
  const pa = stPoint(rows, "PA");
  // Old behavior: one point per pipe row at the From end, invert from structure startElev or EGL-3.
  const paPipe = pa.filter((p) => p.kind === "pipe");
  assert.strictEqual(paPipe.length, 1, "without inverts, PA contributes exactly one pipe point");
  viz.dom.window.close();
});

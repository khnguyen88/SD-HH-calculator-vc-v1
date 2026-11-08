/*
 * Drift test: parity with a workbook exported by the MAIN calculator app.
 *
 * fixtures/main-app-export.xlsx is generated headlessly by the main app's own
 * code via fixtures/generate-fixture.js (see fixtures/README.md). These tests
 * re-compute Hf / Hb / end-to-end EGL with the VISUALIZER's functions and
 * assert they agree with the main app's exported values. Formula drift between
 * the two apps breaks these tests immediately.
 */
const test = require("node:test");
const assert = require("node:assert");
const path = require("path");
const fs = require("fs");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

const FIXTURE = path.join(__dirname, "fixtures", "main-app-export.xlsx");
const TOL_PIPE = 0.001;
const TOL_STRUCT = 0.001;
const TOL_EGL = 0.01;

// Real export schema (confirmed against the main app's buildWorkbook):
//   "Pipe Sizing":       ID | From Structure | To Structure | Angle (deg) | Shape |
//                        Size (in or SPANxRISE) | n | US Invert (ft) | DS Invert (ft) |
//                        Slope (ft-ft) | Length (ft) | Design Q (cfs) | ...
//   "Junction Structure": Structure ID | Type | Force Fixed | Fixed-Start Elev (ft) |
//                        Pipe Crown (ft) | Rim-Grate Elev (ft) | Captured Q (cfs) |
//                        Q from Pipes (cfs) | Total Flow (cfs) | Outgoing Pipe ID |
//                        Hf (ft) | Kb | Hb (ft) | Vout (fps) | Upstream HGL (ft) | ...
// Hf lives on the Junction Structure sheet (one per non-outfall structure's
// outgoing pipe), not on the Pipe Sizing sheet.
function loadFixture() {
  const wb = XLSX.readFile(FIXTURE);
  const sh = (name) => {
    assert.ok(wb.Sheets[name], `fixture workbook missing sheet: ${name}`);
    return XLSX.utils.sheet_to_json(wb.Sheets[name], { defval: null });
  };
  return { pipeRows: sh("Pipe Sizing"), strRows: sh("Junction Structure") };
}

const numOrNull = (v) => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return isFinite(n) ? n : null;
};

// Map fixture rows to the visualizer's imported-model shape.
function mapImported(strRows, pipeRows) {
  const structures = strRows.map((r) => ({
    id: String(r["Structure ID"]),
    type: String(r["Type"] || "manhole").toLowerCase(),
    rim: numOrNull(r["Rim-Grate Elev (ft)"]),
    startElev: numOrNull(r["Fixed-Start Elev (ft)"]),
    crown: numOrNull(r["Pipe Crown (ft)"]),
    forceElev: String(r["Force Fixed"] || "").toUpperCase() === "TRUE",
    exportedElev: numOrNull(r["Upstream HGL (ft)"])
  }));
  const pipes = pipeRows.map((r) => ({
    id: String(r["ID"]),
    fromId: String(r["From Structure"]),
    toId: String(r["To Structure"]),
    shape: String(r["Shape"] || "circular").trim().toLowerCase(),
    size: String(r["Size (in or SPANxRISE)"] == null ? "" : r["Size (in or SPANxRISE)"]).trim(),
    n: Number(r["n"]),
    slope: Number(r["Slope (ft-ft)"]),
    length: Number(r["Length (ft)"]),
    angle: numOrNull(r["Angle (deg)"]) ?? 0,
    designQ: Number(r["Design Q (cfs)"])
  }));
  const outfall = structures.find((s) => s.type === "outfall");
  assert.ok(outfall, "fixture has no outfall structure");
  return {
    structures,
    pipes,
    outfallRow: outfall,
    imported: {
      structures,
      pipes,
      // seedExample() root outfall is "OUTFALL" at 100.0 ft (first outfall row);
      // the second outfall (BYPASS at 97.0) is a separate branch, not the root.
      outfall: { structureId: outfall.id, tailwaterElev: outfall.startElev },
      kbTable: null, // caller replaces with the visualizer's KB_SEED
      config: {}
    }
  };
}

// Reverse BFS upstream from the outfall. Returns alternating
// [structureId, pipeId, structureId, ...] starting at the outfall, or null.
function findPathUpstream(outfallSid, targetSid, pipes) {
  const parent = { [outfallSid]: null };
  const parentPipe = {};
  const queue = [outfallSid];
  while (queue.length) {
    const cur = queue.shift();
    for (const p of pipes) {
      if (p.toId === cur && !(p.fromId in parent)) {
        parent[p.fromId] = cur;
        parentPipe[p.fromId] = p.id;
        queue.push(p.fromId);
      }
    }
  }
  if (!(targetSid in parent)) return null;
  const path = [];
  let cur = targetSid;
  while (cur) {
    path.push(cur);
    if (parentPipe[cur]) path.push(parentPipe[cur]);
    cur = parent[cur];
  }
  return path.reverse();
}

test("drift: every structure's outgoing-pipe Hf matches local recompute within 0.001 ft", () => {
  const { window: vw, fn } = loadVisualizer();
  const { pipeRows, strRows } = loadFixture();
  const { pipes } = mapImported(strRows, pipeRows);
  const byId = new Map(pipes.map((p) => [p.id, p]));

  let checked = 0;
  for (const sr of strRows) {
    const sid = String(sr["Structure ID"]);
    const outId = sr["Outgoing Pipe ID"];
    if (outId === null || outId === "") continue; // outfall / no outflow
    const pipe = byId.get(String(outId));
    assert.ok(pipe, `structure ${sid}: outgoing pipe ${outId} not found`);
    const exported = Number(sr["Hf (ft)"]);
    const A = fn("pipeArea")(pipe.shape, pipe.size);
    const R = fn("pipeRadius")(pipe.shape, pipe.size);
    const Sf = fn("frictionSlope")(pipe.designQ, pipe.n, A, R);
    const local = fn("frictionLoss")(Sf, pipe.length);
    assert.ok(
      Math.abs(local - exported) <= TOL_PIPE,
      `Hf drift at ${sid} (pipe ${pipe.id}): exported=${exported}, local=${local}`
    );
    checked++;
  }
  assert.ok(checked >= 1, "no structures with an outgoing pipe were checked");
});

test("drift: every structure's Hb matches local recompute within 0.001 ft", () => {
  const { window: vw, fn } = loadVisualizer();
  const { pipeRows, strRows } = loadFixture();
  const { structures, pipes } = mapImported(strRows, pipeRows);
  const pipeById = new Map(pipes.map((p) => [p.id, p]));

  let checked = 0;
  for (const s of structures) {
    if (s.type === "outfall") continue;
    const sr = strRows.find((r) => String(r["Structure ID"]) === s.id);
    const outId = sr["Outgoing Pipe ID"];
    if (outId === null || outId === "") continue;
    const outPipe = pipeById.get(String(outId));
    assert.ok(outPipe, `structure ${s.id}: outgoing pipe ${outId} not found`);

    // Every pipe entering this structure contributes its own Design Q and angle.
    const inflows = pipes
      .filter((p) => p.toId === s.id)
      .map((p) => ({ angleDeg: p.angle, Qcfs: p.designQ }));
    // Vout uses the structure's TOTAL flow (K), not the outgoing pipe's Design Q:
    // for a splitter the outgoing primary pipe carries only the primary share.
    const Qtotal = Number(sr["Total Flow (cfs)"]);
    const Aout = fn("pipeArea")(outPipe.shape, outPipe.size);
    const res = fn("structureLoss")(inflows, Qtotal, Aout, s.type, vw.KB_SEED);
    if (res.error) continue;

    const exported = Number(sr["Hb (ft)"]);
    assert.ok(
      Math.abs(res.Hb - exported) <= TOL_STRUCT,
      `Hb drift at ${s.id}: exported=${exported}, local=${res.Hb}`
    );
    checked++;
  }
  assert.ok(checked >= 1, "no structures were checked");
});

test("drift: end-to-end EGL at every structure matches within 0.01 ft", () => {
  const { window: vw, fn } = loadVisualizer();
  const { pipeRows, strRows } = loadFixture();
  const { structures, pipes, outfallRow, imported } = mapImported(strRows, pipeRows);

  imported.kbTable = vw.KB_SEED;
  vw.state.imported = imported;
  vw.state.overrides = { byId: {} };

  // The main app's "Upstream HGL (ft)" column is the accumulated grade-line walk
  // (downstream elevation + Hf + Hb at each upstream step). The visualizer
  // reproduces that same walk as its EGL, so the last ledger row's `after` must
  // match the exported value at each structure.
  let checked = 0;
  for (const s of structures) {
    if (s.type === "outfall") continue;
    const path = findPathUpstream(outfallRow.id, s.id, pipes);
    if (!path) continue; // structure not upstream of the root outfall
    const rows = fn("buildLedger")(path, vw.state, vw.KB_SEED, "hec22");
    assert.ok(rows.length > 0, `empty ledger for ${s.id}`);
    const local = rows[rows.length - 1].after;
    assert.ok(
      Math.abs(local - s.exportedElev) <= TOL_EGL,
      `EGL drift at ${s.id}: exported=${s.exportedElev}, local=${local}`
    );
    checked++;
  }
  assert.ok(checked >= 1, "no upstream structures were checked");
});

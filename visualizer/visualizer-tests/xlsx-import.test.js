/*
 * Importer-level test for the XLSX path. The visualizer imports workbooks
 * exported by the MAIN calculator; those sheets use long, human-readable
 * headers ("Size (in or SPANxRISE)") rather than JSON-style keys ("size").
 * This test feeds a real main-app export through importFromXlsxFile() so a
 * header-name regression (all pipes silently importing as 18") fails loudly.
 */
const test = require("node:test");
const assert = require("node:assert");
const path = require("path");
const fs = require("fs");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

const FIXTURE = path.join(__dirname, "fixtures", "main-app-export.xlsx");
const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

// jsdom 24 does not implement File.prototype.arrayBuffer(). Polyfill it via
// FileReader so the real File + importer path is exercised. The reader result
// is copied into a Node-realm Uint8Array: jsdom's ArrayBuffer lives in another
// realm, so xlsx's `instanceof ArrayBuffer` check would miss it otherwise.
function ensureFileArrayBuffer(window) {
  const proto = window.File && window.File.prototype;
  if (proto && typeof proto.arrayBuffer !== "function") {
    proto.arrayBuffer = function fileArrayBuffer() {
      return new Promise((resolve, reject) => {
        const reader = new window.FileReader();
        reader.onload = () => resolve(new Uint8Array(reader.result));
        reader.onerror = () => reject(reader.error || new Error("FileReader failed"));
        reader.readAsArrayBuffer(this);
      });
    };
  }
}

async function importFixture(window) {
  ensureFileArrayBuffer(window);
  const buf = fs.readFileSync(FIXTURE);
  const blob = new window.Blob([buf], { type: XLSX_TYPE });
  const file = new window.File([blob], "main-app-export.xlsx", { type: XLSX_TYPE });
  await window.importFromXlsxFile(file);
}

// Build a synthetic main-app-style workbook in memory. Header strings must match
// exactly what importFromXlsxFile reads (the importer keys off human-readable
// headers, not JSON field names).
function buildSyntheticWorkbook() {
  const strRows = [
    { "Structure ID": "OUT", "Type": "outfall", "Fixed-Start Elev (ft)": 100,
      "Pipe Crown (ft)": 99, "Rim-Grate Elev (ft)": null, "Total Flow (cfs)": 0, "Outgoing Pipe ID": "" },
    { "Structure ID": "S", "Type": "splitter", "Fixed-Start Elev (ft)": null,
      "Pipe Crown (ft)": 104, "Rim-Grate Elev (ft)": 107, "Total Flow (cfs)": 7, "Outgoing Pipe ID": "P1" },
    { "Structure ID": "A", "Type": "inlet", "Fixed-Start Elev (ft)": null,
      "Pipe Crown (ft)": 101, "Rim-Grate Elev (ft)": 110, "Total Flow (cfs)": 7, "Outgoing Pipe ID": "P-in" },
    { "Structure ID": "B", "Type": "outfall", "Fixed-Start Elev (ft)": 98,
      "Pipe Crown (ft)": 97, "Rim-Grate Elev (ft)": null, "Total Flow (cfs)": 0, "Outgoing Pipe ID": "" }
  ];
  const pipeRows = [
    { "ID": "P-in", "From Structure": "A", "To Structure": "S", "Shape": "circular",
      "Size (in or SPANxRISE)": 18, "n": 0.013, "Slope (ft-ft)": 0.005, "Length (ft)": 100,
      "Angle (deg)": 0, "Design Q (cfs)": "", "Split Role": "" },
    { "ID": "P1", "From Structure": "S", "To Structure": "OUT", "Shape": "circular",
      "Size (in or SPANxRISE)": 24, "n": 0.013, "Slope (ft-ft)": 0.005, "Length (ft)": 120,
      "Angle (deg)": 0, "Design Q (cfs)": 5, "Split Role": "primary" },
    { "ID": "P2", "From Structure": "S", "To Structure": "B", "Shape": "circular",
      "Size (in or SPANxRISE)": 15, "n": 0.013, "Slope (ft-ft)": 0.005, "Length (ft)": 80,
      "Angle (deg)": 45, "Design Q (cfs)": 2, "Split Role": "secondary" }
  ];
  const daRows = [
    { "ID": "DA-X", "Structure": "A", "Area A (ac)": 1.2, "C": 0.6, "Tc (min)": 15 }
  ];
  const tr55Rows = [
    { "Drainage Area": "DA-X", "Order": 1, "Type": "sheet", "n": 0.24, "L (ft)": 50,
      "s (ft/ft)": 0.01, "P2 (in)": 3.2, "Surface": "lawn", "Area a (sf)": 2000,
      "Wetted Perimeter Pw (ft)": 40 }
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(strRows), "Junction Structure");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(pipeRows), "Pipe Sizing");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(daRows), "Drainage Area");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(tr55Rows), "TR-55 Segments");
  return wb;
}

async function importSynthetic(window) {
  ensureFileArrayBuffer(window);
  const arr = XLSX.write(buildSyntheticWorkbook(), { type: "array", bookType: "xlsx" });
  const blob = new window.Blob([arr], { type: XLSX_TYPE });
  const file = new window.File([blob], "syn.xlsx", { type: XLSX_TYPE });
  await window.importFromXlsxFile(file);
}

test("xlsx import: reads the real main-app export headers", async () => {
  const { window } = loadVisualizer({ XLSX });
  await importFixture(window);

  const imp = window.state.imported;
  assert.ok(imp, "state.imported populated");
  assert.strictEqual(imp.structures.length, 6, "6 structures");
  assert.strictEqual(imp.pipes.length, 5, "5 pipes");

  // Pipe ids must come from the export (r12..r16), never generated P-1.. fallbacks.
  const byId = {};
  for (const p of imp.pipes) {
    byId[p.id] = p;
    assert.ok(!/^P-\d+$/.test(p.id), `pipe id ${p.id} must not be a generated fallback`);
  }
  assert.deepStrictEqual(Object.keys(byId).sort(), ["r12", "r13", "r14", "r15", "r16"]);

  // Sizes match "Size (in or SPANxRISE)" per exported pipe id (24,18,30,24,18).
  assert.strictEqual(byId.r12.size, 24);
  assert.strictEqual(byId.r13.size, 18);
  assert.strictEqual(byId.r14.size, 30, "30-in pipe must not default to 18");
  assert.strictEqual(byId.r15.size, 24);
  assert.strictEqual(byId.r16.size, 18);

  // Fixed-start elevation survives the round trip.
  const outfall = imp.structures.find((s) => s.id === "OUTFALL");
  assert.ok(outfall, "OUTFALL structure present");
  assert.strictEqual(outfall.startElev, 100);
  assert.strictEqual(outfall.forceElev, true, "Force Fixed TRUE honored");

  // Total flow + declared outgoing pipe are read from the Junction Structure sheet.
  const stj = imp.structures.find((s) => s.id === "ST-J");
  assert.ok(stj, "ST-J structure present");
  assert.ok(stj.totalQ > 0, "ST-J totalQ read from Total Flow (cfs)");
  assert.ok(stj.outPipeId && stj.outPipeId.length > 0, "ST-J outPipeId read");
  assert.strictEqual(stj.outPipeId, "r14");

  // Captured Q comes from the Junction Structure sheet, not the 1-yr DA column.
  const st1 = imp.structures.find((s) => s.id === "ST-1");
  assert.ok(st1 && st1.capturedQ > 0, "ST-1 capturedQ read");

  // Import resets the walk cursor and branch choices (stale-path guard).
  assert.strictEqual(window.state.cursor.id, "OUTFALL", "cursor reset to outfall");
  assert.strictEqual(
    Object.keys(window.state.ui.branchChoices.byStructureId).length,
    0,
    "branch choices cleared"
  );
});

test("xlsx import (real fixture): split roles, outfalls, DAs, TR-55, splitters", async () => {
  const { window } = loadVisualizer({ XLSX });
  await importFixture(window);

  const imp = window.state.imported;
  const pipeById = Object.create(null);
  for (const p of imp.pipes) pipeById[p.id] = p;

  assert.strictEqual(pipeById.r15.splitRole, "primary", "r15 primary role read");
  assert.strictEqual(pipeById.r16.splitRole, "secondary", "r16 secondary role read");
  for (const id of ["r12", "r13", "r14"]) {
    assert.strictEqual(pipeById[id].splitRole, "", `${id} has no split role`);
  }

  const a = window.state.analysis;
  assert.ok(a.outfallIds.includes("OUTFALL"), "OUTFALL is an outfall");
  assert.ok(a.outfallIds.includes("BYPASS"), "BYPASS is an outfall");
  assert.strictEqual(a.defaultWalkStart, "OUTFALL", "first outfall is the walk start");

  assert.strictEqual(imp.drainageAreas.length, 2, "two drainage areas");
  const da1 = imp.drainageAreas.find((d) => d.id === "DA-1");
  assert.ok(da1, "DA-1 present");
  assert.strictEqual(da1.structureId, "ST-1", "DA-1 linked to ST-1");

  assert.strictEqual(imp.tr55Segments.length, 3, "three TR-55 segments");

  assert.ok(a.splitterIds.includes("SPLIT-1"), "SPLIT-1 detected as splitter");
  assert.strictEqual(a.primaryPipeByStructureId["SPLIT-1"], "r15", "r15 is SPLIT-1 primary");
});

test("xlsx import (synthetic): split roles, blank Design Q, DA/TR-55, analysis", async () => {
  const { window } = loadVisualizer({ XLSX });
  await importSynthetic(window);

  const imp = window.state.imported;
  const pipeById = Object.create(null);
  for (const p of imp.pipes) pipeById[p.id] = p;

  assert.strictEqual(pipeById.P1.splitRole, "primary", "primary split role read");
  assert.strictEqual(pipeById.P2.splitRole, "secondary", "secondary split role read");

  // A blank Design Q cell must import as null, never as a fabricated 0.
  assert.strictEqual(pipeById["P-in"].designQ, null, "blank Design Q is null");
  assert.notStrictEqual(pipeById["P-in"].designQ, 0, "blank Design Q is not 0");

  assert.strictEqual(imp.drainageAreas.length, 1, "one drainage area parsed");
  assert.strictEqual(imp.drainageAreas[0].id, "DA-X", "drainage area id parsed");
  assert.strictEqual(imp.drainageAreas[0].structureId, "A", "drainage area linked to A");

  assert.strictEqual(imp.tr55Segments.length, 1, "one TR-55 segment parsed");
  assert.strictEqual(imp.tr55Segments[0].drainageAreaId, "DA-X", "segment joins DA-X");
  assert.strictEqual(imp.tr55Segments[0].order, 1, "segment order parsed");

  const a = window.state.analysis;
  assert.ok(a.missingDesignQ.includes("P-in"), "blank-Design-Q pipe flagged missing");
  assert.ok(a.splitterIds.includes("S"), "S detected as splitter");
  assert.strictEqual(a.primaryPipeByStructureId["S"], "P1", "P1 is S primary");
});

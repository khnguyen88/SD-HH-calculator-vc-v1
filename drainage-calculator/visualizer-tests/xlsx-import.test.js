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

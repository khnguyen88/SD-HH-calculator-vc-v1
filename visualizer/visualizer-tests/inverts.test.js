/*
 * Pipe inverts: optional usInvert/dsInvert fields — schema validation,
 * xlsx column import, JSON passthrough into state.
 */
const test = require("node:test");
const assert = require("node:assert");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

// jsdom 24 does not implement File.prototype.arrayBuffer(). Polyfill it via
// FileReader so the real File + importer path is exercised. The reader result
// is copied into a Node-realm Uint8Array: jsdom's ArrayBuffer lives in another
// realm, so xlsx's `instanceof ArrayBuffer` check would miss it otherwise.
// (Same polyfill as xlsx-import.test.js.)
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

// Header strings must match exactly what importFromXlsxFile reads
// (human-readable headers, not JSON field names) — mirrors xlsx-import.test.js.
function buildSyntheticWorkbook(extraPipeFields) {
  const strRows = [
    { "Structure ID": "OUT", "Type": "outfall", "Fixed-Start Elev (ft)": 89,
      "Pipe Crown (ft)": null, "Rim-Grate Elev (ft)": null, "Total Flow (cfs)": 0, "Outgoing Pipe ID": "" },
    { "Structure ID": "MH", "Type": "manhole", "Fixed-Start Elev (ft)": null,
      "Pipe Crown (ft)": 92, "Rim-Grate Elev (ft)": 95, "Total Flow (cfs)": 9, "Outgoing Pipe ID": "P1" }
  ];
  const pipeRow = {
    "ID": "P1",
    "From Structure": "MH",
    "To Structure": "OUT",
    "Shape": "circular",
    "Size (in or SPANxRISE)": 24,
    "n": 0.013,
    "Slope (ft-ft)": 0.01,
    "Length (ft)": 100,
    "Angle (deg)": 0,
    "Design Q (cfs)": 9,
    "Split Role": ""
  };
  Object.assign(pipeRow, extraPipeFields);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(strRows), "Junction Structure");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([pipeRow]), "Pipe Sizing");
  return wb;
}

// importFromXlsxFile returns undefined and throws on failure — success is
// simply not throwing (mirrors xlsx-import.test.js).
async function importSynthetic(window, wb) {
  ensureFileArrayBuffer(window);
  const arr = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  const blob = new window.Blob([arr], { type: XLSX_TYPE });
  const file = new window.File([blob], "synthetic.xlsx", { type: XLSX_TYPE });
  await window.importFromXlsxFile(file);
}

// validateImportedJson requires schemaVersion 1 + string sourceApp + an
// outfall object at the top level; structure types are lowercase strings.
function base() {
  return {
    schemaVersion: 1,
    sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall" },
      { id: "MH", type: "manhole" }
    ],
    pipes: [{ id: "P1", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013, slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9 }],
    outfall: { structureId: "OUT", tailwaterElev: 89 }
  };
}

test("schema: usInvert/dsInvert absent passes, finite number passes, non-number fails", () => {
  const viz = loadVisualizer();
  const validate = viz.fn("validateImportedJson");

  const absent = validate(base());
  assert.strictEqual(absent.errors.length, 0, "absent inverts must pass: " + absent.errors.join("; "));

  const presentObj = base();
  presentObj.pipes[0].usInvert = 102;
  presentObj.pipes[0].dsInvert = 101;
  const present = validate(presentObj);
  assert.strictEqual(present.errors.length, 0, "finite numbers must pass: " + present.errors.join("; "));

  const badUpObj = base();
  badUpObj.pipes[0].usInvert = "102";
  const badUp = validate(badUpObj);
  assert.ok(badUp.errors.some((e) => /pipes\[0\]\.usInvert/.test(e)), "non-number usInvert must fail with field-named error: " + badUp.errors.join("; "));

  const badDnObj = base();
  badDnObj.pipes[0].dsInvert = "one hundred";
  const badDn = validate(badDnObj);
  assert.ok(badDn.errors.some((e) => /pipes\[0\]\.dsInvert/.test(e)), "non-number dsInvert must fail with field-named error");

  viz.dom.window.close();
});

test("xlsx: US Invert (ft) / DS Invert (ft) columns import into usInvert/dsInvert", async () => {
  const viz = loadVisualizer({ XLSX });
  const wb = buildSyntheticWorkbook({ "US Invert (ft)": 90, "DS Invert (ft)": 89 });
  await importSynthetic(viz.window, wb);
  assert.strictEqual(viz.window.state.imported.pipes.length, 1);
  const p = viz.window.state.imported.pipes[0];
  assert.strictEqual(p.usInvert, 90);
  assert.strictEqual(p.dsInvert, 89);
  viz.dom.window.close();
});

test("xlsx: blank invert cells stay absent", async () => {
  const viz = loadVisualizer({ XLSX });
  const wb = buildSyntheticWorkbook({ "US Invert (ft)": "", "DS Invert (ft)": "" });
  await importSynthetic(viz.window, wb);
  const p = viz.window.state.imported.pipes[0];
  // pickNum returns null for blanks — same convention as designQ/rim/crown.
  assert.strictEqual(p.usInvert, null);
  assert.strictEqual(p.dsInvert, null);
  viz.dom.window.close();
});

test("json: applyImportedJson carries usInvert/dsInvert into state.imported.pipes", () => {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const obj = base();
  obj.structures = [
    { id: "OUT", type: "outfall", rim: 89 },
    { id: "MH", type: "manhole", rim: 95 }
  ];
  obj.pipes[0].usInvert = 90;
  obj.pipes[0].dsInvert = 89;
  // applyImportedJson returns undefined and throws on validation failure —
  // reaching the state assertions means validation passed.
  apply(obj, "test.json");
  assert.strictEqual(viz.window.state.imported.pipes[0].usInvert, 90);
  assert.strictEqual(viz.window.state.imported.pipes[0].dsInvert, 89);
  viz.dom.window.close();
});

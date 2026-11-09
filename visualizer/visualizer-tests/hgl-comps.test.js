// HGL comps: expanded ledger rows must show the HGL computation
// alongside the existing EGL equations, and the ledger header must carry
// the county (MCDOT 4.3.2) HGL criteria note.
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

const SEED = {
  schemaVersion: 1,
  exportedAt: "2026-11-07T10:00:00Z",
  sourceApp: "storm-drain-design-calculator",
  sourceAppVersion: "test",
  config: { stormLabel: "10-yr", units: "us-customary", hglMethod: "hec22" },
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 103, startElev: 100, crown: 99 },
    { id: "A", type: "bend", x: 0, y: -100, rim: 108, startElev: 102, crown: 101 }
  ],
  pipes: [
    {
      id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5
    }
  ],
  kbTable: null,
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

// jsdom 24 lacks File.prototype.text(); the JSON importer relies on it.
function ensureFileText(window) {
  const proto = window.File && window.File.prototype;
  if (proto && typeof proto.text !== "function") {
    proto.text = function fileText() {
      return new Promise((resolve, reject) => {
        const reader = new window.FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error || new Error("FileReader failed"));
        reader.readAsText(this);
      });
    };
  }
}

async function bootWithJson(window, obj) {
  ensureFileText(window);
  const blob = new window.Blob([JSON.stringify(obj)], { type: "application/json" });
  const file = new window.File([blob], "seed.json", { type: "application/json" });
  await window.importFromJsonFile(file);
}

function expandedDetail(document) {
  const host = document.getElementById("ledger");
  return Array.from(host.children)
    .find((n) => (n.getAttribute("style") || "").includes("4px 20px")) || null;
}

test("hf expanded row shows HGL step comps alongside the EGL equations", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.renderAll();
  const detail = expandedDetail(document);
  assert.ok(detail, "expanded detail rendered");
  const text = detail.textContent;
  assert.ok(text.includes("EGL_up = EGL_dn + Hf"), "EGL comp must stay");
  assert.ok(text.includes("HGL_dn = EGL_dn - V²/(2g)"), "HGL_dn formula missing");
  assert.ok(text.includes("HGL_up = HGL_dn + Hf"), "HGL_up formula missing");
  assert.ok(text.includes("HGL_up"), "HGL_up result missing");
});

test("hb expanded row shows the HGL comp (HGL_prev + Hb)", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
  window.renderAll();
  const detail = expandedDetail(document);
  assert.ok(detail, "expanded detail rendered");
  const text = detail.textContent;
  assert.ok(text.includes("HGL_up = HGL_prev + Hb"), "HGL comp missing on hb row");
});

test("start expanded row shows the HGL boundary comp", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "structure", id: "OUT", pathStack: ["OUT"] };
  window.renderAll();
  const detail = expandedDetail(document);
  assert.ok(detail, "expanded detail rendered");
  const text = detail.textContent;
  assert.ok(text.includes("HGL = max(boundary EGL, crown)"), "HGL boundary comp missing");
});

test("ledger header carries the MCDOT 4.3.2 county criteria note", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.renderAll();
  const text = document.getElementById("ledger").textContent;
  assert.ok(text.includes("MCDOT Drainage Design Criteria §4.3.2"),
    "county citation missing from ledger header");
  assert.ok(text.includes("no higher than 1 foot above the crown of the pipe"),
    "county crown criterion missing");
  assert.ok(text.includes("at least one foot below the top of any inlet grate or manhole cover"),
    "county rim criterion missing");
});

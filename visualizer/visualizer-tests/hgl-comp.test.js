// v82 regression: the expanded +Hf row's "HGL step" section rendered its final
// result as "HGL_up = undefined ft" because the hf branch of annotateLedgerHgl
// never set a `hgl` key on hglDetail, while hglCompSection reads hd.hgl.
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

test("expanded +Hf row: HGL step result is a number, never 'undefined'", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1", "A"] };
  window.renderAll();

  const text = document.getElementById("ledger").textContent.replace(/\s+/g, " ");
  assert(!text.includes("undefined"),
    "ledger must not contain 'undefined'; got: " + JSON.stringify(
      text.slice(text.indexOf("HGL step"), text.indexOf("HGL step") + 300)));

  // The HGL step result line must exist and carry the same value the formula
  // line derived (hd.hgl must equal hd.hglUp for hf rows).
  const m = text.match(/HGL_up = HGL_dn \+ Hf = [\d.-]+ \+ [\d.-]+ = ([\d.-]+) ft/);
  assert(m, "HGL_up formula line not found in: " + JSON.stringify(text.slice(0, 400)));
  assert(text.includes("HGL_up = " + m[1] + " ft"),
    "HGL_up result line must repeat the derived value " + m[1]);
});

test("expanded +Hb row shows the EGL step across the structure", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
  window.renderAll();

  window.state.ui.expandedRowId = "A";
  window.renderAll();
  const text = document.getElementById("ledger").textContent.replace(/\s+/g, " ");

  // EGL_up = EGL_dn + Hb must appear with before + delta = after consistency.
  const m = text.match(/EGL_up = EGL_dn \+ Hb = ([\d.-]+) \+ ([\d.-]+) = ([\d.-]+) ft/);
  assert(m, "structure row must show EGL_up = EGL_dn + Hb, got: " + JSON.stringify(
    text.slice(text.indexOf("HGL step") - 400, text.indexOf("HGL step"))));
  // Each term is displayed at 3 decimals, so the sum can differ from the
  // displayed result by up to one rounding ulp.
  assert.ok(Math.abs(Number(m[1]) + Number(m[2]) - Number(m[3])) < 2e-3,
    "EGL step must be internally consistent: " + m[1] + " + " + m[2] + " != " + m[3]);
});

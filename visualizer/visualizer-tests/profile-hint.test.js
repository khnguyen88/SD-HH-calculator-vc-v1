// v82.2 regression: profile view right after import drew a single degenerate
// station (the walk anchors at the outfall only) with no explanation. The
// profile must show a "press ↑" hint until the walk contains at least one pipe.
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

const SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0, rim: 103, startElev: 100, crown: 99 },
    { id: "A", type: "bend", x: 0, y: -100, rim: 108, startElev: 102, crown: 101 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

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

function keydown(window, document, key) {
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
}

test("profile shows the walk hint until the walk contains a pipe", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.ui.view = "profile";
  window.renderAll();

  const svg = document.getElementById("viewSvg");
  assert(svg.textContent.includes("press"),
    "fresh-import profile must show the press-↑ hint, got: " + JSON.stringify(svg.textContent));

  keydown(window, document, "ArrowUp");
  assert.strictEqual(window.state.cursor.id, "P1");

  const textAfter = svg.textContent;
  assert(!textAfter.includes("press"), "hint must disappear once the walk has a pipe");
  const polys = Array.from(svg.children).filter((n) => n.tagName === "polyline");
  assert(polys.length > 0, "polylines drawn");
  const xs = new Set(polys[0].getAttribute("points").split(" ").map((pt) => pt.split(",")[0]));
  assert(xs.size >= 2, "profile spans pipe length; got points " + polys[0].getAttribute("points"));
});

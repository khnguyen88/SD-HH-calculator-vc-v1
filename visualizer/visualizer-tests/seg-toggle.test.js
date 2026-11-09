// Segmented ISO/profile view toggle: buttons switch directly (not flip),
// the active segment reflects state.ui.view, and the "v" hotkey still flips.
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

async function boot(window) {
  ensureFileText(window);
  const blob = new window.Blob([JSON.stringify(SEED)], { type: "application/json" });
  await window.importFromJsonFile(new window.File([blob], "seed.json", { type: "application/json" }));
  window.renderAll();
}

test("segmented view buttons switch directly and highlight the active view", async () => {
  const { window, document } = loadVisualizer();
  await boot(window);

  const iso = document.getElementById("viewSegIso");
  const profile = document.getElementById("viewSegProfile");
  assert(iso && profile, "segmented toggle buttons exist");

  assert.strictEqual(window.state.ui.view, "iso");
  assert(iso.classList.contains("active"), "ISO active initially");
  assert(!profile.classList.contains("active"), "profile inactive initially");

  profile.click();
  assert.strictEqual(window.state.ui.view, "profile");
  assert(profile.classList.contains("active"), "profile active after click");
  assert(!iso.classList.contains("active"));

  // Clicking the already-active segment must not flip away.
  profile.click();
  assert.strictEqual(window.state.ui.view, "profile", "re-clicking active segment is a no-op");

  iso.click();
  assert.strictEqual(window.state.ui.view, "iso");
  assert(iso.classList.contains("active"));

  // "v" hotkey still flips.
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "v", bubbles: true, cancelable: true }));
  assert.strictEqual(window.state.ui.view, "profile", "v hotkey flips iso -> profile");
});

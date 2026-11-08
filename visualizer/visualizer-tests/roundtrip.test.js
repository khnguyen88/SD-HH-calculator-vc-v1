// Task 36: import -> edit -> export -> re-import round-trip.
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
  outfall: { structureId: "OUT", tailwaterElev: 100 },
  drainageAreas: [
    { id: "DA-1", structureId: "A", areaAc: 1.5, C: 0.9, tc: 12 }
  ],
  tr55Segments: [
    { drainageAreaId: "DA-1", order: 1, type: "sheet", n: 0.24, L: 50, s: 0.01, P2: 3.2, surface: "lawn", area: 2000, wp: 40 }
  ]
};

// jsdom 24 does not implement Blob/File.prototype.text(); browsers do, and the
// importer relies on it. Polyfill the missing method (via FileReader) so the
// test exercises the real File + importer path instead of a bespoke stub.
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

// Build a File-like object in jsdom and feed it through the real importer.
async function bootWithJson(window, obj) {
  ensureFileText(window);
  const blob = new window.Blob([JSON.stringify(obj)], { type: "application/json" });
  const file = new window.File([blob], "seed.json", { type: "application/json" });
  await window.importFromJsonFile(file);
}

test("roundtrip: import preserves structure count and outfall", async () => {
  const { window } = loadVisualizer();
  await bootWithJson(window, SEED);
  assert.strictEqual(window.state.imported.structures.length, 2);
  assert.strictEqual(window.state.imported.pipes.length, 1);
  assert.strictEqual(window.state.imported.outfall.tailwaterElev, 100);
  assert.strictEqual(window.state.ui.mode, "explore");
});

test("roundtrip: tweaked export round-trips an override", async () => {
  const { window } = loadVisualizer();
  await bootWithJson(window, SEED);

  // Set an override via the API
  window.setOverride("P1", "slope", 0.006);
  assert.strictEqual(window.state.overrides.byId.P1.slope, 0.006);

  // Build tweaked export
  const tweaked = window.buildTweakedJsonExport();
  assert.strictEqual(tweaked.schemaVersion, 1);
  assert.strictEqual(tweaked.sourceApp, "storm-drain-hgl-visualizer");
  assert.strictEqual(tweaked._overrides.length, 1);
  assert.strictEqual(tweaked._overrides[0].elementId, "P1");
  assert.strictEqual(tweaked._overrides[0].field, "slope");
  assert.strictEqual(tweaked._overrides[0].originalValue, 0.005);
  assert.strictEqual(tweaked._overrides[0].newValue, 0.006);
  assert.strictEqual(
    tweaked.pipes.find((p) => p.id === "P1").slope,
    0.006,
    "override merged into pipe field"
  );
  // Normalize across the jsdom realm boundary so deepStrictEqual (which
  // compares prototypes) sees plain objects.
  const plain = (v) => JSON.parse(JSON.stringify(v));
  assert.deepStrictEqual(plain(tweaked.drainageAreas), SEED.drainageAreas);
  assert.deepStrictEqual(plain(tweaked.tr55Segments), SEED.tr55Segments);

  // Re-import the tweaked payload: override restored, baseline clean.
  await bootWithJson(window, tweaked);
  assert.deepStrictEqual(plain(window.state.imported.drainageAreas), SEED.drainageAreas);
  assert.deepStrictEqual(plain(window.state.imported.tr55Segments), SEED.tr55Segments);
  assert.strictEqual(window.state.ui.mode, "edit", "edit mode restored");
  assert.strictEqual(window.state.overrides.byId.P1.slope, 0.006, "override restored");
  assert.strictEqual(
    window.state.imported.pipes[0].slope,
    0.005,
    "imported value is the original"
  );
});

test("roundtrip: invalid JSON is rejected without mutating state.imported", async () => {
  const { window } = loadVisualizer();
  await bootWithJson(window, SEED);
  const before = window.state.imported;
  const beforeMode = window.state.ui.mode;

  const bad = Object.assign({}, SEED, { schemaVersion: 99 });
  await assert.rejects(
    () => bootWithJson(window, bad),
    /validation failed/,
    "bad schemaVersion should reject"
  );

  // The importer validates before touching state, so the prior import survives
  // byte-for-byte (same reference) and the UI mode is untouched.
  assert.strictEqual(window.state.imported, before, "state.imported not replaced");
  assert.strictEqual(window.state.imported.structures.length, 2);
  assert.strictEqual(window.state.ui.mode, beforeMode);
});

test("roundtrip: re-import resets a stale cursor and branch memory", async () => {
  const { window } = loadVisualizer();
  await bootWithJson(window, SEED);

  // Simulate a stale walk left over from prior interaction.
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.state.ui.branchChoices.byStructureId.X = {};

  await bootWithJson(window, SEED);

  assert.strictEqual(window.state.cursor.id, "OUT", "cursor reset to outfall");
  assert.strictEqual(
    Object.keys(window.state.ui.branchChoices.byStructureId).length,
    0,
    "branch memory cleared"
  );
});

test("roundtrip: kbTable is preserved through export+reimport", async () => {
  const { window } = loadVisualizer();
  const customKb = [
    { angleDeg: 0, inlet: 0.0, manhole: 0.0, bend: 0.0 },
    { angleDeg: 90, inlet: 0.9, manhole: 0.9, bend: 0.9 }
  ];
  await bootWithJson(window, Object.assign({}, SEED, { kbTable: customKb }));
  assert.strictEqual(window.state.imported.kbTable.length, 2);
  const tweaked = window.buildTweakedJsonExport();
  assert.strictEqual(tweaked.kbTable.length, 2);
});

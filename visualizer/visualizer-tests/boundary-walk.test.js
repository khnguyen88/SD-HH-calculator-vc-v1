/*
 * Hardening tests for the v81.3 walk-start feature:
 *  - boundary-EGL precedence per design §3.4 (outfall / fixed / crown / rim / zero),
 *    including a walk start whose structure record is missing but names the outfall;
 *  - resolveWalkStart fallback when ui.walkStartId is invalid or absent;
 *  - walk-from select changing the ledger start boundary;
 *  - profile TR-55 band reserved only when the current walk actually carries a card.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

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

async function boot(window, seed) {
  ensureFileText(window);
  const blob = new window.Blob([JSON.stringify(seed)], { type: "application/json" });
  const file = new window.File([blob], "seed.json", { type: "application/json" });
  await window.importFromJsonFile(file);
}

// Build a single start row from a hermetic imported object (no full import needed).
function startRow(window, imported, walkStartId) {
  const resolved = {
    imported,
    overrides: { byId: {} },
    ui: { walkStartId },
    analysis: null
  };
  const rows = window.buildLedger([walkStartId], resolved, null, "hec22");
  return rows[0];
}

// --- boundary precedence (design §3.4) --------------------------------------

test("boundary: outfall start uses tailwaterElev", () => {
  const { window } = loadVisualizer();
  const row = startRow(window, {
    structures: [{ id: "OUT", type: "outfall" }],
    pipes: [],
    outfall: { structureId: "OUT", tailwaterElev: 99 }
  }, "OUT");
  assert.strictEqual(row.after, 99);
  assert.strictEqual(row.detail.boundaryReason, "tailwater");
});

test("boundary: forceElev + startElev wins as a fixed elevation", () => {
  const { window } = loadVisualizer();
  const row = startRow(window, {
    structures: [{ id: "A", type: "manhole", forceElev: true, startElev: 102, crown: 101, rim: 108 }],
    pipes: [],
    outfall: null
  }, "A");
  assert.strictEqual(row.after, 102);
  assert.strictEqual(row.detail.boundaryReason, "fixed elevation");
});

test("boundary: crown then rim then zero when higher fields are absent", () => {
  const { window } = loadVisualizer();
  const crown = startRow(window, {
    structures: [{ id: "A", type: "manhole", crown: 101, rim: 108 }],
    pipes: [], outfall: null
  }, "A");
  assert.strictEqual(crown.after, 101);
  assert.strictEqual(crown.detail.boundaryReason, "crown boundary");

  const rim = startRow(window, {
    structures: [{ id: "A", type: "manhole", rim: 108 }],
    pipes: [], outfall: null
  }, "A");
  assert.strictEqual(rim.after, 108);
  assert.strictEqual(rim.detail.boundaryReason, "rim boundary");

  const zero = startRow(window, {
    structures: [{ id: "A", type: "manhole" }],
    pipes: [], outfall: null
  }, "A");
  assert.strictEqual(zero.after, 0);
  assert.strictEqual(zero.detail.boundaryReason, "zero boundary");
});

test("boundary: missing start record that names the outfall falls back to tailwater, not zero", () => {
  const { window } = loadVisualizer();
  const row = startRow(window, {
    structures: [],                       // OUT record absent from the payload
    pipes: [],
    outfall: { structureId: "OUT", tailwaterElev: 97.5 }
  }, "OUT");
  assert.strictEqual(row.after, 97.5);
  assert.strictEqual(row.detail.boundaryReason, "tailwater");
});

// --- resolveWalkStart fallback ----------------------------------------------

test("resolveWalkStart: valid id wins; invalid id falls back to outfall; none → null", () => {
  const { window } = loadVisualizer();
  const imp = {
    structures: [{ id: "A", type: "manhole" }],
    pipes: [],
    outfall: { structureId: "OUT", tailwaterElev: 100 }
  };
  assert.strictEqual(window.resolveWalkStart(imp, { walkStartId: "A" }), "A", "valid id used");
  assert.strictEqual(window.resolveWalkStart(imp, { walkStartId: "GHOST" }), "OUT", "invalid id → outfall");
  assert.strictEqual(window.resolveWalkStart(imp, {}), "OUT", "absent id → outfall");
  assert.strictEqual(window.resolveWalkStart({ structures: [], outfall: null }, { walkStartId: "GHOST" }), null,
    "no outfall and invalid id → null");
});

// --- walk-from select drives the ledger start -------------------------------

test("walk-from select: choosing a structure changes the ledger start boundary", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, {
    schemaVersion: 1, sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall", x: 0, y:    0, rim: 103, startElev: 100, crown: 99 },
      { id: "A",   type: "manhole", x: 0, y: -100, rim: 108, startElev: 102, crown: 101 }
    ],
    pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
              n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 }],
    outfall: { structureId: "OUT", tailwaterElev: 100 }
  });
  window.renderAll();

  // Default walk start is the outfall → tailwater boundary.
  const defRows = window.buildLedger(window.state.cursor.pathStack, window.state,
                                     window.state.imported.kbTable, window.state.ui.hglMethod);
  assert.strictEqual(defRows[0].detail.boundaryReason, "tailwater", "default start is the outfall");

  const sel = document.getElementById("walkFromSelect");
  sel.value = "A";
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));

  assert.strictEqual(window.state.ui.walkStartId, "A", "walk start changed");
  assert.deepStrictEqual(Array.from(window.state.cursor.pathStack), ["A"], "cursor reset to the new start");

  const rows = window.buildLedger(window.state.cursor.pathStack, window.state,
                                  window.state.imported.kbTable, window.state.ui.hglMethod);
  assert.strictEqual(rows[0].after, 101, "start EGL is A's crown");
  assert.strictEqual(rows[0].detail.boundaryReason, "crown boundary", "boundary follows the chosen start");
});

// --- profile TR-55 band gating ----------------------------------------------

test("profile: TR-55 band reserved only when the current walk carries a card", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, {
    schemaVersion: 1, sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall", x: 0, y:    0, rim: 103, startElev: 100, crown: 99 },
      { id: "A",   type: "inlet",   x: 0, y: -100, rim: 108, startElev: 102, crown: 101 }
    ],
    pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
              n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 }],
    outfall: { structureId: "OUT", tailwaterElev: 100 },
    drainageAreas: [{ id: "DA-1", structureId: "A", areaAc: 1.5, C: 0.9, tc: 12 }],
    tr55Segments: [{ drainageAreaId: "DA-1", order: 1, type: "sheet", n: 0.24, L: 50, s: 0.01,
                     P2: 3.2, surface: "lawn", area: 2000, wp: 40 }]
  });

  const svg = document.getElementById("viewSvg");
  window.state.ui.view = "profile";
  window.state.ui.showTr55 = true;

  // Walk reaches A → band reserved (H = 300 + 96) and a card renders.
  window.state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
  window.renderActiveView();
  assert.strictEqual(svg.getAttribute("viewBox"), "0 0 800 396", "card band reserved on-path");
  assert.ok(document.querySelectorAll('[data-kind="tr55-card"]').length >= 1, "card rendered on-path");

  // Walk stops at the outfall → no card, band not reserved (H = 300).
  window.state.cursor = { kind: "structure", id: "OUT", pathStack: ["OUT"] };
  window.renderActiveView();
  assert.strictEqual(svg.getAttribute("viewBox"), "0 0 800 300", "no band reserved off-path");
  assert.strictEqual(document.querySelectorAll('[data-kind="tr55-card"]').length, 0, "no card off-path");
});

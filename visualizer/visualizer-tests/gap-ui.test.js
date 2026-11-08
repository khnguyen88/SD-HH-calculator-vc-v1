/*
 * DOM-level tests for the v81.2–v81.8 gap features: warning banner, walk-from
 * select, profile TR-55 cards, iso flow arrows, selection glow, and print mode.
 *
 * Importing a JSON seed does NOT render (the file-input change handler is what
 * normally calls renderAll), so each test imports via importFromJsonFile and
 * then invokes renderAll/renderActiveView explicitly.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

// jsdom 24 lacks File.prototype.text(); polyfill via FileReader (same as roundtrip.test.js).
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

// --- shared seeds -----------------------------------------------------------

// Splitter S with two outgoing pipes; P2 has no Design Q → both warnings fire.
const WARN_SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x:   0, y:    0, rim: 103, startElev: 100, crown: 99 },
    { id: "S",   type: "splitter", x:  0, y: -100, rim: 107, startElev: 104, crown: 103 },
    { id: "B",   type: "outfall", x:  80, y: -100, rim: 101, startElev:  98, crown: 97 }
  ],
  pipes: [
    { id: "P1", fromId: "S", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 },
    { id: "P2", fromId: "S", toId: "B", shape: "circular", size: 15,
      n: 0.013, slope: 0.005, length: 80, angle: 45, designQ: null }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

// Clean network: one pipe, no splitter, no missing Design Q → no warnings.
const CLEAN_SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x:  0, y: 0, rim: 103, startElev: 100, crown: 99 },
    { id: "A",   type: "manhole", x:  0, y: -100, rim: 108, startElev: 102, crown: 101 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

// One structure ("A") carries a drainage area + TR-55 segment.
const TR55_SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x: 0, y:    0, rim: 103, startElev: 100, crown: 99 },
    { id: "A",   type: "inlet",   x: 0, y: -100, rim: 108, startElev: 102, crown: 101 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 },
  drainageAreas: [
    { id: "DA-1", structureId: "A", areaAc: 1.5, C: 0.9, tc: 12 }
  ],
  tr55Segments: [
    { drainageAreaId: "DA-1", order: 1, type: "sheet", n: 0.24, L: 50, s: 0.01,
      P2: 3.2, surface: "lawn", area: 2000, wp: 40 }
  ]
};

// Two well-separated pipes plus one degenerate pipe (D1 and D2 share x/y and rim,
// so their endpoints collide when projected and no flow arrow is drawn for it).
const ISO_SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x:   0, y:    0, rim: 100 },
    { id: "A",   type: "manhole", x:   0, y: -100, rim: 101 },
    { id: "B",   type: "bend",    x:  60, y: -100, rim: 102 },
    { id: "D1",  type: "manhole", x: 200, y:  200, rim:  90 },
    { id: "D2",  type: "manhole", x: 200, y:  200, rim:  90 }
  ],
  pipes: [
    { id: "P1", fromId: "A",  toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.5 },
    { id: "P2", fromId: "B",  toId: "A",   shape: "circular", size: 15,
      n: 0.013, slope: 0.005, length:  80, angle: 45, designQ: 4 },
    { id: "PD", fromId: "D1", toId: "D2",  shape: "circular", size: 15,
      n: 0.013, slope: 0.005, length:  10, angle: 0, designQ: 1 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

// --- warning banner ---------------------------------------------------------

test("warning banner: shows splitter + missing-Q warnings, dismisses, resets on re-import", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, WARN_SEED);
  window.renderAll();

  const banner = document.getElementById("warningBanner");
  assert.ok(banner, "#warningBanner exists");
  assert.strictEqual(banner.style.display, "block", "banner visible with warnings");
  assert.ok(banner.textContent.includes("Flow splitter"), "splitter warning shown");
  assert.ok(banner.textContent.includes("No Design Q"), "missing Design Q warning shown");

  const dismiss = banner.querySelector('button[aria-label="Dismiss"]');
  assert.ok(dismiss, "dismiss button rendered");
  dismiss.click();
  assert.strictEqual(banner.style.display, "none", "banner hidden after dismiss");

  // Re-import a clean network: warnings stay gone and the dismissal flag resets.
  await boot(window, CLEAN_SEED);
  window.renderAll();
  assert.strictEqual(banner.style.display, "none", "clean network has no warnings");
  assert.strictEqual(window.state.ui.warningsDismissed, false, "dismissal reset on import");
});

// --- walk-from select -------------------------------------------------------

test("walk-from select: outfalls group first; change updates walk start, cursor, branches", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, WARN_SEED);
  window.renderAll();

  const sel = document.getElementById("walkFromSelect");
  assert.ok(sel, "#walkFromSelect exists");

  const groupLabels = Array.from(sel.querySelectorAll("optgroup")).map((g) => g.label);
  assert.deepStrictEqual(groupLabels, ["Outfalls", "Structures"], "Outfalls group precedes Structures");

  sel.value = "S";
  sel.dispatchEvent(new window.Event("change", { bubbles: true }));

  assert.strictEqual(window.state.ui.walkStartId, "S", "walkStartId updated");
  assert.strictEqual(window.state.cursor.id, "S", "cursor moved to chosen structure");
  assert.strictEqual(
    Object.keys(window.state.ui.branchChoices.byStructureId).length,
    0,
    "branch choices cleared for the new walk"
  );
});

// --- profile TR-55 cards ----------------------------------------------------

test("profile TR-55 cards: render for linked structure, disappear when toggled off", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, TR55_SEED);

  window.state.ui.view = "profile";
  window.state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
  window.state.ui.showTr55 = true;
  window.renderActiveView();

  const cards = document.querySelectorAll('[data-kind="tr55-card"]');
  assert.ok(cards.length >= 1, "at least one TR-55 card rendered");
  const ids = Array.from(cards).map((c) => c.getAttribute("data-id"));
  assert.ok(ids.includes("A"), "card for structure A rendered");

  window.toggleTr55();
  assert.strictEqual(document.querySelectorAll('[data-kind="tr55-card"]').length, 0,
    "cards removed when TR-55 toggled off");
});

// --- iso flow arrows --------------------------------------------------------

test("iso flow arrows: one per non-degenerate pipe only", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, ISO_SEED);

  window.state.ui.view = "iso";
  window.renderActiveView();

  const arrows = document.querySelectorAll('[data-kind="flow-arrow"]');
  assert.strictEqual(arrows.length, 2, "degenerate pipe draws no flow arrow");
  const arrowIds = Array.from(arrows).map((a) => a.getAttribute("data-id")).sort();
  assert.deepStrictEqual(arrowIds, ["P1", "P2"], "arrows only for distinct-endpoint pipes");
});

// --- selection glow ---------------------------------------------------------

test("selection glow: iso pipe selection adds drop-shadow; unselected pipe is plain", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, ISO_SEED);

  window.state.ui.view = "iso";
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.renderActiveView();

  const p1 = document.querySelector('#viewSvg line[data-kind="pipe"][data-id="P1"]');
  const p2 = document.querySelector('#viewSvg line[data-kind="pipe"][data-id="P2"]');
  assert.ok(p1 && p2, "both pipe lines exist");
  assert.ok((p1.getAttribute("style") || "").includes("drop-shadow"), "selected pipe glows");
  assert.strictEqual(p1.getAttribute("stroke"), "#ffd60a", "selected pipe is yellow");
  assert.strictEqual(p2.getAttribute("style"), null, "unselected pipe has no inline style");

  window.state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
  window.renderActiveView();

  const selStruct = document.querySelector('#viewSvg g[data-kind="structure"][data-id="A"]');
  const otherStruct = document.querySelector('#viewSvg g[data-kind="structure"][data-id="OUT"]');
  assert.ok(selStruct && otherStruct, "both structure groups exist");
  assert.ok((selStruct.getAttribute("style") || "").includes("drop-shadow"), "selected structure glows");
  assert.strictEqual(otherStruct.getAttribute("style"), null, "unselected structure has no inline style");
});

// --- print mode -------------------------------------------------------------

test("print: builds print area with one calc-sheet per annotated row, enters print mode", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, CLEAN_SEED);

  const path = ["OUT", "P1", "A"];
  window.state.ui.walkStartId = "OUT";
  window.state.cursor = { kind: "structure", id: "A", pathStack: path.slice() };

  const rows = window.buildLedger(path, window.state, window.state.imported.kbTable, window.state.ui.hglMethod);
  const annotated = window.annotateLedgerHgl(rows, window.state, window.state.ui.hglMethod);

  let printed = 0;
  window.print = () => { printed++; };
  window.printLedger();

  const area = document.getElementById("printArea");
  assert.ok(area, "#printArea created for a loaded network");
  assert.strictEqual(area.querySelectorAll(".calc-sheet").length, annotated.length,
    "one calc-sheet per annotated ledger row (start + hf + hb + end)");
  assert.ok(document.body.classList.contains("print-mode"), "body enters print mode");
  assert.strictEqual(printed, 1, "window.print called once");
});

test("print: with no import, printLedger creates no print area and never calls print", () => {
  const { window, document } = loadVisualizer();

  let printed = 0;
  window.print = () => { printed++; };
  window.printLedger();

  assert.strictEqual(document.getElementById("printArea"), null, "no print area without a network");
  assert.strictEqual(printed, 0, "window.print not called without a network");
});

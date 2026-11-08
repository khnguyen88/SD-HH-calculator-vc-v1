// Task 43 follow-up: ledger expand/collapse (click-to-collapse, lock-open,
// auto-follow on cursor move, Enter toggle).
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

function ledgerChildren(document) {
  const host = document.getElementById("ledger");
  return host ? Array.from(host.children) : [];
}

// Expanded detail divs are direct #ledger children carrying the detail padding.
function detailCount(window, document) {
  return ledgerChildren(document)
    .filter((n) => (n.getAttribute("style") || "").includes("4px 20px")).length;
}

// Interactive (clickable) ledger rows — the end row omits cursor:pointer.
function pointerRows(document) {
  return ledgerChildren(document)
    .filter((n) => (n.getAttribute("style") || "").includes("cursor:pointer"));
}

function highlightedRow(document) {
  return pointerRows(document)
    .find((n) => (n.getAttribute("style") || "").includes("ffeaa7")) || null;
}

function rowContaining(document, text) {
  return pointerRows(document).find((n) => n.textContent.includes(text)) || null;
}

function pressEnter(window) {
  window.document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true })
  );
}

function setCursorP1(window) {
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
}

test("Enter toggles the current row: 1 -> 0 -> 1", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  setCursorP1(window);
  window.renderAll();
  assert.strictEqual(detailCount(window, document), 1, "current row expanded on load");

  pressEnter(window);
  window.renderAll();
  assert.strictEqual(detailCount(window, document), 0, "Enter collapses");

  pressEnter(window);
  window.renderAll();
  assert.strictEqual(detailCount(window, document), 1, "Enter re-expands");
});

test("Clicking the current (shown-expanded) row collapses it", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  setCursorP1(window);
  window.renderAll();
  assert.strictEqual(detailCount(window, document), 1);

  const current = highlightedRow(document);
  assert.ok(current, "a highlighted/current row exists");
  current.click();
  window.renderAll();

  assert.strictEqual(detailCount(window, document), 0);
  assert.strictEqual(window.state.ui.expandedRowId, "(collapsed)");
});

test("Clicking another row locks it open (one expanded)", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  setCursorP1(window);
  window.renderAll();

  const startRow = rowContaining(document, "Start:");
  assert.ok(startRow, "a Start: row exists");
  startRow.click();
  window.renderAll();

  assert.strictEqual(window.state.ui.expandedRowId, "OUT");
  assert.strictEqual(detailCount(window, document), 1);
});

test("Moving the cursor resumes auto-follow", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);

  // Import leaves the cursor on the outfall. Render once so lastCursorId == "OUT",
  // then simulate the OUT row being locked open (the outcome of clicking it).
  // NOTE: auto-follow fires only on a *genuine* cursor id change, so the cursor
  // must start somewhere other than P1 before we move it to P1 below.
  assert.strictEqual(window.state.cursor.id, "OUT");
  window.renderAll();
  window.state.ui.expandedRowId = "OUT";
  window.renderAll();
  assert.strictEqual(window.state.ui.expandedRowId, "OUT", "OUT row locked open");

  // Move the cursor: auto-follow must clear the manual lock and re-expand P1.
  setCursorP1(window);
  window.renderAll();

  assert.strictEqual(window.state.ui.expandedRowId, null);
  assert.strictEqual(detailCount(window, document), 1);
});

test("Enter while an input is focused does not toggle", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  setCursorP1(window);
  window.renderAll();
  assert.strictEqual(detailCount(window, document), 1);

  const input = document.createElement("input");
  document.body.appendChild(input);
  input.focus();

  input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  window.renderAll();

  assert.strictEqual(detailCount(window, document), 1, "count unchanged while typing");
});

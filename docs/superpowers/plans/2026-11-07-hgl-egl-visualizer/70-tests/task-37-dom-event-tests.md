# Task 37: DOM event tests + focus-preservation audit

## Context

Dispatch real `keydown` and `input` events, assert state changes. Also audit the dev file for `oninput`/`onchange` handlers that call a render function without going through `withFocusPreserved`. Implements spec §8.4 and §8.5.

## Preconditions

- Prior tasks: task-19, task-20, task-24, task-31.

## Exact changes

**Create** `drainage-calculator/visualizer-tests/dom-events.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { loadVisualizer, DEV_HTML_PATH } = require("./_harness");

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

async function bootWithJson(window, obj) {
  const blob = new window.Blob([JSON.stringify(obj)]);
  const file = new window.File([blob], "seed.json");
  await window.importFromJsonFile(file);
  if (typeof window.autoLayoutIfNeeded === "function") window.autoLayoutIfNeeded();
  window.renderAll();
}

test("ArrowUp at outfall advances cursor onto P1 and ledger grows by one row", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = window.initialCursor(window.state.imported);
  assert.strictEqual(window.state.cursor.id, "OUT");

  const ev = new window.KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true });
  document.dispatchEvent(ev);
  assert.strictEqual(window.state.cursor.id, "P1");
  assert.strictEqual(window.state.cursor.pathStack.length, 2);
});

test("At 2-inflow junction, ArrowUp opens branch popup; Enter advances", async () => {
  const { window, document } = loadVisualizer();
  const seed2 = Object.assign({}, SEED, {
    structures: SEED.structures.concat([{ id: "B", type: "manhole", x: 60, y: -100, rim: 108, startElev: 102, crown: 101 }]),
    pipes: SEED.pipes.concat([{ id: "P2", fromId: "B", toId: "OUT", shape: "circular",
      size: 18, n: 0.013, slope: 0.005, length: 100, angle: 45, designQ: 4 }])
  });
  await bootWithJson(window, seed2);
  window.state.cursor = window.initialCursor(window.state.imported);

  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
  assert.ok(document.getElementById("branchPopup"), "popup should open");
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  assert.strictEqual(document.getElementById("branchPopup"), null, "popup closed");
  assert.ok(["P1", "P2"].includes(window.state.cursor.id), "cursor advanced onto one of the pipes");
});

test("Edit mode input: slope change updates state.overrides via withFocusPreserved", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.setMode("edit");
  window.renderAll();

  const input = document.querySelector('input[data-focus-key="edit:P1:slope"]');
  assert.ok(input, "editable slope input present");
  input.focus();
  input.value = "0.007";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  assert.strictEqual(window.state.overrides.byId.P1.slope, 0.007, "override recorded");

  // Focus is preserved on the same input after re-render
  assert.strictEqual(document.activeElement.dataset.focusKey, "edit:P1:slope", "focus preserved");
});

test("V hotkey toggles view (not when typing in a field)", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  assert.strictEqual(window.state.ui.view, "iso");
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "v", bubbles: true }));
  assert.strictEqual(window.state.ui.view, "profile");

  // V while an input is focused should NOT toggle
  window.state.ui.view = "iso";
  const input = document.createElement("input"); input.type = "text";
  document.body.appendChild(input); input.focus();
  input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "v", bubbles: true }));
  assert.strictEqual(window.state.ui.view, "iso", "V in focused input must not toggle");
  document.body.removeChild(input);
});

test("audit: every oninput/onchange that calls a render routes through withFocusPreserved", () => {
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");
  // Find all occurrences of `oninput:` and `onchange:` and check the following 200 chars
  // contain either `withFocusPreserved` OR do NOT contain `renderAll(`/`renderLedger(`/`renderActiveView(`.
  const patterns = [/oninput\s*:\s*\([^)]*\)\s*=>\s*\{[^}]*\}/g,
                    /onchange\s*:\s*\([^)]*\)\s*=>\s*\{[^}]*\}/g];
  const violations = [];
  for (const p of patterns) {
    let m;
    while ((m = p.exec(html)) !== null) {
      const body = m[0];
      const callsRender = /\brender(All|Ledger|ActiveView)\(/.test(body);
      const safe = /\bwithFocusPreserved\s*\(/.test(body);
      if (callsRender && !safe) violations.push(body.slice(0, 120));
    }
  }
  assert.strictEqual(violations.length, 0,
    "unguarded render-triggering handlers:\n" + violations.join("\n"));
});
```

## Acceptance test

```powershell
node --test drainage-calculator/visualizer-tests/dom-events.test.js
```

Expected: `pass 5 / fail 0`.

## Done when

- File `dom-events.test.js` exists with 5 tests.
- All 5 pass.
- The focus-preservation audit passes — no violations.
- Commit: `test(visualizer): task-37 DOM events and focus audit`.

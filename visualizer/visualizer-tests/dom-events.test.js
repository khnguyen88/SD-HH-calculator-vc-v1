// Task 37: DOM event tests (cursor walk, branch popup, edit inputs, V hotkey)
// plus a focus-preservation audit of every render-triggering oninput/onchange.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
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

// jsdom 24 does not implement Blob/File.prototype.text(); the importer relies on
// it. Polyfill via FileReader (same helper as roundtrip.test.js).
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

// jsdom 24 does not expose CSS.escape either; withFocusPreserved uses it to
// re-find the focused field after a re-render. A conservative ident escape is
// enough for the `edit:<id>:<field>` keys used by the app.
function ensureCssEscape(window) {
  if (!window.CSS) window.CSS = {};
  if (typeof window.CSS.escape !== "function") {
    window.CSS.escape = (value) => String(value).replace(/[^a-zA-Z0-9_-]/g, (c) => "\\" + c);
  }
}

async function bootWithJson(window, obj) {
  ensureFileText(window);
  ensureCssEscape(window);
  const blob = new window.Blob([JSON.stringify(obj)], { type: "application/json" });
  const file = new window.File([blob], "seed.json", { type: "application/json" });
  await window.importFromJsonFile(file);
  if (typeof window.autoLayoutIfNeeded === "function") window.autoLayoutIfNeeded();
  window.renderAll();
}

function keydown(window, document, key, target) {
  const ev = new window.KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  (target || document).dispatchEvent(ev);
}

test("ArrowUp at outfall advances cursor onto P1 and pathStack grows", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = window.initialCursor(window.state.imported);
  assert.strictEqual(window.state.cursor.id, "OUT");

  keydown(window, document, "ArrowUp");
  assert.strictEqual(window.state.cursor.id, "P1");
  assert.strictEqual(window.state.cursor.pathStack.length, 2);
});

test("At 2-inflow junction, ArrowUp opens branch popup; Enter advances", async () => {
  const { window, document } = loadVisualizer();
  const seed2 = Object.assign({}, SEED, {
    structures: SEED.structures.concat([
      { id: "B", type: "manhole", x: 60, y: -100, rim: 108, startElev: 102, crown: 101 }
    ]),
    pipes: SEED.pipes.concat([
      { id: "P2", fromId: "B", toId: "OUT", shape: "circular",
        size: 18, n: 0.013, slope: 0.005, length: 100, angle: 45, designQ: 4 }
    ])
  });
  await bootWithJson(window, seed2);
  window.state.cursor = window.initialCursor(window.state.imported);
  assert.strictEqual(window.state.cursor.id, "OUT");

  keydown(window, document, "ArrowUp");
  assert.ok(document.getElementById("branchPopup"), "popup should open");
  keydown(window, document, "Enter");
  assert.strictEqual(document.getElementById("branchPopup"), null, "popup closed");
  assert.ok(["P1", "P2"].includes(window.state.cursor.id), "cursor advanced onto one of the pipes");
  assert.strictEqual(window.state.cursor.pathStack.length, 2);
});

test("Edit mode input: slope change updates overrides and preserves focus", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.setMode("edit");
  window.renderAll();

  const input = document.querySelector('input[data-focus-key="edit:P1:slope"]');
  assert.ok(input, "editable slope input present");
  input.focus();
  assert.strictEqual(document.activeElement, input);
  input.value = "0.007";
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  assert.strictEqual(window.state.overrides.byId.P1.slope, 0.007, "override recorded");

  // Focus is preserved on the same input after the re-render.
  assert.strictEqual(document.activeElement.dataset.focusKey, "edit:P1:slope", "focus preserved");
});

test("V hotkey toggles view (not when typing in a field)", async () => {
  const { window, document } = loadVisualizer();
  await bootWithJson(window, SEED);
  assert.strictEqual(window.state.ui.view, "iso");

  keydown(window, document, "v");
  assert.strictEqual(window.state.ui.view, "profile");

  // V while a real focused input owns the keystroke must NOT toggle.
  window.state.ui.view = "iso";
  const input = document.createElement("input");
  input.type = "text";
  document.body.appendChild(input);
  input.focus();
  keydown(window, document, "v", input);
  assert.strictEqual(window.state.ui.view, "iso", "V in focused input must not toggle");
  document.body.removeChild(input);
});

// --- Focus-preservation audit -------------------------------------------------
// Return the full body of every `name:` handler (oninput/onchange), with balanced
// brace matching so we do not truncate at the first nested `}`.
function handlerBodies(html, name) {
  const out = [];
  const re = new RegExp(name + "\\s*:", "g");
  let m;
  while ((m = re.exec(html)) !== null) {
    const arrow = html.indexOf("=>", m.index + m[0].length);
    if (arrow === -1) continue;
    let i = arrow + 2;
    while (i < html.length && /\s/.test(html[i])) i++;
    if (html[i] === "{") {
      let depth = 1;
      const start = ++i;
      while (i < html.length && depth > 0) {
        const ch = html[i];
        if (ch === "{") depth++;
        else if (ch === "}") depth--;
        i++;
      }
      out.push(html.slice(start, i - 1));
    } else {
      const start = i;
      let depth = 0;
      while (i < html.length) {
        const ch = html[i];
        if (ch === "(" || ch === "[" || ch === "{") depth++;
        else if (ch === ")" || ch === "]" || ch === "}") {
          if (depth === 0) break;
          depth--;
        } else if ((ch === "," || ch === "\n") && depth === 0) break;
        i++;
      }
      out.push(html.slice(start, i));
    }
  }
  return out;
}

test("audit: every oninput/onchange that calls a render routes through withFocusPreserved", () => {
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");
  const bodies = handlerBodies(html, "oninput").concat(handlerBodies(html, "onchange"));
  assert.ok(bodies.length >= 2, "scanner should find the editable field handlers");

  const violations = [];
  for (const body of bodies) {
    const callsRender = /\brender(All|Ledger|ActiveView)\s*\(/.test(body);
    const safe = /\bwithFocusPreserved\s*\(/.test(body);
    if (callsRender && !safe) violations.push(body.trim().slice(0, 160));
  }
  assert.strictEqual(violations.length, 0,
    "unguarded render-triggering handlers:\n" + violations.join("\n---\n"));
});

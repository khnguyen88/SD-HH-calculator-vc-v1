# Task 24: Editable ledger field inputs + E hotkey

## Context

In edit mode, the expanded ledger row shows editable inputs for its row kind. Every input goes through `withFocusPreserved(renderAll)` so typing doesn't lose focus mid-render. E hotkey toggles mode. Implements spec §6.1.

## Preconditions

- Prior tasks: task-01, task-03, task-12, task-23, task-27 (expanded-row helpers from group 60 — if group 60 isn't done yet, this task provides minimal inputs anyway and group 60 refines).

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `edit-mode` sentinel block after task-23:

```js
  // --- Editable field helpers (task-24) ---

  // A monospace numeric input bound to an override. Uses data-focus-key per main spec §A.2.
  function editableNumber(elementId, field, imported, overrides, opts) {
    opts = opts || {};
    const currentVal = resolveField(elementId, field, imported, overrides);
    const originalEl = (imported.structures.find((s) => s.id === elementId)
                     || imported.pipes.find((p) => p.id === elementId));
    const original = originalEl ? originalEl[field] : null;
    const isOverridden = overrides.byId[elementId] && Object.prototype.hasOwnProperty.call(overrides.byId[elementId], field);

    // text + inputmode rather than type=number: a number input reports "" for
    // in-progress text like "0." so decimals cannot be typed reliably.
    const input = el("input", {
      type: "text",
      inputmode: "decimal",
      value: currentVal != null ? currentVal : "",
      placeholder: original != null ? String(original) : "",
      style: "width:90px; font-family:ui-monospace,monospace; "
           + (isOverridden ? "font-weight:bold; color:#ffd60a;" : "color:#1a1a1a;"),
      "data-focus-key": "edit:" + elementId + ":" + field,
      oninput: (ev) => {
        const raw = ev.target.value;
        if (raw.trim() === "") { revertOverride(elementId, field); withFocusPreserved(renderAll); return; }
        const n = Number(raw);
        if (!isFinite(n)) return; // partial ("-", "1e", ".") — keep the text, store nothing
        const cur = resolveField(elementId, field, imported, overrides);
        if (cur === n) return;    // no semantic change yet; preserves "0.0" / "1.50"
        setOverride(elementId, field, n);
        withFocusPreserved(renderAll);
      }
    });
    return input;
  }

  function editableSelect(elementId, field, imported, overrides, options) {
    const currentVal = resolveField(elementId, field, imported, overrides);
    const originalEl = (imported.structures.find((s) => s.id === elementId)
                     || imported.pipes.find((p) => p.id === elementId));
    const original = originalEl ? originalEl[field] : null;
    const isOverridden = overrides.byId[elementId] && Object.prototype.hasOwnProperty.call(overrides.byId[elementId], field);
    const sel = el("select", {
      style: "font-family:ui-monospace,monospace; " + (isOverridden ? "font-weight:bold; color:#ffd60a;" : ""),
      "data-focus-key": "edit:" + elementId + ":" + field,
      onchange: (ev) => {
        const v = ev.target.value;
        // Picking the original value is a revert, not an override.
        if (original != null && String(v) === String(original)) revertOverride(elementId, field);
        else setOverride(elementId, field, v);
        withFocusPreserved(renderAll);
      }
    });
    for (const opt of options) {
      const o = el("option", { value: opt, selected: (String(opt) === String(currentVal)) ? "selected" : null }, opt);
      sel.appendChild(o);
    }
    return sel;
  }

  // E hotkey
  document.addEventListener("keydown", (ev) => {
    if (isTypingTarget(ev)) return;
    if (ev.shiftKey) return;
    if (isBranchPopupOpen()) return;
    if (document.getElementById("overridePanel")) return;
    if (ev.key === "e" || ev.key === "E") {
      ev.preventDefault();
      setMode(state.ui.mode === "edit" ? "explore" : "edit");
    }
  });

  // Toolbar button
  const modeBtn = document.getElementById("modeToggle");
  if (modeBtn) modeBtn.addEventListener("click", () => setMode(state.ui.mode === "edit" ? "explore" : "edit"));
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [{ id: "A", type: "bend" }, { id: "OUT", type: "outfall" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 30, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };

// E hotkey toggles mode
state.ui.mode = "explore";
document.dispatchEvent(new KeyboardEvent("keydown", { key: "e", bubbles: true }));
console.assert(state.ui.mode === "edit", "E to edit");
document.dispatchEvent(new KeyboardEvent("keydown", { key: "E", bubbles: true }));
console.assert(state.ui.mode === "explore", "E to explore");

// editableNumber builds a bound input
const inp = editableNumber("P1", "slope", state.imported, state.overrides);
console.assert(inp.tagName === "INPUT" && inp.getAttribute("inputmode") === "decimal", "input built");
console.assert(inp.value === "0.005", "imported value shown");
console.assert(inp.dataset.focusKey === "edit:P1:slope", "focus key set");

// Simulate user typing a new value
inp.value = "0.009";
inp.dispatchEvent(new Event("input", { bubbles: true }));
console.assert(state.overrides.byId.P1.slope === 0.009, "override recorded on input");

// Decimal entry: in-progress text parses without clobbering the field.
inp.value = "0.";
inp.dispatchEvent(new Event("input", { bubbles: true }));
console.assert(state.overrides.byId.P1.slope === 0, "trailing-dot commits its numeric value");
inp.value = "0.0085";
inp.dispatchEvent(new Event("input", { bubbles: true }));
console.assert(state.overrides.byId.P1.slope === 0.0085, "decimal override recorded");

// Clearing the input reverts
inp.value = "";
inp.dispatchEvent(new Event("input", { bubbles: true }));
console.assert(!state.overrides.byId.P1 || state.overrides.byId.P1.slope === undefined, "clearing reverts");

// Select bound
const sel = editableSelect("A", "type", state.imported, state.overrides, ["inlet", "manhole", "bend", "junction"]);
console.assert(sel.tagName === "SELECT", "select built");
sel.value = "manhole";
sel.dispatchEvent(new Event("change", { bubbles: true }));
console.assert(state.overrides.byId.A.type === "manhole", "select override recorded");

console.log("task-24 editable fields: OK");
```

## Done when

- `editableNumber`, `editableSelect`, E hotkey, mode-toggle button all defined.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-24 editable ledger fields and E hotkey`.

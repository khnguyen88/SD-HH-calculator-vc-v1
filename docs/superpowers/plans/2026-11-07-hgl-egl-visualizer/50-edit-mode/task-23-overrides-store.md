# Task 23: Overrides store (set/revert/reset/resolve)

## Context

Centralize the overrides API used by task-24 (editable inputs) and task-25 (reset UI). `resolveField` already exists (task-12); this task adds setters and reset helpers. Implements spec §6.1.

## Preconditions

- Prior tasks: task-01, task-03, task-12.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Insert inside the `edit-mode` sentinel block, immediately after the `begin` line:

```js
  // --- Overrides store (task-23) ---

  // Reject prototype-polluting / malformed keys before they reach the store.
  function isSafeOverrideKey(k) {
    return typeof k === "string" && k !== "" && k !== "__proto__" && k !== "constructor" && k !== "prototype";
  }

  function setOverride(elementId, field, newValue) {
    if (!isSafeOverrideKey(elementId) || !isSafeOverrideKey(field)) return;
    state.overrides.byId[elementId] = state.overrides.byId[elementId] || {};
    state.overrides.byId[elementId][field] = newValue;
  }

  function revertOverride(elementId, field) {
    if (!isSafeOverrideKey(elementId) || !isSafeOverrideKey(field)) return;
    const ov = state.overrides.byId[elementId];
    if (!ov) return;
    delete ov[field];
    if (Object.keys(ov).length === 0) delete state.overrides.byId[elementId];
  }

  function resetAllOverrides() {
    state.overrides = { byId: {} };
  }

  function listOverrides() {
    const out = [];
    for (const elementId of Object.keys(state.overrides.byId)) {
      const fields = state.overrides.byId[elementId];
      for (const field of Object.keys(fields)) {
        const el = state.imported
          ? (state.imported.structures.find((s) => s.id === elementId)
             || state.imported.pipes.find((p) => p.id === elementId))
          : null;
        out.push({
          elementId, field,
          newValue: fields[field],
          originalValue: el ? el[field] : null
        });
      }
    }
    return out;
  }

  // Toolbar label is a pure function of state.ui.mode; renderAll calls this so the
  // label survives imports and programmatic mode changes, not just clicks.
  function syncModeButton() {
    const btn = document.getElementById("modeToggle");
    if (btn) btn.textContent = state.ui.mode === "edit" ? "▸ edit" : "▸ explore";
  }

  function setMode(mode) {
    if (mode !== "explore" && mode !== "edit") return;
    state.ui.mode = mode;
    renderAll();
  }
```

`renderAll` (bootstrap) must call `if (typeof syncModeButton === "function") syncModeButton();` after the other renderers so the label tracks every mode change.

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [{ id: "A", type: "bend", crown: 100 }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", slope: 0.005 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };

setOverride("P1", "slope", 0.006);
console.assert(state.overrides.byId.P1.slope === 0.006, "set");
console.assert(resolveField("P1", "slope", state.imported, state.overrides) === 0.006, "resolve returns override");
console.assert(resolveField("P1", "length", state.imported, state.overrides) === undefined, "resolve falls back to imported (undefined here)");

setOverride("P1", "length", 150);
console.assert(Object.keys(state.overrides.byId.P1).length === 2, "two overrides");

const ovs = listOverrides();
console.assert(ovs.length === 2, "listOverrides count");
console.assert(ovs.find((o) => o.field === "slope").newValue === 0.006, "slope entry");

revertOverride("P1", "slope");
console.assert(state.overrides.byId.P1.slope === undefined, "slope reverted");
console.assert(state.overrides.byId.P1.length === 150, "length kept");

revertOverride("P1", "length");
console.assert(state.overrides.byId.P1 === undefined, "empty override object removed");

setOverride("A", "crown", 101);
setOverride("P1", "slope", 0.006);
resetAllOverrides();
console.assert(Object.keys(state.overrides.byId).length === 0, "reset all");

setMode("edit");
console.assert(state.ui.mode === "edit", "mode set");
setMode("explore");
console.assert(state.ui.mode === "explore", "mode reset");

console.log("task-23 overrides store: OK");
```

## Done when

- `setOverride`, `revertOverride`, `resetAllOverrides`, `listOverrides`, `setMode` defined.
- Smoke test prints `OK`.
- `state.imported` is never mutated by these functions (`listOverrides` reads it only).
- Build still succeeds.
- Commit: `feat(visualizer): task-23 overrides store`.

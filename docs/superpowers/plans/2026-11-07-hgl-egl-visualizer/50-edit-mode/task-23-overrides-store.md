# Task 23: Overrides store (set/revert/reset/resolve)

## Context

Centralize the overrides API used by task-24 (editable inputs) and task-25 (reset UI). `resolveField` already exists (task-12); this task adds setters and reset helpers. Implements spec §6.1.

## Preconditions

- Prior tasks: task-01, task-03, task-12.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Insert inside the `edit-mode` sentinel block, immediately after the `begin` line:

```js
  // --- Overrides store (task-23) ---

  function setOverride(elementId, field, newValue) {
    state.overrides.byId[elementId] = state.overrides.byId[elementId] || {};
    state.overrides.byId[elementId][field] = newValue;
  }

  function revertOverride(elementId, field) {
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
    for (const elementId in state.overrides.byId) {
      const fields = state.overrides.byId[elementId];
      for (const field in fields) {
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

  // Mode toggle (E hotkey + toolbar button are handled in task-24 for completeness).
  function setMode(mode) {
    if (mode !== "explore" && mode !== "edit") return;
    state.ui.mode = mode;
    const btn = document.getElementById("modeToggle");
    if (btn) btn.textContent = mode === "edit" ? "▸ edit" : "▸ explore";
    renderAll();
  }
```

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

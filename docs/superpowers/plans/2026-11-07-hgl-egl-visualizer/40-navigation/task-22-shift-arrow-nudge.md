# Task 22: Shift+Arrow nudge (edit mode only)

## Context

In edit mode, holding Shift and pressing an arrow key nudges the selected structure's world `x, y` by 10 ft/step. Overrides are stored in `state.overrides.byId[sid].x/.y`. Implements spec §5.1 Shift+Arrow row.

## Preconditions

- Prior tasks: task-01, task-03, task-15, task-19.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-21:

```js
  // --- Shift+Arrow nudge (task-22) ---

  const NUDGE_FT = 10;

  function nudgeSelectedStructure(dx, dy) {
    if (state.ui.mode !== "edit") return;
    if (!state.cursor || state.cursor.kind !== "structure") return;
    const sid = state.cursor.id;
    const str = state.imported && state.imported.structures.find((s) => s.id === sid);
    if (!str) return;

    const ov = state.overrides.byId[sid] = state.overrides.byId[sid] || {};
    const curX = (typeof ov.x === "number") ? ov.x : (str.x || 0);
    const curY = (typeof ov.y === "number") ? ov.y : (str.y || 0);
    ov.x = curX + dx;
    ov.y = curY + dy;
    // Materialize into imported so renderIso reads it via normal field path
    str.x = ov.x;
    str.y = ov.y;
    renderAll();
  }

  document.addEventListener("keydown", (ev) => {
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;
    if (!ev.shiftKey) return;
    let dx = 0, dy = 0;
    if (ev.key === "ArrowUp") dy = -NUDGE_FT;
    else if (ev.key === "ArrowDown") dy = NUDGE_FT;
    else if (ev.key === "ArrowLeft") dx = -NUDGE_FT;
    else if (ev.key === "ArrowRight") dx = NUDGE_FT;
    else return;
    ev.preventDefault();
    nudgeSelectedStructure(dx, dy);
  });
```

**Important:** The non-Shift arrow handler from task-19 should ignore events where `ev.shiftKey === true` so Shift+Arrow doesn't also advance the cursor. Modify task-19's handler to add the guard (if not already present). Locate the handler installed by task-19 (starts `document.addEventListener("keydown"` and handles `ArrowUp`/`ArrowDown`). Add `if (ev.shiftKey) return;` as the first line inside the handler body:

```js
  document.addEventListener("keydown", (ev) => {
    if (ev.shiftKey) return;                         // ← ADD this guard (task-22 compatibility)
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;
    if (ev.key === "ArrowUp") { /* ... */ }
    // ...
  });
```

## Acceptance test

In DevTools console (after rendering):

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0 },
    { id: "A",   type: "bend",    x: 0, y: -100 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };

// Default mode: Shift+ArrowRight should NOT move
state.ui.mode = "explore";
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true, bubbles: true }));
console.assert((state.imported.structures.find((s) => s.id === "A")).x === 0, "no move in explore mode");

// Edit mode: moves
state.ui.mode = "edit";
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true, bubbles: true }));
let aX = state.imported.structures.find((s) => s.id === "A").x;
console.assert(aX === 10, "Shift+ArrowRight moved A to x=10, got " + aX);
console.assert(state.overrides.byId["A"].x === 10, "override recorded");

// Multiple nudges accumulate
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", shiftKey: true, bubbles: true }));
let aY = state.imported.structures.find((s) => s.id === "A").y;
console.assert(aY === -110, "Shift+ArrowUp moved A to y=-110, got " + aY);

// Plain ArrowUp (no shift) in edit mode should NOT nudge — it should walk the cursor
// (we're already at A which is a headwater so no advance happens).
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
aY = state.imported.structures.find((s) => s.id === "A").y;
console.assert(aY === -110, "non-Shift ArrowUp did not nudge: y still -110");

console.log("task-22 nudge: OK");
```

## Done when

- `NUDGE_FT`, `nudgeSelectedStructure`, Shift+Arrow handler all defined.
- Task-19's non-Shift handler has `if (ev.shiftKey) return;` guard.
- Shift+Arrow only moves in edit mode.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-22 Shift+Arrow structure nudge`.

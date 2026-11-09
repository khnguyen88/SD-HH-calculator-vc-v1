# Task 22: Shift+Arrow nudge (edit mode only)

## Context

In edit mode, holding Shift and pressing an arrow key nudges the selected structure's world `x, y` by 10 ft/step. Overrides are stored in `state.overrides.byId[sid].x/.y`. Implements spec §5.1 Shift+Arrow row.

## Preconditions

- Prior tasks: task-01, task-03, task-15, task-19.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-21:

```js
  // --- Shift+Arrow nudge (task-22) ---

  const NUDGE_FT = 10;

  function nudgeSelectedStructure(dx, dy) {
    if (state.ui.mode !== "edit") return;
    if (!state.cursor || state.cursor.kind !== "structure") return;
    const sid = state.cursor.id;
    if (!isSafeOverrideKey(sid)) return;
    const str = state.imported && state.imported.structures.find((s) => s.id === sid);
    if (!str) return;

    // Overrides are a separate layer; never mutate state.imported (task-23 depends on
    // imported staying the immutable source). renderIso resolves x/y overrides.
    const ov = state.overrides.byId[sid] = state.overrides.byId[sid] || {};
    if (dx) {
      const curX = (typeof ov.x === "number") ? ov.x : (typeof str.x === "number" ? str.x : 0);
      ov.x = curX + dx;
    }
    if (dy) {
      const curY = (typeof ov.y === "number") ? ov.y : (typeof str.y === "number" ? str.y : 0);
      ov.y = curY + dy;
    }
    renderAll();
  }

  document.addEventListener("keydown", (ev) => {
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;
    if (!ev.shiftKey) return;
    // Only claim the gesture when it will actually nudge; otherwise let the
    // browser handle Shift+Arrow (text selection) in explore mode.
    if (state.ui.mode !== "edit") return;
    if (!state.cursor || state.cursor.kind !== "structure") return;
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

**Also modify `renderIso` (task-15)** so it resolves `x`/`y` through `resolveField`, keeping overrides out of `state.imported`. Replace its `pts` construction with:

```js
    const pts = s.imported.structures.map((st) => {
      const rx = resolveField(st.id, "x", s.imported, s.overrides);
      const ry = resolveField(st.id, "y", s.imported, s.overrides);
      const x = (typeof rx === "number" && isFinite(rx)) ? rx : 0;
      const y = (typeof ry === "number" && isFinite(ry)) ? ry : 0;
      return { id: st.id, type: st.type, x, y, z: (st.rim || 0) };
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
console.assert(state.overrides.byId["A"] === undefined, "no override in explore mode");

// Edit mode: moves, recorded as an override (imported stays immutable)
state.ui.mode = "edit";
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", shiftKey: true, bubbles: true }));
console.assert(state.overrides.byId["A"].x === 10, "override A.x=10, got " + state.overrides.byId["A"].x);
console.assert(state.imported.structures.find((s) => s.id === "A").x === 0, "imported A.x untouched");
const isoA = state.imported; // renderIso resolves overrides, so A renders at x=10
console.assert(typeof resolveField("A", "x", isoA, state.overrides) === "number", "renderIso reads resolved x");

// Multiple nudges accumulate
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", shiftKey: true, bubbles: true }));
console.assert(state.overrides.byId["A"].y === -110, "override A.y=-110, got " + state.overrides.byId["A"].y);

// Plain ArrowUp (no shift) in edit mode should NOT nudge — it should walk the cursor
// (we're already at A which is a headwater so no advance happens).
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(state.overrides.byId["A"].y === -110, "non-Shift ArrowUp did not nudge: y still -110");

console.log("task-22 nudge: OK");
```

## Done when

- `NUDGE_FT`, `nudgeSelectedStructure`, Shift+Arrow handler all defined.
- Task-19's non-Shift handler has `if (ev.shiftKey) return;` guard.
- Shift+Arrow only moves in edit mode.
- `state.imported` is not mutated; `renderIso` resolves x/y overrides.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-22 Shift+Arrow structure nudge`.

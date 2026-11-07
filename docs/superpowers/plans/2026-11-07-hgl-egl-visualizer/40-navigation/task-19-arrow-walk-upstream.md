# Task 19: Arrow-key walk upstream handler

## Context

Document-level `keydown` handler for `↑/↓/Enter/Esc`. Default (upstream) mode. Branch popup (task-20) fires when `↑` lands on a multi-inflow structure. Implements spec §5.1.

## Preconditions

- Prior tasks: task-01, task-03, task-05, task-12, task-17, task-18.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-18:

```js
  // --- Arrow walk handler (task-19) ---

  function isTypingTarget(ev) {
    const t = ev.target;
    if (!t) return false;
    const tag = t.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (t.isContentEditable) return true;
    return false;
  }

  // Branch popup state is managed by task-20; this handler just checks for it.
  function isBranchPopupOpen() {
    return !!document.getElementById("branchPopup");
  }

  // Attempt to advance the cursor upstream. If >1 options, calls openBranchPopup from task-20.
  function tryAdvance() {
    if (!state.imported) return;
    const opts = upstreamOptions(state.cursor, state.imported);
    if (opts.length === 0) return;
    if (opts.length === 1) {
      state.cursor = advanceCursor(state.cursor, opts[0]);
      renderAll();
      return;
    }
    // >1 options: remember a previous choice if any; otherwise open popup
    const sid = state.cursor.id;
    const remembered = state.ui.branchChoices.byStructureId[sid];
    const chosen = remembered ? opts.find((o) => o.id === remembered) : null;
    if (chosen) {
      state.cursor = advanceCursor(state.cursor, chosen);
      renderAll();
      return;
    }
    if (typeof openBranchPopup === "function") {
      openBranchPopup(sid, opts);
    } else {
      // Fallback: pick the first until task-20 lands.
      state.cursor = advanceCursor(state.cursor, opts[0]);
      renderAll();
    }
  }

  function tryRetreat() {
    state.cursor = retreatCursor(state.cursor);
    state.cursor = resolveCursorKind(state.cursor, state.imported);
    renderAll();
  }

  function resetWalk() {
    if (!state.imported) return;
    state.cursor = initialCursor(state.imported);
    renderAll();
  }

  document.addEventListener("keydown", (ev) => {
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;  // popup owns the keyboard while open
    if (ev.key === "ArrowUp") {
      ev.preventDefault();
      tryAdvance();
    } else if (ev.key === "ArrowDown") {
      ev.preventDefault();
      tryRetreat();
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      resetWalk();
    }
  });
```

## Acceptance test

In DevTools console of the dev HTML (populate state first via console or an import):

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0 },
    { id: "A", type: "bend", x: 0, y: -100 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT",
      shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = initialCursor(state.imported);

// Simulate ArrowUp
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(state.cursor.id === "P1", "ArrowUp should advance onto P1, got " + state.cursor.id);

document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(state.cursor.id === "A", "second ArrowUp should advance onto A");

// Nothing upstream of A
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(state.cursor.id === "A", "no advance past headwater");

// ArrowDown retreats
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
console.assert(state.cursor.id === "P1", "ArrowDown retreats to P1");

// Escape resets
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
console.assert(state.cursor.id === "OUT" && state.cursor.pathStack.length === 1, "Escape resets");

console.log("task-19 arrow walk: OK");
```

## Done when

- `tryAdvance`, `tryRetreat`, `resetWalk`, `isTypingTarget`, `isBranchPopupOpen`, keydown handler all present.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-19 arrow-key upstream walk`.

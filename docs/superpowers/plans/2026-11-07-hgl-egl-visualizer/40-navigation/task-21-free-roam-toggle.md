# Task 21: Free-roam mode toggle

## Context

Settings toggle that flips `state.ui.freeRoam`. In free-roam mode, `↑/↓` move cursor toward headwater / outfall from any starting point, and clicking an iso element starts a new walk there. Branch popup never auto-fires. `←/→` reopens the popup manually at any junction. Implements spec §5 free-roam rows.

## Preconditions

- Prior tasks: task-01, task-03, task-15, task-19, task-20.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-20:

```js
  // --- Free-roam mode (task-21) ---

  function toggleFreeRoam() {
    state.ui.freeRoam = !state.ui.freeRoam;
    renderAll();
  }

  // In free-roam, clicking an iso element starts a new walk there.
  function installIsoClickHandler() {
    const svg = document.getElementById("viewSvg");
    if (!svg) return;
    svg.addEventListener("click", (ev) => {
      if (!state.ui.freeRoam) return;
      const target = ev.target.closest("[data-kind][data-id]");
      if (!target) return;
      const kind = target.getAttribute("data-kind");
      const id = target.getAttribute("data-id");
      state.cursor = { kind, id, pathStack: [id] };
      renderAll();
    });
  }
  installIsoClickHandler();

  // ←/→ in free-roam: at any junction (multi-inflow structure), open the popup to re-pick.
  document.addEventListener("keydown", (ev) => {
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;
    if (!state.ui.freeRoam) return;
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
      if (!state.imported || !state.cursor || state.cursor.kind !== "structure") return;
      const opts = upstreamOptions(state.cursor, state.imported);
      if (opts.length >= 2) {
        ev.preventDefault();
        openBranchPopup(state.cursor.id, opts);
      }
    }
  });
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", x: 0, y: 0 },
    { id: "A", type: "bend", x: 0, y: -100 },
    { id: "B", type: "manhole", x: 60, y: -100 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 },
    { id: "P2", fromId: "B", toId: "OUT", shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = initialCursor(state.imported);
state.ui.freeRoam = false;
renderAll();

// In default mode: ArrowLeft does nothing
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "ArrowLeft in default mode: no popup");

// Toggle free-roam
toggleFreeRoam();
console.assert(state.ui.freeRoam === true, "freeRoam toggled on");

// ArrowLeft at OUT (2 upstream pipes) opens popup
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
console.assert(document.getElementById("branchPopup") !== null, "ArrowLeft in free-roam opens popup");
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

// Simulate click on a structure in iso view to start a new walk
const stA = document.querySelector('#viewSvg [data-kind="structure"][data-id="A"]');
console.assert(stA !== null, "iso element for A exists (renderIso must have run)");
if (stA) {
  stA.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  console.assert(state.cursor.id === "A" && state.cursor.pathStack.length === 1, "click starts new walk at A");
}

console.log("task-21 free-roam: OK");
```

## Done when

- `toggleFreeRoam`, `installIsoClickHandler`, `←/→` handler defined.
- Click on an iso element in free-roam starts a new walk there.
- `←/→` in free-roam at a junction opens the branch popup.
- Default mode is unaffected by `←/→`.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-21 free-roam mode toggle`.

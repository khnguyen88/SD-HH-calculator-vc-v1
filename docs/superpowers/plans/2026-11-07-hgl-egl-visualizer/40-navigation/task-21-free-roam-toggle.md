# Task 21: Free-roam mode toggle

## Context

Settings toggle that flips `state.ui.freeRoam`. In free-roam mode, `↑/↓` move cursor toward headwater / outfall from any starting point, and clicking an iso element starts a new walk there. The branch popup never fires in free-roam (spec §5.2); `←/→` cycle the remembered branch directly at a multi-inflow junction. In default mode, `←/→` open the branch popup (spec §5.1). Implements spec §5 free-roam rows.

## Preconditions

- Prior tasks: task-01, task-03, task-15, task-19, task-20.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-20:

```js
  // --- Free-roam mode (task-21) ---

  function toggleFreeRoam() {
    state.ui.freeRoam = !state.ui.freeRoam;
    renderAll();
  }

  // Build the canonical outfall→elementId chain by walking downstream from elementId.
  // The cursor may start mid-network in free-roam, but the ledger always needs an
  // outfall-anchored path so HGL accumulates from the tailwater boundary.
  function pathFromOutfall(elementId, imported) {
    if (!imported || !elementId) return [];
    const outfallSid = imported.outfall && imported.outfall.structureId;
    const seen = new Set();
    const down = [elementId];
    let cur = elementId;
    while (cur && cur !== outfallSid && !seen.has(cur)) {
      seen.add(cur);
      const pipe = imported.pipes.find((p) => p.id === cur);
      if (pipe) {
        cur = pipe.toId;
      } else {
        const outlet = imported.pipes.find((p) => p.fromId === cur);
        cur = outlet ? outlet.id : null;
      }
      if (cur) down.push(cur);
    }
    const path = down.reverse();
    if (outfallSid && path[0] !== outfallSid) path.unshift(outfallSid);
    return path;
  }

  // In free-roam, clicking an iso element starts a new walk there.
  function installIsoClickHandler() {
    const svg = document.getElementById("viewSvg");
    if (!svg) return;
    svg.addEventListener("click", (ev) => {
      if (!state.ui.freeRoam || state.ui.view !== "iso") return;
      const target = ev.target.closest("[data-kind][data-id]");
      if (!target) return;
      const kind = target.getAttribute("data-kind");
      const id = target.getAttribute("data-id");
      const pathStack = pathFromOutfall(id, state.imported);
      state.cursor = { kind, id, pathStack: pathStack.length ? pathStack : [id] };
      renderAll();
    });
  }
  installIsoClickHandler();

  // ←/→ at a multi-inflow junction. Default mode opens the branch popup; free-roam
  // must never fire the popup (spec §5.2), so it cycles the remembered branch directly.
  document.addEventListener("keydown", (ev) => {
    if (ev.shiftKey) return;  // Shift+Arrow is the task-22 nudge gesture
    if (isTypingTarget(ev)) return;
    if (isBranchPopupOpen()) return;
    if (!state.imported || !state.cursor || state.cursor.kind !== "structure") return;
    if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
    const opts = upstreamOptions(state.cursor, state.imported);
    if (opts.length < 2) return;
    ev.preventDefault();
    const sid = state.cursor.id;
    if (state.ui.freeRoam) {
      const remembered = state.ui.branchChoices.byStructureId[sid];
      const at = Math.max(0, opts.findIndex((o) => o.id === remembered));
      const step = ev.key === "ArrowRight" ? 1 : -1;
      const next = (at + step + opts.length) % opts.length;
      state.ui.branchChoices.byStructureId[sid] = opts[next].id;
      renderAll();
    } else {
      openBranchPopup(sid, opts);
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

// Default mode: ArrowLeft at a 2-inflow junction opens the popup (spec §5.1)
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
console.assert(document.getElementById("branchPopup") !== null, "ArrowLeft in default mode opens popup");
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "Esc closes popup");

// Toggle free-roam
toggleFreeRoam();
console.assert(state.ui.freeRoam === true, "freeRoam toggled on");

// Free-roam: ArrowRight cycles the remembered branch WITHOUT opening the popup
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "free-roam ArrowRight must not open popup");
console.assert(state.ui.branchChoices.byStructureId.OUT === "P2", "free-roam ArrowRight cycled to P2");

// Simulate click on a structure in iso view to start a new walk
const stA = document.querySelector('#viewSvg [data-kind="structure"][data-id="A"]');
console.assert(stA !== null, "iso element for A exists (renderIso must have run)");
if (stA) {
  stA.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  console.assert(state.cursor.id === "A", "click starts new walk at A");
  console.assert(state.cursor.pathStack[0] === "OUT", "click path is outfall-anchored");
  console.assert(state.cursor.pathStack[state.cursor.pathStack.length - 1] === "A", "click path ends at A");
}

// Free-roam down-arrow from the clicked structure walks toward the outfall
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
console.assert(state.cursor.id === "P1", "ArrowDown from A moves toward outfall onto P1");

console.log("task-21 free-roam: OK");
```

## Done when

- `toggleFreeRoam`, `pathFromOutfall`, `installIsoClickHandler`, `←/→` handler defined.
- Click on an iso element in free-roam starts a new walk there, with an outfall-anchored `pathStack`; `↓` walks toward the outfall.
- `←/→` in free-roam cycles the remembered branch at a junction and never opens the popup.
- In default mode, `←/→` at a multi-inflow junction opens the branch popup.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-21 free-roam mode toggle`.

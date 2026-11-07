# Task 20: Branch popup for multi-inflow junctions

## Context

Modal popup when the cursor's upstream has >1 pipes. Keyboard-first (`↑/↓` cycle, `Enter` confirm, `Esc` cancel). Chosen branch is remembered in `state.ui.branchChoices.byStructureId`. Implements spec §5.2.

## Preconditions

- Prior tasks: task-01, task-03, task-19.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `navigation` sentinel block after task-19:

```js
  // --- Branch popup (task-20) ---

  let branchKeyHandler = null;

  function closeBranchPopup() {
    const e = document.getElementById("branchPopup");
    if (e) e.remove();
    if (branchKeyHandler) {
      document.removeEventListener("keydown", branchKeyHandler, true);
      branchKeyHandler = null;
    }
  }

  function openBranchPopup(sid, options) {
    closeBranchPopup();
    let selectedIndex = 0;

    const render = () => {
      const old = document.getElementById("branchPopup");
      if (old) old.remove();
      const panel = el("div", {
        id: "branchPopup",
        style: "position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); "
             + "background:#161b22; color:#e6edf3; padding:16px 20px; border:1px solid #30363d; "
             + "border-radius:6px; font-family:system-ui,sans-serif; min-width:320px; z-index:1000;"
      });
      panel.appendChild(el("div", { style: "margin-bottom:10px; font-weight:600;" },
        "Structure " + sid + " has " + options.length + " upstream pipes."));
      panel.appendChild(el("div", { style: "margin-bottom:12px; color:#8b949e;" },
        "Which branch do you want to follow?"));
      const ul = el("div", null);
      options.forEach((opt, i) => {
        const row = el("div", {
          style: "padding:6px 8px; font-family:ui-monospace,monospace; "
               + (i === selectedIndex ? "background:#30363d;" : "")
        }, (i === selectedIndex ? "◉ " : "○ ") + opt.label);
        ul.appendChild(row);
      });
      panel.appendChild(ul);
      panel.appendChild(el("div", { style: "margin-top:12px; color:#8b949e; font-size:12px;" },
        "↑/↓ cycle · Enter follow · Esc cancel"));
      document.body.appendChild(panel);
    };
    render();

    const keyHandler = (ev) => {
      if (ev.key === "ArrowUp") {
        ev.preventDefault(); ev.stopImmediatePropagation();
        selectedIndex = (selectedIndex - 1 + options.length) % options.length;
        render();
      } else if (ev.key === "ArrowDown") {
        ev.preventDefault(); ev.stopImmediatePropagation();
        selectedIndex = (selectedIndex + 1) % options.length;
        render();
      } else if (ev.key === "Enter") {
        ev.preventDefault(); ev.stopImmediatePropagation();
        const chosen = options[selectedIndex];
        state.ui.branchChoices.byStructureId[sid] = chosen.id;
        state.cursor = advanceCursor(state.cursor, chosen);
        closeBranchPopup();
        renderAll();
      } else if (ev.key === "Escape") {
        ev.preventDefault(); ev.stopImmediatePropagation();
        closeBranchPopup();
      }
    };
    branchKeyHandler = keyHandler;
    document.addEventListener("keydown", keyHandler, true);
  }

  function resetBranchChoices() {
    state.ui.branchChoices = { byStructureId: {} };
  }
```

## Acceptance test

In the dev HTML DevTools console:

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall" },
    { id: "A",   type: "bend" },
    { id: "B",   type: "manhole" }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT" },
    { id: "P2", fromId: "B", toId: "OUT" }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = initialCursor(state.imported);

// ArrowUp at OUT (which has 2 upstream pipes) should open popup
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(document.getElementById("branchPopup") !== null, "popup should open");

// ArrowDown cycles
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
console.assert(document.getElementById("branchPopup").textContent.includes("◉ P2"), "second option selected");

// Enter commits
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "popup should close");
console.assert(state.cursor.id === "P2", "cursor advanced to P2");
console.assert(state.ui.branchChoices.byStructureId.OUT === "P2", "choice remembered");

// Next time at OUT, the remembered choice fires silently
state.cursor = initialCursor(state.imported);
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "remembered choice should bypass popup");
console.assert(state.cursor.id === "P2", "advanced via remembered choice");

// Reset and try Escape
state.cursor = initialCursor(state.imported);
resetBranchChoices();
document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
console.assert(document.getElementById("branchPopup") !== null, "popup reopens after reset");
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
console.assert(document.getElementById("branchPopup") === null, "Esc closes popup");
console.assert(state.cursor.id === "OUT", "Esc leaves cursor unchanged");

console.log("task-20 branch popup: OK");
```

## Done when

- `openBranchPopup`, `closeBranchPopup`, `resetBranchChoices` defined.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-20 branch popup with remembered choice`.

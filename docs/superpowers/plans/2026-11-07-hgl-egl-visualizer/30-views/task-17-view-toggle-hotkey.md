# Task 17: View toggle hotkey and toolbar button

## Context

Wire the `V` key and the toolbar `[ISO | profile]` label to toggle `state.ui.view` and re-render the top-half SVG. Align the static markup with the runtime label so there is no first-paint flash, and give it `cursor:pointer` since it is clickable. Also implement a `renderActiveView` dispatcher used by `renderAll`. Implements spec §5.1 (hotkey) and §3.3 (toolbar).

## Preconditions

- Prior tasks: task-01, task-03, task-15, task-16.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `views` sentinel block after task-16:

```js
  // --- Active view dispatcher + V hotkey (task-17) ---

  function renderActiveView() {
    const svg = document.getElementById("viewSvg");
    if (!svg) return;
    if (state.ui.view === "iso") {
      renderIso(svg, state);
    } else {
      // Build ledger from current path (or empty) and annotate for the active HGL method.
      const path = (state.imported && state.cursor && state.cursor.pathStack && state.cursor.pathStack.length)
        ? state.cursor.pathStack
        : (state.imported && state.imported.outfall && state.imported.outfall.structureId
            ? [state.imported.outfall.structureId] : []);
      const rows = buildLedger(path, state, state.imported ? state.imported.kbTable : null, state.ui.hglMethod);
      const annotated = annotateLedgerHgl(rows, state, state.ui.hglMethod);
      renderProfile(svg, state, annotated);
    }
    // Update toolbar indicator
    const label = document.getElementById("viewToggle");
    if (label) label.textContent = state.ui.view === "iso" ? "[ISO | profile]" : "[iso | PROFILE]";
  }

  function toggleView() {
    state.ui.view = state.ui.view === "iso" ? "profile" : "iso";
    renderActiveView();
  }
```

**Modify** the bootstrap block. Locate the `renderAll` stub:

```js
  function renderAll() {
    // (fleshed out as views/ledger/navigation tasks land)
  }
```

Replace with:

```js
  function renderAll() {
    renderActiveView();
    // ledger render is wired in by group 60
    if (typeof renderLedger === "function") renderLedger();
  }

  // V hotkey (also 'v' lowercase).
  document.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey || ev.metaKey || ev.altKey || ev.repeat) return;
    if (isBranchPopupOpen()) return;  // modal popup owns the keyboard while open
    const t = ev.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    if (ev.key === "v" || ev.key === "V") {
      ev.preventDefault();
      toggleView();
    }
  });

  // Toolbar click
  const toggleLabel = document.getElementById("viewToggle");
  if (toggleLabel) toggleLabel.addEventListener("click", () => toggleView());
```

## Acceptance test

In the dev HTML browser console (after task-15/16 populate some state):

```js
// Starts in iso
console.assert(state.ui.view === "iso", "initial view");

// Simulate V keydown
document.dispatchEvent(new KeyboardEvent("keydown", { key: "v", bubbles: true }));
console.assert(state.ui.view === "profile", "V did not toggle to profile");

// And back
document.dispatchEvent(new KeyboardEvent("keydown", { key: "V", bubbles: true }));
console.assert(state.ui.view === "iso", "V did not toggle back");

// V in a text input should NOT toggle
const input = document.createElement("input");
input.type = "text";
document.body.appendChild(input);
input.focus();
input.addEventListener("keydown", (ev) => ev.stopPropagation && 0);  // just ensure we test the guard
const prevView = state.ui.view;
document.dispatchEvent(new KeyboardEvent("keydown", { key: "v", target: input, bubbles: true }));
// Note: dispatching on document with target=input won't actually set ev.target properly,
// but the guard checks document.activeElement; focused input blocks V.
// Easier test: focus an input and simulate a REAL keydown via the input element:
input.dispatchEvent(new KeyboardEvent("keydown", { key: "v", bubbles: true }));
console.assert(state.ui.view === prevView, "V in input should not toggle (focused input)");
document.body.removeChild(input);

// Toolbar click
document.getElementById("viewToggle").click();
console.assert(state.ui.view === "profile", "toolbar click did not toggle");

console.log("task-17 toggle: OK");
```

## Done when

- `renderActiveView` and `toggleView` defined.
- `renderAll` dispatches to active view + ledger.
- V hotkey and toolbar click both toggle the view.
- V in a focused input does NOT toggle (guard works).
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-17 V hotkey and view toggle`.

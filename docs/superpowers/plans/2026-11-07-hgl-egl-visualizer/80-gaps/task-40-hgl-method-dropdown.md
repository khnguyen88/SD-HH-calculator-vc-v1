# Task 40: HGL method dropdown in topbar

## Context

Spec §4.2 says: "Top-bar dropdown: `HEC-22 EGL (d/s crown floor)` (default) or
`Legacy both-end crown floor`."  Task-13 implemented `hglAt` and `annotateLedgerHgl`
(the compute side). No task ever wired the UI control that changes `state.ui.hglMethod`.
Without this dropdown the user cannot switch methods from the browser.

## Preconditions

- Prior tasks: task-01 (skeleton with topbar HTML), task-03 (`el`, `withFocusPreserved`),
  task-13 (`hglAt`, `annotateLedgerHgl`), task-17 (`renderAll` defined).

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the
`views` sentinel block, **after** the task-17 code:

```js
  // --- HGL method dropdown (task-40) ---

  // Keep the select's displayed value in sync with state (called from renderAll).
  function syncHglSelect() {
    const sel = document.getElementById("hglMethodSelect");
    if (sel && sel.value !== state.ui.hglMethod) sel.value = state.ui.hglMethod;
  }

  // Inject into topbar once at page load.
  (function () {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return;

    const label = el("label", {
      for: "hglMethodSelect",
      style: "font-size:12px; color:var(--fg-dim); margin-left:8px; white-space:nowrap;"
    }, "HGL method:");

    const sel = el("select", {
      id: "hglMethodSelect",
      style: "font-family:var(--mono); font-size:12px; "
           + "background:var(--bg-elev); color:var(--fg); "
           + "border:1px solid #30363d; padding:2px 4px; margin-left:4px;",
      onchange: (ev) => {
        state.ui.hglMethod = ev.target.value;
        withFocusPreserved(renderAll);
      }
    });
    sel.appendChild(el("option", { value: "hec22" },              "HEC-22 EGL"));
    sel.appendChild(el("option", { value: "legacy-both-crown" },  "Legacy both-crown"));

    // Insert label + select before the mode toggle button (keeps topbar order clean).
    const modeBtn = document.getElementById("modeToggle");
    if (modeBtn) {
      topbar.insertBefore(sel,   modeBtn);
      topbar.insertBefore(label, sel);
    } else {
      topbar.appendChild(label);
      topbar.appendChild(sel);
    }
  })();
```

**Also modify** the `renderAll` function in the `bootstrap` sentinel block.

Locate the current `renderAll` body (from task-17):

```js
  function renderAll() {
    renderActiveView();
    if (typeof renderLedger === "function") renderLedger();
  }
```

Replace with:

```js
  function renderAll() {
    renderActiveView();
    if (typeof renderLedger === "function") renderLedger();
    if (typeof syncHglSelect === "function") syncHglSelect();
  }
```

This ensures the select reflects `state.ui.hglMethod` after every import (task-05 sets
it from `config.hglMethod`) and after every programmatic state change.

## Acceptance test

In DevTools console of the dev HTML:

```js
// Verify dropdown exists after page load.
const sel = document.getElementById("hglMethodSelect");
console.assert(sel !== null, "dropdown should exist");
console.assert(sel.value === "hec22", "default value should be hec22");

// Switching to legacy changes state.ui.hglMethod.
sel.value = "legacy-both-crown";
sel.dispatchEvent(new Event("change", { bubbles: true }));
console.assert(state.ui.hglMethod === "legacy-both-crown", "state not updated after change");

// Switching back.
sel.value = "hec22";
sel.dispatchEvent(new Event("change", { bubbles: true }));
console.assert(state.ui.hglMethod === "hec22", "state not reset");

// Programmatic change propagates back to the select on next renderAll.
state.ui.hglMethod = "legacy-both-crown";
renderAll();
console.assert(sel.value === "legacy-both-crown", "select not synced after renderAll");

// Label is adjacent to the select.
console.assert(sel.previousSibling && sel.previousSibling.tagName === "LABEL",
  "label should precede select");

console.log("task-40 hgl dropdown: OK");
```

For the visual verification: load `visualizer-tests/fixtures/main-app-export.xlsx`, switch
to Profile view, then toggle the HGL method dropdown. The EGL (dashed blue) polyline stays
fixed; the HGL (solid yellow) polyline should shift when switching to "Legacy both-crown"
if any crown floors are above the HEC-22 HGL.

## Done when

- `hglMethodSelect` `<select>` is visible in the topbar when the built file loads.
- Select defaults to "HEC-22 EGL" (matches `state.ui.hglMethod === "hec22"`).
- Changing the select updates `state.ui.hglMethod` and triggers a re-render.
- `syncHglSelect` is called from `renderAll` and keeps the select in sync.
- Build still succeeds: `node visualizer/build-visualizer.js`.
- `node --test visualizer/visualizer-tests/` — no prior tests regressed.
- Commit: `feat(visualizer): task-40 HGL method dropdown in topbar`.

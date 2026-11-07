# Task 25: Override badge and reset panel

## Context

Toolbar badge showing the count of active overrides; clicking it opens a modal listing every override with per-row "Revert" buttons and a panel-level "Reset all". Implements spec §6.2.

## Preconditions

- Prior tasks: task-01, task-03, task-23.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `edit-mode` sentinel block after task-24:

```js
  // --- Override badge + reset panel (task-25) ---

  function renderOverrideBadge() {
    let badge = document.getElementById("overrideBadge");
    const count = listOverrides().length;
    if (!badge) {
      const topbar = document.querySelector(".topbar");
      if (!topbar) return;
      badge = el("button", { id: "overrideBadge", type: "button", style: "display:none;" });
      badge.addEventListener("click", openOverridePanel);
      topbar.appendChild(badge);
    }
    if (count === 0) {
      badge.style.display = "none";
    } else {
      badge.style.display = "";
      badge.textContent = count + " fields overridden";
      badge.style.cssText = "background:#ffd60a; color:#1a1a1a; border:none; padding:4px 10px; border-radius:4px; font-weight:600;";
    }
  }

  function closeOverridePanel() {
    const p = document.getElementById("overridePanel");
    if (p) p.remove();
  }

  function openOverridePanel() {
    closeOverridePanel();
    const ovs = listOverrides();
    const panel = el("div", {
      id: "overridePanel",
      style: "position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); "
           + "background:#161b22; color:#e6edf3; padding:16px 20px; border:1px solid #30363d; "
           + "border-radius:6px; font-family:system-ui,sans-serif; min-width:420px; max-height:70vh; overflow:auto; z-index:1000;"
    });
    panel.appendChild(el("div", { style: "font-weight:600; margin-bottom:10px;" }, "Active overrides (" + ovs.length + ")"));
    if (ovs.length === 0) {
      panel.appendChild(el("div", { style: "color:#8b949e;" }, "No overrides. Edits in the ledger will appear here."));
    } else {
      const table = el("table", { style: "width:100%; border-collapse:collapse; font-family:ui-monospace,monospace; font-size:12px;" });
      const head = el("tr", { style: "border-bottom:1px solid #30363d;" }, [
        el("th", { style: "text-align:left; padding:4px;" }, "Element"),
        el("th", { style: "text-align:left; padding:4px;" }, "Field"),
        el("th", { style: "text-align:right; padding:4px;" }, "Original"),
        el("th", { style: "text-align:right; padding:4px;" }, "New"),
        el("th", { style: "padding:4px;" }, "")
      ]);
      table.appendChild(head);
      for (const o of ovs) {
        const revertBtn = el("button", {
          type: "button",
          style: "padding:2px 8px;",
          onclick: () => { revertOverride(o.elementId, o.field); renderAll(); openOverridePanel(); }
        }, "Revert");
        const row = el("tr", { style: "border-bottom:1px solid #21262d;" }, [
          el("td", { style: "padding:4px;" }, o.elementId),
          el("td", { style: "padding:4px;" }, o.field),
          el("td", { style: "padding:4px; text-align:right;" }, String(o.originalValue)),
          el("td", { style: "padding:4px; text-align:right; color:#ffd60a;" }, String(o.newValue)),
          el("td", { style: "padding:4px;" }, revertBtn)
        ]);
        table.appendChild(row);
      }
      panel.appendChild(table);
    }

    const footer = el("div", { style: "margin-top:12px; display:flex; gap:8px; justify-content:flex-end;" }, [
      el("button", { type: "button",
        onclick: () => { resetAllOverrides(); renderAll(); openOverridePanel(); }
      }, "Reset all"),
      el("button", { type: "button", onclick: closeOverridePanel }, "Close")
    ]);
    panel.appendChild(footer);

    document.body.appendChild(panel);
  }

  // Esc closes the panel. Capture phase + stopImmediatePropagation so the walk
  // handlers (registered earlier, bubble phase) don't also run resetWalk.
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && document.getElementById("overridePanel")) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      closeOverridePanel();
    }
  }, true);
```

**Also modify the bootstrap `renderAll`** to refresh the badge after each render (no monkey-patching):

```js
  function renderAll() {
    renderActiveView();
    // ledger render is wired in by group 60
    if (typeof renderLedger === "function") renderLedger();
    if (typeof renderOverrideBadge === "function") renderOverrideBadge();
  }
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [{ id: "A", type: "bend" }, { id: "OUT", type: "outfall" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };

// Badge hidden initially
renderOverrideBadge();
let badge = document.getElementById("overrideBadge");
console.assert(badge && badge.style.display === "none", "badge hidden at 0 overrides");

// Add one override, re-render badge
setOverride("P1", "slope", 0.006);
renderOverrideBadge();
console.assert(badge.style.display !== "none", "badge visible at 1 override");
console.assert(badge.textContent === "1 fields overridden", "badge text");

// Open panel
openOverridePanel();
const panel = document.getElementById("overridePanel");
console.assert(panel !== null, "panel opened");
console.assert(panel.textContent.includes("P1"), "panel lists P1");
console.assert(panel.textContent.includes("0.006"), "panel lists new value");

// Revert via button
const revertBtn = Array.from(panel.querySelectorAll("button")).find((b) => b.textContent === "Revert");
console.assert(revertBtn !== undefined, "revert button present");
revertBtn.click();
console.assert(!state.overrides.byId.P1 || state.overrides.byId.P1.slope === undefined, "revert worked");

// Reset all
setOverride("P1", "slope", 0.006);
setOverride("A", "crown", 102);
openOverridePanel();
const resetBtn = Array.from(document.getElementById("overridePanel").querySelectorAll("button")).find((b) => b.textContent === "Reset all");
resetBtn.click();
console.assert(listOverrides().length === 0, "reset all cleared overrides");

// Esc closes
openOverridePanel();
document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
console.assert(document.getElementById("overridePanel") === null, "Esc closed panel");

console.log("task-25 badge+panel: OK");
```

## Done when

- `renderOverrideBadge`, `openOverridePanel`, `closeOverridePanel` defined.
- `renderAll` now also calls `renderOverrideBadge`.
- Badge hidden when 0 overrides, visible otherwise.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-25 override badge and reset panel`.

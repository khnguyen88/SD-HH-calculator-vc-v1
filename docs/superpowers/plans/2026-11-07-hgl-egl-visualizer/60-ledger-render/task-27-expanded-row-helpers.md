# Task 27: Expanded-row helpers (csSection, csFormula, csResult, csWarn)

## Context

Build the composable DOM helpers for calc-sheet-style content inside expanded ledger rows. Visual grammar matches the main app's print calc sheets. Also wire the top-level `renderLedger` function that `renderAll` already references. Implements spec §4 (equation panel) and §4.1 (row kinds).

## Preconditions

- Prior tasks: task-01, task-03, task-12.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Insert inside the `ledger-render` sentinel block, immediately after the `begin` line:

```js
  // --- Calc-sheet helpers (task-27) ---

  function csSection(label, children) {
    return el("div", { class: "cs-section", style: "margin:4px 0 8px 0;" }, [
      el("div", { style: "font-weight:600; font-size:11px; color:#444; text-transform:uppercase; margin-bottom:4px;" }, label),
      el("div", null, children)
    ]);
  }

  function csFormula(symbolic, substituted, result, unit) {
    return el("div", { style: "font-family:ui-monospace,monospace; font-size:12px; margin:2px 0;" }, [
      el("span", { style: "color:#555;" }, symbolic + " = "),
      substituted != null ? el("span", { style: "color:#222;" }, substituted + " = ") : null,
      el("span", { style: "font-weight:600;" }, String(result)),
      unit ? el("span", { style: "color:#555;" }, " " + unit) : null
    ]);
  }

  function csResult(label, value, unit) {
    return el("div", { style: "margin:6px 0; padding:4px 8px; background:#eceae2; font-family:ui-monospace,monospace;" }, [
      el("span", { style: "color:#444;" }, label + " = "),
      el("span", { style: "font-weight:700;" }, String(value)),
      unit ? el("span", { style: "color:#444;" }, " " + unit) : null
    ]);
  }

  function csWarn(text) {
    return el("div", {
      style: "margin:6px 0; padding:6px 10px; background:#fff4e5; color:#8a3a00; border-left:3px solid #ff8c00; font-size:12px;"
    }, text);
  }

  function fmtNum(v, decimals) {
    const d = (typeof decimals === "number") ? decimals : 3;
    if (typeof v !== "number" || !isFinite(v)) return String(v);
    return v.toFixed(d);
  }

  // Top-level ledger container — invoked by renderAll (task-17 wiring).
  function renderLedger() {
    const host = document.getElementById("ledger");
    if (!host) return;
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!state.imported) {
      host.appendChild(el("div", { style: "color:#666;" }, "No data imported."));
      return;
    }
    const path = (state.cursor && state.cursor.pathStack && state.cursor.pathStack.length)
      ? state.cursor.pathStack
      : [state.imported.outfall.structureId];
    const rows = buildLedger(path, state, state.imported.kbTable, state.ui.hglMethod);
    const annotated = annotateLedgerHgl(rows, state, state.ui.hglMethod);

    // Header line
    host.appendChild(el("div", { style: "font-weight:700; margin-bottom:8px;" },
      "Energy ledger (" + (state.ui.freeRoam ? "free-roam" : "upstream walk") + ") — HGL method: " + state.ui.hglMethod));

    // One row per ledger entry
    const cursorId = state.cursor && state.cursor.id;
    for (const row of annotated) {
      const isCurrent = row.id === cursorId;
      const collapsed = el("div", {
        style: "padding:3px 6px; font-family:ui-monospace,monospace; cursor:pointer; "
             + (isCurrent ? "background:#ffeaa7;" : ""),
        onclick: () => { /* click-to-expand handled by task-28/29 rendering an expanded block */ }
      }, oneLineForRow(row));
      host.appendChild(collapsed);
      if (isCurrent) {
        const details = el("div", { style: "padding:4px 20px;" }, renderExpandedRow(row));
        host.appendChild(details);
      }
    }
  }

  function oneLineForRow(row) {
    const arrow = " → ";
    const after = fmtNum(row.after, 2);
    if (row.kind === "start")  return "Start: " + row.label + "   EGL = " + after + " ft (tailwater)";
    if (row.kind === "hf")     return "+Hf " + row.label + "   +" + fmtNum(row.delta, 3) + arrow + after;
    if (row.kind === "hb")     return "+Hb " + row.label + "   +" + fmtNum(row.delta, 3) + arrow + after;
    if (row.kind === "end")    return "End: " + row.label + "   total rise = " + fmtNum(row.detail.totalRise, 3) + " ft";
    return JSON.stringify(row);
  }

  // Default expanded renderer — replaced by task-28/29 per row kind.
  function renderExpandedRow(row) {
    if (typeof renderHfRow === "function" && row.kind === "hf")   return renderHfRow(row);
    if (typeof renderHbRow === "function" && row.kind === "hb")   return renderHbRow(row);
    if (row.kind === "start") return csResult("Tailwater elevation", fmtNum(row.detail.tailwaterElev, 2), "ft");
    if (row.kind === "end")   return csResult("Total rise over walked path", fmtNum(row.detail.totalRise, 3), "ft");
    return el("div", null, "(no detail)");
  }
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [{ id: "OUT", type: "outfall" }, { id: "A", type: "bend" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };

renderLedger();

const host = document.getElementById("ledger");
console.assert(host.textContent.includes("Energy ledger"), "header rendered");
console.assert(host.textContent.includes("Start: OUT"), "start row rendered");
console.assert(host.textContent.includes("+Hf P1"), "hf row rendered");

// csSection/Formula/Result produce DOM
const s = csSection("test", csFormula("x", "2+2", 4, "ft"));
console.assert(s.textContent.includes("x = 2+2 = 4 ft"), "formula composed");
const r = csResult("Q", 8.4, "cfs");
console.assert(r.textContent.includes("Q = 8.4 cfs"), "result composed");
const w = csWarn("danger");
console.assert(w.textContent === "danger", "warn text");

console.log("task-27 ledger helpers: OK");
```

## Done when

- `csSection`, `csFormula`, `csResult`, `csWarn`, `fmtNum`, `renderLedger`, `oneLineForRow`, `renderExpandedRow` all defined.
- Ledger host populated after `renderLedger()`.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-27 expanded-row helpers and renderLedger`.

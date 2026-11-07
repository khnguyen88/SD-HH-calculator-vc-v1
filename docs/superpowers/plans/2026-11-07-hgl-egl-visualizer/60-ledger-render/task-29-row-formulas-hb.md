# Task 29: Expanded Hb row — structure loss formulas

## Context

Render the full structure-loss derivation for a `+Hb` ledger row. Dispatches by inflow count (0 / 1 / 2 / >2). Two-inflow detail is factored into task-30. Implements spec §4.1 `+Hb row` (0 and 1 inflow cases plus the 3+ inflow warning).

## Preconditions

- Prior tasks: task-01, task-03, task-10, task-11, task-12, task-23, task-24, task-27.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `ledger-render` sentinel block after task-28:

```js
  // --- Hb row expanded render (task-29) ---

  function renderHbRow(row) {
    const d = row.detail;
    const res = d.result;
    const isEdit = state.ui.mode === "edit";
    const typeSelect = isEdit
      ? editableSelect(row.id, "type", state.imported, state.overrides, ["inlet", "manhole", "bend", "junction", "splitter", "outfall"])
      : el("span", { style: "font-family:ui-monospace,monospace;" }, d.structureType);

    const header = el("div", null, [
      csSection("structure", el("table", { style: "font-family:ui-monospace,monospace; font-size:12px;" }, [
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "Type"), el("td", null, typeSelect)]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "Total Q (cfs)"), el("td", null, fmtNum(d.Qtotal, 2))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "Outflow pipe A_out (sf)"), el("td", null, fmtNum(d.Aout, 3))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "Vout (ft/s)"),
          el("td", null, fmtNum(d.Aout > 0 ? d.Qtotal / d.Aout : 0, 3))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "V²/(2g) (ft)"),
          el("td", null, fmtNum(velocityHead(d.Aout > 0 ? d.Qtotal / d.Aout : 0), 4))])
      ]))
    ]);

    if (res && res.error === "too-many-inflows") {
      return el("div", null, [
        header,
        csWarn(d.inflows.length + " inflows at structure " + row.id + "; controlling-angle method supports ≤2. No Hb computed.")
      ]);
    }

    const n = d.inflows.length;
    if (n === 0) {
      return el("div", null, [
        header,
        csSection("zero inflows (headwater)", el("div", { style: "font-size:12px; color:#444;" },
          "Nominal entrance condition: Kb evaluated at 0° for a " + d.structureType + ".")),
        csFormula("Kb(0°, " + d.structureType + ")", fmtNum(res.kbUsed, 3), fmtNum(res.kbUsed, 3), ""),
        csFormula("Hb = Kb · V²/(2g)",
          fmtNum(res.kbUsed, 3) + " · " + fmtNum(velocityHead(d.Aout > 0 ? d.Qtotal / d.Aout : 0), 4),
          fmtNum(res.Hb, 4), "ft"),
        csResult("Hb", fmtNum(res.Hb, 4), "ft")
      ]);
    }
    if (n === 1) {
      const a = d.inflows[0];
      return el("div", null, [
        header,
        csSection("one inflow", el("div", { style: "font-size:12px; color:#444;" },
          "Pipe " + a.pipeId + " enters at " + fmtNum(a.angleDeg, 1) + "°; Kb read at that angle.")),
        csFormula("Kb(" + fmtNum(a.angleDeg, 1) + "°, " + d.structureType + ")", null, fmtNum(res.kbUsed, 3), ""),
        csFormula("Hb = Kb · V²/(2g)",
          fmtNum(res.kbUsed, 3) + " · " + fmtNum(velocityHead(d.Aout > 0 ? d.Qtotal / d.Aout : 0), 4),
          fmtNum(res.Hb, 4), "ft"),
        csResult("Hb", fmtNum(res.Hb, 4), "ft")
      ]);
    }
    // n === 2 — defer to task-30
    if (typeof renderTwoInflowDetail === "function") {
      return el("div", null, [header, renderTwoInflowDetail(row)]);
    }
    return el("div", null, [header,
      csFormula("Hb (2-inflow controlling)", null, fmtNum(res.Hb, 4), "ft (detail in task-30)")]);
  }
```

## Acceptance test

In DevTools console:

```js
// 0-inflow (headwater)
state.imported = {
  structures: [{ id: "A", type: "manhole" }, { id: "OUT", type: "outfall" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 5 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
state.ui.mode = "explore";
renderLedger();
let host = document.getElementById("ledger");
console.assert(host.textContent.includes("zero inflows"), "0-inflow section rendered");
console.assert(host.textContent.includes("Hb"), "Hb rendered");

// 3-inflow should warn
state.imported = {
  structures: [
    { id: "A", type: "manhole" }, { id: "B1", type: "manhole" },
    { id: "B2", type: "manhole" }, { id: "B3", type: "manhole" },
    { id: "OUT", type: "outfall" }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 15 },
    { id: "PA1", fromId: "B1", toId: "A", shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 100, angle: 10, designQ: 5 },
    { id: "PA2", fromId: "B2", toId: "A", shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 100, angle: 30, designQ: 5 },
    { id: "PA3", fromId: "B3", toId: "A", shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 100, angle: 50, designQ: 5 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
renderLedger();
host = document.getElementById("ledger");
console.assert(host.textContent.includes("3 inflows at structure A"), "3-inflow warn");

console.log("task-29 hb row: OK");
```

## Done when

- `renderHbRow` defined.
- 0-inflow renders "zero inflows (headwater)" section.
- 1-inflow renders "one inflow" section with angle.
- 2-inflow delegates to `renderTwoInflowDetail` from task-30 (fallback renders "detail in task-30" if 30 isn't landed).
- 3+ inflow renders a `csWarn` panel.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-29 expanded Hb row (0/1/3+ inflow cases)`.

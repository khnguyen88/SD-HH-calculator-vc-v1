# Task 30: Two-inflow detail — both candidate losses + "smaller controls"

## Context

Render the pedagogical payoff of the controlling-angle method: show BOTH candidate losses (Lv1, Lv2), mark the smaller one `← controls`, and the larger one `(not used)`. Implements spec §4.1 2-inflow row + main spec §1.4.

## Preconditions

- Prior tasks: task-11, task-27, task-29.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `ledger-render` sentinel block after task-29:

```js
  // --- Two-inflow detail (task-30) ---

  function renderTwoInflowDetail(row) {
    const d = row.detail;
    const res = d.result;
    const cands = res.candidateLosses || [];
    if (cands.length !== 2) return csWarn("Expected 2 candidate losses, got " + cands.length);

    const candTable = el("table", { style: "font-family:ui-monospace,monospace; font-size:12px; border-collapse:collapse;" }, [
      el("tr", { style: "border-bottom:1px solid #999;" }, [
        el("th", { style: "padding:3px 10px; text-align:left;" }, "angle"),
        el("th", { style: "padding:3px 10px; text-align:right;" }, "V_i/3"),
        el("th", { style: "padding:3px 10px; text-align:right;" }, "Kb(angle)"),
        el("th", { style: "padding:3px 10px; text-align:right;" }, "Lv = Kb·V²/(2g)"),
        el("th", { style: "padding:3px 10px;" }, "")
      ])
    ]);
    // Derive the marker from the loss itself, not `isControlling`: when both
    // inflows share an angle the engine marks both true, which would label the
    // larger loss "smaller".
    const minLv = Math.min(cands[0].Lv, cands[1].Lv);
    for (const c of cands) {
      const marker = c.Lv === minLv
        ? el("span", { style: "color:#0a7a0a; font-weight:700;" }, "← controls (smaller)")
        : el("span", { style: "color:#999;" }, "(not used)");
      candTable.appendChild(el("tr", { style: "border-bottom:1px dotted #ccc;" }, [
        el("td", { style: "padding:3px 10px;" }, fmtNum(c.angle, 1) + "°"),
        el("td", { style: "padding:3px 10px; text-align:right;" }, fmtNum(c.V, 3)),
        el("td", { style: "padding:3px 10px; text-align:right;" }, fmtNum(c.Kb, 3)),
        el("td", { style: "padding:3px 10px; text-align:right;" }, fmtNum(c.Lv, 4)),
        el("td", { style: "padding:3px 10px;" }, marker)
      ]));
    }

    return el("div", null, [
      csSection("two inflows — controlling-angle method", el("div", { style: "font-size:12px; color:#444; margin-bottom:6px;" }, [
        "Compute Lv = Kb·V²/(2g) for each inflow using that inflow's partial velocity (V_i/3 = Q_i / A_out). ",
        el("b", null, "The SMALLER of the two Lv's picks the controlling angle θc."),
        " (The counter-intuitive detail: smaller Lv → θc, not larger. Per main spec §1.4.)"
      ])),
      candTable,
      csSection("controlling angle", csFormula(
        "θc  (angle giving the SMALLER Lv)",
        null,
        fmtNum(res.thetaControlling, 1), "°"
      )),
      csSection("Hb at the structure", csFormula(
        "Hb = Kb(θc) · V_out²/(2g)",
        fmtNum(res.kbUsed, 3) + " · " + fmtNum(velocityHead(d.Aout > 0 ? d.Qtotal / d.Aout : 0), 4),
        fmtNum(res.Hb, 4), "ft"
      )),
      csResult("Hb", fmtNum(res.Hb, 4), "ft")
    ]);
  }
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [
    { id: "A", type: "manhole" },
    { id: "B1", type: "manhole" }, { id: "B2", type: "manhole" },
    { id: "OUT", type: "outfall" }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18, n: 0.013, slope: 0.005, length: 100, angle: 0, designQ: 8 },
    { id: "PA1", fromId: "B1", toId: "A", shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 100, angle: 10, designQ: 6 },
    { id: "PA2", fromId: "B2", toId: "A", shape: "circular", size: 12, n: 0.013, slope: 0.005, length: 100, angle: 60, designQ: 2 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "structure", id: "A", pathStack: ["OUT", "P1", "A"] };
state.ui.mode = "explore";
renderLedger();

const host = document.getElementById("ledger");
console.assert(host.textContent.includes("controlling-angle method"), "section rendered");
console.assert(host.textContent.includes("controls (smaller)"), "controls marker rendered");
console.assert(host.textContent.includes("(not used)"), "not-used marker rendered");

// The controlling angle in this setup is 60° (B2, smaller Lv) per main spec §1.4.
// Test the table rendered B2's angle marked as controlling, not B1's.
// (This test relies on structureLoss's output; just check the text.)
const text = host.textContent;
const i60 = text.indexOf("60.0");
const i10 = text.indexOf("10.0");
console.assert(i60 > 0 && i10 > 0, "both angles present in output");
// The 'controls (smaller)' string should be closer to the 60° row than the 10° row.
const iCtrl = text.indexOf("controls (smaller)");
console.assert(Math.abs(iCtrl - i60) < Math.abs(iCtrl - i10), "60° marked as controlling (smaller Lv)");

// Duplicate angles: the engine marks both candidates controlling, but the table
// must still label only the smaller loss as controlling.
state.imported.pipes.find((p) => p.id === "PA2").angle = 10;
renderLedger();
const text2 = host.textContent;
const first = text2.indexOf("controls (smaller)");
console.assert(first >= 0 && text2.indexOf("controls (smaller)", first + 1) === -1,
  "duplicate angles still mark exactly one controlling candidate");
console.assert(text2.includes("(not used)"), "larger duplicate-angle loss marked not used");

console.log("task-30 two-inflow detail: OK");
```

## Done when

- `renderTwoInflowDetail` defined.
- Two-inflow ledger row renders both candidate rows, with the smaller marked `← controls (smaller)` and the larger marked `(not used)`.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-30 two-inflow controlling-angle detail`.

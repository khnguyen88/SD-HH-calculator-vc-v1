# Task 28: Expanded Hf row — formula with substituted numbers

## Context

Render the full Manning friction loss derivation for a `+Hf` ledger row: A, R, Sf, Hf, EGL_up — each with symbolic form and substituted numbers. Includes an editable form in edit mode. Implements spec §4.1 `+Hf row`.

## Preconditions

- Prior tasks: task-01, task-03, task-09, task-12, task-23, task-24, task-27.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `ledger-render` sentinel block after task-27:

```js
  // --- Hf row expanded render (task-28) ---

  function renderHfRow(row) {
    const d = row.detail;
    const isEdit = state.ui.mode === "edit";
    const inp = (field, step) => isEdit
      ? editableNumber(row.id, field, state.imported, state.overrides, { step })
      : el("span", { style: "font-family:ui-monospace,monospace;" }, fmtNum(resolveField(row.id, field, state.imported, state.overrides), 3));

    return el("div", null, [
      csSection("inputs", el("table", { style: "font-family:ui-monospace,monospace; font-size:12px;" }, [
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "Q (cfs)"), el("td", null, fmtNum(d.designQ, 2))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "n"), el("td", null, inp("n", "0.001"))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "slope (ft/ft)"), el("td", null, inp("slope", "0.0001"))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "length (ft)"), el("td", null, inp("length", "0.1"))]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "shape"), el("td", null, d.shape)]),
        el("tr", null, [el("td", { style: "padding:2px 8px;" }, "size"), el("td", null, isEdit
          ? editableNumber(row.id, "size", state.imported, state.overrides, { step: 3 })
          : String(d.size))])
      ])),
      csSection("hydraulics", el("div", null, [
        csFormula("A", fmtNum(d.A, 4), fmtNum(d.A, 4), "ft²"),
        csFormula("R", fmtNum(d.R, 4), fmtNum(d.R, 4), "ft")
      ])),
      csSection("friction slope", csFormula(
        "Sf = (Q·n / (1.486·A·R^(2/3)))²",
        "(" + fmtNum(d.designQ, 2) + "·" + fmtNum(d.n, 3) + " / (1.486·" + fmtNum(d.A, 3) + "·" + fmtNum(d.R, 3) + "^(2/3)))²",
        fmtNum(d.Sf, 6),
        "ft/ft"
      )),
      csSection("friction loss", csFormula(
        "Hf = Sf · L",
        fmtNum(d.Sf, 6) + " · " + fmtNum(d.length, 2),
        fmtNum(d.Hf, 3),
        "ft"
      )),
      csResult("EGL_up = EGL_dn + Hf = " + fmtNum(row.before, 3) + " + " + fmtNum(d.Hf, 3), fmtNum(row.after, 3), "ft")
    ]);
  }
```

## Acceptance test

In DevTools console:

```js
state.imported = {
  structures: [{ id: "OUT", type: "outfall" }, { id: "A", type: "bend" }],
  pipes: [{ id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
           n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.4 }],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};
state.overrides = { byId: {} };
state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
state.ui.mode = "explore";
renderLedger();

const host = document.getElementById("ledger");
console.assert(host.textContent.includes("Sf"), "Sf label present");
console.assert(host.textContent.includes("A ="), "A formula present");
console.assert(host.textContent.includes("1.486"), "symbolic form present");
console.assert(host.textContent.includes("EGL_up"), "EGL_up line present");

// Edit mode: inputs appear
state.ui.mode = "edit";
renderLedger();
const inputs = host.querySelectorAll("input[type='number']");
console.assert(inputs.length >= 3, "expected ≥3 numeric inputs (n, slope, length) in edit mode, got " + inputs.length);

console.log("task-28 hf row: OK");
```

## Done when

- `renderHfRow` defined.
- Expanded Hf shows A, R, Sf, Hf, EGL_up with substituted numbers.
- Edit mode renders editable inputs for n, slope, length, size.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-28 expanded Hf row with substituted formulas`.

# task-30-01 — TR-55 detail sheet formulas: substitute actual values

## Context

Spec §1B.6 requires the TR-55 calc sheet to show "the governing formula with substituted
numbers." All other detail sheets (drainage, pipe, HGL, outlet stage) already do this.
`buildTr55Sheet()` is the only one that shows bare templates like
`"Tt = 0.007(nL)^0.8 / (P2^0.5 × s^0.4)"`.

## Preconditions

- `drainage-calculator/storm-drain-design-calculator-dev.html` exists.
- Seeded example DA-1 uses `tcMethod:"tr55"` with one sheet-flow segment.

## Exact changes

**File:** `drainage-calculator/storm-drain-design-calculator-dev.html`

Locate `function buildTr55Sheet(row){` (~line 5200). Inside the `segs.forEach` loop,
find the block that builds `formulaLines` and replaces it.

**Find this block** (lines ~5226-5232):
```js
    const formulaLines = seg.type==="sheet" ? ["Tt = 0.007(nL)^0.8 / (P2^0.5 × s^0.4)"]
      : seg.type==="shallow" ? ["V = Cp × √s", "Tt = L / (3600 × V)"]
      : ["r = a / Pw", "V = (1.486/n) × r^(2/3) × s^0.5", "Tt = L / (3600 × V)"];
    const resultsBody = [csTable(rows), csFormula(formulaLines)];
```

**Replace with:**
```js
    let formulaLines;
    const f4 = v => fmt(v, 4), f3 = v => fmt(v, 3), f0 = v => fmt(v, 0);
    if (seg.type === "sheet") {
      const n_ = parseFloat(seg.n), L_ = parseFloat(seg.L),
            s_ = parseFloat(seg.s), P2_ = parseFloat(seg.P2);
      formulaLines = [
        "Tt = 0.007(×n×L)^0.8 / (P2^0.5 × s^0.4)",
        "Tt = 0.007(" + f3(n_) + "×" + f0(L_) + ")^0.8 / (" +
          f3(P2_) + "^0.5 × " + f4(s_) + "^0.4) = " + f4(r.tt) + " hr",
      ];
    } else if (seg.type === "shallow") {
      const Cp = (sdc_tr55ShallowCp(seg.surface)||0);
      const s_ = parseFloat(seg.s), L_ = parseFloat(seg.L);
      formulaLines = [
        "V = Cp × √s  =  " + f3(Cp) + " × √" + f4(s_) + " = " + f3(r.V||0) + " fps",
        "Tt = L / (3600 × V)  =  " + f0(L_) + " / (3600 × " + f3(r.V||0) + ") = " + f4(r.tt) + " hr",
      ];
    } else {
      const L_ = parseFloat(seg.L), s_ = parseFloat(seg.s),
            n_ = parseFloat(seg.n);
      formulaLines = [
        "r = a / Pw  =  " + f3(parseFloat(seg.area)||0) + " / " + f3(parseFloat(seg.wp)||0) + " = " + f3(r.r||0) + " ft",
        "V = (1.486/n) × r^(2/3) × s^0.5  =  (1.486/" + f3(n_) + ") × " +
          f3(r.r||0) + "^(2/3) × " + f4(s_) + "^0.5 = " + f3(r.V||0) + " fps",
        "Tt = L / (3600 × V)  =  " + f0(L_) + " / (3600 × " + f3(r.V||0) + ") = " + f4(r.tt) + " hr",
      ];
    }
    const resultsBody = [csTable(rows), csFormula(formulaLines)];
```

**Also add this helper** immediately before `function buildTr55Sheet(row){`:
```js
function sdc_tr55ShallowCp(surfaceKey){
  const entry = TR55_SHALLOW_CP[surfaceKey] || TR55_SHALLOW_CP.unpaved;
  return entry ? entry.Cp : 0;
}
```

> Note: `TR55_SHALLOW_CP` already exists in the file and each entry has a `.Cp` numeric
> property.  Check the actual shape in the app by searching for `TR55_SHALLOW_CP` near
> line ~1753. If the property is named differently (e.g. `.cp` lowercase), adjust the
> helper accordingly before saving.

## Build step

```
node drainage-calculator/build.js
```

Expected: success message, no errors.

## Acceptance test

**Manual check (open the built file):**

1. Load `drainage-calculator/storm-drain-design-calculator.html`.
2. Click the **Drainage Area** tab.
3. Find row **DA-1** (the seeded example with `tcMethod="tr55"`).
4. Click its **⤢ Detail** button.
5. In the modal, the TR-55 segment section must show a formula like:
   `Tt = 0.007(0.24 × 200)^0.8 / (3.60^0.5 × 0.0100^0.4) = 0.3215 hr`
   (actual numbers depend on the seeded segment values — the key is that real numbers
   appear, not the placeholder variable names n, L, s, P2).
6. The "Total" section at the bottom still shows Tc in both hours and minutes.

## Done when

- Build succeeds.
- TR-55 detail sheet shows substituted formula strings for all three segment types.
- Other detail sheets (drainage, pipe, HGL) are unaffected.

# Task 13: HGL method toggle (HEC-22 vs Legacy both-crown)

## Context

Compute the HGL value at each ledger row given the row's EGL. HEC-22 just subtracts the velocity head; Legacy additionally pins HGL at the upstream crown if it would otherwise fall below. Implements spec §4.2.

Both modes compute `EGL_up` identically in `buildLedger` (task-12); this task only differs in how HGL is derived at each step.

## Preconditions

- Prior tasks: task-01, task-03, task-08, task-09, task-10, task-11, task-12.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-12:

```js
  // --- HGL derivation (task-13) ---

  // Given an EGL value at a station and the pipe context there, return HGL.
  //   V_fps:      velocity in the relevant pipe at that station
  //   crown_ft:   upstream crown elevation (only used for Legacy clamp)
  //   method:     "hec22" | "legacy-both-crown"
  //   Returns { hgl, clamped } — clamped=true means the Legacy crown floor fired.
  function hglAt(EGL, V_fps, crown_ft, method) {
    const base = EGL - velocityHead(V_fps);
    if (method === "legacy-both-crown" && typeof crown_ft === "number" && isFinite(crown_ft)) {
      if (base < crown_ft) return { hgl: crown_ft, clamped: true };
    }
    return { hgl: base, clamped: false };
  }

  // Convenience: annotate each ledger row with hgl value for the method in use.
  // Does NOT mutate the row; returns a new array of rows with .hgl and .hglClamped added.
  function annotateLedgerHgl(rows, resolvedState, method) {
    const imp = resolvedState.imported;
    const ovr = resolvedState.overrides;
    return rows.map((row) => {
      if (row.kind === "start") {
        return Object.assign({}, row, { hgl: row.after, hglClamped: false });
      }
      // Determine the relevant pipe + velocity at this row's position.
      // For an hf row the velocity is this pipe's velocity; for hb row it's the OUTFLOW pipe's velocity.
      let V = 0, crown = null;
      if (row.kind === "hf") {
        const d = row.detail;
        V = (d.A > 0) ? (d.designQ / d.A) : 0;
        // Crown at the upstream end of this pipe = toStructure.crown + its rise; here we just use the pipe's To-structure crown.
        const pipe = imp.pipes.find((p) => p.id === row.id);
        const toStr = pipe ? imp.structures.find((s) => s.id === pipe.toId) : null;
        crown = toStr ? resolveField(toStr.id, "crown", imp, ovr) : null;
      } else if (row.kind === "hb") {
        const d = row.detail;
        V = (d.Aout > 0) ? (d.Qtotal / d.Aout) : 0;
        crown = resolveField(row.id, "crown", imp, ovr);
      } else {
        // end row
        V = 0;
      }
      const { hgl, clamped } = hglAt(row.after, V, crown, method);
      return Object.assign({}, row, { hgl, hglClamped: clamped });
    });
  }
```

## Acceptance test

In DevTools console (assumes task-12 setup is still in `state`):

```js
// HEC-22: HGL = EGL − V²/(2g), no crown floor.
let r = hglAt(102.5, 10, 101.0, "hec22");
console.assert(Math.abs(r.hgl - (102.5 - 10*10/(2*32.2))) < 1e-12, "hec22 hgl");
console.assert(r.clamped === false, "hec22 never clamps");

// Legacy: EGL − V²/(2g) = 101.95, crown = 102.0 → clamp to 102.0
r = hglAt(102.5, 6, 102.0, "legacy-both-crown");
console.assert(r.hgl === 102.0 && r.clamped === true, "legacy clamp");

// Legacy: same EGL, lower crown = 101.0 → no clamp, hgl = 101.95
r = hglAt(102.5, 6, 101.0, "legacy-both-crown");
console.assert(r.clamped === false, "legacy no-clamp");

// annotateLedgerHgl smoke
state.imported = {
  structures: [
    { id: "OUT", type: "outfall", crown: 99 },
    { id: "A",   type: "bend",    crown: 101 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 0, designQ: 8.4 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 },
  kbTable: null
};
state.overrides = { byId: {} };
const rows = buildLedger(["OUT", "P1", "A"], state, null, "hec22");
const annotated = annotateLedgerHgl(rows, state, "hec22");
console.assert(annotated.length === rows.length, "annotate preserves row count");
console.assert(typeof annotated[1].hgl === "number", "hf row has hgl");

console.log("task-13 hgl method: OK");
```

## Done when

- `hglAt` and `annotateLedgerHgl` defined in the `compute` sentinel block.
- Smoke test prints `OK`.
- Legacy clamp fires only when base < crown and method is `legacy-both-crown`.
- Build still succeeds.
- Commit: `feat(visualizer): task-13 HGL method toggle with Legacy crown clamp`.

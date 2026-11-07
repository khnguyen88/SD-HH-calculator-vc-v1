# Task 13: HGL method toggle (HEC-22 vs Legacy both-crown)

## Context

Compute the HGL value at each ledger row given the row's EGL. Implements spec §4.2
and matches the golden reference in `docs/superpowers/plans/2026-11-06-bburg-xlsx-redesign.md`
(`hgl_walk_step`, lines ~503-604):

- Both methods share the **downstream crown floor**: `HGL_dn = max(EGL_dn − V²/(2g), Crown_dn)`.
- HEC-22: `HGL_up = HGL_dn + Hf` — no upstream crown floor.
- Legacy: `HGL_up = max(HGL_dn + Hf, Crown_up)`.

Both modes compute `EGL_up` identically in `buildLedger` (task-12); this task only
differs in how HGL is derived at each step. The earlier draft of this task used a
stateless per-row `HGL = EGL − V²/(2g)` with no downstream floor for HEC-22; that
contradicted spec §4.2 and the bburg reference and has been replaced.

## Preconditions

- Prior tasks: task-01, task-03, task-08, task-09, task-10, task-11, task-12.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-12:

```js
  // --- HGL derivation (task-13) ---

  // One pipe step per bburg reference_calcs.hgl_walk_step and spec §4.2:
  //   both methods: HGL_dn = max(EGL_dn - V^2/(2g), Crown_dn)
  //   hec22:        HGL_up = HGL_dn + Hf
  //   legacy:       HGL_up = max(HGL_dn + Hf, Crown_up)
  // Returns { hglDn, hglUp, clamped } — clamped means a crown floor fired.
  function hglWalkStep(EGL_dn, V_fps, crownDn, crownUp, Hf, method) {
    const hglDnRaw = EGL_dn - velocityHead(V_fps);
    const hglDn = (crownDn == null) ? hglDnRaw : Math.max(hglDnRaw, crownDn);
    const hglUpRaw = hglDn + Hf;
    const hglUp = (method === "legacy-both-crown" && crownUp != null)
      ? Math.max(hglUpRaw, crownUp) : hglUpRaw;
    return { hglDn, hglUp, clamped: Math.abs(hglUp - (hglDnRaw + Hf)) > 1e-12 };
  }

  // Annotate each ledger row with HGL. Does not mutate rows.
  //   start row:      HGL = max(TW, outfall crown) — downstream boundary floor.
  //   +Hf row:        hglWalkStep using EGL at the downstream node.
  //   +Hb row:        HGL carries the previous value plus the structure loss.
  function annotateLedgerHgl(rows, resolvedState, method) {
    const imp = resolvedState.imported;
    const ovr = resolvedState.overrides;
    const legacy = method === "legacy-both-crown";
    const crownOf = (id) => {
      const crown = resolveField(id, "crown", imp, ovr);
      return (typeof crown === "number" && isFinite(crown)) ? crown : null;
    };

    const out = [];
    let hgl = null;
    for (const row of rows) {
      if (row.kind === "start") {
        const crown = crownOf(row.id);
        hgl = (crown == null) ? row.after : Math.max(row.after, crown);
        out.push(Object.assign({}, row, { hgl, hglClamped: hgl !== row.after }));
        continue;
      }

      if (row.kind === "hf") {
        const d = row.detail;
        const q = (typeof d.designQ === "number" && isFinite(d.designQ)) ? d.designQ : 0;
        const V = (d.A > 0) ? (q / d.A) : 0;
        const pipe = imp.pipes.find((p) => p.id === row.id);
        const step = hglWalkStep(row.before, V,
          pipe ? crownOf(pipe.toId) : null,
          pipe ? crownOf(pipe.fromId) : null,
          row.delta, method);
        hgl = step.hglUp;
        out.push(Object.assign({}, row, { hgl, hglClamped: step.clamped }));
        continue;
      }

      if (row.kind === "hb") {
        const rawUp = (hgl == null ? row.before : hgl) + row.delta;
        const crown = crownOf(row.id);
        const up = (legacy && crown != null) ? Math.max(rawUp, crown) : rawUp;
        hgl = up;
        out.push(Object.assign({}, row, { hgl, hglClamped: up !== rawUp }));
        continue;
      }

      out.push(Object.assign({}, row, {
        hgl: hgl == null ? row.after : hgl,
        hglClamped: false
      }));
    }
    return out;
  }
```

## Acceptance test

In DevTools console (assumes task-12 setup is still in `state`):

```js
// Direct step, V = 0 isolates the crown floors.
let r = hglWalkStep(93.0, 0, 96.0, 97.0, 0.05, "hec22");
console.assert(Math.abs(r.hglDn - 96.0) < 1e-12, "hec22 d/s crown floor");
console.assert(Math.abs(r.hglUp - 96.05) < 1e-12, "hec22 no u/s floor");
console.assert(r.clamped === true, "hec22 floor reported");

r = hglWalkStep(93.0, 0, 96.0, 97.0, 0.05, "legacy-both-crown");
console.assert(Math.abs(r.hglDn - 96.0) < 1e-12, "legacy d/s crown floor");
console.assert(Math.abs(r.hglUp - 97.0) < 1e-12, "legacy u/s crown floor");

r = hglWalkStep(100.0, 0, 96.0, 96.5, 0.2, "legacy-both-crown");
console.assert(Math.abs(r.hglUp - 100.2) < 1e-12 && r.clamped === false, "pressurized: no floor");

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
console.assert(Math.abs(annotated[0].hgl - 100) < 1e-12, "start HGL = max(TW, outfall crown)");
console.assert(typeof annotated[1].hgl === "number", "hf row has hgl");
const legacyRows = annotateLedgerHgl(rows, state, "legacy-both-crown");
console.assert(legacyRows[1].hgl >= annotated[1].hgl, "legacy never below hec22");

console.log("task-13 hgl method: OK");
```

## Done when

- `hglWalkStep` and `annotateLedgerHgl` defined in the `compute` sentinel block.
- Smoke test prints `OK`.
- HEC-22 applies the downstream crown floor and no upstream floor.
- Legacy additionally clamps `HGL_up` at `Crown_up`.
- Build still succeeds.
- Commit: `feat(visualizer): task-13 HGL method toggle with crown floors`.

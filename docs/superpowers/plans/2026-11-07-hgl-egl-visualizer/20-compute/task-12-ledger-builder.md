# Task 12: Ledger builder

## Context

Build the ledger from the current walk path. Pure function — takes the path and resolved state, returns an array of row objects. Each row carries enough detail to render both the collapsed one-liner and the expanded formula view. Implements spec §7.4 and §4.1.

## Preconditions

- Prior tasks: task-01, task-03, task-08, task-09, task-10, task-11.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-11:

```js
  // --- Ledger builder (task-12) ---

  // Resolve one field: override if present, else imported.
  function resolveField(id, field, imported, overrides) {
    const ov = overrides && overrides.byId && overrides.byId[id];
    if (ov && Object.prototype.hasOwnProperty.call(ov, field)) return ov[field];
    const el = (imported.structures.find((s) => s.id === id)
             || imported.pipes.find((p) => p.id === id));
    return el ? el[field] : undefined;
  }

  // Build an ordered list of ledger rows.
  //   path: array of elementIds in walk order, starting with the outfall structureId.
  //   resolvedState: { imported, overrides } — pass state directly.
  //   kbTable: typically state.imported.kbTable (null → seed).
  //   hglMethod: "hec22" | "legacy-both-crown".
  function buildLedger(path, resolvedState, kbTable, hglMethod) {
    if (!path || path.length === 0) return [];
    const rows = [];
    const imp = resolvedState.imported;
    const ovr = resolvedState.overrides;

    // Start row
    const tw = imp.outfall.tailwaterElev;
    let EGL = tw;
    rows.push({ kind: "start", id: imp.outfall.structureId, label: imp.outfall.structureId,
                before: null, delta: null, after: EGL,
                detail: { tailwaterElev: tw } });

    // Walk pairs: each (structure -> pipe) adds an Hb row; each pipe adds an Hf row.
    // We expect the path to alternate: [outfallSid, pipeId, structureId, pipeId, structureId, ...].
    // The first Hb at the outfall structure is nominal (0 inflows, tailwater is set).
    for (let i = 1; i < path.length; i++) {
      const id = path[i];
      const pipe = imp.pipes.find((p) => p.id === id);
      if (pipe) {
        // +Hf row
        const n = resolveField(id, "n", imp, ovr);
        const slope = resolveField(id, "slope", imp, ovr);
        const length = resolveField(id, "length", imp, ovr);
        const shape = resolveField(id, "shape", imp, ovr);
        const size = resolveField(id, "size", imp, ovr);
        const designQ = resolveField(id, "designQ", imp, ovr);
        const A = pipeArea(shape, size);
        const R = pipeRadius(shape, size);
        const Sf = frictionSlope(designQ, n, A, R);
        const Hf = frictionLoss(Sf, length);
        const before = EGL; EGL = EGL + Hf;
        rows.push({ kind: "hf", id, label: id, before, delta: Hf, after: EGL,
                    detail: { n, slope, length, shape, size, A, R, Sf, Hf, designQ } });
      } else {
        // +Hb row
        const str = imp.structures.find((s) => s.id === id);
        if (!str) continue;
        const structureType = resolveField(id, "type", imp, ovr) || "manhole";
        // Find inflows: imp.pipes where toId == id. Angles may be overridden per-pipe.
        const inflowPipes = imp.pipes.filter((p) => p.toId === id);
        const inflows = inflowPipes.map((p) => ({
          angleDeg: resolveField(p.id, "angle", imp, ovr) || 0,
          Qcfs:     resolveField(p.id, "designQ", imp, ovr) || 0,
          pipeId:   p.id
        }));
        // Outflow pipe: the pipe whose fromId == this structure's id (take the first).
        const outPipe = imp.pipes.find((p) => p.fromId === id);
        const Aout = outPipe
          ? pipeArea(resolveField(outPipe.id, "shape", imp, ovr),
                     resolveField(outPipe.id, "size", imp, ovr))
          : 0;
        const Qtotal = outPipe ? (resolveField(outPipe.id, "designQ", imp, ovr) || 0) : 0;
        const res = structureLoss(inflows, Qtotal, Aout, structureType, kbTable);
        const before = EGL;
        const delta = res.error ? 0 : res.Hb;
        EGL = EGL + delta;
        rows.push({ kind: "hb", id, label: id, before, delta, after: EGL,
                    detail: { structureType, inflows, Qtotal, Aout, result: res } });
      }
    }

    // End row
    const endId = path[path.length - 1];
    rows.push({ kind: "end", id: endId, label: endId,
                before: tw, delta: EGL - tw, after: EGL,
                detail: { totalRise: EGL - tw } });

    return rows;
  }
```

## Acceptance test

In DevTools console (after seeding state manually):

```js
state.imported = {
  structures: [
    { id: "OUT", type: "outfall" },
    { id: "A",   type: "bend" }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle: 30, designQ: 8.4 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 },
  kbTable: null
};
state.overrides = { byId: {} };

const rows = buildLedger(["OUT", "P1", "A"], state, null, "hec22");
console.assert(rows.length === 4, "expected 4 rows (start, hf, hb, end), got " + rows.length);
console.assert(rows[0].kind === "start" && rows[0].after === 100, "start row");
console.assert(rows[1].kind === "hf", "hf row");
console.assert(Math.abs(rows[1].delta - frictionLoss(frictionSlope(8.4, 0.013, pipeAreaCircular(18), pipeRadiusCircular(18)), 120)) < 1e-12, "hf delta");
console.assert(rows[2].kind === "hb" && rows[2].id === "A", "hb row");
console.assert(rows[3].kind === "end", "end row");
console.assert(rows[3].detail.totalRise === rows[3].after - 100, "total rise matches");

// Overrides should affect the ledger
state.overrides.byId["P1"] = { slope: 0.01 };
// Note: slope doesn't enter frictionSlope directly (we use Q, not velocity), so this is an
// example of an override that would matter if slope-dependent partial-flow were added.
// For now, override length instead to see the difference.
state.overrides.byId["P1"] = { length: 240 };
const rows2 = buildLedger(["OUT", "P1", "A"], state, null, "hec22");
console.assert(Math.abs(rows2[1].delta - 2 * rows[1].delta) < 1e-9, "override length doubles Hf: " + rows2[1].delta + " vs " + rows[1].delta);

console.log("task-12 ledger: OK");
```

## Done when

- `resolveField` and `buildLedger` defined in the `compute` sentinel block.
- Smoke test prints `OK`.
- Ledger reflects overrides (the length-override assertion passes).
- Build still succeeds.
- Commit: `feat(visualizer): task-12 ledger builder`.

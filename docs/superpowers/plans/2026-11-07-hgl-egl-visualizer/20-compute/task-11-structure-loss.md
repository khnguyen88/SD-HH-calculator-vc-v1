# Task 11: Structure loss (controlling-angle method)

## Context

Implement `outletVelocity`, `velocityHead`, and `structureLoss` per spec §7.3 and main spec §1.4. The 2-inflow branch uses the controlling-angle method where **the SMALLER of the two candidate losses picks θc** — not the larger. This is counter-intuitive and tested explicitly.

## Preconditions

- Prior tasks: task-01, task-03, task-08, task-09, task-10.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-10:

```js
  // --- Structure loss (task-11) ---

  const G_FT = 32.2;

  function outletVelocity(Q_total_cfs, Aout_sf) {
    if (!(isFinite(Q_total_cfs) && isFinite(Aout_sf) && Aout_sf > 0)) return 0;
    return Q_total_cfs / Aout_sf;
  }

  function velocityHead(V_fps) {
    if (!isFinite(V_fps)) return 0;
    return (V_fps * V_fps) / (2 * G_FT);
  }

  // Structure loss per main spec §1.4.
  //   inflows:   array of {angleDeg, Qcfs}, length 0..2 (length 3+ returns {error}).
  //   Qtotal:    total flow through the structure (cfs) — used for Vout.
  //   Aout_sf:   outflow pipe's full-flow area (sf).
  //   structureType: "inlet"|"manhole"|"bend"|"junction"|"splitter".
  //   kbTable:   editable Kb lookup (or null to use KB_SEED).
  //
  // Returns:
  //   { Hb, kbUsed, thetaControlling, candidateLosses }
  //   - For >2 inflows: { error: "too-many-inflows" }.
  function structureLoss(inflows, Qtotal_cfs, Aout_sf, structureType, kbTable) {
    if (!Array.isArray(inflows)) return { error: "inflows-not-array" };
    if (inflows.length > 2) return { error: "too-many-inflows" };

    // Coerce inflow fields defensively (main-app parity: parseFloat(angle) || 0).
    // Missing/NaN angles fall back to 0° so kbAt clamps to the 5° row (Kb 0.06)
    // instead of falling through to the last row; null inflows are tolerated.
    const angleOf = (inf) => {
      const a = Number(inf && inf.angleDeg);
      return isFinite(a) ? a : 0;
    };
    const qOf = (inf) => {
      const q = Number(inf && inf.Qcfs);
      return isFinite(q) ? q : 0;
    };

    const Vout = outletVelocity(Qtotal_cfs, Aout_sf);
    const Hvout = velocityHead(Vout);

    if (inflows.length === 0) {
      const Kb = kbAt(0, structureType, kbTable);
      return { Hb: Kb * Hvout, kbUsed: Kb, thetaControlling: 0, candidateLosses: [] };
    }

    if (inflows.length === 1) {
      const angle = angleOf(inflows[0]);
      const Kb = kbAt(angle, structureType, kbTable);
      return { Hb: Kb * Hvout, kbUsed: Kb, thetaControlling: angle, candidateLosses: [] };
    }

    // length === 2 — controlling angle method
    const [a, b] = inflows;
    const aAngle = angleOf(a);
    const bAngle = angleOf(b);
    const V1_3 = (Aout_sf > 0) ? (qOf(a) / Aout_sf) : 0;
    const V2_3 = (Aout_sf > 0) ? (qOf(b) / Aout_sf) : 0;
    const Kb_a = kbAt(aAngle, structureType, kbTable);
    const Kb_b = kbAt(bAngle, structureType, kbTable);
    const Lv1 = Kb_a * velocityHead(V1_3);
    const Lv2 = Kb_b * velocityHead(V2_3);
    // CRITICAL: the SMALLER candidate loss picks the controlling angle.
    const thetaC = (Lv1 > Lv2) ? bAngle : aAngle;
    const Kb = kbAt(thetaC, structureType, kbTable);
    return {
      Hb: Kb * Hvout,
      kbUsed: Kb,
      thetaControlling: thetaC,
      candidateLosses: [
        { angle: aAngle, Lv: Lv1, V: V1_3, Kb: Kb_a, isControlling: thetaC === aAngle },
        { angle: bAngle, Lv: Lv2, V: V2_3, Kb: Kb_b, isControlling: thetaC === bAngle }
      ]
    };
  }
```

## Acceptance test

In DevTools console:

```js
// 0-inflow (headwater): Kb at 0°, which clamps to 5°→0.06.
// Qtotal=5, Aout=1.77 → Vout=2.825 fps → Hvout=0.1239 ft → Hb ≈ 0.00744 ft
let r = structureLoss([], 5.0, pipeAreaCircular(18), "manhole", KB_SEED);
console.assert(Math.abs(r.Hb - 0.06 * velocityHead(5.0 / pipeAreaCircular(18))) < 1e-12, "0-inflow Hb");
console.assert(r.thetaControlling === 0, "0-inflow theta");

// 1-inflow at 30°: Kb=0.35
r = structureLoss([{ angleDeg: 30, Qcfs: 5.0 }], 5.0, pipeAreaCircular(18), "manhole", KB_SEED);
console.assert(Math.abs(r.Hb - 0.35 * velocityHead(5.0 / pipeAreaCircular(18))) < 1e-12, "1-inflow Hb");
console.assert(r.thetaControlling === 30, "1-inflow theta");

// 2-inflow controlling-angle counter-example:
//   Aout=1.767 sf.
//   Inflow A: angle=10°, Q=6 cfs → V=3.39 → Hv=0.179 → Lv1=0.13·0.179 = 0.0233
//   Inflow B: angle=60°, Q=2 cfs → V=1.13 → Hv=0.020 → Lv2=0.56·0.020 = 0.0112
//   Lv1 > Lv2 → SMALLER is Lv2 → thetaC = B's angle = 60°
r = structureLoss(
  [{ angleDeg: 10, Qcfs: 6 }, { angleDeg: 60, Qcfs: 2 }],
  8, pipeAreaCircular(18), "manhole", KB_SEED);
console.assert(r.thetaControlling === 60, "controlling: expected 60, got " + r.thetaControlling);
console.assert(r.candidateLosses[0].isControlling === false, "A should NOT control");
console.assert(r.candidateLosses[1].isControlling === true, "B should control");

// 3+ inflows → error
r = structureLoss(
  [{ angleDeg: 10, Qcfs: 1 }, { angleDeg: 30, Qcfs: 2 }, { angleDeg: 50, Qcfs: 3 }],
  6, pipeAreaCircular(18), "manhole", KB_SEED);
console.assert(r.error === "too-many-inflows", "3-inflow should error");

console.log("task-11 structure loss: OK");
```

## Done when

- `G_FT`, `outletVelocity`, `velocityHead`, `structureLoss` defined.
- Smoke test prints `OK`.
- The controlling-angle counter-example passes (this is the single most important assertion in the test).
- Build still succeeds.
- Commit: `feat(visualizer): task-11 controlling-angle structure loss`.

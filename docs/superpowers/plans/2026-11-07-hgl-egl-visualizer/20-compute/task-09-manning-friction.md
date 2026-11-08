# Task 09: Manning's friction slope and loss

## Context

Implement `frictionSlope` and `frictionLoss` per spec §7.2 and main spec §1.2. Full-flow equations only — no partial-flow handling in v1.

## Preconditions

- Prior tasks: task-01, task-03, task-08.

## Exact changes

**Modify** `visualizer/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-08:

```js
  // --- Manning's friction (task-09) ---

  // Friction slope at design Q (full-flow).
  //   Q in cfs, n unitless, A in ft², R in ft.
  //   Returns Sf in ft/ft (unitless but conceptually ft of head per ft of pipe).
  //   Formula: Sf = ( Q·n / (1.486·A·R^(2/3)) )²
  function frictionSlope(Q, n, A, R) {
    if (!(isFinite(Q) && isFinite(n) && isFinite(A) && isFinite(R))) return 0;
    if (A <= 0 || R <= 0) return 0;
    const num = Q * n;
    const den = 1.486 * A * Math.pow(R, 2 / 3);
    const ratio = num / den;
    return ratio * ratio;
  }

  // Friction loss along the pipe.  L in ft.  Returns Hf in ft.
  function frictionLoss(Sf, L) {
    if (!(isFinite(Sf) && isFinite(L))) return 0;
    return Sf * L;
  }
```

## Acceptance test

In DevTools console:

```js
// Hand-check:
//   Q = 8.4 cfs, n = 0.013, D = 18 in → A = π·(1.5)²/4 = 1.76715 ft², R = 0.375 ft
//   Sf = (8.4·0.013 / (1.486·1.76715·0.375^0.6667))²
//
//   0.375^(2/3) = 0.5192...
//   denom = 1.486 · 1.76715 · 0.5192 = 1.3636
//   num = 0.1092
//   ratio = 0.08009...
//   Sf = 0.006414... (hand-calculated to ~5 sig figs)
const Q = 8.4, n = 0.013, A = pipeAreaCircular(18), R = pipeRadiusCircular(18);
const sf = frictionSlope(Q, n, A, R);
console.assert(Math.abs(sf - 0.006414) < 0.0001, "frictionSlope 8.4 cfs: " + sf);

// Hf = Sf · L for L = 120 ft ≈ 0.77 ft
const hf = frictionLoss(sf, 120);
console.assert(Math.abs(hf - sf * 120) < 1e-12, "frictionLoss");
console.assert(Math.abs(hf - 0.770) < 0.01, "Hf 120 ft at Q=8.4: " + hf);

// Zero Q → zero Sf
console.assert(frictionSlope(0, n, A, R) === 0, "zero Q");

// NaN inputs → 0 (defensive)
console.assert(frictionSlope(NaN, n, A, R) === 0, "NaN Q");
console.assert(frictionLoss(NaN, 120) === 0, "NaN Sf");

// Degenerate geometry → 0
console.assert(frictionSlope(Q, n, 0, R) === 0, "A=0");
console.assert(frictionSlope(Q, n, A, 0) === 0, "R=0");

console.log("task-09 friction: OK");
```

## Done when

- `frictionSlope` and `frictionLoss` defined in the `compute` sentinel block.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-09 Manning friction slope and loss`.

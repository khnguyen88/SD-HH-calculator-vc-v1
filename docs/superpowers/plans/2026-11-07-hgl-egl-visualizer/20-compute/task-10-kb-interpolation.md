# Task 10: Kb lookup and linear interpolation

## Context

Define the Kb seed table (identical to main app §1.6) and `kbAt(angleDeg, structureType, kbTable)` which linearly interpolates between rows and clamps at endpoints. Implements spec §7.3 and §7.5.

## Preconditions

- Prior tasks: task-01, task-03.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Append inside the `compute` sentinel block after task-09:

```js
  // --- Kb lookup (task-10) ---

  // KB_SEED: standard AASHTO bend-loss curve (matches main app defaultKbRows(), spec §1.6).
  // 12 rows, 5° → 0.06 ... 90° → 0.70. All three columns seeded identically — users are
  // expected to override per column before using for submittal.
  const KB_SEED = [
    { angleDeg:  5,  inlet: 0.06, manhole: 0.06, bend: 0.06 },
    { angleDeg: 10,  inlet: 0.13, manhole: 0.13, bend: 0.13 },
    { angleDeg: 15,  inlet: 0.19, manhole: 0.19, bend: 0.19 },
    { angleDeg: 20,  inlet: 0.25, manhole: 0.25, bend: 0.25 },
    { angleDeg: 25,  inlet: 0.30, manhole: 0.30, bend: 0.30 },
    { angleDeg: 30,  inlet: 0.35, manhole: 0.35, bend: 0.35 },
    { angleDeg: 40,  inlet: 0.43, manhole: 0.43, bend: 0.43 },
    { angleDeg: 50,  inlet: 0.50, manhole: 0.50, bend: 0.50 },
    { angleDeg: 60,  inlet: 0.56, manhole: 0.56, bend: 0.56 },
    { angleDeg: 70,  inlet: 0.61, manhole: 0.61, bend: 0.61 },
    { angleDeg: 80,  inlet: 0.66, manhole: 0.66, bend: 0.66 },
    { angleDeg: 90,  inlet: 0.70, manhole: 0.70, bend: 0.70 }
  ];

  // Linear interpolation across the Kb table, clamping at endpoints.
  //   structureType ∈ "inlet" | "manhole" | "bend" (junction/splitter also map to bend/manhole upstream).
  function kbAt(angleDeg, structureType, kbTable) {
    const col = (structureType === "inlet") ? "inlet"
              : (structureType === "manhole") ? "manhole"
              : (structureType === "bend") ? "bend"
              : (structureType === "junction") ? "bend"
              : (structureType === "splitter") ? "manhole"
              : "manhole";
    const table = (kbTable && kbTable.length > 0) ? kbTable : KB_SEED;
    const sorted = table.slice().sort((a, b) => a.angleDeg - b.angleDeg);

    if (angleDeg <= sorted[0].angleDeg) return sorted[0][col];
    if (angleDeg >= sorted[sorted.length - 1].angleDeg) return sorted[sorted.length - 1][col];
    for (let i = 0; i < sorted.length - 1; i++) {
      const lo = sorted[i], hi = sorted[i + 1];
      if (angleDeg >= lo.angleDeg && angleDeg <= hi.angleDeg) {
        if (hi.angleDeg === lo.angleDeg) return lo[col];  // duplicate-angle guard (main-app parity)
        const t = (angleDeg - lo.angleDeg) / (hi.angleDeg - lo.angleDeg);
        return lo[col] + t * (hi[col] - lo[col]);
      }
    }
    return sorted[sorted.length - 1][col];
  }
```

## Acceptance test

In DevTools console:

```js
// Exact table hits
console.assert(kbAt(5, "manhole", KB_SEED) === 0.06, "kbAt 5°");
console.assert(kbAt(90, "bend", KB_SEED) === 0.70, "kbAt 90°");

// Linear interp between 5° (0.06) and 10° (0.13) at 7.5° should give 0.095
console.assert(Math.abs(kbAt(7.5, "inlet", KB_SEED) - 0.095) < 1e-12, "interp 7.5°: " + kbAt(7.5, "inlet", KB_SEED));

// Linear interp between 30° (0.35) and 40° (0.43) at 35° → 0.39
console.assert(Math.abs(kbAt(35, "bend", KB_SEED) - 0.39) < 1e-12, "interp 35°: " + kbAt(35, "bend", KB_SEED));

// Clamp low
console.assert(kbAt(-5, "manhole", KB_SEED) === 0.06, "clamp low");
console.assert(kbAt(0, "manhole", KB_SEED) === 0.06, "clamp at 0°");

// Clamp high
console.assert(kbAt(200, "bend", KB_SEED) === 0.70, "clamp high");

// Column mapping: junction → bend, splitter → manhole
console.assert(kbAt(30, "junction", KB_SEED) === kbAt(30, "bend", KB_SEED), "junction uses bend");
console.assert(kbAt(30, "splitter", KB_SEED) === kbAt(30, "manhole", KB_SEED), "splitter uses manhole");

// Empty/null table falls back to seed
console.assert(kbAt(30, "manhole", null) === kbAt(30, "manhole", KB_SEED), "null fallback");
console.assert(kbAt(30, "manhole", []) === kbAt(30, "manhole", KB_SEED), "empty fallback");

console.log("task-10 kb interp: OK");
```

## Done when

- `KB_SEED` and `kbAt` defined in the `compute` sentinel block.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-10 Kb seed table and interpolation`.

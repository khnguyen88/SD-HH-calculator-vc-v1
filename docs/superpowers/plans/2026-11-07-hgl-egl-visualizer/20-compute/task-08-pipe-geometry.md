# Task 08: Pipe geometry (circular + elliptical lookup)

## Context

Implement pipe area and hydraulic radius for both circular and elliptical shapes. Implements spec §7.1. Table 4-6 lookup values come from main spec §1.5 (AASHTO/state-DOT equivalent-diameter table).

## Preconditions

- Prior tasks: task-01, task-03.
- Sentinel block `// ==== compute: begin ==== / end ====` exists and is empty.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Insert inside the `compute` sentinel block, immediately after the `begin` line:

```js
  // --- pipe geometry (task-08) ---

  // Table 4-6: circular diameter (in), elliptical span×rise (in), elliptical area (sf).
  // Elliptical values mirror the main app's TABLE46 (spec §1.5).
  const TABLE_4_6 = [
    { dia_in: 15, span_rise: null, ell_area_sf: null },
    { dia_in: 18, span_rise: "23x14", ell_area_sf: 1.8 },
    { dia_in: 21, span_rise: null, ell_area_sf: null },
    { dia_in: 24, span_rise: "30x19", ell_area_sf: 4.1 },
    { dia_in: 27, span_rise: "34x22", ell_area_sf: 5.1 },
    { dia_in: 30, span_rise: "38x24", ell_area_sf: 6.3 },
    { dia_in: 33, span_rise: "42x27", ell_area_sf: 7.4 },
    { dia_in: 36, span_rise: "45x29", ell_area_sf: 8.8 },
    { dia_in: 42, span_rise: "53x34", ell_area_sf: 10.2 },
    { dia_in: 48, span_rise: "60x38", ell_area_sf: 12.9 },
    { dia_in: 54, span_rise: "68x43", ell_area_sf: 16.6 },
    { dia_in: 60, span_rise: "76x48", ell_area_sf: 20.5 },
    { dia_in: 66, span_rise: "83x53", ell_area_sf: 24.8 },
    { dia_in: 72, span_rise: "91x58", ell_area_sf: 29.5 },
    { dia_in: 78, span_rise: "98x63", ell_area_sf: 34.6 },
    { dia_in: 84, span_rise: "106x68", ell_area_sf: 40.1 },
    { dia_in: 90, span_rise: "113x72", ell_area_sf: 46.1 },
    { dia_in: 96, span_rise: "121x77", ell_area_sf: 52.4 },
    { dia_in: 102, span_rise: "128x82", ell_area_sf: 59.2 },
    { dia_in: 108, span_rise: "136x87", ell_area_sf: 66.4 },
    { dia_in: 114, span_rise: "143x92", ell_area_sf: 74.0 },
    { dia_in: 120, span_rise: "151x97", ell_area_sf: 82.0 },
    { dia_in: 132, span_rise: "166x106", ell_area_sf: 99.2 },
    { dia_in: 144, span_rise: "180x116", ell_area_sf: 118.6 }
  ];

  function pipeAreaCircular(d_in) {
    const D_ft = d_in / 12;
    return Math.PI * D_ft * D_ft / 4;
  }

  function pipeRadiusCircular(d_in) {
    return (d_in / 12) / 4;
  }

  function pipeAreaElliptical(spanRise) {
    const key = normalizeSize("elliptical", spanRise);
    const row = key ? TABLE_4_6.find((r) => r.span_rise === key) : null;
    if (!row) throw new Error("elliptical size not in Table 4-6: " + spanRise);
    return row.ell_area_sf;
  }

  // Elliptical hydraulic radius uses the equivalent circular diameter from Table 4-6.
  function pipeRadiusElliptical(spanRise) {
    const key = normalizeSize("elliptical", spanRise);
    const row = key ? TABLE_4_6.find((r) => r.span_rise === key) : null;
    if (!row) throw new Error("elliptical size not in Table 4-6: " + spanRise);
    return (row.dia_in / 12) / 4;
  }

  function pipeArea(shape, size) {
    if (shape === "circular") return pipeAreaCircular(Number(size));
    if (shape === "elliptical") return pipeAreaElliptical(String(size));
    throw new Error("unknown pipe shape: " + shape);
  }

  function pipeRadius(shape, size) {
    if (shape === "circular") return pipeRadiusCircular(Number(size));
    if (shape === "elliptical") return pipeRadiusElliptical(String(size));
    throw new Error("unknown pipe shape: " + shape);
  }

  // Normalize shape and size strings from imports; mirrors main-app pipeGeometry leniency.
  function normalizeShape(value) {
    return String(value == null ? "" : value).trim().toLowerCase();
  }

  // Circular: numeric diameter. Elliptical: nearest Table 4-6 span x rise key.
  function normalizeSize(shape, value) {
    if (shape === "circular") return Number(value);
    const parts = String(value == null ? "" : value)
      .toLowerCase().replace(/[×\s]/g, "").split("x");
    const span = parseFloat(parts[0]);
    const rise = parseFloat(parts[1]);
    if (!isFinite(span) || !isFinite(rise)) return null;
    let best = null;
    let bestDiff = Infinity;
    for (const row of TABLE_4_6) {
      if (row.span_rise == null) continue;
      const dims = row.span_rise.split("x").map(Number);
      const diff = Math.abs(dims[0] - span) + Math.abs(dims[1] - rise);
      if (diff < bestDiff) { bestDiff = diff; best = row.span_rise; }
    }
    return best;
  }
```

## Acceptance test

In DevTools console (dev or built file both work — pure math, no SheetJS needed):

```js
// Closed-form: π(18/12)²/4 = π·2.25/4 ≈ 1.767...
const a = pipeAreaCircular(18);
console.assert(Math.abs(a - Math.PI * 2.25 / 4) < 1e-12, "pipeAreaCircular(18): " + a);

// R = D/4 = 18/48 = 0.375 ft
console.assert(Math.abs(pipeRadiusCircular(18) - 0.375) < 1e-12, "pipeRadiusCircular(18)");

// Elliptical: 38x24 → 6.3 sf per Table 4-6
console.assert(pipeAreaElliptical("38x24") === 6.3, "pipeAreaElliptical(38x24)");
console.assert(Math.abs(pipeRadiusElliptical("38x24") - pipeRadiusCircular(30)) < 1e-12, "elliptical R matches circular 30");

// Dispatch
console.assert(pipeArea("circular", 18) === a, "dispatch circular");
console.assert(pipeArea("elliptical", "38x24") === 6.3, "dispatch elliptical");

// Unknown shape throws
let threw = false;
try { pipeArea("rectangular", 12); } catch (e) { threw = true; }
console.assert(threw, "unknown shape should throw");

// Unknown elliptical size throws
threw = false;
try { pipeAreaElliptical("99x99"); } catch (e) { threw = true; }
console.assert(threw, "unknown elliptical size should throw");

console.log("task-08 pipe geometry: OK");
```

The proper node-test lives in task-32.

## Done when

- `TABLE_4_6`, `pipeAreaCircular`, `pipeRadiusCircular`, `pipeAreaElliptical`, `pipeRadiusElliptical`, `pipeArea`, `pipeRadius` all defined in the `compute` sentinel block.
- Smoke test above prints `OK`, no AssertionErrors.
- Build still succeeds.
- Commit: `feat(visualizer): task-08 pipe geometry + Table 4-6`.

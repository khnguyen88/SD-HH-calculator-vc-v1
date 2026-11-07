# Task 14: Isometric projection function

## Context

Implement `projectIso(x, y, z, kZ)` — the pure math that maps world coordinates to screen coordinates for the iso view. Implements spec §3.1.

## Preconditions

- Prior tasks: task-01, task-03.

## Exact changes

**Modify** `drainage-calculator/storm-drain-visualizer-dev.html`. Insert inside the `views` sentinel block, immediately after the `begin` line:

```js
  // --- Iso projection (task-14) ---

  const ISO_COS30 = Math.cos(Math.PI / 6);   // 0.866025...
  const ISO_SIN30 = Math.sin(Math.PI / 6);   // 0.5

  // Project world (x, y, z) to screen (sx, sy).
  //   x, y in world units (feet); z in feet; kZ is vertical exaggeration (default 2.0).
  //   screen_y is flipped (positive screen_y goes down).
  function projectIso(x, y, z, kZ) {
    const K = (typeof kZ === "number" && isFinite(kZ)) ? kZ : 2.0;
    const sx = (x - y) * ISO_COS30;
    const sy = (x + y) * ISO_SIN30 - z * K;
    return { sx, sy };
  }

  // Compute view bounds for a set of world points; used by renderIso to set SVG viewBox.
  function isoBounds(points, kZ) {
    if (!points || points.length === 0) return { minX: 0, maxX: 100, minY: 0, maxY: 100 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    let count = 0;
    for (const p of points) {
      const x = Number(p.x);
      const y = Number(p.y);
      const z = Number(p.z == null ? 0 : p.z);
      if (!isFinite(x) || !isFinite(y) || !isFinite(z)) continue;
      const pr = projectIso(x, y, z, kZ);
      if (pr.sx < minX) minX = pr.sx;
      if (pr.sx > maxX) maxX = pr.sx;
      if (pr.sy < minY) minY = pr.sy;
      if (pr.sy > maxY) maxY = pr.sy;
      count++;
    }
    if (count === 0) return { minX: 0, maxX: 100, minY: 0, maxY: 100 };
    return { minX, maxX, minY, maxY };
  }
```

## Acceptance test

In DevTools console:

```js
// (0,0,0) with kZ=2 → (0, 0)
let r = projectIso(0, 0, 0, 2);
console.assert(Math.abs(r.sx) < 1e-12 && Math.abs(r.sy) < 1e-12, "(0,0,0)");

// (1, 0, 0) with kZ=2 → (cos30, sin30) = (0.866..., 0.5)
r = projectIso(1, 0, 0, 2);
console.assert(Math.abs(r.sx - ISO_COS30) < 1e-12, "(1,0,0).sx");
console.assert(Math.abs(r.sy - ISO_SIN30) < 1e-12, "(1,0,0).sy");

// (0, 0, 1) with kZ=2 → (0, -2)  (z shifts upward on screen = negative sy)
r = projectIso(0, 0, 1, 2);
console.assert(Math.abs(r.sx) < 1e-12 && Math.abs(r.sy - (-2)) < 1e-12, "z=1");

// Depth-sort invariant: larger (x+y) ⇒ greater sy before z term.
r = projectIso(10, 10, 0, 2);
let r2 = projectIso(0, 0, 0, 2);
console.assert(r.sy > r2.sy, "painter's depth order");

// Default kZ when omitted
r = projectIso(0, 0, 1);
console.assert(Math.abs(r.sy - (-2)) < 1e-12, "default kZ=2");

// isoBounds sanity
const pts = [{ x: 0, y: 0, z: 0 }, { x: 100, y: 0, z: 0 }, { x: 0, y: 100, z: 0 }];
const b = isoBounds(pts, 2);
console.assert(b.maxX > b.minX && b.maxY > b.minY, "bounds non-empty");

console.log("task-14 projection: OK");
```

## Done when

- `ISO_COS30`, `ISO_SIN30`, `projectIso`, `isoBounds` defined in the `views` sentinel block.
- Smoke test prints `OK`.
- Build still succeeds.
- Commit: `feat(visualizer): task-14 isometric projection function`.

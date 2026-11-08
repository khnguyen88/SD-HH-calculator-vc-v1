# Task 42: SVG integrity node tests

## Context

Spec §8.5 lists three automated checks:

1. **Cross-view cursor persistence** — select a pipe in iso, press V to switch to profile,
   assert the same `pipe.id` cursor band is highlighted. This is NOT tested anywhere in the
   existing 37 test tasks.
2. **Null/undefined guard audit** — verify `svgEl` contains the guard from main spec §A.1
   (task-15 does implement it; this test asserts the guard is still present after any edit).
3. **Depth-sort correctness** — structures with smaller `(x + y)` appear earlier in SVG
   document order. Task-15 smoke-tests this in a browser console but no node test exists.

## Preconditions

- Prior tasks: task-15 (`renderIso`, `svgEl`), task-16 (`renderProfile`),
  task-17 (`toggleView`, `renderAll`), task-31 (harness).

## Exact changes

**Create** `visualizer/visualizer-tests/svg-integrity.test.js`:

```js
const test  = require("node:test");
const assert = require("node:assert");
const fs    = require("fs");
const { loadVisualizer, DEV_HTML_PATH } = require("./_harness");

const SEED = {
  schemaVersion: 1, sourceApp: "test",
  structures: [
    { id: "OUT", type: "outfall", x:  0, y:    0, rim: 103, startElev: 100, crown: 99 },
    { id: "A",   type: "manhole", x:  0, y: -100, rim: 108, startElev: 102, crown: 101 },
    { id: "B",   type: "bend",    x: 60, y: -100, rim: 109, startElev: 103, crown: 102 }
  ],
  pipes: [
    { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
      n: 0.013, slope: 0.005, length: 120, angle:  0, designQ: 8.5 },
    { id: "P2", fromId: "B", toId: "A",   shape: "circular", size: 15,
      n: 0.013, slope: 0.005, length:  80, angle: 45, designQ: 4.0 }
  ],
  outfall: { structureId: "OUT", tailwaterElev: 100 }
};

async function boot(window, seed) {
  const blob = new window.Blob([JSON.stringify(seed)]);
  await window.importFromJsonFile(new window.File([blob], "seed.json"));
}

test("SVG cross-view: pipe selected in iso stays highlighted after V-toggle to profile", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, SEED);

  // Set cursor to pipe P1 and render iso
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.state.ui.view = "iso";
  window.renderAll();

  // Verify P1 is highlighted in iso (yellow stroke)
  const isoLine = document.querySelector('#viewSvg [data-kind="pipe"][data-id="P1"]');
  assert.ok(isoLine, "P1 line should exist in iso view");
  assert.strictEqual(isoLine.getAttribute("stroke"), "#ffd60a", "P1 should be yellow in iso");

  // Toggle to profile view
  window.toggleView();
  assert.strictEqual(window.state.ui.view, "profile", "view should be profile after toggle");

  // Cursor is still on P1; profile should render a cursor band for P1
  const band = document.querySelector('#viewSvg rect[data-kind="pipe"][data-id="P1"]');
  assert.ok(band, "cursor band for P1 should appear in profile view after toggle");
});

test("SVG depth-sort: structures render in ascending (x+y) order in DOM", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, SEED);
  window.state.cursor = { kind: "structure", id: "OUT", pathStack: ["OUT"] };
  window.state.ui.view = "iso";
  window.renderAll();

  // x+y values: OUT = 0+0 = 0, A = 0+(-100) = -100, B = 60+(-100) = -40
  // Painter's algorithm: smaller (x+y) = deeper = rendered earlier in DOM.
  // Expected document order: A (-100), B (-40), OUT (0)
  const structs = Array.from(document.querySelectorAll('#viewSvg [data-kind="structure"]'));
  const ids = structs.map((g) => g.getAttribute("data-id"));
  assert.strictEqual(ids[0], "A",   `first (deepest) should be A, got ${ids[0]}`);
  assert.strictEqual(ids[1], "B",   `second should be B, got ${ids[1]}`);
  assert.strictEqual(ids[2], "OUT", `third should be OUT, got ${ids[2]}`);
});

test("svgEl null guard: setAttribute is never called with null/undefined value", () => {
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");

  // Locate the svgEl function body — it must contain the null/undefined guard.
  const svgElMatch = html.match(/function svgEl\s*\([^)]*\)\s*\{([\s\S]*?)\n  \}/);
  assert.ok(svgElMatch, "svgEl function not found in dev HTML");
  const body = svgElMatch[1];
  assert.ok(
    /v === null.*continue|v === undefined.*continue|null.*undefined.*continue/s.test(body),
    "svgEl must skip null/undefined attribute values before calling setAttribute"
  );
});

test("SVG iso: selected pipe has yellow stroke, unselected pipe has grey stroke", async () => {
  const { window, document } = loadVisualizer();
  await boot(window, SEED);
  window.state.cursor = { kind: "pipe", id: "P1", pathStack: ["OUT", "P1"] };
  window.state.ui.view = "iso";
  window.renderAll();

  const p1 = document.querySelector('#viewSvg [data-id="P1"]');
  const p2 = document.querySelector('#viewSvg [data-id="P2"]');
  assert.ok(p1, "P1 should be in SVG");
  assert.ok(p2, "P2 should be in SVG");
  assert.strictEqual(p1.getAttribute("stroke"), "#ffd60a", "selected pipe yellow");
  assert.notStrictEqual(p2.getAttribute("stroke"), "#ffd60a", "unselected pipe not yellow");
});
```

## Acceptance test

```powershell
node --test visualizer/visualizer-tests/svg-integrity.test.js
```

Expected output:

```
# tests 4
# suites 0
# pass 4
# fail 0
```

## Done when

- `svg-integrity.test.js` created with 4 tests.
- All 4 pass.
- `node --test visualizer/visualizer-tests/` — no prior tests regressed.
- Commit: `test(visualizer): task-42 SVG integrity tests (cross-view cursor, depth-sort)`.

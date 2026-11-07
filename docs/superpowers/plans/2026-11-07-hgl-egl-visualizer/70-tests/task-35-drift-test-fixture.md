# Task 35: Drift test — parity with main app export

## Context

Check in a fixture `.xlsx` exported from the main app. Load it with the independent `xlsx` npm package (not SheetJS from the dev file). Re-compute every pipe's Hf and every structure's Hb locally. Assert `|local - exported| ≤ 0.001 ft` for Hf/Hb and `≤ 0.01 ft` for end-to-end EGL.

This is the central guarantee: formula drift between the main app and the visualizer breaks this test immediately. Implements spec §8.2.

## Preconditions

- Prior tasks: task-08, task-09, task-10, task-11, task-12, task-31.
- Main app's `storm-drain-design-calculator.html` exists and can export .xlsx.

## Exact changes

**Create** `drainage-calculator/visualizer-tests/fixtures/README.md`:

```markdown
# Visualizer test fixtures

## main-app-export.xlsx

Generated once by the main app. To regenerate:

1. Open `drainage-calculator/storm-drain-design-calculator.html` in a browser.
2. Seed a project matching the schema below (click Add row in each tab).
3. Click Export → save as `main-app-export.xlsx` in this directory.

### Required seed data

- 1 Drainage Area: structureId=A, area=2.0 ac, C=0.85, i=5.0 in/hr, tc=10 min, cf=1.0.
  Expected Q = 1.0 × 0.85 × 5.0 × 2.0 = 8.5 cfs.
- 3 Structures:
  - OUT: type=outfall, forceElev=true, startElev=100.0, crown=97.0, rim=103.0.
  - A:   type=manhole, forceElev=false, rim=108.0, crown=102.0, drainage area linked.
  - B:   type=bend,    forceElev=false, rim=109.0, crown=103.0.
- 2 Pipes:
  - P1: A→OUT, circular 18 in, n=0.013, slope=0.005, length=120, angle=0.
  - P2: B→A,   circular 15 in, n=0.013, slope=0.005, length=80,  angle=45.

After export, verify in Excel that the Drainage Area, Junction Structure, Pipe Sizing sheets have the expected columns and that Total Q / Hf / Hb columns populate.
```

**Create** `drainage-calculator/visualizer-tests/fixtures/main-app-export.xlsx` — generate per the README above; place the file in this directory. **Commit the binary into git**: it's tiny (~10 KB) and is the test contract.

**Create** `drainage-calculator/visualizer-tests/drift.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const path = require("path");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

const FIXTURE = path.join(__dirname, "fixtures", "main-app-export.xlsx");
const TOL_PIPE = 0.001;
const TOL_STRUCT = 0.001;
const TOL_EGL = 0.01;

function parseFixtureIntoImported(window) {
  const wb = XLSX.readFile(FIXTURE);
  // Boot the visualizer's window.XLSX so importFromXlsxFile works
  window.XLSX = XLSX;
  // Build a jsdom File-like object from the raw buffer
  const fs = require("fs");
  const buf = fs.readFileSync(FIXTURE);
  // Re-use the window's import function
  const sheets = window.importFromXlsxFile.toString();
  // Simpler: call the parsing logic directly rather than importFromXlsxFile (which expects a File).
  // Re-implement the sheet reads here.
  const sh = (name) => wb.Sheets[name] ? XLSX.utils.sheet_to_json(wb.Sheets[name], { defval: null }) : [];
  return { daRows: sh("Drainage Area"),
           strRows: sh("Junction Structure"),
           pipeRows: sh("Pipe Sizing") };
}

test("drift: every pipe's Hf matches local recompute within 0.001 ft", () => {
  const { window, fn } = loadVisualizer();
  const { pipeRows, strRows } = parseFixtureIntoImported(window);
  for (const r of pipeRows) {
    const exported = Number(r["Hf (ft)"] || 0);
    const designQ = Number(r["Design Q (cfs)"] || 0);
    const n = Number(r["Manning's n"]);
    const length = Number(r["Length (ft)"]);
    const shape = String(r["Shape"] || "circular").toLowerCase();
    const size = r["Size"];
    const A = fn("pipeArea")(shape, size);
    const R = fn("pipeRadius")(shape, size);
    const Sf = fn("frictionSlope")(designQ, n, A, R);
    const local = fn("frictionLoss")(Sf, length);
    assert.ok(Math.abs(local - exported) <= TOL_PIPE,
      `pipe ${r["Pipe ID"]}: exported=${exported}, local=${local}`);
  }
});

test("drift: every structure's Hb matches local recompute within 0.001 ft", () => {
  const { window, fn } = loadVisualizer();
  const { strRows, pipeRows } = parseFixtureIntoImported(window);
  for (const sr of strRows) {
    const exported = Number(sr["Hb (ft)"] || 0);
    const sid = String(sr["Structure ID"]);
    const type = String(sr["Type"] || "manhole").toLowerCase();
    const inflows = pipeRows.filter((p) => String(p["To Structure"]) === sid).map((p) => ({
      angleDeg: Number(p["Angle (deg)"] || 0),
      Qcfs: Number(p["Design Q (cfs)"] || 0)
    }));
    const outPipe = pipeRows.find((p) => String(p["From Structure"]) === sid);
    if (!outPipe) continue;  // outfall has no outflow pipe
    const Aout = fn("pipeArea")(String(outPipe["Shape"] || "circular").toLowerCase(), outPipe["Size"]);
    const Qtotal = Number(outPipe["Design Q (cfs)"]);
    const res = fn("structureLoss")(inflows, Qtotal, Aout, type, window.KB_SEED);
    if (res.error) continue;
    assert.ok(Math.abs(res.Hb - exported) <= TOL_STRUCT,
      `structure ${sid}: exported=${exported}, local=${res.Hb}`);
  }
});

test("drift: end-to-end EGL at every structure matches within 0.01 ft", () => {
  const { window, fn } = loadVisualizer();
  // Seed window.state directly from the fixture and walk upstream from outfall.
  const { strRows, pipeRows } = parseFixtureIntoImported(window);
  const structures = strRows.map((r) => ({
    id: String(r["Structure ID"]), type: String(r["Type"] || "manhole").toLowerCase(),
    x: Number(r["X"] || 0), y: Number(r["Y"] || 0),
    rim: Number(r["Rim"] || 0), startElev: Number(r["Start Elev"] || 0),
    crown: Number(r["Crown"] || 0), forceElev: !!r["Force Elev"],
    exportedElev: Number(r["Upstream EGL (ft)"] || 0)
  }));
  const pipes = pipeRows.map((r) => ({
    id: String(r["Pipe ID"]), fromId: String(r["From Structure"]), toId: String(r["To Structure"]),
    shape: String(r["Shape"] || "circular").toLowerCase(), size: r["Size"],
    n: Number(r["Manning's n"]), slope: Number(r["Slope (ft/ft)"]),
    length: Number(r["Length (ft)"]), angle: Number(r["Angle (deg)"] || 0),
    designQ: Number(r["Design Q (cfs)"])
  }));
  const outfallSid = structures.find((s) => s.type === "outfall").id;
  const outfallTw = structures.find((s) => s.type === "outfall").startElev;
  window.state.imported = { structures, pipes,
    outfall: { structureId: outfallSid, tailwaterElev: outfallTw },
    kbTable: window.KB_SEED, config: {} };
  window.state.overrides = { byId: {} };

  // Walk the longest path (outfall → deepest upstream structure) and compare.
  // For each non-outfall structure, build a path and compare final EGL with exported.
  for (const s of structures) {
    if (s.type === "outfall") continue;
    // Find any path from outfall to s (DFS on reverse edges)
    const path = findPathUpstream(outfallSid, s.id, pipes);
    if (!path) continue;
    const rows = fn("buildLedger")(path, window.state, window.KB_SEED, "hec22");
    const localEnd = rows[rows.length - 1].after;
    assert.ok(Math.abs(localEnd - s.exportedElev) <= TOL_EGL,
      `EGL at ${s.id}: exported=${s.exportedElev}, local=${localEnd}`);
  }
});

function findPathUpstream(outfallSid, targetSid, pipes) {
  // Simple reverse BFS producing alternating structure/pipe path.
  const parent = { [outfallSid]: null };
  const parentPipe = {};
  const queue = [outfallSid];
  while (queue.length) {
    const cur = queue.shift();
    for (const p of pipes) if (p.toId === cur && !(p.fromId in parent)) {
      parent[p.fromId] = cur;
      parentPipe[p.fromId] = p.id;
      queue.push(p.fromId);
    }
  }
  if (!(targetSid in parent)) return null;
  const path = [];
  let cur = targetSid;
  while (cur) {
    path.push(cur);
    if (parentPipe[cur]) path.push(parentPipe[cur]);
    cur = parent[cur];
  }
  return path.reverse();
}
```

## Acceptance test

```powershell
node --test drainage-calculator/visualizer-tests/drift.test.js
```

Expected: `pass 3 / fail 0`. If any assertion fails, either a formula drifted between the main app and the visualizer (fix the visualizer) or the fixture was regenerated from a different version of the main app (regenerate against current main).

## Done when

- `fixtures/main-app-export.xlsx` committed (small binary).
- `fixtures/README.md` documents how to regenerate.
- `drift.test.js` passes all 3 tests.
- Commit: `test(visualizer): task-35 drift test vs main-app fixture`.

# Visualizer Pipe Inverts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring pipe US/DS invert elevations into the visualizer (xlsx + JSON import, optional fields) so the profile draws true geometry (including drop structures) and the HGL walk floors at the pipe's own end crown instead of the neighboring structure's outgoing-pipe crown.

**Architecture:** All changes in `visualizer/storm-drain-visualizer-dev.html` + `visualizer/visualizer-tests/`. Pipes gain optional `usInvert`/`dsInvert` fields (backward compatible — absent = today's behavior exactly). A `pipeBarrelHeightFt` helper converts shape/size to barrel rise in feet; the HGL walk's `annotateLedgerHgl` prefers `invert + barrel height` per pipe end and falls back to the current structure-`crown` per end. `profileStations` gains a derived structure flowline and per-pipe true-elevation points. `analyzeImported` computes drop structures + slope mismatches rendered through the existing warning banner. Samples gain real inverts pinned by the extended drift test.

**Tech Stack:** Single-file HTML app (no build step for tests), node:test + CommonJS, jsdom harness (`visualizer/visualizer-tests/_harness.js`), xlsx (SheetJS) for synthetic workbook tests.

**Spec:** `docs/superpowers/specs/2026-11-09-visualizer-pipe-inverts-design.md`

---

## Conventions (read first)

- **Edit `visualizer/storm-drain-visualizer-dev.html` only.** The built file `visualizer/storm-drain-visualizer.html` is gitignored output; Task 6 regenerates it via `node visualizer/build-visualizer.js`.
- **Commit style:** `feat(visualizer): v82.1 <slug>` (or `test(visualizer): v82.1 <slug>`). NEVER add LLM attribution trailers (no `Co-Authored-By` lines).
- **Work directly on `main`.** This repo does not use feature branches (established pattern from the samples feature).
- **Test harness:** `require("./_harness")` → `loadVisualizer()` → `{dom, window, document, fn: (name) => dom.window[name]}`. Top-level `function` declarations in the dev HTML are window-exposed automatically; `const`/`let` need explicit `window.X = X` (already done for `state`, `SAMPLES`).
- **Run tests:** single file — `node visualizer\visualizer-tests\<file>.test.js` from repo root; full suite — `cd visualizer\visualizer-tests` then `npm test`. `node_modules` (jsdom, xlsx) is already installed there.
- **Cross-realm pitfall:** values coming out of a jsdom window (e.g. arrays from `fn(...)`) live in the jsdom realm; `assert.deepStrictEqual` against Node-realm literals fails on prototype identity. Use `assert.strictEqual` on scalars/lengths, or round-trip through `JSON.parse(JSON.stringify(v))`.
- **withFocusPreserved:** every event handler that triggers a render routes through it (enforced by the audit test in dom-events.test.js:174-187). No new handlers in this feature touch that, but keep it in mind if you add any.
- **No placeholder edits:** every code block below is complete — paste it verbatim.
- **Corrections discovered in Task 1 (apply to ALL later test code in this plan):**
  1. `validateImportedJson` requires a top-level `outfall` object — every JSON fixture in Tasks 2-5 must include `outfall: { structureId: <outfall id>, tailwaterElev: <number> }` (in addition to `schemaVersion: 1` and `sourceApp`).
  2. `applyImportedJson` and `importFromXlsxFile` return **undefined** and **throw** on failure — tests must assert not-throws and then inspect `state`, not a `result.errors` return value.
  3. `pickNum` maps blank xlsx cells to `null` (the designQ/rim/crown convention), not `undefined`.
  4. Tests that exercise `importFromXlsxFile` must boot the harness as `loadVisualizer({ XLSX })` (SheetJS injection; see xlsx-import.test.js). JSON-only tests can use plain `loadVisualizer()`.

## File structure

- Modify: `visualizer/storm-drain-visualizer-dev.html` — all app changes (schema, xlsx import, walk floors, profile, warnings, samples).
- Create: `visualizer/visualizer-tests/inverts.test.js` — Task 1 (schema + xlsx + JSON passthrough).
- Create: `visualizer/visualizer-tests/inverts-walk.test.js` — Task 2 (crown floors) and Task 3 (profile stations) assertions.
- Create: `visualizer/visualizer-tests/inverts-warnings.test.js` — Task 4 (banner).
- Modify: `visualizer/visualizer-tests/samples-drift.test.js` — Task 5 (drift guard extension).

Task 1 (import), Task 2 (walk), Task 3 (profile), Task 4 (warnings), Task 5 (samples), Task 6 (full suite + build + smoke). Tasks build on each other; do them in order.

---

### Task 1: Import pipe inverts (xlsx + JSON schema)

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (`validateImportedJson` ~line 632, xlsx pipe mapping ~line 899)
- Create: `visualizer/visualizer-tests/inverts.test.js`

- [ ] **Step 1: Write the failing tests**

Create `visualizer/visualizer-tests/inverts.test.js`:

```js
/*
 * Pipe inverts: optional usInvert/dsInvert fields — schema validation,
 * xlsx column import, JSON passthrough into state.
 */
const test = require("node:test");
const assert = require("node:assert");
const XLSX = require("xlsx");
const { loadVisualizer } = require("./_harness");

function ensureFileArrayBuffer(window) {
  if (!window.File.prototype.arrayBuffer) {
    window.File.prototype.arrayBuffer = function () {
      return new window.Promise((resolve) => {
        const fr = new window.FileReader();
        fr.onload = () => resolve(fr.result);
        fr.readAsArrayBuffer(this);
      });
    };
  }
}

// Header strings must match exactly what importFromXlsxFile reads
// (human-readable headers, not JSON field names) — mirrors xlsx-import.test.js.
function buildSyntheticWorkbook(extraPipeFields) {
  const strRows = [
    { "Structure ID": "OUT", "Type": "outfall", "Fixed-Start Elev (ft)": 89,
      "Pipe Crown (ft)": null, "Rim-Grate Elev (ft)": null, "Total Flow (cfs)": 0, "Outgoing Pipe ID": "" },
    { "Structure ID": "MH", "Type": "manhole", "Fixed-Start Elev (ft)": null,
      "Pipe Crown (ft)": 92, "Rim-Grate Elev (ft)": 95, "Total Flow (cfs)": 9, "Outgoing Pipe ID": "P1" }
  ];
  const pipeRow = {
    "ID": "P1",
    "From Structure": "MH",
    "To Structure": "OUT",
    "Shape": "circular",
    "Size (in or SPANxRISE)": 24,
    "n": 0.013,
    "Slope (ft-ft)": 0.01,
    "Length (ft)": 100,
    "Angle (deg)": 0,
    "Design Q (cfs)": 9,
    "Split Role": ""
  };
  Object.assign(pipeRow, extraPipeFields);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(strRows), "Junction Structure");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([pipeRow]), "Pipe Sizing");
  return wb;
}

async function importSynthetic(window, wb) {
  ensureFileArrayBuffer(window);
  const arr = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  const blob = new window.Blob([arr]);
  const file = new window.File([blob], "synthetic.xlsx");
  return await window.importFromXlsxFile(file);
}

test("schema: usInvert/dsInvert absent passes, finite number passes, non-number fails", () => {
  const viz = loadVisualizer();
  const validate = viz.fn("validateImportedJson");
  // validateImportedJson requires schemaVersion 1 + string sourceApp at the
  // top level; structure types are lowercase strings ("outfall", "manhole").
  const base = () => ({
    schemaVersion: 1,
    sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall" },
      { id: "MH", type: "manhole" }
    ],
    pipes: [{ id: "P1", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013, slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9 }]
  });

  const absent = validate(base());
  assert.strictEqual(absent.errors.length, 0, "absent inverts must pass: " + absent.errors.join("; "));

  const present = validate(base());
  present.pipes[0].usInvert = 102;
  present.pipes[0].dsInvert = 101;
  assert.strictEqual(present.errors.length, 0, "finite numbers must pass: " + present.errors.join("; "));

  const badUp = validate(base());
  badUp.pipes[0].usInvert = "102";
  assert.ok(badUp.errors.some((e) => /pipes\[0\]\.usInvert/.test(e)), "non-number usInvert must fail with field-named error: " + badUp.errors.join("; "));

  const badDn = validate(base());
  badDn.pipes[0].dsInvert = "one hundred";
  assert.ok(badDn.errors.some((e) => /pipes\[0\]\.dsInvert/.test(e)), "non-number dsInvert must fail with field-named error");

  viz.dom.window.close();
});

test("xlsx: US Invert (ft) / DS Invert (ft) columns import into usInvert/dsInvert", async () => {
  const viz = loadVisualizer();
  const wb = buildSyntheticWorkbook({ "US Invert (ft)": 90, "DS Invert (ft)": 89 });
  const result = await importSynthetic(viz.window, wb);
  assert.strictEqual(result.errors.length, 0, result.errors.join("; "));
  assert.strictEqual(viz.window.state.imported.pipes.length, 1);
  const p = viz.window.state.imported.pipes[0];
  assert.strictEqual(p.usInvert, 90);
  assert.strictEqual(p.dsInvert, 89);
  viz.dom.window.close();
});

test("xlsx: blank invert cells stay absent", async () => {
  const viz = loadVisualizer();
  const wb = buildSyntheticWorkbook({ "US Invert (ft)": "", "DS Invert (ft)": "" });
  const result = await importSynthetic(viz.window, wb);
  assert.strictEqual(result.errors.length, 0, result.errors.join("; "));
  const p = viz.window.state.imported.pipes[0];
  assert.strictEqual(p.usInvert, undefined);
  assert.strictEqual(p.dsInvert, undefined);
  viz.dom.window.close();
});

test("json: applyImportedJson carries usInvert/dsInvert into state.imported.pipes", () => {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall", rim: 89 },
      { id: "MH", type: "manhole", rim: 95 }
    ],
    pipes: [{ id: "P1", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013, slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 }]
  };
  const result = apply(obj, "test.json");
  assert.strictEqual(result.errors.length, 0, result.errors.join("; "));
  assert.strictEqual(viz.window.state.imported.pipes[0].usInvert, 90);
  assert.strictEqual(viz.window.state.imported.pipes[0].dsInvert, 89);
  viz.dom.window.close();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node visualizer\visualizer-tests\inverts.test.js`
Expected: FAIL — schema errors don't mention usInvert (non-number test fails), xlsx imports without usInvert (undefined !== 102).

- [ ] **Step 3: Implement schema validation**

In `visualizer/storm-drain-visualizer-dev.html`, in `validateImportedJson`, find the pipe designQ check (~line 632):

```js
if (p.designQ != null && (typeof p.designQ !== "number" || !isFinite(p.designQ)))
  push("pipes[" + i + "].designQ must be a finite number");
```

Immediately after it add:

```js
["usInvert", "dsInvert"].forEach((f) => {
  if (p[f] != null && (typeof p[f] !== "number" || !isFinite(p[f])))
    push("pipes[" + i + "]." + f + " must be a finite number");
});
```

- [ ] **Step 4: Implement xlsx column import**

In the xlsx pipe mapping object literal (~line 886-899), find:

```js
designQ: pickNum(r["Design Q (cfs)"], r.designQ),
```

Immediately after it add:

```js
usInvert: pickNum(r["US Invert (ft)"], r.usInvert),
dsInvert: pickNum(r["DS Invert (ft)"], r.dsInvert),
```

No `applyImportedJson` change needed — pipes are copied via `Object.assign({}, p)` in the `_overrides` handling, so new fields flow through automatically.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `node visualizer\visualizer-tests\inverts.test.js`
Expected: 4 PASS.

- [ ] **Step 6: Run the full suite (regression check)**

Run: `cd visualizer\visualizer-tests` then `npm test`
Expected: all green (99 existing + 4 new). Old imports without inverts are unaffected (fields absent).

- [ ] **Step 7: Commit**

```bash
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/inverts.test.js
git commit -m "feat(visualizer): v82.1 import pipe inverts (xlsx + json schema)"
```

---

### Task 2: Pipe-end crown floors in the HGL walk

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (new `pipeBarrelHeightFt` helper near `pipeRadius`; `annotateLedgerHgl` ~lines 522-570)
- Create: `visualizer/visualizer-tests/inverts-walk.test.js`

- [ ] **Step 1: Write the failing tests**

Create `visualizer/visualizer-tests/inverts-walk.test.js`:

```js
/*
 * Pipe-end crown floors: when a pipe has end inverts, its HGL walk floor is
 * that end's invert + barrel height (its own soffit), not the neighboring
 * structure's outgoing-pipe crown. Per-end fallback keeps old behavior when
 * an invert is absent.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

// Drop network from the spec's motivating case:
//   OUT (outfall, rim 89) <-- PA (24", usInv 90, dsInv 89, L 100, Q 9) -- MH
//   MH <-- PB (18", usInv 101, dsInv 100, L 200, Q 3.4) -- UP (rim 105)
// Under old behavior PB's downstream floor = MH's structure crown (92);
// with inverts it is PB's own soffit: 100 + 1.5 = 101.5.
function loadDropNetwork(withInverts) {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const mkPipe = (id, fromId, toId, size, length, designQ, usInv, dsInv) => {
    const p = { id, fromId, toId, shape: "circular", size, n: 0.013, slope: 0.01, length, angle: 0, splitRole: "", designQ };
    if (withInverts) { p.usInvert = usInv; p.dsInvert = dsInv; }
    return p;
  };
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall", rim: 89, startElev: 89 },   // startElev = fixed tailwater
      { id: "MH", type: "manhole", rim: 95, crown: 92 },
      { id: "UP", type: "manhole", rim: 105 },
    ],
    pipes: [
      mkPipe("PA", "MH", "OUT", 24, 100, 9, 90, 89),
      mkPipe("PB", "UP", "MH", 18, 200, 3.4, 101, 100),
    ],
  };
  const result = apply(obj, "drop.json");
  assert.strictEqual(result.errors.length, 0, result.errors.join("; "));
  return viz;
}

const PATH = ["OUT", "PA", "MH", "PB", "UP"];

function walkRows(viz, method) {
  viz.window.state.ui.hglMethod = method;
  const buildLedger = viz.fn("buildLedger");
  const rows = buildLedger(PATH, viz.window.state, viz.window.state.imported.kbTable, method);
  const annotate = viz.fn("annotateLedgerHgl");
  return annotate(rows, viz.window.state, method);
}

function hfRow(rows, id) {
  const r = rows.find((x) => x.kind === "hf" && x.id === id);
  assert.ok(r, "no hf row for " + id);
  return r;
}

test("pipeBarrelHeightFt: circular diameter/12, elliptical RISE/12, bad input null", () => {
  const viz = loadVisualizer();
  const h = viz.fn("pipeBarrelHeightFt");
  assert.strictEqual(h("circular", 24), 2);
  assert.strictEqual(h("circular", 18), 1.5);
  assert.strictEqual(h("elliptical", "38x24"), 2);
  assert.strictEqual(h("elliptical", "38X24"), 2);
  assert.strictEqual(h("circular", null), null);
  assert.strictEqual(h("elliptical", "garbage"), null);
  viz.dom.window.close();
});

test("with inverts: PB downstream floor is its own soffit 101.5, not MH crown 92", () => {
  const viz = loadDropNetwork(true);
  const rows = walkRows(viz, "hec22");
  const pb = hfRow(rows, "PB");
  assert.strictEqual(pb.hglDn, 101.5);
  // PA: ds floor = 89 + 2 = 91 (its own dsInvert soffit)
  const pa = hfRow(rows, "PA");
  assert.strictEqual(pa.hglDn, 91);
  viz.dom.window.close();
});

test("with inverts: hec22 hglUp = hglDn + Hf (101.5 + 0.21062); legacy also pins at upstream soffit 102.5", () => {
  const viz = loadDropNetwork(true);

  const hec = walkRows(viz, "hec22");
  const pbHec = hfRow(hec, "PB");
  // Hf = Sf*L, Sf from full-flow Manning: (Q*n/(1.486*A*R^(2/3)))^2
  // A=1.767146, R=0.375 -> Hf = 0.21062 (rounded)
  assert.ok(Math.abs(pbHec.hgl - (101.5 + 0.21062)) < 0.01,
    "hec22 PB hglUp expected ~101.71, got " + pbHec.hgl);

  const legacy = walkRows(viz, "legacy-both-crown");
  const pbLegacy = hfRow(legacy, "PB");
  assert.strictEqual(pbLegacy.hglDn, 101.5);
  assert.strictEqual(pbLegacy.hgl, 102.5, "legacy upstream pin at usInvert 101 + 1.5");
  viz.dom.window.close();
});

test("without inverts: PB floor falls back to MH structure crown 92 (old behavior)", () => {
  const viz = loadDropNetwork(false);
  const rows = walkRows(viz, "hec22");
  const pb = hfRow(rows, "PB");
  assert.strictEqual(pb.hglDn, 92);
  viz.dom.window.close();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node visualizer\visualizer-tests\inverts-walk.test.js`
Expected: FAIL — `pipeBarrelHeightFt` is not a function; hf rows have no `hglDn` property (undefined !== 101.5).

- [ ] **Step 3: Implement `pipeBarrelHeightFt`**

In `visualizer/storm-drain-visualizer-dev.html`, next to the existing `pipeRadius` helper (search for `function pipeRadius`), add:

```js
function pipeBarrelHeightFt(shape, size) {
  if (shape === "circular") {
    const d = Number(size);
    return (isFinite(d) && d > 0) ? d / 12 : null;
  }
  // Elliptical "SPANxRISE" (e.g. "38x24") -> RISE/12. Mirrors normalizeSize parsing.
  const parts = String(size == null ? "" : size).toLowerCase().replace(/[×\s]/g, "").split("x");
  const rise = parseFloat(parts[1]);
  return (isFinite(rise) && rise > 0) ? rise / 12 : null;
}
```

- [ ] **Step 4: Implement pipe-end crown floors in `annotateLedgerHgl`**

In `annotateLedgerHgl`, find the `crownOf` helper definition (~line 526-529):

```js
const crownOf = (id) => { ... };
```

Immediately after it add:

```js
const pipeCrownAt = (pipe, end) => {
  const inv = resolveField(pipe.id, end === "dn" ? "dsInvert" : "usInvert", imp, ovr);
  if (typeof inv !== "number" || !isFinite(inv)) return null;
  const h = pipeBarrelHeightFt(resolveField(pipe.id, "shape", imp, ovr),
    resolveField(pipe.id, "size", imp, ovr));
  return (h != null) ? inv + h : null;
};
```

(`annotateLedgerHgl` opens with `const imp = resolvedState.imported; const ovr = resolvedState.overrides;` — lines 523-524 — and `resolveField(id, field, imported, overrides)` is the same helper `crownOf` uses. Verified.)

Then find the hf branch call (lines 546-550):

```js
        const step = hglWalkStep(row.before, V,
          pipe ? crownOf(pipe.toId) : null,
          pipe ? crownOf(pipe.fromId) : null,
          row.delta, method);
        hgl = step.hglUp;
```

Replace with:

```js
        let crownDn = null, crownUp = null;
        if (pipe) {
          const pDn = pipeCrownAt(pipe, "dn");
          const pUp = pipeCrownAt(pipe, "up");
          crownDn = (pDn != null) ? pDn : crownOf(pipe.toId);
          crownUp = (pUp != null) ? pUp : crownOf(pipe.fromId);
        }
        const step = hglWalkStep(row.before, V, crownDn, crownUp, row.delta, method);
        hgl = step.hglUp;
```

And the hf-row push on the next line (551):

```js
        out.push(Object.assign({}, row, { hgl, hglClamped: step.clamped }));
```

becomes:

```js
        out.push(Object.assign({}, row, { hgl, hglDn: step.hglDn, hglClamped: step.clamped }));
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `node visualizer\visualizer-tests\inverts-walk.test.js`
Expected: 4 PASS.

- [ ] **Step 6: Run the full suite; update pinned HGL expectations ONLY if diffs are floor-related**

Run: `cd visualizer\visualizer-tests` then `npm test`

The main-app-export fixture (`fixtures/main-app-export.xlsx`) contains real inverts, so fixture-pinned walk HGL values may legitimately change — e.g. `xlsx-import.test.js` or walk tests that pinned r12's floor at `crownOf(ST-J)` = 103.5 will now see r12's own ds soffit `101 + 2 = 103`. For each failing test:
1. Read the assertion and recompute the expected value by hand from the pipe's inverts in the fixture (dsInvert + barrel height).
2. Confirm the new value IS the pipe-end floor (not an unrelated regression) before updating the pin.
3. Update the pinned expectation with a comment `// floor now from pipe dsInvert + barrel height`.

If any failure is NOT floor-related, STOP — investigate before touching anything.

- [ ] **Step 7: Commit**

```bash
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/inverts-walk.test.js
git commit -m "feat(visualizer): v82.1 pipe-end crown floors in HGL walk"
```

---

### Task 3: True invert geometry in the profile

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (`profileStations` ~lines 1258-1305)
- Modify: `visualizer/visualizer-tests/inverts-walk.test.js` (append profile tests)

- [ ] **Step 1: Write the failing tests**

Append to `visualizer/visualizer-tests/inverts-walk.test.js`:

```js
function profileRows(viz) {
  const buildLedger = viz.fn("buildLedger");
  const annotate = viz.fn("annotateLedgerHgl");
  const profileStations = viz.fn("profileStations");
  viz.window.state.ui.hglMethod = "hec22";
  const rows = annotate(buildLedger(PATH, viz.window.state, viz.window.state.imported.kbTable, "hec22"),
    viz.window.state, "hec22");
  return profileStations(rows, viz.window.state.imported, viz.window.state.overrides);
}

function stPoint(rows, id) {
  const r = rows.filter((x) => x.id === id);
  assert.ok(r.length > 0, "no station points for " + id);
  return r;
}

test("profile with inverts: stations carry true pipe-end inverts; drop draws as vertical step", () => {
  const viz = loadDropNetwork(true);
  const rows = profileRows(viz);

  // PA contributes points at BOTH ends: ds at station 0 (inv 89), us at station 100 (inv 90).
  const pa = stPoint(rows, "PA");
  const paDs = pa.find((p) => p.invert === 89);
  const paUs = pa.find((p) => p.invert === 90);
  assert.ok(paDs && paDs.station === 0, "PA ds point (inv 89) at station 0");
  assert.ok(paUs && Math.abs(paUs.station - 100) < 1e-9, "PA us point (inv 90) at station 100");
  assert.strictEqual(paUs.crown, 92, "PA us crown = 90 + 2");

  // PB: ds invert 100 at station 100, us invert 101 at station 300.
  const pb = stPoint(rows, "PB");
  const pbDs = pb.find((p) => p.invert === 100);
  const pbUs = pb.find((p) => p.invert === 101);
  assert.ok(pbDs && Math.abs(pbDs.station - 100) < 1e-9, "PB ds point (inv 100) at station 100");
  assert.ok(pbUs && Math.abs(pbUs.station - 300) < 1e-9, "PB us point (inv 101) at station 300");
  assert.strictEqual(pbDs.crown, 101.5, "PB ds crown = 100 + 1.5");

  // The 10-ft drop inside MH appears as the invert step at station 100: PA us 90 vs PB ds 100.
  assert.ok(paUs && pbDs && Math.abs(paUs.station - pbDs.station) < 1e-9,
    "drop renders as two points at the same station (90 vs 100)");
  viz.dom.window.close();
});

test("profile with inverts: structure stations use derived flowline (MH 90 from PA usInvert)", () => {
  const viz = loadDropNetwork(true);
  const rows = profileRows(viz);
  const mh = stPoint(rows, "MH");
  assert.ok(mh.some((p) => p.kind === "structure" && p.invert === 90),
    "MH structure station invert = min outgoing usInvert = 90");
  viz.dom.window.close();
});

test("profile without inverts: fallback values match today's single-point-per-pipe behavior", () => {
  const viz = loadDropNetwork(false);
  const rows = profileRows(viz);
  const pa = stPoint(rows, "PA");
  // Old behavior: one point per pipe row at the From end, invert from structure startElev or EGL-3.
  const paPipe = pa.filter((p) => p.kind === "pipe");
  assert.strictEqual(paPipe.length, 1, "without inverts, PA contributes exactly one pipe point");
  viz.dom.window.close();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node visualizer\visualizer-tests\inverts-walk.test.js`
Expected: the 3 new profile tests FAIL (PA has one point at the From end with EGL-relative invert, not two true-elevation points). The 4 Task-2 tests still pass.

- [ ] **Step 3: Implement derived flowline and true pipe geometry in `profileStations`**

In `visualizer/storm-drain-visualizer-dev.html`, inside `profileStations(rows, imported, overrides)` — immediately after the `elev` helper (lines 1261-1264) — add a flowline helper:

```js
    const flowlineOf = (id) => {
      const outInv = imported.pipes
        .filter((p) => p.fromId === id)
        .map((p) => resolveField(p.id, "usInvert", imported, overrides))
        .filter((v) => typeof v === "number" && isFinite(v));
      if (outInv.length) return Math.min.apply(null, outInv);
      const inInv = imported.pipes
        .filter((p) => p.toId === id)
        .map((p) => resolveField(p.id, "dsInvert", imported, overrides))
        .filter((v) => typeof v === "number" && isFinite(v));
      if (inInv.length) return Math.min.apply(null, inInv);
      return null;
    };
```

(`resolveField(id, field, imported, overrides)` is the existing override-aware helper at ~line 371 — same one the walk uses. Using it keeps `_overrides` sidecar edits to inverts working everywhere.)

Then replace the entire hf branch (currently lines 1275-1291):

```js
      } else if (row.kind === "hf") {
        const pipe = imported.pipes.find((p) => p.id === row.id);
        const rawLength = (overrides && overrides.byId[row.id] && overrides.byId[row.id].length != null)
          ? overrides.byId[row.id].length
          : (pipe ? pipe.length : 0);
        const length = Number(rawLength);
        const fromStr = pipe ? imported.structures.find((s) => s.id === pipe.fromId) : null;
        const dsInv = (pipe && typeof pipe.dsInvert === "number" && isFinite(pipe.dsInvert)) ? pipe.dsInvert : null;
        const usInv = (pipe && typeof pipe.usInvert === "number" && isFinite(pipe.usInvert)) ? pipe.usInvert : null;
        const barrel = pipe ? pipeBarrelHeightFt(pipe.shape, pipe.size) : null;
        // The walk runs downstream -> upstream: the station before marching is
        // this pipe's To-structure station; after marching it's the From-structure.
        if (dsInv != null && barrel != null) {
          stations.push({
            station, kind: "pipe", id: row.id,
            invert: dsInv, crown: dsInv + barrel, rim: null,
            egl: row.before, hgl: row.hglDn != null ? row.hglDn : row.before
          });
        }
        // March station forward by this pipe's length (horizontally — profile ignores plan curvature)
        if (isFinite(length) && length > 0) station += length;
        if (usInv != null && barrel != null) {
          stations.push({
            station, kind: "pipe", id: row.id,
            invert: usInv, crown: usInv + barrel, rim: null,
            egl: row.after, hgl: row.hgl != null ? row.hgl : row.after
          });
        } else {
          // Legacy fallback: single From-structure point (today's behavior).
          stations.push({
            station, kind: "pipe", id: row.id,
            invert: elev(fromStr, "startElev", row.after - 3),
            crown: elev(fromStr, "crown", row.after),
            rim: null,
            egl: row.after, hgl: row.hgl != null ? row.hgl : row.after
          });
        }
      } else if (row.kind === "hb") {
```

Per-end independence falls out naturally: a pipe with only `dsInvert` pushes the true ds point plus the legacy us point; only `usInvert` pushes just the true us point. The `row.hglDn` reference requires Task 2's push of `hglDn` onto annotated rows — that's why the tasks are ordered.

- [ ] **Step 4: Use the derived flowline for structure stations**

The line `invert: elev(str, "startElev", row.after - 3),` appears identically in BOTH structure branches — the "start" branch (line 1270) and the "hb" branch (line 1296). Replace both occurrences with:

```js
invert: (flowlineOf(str.id) != null) ? flowlineOf(str.id) : elev(str, "startElev", row.after - 3),
```

Rim and crown anchors for structure stations keep their current sources (`rim`, `crown` fields).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `node visualizer\visualizer-tests\inverts-walk.test.js`
Expected: all 7 PASS (4 walk + 3 profile).

- [ ] **Step 6: Run the full suite**

Run: `cd visualizer\visualizer-tests` then `npm test`
Expected: all green. Profile-rendering tests without inverts must be byte-identical in behavior (the else branch is exactly today's push).

- [ ] **Step 7: Commit**

```bash
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/inverts-walk.test.js
git commit -m "feat(visualizer): v82.1 true invert geometry in profile"
```

---

### Task 4: Drop-structure and slope warnings

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (`analyzeImported` ~lines 1023-1090, `renderWarningBanner` ~lines 2646-2731)
- Create: `visualizer/visualizer-tests/inverts-warnings.test.js`

- [ ] **Step 1: Write the failing tests**

Create `visualizer/visualizer-tests/inverts-warnings.test.js`:

```js
/*
 * Warnings: drop structures (internal drop > 0.5 ft) and slope-vs-invert
 * mismatches surface through the existing warning banner.
 */
const test = require("node:test");
const assert = require("node:assert");
const { loadVisualizer } = require("./_harness");

function loadNetwork(pipes) {
  const viz = loadVisualizer();
  const apply = viz.fn("applyImportedJson");
  const obj = {
    schemaVersion: 1,
    sourceApp: "test",
    structures: [
      { id: "OUT", type: "outfall", rim: 89 },
      { id: "MH", type: "manhole", rim: 95 },
      { id: "UP", type: "manhole", rim: 105 },
    ],
    pipes,
  };
  const result = apply(obj, "warn.json");
  assert.strictEqual(result.errors.length, 0, result.errors.join("; "));
  return viz;
}

const SLOPE_OK_PIPE = { id: "PB", fromId: "UP", toId: "MH", shape: "circular", size: 18, n: 0.013,
  slope: 0.005, length: 200, angle: 0, splitRole: "", designQ: 3.4, usInvert: 101, dsInvert: 100 };

test("drop banner fires at a 10-ft drop with correct text", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  const a = viz.window.state.analysis;
  assert.strictEqual(a.dropStructures.length, 1);
  const d = a.dropStructures[0];
  assert.strictEqual(d.id, "MH");
  assert.strictEqual(d.dropFt, 10);

  const renderAll = viz.fn("renderAll");
  renderAll();
  const banner = viz.window.document.getElementById("warningBanner");
  const text = banner.textContent;
  assert.ok(/Drop structure MH/.test(text), "banner names the structure: " + text);
  assert.ok(/10\.00 ft drop/.test(text), "banner states the drop: " + text);
  assert.ok(/100\.00/.test(text) && /90\.00/.test(text), "banner states both inverts: " + text);
  viz.dom.window.close();
});

test("drop banner stays silent at a 0.4-ft drop", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 100.4, dsInvert: 99.4 },
    { id: "PB", fromId: "UP", toId: "MH", shape: "circular", size: 18, n: 0.013,
      slope: 0.005, length: 200, angle: 0, splitRole: "", designQ: 3.4, usInvert: 101, dsInvert: 100 },
  ]);
  assert.strictEqual(viz.window.state.analysis.dropStructures.length, 0);
  viz.dom.window.close();
});

test("outfalls are never drop structures", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  // OUT is an outfall with an incoming pipe at dsInv 89 — must NOT be flagged even if its (absent) outgoing inverts would imply a drop.
  const ids = viz.window.state.analysis.dropStructures.map((d) => d.id);
  assert.ok(ids.indexOf("OUT") === -1);
  viz.dom.window.close();
});

test("slope banner fires when (usInv-dsInv)/L disagrees with declared slope", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    // computed = 1/200 = 0.005 vs declared 0.01 -> |diff| 0.005 > max(0.002, 0.002) -> flag
    Object.assign({}, SLOPE_OK_PIPE, { slope: 0.01 }),
  ]);
  const a = viz.window.state.analysis;
  assert.strictEqual(a.slopeMismatches.length, 1);
  assert.strictEqual(a.slopeMismatches[0].id, "PB");

  const renderAll = viz.fn("renderAll");
  renderAll();
  const text = viz.window.document.getElementById("warningBanner").textContent;
  assert.ok(/PB/.test(text), "banner names the pipe: " + text);
  viz.dom.window.close();
});

test("slope banner silent when consistent (computed 0.005 vs declared 0.005)", () => {
  const viz = loadNetwork([
    { id: "PA", fromId: "MH", toId: "OUT", shape: "circular", size: 24, n: 0.013,
      slope: 0.01, length: 100, angle: 0, splitRole: "", designQ: 9, usInvert: 90, dsInvert: 89 },
    SLOPE_OK_PIPE,
  ]);
  assert.strictEqual(viz.window.state.analysis.slopeMismatches.length, 0);
  viz.dom.window.close();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node visualizer\visualizer-tests\inverts-warnings.test.js`
Expected: FAIL — `state.analysis.dropStructures` is undefined.

- [ ] **Step 3: Compute warnings in `analyzeImported`**

In `analyzeImported(imported)`, before the return statement, add:

```js
const finNum = (v) => (typeof v === "number" && isFinite(v)) ? v : null;
const dropStructures = [];
for (const st of structures) {
  if (st.type === "outfall") continue;   // lowercase — same check analyzeImported already uses (line 1028)
  const incoming = pipes.filter((p) => p.toId === st.id && finNum(p.dsInvert) != null);
  const outgoing = pipes.filter((p) => p.fromId === st.id && finNum(p.usInvert) != null);
  if (!incoming.length || !outgoing.length) continue;
  const fromInvert = Math.min.apply(null, incoming.map((p) => p.dsInvert));
  const toInvert = Math.min.apply(null, outgoing.map((p) => p.usInvert));
  const dropFt = fromInvert - toInvert;
  if (dropFt > 0.5) {
    dropStructures.push({
      id: st.id,
      dropFt: Math.round(dropFt * 100) / 100,
      fromInvert: Math.round(fromInvert * 100) / 100,
      toInvert: Math.round(toInvert * 100) / 100,
      incomingPipeIds: incoming.map((p) => p.id),
      outgoingPipeId: outgoing[0].id
    });
  }
}

const slopeMismatches = [];
for (const p of pipes) {
  const us = finNum(p.usInvert), ds = finNum(p.dsInvert);
  if (us == null || ds == null || !(p.length > 0) || finNum(p.slope) == null) continue;
  const computed = (us - ds) / p.length;
  const declared = p.slope;
  if (Math.abs(computed - declared) > Math.max(0.002, 0.2 * Math.abs(declared))) {
    slopeMismatches.push({
      id: p.id,
      declared: Math.round(declared * 100000) / 100000,
      computed: Math.round(computed * 100000) / 100000
    });
  }
}
```

and extend the return at line 1089 — keep every existing key, append the two new ones (the `structures`/`pipes` locals at lines 1025-1026 are already in scope):

```js
    return { outfallIds, defaultWalkStart, splitterIds, primaryPipeByStructureId, missingDesignQ,
      tr55ByStructureId, walkStarts, dropStructures, slopeMismatches };
```

`analyzeImported` runs inside `applyImportedJson`, so `state.analysis.dropStructures` exists right after import.

- [ ] **Step 4: Render the warnings in `renderWarningBanner`**

In `renderWarningBanner` (line 2646), make four edits:

1. After the `missingQ` line (2652), add:

```js
    const dropStructs = (a && Array.isArray(a.dropStructures)) ? a.dropStructures : [];
    const slopeMis = (a && Array.isArray(a.slopeMismatches)) ? a.slopeMismatches : [];
```

2. Replace the `hasWarning` line (2653):

```js
    const hasWarning = !!(a && !state.ui.warningsDismissed
      && (splitterIds.length || missingQ.length || dropStructs.length || slopeMis.length));
```

3. Extend the signature array (2657) so the skip check notices the new inputs:

```js
      ? JSON.stringify([splitterIds, missingQ, dropStructs, slopeMis, warningDetailsOpen, state.ui.warningsDismissed])
```

4. After the `missingQ` summary block (2678-2681), append the new summary lines, mirroring the existing `summary.appendChild(el("div", null, ...))` pattern (em-dash "—" is fine — the file already uses it):

```js
    for (const d of dropStructs) {
      summary.appendChild(el("div", null,
        "Drop structure " + d.id + " — " + d.dropFt.toFixed(2) + " ft drop inside structure (invert "
        + d.fromInvert.toFixed(2) + " → " + d.toInvert.toFixed(2)
        + "): incoming pipe treated as free outfall; HGL floored at the pipe crown."));
    }
    if (slopeMis.length > 0) {
      summary.appendChild(el("div", null,
        "Slope vs inverts: pipe " + slopeMis.map((m) =>
          m.id + " (declared " + m.declared + ", inverts give " + m.computed + ")").join("; ")));
    }
```

(The existing `el(tag, attrs, text)` helper and the summary/controls row structure are already in scope — this follows the exact pattern of lines 2669-2681.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `node visualizer\visualizer-tests\inverts-warnings.test.js`
Expected: 5 PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd visualizer\visualizer-tests` then `npm test`

Known interaction: after Task 5 adds inverts to the calculator-demo sample, SPLIT-1 will show a legitimate 3.0 ft drop warning (incoming P3 dsInvert 100.6 vs outgoing P5 usInvert 97.6). Before Task 5, no existing test asserts banner absence on the samples, so this task should stay green. If a banner test fails, read it — do not weaken existing dismiss/skip semantics.

- [ ] **Step 7: Commit**

```bash
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/inverts-warnings.test.js
git commit -m "feat(visualizer): v82.1 drop-structure and slope warnings"
```

---

### Task 5: Samples with real inverts, pinned by the drift guard

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (`const SAMPLES` ~line 730)
- Modify: `visualizer/visualizer-tests/samples-drift.test.js` (mappedPipes)

- [ ] **Step 1: Write the failing test change (drift guard extension)**

In `visualizer/visualizer-tests/samples-drift.test.js`:
1. Add a helper next to `canon`:

```js
const invNum = (v) => {
  const n = (v === "" || v == null) ? null : Number(v);
  return (n != null && isFinite(n)) ? n : null;
};
```

2. In `mappedPipes`, add two fields to the returned object after `designQ`:

```js
      splitRole: p.splitRole || "",
      designQ,
      usInvert: invNum(p.upstreamInvert),
      dsInvert: invNum(p.downstreamInvert)
```

- [ ] **Step 2: Run the drift test to verify it fails**

Run: `node visualizer\visualizer-tests\samples-drift.test.js`
Expected: FAIL — "pipes drifted from seedExample() — update SAMPLES[\"calculator-demo\"]" because the embedded sample has no usInvert/dsInvert.

- [ ] **Step 3: Add inverts to both embedded samples**

In `visualizer/storm-drain-visualizer-dev.html`, `const SAMPLES`:

**calculator-demo pipes** (verify each pair against `seedExample()` in `drainage-calculator/storm-drain-design-calculator-dev.html` lines 1529-1555 before typing):

```js
// P1: usInvert: 102, dsInvert: 101
// P2: usInvert: 101.96, dsInvert: 101
// P3: usInvert: 101, dsInvert: 100.6
// P4: usInvert: 100.6, dsInvert: 100
// P5: usInvert: 97.6, dsInvert: 97
```

**bburg-simplified pipes**:

```js
// B1 (I-1 → MH-1, 15"): usInvert: 68.15, dsInvert: 67.35
// B2 (MH-1 → CULVERT, 24"): usInvert: 67.35, dsInvert: 67
```

Add each as a property in the pipe object literal, e.g. `usInvert: 102, dsInvert: 101,`.

- [ ] **Step 4: Run the drift test to verify it passes**

Run: `node visualizer\visualizer-tests\samples-drift.test.js`
Expected: PASS — embedded inverts now match `seedExample()`.

- [ ] **Step 5: Run the full suite**

Run: `cd visualizer\visualizer-tests` then `npm test`
Expected: all green. samples.test.js still passes (structure counts and hglMethod unchanged). The calculator-demo now legitimately triggers the drop banner for SPLIT-1 (3.0 ft, P3 100.6 → P5 97.6) — no existing test asserts its absence, but if samples.test.js asserts banner text, verify the new line renders correctly instead of failing on absence.

- [ ] **Step 6: Commit**

```bash
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/samples-drift.test.js
git commit -m "feat(visualizer): v82.1 sample inverts pinned by drift guard"
```

---

### Task 6: Full suite, build, and built-file smoke

**Files:**
- Modify: nothing new — verification only.

- [ ] **Step 1: Run the entire test suite**

Run: `cd visualizer\visualizer-tests` then `npm test`
Expected: ALL tests green (99 prior + ~19 new across inverts.test.js, inverts-walk.test.js, inverts-warnings.test.js, drift extension).

- [ ] **Step 2: Build the distributable**

Run from repo root: `node visualizer\build-visualizer.js`
Expected: `visualizer/storm-drain-visualizer.html` regenerated. Verify the offline rule:

```powershell
Select-String -Path visualizer\storm-drain-visualizer.html -Pattern "https?://" | Select-Object -First 5
```

Expected: no remote-script/CSS references (a comment URL or two inside the SheetJS bundle is fine — check they are not `<script src=`/`<link href=` references).

- [ ] **Step 3: Smoke the BUILT file headless**

Write `C:\Users\khngu\AppData\Local\Temp\smoke_inverts.cjs` (pattern: the existing `smoke_built.cjs`) and run `node C:\Users\khngu\AppData\Local\Temp\smoke_inverts.cjs`. It must:
1. Boot the built file in JSDOM (runScripts dangerously, ResizeObserver polyfill).
2. `sampleSelect.value = "calculator-demo"` + change event → assert `state.imported.pipes` carry inverts (P1 usInvert 102, dsInvert 101).
3. Run `buildLedger` + `annotateLedgerHgl` via `window` on the sample's default path under hec22 → assert some hf row has `hglDn` equal to its pipe's `dsInvert + barrel height` (e.g. P1: 101 + 2 = 103).
4. Assert `state.analysis.dropStructures` contains SPLIT-1 with dropFt 3.
5. Switch to bburg-simplified → assert B1 usInvert 68.15 and the walk runs without errors.
6. Print `SMOKE OK` / `SMOKE FAILED` and set exitCode accordingly.

- [ ] **Step 4: Final git status check**

Run: `git status` from repo root
Expected: `visualizer/storm-drain-visualizer-dev.html` and `visualizer/visualizer-tests/` clean (all committed); the built HTML is gitignored and stays untracked. The smoke script lives in the OS temp dir — never commit it.

---

## Self-review notes (for the executor)

- **Spec coverage check:** every spec section maps to a task — Data model → Task 1; barrel-height helper → Task 2; HGL walk floors → Task 2; Profile drawing → Task 3; Derived flowline → Task 3 (flowlineOf); Warnings → Task 4; Built-in samples → Task 5; Testing → Tasks 1-5 test files; drift guard → Task 5; regression → Task 6. Out of scope per spec: calculator changes, iso labels, loss-equation changes, partial-flow engine — none appear here.
- **Fixture floor caveat:** `fixtures/main-app-export.xlsx` has real inverts, so Task 2 Step 6 may require updating pinned HGL expectations in existing tests. That is expected and legitimate — verify each new value is exactly the pipe-end floor (dsInvert + barrel height) before pinning it.
- **Verify-then-edit:** several steps say "read the actual code first" (annotateLedgerHgl scope names, analyzeImported return keys, banner DOM helpers). The line numbers are accurate as of the spec session but the file is large — always read the surrounding code before each edit rather than trusting line numbers alone.
- **SPLIT-1 drop warning** in calculator-demo after Task 5 is correct true geometry, not a bug.


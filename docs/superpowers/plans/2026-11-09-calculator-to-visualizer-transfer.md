# Calculator → Visualizer Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One-click "Open in Visualizer" handoff from the calculator (URL-hash JSON payload with file-download fallback) plus the visualizer honoring the calculator's exported HGL method on import.

**Architecture:** A new `buildVisualizerPayload()` in the calculator serializes the same `computeStructureCalc`/`calcPipeRow` results the xlsx export carries — never a new computation. The visualizer gains (a) a read of the Rainfall Settings `HGL Method` row in its xlsx importer, and (b) a `#data=` URL-hash import that reuses `validateImportedJson` → `applyImportedJson` (never bypassing validation). A drift test pins the payload to the xlsx serialization.

**Tech Stack:** Vanilla JS (single-file HTML apps), SheetJS, jsdom + node:test for both test suites.

**Spec:** `docs/superpowers/specs/2026-11-09-calculator-to-visualizer-transfer-design.md`

---

## Repo rules (binding — read before every task)

- **Edit ONLY the dev files** — `drainage-calculator/storm-drain-design-calculator-dev.html` and `visualizer/storm-drain-visualizer-dev.html`. Never hand-edit built output.
- After every calculator dev-file edit run `node drainage-calculator/build.js`; commit dev **and** built file together. The visualizer built file is **gitignored** — run `node visualizer/build-visualizer.js` to regenerate locally but do NOT commit it.
- Built files must stay ONE self-contained offline HTML (no CDN, no network).
- **Never add LLM attribution to commit messages** (no `Co-Authored-By` lines, no "(Generated with Claude Code)" trailers).
- Never amend commits; create new commits.
- Commit style: `feat(calculator): ...`, `test(calculator): ...`, `feat(visualizer): ...`.
- Work directly on `main` (established practice in this repo, user-approved in prior sessions).

## Test commands

- Calculator suite (loads the **BUILT** calculator — build first):
  ```
  node drainage-calculator/build.js
  cd tests ; node --test run-tests.mjs
  ```
  Currently 97 tests, all must stay green.
- Visualizer suite (loads the **DEV** visualizer via `_harness.js` — no build needed for tests):
  ```
  cd visualizer/visualizer-tests ; npm test
  ```
  Currently 120 tests, all must stay green.

## Key file anchors (verified line numbers, dev files)

**Calculator dev file** (`drainage-calculator/storm-drain-design-calculator-dev.html`):
- Line 631-633: topbar — export button, then the `<a href="visualizer.html">Open HGL Visualizer</a>` link to be replaced.
- Line 6452-6462: `exportExcel()` — insert the new handoff code right after it.
- Line 6787: `document.getElementById("exportBtn").addEventListener("click", exportExcel);` inside `init()` — wire the new button after it.
- Line 6833-6846: `window.__sdc = {...}` test exports.
- Helpers already available at top level: `num(v,def)` (line 5999 — `parseFloat` with fallback, does NOT round), `round(v,d)` (line 6001), `toast(msg,isErr)` (line 2330), `escapeHtml`, `findStructure`, `computeStructureCalc`, `calcPipeRow`, `pipeEffectiveN`, `state` (with `state.project`, `state.hydraulics.hglMethod`, `state.rainfall.pipeStorm`).

**Visualizer dev file** (`visualizer/storm-drain-visualizer-dev.html`):
- Line 601: `validateImportedJson(obj)` → `{valid, errors}`.
- Line 697: `applyImportedJson(obj, fileName)` — sync, throws on invalid; applies `config.hglMethod` when `"hec22"|"legacy-both-crown"` (line 748).
- Line 833: `importFromXlsxFile(file)` — async; builds `state.imported` directly (does NOT route through `applyImportedJson`).
- Line 857-861: `const daRows/tr55Rows/strRows/pipeRows/outRows = sh(...)` — sheet reads.
- Line 983: `config: { stormLabel: "", units: "us-customary", hglMethod: state.ui.hglMethod }`.
- Line 978: `state.ui.fileName = (file && file.name) || "";`.
- Line 1039: `autoLayoutIfNeeded()`.
- Line 2989-2995: bootstrap tail — `window.state = state; ... window.SAMPLES = SAMPLES; renderAll();`.
- Top-level function declarations are automatically `window` properties (that is how tests call `window.importFromXlsxFile`).
- `state.ui.hglMethod` default `"hec22"` (line 115); topbar select id `hglMethodSelect` synced by `syncHglSelect()` in `renderAll()`.
- File-import failure UX is `alert("Import failed: " + err.message)` (line 2985) — the hash path reuses the same error surface.

## Two known subtleties (do not get these wrong)

1. **The xlsx importer does NOT go through `applyImportedJson`** — the spec's Feature A text mentions the config passthrough, but that only exists in `applyImportedJson` (JSON path). The xlsx importer must set `state.ui.hglMethod` itself. Observable behavior is exactly the spec's table.
2. **Label fallback:** the xlsx importer reads structure `label` as `pick("Label", "Description") || structureId` — when `s.desc` is empty, the imported label is the structure ID. The payload must mirror this (`s.desc || s.structureId || s.id || ""`), or the drift test fails.

---

### Task 1: Calculator payload builder `buildVisualizerPayload()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (insert after `exportExcel()`, ~line 6462; extend `__sdc` at line 6833)
- Test: `tests/run-tests.mjs` (append new section)

- [ ] **Step 1: Write the failing tests**

Append to `tests/run-tests.mjs` (new section after the last existing test):

```js
// ==================== Visualizer handoff (transfer spec Feature B) ====================

// Boots the visualizer DEV file headless with the Node xlsx module injected,
// so its real validateImportedJson/applyImportedJson/importFromXlsxFile run.
function loadVisualizerWindow(){
  const vizHtml = readFileSync(new URL("../visualizer/storm-drain-visualizer-dev.html", import.meta.url), "utf8");
  const vizDom = new JSDOM(vizHtml, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(w){ w.XLSX = XLSX_NODE; }
  });
  return vizDom.window;
}

test("buildVisualizerPayload passes the visualizer's validateImportedJson", () => {
  const payload = sdc.buildVisualizerPayload();
  assert.equal(typeof payload, "object", "payload must be an object");
  const viz = loadVisualizerWindow();
  const result = viz.validateImportedJson(payload);
  assert.deepEqual(result.errors, [], "schema validation errors: " + result.errors.join("; "));
  assert.equal(result.valid, true);
  viz.close();
});

test("payload config maps HGL method to visualizer method names", () => {
  const prev = sdc.state.hydraulics.hglMethod;
  try {
    sdc.state.hydraulics.hglMethod = "hec22";
    assert.equal(sdc.buildVisualizerPayload().config.hglMethod, "hec22");
    sdc.state.hydraulics.hglMethod = "conservative";
    assert.equal(sdc.buildVisualizerPayload().config.hglMethod, "legacy-both-crown",
      "calculator Conservative must map to legacy-both-crown, never the literal 'conservative'");
  } finally {
    sdc.state.hydraulics.hglMethod = prev;
  }
});
```

- [ ] **Step 2: Run tests to verify they fail**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: both new tests FAIL (`sdc.buildVisualizerPayload is not a function`).

- [ ] **Step 3: Implement the payload builder**

In `drainage-calculator/storm-drain-design-calculator-dev.html`, insert immediately after the closing `}` of `exportExcel()` (line 6462):

```js
/* =======================================================================
   Visualizer handoff (one-click "Open in Visualizer")
   ======================================================================= */
// Second serialization of the same computeStructureCalc / calcPipeRow results
// the Excel export carries — never a new computation. Field-for-field it
// mirrors what the visualizer's xlsx importer reads from the exported
// workbook; the payload-vs-xlsx drift test pins the two together.
const VISUALIZER_HASH_MAX = 60000; // URL-hash safety guard (~60k chars)

const VISUALIZER_STORM_LABELS = { "1yr":"1-yr","2yr":"2-yr","5yr":"5-yr","10yr":"10-yr",
  "25yr":"25-yr","50yr":"50-yr","100yr":"100-yr","500yr":"500-yr" };

function buildVisualizerPayload(){
  const structures = state.structures.map(s=>{
    const calc = computeStructureCalc(s.id);
    return {
      id: s.structureId || s.id,
      // Mirrors the xlsx importer's label fallback: empty Description falls
      // back to the Structure ID column.
      label: s.desc || s.structureId || s.id || "",
      type: String(s.type || "manhole").toLowerCase(),
      rim: (s.rim===""||s.rim==null) ? null : num(s.rim),
      startElev: (s.startElev===""||s.startElev==null) ? null : num(s.startElev),
      crown: (calc && calc.crown!=null) ? num(calc.crown) : null,
      forceElev: !!s.forceElev,
      capturedQ: round(calc ? calc.captured : 0, 4),
      totalQ: round(calc ? calc.totalFlow : 0, 4),
      Hb: (calc && calc.isBase) ? 0 : round(calc ? calc.Hb : 0, 4),
      elevation: round(calc ? calc.elevation : 0, 3),
      outPipeId: (calc && calc.outPipe) ? calc.outPipe.id : ""
    };
  });

  const pipes = state.pipes.map(p=>{
    const calc = calcPipeRow(p);
    const fromLabel = (findStructure(p.fromStructureId)||{}).structureId || p.fromStructureId || "";
    const toLabel = (findStructure(p.toStructureId)||{}).structureId || p.toStructureId || "";
    return {
      id: p.id,
      fromId: fromLabel,
      toId: toLabel,
      shape: p.shape,
      size: p.size||"",
      n: num(pipeEffectiveN(p), 3),
      slope: num(p.slope, 4),
      length: num(p.length),
      angle: num(p.angle, 0),
      designQ: round(calc.designQ, 4),
      usInvert: (p.upstreamInvert===""||p.upstreamInvert==null) ? null : parseFloat(p.upstreamInvert),
      dsInvert: (p.downstreamInvert===""||p.downstreamInvert==null) ? null : parseFloat(p.downstreamInvert),
      splitRole: String(p.splitRole||"").toLowerCase(),
      // The exported Pipe Sizing sheet has no Hf column, so the xlsx import
      // always yields 0 here; the visualizer recomputes friction itself.
      Hf: 0
    };
  });

  // Outfall + tailwater: mirrors the visualizer's xlsx fallback order exactly
  // (first outfall-type structure's startElev/rim, else lowest startElev,
  // with Outlet Structures fixed-TW override).
  let outfallSid = null, outfallTw = null;
  const outfallStructs = structures.filter(s=>s.type==="outfall");
  if (outfallStructs.length > 0) {
    outfallSid = outfallStructs[0].id;
    outfallTw = outfallStructs[0].startElev != null ? outfallStructs[0].startElev : outfallStructs[0].rim;
  } else if (structures.length > 0) {
    const lowest = structures.slice().sort((a,b)=>((a.startElev||1e9)-(b.startElev||1e9)))[0];
    outfallSid = lowest.id;
    outfallTw = lowest.startElev;
  }
  for (const os of state.outletStructures) {
    const linkedLabel = os.twStructureId ? ((findStructure(os.twStructureId)||{}).structureId||"") : "";
    if (linkedLabel === outfallSid) {
      const tw = (os.twFixed===""||os.twFixed==null) ? null : num(os.twFixed);
      if (tw != null) outfallTw = tw;
    }
  }
  const outfall = { structureId: outfallSid || "", tailwaterElev: outfallTw != null ? outfallTw : 100 };

  const drainageAreas = state.drainage.map(r=>{
    const linked = state.structures.find(s=>s.drainageAreaId===r.id);
    return {
      id: r.structureId||r.id,
      structureId: linked ? (linked.structureId||"") : "",
      areaAc: num(r.area),
      C: num(r.C),
      tc: num(r.tc)
    };
  });

  // TR-55: mirrors the exported sheet's per-type blanks (the xlsx importer's
  // pickNum turns those cells into null).
  const tr55Segments = [];
  state.drainage.forEach(r=>{
    const segs = (r.tr55 && r.tr55.segments) || [];
    segs.forEach((seg,i)=>{
      const segNum = (v)=> (v===""||v==null) ? null : num(v);
      tr55Segments.push({
        drainageAreaId: r.structureId||r.id,
        order: i+1,
        type: seg.type,
        n: (seg.type==="sheet"||seg.type==="channel") ? segNum(seg.n) : null,
        L: segNum(seg.L),
        s: segNum(seg.s),
        P2: seg.type==="sheet" ? segNum(seg.P2) : null,
        surface: seg.type==="shallow" ? (seg.surface||"unpaved") : null,
        area: seg.type==="channel" ? segNum(seg.area) : null,
        wp: seg.type==="channel" ? segNum(seg.wp) : null
      });
    });
  });

  return {
    schemaVersion: 1,
    sourceApp: "storm-drain-design-calculator",
    structures, pipes, outfall,
    drainageAreas, tr55Segments,
    config: {
      stormLabel: VISUALIZER_STORM_LABELS[state.rainfall.pipeStorm||"10yr"] || (state.rainfall.pipeStorm||""),
      units: "us-customary",
      hglMethod: (state.hydraulics && state.hydraulics.hglMethod) === "conservative" ? "legacy-both-crown" : "hec22"
    }
  };
}
```

Then extend `window.__sdc` (line 6833): append `buildVisualizerPayload, VISUALIZER_HASH_MAX,` to the object literal (e.g. right after `buildFormulasReferenceSheet,`). Tasks 3 and 4 will add `encodeVisualizerHandoff,` and `openInVisualizer,` to the same line.

- [ ] **Step 4: Run tests to verify they pass**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: 99 passing (97 existing + 2 new), 0 failing.

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "feat(calculator): visualizer handoff payload builder"
```

---

### Task 2: Drift guard — payload matches xlsx import

**Files:**
- Test: `tests/run-tests.mjs` (append; uses `loadVisualizerWindow` from Task 1)
- Fix (only if the test finds mismatches): `drainage-calculator/storm-drain-design-calculator-dev.html` `buildVisualizerPayload()`

- [ ] **Step 1: Write the failing-or-passing guard test**

Append to `tests/run-tests.mjs`:

```js
// Compare what the visualizer state holds after importing the JSON payload
// vs after importing the xlsx export of the SAME state. Numbers rounded to
// 5 decimals to absorb float noise; JSON round-trip puts both sides in the
// Node realm. x/y and pipe Hf are excluded (xlsx fills 0, payload omits —
// auto-layout assigns real coordinates either way).
function curatedImported(imported){
  return JSON.parse(JSON.stringify({
    structures: imported.structures.map(s=>({
      id:s.id, label:s.label, type:s.type, rim:s.rim, startElev:s.startElev, crown:s.crown,
      forceElev:s.forceElev, capturedQ:s.capturedQ, totalQ:s.totalQ, Hb:s.Hb,
      elevation:s.elevation, outPipeId:s.outPipeId })),
    pipes: imported.pipes.map(p=>({
      id:p.id, fromId:p.fromId, toId:p.toId, shape:p.shape, size:p.size, n:p.n,
      slope:p.slope, length:p.length, angle:p.angle, designQ:p.designQ,
      usInvert:p.usInvert, dsInvert:p.dsInvert, splitRole:p.splitRole })),
    outfall: imported.outfall,
    config: { hglMethod: imported.config.hglMethod },
    drainageAreas: imported.drainageAreas,
    tr55Segments: imported.tr55Segments
  }), (k,v)=> (typeof v==="number" && isFinite(v)) ? Number(v.toFixed(5)) : v);
}

// `window` here is the CALCULATOR's jsdom window (module top of this file);
// window.XLSX is the SheetJS bundled inside the BUILT calculator. Write the
// workbook in that realm, then wrap the bytes in a plain object (name +
// arrayBuffer) so the visualizer's importer runs its real code path without
// needing a jsdom File.
async function importExportedWorkbook(viz){
  const ab = window.XLSX.write(sdc.buildWorkbook(), { bookType:"xlsx", type:"array", bookSST:true });
  const fakeFile = { name:"drift.xlsx", arrayBuffer: async ()=> Buffer.from(new Uint8Array(ab)) };
  await viz.importFromXlsxFile(fakeFile);
}

test("visualizer payload matches xlsx import (drift guard, HEC-22)", async () => {
  const viz = loadVisualizerWindow();
  try {
    const payload = sdc.buildVisualizerPayload();
    await importExportedWorkbook(viz);
    const viaXlsx = curatedImported(viz.state.imported);
    viz.applyImportedJson(payload, "(test)");
    const viaJson = curatedImported(viz.state.imported);
    assert.deepEqual(viaJson, viaXlsx, "JSON payload drifted from the xlsx serialization");
    assert.equal(viaXlsx.config.hglMethod, "hec22");
  } finally {
    viz.close();
  }
});

test("visualizer payload matches xlsx import (drift guard, Conservative)", async () => {
  const prev = sdc.state.hydraulics.hglMethod;
  sdc.state.hydraulics.hglMethod = "conservative";
  const viz = loadVisualizerWindow();
  try {
    const payload = sdc.buildVisualizerPayload();
    await importExportedWorkbook(viz);
    const viaXlsx = curatedImported(viz.state.imported);
    viz.applyImportedJson(payload, "(test)");
    const viaJson = curatedImported(viz.state.imported);
    assert.deepEqual(viaJson, viaXlsx, "Conservative payload drifted from the xlsx serialization");
    assert.equal(viaXlsx.config.hglMethod, "legacy-both-crown");
  } finally {
    sdc.state.hydraulics.hglMethod = prev;
    viz.close();
  }
});
```

- [ ] **Step 2: Run the tests**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: 101 passing. If a drift assertion fails, read the diff carefully — the fix belongs in `buildVisualizerPayload()` (mirror the xlsx cell value exactly, including the `num()` fallbacks and null-vs-blank semantics). Do NOT change the visualizer importer or `buildWorkbook` to make the test pass.

- [ ] **Step 3: Commit**

```
git add tests/run-tests.mjs drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html
git commit -m "test(calculator): payload-vs-xlsx drift guard"
```

---

### Task 3: Hash encoding + 60k size guard

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (after `buildVisualizerPayload`, which was added in Task 1)
- Test: `tests/run-tests.mjs` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/run-tests.mjs`:

```js
test("hash handoff encoding round-trips the payload", () => {
  const payload = sdc.buildVisualizerPayload();
  const enc = sdc.encodeVisualizerHandoff(payload);
  assert.equal(typeof enc, "string", "seed payload must fit under the guard");
  assert.ok(enc.length <= sdc.VISUALIZER_HASH_MAX);
  assert.deepEqual(JSON.parse(decodeURIComponent(enc)), JSON.parse(JSON.stringify(payload)));
});

test("hash handoff size guard trips on oversized payloads", () => {
  const big = sdc.buildVisualizerPayload();
  big.structures[0].label = "x".repeat(70000);
  assert.equal(sdc.encodeVisualizerHandoff(big), null, "oversized payload must return null");
});
```

- [ ] **Step 2: Run to verify failure**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: both new tests FAIL (`sdc.encodeVisualizerHandoff is not a function`).

- [ ] **Step 3: Implement**

In the calculator dev file, directly after `buildVisualizerPayload()` (same section), add:

```js
// Encode for the #data= URL-hash protocol. Returns the encoded string, or
// null when it exceeds the size guard (caller falls back to file download).
function encodeVisualizerHandoff(payload){
  const encoded = encodeURIComponent(JSON.stringify(payload));
  return encoded.length <= VISUALIZER_HASH_MAX ? encoded : null;
}
```

Extend `window.__sdc` with `encodeVisualizerHandoff,` (Task 1 already added `VISUALIZER_HASH_MAX`).

- [ ] **Step 4: Run to verify pass**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: 103 passing.

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "feat(calculator): hash handoff encoding with 60k guard"
```

---

### Task 4: "Open in Visualizer" button + fallbacks

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html` (topbar HTML line 632-633; handoff section after `encodeVisualizerHandoff`; `init()` wiring after line 6787; `__sdc`)
- Test: `tests/run-tests.mjs` (append one smoke test)

- [ ] **Step 1: Write the failing smoke test**

Append to `tests/run-tests.mjs`:

```js
test("Open in Visualizer button exists in the built toolbar", () => {
  assert.ok(window.document.getElementById("openVisualizerBtn"), "openVisualizerBtn missing");
  assert.equal(window.document.getElementById("openVisualizerBtn").tagName, "BUTTON");
});
```

- [ ] **Step 2: Run to verify failure**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: new test FAILS (button absent).

- [ ] **Step 3: Implement**

3a. Replace the topbar link (lines 632-633):

```html
        <a href="visualizer.html" target="_blank" rel="noopener"
           style="margin-left:12px; color:inherit; font-size:13px;">Open HGL Visualizer &rarr;</a>
```
with:

```html
        <button class="btn btn-sm" id="openVisualizerBtn" title="Send the current project to the HGL/EGL visualizer">Open in Visualizer</button>
```

3b. In the handoff section (after `encodeVisualizerHandoff`), add:

```js
function downloadVisualizerPayload(payload){
  const name = (state.project||"storm-drain-project").replace(/[^a-z0-9\-_ ]/gi,"").trim().replace(/\s+/g,"-") || "storm-drain-project";
  const blob = new Blob([JSON.stringify(payload,null,2)], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name + "-visualizer.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 5000);
}

function openInVisualizer(){
  if(!state.structures.length){
    toast("Nothing to send yet — add structures first.", true);
    return;
  }
  let payload;
  try { payload = buildVisualizerPayload(); }
  catch(err){ console.error(err); toast("Visualizer handoff failed: "+escapeHtml(err.message), true); return; }
  const encoded = encodeVisualizerHandoff(payload);
  if(!encoded){
    downloadVisualizerPayload(payload);
    toast("Project too large for a one-click link — downloaded the visualizer JSON instead. Import it in the visualizer.");
    return;
  }
  const hashUrl = (base)=> base + "#data=" + encoded;
  if(location.protocol === "file:"){
    // Offline: cross-tab load-failure detection is unreliable and file://
    // cannot be probed synchronously, so always offer the downloaded file
    // alongside the open attempt (binding simplification in the spec).
    downloadVisualizerPayload(payload);
    const w1 = window.open(hashUrl("visualizer.html"), "_blank");
    if(!w1) window.open(hashUrl("../visualizer/storm-drain-visualizer.html"), "_blank");
    toast("If the visualizer didn't open, import the downloaded JSON in the visualizer.");
  } else {
    const w = window.open(hashUrl("visualizer.html"), "_blank");
    if(!w){
      downloadVisualizerPayload(payload);
      toast("Popup blocked — downloaded the visualizer JSON. Import it in the visualizer.");
    }
  }
}
```

3c. In `init()`, after the `exportBtn` listener line (6787), add:

```js
  document.getElementById("openVisualizerBtn").addEventListener("click", openInVisualizer);
```

3d. Extend `window.__sdc` with `openInVisualizer,`.

- [ ] **Step 4: Run to verify pass + full suite**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs
```
Expected: 104 passing.

- [ ] **Step 5: Manual UI smoke (repo rule: verify UI features in a browser)**

Open `drainage-calculator/storm-drain-design-calculator.html` by double-click (file://). Verify: button visible in topbar; click opens `visualizer.html` (copy `visualizer/storm-drain-visualizer.html` next to the built calculator first — the sibling-path convention) and the visualizer loads the project from the hash with fileName "(from calculator)"; the downloaded `<project>-visualizer.json` also imports via the visualizer's Import button. Report the result honestly — if a step cannot be verified in this environment, say so.

- [ ] **Step 6: Commit**

```
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "feat(calculator): Open in Visualizer button with download fallback"
```

---

### Task 5: Visualizer xlsx importer honors HGL Method

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (`importFromXlsxFile`, insert after the `outRows` read ~line 861 and set method before `state.imported` build ~line 978)
- Test: `visualizer/visualizer-tests/xlsx-import.test.js` (append)

- [ ] **Step 1: Write the failing tests**

Append to `visualizer/visualizer-tests/xlsx-import.test.js`:

```js
// ==================== HGL Method row (transfer spec Feature A) ====================

function buildWorkbookWithHglMethod(hglValue) {
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([
    { "Structure ID": "OUT", "Type": "outfall", "Fixed-Start Elev (ft)": 100 },
    { "Structure ID": "S", "Type": "inlet", "Rim-Grate Elev (ft)": 110 }
  ]), "Junction Structure");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([
    { "ID": "P1", "From Structure": "S", "To Structure": "OUT", "Shape": "circular",
      "Size (in or SPANxRISE)": 18, "n": 0.013, "Slope (ft-ft)": 0.005, "Length (ft)": 100 }
  ]), "Pipe Sizing");
  if (hglValue !== undefined) {
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
      ["Rainfall Source", "noaa"],
      ["HGL Method", hglValue]
    ]), "Rainfall Settings");
  }
  return wb;
}

async function importHglWorkbook(window, hglValue) {
  ensureFileArrayBuffer(window);
  const arr = XLSX.write(buildWorkbookWithHglMethod(hglValue), { type: "array", bookType: "xlsx", bookSST: true });
  const blob = new window.Blob([arr], { type: XLSX_TYPE });
  const file = new window.File([blob], "hgl.xlsx", { type: XLSX_TYPE });
  await window.importFromXlsxFile(file);
}

test("xlsx 'HGL Method: Conservative' sets legacy-both-crown", async () => {
  const { window } = loadVisualizer({ XLSX });
  await importHglWorkbook(window, "Conservative");
  assert.strictEqual(window.state.ui.hglMethod, "legacy-both-crown");
  assert.strictEqual(window.state.imported.config.hglMethod, "legacy-both-crown");
});

test("xlsx 'HGL Method: HEC-22' sets hec22", async () => {
  const { window } = loadVisualizer({ XLSX });
  window.state.ui.hglMethod = "legacy-both-crown"; // must be overridden by the sheet
  await importHglWorkbook(window, "HEC-22");
  assert.strictEqual(window.state.ui.hglMethod, "hec22");
});

test("xlsx with no HGL Method row leaves the current method untouched", async () => {
  const { window } = loadVisualizer({ XLSX });
  window.state.ui.hglMethod = "legacy-both-crown";
  await importHglWorkbook(window, undefined); // no Rainfall Settings sheet at all
  assert.strictEqual(window.state.ui.hglMethod, "legacy-both-crown");
});

test("xlsx with unrecognized HGL Method value leaves the current method untouched", async () => {
  const { window } = loadVisualizer({ XLSX });
  window.state.ui.hglMethod = "hec22";
  await importHglWorkbook(window, "Weird Method");
  assert.strictEqual(window.state.ui.hglMethod, "hec22");
});
```

- [ ] **Step 2: Run to verify failure**

```
cd visualizer/visualizer-tests ; npm test
```
Expected: 4 new tests FAIL (first two: method not applied; last two: pass vacuously today — the first two are the real red signal).

- [ ] **Step 3: Implement**

In `visualizer/storm-drain-visualizer-dev.html`, inside `importFromXlsxFile`, after the `const outRows = sh("Outlet Structures");` line, add:

```js
    // Rainfall Settings: honor the calculator's HGL method row. The sheet is
    // a label/value AoA with no header row, so read it as rows. A missing row
    // or unrecognized value leaves the current method untouched (old exports
    // behave exactly as before).
    let hglMethodFromSheet = null;
    if (wb.Sheets["Rainfall Settings"]) {
      const rfAoA = XLSX.utils.sheet_to_json(wb.Sheets["Rainfall Settings"], { header: 1, defval: null });
      for (const row of rfAoA) {
        if (row && String(row[0]).trim() === "HGL Method") {
          const v = String(row[1] == null ? "" : row[1]).trim();
          if (v === "HEC-22") hglMethodFromSheet = "hec22";
          else if (v === "Conservative") hglMethodFromSheet = "legacy-both-crown";
        }
      }
    }
    if (hglMethodFromSheet) state.ui.hglMethod = hglMethodFromSheet;
```

The `state.imported` config literal (line 983) already reads `hglMethod: state.ui.hglMethod`, so setting `state.ui.hglMethod` BEFORE the state build makes both the UI select (synced by `renderAll` → `syncHglSelect`) and `state.imported.config` correct. Place the `if (hglMethodFromSheet) ...` line immediately before `state.ui.fileName = ...` (line 978).

- [ ] **Step 4: Run to verify pass + full suite**

```
cd visualizer/visualizer-tests ; npm test
```
Expected: 124 passing (120 + 4).

- [ ] **Step 5: Build and manual smoke**

```
node visualizer/build-visualizer.js
```
Open the built visualizer, import a calculator export with `HGL Method: Conservative` (export one from the calculator after switching the Rainfall & IDF method selector) and confirm the topbar select flips to "Legacy both-crown". The built file is gitignored — do not commit it.

- [ ] **Step 6: Commit**

```
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/xlsx-import.test.js
git commit -m "feat(visualizer): honor calculator HGL Method on xlsx import"
```

---

### Task 6: Visualizer `#data=` hash import

**Files:**
- Modify: `visualizer/storm-drain-visualizer-dev.html` (new `importFromHash` after `applyImportedJson` ends ~line 761; bootstrap tail ~line 2991)
- Modify: `visualizer/visualizer-tests/_harness.js` (optional opts: url, virtualConsole)
- Test: `visualizer/visualizer-tests/hash-import.test.js` (new file)

- [ ] **Step 1: Extend the harness**

In `visualizer/visualizer-tests/_harness.js`, change `loadVisualizer` to accept a second argument (backward compatible — existing callers pass one argument):

```js
function loadVisualizer(extraHeadScripts, opts) {
  opts = opts || {};
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");
  // Replace the SHEETJS sentinel with an inlined bundle when needed; tests pass
  // extraHeadScripts to inject the real `xlsx` module into globalThis.
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    url: opts.url,
    virtualConsole: opts.virtualConsole,
    beforeParse(window) {
      if (extraHeadScripts && extraHeadScripts.XLSX) window.XLSX = extraHeadScripts.XLSX;
    }
  });
  return {
    dom,
    window: dom.window,
    document: dom.window.document,
    // Grab any inlined function by name from window scope.
    fn: (name) => dom.window[name]
  };
}
```

- [ ] **Step 2: Write the failing tests**

Create `visualizer/visualizer-tests/hash-import.test.js`:

```js
/*
 * One-click handoff from the calculator: #data=<encoded JSON> URL hash.
 * Valid payloads load through the shared applyImportedJson path; garbage
 * hashes must never crash the app (empty start + error surfaced + hash
 * stripped so a refresh does not retry).
 */
const test = require("node:test");
const assert = require("node:assert");
const { VirtualConsole } = require("jsdom");
const { loadVisualizer } = require("./_harness");

function samplePayload() {
  return {
    schemaVersion: 1,
    sourceApp: "storm-drain-design-calculator",
    structures: [
      { id: "A", type: "manhole", rim: 110, startElev: null, crown: 104 },
      { id: "OUT", type: "outfall", rim: null, startElev: 100, crown: null }
    ],
    pipes: [
      { id: "P1", fromId: "A", toId: "OUT", shape: "circular", size: 18,
        n: 0.013, slope: 0.005, length: 100, designQ: 2.5 }
    ],
    outfall: { structureId: "OUT", tailwaterElev: 100 },
    config: { stormLabel: "10-yr", units: "us-customary", hglMethod: "legacy-both-crown" }
  };
}

test("#data= hash loads through the shared import path at boot", () => {
  const payload = samplePayload();
  const url = "http://localhost/visualizer.html#data=" + encodeURIComponent(JSON.stringify(payload));
  const viz = loadVisualizer(null, { url });
  const w = viz.window;
  assert.ok(w.state.imported, "hash payload not imported");
  assert.strictEqual(w.state.imported.structures.length, 2);
  assert.strictEqual(w.state.ui.fileName, "(from calculator)");
  assert.strictEqual(w.document.getElementById("fileName").textContent, "(from calculator)");
  assert.strictEqual(w.location.hash, "", "hash must be stripped after import");
  assert.strictEqual(w.state.ui.hglMethod, "legacy-both-crown", "config.hglMethod must apply");
});

test("garbage #data= hash: no crash, empty start, error surfaced, hash stripped", () => {
  const vc = new VirtualConsole();
  const alerts = [];
  vc.on("jsdomError", (e) => {
    if (String(e.message || "").includes("window.alert")) alerts.push(String(e.message));
  });
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html#data=%ZZ-not-json", virtualConsole: vc });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null, "must start empty");
  assert.strictEqual(w.location.hash, "", "hash must be stripped");
  assert.strictEqual(w.state.ui.fileName, "");
  assert.ok(alerts.length > 0, "the import-error alert must fire");
});

test("importFromHash works when the visualizer is already open", () => {
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html" });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null);
  w.location.hash = "#data=" + encodeURIComponent(JSON.stringify(samplePayload()));
  assert.strictEqual(w.importFromHash(), true);
  assert.ok(w.state.imported, "payload imported on live page");
  assert.strictEqual(w.state.ui.hglMethod, "legacy-both-crown");
  assert.strictEqual(w.location.hash, "");
});

test("non-#data= hash is ignored (normal startup)", () => {
  const viz = loadVisualizer(null, { url: "http://localhost/visualizer.html#section" });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null);
  assert.strictEqual(w.location.hash, "#section", "unrelated hash must be untouched");
});

test("#data= hash with schema-invalid payload surfaces the error and starts empty", () => {
  const vc = new VirtualConsole();
  const alerts = [];
  vc.on("jsdomError", (e) => {
    if (String(e.message || "").includes("window.alert")) alerts.push(String(e.message));
  });
  const bad = { schemaVersion: 1, sourceApp: "x", structures: "not-an-array" };
  const url = "http://localhost/visualizer.html#data=" + encodeURIComponent(JSON.stringify(bad));
  const viz = loadVisualizer(null, { url, virtualConsole: vc });
  const w = viz.window;
  assert.strictEqual(w.state.imported, null, "invalid payload must not import");
  assert.strictEqual(w.location.hash, "");
  assert.ok(alerts.length > 0, "validation errors must surface");
});
```

- [ ] **Step 3: Run to verify failure**

```
cd visualizer/visualizer-tests ; npm test
```
Expected: 4-5 new tests FAIL (boot-time hash not consumed; `importFromHash` undefined).

- [ ] **Step 4: Implement**

4a. In `visualizer/storm-drain-visualizer-dev.html`, directly after `applyImportedJson` ends (after the line `state.ui.lastCursorId = null;` that closes it, ~line 761), add:

```js
  // --- one-click handoff from the calculator (transfer spec Feature B) ---
  // URL hash protocol: #data=<encodeURIComponent(JSON.stringify(payload))>.
  // Consumed at boot (before the first render) and on hashchange (visualizer
  // tab already open). Reuses applyImportedJson — never bypasses validation.
  function importFromHash() {
    const HASH_PREFIX = "#data=";
    const h = window.location.hash || "";
    if (!h.startsWith(HASH_PREFIX)) return false;

    let payload = null;
    let parseErr = null;
    try {
      payload = JSON.parse(decodeURIComponent(h.slice(HASH_PREFIX.length)));
    } catch (e) {
      parseErr = e;
    }
    const result = payload
      ? validateImportedJson(payload)
      : { valid: false, errors: ["handoff payload is not valid JSON" + (parseErr ? ": " + parseErr.message : "")] };

    // Strip the hash either way so a refresh does not re-import.
    history.replaceState(null, "", window.location.href.split("#")[0]);

    if (!result.valid) {
      // Same error surface as a failed file import.
      alert("Import failed: " + result.errors.join("; "));
      return true;
    }

    applyImportedJson(payload, "(from calculator)");
    const nameSpan = document.getElementById("fileName");
    if (nameSpan) nameSpan.textContent = "(from calculator)";
    return true;
  }
```

4b. In the bootstrap tail, change:

```js
  window.state = state;
  window.KB_SEED = KB_SEED;
  window.TABLE_4_6 = TABLE_4_6;
  window.SAMPLES = SAMPLES;
  renderAll();
```
to:

```js
  window.state = state;
  window.KB_SEED = KB_SEED;
  window.TABLE_4_6 = TABLE_4_6;
  window.SAMPLES = SAMPLES;
  // One-click handoff: consume a #data= hash before the first render.
  if (importFromHash()) autoLayoutIfNeeded();
  window.addEventListener("hashchange", () => {
    if (importFromHash()) { autoLayoutIfNeeded(); renderAll(); }
  });
  renderAll();
```

(`history.replaceState` does not fire `hashchange`, so there is no loop. `importFromHash` is a top-level function declaration, so it is automatically reachable as `window.importFromHash` by the test harness.)

- [ ] **Step 5: Run to verify pass + full suite**

```
cd visualizer/visualizer-tests ; npm test
```
Expected: 129 passing (124 from Task 5 + 5 new).

- [ ] **Step 6: Build and manual smoke**

```
node visualizer/build-visualizer.js
```
End-to-end check in a browser: from the built calculator click "Open in Visualizer" (with `visualizer.html` copied as its sibling, or on the deployed layout); the visualizer tab must show fileName "(from calculator)", the project renders, and refreshing the tab starts the visualizer normally (hash gone). Report honestly if this cannot be verified locally.

- [ ] **Step 7: Commit**

```
git add visualizer/storm-drain-visualizer-dev.html visualizer/visualizer-tests/_harness.js visualizer/visualizer-tests/hash-import.test.js
git commit -m "feat(visualizer): one-click #data= hash handoff import"
```

---

### Task 7: Final verification

**Files:** none new — verification only (plus fixes if anything is red).

- [ ] **Step 1: Rebuild both and run both suites**

```
node drainage-calculator/build.js
cd tests ; node --test run-tests.mjs        # expect 104 passing
cd .. ; cd visualizer/visualizer-tests ; npm test   # expect 129 passing
```

- [ ] **Step 2: Cross-checks against the spec**

- Deployed-site branch: calculator opens `visualizer.html` (relative) with `#data=`; no download unless the guard trips.
- Offline branch: download always offered; both sibling-path candidates attempted per the plan code.
- Method mapping table in the spec matches Task 1 config code and Task 5 importer code exactly.
- No new libraries, no network, no storage; both built files remain self-contained (check the built calculator opens by double-click).
- The spec's caveat (visualizer legacy-both-crown floors both pipe ends ≥ calculator Conservative's upstream-only pin) is behavior-unchanged — nothing in this plan alters the walk math.

- [ ] **Step 3: Commit any fixups, report**

If Steps 1-2 found nothing: no commit; report done. If fixes were needed, commit them with a descriptive message (no LLM attribution).

---

## Self-review notes (plan → spec coverage)

- Feature A method mapping (xlsx row read + JSON payload mapped value): Tasks 1, 5. ✅
- Feature B payload builder, empty-state guard, hash protocol, size guard, URL resolution, popup-blocked fallback, garbage-hash safety: Tasks 1, 3, 4, 6. ✅
- Spec testing items 1-8: Task 1 (items 1, 3), Task 2 (item 2), Task 3 (item 4), Task 5 (item 7), Task 6 (items 5, 6; item 8 — JSON config passthrough — already covered by an existing test, no extension needed). ✅
- Known deviation, documented: the spec's Feature A change text cites `applyImportedJson`'s config passthrough, but the xlsx importer bypasses `applyImportedJson`; Task 5 sets `state.ui.hglMethod` directly in the importer. Observable behavior matches the spec's table exactly.
- The visualizer test suite loads the DEV file (spec says "BUILT visualizer" — the established `_harness.js` loads dev with injected XLSX; dev and built differ only by the inlined SheetJS, which tests inject anyway).

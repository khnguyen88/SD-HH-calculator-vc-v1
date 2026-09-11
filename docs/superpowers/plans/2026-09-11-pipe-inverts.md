# Pipe Inverts & Computed Slope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add US/DS invert inputs to each pipe; auto-compute slope from `(US − DS) / L` when both are set; fall back to manual slope entry when inverts are absent; display outgoing-pipe inverts in the HGL and HGL-25yr tabs.

**Architecture:** A single `pipeEffectiveSlope(pipe)` helper is the sole reader of slope for all calc and display functions. `renderPipes` grows two input columns (US Inv, DS Inv) and a context-sensitive slope cell. `renderHgl` / `renderHgl25` each gain two read-only invert columns sourced from `calc.outPipe`. Excel export/import gains the two new columns on the Pipe Sizing sheet.

**Tech Stack:** Vanilla JS, single HTML file (`drainage-calculator/storm-drain-design-calculator.html`), Node test runner + JSDOM (`tests/run-tests.mjs`).

---

## File Structure

**Only two files modified:**
- `drainage-calculator/storm-drain-design-calculator.html` — all logic and UI changes
- `tests/run-tests.mjs` — new tests for `pipeEffectiveSlope`, export columns

---

## Task 1: Add `pipeEffectiveSlope()` helper, update `calcPipeRow`, expose on `__sdc`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (~line 1660 for `calcPipeRow`; ~line 5838 for `__sdc`)
- Modify: `tests/run-tests.mjs` (append new tests)

- [ ] **Step 1: Write the failing tests**

  Append to `tests/run-tests.mjs`:
  ```js
  // ==================== pipeEffectiveSlope ====================
  test("pipeEffectiveSlope: computes (US-DS)/L when both inverts and length set", () => {
    // US=105.0, DS=104.0, L=200 → (105-104)/200 = 0.005
    const pipe = { upstreamInvert:"105.0", downstreamInvert:"104.0", slope:"0.001", length:"200" };
    isClose(sdc.pipeEffectiveSlope(pipe), 0.005, 0.00001, "invert-derived slope");
  });
  test("pipeEffectiveSlope: falls back to slope field when both inverts absent", () => {
    const pipe = { upstreamInvert:"", downstreamInvert:"", slope:"0.007", length:"200" };
    isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "manual slope fallback");
  });
  test("pipeEffectiveSlope: falls back to slope field when one invert absent", () => {
    const pipe = { upstreamInvert:"105.0", downstreamInvert:"", slope:"0.007", length:"200" };
    isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "partial invert fallback");
  });
  test("pipeEffectiveSlope: falls back to slope field when length absent", () => {
    const pipe = { upstreamInvert:"105.0", downstreamInvert:"104.0", slope:"0.007", length:"" };
    isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "no length fallback");
  });
  ```

- [ ] **Step 2: Run tests — confirm 4 failures**

  ```
  cd tests && npm test 2>&1 | grep -E "fail|pipeEffectiveSlope"
  ```
  Expected: 4 failures mentioning `pipeEffectiveSlope`.

- [ ] **Step 3: Insert `pipeEffectiveSlope` immediately before `calcPipeRow`**

  Find at ~line 1660:
  ```js
  function calcPipeRow(row){
  ```
  Insert immediately before it:
  ```js
  function pipeEffectiveSlope(pipe){
    const US = parseFloat(pipe.upstreamInvert);
    const DS = parseFloat(pipe.downstreamInvert);
    const L  = parseFloat(pipe.length);
    if(isFinite(US) && isFinite(DS) && isFinite(L) && L > 0) return (US - DS) / L;
    return parseFloat(pipe.slope);
  }
  ```

- [ ] **Step 4: Update `calcPipeRow` to use `pipeEffectiveSlope`**

  At ~line 1664, replace:
  ```js
    const n = parseFloat(row.n), S = parseFloat(row.slope);
  ```
  With:
  ```js
    const n = parseFloat(row.n), S = pipeEffectiveSlope(row);
  ```

- [ ] **Step 5: Expose `pipeEffectiveSlope` on `window.__sdc`**

  Find at ~line 5838:
  ```js
  window.__sdc = { state, buildWorkbook, computeTotalFlow, computeStructureCalc, calcPipeRow, calcDrainageRow, findStructure, findDrainage, findPipe,
  ```
  Replace with:
  ```js
  window.__sdc = { state, buildWorkbook, computeTotalFlow, computeStructureCalc, calcPipeRow, pipeEffectiveSlope, calcDrainageRow, findStructure, findDrainage, findPipe,
  ```

- [ ] **Step 6: Run tests — confirm all pass**

  ```
  cd tests && npm test 2>&1 | tail -8
  ```
  Expected: `# pass 40`, `# fail 0`.

- [ ] **Step 7: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
  git commit -m "Task 1: add pipeEffectiveSlope helper, update calcPipeRow, expose on __sdc"
  ```

---

## Task 2: Update `renderPipes()` — new invert columns + smart slope cell; update `renderPipeSizing25`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (~line 2498, 2505–2533, 3291)

- [ ] **Step 1: Add `upstreamInvert` and `downstreamInvert` to the Add Row button**

  At ~line 2498, replace:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row"),
  ```
  With:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, upstreamInvert:"", downstreamInvert:"", slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row"),
  ```

- [ ] **Step 2: Add column headers for US Inv and DS Inv**

  At ~line 2507, replace:
  ```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"n"), el("th",{},"Slope (ft/ft)"), el("th",{},"Length (ft)"),
  ```
  With:
  ```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"n"), el("th",{},"US Inv\n(ft)"), el("th",{},"DS Inv\n(ft)"), el("th",{},"Slope (ft/ft)"), el("th",{},"Length (ft)"),
  ```

- [ ] **Step 3: Add invert input cells and replace slope cell with context-sensitive logic**

  At ~line 2521–2523, replace:
  ```js
        el("td",{}, txtInput(row,"size",80)),
        el("td",{}, numInput(row,"n",60)),
        el("td",{}, numInput(row,"slope",75)),
  ```
  With:
  ```js
        el("td",{}, txtInput(row,"size",80)),
        el("td",{}, numInput(row,"n",60)),
        el("td",{}, numInput(row,"upstreamInvert",70)),
        el("td",{}, numInput(row,"downstreamInvert",70)),
        el("td",{}, (()=>{
          const S = pipeEffectiveSlope(row);
          const hasInverts = (row.upstreamInvert!==""&&row.upstreamInvert!=null) &&
                             (row.downstreamInvert!==""&&row.downstreamInvert!=null) &&
                             (row.length!==""&&row.length!=null);
          return hasInverts
            ? el("td",{class:"out computed-cell"}, isFinite(S)?fmt(S,4):"—")
            : numInput(row,"slope",75);
        })()),
  ```

  Note: the `el("td",{}, ...)` wrapper in the row array means the IIFE returns the inner element only. Replace the whole line with just the IIFE result — the outer `el("td",{})` wrapping `numInput` is already handled inside `numInput`. Use this exact form instead:

  ```js
        el("td",{}, txtInput(row,"size",80)),
        el("td",{}, numInput(row,"n",60)),
        el("td",{}, numInput(row,"upstreamInvert",70)),
        el("td",{}, numInput(row,"downstreamInvert",70)),
        (()=>{
          const S = pipeEffectiveSlope(row);
          const hasInverts = row.upstreamInvert!==""&&row.upstreamInvert!=null&&
                             row.downstreamInvert!==""&&row.downstreamInvert!=null&&
                             row.length!==""&&row.length!=null;
          return hasInverts
            ? el("td",{class:"out computed-cell"}, isFinite(S)?fmt(S,4):"—")
            : el("td",{}, numInput(row,"slope",75));
        })(),
  ```

- [ ] **Step 4: Update `renderPipeSizing25` to use `pipeEffectiveSlope`**

  At ~line 3291, replace:
  ```js
    const S     = parseFloat(row.slope);
  ```
  With:
  ```js
    const S     = pipeEffectiveSlope(row);
  ```

- [ ] **Step 5: Verify in browser**

  Open the calculator. Go to Pipe Sizing & Capacity tab. Confirm:
  - Two new columns "US Inv (ft)" and "DS Inv (ft)" appear between n and Slope.
  - With inverts blank: Slope cell is an editable input.
  - Enter US Inv = 105.0, DS Inv = 104.0, Length = 200 on any pipe row: Slope cell becomes a computed display showing 0.0050.
  - Clear one invert: Slope cell reverts to editable input showing the previous manual slope value.

- [ ] **Step 6: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 2: renderPipes invert columns + smart slope cell; renderPipeSizing25 uses pipeEffectiveSlope"
  ```

---

## Task 3: Update `renderHgl()` and `renderHgl25()` — add US/DS invert columns

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (~line 3343–3381 for `renderHgl`; ~line 3410–3441 for `renderHgl25`)

- [ ] **Step 1: Add column headers to `renderHgl` thead**

  At ~line 3350–3351, replace:
  ```js
      el("th",{class:"computed"},"Upstream HGL\n(ft)"),
      el("th",{},"Crown\n(ft)"),
  ```
  With:
  ```js
      el("th",{class:"computed"},"Upstream HGL\n(ft)"),
      el("th",{},"US Inv\n(ft)"),
      el("th",{},"DS Inv\n(ft)"),
      el("th",{},"Crown\n(ft)"),
  ```

- [ ] **Step 2: Add invert cells to `renderHgl` tbody rows**

  At ~line 3371–3373, replace:
  ```js
        el("td",{class:"out computed-cell", style:"font-weight:700"},
          calc && isFinite(calc.elevation) ? fmt(calc.elevation,2) : "—"),
        el("td",{}, isFinite(crown) ? fmt(crown,2) : "—"),
  ```
  With:
  ```js
        el("td",{class:"out computed-cell", style:"font-weight:700"},
          calc && isFinite(calc.elevation) ? fmt(calc.elevation,2) : "—"),
        el("td",{}, (()=>{ const p=calc&&calc.outPipe; const v=p&&parseFloat(p.upstreamInvert); return isFinite(v)?fmt(v,2):"—"; })()),
        el("td",{}, (()=>{ const p=calc&&calc.outPipe; const v=p&&parseFloat(p.downstreamInvert); return isFinite(v)?fmt(v,2):"—"; })()),
        el("td",{}, isFinite(crown) ? fmt(crown,2) : "—"),
  ```

- [ ] **Step 3: Add column headers to `renderHgl25` thead**

  At ~line 3413–3414, replace:
  ```js
      el("th",{class:"computed"},"Upstream HGL\n(ft)"),
      el("th",{class:"computed"},"Crown\nCheck"),
  ```
  With:
  ```js
      el("th",{class:"computed"},"Upstream HGL\n(ft)"),
      el("th",{},"US Inv\n(ft)"),
      el("th",{},"DS Inv\n(ft)"),
      el("th",{class:"computed"},"Crown\nCheck"),
  ```

- [ ] **Step 4: Add invert cells to `renderHgl25` tbody rows**

  At ~line 3435–3436, replace:
  ```js
        el("td",{class:"out computed-cell"}, isFinite(hgl)  ? fmt(hgl,2)  : "—"),
        el("td",{class:"out computed-cell", style:crownStyle},
  ```
  With:
  ```js
        el("td",{class:"out computed-cell"}, isFinite(hgl)  ? fmt(hgl,2)  : "—"),
        el("td",{}, (()=>{ const p=calc&&calc.outPipe; const v=p&&parseFloat(p.upstreamInvert); return isFinite(v)?fmt(v,2):"—"; })()),
        el("td",{}, (()=>{ const p=calc&&calc.outPipe; const v=p&&parseFloat(p.downstreamInvert); return isFinite(v)?fmt(v,2):"—"; })()),
        el("td",{class:"out computed-cell", style:crownStyle},
  ```

- [ ] **Step 5: Verify in browser**

  Go to HGL tab. Confirm two new columns "US Inv (ft)" and "DS Inv (ft)" appear after "Upstream HGL (ft)". With no inverts set on pipes, both show "—". After setting US/DS inverts on a pipe in the Pipe Sizing tab, the corresponding structure row in HGL shows the values. Same for HGL 25-yr tab.

- [ ] **Step 6: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 3: add US/DS invert columns to renderHgl and renderHgl25"
  ```

---

## Task 4: Update detail/print functions to use `pipeEffectiveSlope`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`
  - `buildPipeSheet` ~line 3808–3819
  - `buildPipesDetailSheet` ~line 4828
  - `buildHglDetailSheet` ~line 4947

- [ ] **Step 1: Update `buildPipeSheet` — geometry rows and Manning's formula**

  At ~line 3809–3810, replace:
  ```js
    geoRows.push(["Manning's n", fmt(parseFloat(row.n),3)]);
    geoRows.push(["Slope, S", fmt(parseFloat(row.slope),4)+" ft/ft"]);
  ```
  With:
  ```js
    geoRows.push(["Manning's n", fmt(parseFloat(row.n),3)]);
    const So = pipeEffectiveSlope(row);
    const hasInverts = row.upstreamInvert!==""&&row.upstreamInvert!=null&&
                       row.downstreamInvert!==""&&row.downstreamInvert!=null&&
                       row.length!==""&&row.length!=null;
    geoRows.push(["Slope, So"+(hasInverts?" (from inverts)":""), fmt(So,4)+" ft/ft"]);
    if(hasInverts) geoRows.push(["  US invert", fmt(parseFloat(row.upstreamInvert),2)+" ft"]);
    if(hasInverts) geoRows.push(["  DS invert", fmt(parseFloat(row.downstreamInvert),2)+" ft"]);
  ```

  Then at ~line 3818, replace the formula line that references `parseFloat(row.slope)`:
  ```js
      csFormula(["V = (1.486/"+fmt(parseFloat(row.n),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(parseFloat(row.slope),4)+"^(1/2)"]),
  ```
  With:
  ```js
      csFormula(["V = (1.486/"+fmt(parseFloat(row.n),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(So,4)+"^(1/2)"]),
  ```

- [ ] **Step 2: Update `buildPipesDetailSheet` — `So (%)` column**

  At ~line 4828, replace:
  ```js
    const n = parseFloat(pipe.n), S = parseFloat(pipe.slope), L = parseFloat(pipe.length);
  ```
  With:
  ```js
    const n = parseFloat(pipe.n), S = pipeEffectiveSlope(pipe), L = parseFloat(pipe.length);
  ```

- [ ] **Step 3: Update `buildHglDetailSheet` — `So` column**

  At ~line 4947, replace:
  ```js
    const S = parseFloat(pipe.slope), n = parseFloat(pipe.n), L = parseFloat(pipe.length);
  ```
  With:
  ```js
    const S = pipeEffectiveSlope(pipe), n = parseFloat(pipe.n), L = parseFloat(pipe.length);
  ```

- [ ] **Step 4: Verify**

  With a pipe that has US/DS inverts set, open its "⇡ Detail" modal from the Pipe Sizing tab. The Geometry section should show "Slope, So (from inverts)" with the computed value, plus the two invert elevations listed below it. The Manning's formula should show the computed slope value.

- [ ] **Step 5: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 4: update buildPipeSheet, buildPipesDetailSheet, buildHglDetailSheet to use pipeEffectiveSlope"
  ```

---

## Task 5: Excel export — add US/DS invert columns to Pipe Sizing sheet

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (~line 5218, 5223, 5243, 5255)
- Modify: `tests/run-tests.mjs` (append new test)

- [ ] **Step 1: Write the failing test**

  Append to `tests/run-tests.mjs`:
  ```js
  test("buildWorkbook: Pipe Sizing sheet has US Invert and DS Invert columns", () => {
    const wb = sdc.buildWorkbook();
    const XLSX = window.XLSX;
    const ws = wb.Sheets["Pipe Sizing"];
    const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
    const headers = aoa[0] || [];
    assert.ok(headers.includes("US Invert (ft)"), "US Invert (ft) column missing from Pipe Sizing sheet");
    assert.ok(headers.includes("DS Invert (ft)"), "DS Invert (ft) column missing from Pipe Sizing sheet");
  });
  ```

- [ ] **Step 2: Run test — confirm 1 failure**

  ```
  cd tests && npm test 2>&1 | grep -E "fail|US Invert|DS Invert"
  ```

- [ ] **Step 3: Update `pipeHeader` to include invert columns**

  At ~line 5218, replace:
  ```js
    const pipeHeader = ["ID","From Structure","To Structure","Angle (deg)","Shape","Size (in or SPANxRISE)","n","Slope (ft-ft)","Length (ft)","Design Q (cfs)","Area (sf)","Qfull (cfs)","Velocity (fps)","Status","Split Role","From|Role Key"];
  ```
  With:
  ```js
    const pipeHeader = ["ID","From Structure","To Structure","Angle (deg)","Shape","Size (in or SPANxRISE)","n","US Invert (ft)","DS Invert (ft)","Slope (ft-ft)","Length (ft)","Design Q (cfs)","Area (sf)","Qfull (cfs)","Velocity (fps)","Status","Split Role","From|Role Key"];
  ```

- [ ] **Step 4: Update the data row push to include invert values**

  At ~line 5223, replace:
  ```js
      pipeAoa.push([p.id, fromLabel, toLabel, num(p.angle,0), p.shape, p.size||"", num(p.n,3), num(p.slope,4), num(p.length), null, null, null, null, null, p.splitRole||"", null]);
  ```
  With:
  ```js
      pipeAoa.push([p.id, fromLabel, toLabel, num(p.angle,0), p.shape, p.size||"", num(p.n,3),
        (p.upstreamInvert===""||p.upstreamInvert==null)?"":parseFloat(p.upstreamInvert),
        (p.downstreamInvert===""||p.downstreamInvert==null)?"":parseFloat(p.downstreamInvert),
        num(p.slope,4), num(p.length), null, null, null, null, null, p.splitRole||"", null]);
  ```

- [ ] **Step 5: Update the column-letter comment and the from|role key formula**

  At ~line 5243, replace:
  ```js
    // Pipe Sizing:   A id B from C to D angle E shape F size G n H slope I len J designQ K area L qfull M vel N status O splitRole P from|role key
  ```
  With:
  ```js
    // Pipe Sizing:   A id B from C to D angle E shape F size G n H usInv I dsInv J slope K len L designQ M area N qfull O vel P status Q splitRole R from|role key
  ```

  At ~line 5255, replace:
  ```js
      setFormula(wsPipe, "P"+row, "=B"+row+"&\"|\"&IF(O"+row+"=\"\",\"primary\",O"+row+")", fromLabel+"|"+roleForKey);
  ```
  With:
  ```js
      setFormula(wsPipe, "R"+row, "=B"+row+"&\"|\"&IF(Q"+row+"=\"\",\"primary\",Q"+row+")", fromLabel+"|"+roleForKey);
  ```

- [ ] **Step 6: Run tests — confirm all pass**

  ```
  cd tests && npm test 2>&1 | tail -8
  ```
  Expected: `# pass 41`, `# fail 0`.

- [ ] **Step 7: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
  git commit -m "Task 5: Excel export — add US/DS invert columns to Pipe Sizing sheet"
  ```

---

## Task 6: Excel import — read US/DS invert fields from Pipe Sizing sheet

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (~line 5641–5657)

- [ ] **Step 1: Update the pipe import mapping**

  At ~line 5641–5657, the pipes import block reads:
  ```js
        state.pipes = pipes.map(r=>{
          const fromLabel = r["From Structure"]||"", toLabel = r["To Structure"]||"";
          return {
            id: nextId(),
            fromStructureId: stIdMap[fromLabel] || "",
            toStructureId: stIdMap[toLabel] || "",
            angle: r["Angle (deg)"]||0,
            shape: (r["Shape"]||"circular").toLowerCase()==="elliptical"?"elliptical":"circular",
            size: r["Size (in or SPANxRISE)"]||"",
            n: r["n"]===""||r["n"]==null?0.013:r["n"],
            slope: r["Slope (ft-ft)"]||"",
            length: r["Length (ft)"]||"",
            splitRole: r["Split Role"]||"",
          };
        });
  ```
  Replace with:
  ```js
        state.pipes = pipes.map(r=>{
          const fromLabel = r["From Structure"]||"", toLabel = r["To Structure"]||"";
          return {
            id: nextId(),
            fromStructureId: stIdMap[fromLabel] || "",
            toStructureId: stIdMap[toLabel] || "",
            angle: r["Angle (deg)"]||0,
            shape: (r["Shape"]||"circular").toLowerCase()==="elliptical"?"elliptical":"circular",
            size: r["Size (in or SPANxRISE)"]||"",
            n: r["n"]===""||r["n"]==null?0.013:r["n"],
            upstreamInvert: r["US Invert (ft)"]===""||r["US Invert (ft)"]==null?"":r["US Invert (ft)"],
            downstreamInvert: r["DS Invert (ft)"]===""||r["DS Invert (ft)"]==null?"":r["DS Invert (ft)"],
            slope: r["Slope (ft-ft)"]||"",
            length: r["Length (ft)"]||"",
            splitRole: r["Split Role"]||"",
          };
        });
  ```

- [ ] **Step 2: Verify round-trip manually**

  In the browser:
  1. Set US Invert = 105.0 and DS Invert = 104.0 on a pipe with Length = 200. Slope cell shows 0.0050.
  2. Click "Export to Excel". Open the file — "Pipe Sizing" sheet should have "US Invert (ft)" = 105, "DS Invert (ft)" = 104 in that row.
  3. Re-import the same file. Pipe Sizing tab should still show computed slope 0.0050 (inverts restored from import).

- [ ] **Step 3: Verify backward compat**

  Import an old Excel file (one without US/DS invert columns). Pipes should load with `upstreamInvert: ""` and `downstreamInvert: ""`, and slope should remain the manual value from the "Slope (ft-ft)" column.

- [ ] **Step 4: Run full test suite**

  ```
  cd tests && npm test 2>&1 | tail -8
  ```
  Expected: `# pass 41`, `# fail 0`.

- [ ] **Step 5: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 6: Excel import — read US/DS invert fields from Pipe Sizing sheet"
  ```

---

## Self-Review

**1. Spec coverage:**
- ✅ `pipeEffectiveSlope(pipe)` helper — Task 1
- ✅ `calcPipeRow` uses effective slope — Task 1
- ✅ US Inv / DS Inv input columns in `renderPipes` — Task 2
- ✅ Smart slope cell (computed when inverts set, editable otherwise) — Task 2
- ✅ `renderPipeSizing25` uses effective slope — Task 2
- ✅ US Inv / DS Inv read-only columns in `renderHgl` — Task 3
- ✅ US Inv / DS Inv read-only columns in `renderHgl25` — Task 3
- ✅ `buildPipeSheet` shows effective slope + invert note — Task 4
- ✅ `buildPipesDetailSheet` So column uses effective slope — Task 4
- ✅ `buildHglDetailSheet` So column uses effective slope — Task 4
- ✅ Excel export gains invert columns — Task 5
- ✅ From|role key formula column updated from P→R — Task 5
- ✅ Excel import reads invert fields — Task 6
- ✅ Old files without invert columns load cleanly — Task 6

**2. Placeholder scan:** None — all code blocks are complete.

**3. Type consistency:**
- `pipeEffectiveSlope(pipe)` — defined Task 1, called in Tasks 2, 4 as `pipeEffectiveSlope(row)` / `pipeEffectiveSlope(pipe)` — both are the pipe object, naming is consistent with other functions in this file.
- `upstreamInvert` / `downstreamInvert` — field names are consistent across: Add Row button (Task 2), `numInput` calls (Task 2), IIFE guard expressions (Task 2), `buildPipeSheet` display (Task 4), export push (Task 5), import map (Task 6).
- `calc.outPipe` — already returned by `computeStructureCalc`; the Tasks 3 invert cells use `calc&&calc.outPipe`, which is safe for base structures (`outPipe` is null there).

# Pipe Material Manning's n Table — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an editable pipe-material Manning's n reference table (new tab), a Material dropdown in the Pipe Sizing table that locks n to the selected material's value, and a `pipeEffectiveN()` helper that replaces all raw `row.n` reads in every calculation.

**Architecture:** All changes are in the single app file. `defaultPipeMaterials()` and `pipeEffectiveN()` are added near the existing pipe helpers. A new `renderPipeN()` tab function mirrors the `renderKb()` pattern exactly. The Material dropdown in the pipe table writes `row.material` (an integer id); `pipeEffectiveN(row)` does a live lookup so editing a material's n propagates immediately to all pipes using it.

**Tech Stack:** Vanilla JS, single HTML file — `drainage-calculator/storm-drain-design-calculator.html`. No build step.

---

### Task 1: Add `defaultPipeMaterials()`, `pipeEffectiveN()`, state init, save/restore

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add `defaultPipeMaterials()` immediately before `defaultKbRows()`**

Find this line (~line 667):
```js
function defaultKbRows(){
```

Insert the new function immediately before it:
```js
function defaultPipeMaterials() {
  return [
    { id: 1, label: "RCP (Reinforced Concrete Pipe)",  n: 0.013 },
    { id: 2, label: "CMP (Corrugated Metal Pipe)",      n: 0.024 },
    { id: 3, label: "CMP w/ Paved Invert",              n: 0.018 },
    { id: 4, label: "HDPE — smooth interior",           n: 0.012 },
    { id: 5, label: "HDPE — corrugated",                n: 0.025 },
    { id: 6, label: "PVC",                              n: 0.011 },
    { id: 7, label: "CPEP",                             n: 0.011 },
    { id: 8, label: "Ductile Iron Pipe",                n: 0.013 },
    { id: 9, label: "Steel Pipe",                       n: 0.012 },
  ];
}

```

- [ ] **Step 2: Add `pipeEffectiveN(row)` immediately after `manningFullFlow()`**

Find (~line 1493):
```js
function manningFullFlow(n, areaSf, equivDiamIn, slope){
  const R = (equivDiamIn/12)/4;
  const V = (1.486/n) * Math.pow(R, 2/3) * Math.sqrt(Math.max(slope,0));
  const Qfull = V*areaSf;
  return {R, V, Qfull};
}
```

Insert immediately after the closing brace:
```js

function pipeEffectiveN(row) {
  if (row.material) {
    const mat = state.pipeMaterials.find(m => m.id === row.material);
    if (mat) return parseFloat(mat.n) || 0;
  }
  return parseFloat(row.n) || 0;
}
```

- [ ] **Step 3: Add `pipeMaterials` to the `state` object**

Find the `state` object (~line 1383):
```js
const state = {
  project: "Untitled Storm Drain Project",
  active: "overview",
  drainage: [],
  structures: [],
  pipes: [],
  kb: defaultKbRows(),
```

Add `pipeMaterials` after `kb`:
```js
const state = {
  project: "Untitled Storm Drain Project",
  active: "overview",
  drainage: [],
  structures: [],
  pipes: [],
  kb: defaultKbRows(),
  pipeMaterials: defaultPipeMaterials(),
```

- [ ] **Step 4: Add `pipeMaterials` to `saveState()`**

Find the `saveState()` snapshot object (~line 2180):
```js
  const snap = JSON.parse(JSON.stringify({
    drainage: state.drainage,
    structures: state.structures,
    pipes: state.pipes,
    kb: state.kb,
```

Add `pipeMaterials` after `kb`:
```js
  const snap = JSON.parse(JSON.stringify({
    drainage: state.drainage,
    structures: state.structures,
    pipes: state.pipes,
    kb: state.kb,
    pipeMaterials: state.pipeMaterials,
```

- [ ] **Step 5: Add `pipeMaterials` to `restoreState()`**

Find `restoreState()` (~line 2196):
```js
  state.pipes = snap.pipes || [];
  state.kb = snap.kb || defaultKbRows();
```

Add the restore line after `state.kb`:
```js
  state.pipes = snap.pipes || [];
  state.kb = snap.kb || defaultKbRows();
  state.pipeMaterials = snap.pipeMaterials || defaultPipeMaterials();
```

- [ ] **Step 6: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add defaultPipeMaterials, pipeEffectiveN, state wiring"
```

---

### Task 2: Add the HTML view div, tab entry, `renderPipeN()`, and `renderAll()` call

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add the view div to the HTML**

Find (~line 573):
```html
      <div class="view" id="view-table46"></div>
      <div class="view" id="view-kb"></div>
```

Insert a new div between them:
```html
      <div class="view" id="view-table46"></div>
      <div class="view" id="view-pipe-n"></div>
      <div class="view" id="view-kb"></div>
```

- [ ] **Step 2: Register the tab in `getTabs()`**

Find (~line 2304):
```js
    {id:"table46",        label:"Table 4-6 Reference"},
    {id:"kb",             label:"Kb Coefficients"},
```

Insert the new tab between them:
```js
    {id:"table46",        label:"Table 4-6 Reference"},
    {id:"pipe-n",         label:"Manning's n (Pipe)"},
    {id:"kb",             label:"Kb Coefficients"},
```

- [ ] **Step 3: Add `renderPipeN()` immediately before `renderKb()`**

Find the comment line:
```js
/* ---------------------------------------------------------------------
   Kb Coefficients tab
--------------------------------------------------------------------- */
function renderKb(){
```

Insert the entire new function before it:
```js
/* ---------------------------------------------------------------------
   Manning's n (Pipe Materials) tab
--------------------------------------------------------------------- */
function renderPipeN() {
  const c = document.getElementById("view-pipe-n");
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Manning's n — Pipe Materials"));
  c.appendChild(el("p", {class:"view-desc"}, "General industry-standard Manning’s n values for pipe sizing. Edit to match your governing agency’s design manual. Changes apply immediately to all pipes using that material."));

  const section = el("div", {class:"section"});
  section.appendChild(el("div", {class:"section-head"}, [
    el("h2", {}, "Pipe material reference"),
    el("div", {}, [
      el("button", {class:"btn btn-sm", onclick:()=>{ state.pipeMaterials.push({id:nextId(), label:"", n:""}); renderPipeN(); }}, "+ Add row"),
      el("button", {class:"btn btn-sm btn-ghost", onclick:()=>{ state.pipeMaterials=defaultPipeMaterials(); renderAll(); toast("Pipe material table reset to default values."); }}, "Reset to default")
    ])
  ]));

  const tableWrap = el("div", {class:"table-wrap"});
  const table = el("table", {class:"data"});
  table.appendChild(el("thead", {}, el("tr", {}, [
    el("th", {}, "Pipe Material"),
    el("th", {}, "Manning's n"),
    el("th", {}, "")
  ])));
  const tbody = el("tbody");
  state.pipeMaterials.forEach(row => {
    tbody.appendChild(el("tr", {}, [
      el("td", {}, txtInput(row, "label", 260)),
      el("td", {}, numInput(row, "n", 80)),
      el("td", {}, delBtn(()=>{ state.pipeMaterials = state.pipeMaterials.filter(r => r !== row); renderAll(); }))
    ]));
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  section.appendChild(tableWrap);
  c.appendChild(section);

  function txtInput(row, field, w) {
    return el("input", {class:"cell-input txt", type:"text", style:"width:"+w+"px",
      value: row[field] || "",
      "data-focus-key": "pipe-n:" + row.id + ":" + field,
      oninput: (e) => { row[field] = e.target.value; withFocusPreserved(renderAll); }});
  }
  function numInput(row, field, w) {
    return el("input", {class:"cell-input", type:"text", inputmode:"decimal", step:"any",
      style:"width:"+w+"px",
      value: row[field] === undefined || row[field] === null ? "" : row[field],
      "data-focus-key": "pipe-n:" + row.id + ":" + field,
      oninput: (e) => { row[field] = e.target.value; withFocusPreserved(renderAll); }});
  }
}

```

- [ ] **Step 4: Add `renderPipeN()` to `renderAll()`**

Find (~line 4188):
```js
  renderTable46();
  renderKb();
```

Add the new call between them:
```js
  renderTable46();
  renderPipeN();
  renderKb();
```

- [ ] **Step 5: Open the file in a browser — verify the new tab appears**

Navigate to the "Manning's n (Pipe)" tab. Verify: 9 rows appear with labels and n values. "+ Add row" appends a blank row. "Reset to default" restores the 9 rows. Editing a label or n value persists (no JS errors in console).

- [ ] **Step 6: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add Manning's n (Pipe) tab with editable material table"
```

---

### Task 3: Replace raw `row.n` reads in pipe calculations with `pipeEffectiveN`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Fix `calcPipeRow()`**

Find (~line 1787):
```js
  const n = parseFloat(row.n), S = pipeEffectiveSlope(row);
  const {V, Qfull} = manningFullFlow(n, geo.areaSf, geo.equivDiamIn, S);
```

Change to:
```js
  const n = pipeEffectiveN(row), S = pipeEffectiveSlope(row);
  const {V, Qfull} = manningFullFlow(n, geo.areaSf, geo.equivDiamIn, S);
```

- [ ] **Step 2: Fix the HGL computation (`computeStructureCalc`)**

Find (~line 1854):
```js
    Sf = frictionSlope(outPipeFlow, parseFloat(outPipe.n), geo.areaSf, R);
```

Change to:
```js
    Sf = frictionSlope(outPipeFlow, pipeEffectiveN(outPipe), geo.areaSf, R);
```

- [ ] **Step 3: Fix `renderPipeSizing25()` capacity calculation**

Find (~line 3778 — inside `renderPipeSizing25()`):
```js
    const n     = parseFloat(row.n);
```

Change to:
```js
    const n     = pipeEffectiveN(row);
```

- [ ] **Step 4: Verify in browser**

Add a pipe row, select "RCP (Reinforced Concrete Pipe)" as material, enter a size and slope. Qfull should compute correctly using n=0.013. Change the material to "PVC" — Qfull should recompute with n=0.011 immediately. Open the console and verify no errors.

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: replace raw row.n reads with pipeEffectiveN in all calculations"
```

---

### Task 4: Update `buildPipeSheet()` detail sheet to show material and use `pipeEffectiveN`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add material row and fix n display in geometry table**

Find (~line 4297):
```js
  const geoRows = [
    ["Shape", row.shape==="circular"?"Circular":"Elliptical"],
    ["Size", row.shape==="circular" ? (row.size||"—")+" in diameter" : (row.size||"—")+" in (span × rise)"],
  ];
  if(row.shape==="elliptical" && geo){
    geoRows.push(["Matched Table 4-6 entry", geo.equivDiamIn+" in equivalent circular diameter"]);
  }
  geoRows.push(["Cross-sectional area, A", geo?fmt(geo.areaSf,3)+" sf":"—"]);
  geoRows.push(["Manning's n", fmt(parseFloat(row.n),3)]);
```

Change to:
```js
  const matEntry = row.material ? state.pipeMaterials.find(m => m.id === row.material) : null;
  const geoRows = [
    ["Shape", row.shape==="circular"?"Circular":"Elliptical"],
    ["Size", row.shape==="circular" ? (row.size||"—")+" in diameter" : (row.size||"—")+" in (span × rise)"],
  ];
  if(row.shape==="elliptical" && geo){
    geoRows.push(["Matched Table 4-6 entry", geo.equivDiamIn+" in equivalent circular diameter"]);
  }
  geoRows.push(["Cross-sectional area, A", geo?fmt(geo.areaSf,3)+" sf":"—"]);
  geoRows.push(["Material", matEntry ? matEntry.label : "Manual"]);
  geoRows.push(["Manning's n", fmt(pipeEffectiveN(row),3)]);
```

- [ ] **Step 2: Fix the substituted Manning's formula line in `buildPipeSheet()`**

Find (~line 4321):
```js
      csFormula(["V = (1.486/"+fmt(parseFloat(row.n),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(So,4)+"^(1/2)"]),
```

Change to:
```js
      csFormula(["V = (1.486/"+fmt(pipeEffectiveN(row),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(So,4)+"^(1/2)"]),
```

- [ ] **Step 3: Verify in browser**

Click the Detail button on a pipe row that has a material selected. The geometry table should show "Material: RCP (Reinforced Concrete Pipe)" and "Manning's n: 0.013". The substituted formula should show the correct n. For a manual-n pipe, Material row should read "Manual".

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: show material and pipeEffectiveN in pipe detail sheet"
```

---

### Task 5: Fix HGL detail sheet, Formulas & Examples, and Excel export

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Fix the HGL detail sheet pipe n display**

Find (~line 5357 — inside the HGL/pipe detail builder):
```js
    const n = parseFloat(pipe.n), S = pipeEffectiveSlope(pipe), L = parseFloat(pipe.length);
```

Change to:
```js
    const n = pipeEffectiveN(pipe), S = pipeEffectiveSlope(pipe), L = parseFloat(pipe.length);
```

- [ ] **Step 2: Fix Formulas & Examples worked example**

Find (~line 4616 — inside `buildFormulasSheet()`):
```js
    b2.push(csTable([["Size",pipeEx.size+" in circular"],["n",fmt(parseFloat(pipeEx.n),3)],["S",fmt(pipeEffectiveSlope(pipeEx),4)+" ft/ft"],["A = π/4×D²",fmt(pipeCalc.areaSf,4)+" sf"],["R = D/4",fmt(R,3)+" ft"]]));
    b2.push(csFormula(["V = (1.486/"+fmt(parseFloat(pipeEx.n),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(pipeEffectiveSlope(pipeEx),4)+"^(1/2)"]));
```

Change both `parseFloat(pipeEx.n)` to `pipeEffectiveN(pipeEx)`:
```js
    b2.push(csTable([["Size",pipeEx.size+" in circular"],["n",fmt(pipeEffectiveN(pipeEx),3)],["S",fmt(pipeEffectiveSlope(pipeEx),4)+" ft/ft"],["A = π/4×D²",fmt(pipeCalc.areaSf,4)+" sf"],["R = D/4",fmt(R,3)+" ft"]]));
    b2.push(csFormula(["V = (1.486/"+fmt(pipeEffectiveN(pipeEx),3)+") × "+fmt(R,3)+"^(2/3) × "+fmt(pipeEffectiveSlope(pipeEx),4)+"^(1/2)"]));
```

- [ ] **Step 3: Fix Excel export — pipe n column**

Find (~line 5768):
```js
    pipeAoa.push([p.id, fromLabel, toLabel, num(p.angle,0), p.shape, p.size||"", num(p.n,3),
```

Change `num(p.n,3)` to `num(pipeEffectiveN(p),3)`:
```js
    pipeAoa.push([p.id, fromLabel, toLabel, num(p.angle,0), p.shape, p.size||"", num(pipeEffectiveN(p),3),
```

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: use pipeEffectiveN in HGL detail, Formulas, and Excel export"
```

---

### Task 6: Add Material dropdown + locked n cell to the Pipe Sizing tables

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Update the default new-pipe object to include `material: ""`**

Find (~line 2761 — inside `renderPipes()` section-head):
```js
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, upstreamInvert:"", downstreamInvert:"", slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row"),
```

Change to:
```js
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, material:"", upstreamInvert:"", downstreamInvert:"", slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row"),
```

- [ ] **Step 2: Add "Material" to the primary pipe table header**

Find the `<thead>` row inside `renderPipes()` (~line 2768):
```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"n"), el("th",{},"US Inv\n(ft)"),
```

Change to:
```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"Material"), el("th",{},"n"), el("th",{},"US Inv\n(ft)"),
```

- [ ] **Step 3: Add `materialSelect(row)` helper and the locked n cell inside `renderPipes()`**

Find the local helper functions at the bottom of `renderPipes()` (~line 2821):
```js
  function txtInput(row,field,w){
```

Add two new helpers before `txtInput`:
```js
  function materialSelect(row) {
    const sel = el("select", {class:"cell-input", style:"width:180px;",
      "data-focus-key": "pipes:" + row.id + ":material",
      onchange: (e) => { row.material = e.target.value ? Number(e.target.value) : ""; withFocusPreserved(renderAll); }});
    sel.appendChild(el("option", {value:""}, "— (manual)"));
    state.pipeMaterials.forEach(m => {
      const o = el("option", {value: String(m.id)}, m.label);
      if (row.material === m.id) o.selected = true;
      sel.appendChild(o);
    });
    return sel;
  }
  function nCell(row) {
    if (row.material) {
      return el("td", {class:"out computed-cell", style:"color:#aaa;"}, fmt(pipeEffectiveN(row), 3));
    }
    return el("td", {}, numInput(row, "n", 60));
  }
  function txtInput(row,field,w){
```

- [ ] **Step 4: Insert the Material and n cells into the pipe table body row**

Find inside `renderPipes()` the table body cell sequence (~line 2783):
```js
      el("td",{}, shapeSelect(row)),
      el("td",{}, txtInput(row,"size",80)),
      el("td",{}, numInput(row,"n",60)),
      el("td",{}, numInput(row,"upstreamInvert",70)),
```

Change to:
```js
      el("td",{}, shapeSelect(row)),
      el("td",{}, txtInput(row,"size",80)),
      el("td",{}, materialSelect(row)),
      nCell(row),
      el("td",{}, numInput(row,"upstreamInvert",70)),
```

- [ ] **Step 5: Add "Material" to the 25-yr pipe table header in `renderPipeSizing25()`**

Find the thead row inside `renderPipeSizing25()`. It contains:
```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"n"),
```

Change to:
```js
    el("th",{},"Shape"), el("th",{},"Size (in)"), el("th",{},"Material"), el("th",{},"n"),
```

- [ ] **Step 6: Add the material cell and locked n to the 25-yr table body**

Find inside `renderPipeSizing25()` the pipe table body cell sequence. It contains (approximately):
```js
      el("td",{}, row.shape==="circular"?"Circular":"Elliptical"),
      el("td",{}, row.size||"—"),
      el("td",{}, row.n!=null&&row.n!==""?row.n:"—"),
```

Change to:
```js
      el("td",{}, row.shape==="circular"?"Circular":"Elliptical"),
      el("td",{}, row.size||"—"),
      el("td",{}, row.material ? (state.pipeMaterials.find(m=>m.id===row.material)||{}).label||"—" : "— (manual)"),
      el("td",{class:"out computed-cell", style: row.material?"color:#aaa;":""}, fmt(pipeEffectiveN(row),3)),
```

- [ ] **Step 7: Verify in browser**

Go to Pipe Sizing & Capacity. The table now has a "Material" column before "n". Select "RCP" from the dropdown — the n cell becomes a dimmed read-only "0.013". Switch to "PVC" — it shows "0.011". Clear to "— (manual)" — the n cell becomes an editable input. Check the 25-yr tab (if enabled) shows the same material label and locked n.

- [ ] **Step 8: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add Material dropdown and locked n cell to Pipe Sizing tables"
```

---

### Task 7: Update Excel import to restore `material` field

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Confirm no separate State sheet exists in this app**

This app exports named sheets per data type (Pipe Sizing, Junction Structure, Kb Coefficients, etc.) — there is no JSON State blob sheet. `pipeMaterials` persistence is handled entirely through localStorage snapshots (Task 1 Steps 4–5). This step is a confirmation only — no code change needed. Skip to Step 2.

- [ ] **Step 2: Restore `material` field when importing pipe rows from Excel**

Find (~line 6223):
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

Add `material: ""` to the imported pipe object (imported files from before this feature won't have material data, so always default to manual):
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
            material: "",
            upstreamInvert: r["US Invert (ft)"]===""||r["US Invert (ft)"]==null?"":r["US Invert (ft)"],
            downstreamInvert: r["DS Invert (ft)"]===""||r["DS Invert (ft)"]==null?"":r["DS Invert (ft)"],
            slope: r["Slope (ft-ft)"]||"",
            length: r["Length (ft)"]||"",
            splitRole: r["Split Role"]||"",
          };
        });
```

- [ ] **Step 3: Check for State-sheet export/import and handle `pipeMaterials`**

Search the file for `"State"` (quoted string) to see if a State sheet is written and read. If found, add `pipeMaterials: state.pipeMaterials` to the write and `state.pipeMaterials = parsed.pipeMaterials || defaultPipeMaterials()` to the read. If not found, localStorage round-trip (Task 1 Steps 4–5) is sufficient — skip.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: handle material field in Excel import/export"
```

---

### Task 8: End-to-end verification

**Files:** None (manual browser verification)

- [ ] **Step 1: Manning's n (Pipe) tab — basic CRUD**

Open the app. Navigate to "Manning's n (Pipe)" tab. Verify 9 default rows. Edit "RCP" n from 0.013 to 0.014 — go to Pipe Sizing, select RCP on a pipe — n cell shows 0.014. Click "Reset to default" — n returns to 0.013.

- [ ] **Step 2: Material → locked n → calculation ripple**

Add a pipe row. Select "PVC" — n cell shows 0.011 (dimmed). Enter a size (e.g. 18 in circular) and slope (0.005). Qfull should compute using n=0.011. Switch material to "CMP (Corrugated Metal Pipe)" — Qfull recomputes with n=0.024 (lower velocity, lower capacity). Clear material to "— (manual)" — n input appears, editable.

- [ ] **Step 3: Detail sheet**

With a material-selected pipe, click Detail. Geometry table shows "Material: PVC" and "Manning's n: 0.011". Substituted formula shows the correct n. For a manual pipe, shows "Material: Manual".

- [ ] **Step 4: HGL**

Add two structures and connect a pipe with a material selected. Go to HGL tab — friction loss and elevation should compute correctly. Open HGL detail — n shown should be the effective n.

- [ ] **Step 5: LocalStorage round-trip**

Save a snapshot. Reload the page. Restore snapshot. Material selections and pipeMaterials table edits are preserved.

- [ ] **Step 6: Excel export/import**

Export to `.xlsx`. The n column in the Pipe Sizing sheet shows the effective n (e.g. 0.011 for PVC, not whatever was in `row.n`). Re-import the file. Pipes load with `material: ""` (manual). The n values from the export are preserved in the n column.

- [ ] **Step 7: Final commit if any fixes were needed**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "fix: <describe any issue found during verification>"
```

Skip if no fixes were needed.

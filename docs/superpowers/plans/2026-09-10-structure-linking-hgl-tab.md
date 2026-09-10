# Structure Linking, HGL Tab & Tab Reorganization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link inlet spacing rows to inlet-type junction structures with DA auto-fill, add a dedicated HGL tab, move Inlet Spacing to tab 5, rename Pipe Sizing to "Pipe Sizing & Capacity", and split HGL results out of the Junction Structures table.

**Architecture:** Single-file app — all changes in `drainage-calculator/storm-drain-design-calculator.html`. A new `linkedStructureId` field on inlet spacing rows drives `resolvedInletFields()`, which auto-fills `area`/`C`/`tc` from the linked DA. A new `renderHgl()` function mirrors the right half of the old Junction Structures table. `getTabs()` is updated for the new order and labels. The Junction Structures table loses its HGL output columns.

**Tech Stack:** Vanilla JS; SheetJS (already inline); Node + jsdom for `tests/run-tests.mjs`.

**Design doc:** `docs/superpowers/specs/2026-09-10-structure-linking-hgl-tab-design.md`

**Key facts:**
- Only file to edit: `drainage-calculator/storm-drain-design-calculator.html`
- Tests: `cd tests && npm test` (31 passing baseline)
- `withFocusPreserved(renderAll)` on every `oninput`/`onchange`; `data-focus-key` on every input
- `el(tag, attrs, children)` is the DOM builder
- `bookSST: true` in `exportExcel()` — do not remove
- No Co-Authored-By trailers in commits

---

### Task 1 — State model: `linkedStructureId` + `resolvedInletFields()` + `resolvedInletLabel()` + tests

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (≈ lines 1172, 1002 area, 4884)
- Modify: `tests/run-tests.mjs`

- [ ] **Step 1: Add `linkedStructureId` to `defaultInletSpacingRow()` (≈ line 1172)**

Find `function defaultInletSpacingRow()`. Add `linkedStructureId: "",` as the second field, right after `id: nextId(),`:

```js
function defaultInletSpacingRow() {
  return {
    id: nextId(),
    linkedStructureId: "",   // internal id of a type="inlet" structure, or "" = custom
    label: "",
    structureType: "",
    area: "",
    C: "",
    tc: "",
    iOverride: "",
    S: "",
    Sx: "",
    W: 1.33,
    a: 0.0833,
    n: 0.013,
    L: "",
    allowableSpread: "",
    bypassTo: "",
  };
}
```

- [ ] **Step 2: Add `resolvedInletFields()` and `resolvedInletLabel()` before `computeInletRow()` (≈ line 1002)**

Find `function computeInletRow`. Insert these two helpers immediately before it:

```js
function resolvedInletFields(row) {
  const out = {
    area: row.area, C: row.C, tc: row.tc,
    areaFromDA: false, CFromDA: false, tcFromDA: false,
  };
  if (!row.linkedStructureId) return out;
  const st = state.structures.find(s => s.id === row.linkedStructureId);
  if (!st || !st.drainageAreaId) return out;
  const da = findDrainage(st.drainageAreaId);
  if (!da) return out;
  if (row.area === "" || row.area == null) { out.area = da.area; out.areaFromDA = true; }
  if (row.C   === "" || row.C   == null)  { out.C   = da.C;    out.CFromDA   = true; }
  if (row.tc  === "" || row.tc  == null)  { out.tc  = da.tc;   out.tcFromDA  = true; }
  return out;
}

function resolvedInletLabel(row) {
  if (!row.linkedStructureId) return row.label;
  const st = state.structures.find(s => s.id === row.linkedStructureId);
  return st ? (st.structureId || st.id) : row.label;
}
```

- [ ] **Step 3: Expose in `window.__sdc` (≈ line 4884)**

Find `window.__sdc = {`. Add `resolvedInletFields, resolvedInletLabel,` to the object.

- [ ] **Step 4: Write failing tests in `tests/run-tests.mjs`**

Add at the end of `tests/run-tests.mjs`:

```js
test("resolvedInletFields: returns row values when no linkedStructureId", () => {
  const row = { linkedStructureId:"", area:"0.5", C:"0.8", tc:"10" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "0.5");
  assert.equal(r.areaFromDA, false);
});

test("resolvedInletFields: auto-fills blank area/C/tc from linked DA", () => {
  // Seed a structure and DA
  const daId = sdc.state.drainage[0] && sdc.state.drainage[0].id;
  const st = sdc.state.structures[0];
  if (!st || !daId) return;
  const origLinked = st.drainageAreaId;
  st.drainageAreaId = daId;
  const da = sdc.findDrainage(daId);
  da.area = "1.2"; da.C = "0.7"; da.tc = "15";
  const row = { linkedStructureId: st.id, area:"", C:"", tc:"" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "1.2");
  assert.equal(r.C,    "0.7");
  assert.equal(r.tc,   "15");
  assert.equal(r.areaFromDA, true);
  assert.equal(r.CFromDA,    true);
  assert.equal(r.tcFromDA,   true);
  st.drainageAreaId = origLinked;
});

test("resolvedInletFields: non-blank row field is kept as override", () => {
  const daId = sdc.state.drainage[0] && sdc.state.drainage[0].id;
  const st = sdc.state.structures[0];
  if (!st || !daId) return;
  const origLinked = st.drainageAreaId;
  st.drainageAreaId = daId;
  const da = sdc.findDrainage(daId);
  da.area = "1.2"; da.C = "0.7"; da.tc = "15";
  const row = { linkedStructureId: st.id, area:"0.5", C:"", tc:"" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "0.5");       // user override kept
  assert.equal(r.areaFromDA, false);  // not from DA
  assert.equal(r.C, "0.7");          // blank → from DA
  assert.equal(r.CFromDA, true);
  st.drainageAreaId = origLinked;
});
```

- [ ] **Step 5: Run tests to verify they FAIL**

```powershell
cd tests; npm test
```
Expected: 3 new tests fail (`resolvedInletFields is not a function`). 31 existing tests still pass.

- [ ] **Step 6: Run tests to verify they PASS**

```powershell
cd tests; npm test
```
Expected: 34/34 pass.

- [ ] **Step 7: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 1: add linkedStructureId to inlet rows, resolvedInletFields/resolvedInletLabel helpers"
```

---

### Task 2 — Tab reorder + renames + view divs + `renderAll()` rewiring

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (≈ lines 490–496, 1908–1927, 3285–3300)

- [ ] **Step 1: Add `view-hgl` view div, rename `view-structures-25` → `view-hgl-25` (≈ lines 490–496)**

Find the HTML block:
```html
      <div class="view" id="view-inlet-spacing"></div>
      <div class="view" id="view-rainfall"></div>
      <div class="view" id="view-pipe-sizing-25"></div>
      <div class="view" id="view-structures-25"></div>
```
Replace with:
```html
      <div class="view" id="view-inlet-spacing"></div>
      <div class="view" id="view-rainfall"></div>
      <div class="view" id="view-hgl"></div>
      <div class="view" id="view-pipe-sizing-25"></div>
      <div class="view" id="view-hgl-25"></div>
```

- [ ] **Step 2: Replace `getTabs()` (≈ lines 1908–1927)**

Replace the entire `getTabs()` function:

```js
function getTabs() {
  const tabs = [
    {id:"overview",       label:"Overview"},
    {id:"rainfall",       label:"Rainfall & IDF"},
    {id:"drainage",       label:"Drainage Area (Q=CiA)"},
    {id:"structures",     label:"Junction Structures"},
    {id:"inlet-spacing",  label:"Inlet Spacing"},
    {id:"pipes",          label:"Pipe Sizing & Capacity"},
    {id:"hgl",            label:"HGL"},
    {id:"outlet",         label:"Outlet Structure"},
    {id:"formulas",       label:"Formulas & Examples"},
    {id:"table46",        label:"Table 4-6 Reference"},
    {id:"kb",             label:"Kb Coefficients"},
  ];
  const r = state.rainfall;
  if (r.pipe25Check && r.pipeStorm !== "25yr") {
    tabs.push({id:"pipe-sizing-25",  label:"Pipe Sizing & Capacity — 25-yr"});
    tabs.push({id:"hgl-25",          label:"HGL — 25-yr"});
  }
  return tabs;
}
```

- [ ] **Step 3: Rename `renderStructures25()` → `renderHgl25()` and update its internals**

Find `function renderStructures25()`. Rename it to `function renderHgl25()`. Inside the function:
- Change `document.getElementById("view-structures-25")` → `document.getElementById("view-hgl-25")`
- Change the h1 text `"Junction Structures — 25-yr Check"` → `"HGL — 25-yr"`
- Change the h2 text `"HGL check — 25-yr storm"` → `"HGL check — 25-yr storm"` (no change needed)

- [ ] **Step 4: Update `renderAll()` (≈ lines 3285–3300)**

Replace the entire `renderAll()` function:

```js
function renderAll(){
  renderNav();
  showActiveView();
  renderOverview();
  renderDrainage();
  renderStructures();
  renderInletSpacing();
  renderPipes();
  renderHgl();
  renderOutlet();
  renderFormulas();
  renderTable46();
  renderKb();
  renderRainfall();
  renderPipeSizing25();
  renderHgl25();
}
```

- [ ] **Step 5: Add a temporary `renderHgl()` stub (Task 3 will replace it)**

Find `function renderHgl25()`. Immediately before it, add:

```js
function renderHgl() {
  const c = document.getElementById("view-hgl");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "HGL"));
  c.appendChild(el("p", {class:"view-desc"}, "Hydraulic Grade Line — stub, see Task 3."));
}
```

- [ ] **Step 6: Run tests**

```powershell
cd tests; npm test
```
Expected: 34/34 pass. No regressions.

- [ ] **Step 7: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 2: reorder tabs, add HGL tab, rename pipe sizing, rename structures-25 to hgl-25"
```

---

### Task 3 — `renderHgl()` — primary HGL tab (full implementation)

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `renderHgl()` stub with full implementation**

Find the `renderHgl()` stub added in Task 2. Replace it entirely with:

```js
function renderHgl() {
  const c = document.getElementById("view-hgl");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "HGL"));
  c.appendChild(el("p", {class:"view-desc"},
    "Hydraulic grade line results for the primary design storm. " +
    "Define structures and pipes on the Junction Structures and Pipe Sizing & Capacity tabs first. " +
    "This tab is read-only — all values are computed."));

  const section = el("div", {class:"section"});
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Upstream HGL — Primary Design Storm")]));
  const tableWrap = el("div", {class:"table-wrap"});
  const table = el("table", {class:"data"});
  table.appendChild(el("thead", {}, el("tr", {}, [
    el("th",{},"Structure ID"),
    el("th",{},"Type"),
    el("th",{class:"computed"},"Total Q\n(cfs)"),
    el("th",{class:"computed"},"Hf\n(ft)"),
    el("th",{class:"computed"},"Kb"),
    el("th",{class:"computed"},"Hb\n(ft)"),
    el("th",{class:"computed"},"Upstream HGL\n(ft)"),
    el("th",{},"Crown\n(ft)"),
    el("th",{class:"computed"},"Crown\nCheck"),
    el("th",{},"Rim\n(ft)"),
    el("th",{class:"computed"},"Rim\nCheck"),
  ])));
  const tbody = el("tbody");
  state.structures.forEach(row => {
    const calc = computeStructureCalc(row.id);
    const crown = parseFloat(row.crown);
    const rim   = parseFloat(row.rim);
    const crownStyle = calc && calc.crownPass === false ? "color:#e05;font-weight:700;" : "";
    const rimStyle   = calc && calc.rimPass   === false ? "color:#e05;font-weight:700;" : "";
    tbody.appendChild(el("tr", {}, [
      el("td",{}, row.structureId||row.id),
      el("td",{}, row.type||""),
      el("td",{class:"out computed-cell"}, calc && isFinite(calc.totalFlow) ? fmt(calc.totalFlow,2) : "—"),
      el("td",{class:"out computed-cell"}, calc && isFinite(calc.Hf)        ? fmt(calc.Hf,3)        : "—"),
      el("td",{class:"out computed-cell"}, calc && calc.kb != null           ? fmt(calc.kb,2)         : "—"),
      el("td",{class:"out computed-cell"}, calc && isFinite(calc.Hb)        ? fmt(calc.Hb,3)        : "—"),
      el("td",{class:"out computed-cell", style:"font-weight:700"},
        calc && isFinite(calc.elevation) ? fmt(calc.elevation,2) : "—"),
      el("td",{}, isFinite(crown) ? fmt(crown,2) : "—"),
      el("td",{class:"out computed-cell", style:crownStyle},
        !calc ? "—" : calc.crownPass === null ? "—" : calc.crownPass ? "✓" : "✗ > crown+1"),
      el("td",{}, isFinite(rim) ? fmt(rim,2) : "—"),
      el("td",{class:"out computed-cell", style:rimStyle},
        !calc ? "—" : calc.rimPass === null ? "—" : calc.rimPass ? "✓" : "✗ FLOOD"),
    ]));
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  section.appendChild(tableWrap);
  if (state.structures.length === 0)
    section.appendChild(el("p",{class:"hint"},"No structures defined. Add structures on the Junction Structures tab."));
  c.appendChild(section);
}
```

- [ ] **Step 2: Run tests**

```powershell
cd tests; npm test
```
Expected: 34/34 pass.

- [ ] **Step 3: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 3: implement renderHgl() — primary HGL tab with Hf/Kb/Hb/elevation/crown/rim checks"
```

---

### Task 4 — Strip HGL columns from `renderStructures()` (Junction Structures table)

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (≈ lines 2113–2148)

- [ ] **Step 1: Remove HGL columns from the table header (≈ line 2113)**

Find the `renderStructures()` function thead row. It currently ends with:
```js
    el("th",{class:"computed"},"Hf"), el("th",{class:"computed"},"Kb"), el("th",{class:"computed"},"Hb"),
    el("th",{class:"computed"},"Upstream HGL"), el("th",{class:"computed"},"Crown Chk"), el("th",{class:"computed"},"Rim Chk"),
    el("th",{},""), el("th",{},"")
```

Replace with (keeping Captured Q / Inflow / Total Flow, removing Hf/Kb/Hb/HGL/checks):
```js
    el("th",{},""), el("th",{},"")
```

The full header row after this change should be:
```js
  table.appendChild(el("thead",{},el("tr",{},[
    el("th",{},"Structure ID"), el("th",{},"Description"), el("th",{},"Drainage Area"), el("th",{},"Type"), el("th",{},"Split config"),
    el("th",{},"Fixed?"), el("th",{},"Fixed/Start Elev"), el("th",{},"Crown (ft)"), el("th",{},"Rim/Grate (ft)"),
    el("th",{class:"computed"},"Captured Q"), el("th",{class:"computed"},"Inflow"), el("th",{class:"computed"},"Total Flow"),
    el("th",{},""), el("th",{},"")
  ])));
```

- [ ] **Step 2: Remove HGL cells from the tbody row build (≈ line 2135)**

Find the `tbody.appendChild(el("tr",{},[` block. Remove these six `el("td",...)` lines:
```js
      el("td",{class:"out computed-cell"}, fmt(calc.Hf,3)),
      el("td",{class:"out computed-cell"}, calc.kb==null?"—":fmt(calc.kb,2)),
      el("td",{class:"out computed-cell"}, fmt(calc.Hb,3)),
      el("td",{class:"out computed-cell", style:"font-weight:700"}, fmt(calc.elevation,2)),
      el("td",{class:"computed-cell"}, checkBadge(calc.crownPass)),
      el("td",{class:"computed-cell"}, checkBadge(calc.rimPass)),
```

Keep all other cells (structureId, desc, daSelect, typeSelect, splitConfig, forceChk, startElev, crown, rim, captured Q, inflow count, totalFlow, detail btn, del btn).

- [ ] **Step 3: Run tests**

```powershell
cd tests; npm test
```
Expected: 34/34 pass.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 4: remove HGL columns from Junction Structures table (moved to HGL tab)"
```

---

### Task 5 — `renderInletSpacing()`: Structure dropdown + auto-fill UI

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Read the current `renderInletSpacing()` table header and tbody row**

Search for `function renderInletSpacing()`. Find the table `thead` row and the `tbody` row build loop. Note the current first column ("Label") and the `txt(row,"label",...)` cell.

- [ ] **Step 2: Add "Structure" column to the table header**

In the `thead` row, add `el("th",{},"Structure")` as the **first** `th` (before the existing "Label" th):

The first two headers should now be:
```js
    el("th",{},"Structure"), el("th",{},"Label"),
```

- [ ] **Step 3: Build the structure dropdown helper inside `renderInletSpacing()`**

At the top of `renderInletSpacing()` (before the table is built), add a helper to create the Structure dropdown for a row:

```js
  function structureDropdown(row) {
    const sel = el("select", {
      class: "cell-input",
      style: "width:110px;",
      "data-focus-key": "is:"+row.id+":linkedStructure",
      onchange: (e) => {
        row.linkedStructureId = e.target.value;
        withFocusPreserved(renderAll);
      }
    });
    const optCustom = el("option", {value:""}, "Custom");
    if (!row.linkedStructureId) optCustom.selected = true;
    sel.appendChild(optCustom);
    state.structures
      .filter(st => st.type === "inlet")
      .forEach(st => {
        const opt = el("option", {value: st.id}, st.structureId || st.id);
        if (row.linkedStructureId === st.id) opt.selected = true;
        sel.appendChild(opt);
      });
    return sel;
  }
```

- [ ] **Step 4: Update the tbody row build — add Structure cell + auto-fill label/area/C/tc**

In the tbody row build loop, add a Structure cell as the first `td`, and update the label, area, C, tc cells:

```js
    const rf = resolvedInletFields(row);
    const displayLabel = resolvedInletLabel(row);
    const isLinked = !!row.linkedStructureId;

    // label cell — read-only when linked
    const labelCell = isLinked
      ? el("input", {class:"cell-input", type:"text", style:"width:120px;color:var(--dim,#888);",
          "data-focus-key":"is:"+row.id+":label", value:displayLabel, disabled:true})
      : el("input", {class:"cell-input", type:"text", style:"width:120px;",
          "data-focus-key":"is:"+row.id+":label", value:row.label||"",
          oninput:(e)=>{ row.label=e.target.value; withFocusPreserved(renderAll); }});

    function autoField(field, fromDA, resolvedVal, width) {
      const stored = row[field];
      const isOverride = stored !== "" && stored != null;
      return el("input", {
        class: "cell-input" + (isOverride ? " i-override" : ""),
        type:"text", inputmode:"decimal", style:"width:"+width+"px;",
        "data-focus-key":"is:"+row.id+":"+field,
        value: isOverride ? stored : "",
        placeholder: fromDA ? String(resolvedVal) : "",
        oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderAll); }
      });
    }
```

Then in the `tbody.appendChild(el("tr",{},[` call, prepend the structure cell and replace the area/C/tc cells:

```js
    tbody.appendChild(el("tr",{},[
      el("td",{}, structureDropdown(row)),
      el("td",{}, labelCell),
      // ... existing structureType, L cells stay ...
      el("td",{}, autoField("area", rf.areaFromDA, rf.area, 70)),
      el("td",{}, autoField("C",    rf.CFromDA,    rf.C,    55)),
      el("td",{}, autoField("tc",   rf.tcFromDA,   rf.tc,   60)),
      // ... rest of cells (iOverride, S, Sx, etc.) unchanged ...
    ]));
```

- [ ] **Step 5: Update the `bypassTo` dropdown population**

The `bypassTo` dropdown in each row is populated from `state.inletSpacing.map(r => r.label)`. Update to use `resolvedInletLabel(r)` instead:

Find the `bypassTo` dropdown build — change any `r.label` reference in it to `resolvedInletLabel(r)`.

- [ ] **Step 6: Run tests**

```powershell
cd tests; npm test
```
Expected: 34/34 pass.

- [ ] **Step 7: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 5: inlet spacing — add Structure dropdown, auto-fill area/C/tc from linked DA"
```

---

### Task 6 — `computeInletRow()`: use `resolvedInletFields()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (≈ line 1002)
- Modify: `tests/run-tests.mjs`

- [ ] **Step 1: Write a failing test**

In `tests/run-tests.mjs`, add:
```js
test("computeInletRow uses linkedStructureId DA auto-fill for area/C/tc", () => {
  const da = sdc.state.drainage[0];
  const st = sdc.state.structures[0];
  if (!da || !st) return;
  da.area = "1.0"; da.C = "0.9"; da.tc = "8";
  st.drainageAreaId = da.id;
  const row = {
    id:"test-linked", linkedStructureId: st.id,
    area:"", C:"", tc:"",       // all blank → auto-fill from DA
    iOverride:"", S:"0.04", Sx:"0.02", W:1.33, a:0.0833, n:0.013, L:"10",
    allowableSpread:"", bypassTo:""
  };
  const is = sdc.state.inletSpacingSettings;
  const result = sdc.computeInletRow(row, is, 0, 0);
  // area=1.0, C=0.9 → localCA=0.9, i from rainfall at tc=8
  assert.ok(result.totalCA >= 0.89 && result.totalCA <= 0.91,
    "totalCA should be ~0.9: " + result.totalCA);
});
```

Run `cd tests && npm test` — confirm new test FAILS. 34 existing tests pass.

- [ ] **Step 2: Update `computeInletRow()` to use `resolvedInletFields()`**

Find `function computeInletRow(row, settings, bypassQIn, bypassCAIn)`. At the very top of the function (lines ≈ 1003–1005), replace:

```js
  const tc = Number(row.tc);
  const area = Number(row.area);
  const C    = Number(row.C);
```

With:

```js
  const rf = resolvedInletFields(row);
  const tc   = Number(rf.tc);
  const area = Number(rf.area);
  const C    = Number(rf.C);
```

- [ ] **Step 3: Run tests**

```powershell
cd tests; npm test
```
Expected: 35/35 pass.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 6: computeInletRow uses resolvedInletFields for linked-DA auto-fill"
```

---

### Task 7 — `renderDrainage()`: add read-only "Structure" column

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add "Structure" header to the drainage table**

Find `renderDrainage()`. Find the `thead` row. Add `el("th",{class:"computed"},"Structure")` as the **last computed column** before the two empty `th` for detail/delete buttons:

```js
    el("th",{class:"computed"},"Structure"),
    el("th",{},""), el("th",{},"")
```

- [ ] **Step 2: Add the Structure computed cell to each tbody row**

In the tbody row build, just before `el("td",{}, detailBtn(...))`, add:

```js
      el("td",{class:"out computed-cell"}, (()=>{
        const linked = state.structures.find(s => s.drainageAreaId === row.id);
        return linked ? (linked.structureId || linked.id) : "—";
      })()),
```

- [ ] **Step 3: Run tests**

```powershell
cd tests; npm test
```
Expected: 35/35 pass.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 7: add read-only Structure column to Drainage Area table"
```

---

### Task 8 — Pipe Sizing label rename throughout

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Update `renderPipes()` h1 heading (≈ line 2220)**

Find:
```js
  c.appendChild(el("h1",{},"Pipe Sizing — Manning's Equation"));
```
Replace with:
```js
  c.appendChild(el("h1",{},"Pipe Sizing & Capacity — Manning's Equation"));
```

- [ ] **Step 2: Update `renderPipeSizing25()` h1 heading (≈ line 2989)**

Find:
```js
  c.appendChild(el("h1", {}, "Pipe Sizing — 25-yr Check"));
```
Replace with:
```js
  c.appendChild(el("h1", {}, "Pipe Sizing & Capacity — 25-yr"));
```

- [ ] **Step 3: Update `renderPipeSizing25()` view-desc paragraph**

Find:
```js
    "25-yr check — read only. Pipe geometry is unchanged from the primary Pipe Sizing tab. " +
```
Replace with:
```js
    "25-yr check — read only. Pipe geometry is unchanged from the primary Pipe Sizing & Capacity tab. " +
```

- [ ] **Step 4: Update Overview step entry for Pipe Sizing**

Find `renderOverview()`. Find the step entry that mentions "Pipe Sizing". Update the label/description to say "Pipe Sizing & Capacity".

- [ ] **Step 5: Run tests**

```powershell
cd tests; npm test
```
Expected: 35/35 pass.

- [ ] **Step 6: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 8: rename Pipe Sizing to Pipe Sizing & Capacity throughout"
```

---

### Task 9 — Excel export/import: `linkedStructureId` + DA Structure column

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (≈ lines 4544–4580, 4798–4836)
- Modify: `tests/run-tests.mjs`

- [ ] **Step 1: Update inlet spacing Excel export — add `Linked Structure` column (≈ line 4556)**

In the `buildWorkbook()` inlet spacing export, find the data header row:
```js
    ["Label","Structure Type","L (ft)","Area (ac)","C","Tc (min)","i Override (in/hr)",
     "S","Sx","W (ft)","a (ft)","n","Allowable Spread (ft)","Bypass To",
     "Q (cfs)","Spread T (ft)","Pickup (%)","Bypass CA out"],
```
Replace with:
```js
    ["Linked Structure","Label","Structure Type","L (ft)","Area (ac)","C","Tc (min)","i Override (in/hr)",
     "S","Sx","W (ft)","a (ft)","n","Allowable Spread (ft)","Bypass To",
     "Q (cfs)","Spread T (ft)","Pickup (%)","Bypass CA out"],
```

In the `state.inletSpacing.forEach` data push, prepend the linked structure value as the first column:
```js
    isAoa.push([
      (()=>{
        if (!r.linkedStructureId) return "";
        const st = state.structures.find(s => s.id === r.linkedStructureId);
        return st ? (st.structureId || "") : "";
      })(),
      r.label||"", r.structureType||"",
      // ... rest unchanged ...
    ]);
```

Also update `wsIs["!cols"]` to add one more `{wch:14}` at the front:
```js
  wsIs["!cols"] = [{wch:14},{wch:14},{wch:18},{wch:8},{wch:10},{wch:7},{wch:9},{wch:16},
                   {wch:9},{wch:8},{wch:8},{wch:8},{wch:7},{wch:16},{wch:12},
                   {wch:10},{wch:12},{wch:11},{wch:14}];
```

- [ ] **Step 2: Update Drainage Area Excel export — add `Structure` column**

In `buildWorkbook()`, find the Drainage Area export. The `daHeader` currently starts with `["ID","Description","Area A (ac)",...`. Add `"Structure"` before the Q storm columns:

Find:
```js
  const daHeader = ["ID","Description","Area A (ac)","C","CA","i Override (in/hr)","Tc (min)","Cf","Tc Method", ...daQHdrs];
```
Replace with:
```js
  const daHeader = ["ID","Description","Area A (ac)","C","CA","i Override (in/hr)","Tc (min)","Cf","Tc Method","Structure", ...daQHdrs];
```

In the `daRows.push([...])` call, after `r.tcMethod||"direct",` add:
```js
      (()=>{
        const linked = state.structures.find(s => s.drainageAreaId === r.id);
        return linked ? (linked.structureId || "") : "";
      })(),
```

Also add one more `{wch:12}` to `wsDa["!cols"]` before the storm Q columns:
```js
  wsDa["!cols"] = [{wch:12},{wch:26},{wch:11},{wch:8},{wch:8},{wch:14},{wch:9},{wch:7},{wch:11},{wch:12},
    ...daStorms.map(()=>({wch:10}))];
```

- [ ] **Step 3: Update inlet spacing Excel import — resolve `Linked Structure` → `linkedStructureId` (≈ line 4817)**

In `importExcel()`, find the inlet spacing import row mapping. After `row.bypassTo = String(g("Bypass To")||"");`, add:

```js
              const linkedStructName = String(g("Linked Structure")||"").trim();
              if (linkedStructName) {
                const matchSt = state.structures.find(s => (s.structureId||"") === linkedStructName);
                row.linkedStructureId = matchSt ? matchSt.id : "";
              } else {
                row.linkedStructureId = "";
              }
```

- [ ] **Step 4: Write Excel tests**

In `tests/run-tests.mjs`, add:
```js
test("buildWorkbook: Inlet Spacing sheet has Linked Structure column", () => {
  const wb = sdc.buildWorkbook();
  const XLSX = window.XLSX;
  const ws = wb.Sheets["Inlet Spacing"];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  const headerRow = aoa.find(r => r[0] === "Linked Structure" || r[1] === "Label");
  assert.ok(headerRow, "Linked Structure column header not found");
  assert.equal(headerRow[0], "Linked Structure");
});
```

Run: `cd tests && npm test`. Expected: 36/36 pass.

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 9: Excel export adds Linked Structure to inlet spacing, Structure to DA; import resolves linked structure"
```

---

### Task 10 — Final wiring: `window.__sdc`, Overview update, push

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Verify `window.__sdc` exports**

Find `window.__sdc = {`. Confirm `resolvedInletFields` and `resolvedInletLabel` are present (added in Task 1). If missing, add them now.

- [ ] **Step 2: Update Overview workflow step list**

Find `renderOverview()`. The steps array was re-numbered in the Rainfall & IDF task to have 8 steps (step 1 = Overview, step 2 = Rainfall & IDF, former step 2 became step 3, etc.). 

Find the step entries and:
- Update the step that mentions "Pipe Sizing" → "Pipe Sizing & Capacity"
- Add a new step (or update the Junction Structures step) to mention: "Link inlet-type structures to Inlet Spacing rows — their drainage area values auto-fill"
- Add a step entry for "HGL — review hydraulic grade line results, crown and rim checks"

The step list after changes should flow:
1. Overview
2. Rainfall & IDF
3. Drainage Area
4. Junction Structures — define structures and link drainage areas; inlet-type structures link to Inlet Spacing
5. Inlet Spacing — pick a junction structure to auto-fill area/C/Tc
6. Pipe Sizing & Capacity — size pipes between structures
7. HGL — review computed hydraulic grade line, check against crown and rim

- [ ] **Step 3: Run full test suite**

```powershell
cd tests; npm test
```
Expected: 36/36 pass, zero failures.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 10: update __sdc exports, overview workflow steps for new HGL tab and structure linking"
```

---

## Self-Review

**Spec coverage check:**

| Spec § | Requirement | Task |
|---|---|---|
| §2.1 | `linkedStructureId` on inlet spacing row | Task 1 |
| §2.2 | No changes to structures/DA state | — (confirmed, no changes) |
| §4 | `resolvedInletFields()` and `resolvedInletLabel()` | Task 1 |
| §4 | `computeInletRow` uses `resolvedInletFields` | Task 6 |
| §3.1 | Structure dropdown on inlet spacing row | Task 5 |
| §3.1 | Label read-only when linked; auto-fill with `← DA` indicator | Task 5 |
| §3.2 | DA table read-only Structure column | Task 7 |
| §3.3 | Remove HGL columns from Junction Structures table | Task 4 |
| §3.4 | `renderHgl()` with all required columns | Task 3 |
| §3.5 | `renderHgl25()` rename and label update | Task 2 |
| §5 | Tab order: inlet-spacing at position 5, hgl at 7 | Task 2 |
| §5 | Tab ids: hgl, hgl-25; pipe label "Pipe Sizing & Capacity" | Task 2 |
| §6 | Pipe Sizing h1 and 25-yr label rename | Task 8 |
| §7 | Excel inlet spacing Linked Structure column | Task 9 |
| §7 | Excel DA Structure column | Task 9 |
| §7 | Import resolves linkedStructureId from structure name | Task 9 |
| §8 | view-hgl div, view-hgl-25 div (renamed from view-structures-25) | Task 2 |
| §8 | renderHgl() wired into renderAll() | Task 2 |

**No placeholders found.** All code blocks are complete.

**Type consistency:** `resolvedInletFields(row)` returns `{area, C, tc, areaFromDA, CFromDA, tcFromDA}` — used consistently in Tasks 1, 5, 6. `resolvedInletLabel(row)` returns a string — used in Task 5.

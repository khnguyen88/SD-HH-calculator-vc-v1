# Table Printout (Spreadsheet View) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add "🖨 Print Table" buttons to each of 8 data tabs plus a "🖨 Tables" topbar button, printing the tab's live data table as a compact landscape spreadsheet.

**Architecture:** A shared `buildTablePrintSheet(viewId, title)` deep-clones the first `table.data` from a tab's view div, strips all interactive elements (inputs → text, selects → selected text, buttons removed), and wraps it in a `.calc-sheet.cs-table-sheet` div. `buildOutletTablePrintSheet()` builds rating-curve tables directly from `state` + `computeRatingCurve()` (DOM clone not viable since only the active outlet is rendered). `printNodes()` gains an optional landscape param that injects/removes a `<style id="sdcLandscape">` tag.

**Tech Stack:** Vanilla JS, inline CSS, existing `el()` / `sheetWrapper()` / `printNodes()` helpers, existing `computeRatingCurve()` / `devicesForOutlet()`.

---

## File Structure

**Only one file is modified:**
- `drainage-calculator/storm-drain-design-calculator.html`
  - CSS block (~line 454): add `.cs-table-sheet` styles
  - `printNodes()` (~line 4469): add landscape param
  - `afterprint` handler (~line 4504): remove landscape style tag
  - After `printAllSheets()` (~line 4502): add `buildTablePrintSheet`, `buildOutletTablePrintSheet`, `printTableSheet`, `printAllTableSheets`
  - `renderDrainage()`, `renderStructures()`, `renderPipes()`, `renderOutlet()`, `renderInletSpacing()`, `renderHgl()`, `renderPipeSizing25()`, `renderHgl25()`: add Print Table button to each section head
  - `init()` (~line 5007): wire `printAllTablesBtn`
  - HTML topbar-right (~line 521): add `printAllTablesBtn`

---

## Task 1: Add `.cs-table-sheet` CSS

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (CSS block, after `@media print{...}` block ~line 472)

- [ ] **Step 1: Locate the CSS insertion point**

  Find this block (around line 467):
  ```css
  @media print{
    .app, #toast{ display:none !important; }
    #printArea{ display:block !important; }
    #printArea .calc-sheet{ page-break-after:always; break-after:page; }
    #printArea .calc-sheet:last-child{ page-break-after:auto; }
    @page{ margin:0.5in; }
  }
  ```
  Insert the following immediately after the closing `}`.

- [ ] **Step 2: Insert the CSS**

  ```css
  /* Table printout sheets */
  body.print-mode #printArea .cs-table-sheet{
    min-height:auto;
    padding:0.3in;
  }
  .cs-table-sheet table.data{
    font-size:9.5px;
    width:100%;
    table-layout:auto;
  }
  .cs-table-sheet table.data th,
  .cs-table-sheet table.data td{
    padding:2px 5px;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    max-width:120px;
  }
  @media print{
    .cs-table-sheet table.data{ font-size:8.5px; }
    .cs-table-sheet table.data th,
    .cs-table-sheet table.data td{ max-width:90px; }
  }
  ```

- [ ] **Step 3: Verify** — open the file in a browser and confirm no regressions. The new CSS has no visible effect yet.

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 1: add .cs-table-sheet CSS for table printout"
  ```

---

## Task 2: Update `printNodes()` and `afterprint` handler for landscape support

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (`printNodes` and `afterprint` handler)

- [ ] **Step 1: Find `printNodes`**

  Find:
  ```js
  function printNodes(nodes){
    const pa = document.getElementById("printArea");
    pa.innerHTML = "";
    nodes.forEach(n=>pa.appendChild(n));
    document.body.classList.add("print-mode");
    window.print();
  }
  ```

  Replace with:
  ```js
  function printNodes(nodes, landscape){
    const pa = document.getElementById("printArea");
    pa.innerHTML = "";
    nodes.forEach(n=>pa.appendChild(n));
    if(landscape){
      const s = document.createElement("style");
      s.id = "sdcLandscape";
      s.textContent = "@media print { @page { size: landscape; } }";
      document.head.appendChild(s);
    }
    document.body.classList.add("print-mode");
    window.print();
  }
  ```

- [ ] **Step 2: Find `afterprint` handler**

  Find:
  ```js
  window.addEventListener("afterprint", ()=>{
    document.body.classList.remove("print-mode");
    document.getElementById("printArea").innerHTML = "";
  });
  ```

  Replace with:
  ```js
  window.addEventListener("afterprint", ()=>{
    document.body.classList.remove("print-mode");
    document.getElementById("printArea").innerHTML = "";
    const ls = document.getElementById("sdcLandscape");
    if(ls) ls.remove();
  });
  ```

- [ ] **Step 3: Verify** — existing "Print all" and detail sheet print still work (they don't pass `landscape` so nothing changes for them).

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 2: extend printNodes with optional landscape param"
  ```

---

## Task 3: Add `buildTablePrintSheet`, `buildOutletTablePrintSheet`, `printTableSheet`, `printAllTableSheets`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (JS, after `printAllSheets()` function and before the `window.addEventListener("afterprint"...)`)

- [ ] **Step 1: Locate insertion point**

  Find `window.addEventListener("afterprint", ()=>{`. Insert the following block immediately before it.

- [ ] **Step 2: Insert the four functions**

  ```js
  function buildTablePrintSheet(viewId, title){
    const view = document.getElementById(viewId);
    if(!view) return null;
    const table = view.querySelector("table.data");
    if(!table) return null;
    const tbody = table.querySelector("tbody");
    if(!tbody || tbody.rows.length === 0) return null;

    const clone = table.cloneNode(true);
    // Replace inputs/selects/textareas with their current value as text
    clone.querySelectorAll("input, textarea").forEach(inp=>{
      inp.replaceWith(document.createTextNode(inp.value));
    });
    clone.querySelectorAll("select").forEach(sel=>{
      const txt = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : "";
      sel.replaceWith(document.createTextNode(txt));
    });
    // Remove buttons and checkboxes entirely
    clone.querySelectorAll("button, input[type=checkbox]").forEach(b=>b.remove());

    const now = new Date();
    const pad = n=>String(n).padStart(2,"0");
    const dateStr = now.getFullYear()+"-"+pad(now.getMonth()+1)+"-"+pad(now.getDate());

    const sheet = el("div",{class:"calc-sheet cs-table-sheet"});
    sheet.appendChild(el("div",{class:"cs-header"},[
      el("div",{class:"cs-title"}, title),
      el("div",{class:"cs-sub"}, (state.project||"Untitled")+" — "+dateStr),
    ]));
    const wrap = el("div",{class:"table-wrap"});
    wrap.appendChild(clone);
    sheet.appendChild(wrap);
    sheet.appendChild(el("div",{class:"cs-footer"}, "Storm Drain Design Calculator — "+(state.project||"")));
    return sheet;
  }

  function buildOutletTablePrintSheet(){
    if(state.outletStructures.length===0) return [];
    const nodes = [];
    const now = new Date();
    const pad = n=>String(n).padStart(2,"0");
    const dateStr = now.getFullYear()+"-"+pad(now.getMonth()+1)+"-"+pad(now.getDate());

    state.outletStructures.forEach(os=>{
      const devices = devicesForOutlet(os.id);
      const { rows } = computeRatingCurve(os.id);
      if(!rows || rows.length===0) return;

      const table = el("table",{class:"data"});
      // Build header
      const headCells = [el("th",{},"Stage (ft)"), el("th",{},"TW (ft)")];
      devices.forEach(d=>headCells.push(el("th",{class:"computed"}, (d.label||d.id)+" Q (cfs)")));
      headCells.push(el("th",{class:"computed"},"Total Q (cfs)"));
      table.appendChild(el("thead",{},el("tr",{},headCells)));

      // Build body
      const tbody = el("tbody");
      rows.forEach(r=>{
        const cells = [
          el("td",{class:"out",style:"font-weight:700"}, fmt(r.stage,2)),
          el("td",{class:"out"}, r.tw!=null? fmt(r.tw,2) : "—"),
        ];
        r.devices.forEach(dr=>cells.push(el("td",{class:"out computed-cell"}, fmt(dr.Q,2))));
        cells.push(el("td",{class:"out computed-cell",style:"font-weight:700"}, fmt(r.total,2)));
        tbody.appendChild(el("tr",{},cells));
      });
      table.appendChild(tbody);

      const sheet = el("div",{class:"calc-sheet cs-table-sheet"});
      sheet.appendChild(el("div",{class:"cs-header"},[
        el("div",{class:"cs-title"}, "Outlet — "+(os.label||os.id)),
        el("div",{class:"cs-sub"}, (state.project||"Untitled")+" — "+dateStr),
      ]));
      const wrap = el("div",{class:"table-wrap"});
      wrap.appendChild(table);
      sheet.appendChild(wrap);
      sheet.appendChild(el("div",{class:"cs-footer"}, "Storm Drain Design Calculator — "+(state.project||"")));
      nodes.push(sheet);
    });
    return nodes;
  }

  function printTableSheet(viewId, title){
    if(viewId==="view-outlet"){
      const nodes = buildOutletTablePrintSheet();
      if(nodes.length===0){ toast("No outlet data to print yet.", true); return; }
      printNodes(nodes, true);
      return;
    }
    const sheet = buildTablePrintSheet(viewId, title);
    if(!sheet){ toast("No rows to print yet.", true); return; }
    printNodes([sheet], true);
  }

  function printAllTableSheets(){
    const nodes = [];
    const tabs = [
      ["view-drainage",        "Drainage Area"],
      ["view-structures",      "Junction Structures"],
      ["view-pipes",           "Pipe Sizing & Capacity"],
      ["view-inlet-spacing",   "Inlet Spacing"],
      ["view-hgl",             "HGL — Primary Design Storm"],
      ["view-pipe-sizing-25",  "Pipe Sizing & Capacity — 25-yr"],
      ["view-hgl-25",          "HGL — 25-yr"],
    ];
    tabs.forEach(([vid, title])=>{
      const sheet = buildTablePrintSheet(vid, title);
      if(sheet) nodes.push(sheet);
    });
    // Outlet: one sheet per outlet structure
    buildOutletTablePrintSheet().forEach(n=>nodes.push(n));
    if(nodes.length===0){ toast("Nothing to print yet — add some rows first.", true); return; }
    printNodes(nodes, true);
  }
  ```

- [ ] **Step 3: Verify in browser console**

  Open DevTools → Console and run:
  ```js
  const s = buildTablePrintSheet("view-drainage", "Drainage Area");
  console.log(s ? s.className : "null");
  // Expected: "calc-sheet cs-table-sheet"
  ```

  If no drainage rows exist, it returns null — that's correct.

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 3: add buildTablePrintSheet, buildOutletTablePrintSheet, printTableSheet, printAllTableSheets"
  ```

---

## Task 4: Add Print Table buttons to 8 section heads

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (8 separate section-head changes)

All 8 changes follow the same pattern: find the existing `section.appendChild(el("div",{class:"section-head"},[...]))` call and add the print button as the last child of the array. Each change is shown in full below.

- [ ] **Step 1: Drainage Area — `renderDrainage()`**

  Find:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Drainage areas"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.drainage.push({id:nextId(), structureId:"", desc:"", area:"", C:"", iOverride:"", tc:"", cf:1.0, tcMethod:"direct", tr55:{segments:[]}}); renderDrainage(); }}, "+ Add row")
  ]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Drainage areas"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.drainage.push({id:nextId(), structureId:"", desc:"", area:"", C:"", iOverride:"", tc:"", cf:1.0, tcMethod:"direct", tr55:{segments:[]}}); renderDrainage(); }}, "+ Add row"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-drainage","Drainage Area")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 2: Junction Structures — `renderStructures()`**

  Find:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Structures"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.structures.push({id:nextId(), structureId:"", desc:"", drainageAreaId:"", type:"manhole", forceElev:false, startElev:"", crown:"", rim:"", splitMethod:"capacity", splitCapacity:"", splitRatio:0.5}); renderAll(); }}, "+ Add row")
  ]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Structures"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.structures.push({id:nextId(), structureId:"", desc:"", drainageAreaId:"", type:"manhole", forceElev:false, startElev:"", crown:"", rim:"", splitMethod:"capacity", splitCapacity:"", splitRatio:0.5}); renderAll(); }}, "+ Add row"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-structures","Junction Structures")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 3: Pipe Sizing & Capacity — `renderPipes()`**

  Find:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Pipe runs"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row")
  ]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Pipe runs"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.pipes.push({id:nextId(), fromStructureId:"", toStructureId:"", angle:0, shape:"circular", size:"", n:0.013, slope:"", length:"", splitRole:""}); renderAll(); }}, "+ Add row"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipes","Pipe Sizing & Capacity")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 4: Outlet — `renderOutlet()` devices section**

  Find:
  ```js
  devSection.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Devices"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.outletDevices.push(Object.assign({id:nextId(), outletStructureId:os.id, label:"", type:"orifice", invert:"", crest:"", diameter:"", length:"", weirShape:"rect", notchAngle:90, cd:0.6, coef:3.1, notes:""}, defaultDeviceFields())); renderOutlet(); }}, "+ Add device")
  ]));
  ```
  Replace with:
  ```js
  devSection.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Devices"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.outletDevices.push(Object.assign({id:nextId(), outletStructureId:os.id, label:"", type:"orifice", invert:"", crest:"", diameter:"", length:"", weirShape:"rect", notchAngle:90, cd:0.6, coef:3.1, notes:""}, defaultDeviceFields())); renderOutlet(); }}, "+ Add device"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-outlet","Outlet")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 5: Inlet Spacing — `renderInletSpacing()`**

  Find:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Inlets"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.inletSpacing.push(defaultInletSpacingRow()); withFocusPreserved(renderAll); }}, "+ Add Inlet")
  ]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div",{class:"section-head"},[
    el("h2",{},"Inlets"),
    el("button",{class:"btn btn-sm", onclick:()=>{ state.inletSpacing.push(defaultInletSpacingRow()); withFocusPreserved(renderAll); }}, "+ Add Inlet"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-inlet-spacing","Inlet Spacing")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 6: HGL — `renderHgl()`**

  Find:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Upstream HGL — Primary Design Storm")]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [
    el("h2", {}, "Upstream HGL — Primary Design Storm"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl","HGL — Primary Design Storm")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 7: Pipe Sizing 25-yr — `renderPipeSizing25()`**

  Find:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Pipe capacity check — 25-yr storm")]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [
    el("h2", {}, "Pipe capacity check — 25-yr storm"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipe-sizing-25","Pipe Sizing & Capacity — 25-yr")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 8: HGL 25-yr — `renderHgl25()`**

  Find:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "HGL check — 25-yr storm")]));
  ```
  Replace with:
  ```js
  section.appendChild(el("div", {class:"section-head"}, [
    el("h2", {}, "HGL check — 25-yr storm"),
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl-25","HGL — 25-yr")}, "\u{1F5A8} Print Table")
  ]));
  ```

- [ ] **Step 9: Verify in browser** — navigate to each of the 8 tabs and confirm the "🖨 Print Table" button appears in the section header. Click one (e.g. Drainage Area with example data loaded) and confirm the browser print dialog opens with a landscape-oriented table.

- [ ] **Step 10: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 4: add Print Table button to all 8 section heads"
  ```

---

## Task 5: Add topbar "Print All Tables" button and wire in `init()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (HTML topbar + `init()`)

- [ ] **Step 1: Add the button to topbar HTML**

  Find in the topbar HTML:
  ```html
        <button class="btn btn-sm" id="saveCompBtn" title="Save current project to browser storage">&#8964; Save</button>
        <div class="saves-wrap">
  ```
  Replace with:
  ```html
        <button class="btn btn-sm" id="saveCompBtn" title="Save current project to browser storage">&#8964; Save</button>
        <button class="btn btn-sm" id="printAllTablesBtn" title="Print all data tables as spreadsheet">&#128438; Tables</button>
        <div class="saves-wrap">
  ```

- [ ] **Step 2: Wire in `init()`**

  Find in `init()`:
  ```js
    updateSavesUI();
  ```
  Insert immediately after:
  ```js
    document.getElementById("printAllTablesBtn").addEventListener("click", printAllTableSheets);
  ```

- [ ] **Step 3: Verify in browser** — the "🖨 Tables" button appears in the header between Save and Saves(N). Clicking it with example data loaded opens the print dialog with all tab tables.

- [ ] **Step 4: Full manual test**

  **Test A — Per-tab print (populated):**
  - Go to Drainage Area tab. Click "🖨 Print Table". Print dialog opens. Table shows all drainage rows with no input widgets — just text values.

  **Test B — Per-tab print (empty):**
  - Go to Pipe Sizing & Capacity and delete all rows (or use a fresh state). Click "🖨 Print Table". Toast: "No rows to print yet." No print dialog.

  **Test C — Outlet print:**
  - Go to Outlet tab. Click "🖨 Print Table". Print dialog opens showing Stage / TW / [device Q columns] / Total Q. If no outlet structures, toast "No outlet data to print yet."

  **Test D — Print All Tables:**
  - Click "🖨 Tables" in the topbar. All tabs with data print in sequence. Tabs with no rows are silently skipped.

  **Test E — Landscape orientation:**
  - Check browser print preview — orientation should be landscape. After closing print dialog, orientation is restored (no stale style tag left in DOM). Verify: `document.getElementById("sdcLandscape")` returns null after printing.

  **Test F — Existing detail sheet print unaffected:**
  - Click "⤢ Detail" on any drainage row. In the modal, click "Print all". Detail sheets print correctly in portrait (not landscape).

- [ ] **Step 5: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 5: add Print All Tables topbar button and init() wiring"
  ```

# Detail Table Print Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "📊 Detail Table" print button to each of 8 data tabs and a "📊 Detail" topbar button that prints richly-computed spreadsheet tables built from `state` + calc functions — parallel to the existing DOM-clone "🖨 Print Table" buttons.

**Architecture:** A shared `makeDetailSheet(title, headers, rows)` factory builds the `.calc-sheet.cs-table-sheet` wrapper. Seven per-tab builder functions (`buildDrainageDetailSheet`, `buildStructuresDetailSheet`, `buildPipesDetailSheet(stormOverride)`, `buildInletDetailSheet`, `buildHglDetailSheet(stormOverride)`) compute their rows directly from `state` and existing calc helpers — no DOM clone. Outlet reuses the existing `buildOutletTablePrintSheet()`. A new `computeContributingArea(structureId)` recursive helper accumulates upstream ΣA and ΣCA for the pipe detail table. A `printDetailTableSheet(viewId)` dispatcher and `printAllDetailSheets()` orchestrator route print calls; both pass `landscape:true` to `printNodes()`.

**Tech Stack:** Vanilla JS, inline CSS, existing `el()` / `fmt()` / `printNodes()` helpers, `computeStructureCalc()` / `calcPipeRow()` / `pipeGeometry()` / `manningFullFlow()` / `frictionSlope()` / `lookupIntensity()` / `computeInletChain()` / `resolvedInletFields()` / `resolvedInletLabel()`.

---

## File Structure

**Only one file is modified:**
- `drainage-calculator/storm-drain-design-calculator.html`
  - After `computeTotalFlow` (~line 1619): add `computeContributingArea`
  - After `buildOutletTablePrintSheet` (~line 4637): add `makeDetailSheet` + 5 detail builders
  - After `printAllTableSheets` (~line ~4672): add `printDetailTableSheet` + `printAllDetailSheets`
  - `renderDrainage`, `renderStructures`, `renderPipes`, `renderOutlet` devSection, `renderInletSpacing`, `renderHgl`, `renderPipeSizing25`, `renderHgl25`: add `📊 Detail Table` button to each section-head
  - HTML topbar-right: add `#printAllDetailBtn` between `printAllTablesBtn` and `.saves-wrap`
  - `init()`: wire `printAllDetailBtn` listener

---

## Task 1: Add `computeContributingArea()` helper

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (after `computeTotalFlow`, ~line 1619)

- [ ] **Step 1: Locate insertion point**

  Find:
  ```js
  function computeTotalFlow(structureId, seen, stormOverride){
  ```
  The function ends a few lines after line 1619 with `return { Q: captured+sum, captured, inflow, error:null };`. Insert the new function immediately after the closing `}`.

- [ ] **Step 2: Insert `computeContributingArea`**

  ```js
  function computeContributingArea(structureId, seen){
    seen = seen || new Set();
    if(seen.has(structureId)) return {sumA:0, sumCA:0, controlTc:0};
    const newSeen = new Set(seen);
    newSeen.add(structureId);
    const st = findStructure(structureId);
    if(!st) return {sumA:0, sumCA:0, controlTc:0};
    let sumA=0, sumCA=0, controlTc=0;
    if(st.drainageAreaId){
      const da = findDrainage(st.drainageAreaId);
      if(da){
        const A=parseFloat(da.area)||0, C=parseFloat(da.C)||0;
        sumA+=A; sumCA+=C*A;
        controlTc=Math.max(controlTc, parseFloat(da.tc)||0);
      }
    }
    getIncomingPipes(structureId).forEach(p=>{
      const up = computeContributingArea(p.fromStructureId, newSeen);
      sumA+=up.sumA; sumCA+=up.sumCA;
      controlTc=Math.max(controlTc, up.controlTc);
    });
    return {sumA, sumCA, controlTc};
  }
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 1: add computeContributingArea helper for detail print"
  ```

---

## Task 2: Add `makeDetailSheet` factory + `buildDrainageDetailSheet` + `buildStructuresDetailSheet`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (immediately before `printTableSheet`, ~line 4639)

- [ ] **Step 1: Locate insertion point**

  Find:
  ```js
  function printTableSheet(viewId, title){
  ```
  Insert the following block immediately before it.

- [ ] **Step 2: Insert `makeDetailSheet` factory**

  ```js
  function makeDetailSheet(title, heads, dataRows){
    if(!dataRows.length) return null;
    const now = new Date();
    const pad = n=>String(n).padStart(2,"0");
    const dateStr = now.getFullYear()+"-"+pad(now.getMonth()+1)+"-"+pad(now.getDate());
    const table = el("table",{class:"data"});
    table.appendChild(el("thead",{},el("tr",{},heads)));
    const tbody = el("tbody");
    dataRows.forEach(cells=>tbody.appendChild(el("tr",{},cells)));
    table.appendChild(tbody);
    const sheet = el("div",{class:"calc-sheet cs-table-sheet"});
    sheet.appendChild(el("div",{class:"cs-header"},[
      el("div",{class:"cs-title"}, title),
      el("div",{class:"cs-sub"}, (state.project||"Untitled")+" — "+dateStr),
    ]));
    const wrap = el("div",{class:"table-wrap"});
    wrap.appendChild(table);
    sheet.appendChild(wrap);
    sheet.appendChild(el("div",{class:"cs-footer"}, "Storm Drain Design Calculator — "+(state.project||"")));
    return sheet;
  }
  ```

- [ ] **Step 3: Insert `buildDrainageDetailSheet`**

  ```js
  function buildDrainageDetailSheet(){
    const rf = state.rainfall;
    const storms = availableStorms(rf.rainfallSource);
    const th = (t,c)=>el("th",c?{class:c}:{},t);
    const tdN = (v,d=2)=>el("td",{class:"out computed-cell"},fmt(v,d));
    const heads = [
      th("ID"), th("Description"), th("A (ac)"), th("C"), th("CA"), th("Cf"),
      th("Tc (min)"), th("Tc Method"),
    ];
    storms.forEach(s=>{
      heads.push(th("i "+s+"\n(in/hr)","computed"));
      heads.push(th("Q "+s+"\n(cfs)","computed"));
    });
    heads.push(th("Structure","computed"));
    const rows = state.drainage.map(row=>{
      const calc = calcDrainageRow(row);
      const tc = parseFloat(row.tc);
      const linked = state.structures.find(s=>s.drainageAreaId===row.id);
      const cells = [
        el("td",{},row.structureId||row.id), el("td",{},row.desc||""),
        tdN(calc.A,2), tdN(calc.C,3), tdN(calc.CA,3), tdN(calc.cf,2),
        el("td",{},isFinite(tc)?fmt(tc,1):"—"),
        el("td",{},row.tcMethod==="tr55"?"TR-55":"Direct"),
      ];
      storms.forEach(s=>{
        const i = (isFinite(tc)&&tc>0)
          ? lookupIntensity(tc, rf.rainfallSource, s, rf.county, rf.customNoaa||{})
          : 0;
        cells.push(tdN(i>0?i:null,2));
        cells.push(tdN(calc.Qs[s],2));
      });
      cells.push(el("td",{class:"out computed-cell"}, linked?(linked.structureId||linked.id):"—"));
      return cells;
    });
    return makeDetailSheet("Drainage Area — Detail", heads, rows);
  }
  ```

- [ ] **Step 4: Insert `buildStructuresDetailSheet`**

  ```js
  function buildStructuresDetailSheet(){
    const th = (t,c)=>el("th",c?{class:c}:{},t);
    const tdN = (v,d=2)=>el("td",{class:"out computed-cell"},fmt(v,d));
    const heads = [
      th("Structure ID"), th("Description"), th("Type"), th("DA"),
      th("Cap Q\n(cfs)","computed"), th("Inflow Q\n(cfs)","computed"),
      th("Total Q\n(cfs)","computed"), th("Out Pipe To"),
      th("Hf\n(ft)","computed"), th("Angle\n(°)"), th("Kb","computed"),
      th("Hb\n(ft)","computed"), th("U/S HGL\n(ft)","computed"),
      th("Crown\n(ft)"), th("Crown Chk","computed"),
      th("Rim\n(ft)"),   th("Rim Chk","computed"),
    ];
    const rows = state.structures.map(row=>{
      const calc = computeStructureCalc(row.id);
      const typeLbl = (STRUCTURE_TYPES.find(t=>t[0]===row.type)||["",""])[1];
      const da = row.drainageAreaId ? findDrainage(row.drainageAreaId) : null;
      const outPipe = calc ? calc.outPipe : null;
      const toSt = outPipe ? findStructure(outPipe.toStructureId) : null;
      const inflow = calc ? calc.inflow.reduce((s,p)=>s+(isFinite(p.Q)?p.Q:0),0) : 0;
      const angle = outPipe ? parseFloat(outPipe.angle)||0 : 0;
      const crown = parseFloat(row.crown), rim = parseFloat(row.rim);
      const crownStyle = calc&&calc.crownPass===false ? "color:#e05;font-weight:700;" : "";
      const rimStyle   = calc&&calc.rimPass===false   ? "color:#e05;font-weight:700;" : "";
      return [
        el("td",{},row.structureId||row.id), el("td",{},row.desc||""),
        el("td",{},typeLbl),
        el("td",{},da?(da.structureId||da.id):"—"),
        tdN(calc?calc.captured:null,2), tdN(inflow,2),
        el("td",{class:"out computed-cell",style:"font-weight:700"},fmt(calc?calc.totalFlow:null,2)),
        el("td",{},toSt?(toSt.structureId||toSt.id):"—"),
        tdN(calc?calc.Hf:null,3),
        el("td",{},outPipe?fmt(angle,0)+"°":"—"),
        el("td",{class:"out computed-cell"},calc&&calc.kb!=null?fmt(calc.kb,2):"—"),
        tdN(calc?calc.Hb:null,3),
        el("td",{class:"out computed-cell",style:"font-weight:700"},fmt(calc?calc.elevation:null,2)),
        el("td",{},isFinite(crown)?fmt(crown,2):"—"),
        el("td",{class:"out computed-cell",style:crownStyle},
          !calc||calc.crownPass===null?"—":calc.crownPass?"✓":"✗"),
        el("td",{},isFinite(rim)?fmt(rim,2):"—"),
        el("td",{class:"out computed-cell",style:rimStyle},
          !calc||calc.rimPass===null?"—":calc.rimPass?"✓":"✗ FLOOD"),
      ];
    });
    return makeDetailSheet("Junction Structures — Detail", heads, rows);
  }
  ```

- [ ] **Step 5: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 2: add makeDetailSheet factory, buildDrainageDetailSheet, buildStructuresDetailSheet"
  ```

---

## Task 3: Add `buildPipesDetailSheet(stormOverride)`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (append after Task 2 block, still before `printTableSheet`)

- [ ] **Step 1: Locate insertion point**

  Find `function printTableSheet(viewId, title){` and insert the function immediately before it.

- [ ] **Step 2: Insert `buildPipesDetailSheet`**

  ```js
  function buildPipesDetailSheet(stormOverride){
    const storm = stormOverride || state.rainfall.pipeStorm;
    const rf = state.rainfall;
    const th = (t,c)=>el("th",c?{class:c}:{},t);
    const tdN = (v,d=2)=>el("td",{class:"out computed-cell"},fmt(v,d));
    const heads = [
      th("From"), th("To"),
      th("ΣA\n(ac)","computed"), th("ΣCA","computed"),
      th("Tc\n(min)","computed"), th("i\n(in/hr)","computed"),
      th("Q design\n(cfs)","computed"),
      th("Size\n(in)"), th("Type"), th("n"), th("So\n(%)"), th("L\n(ft)"),
      th("A\n(sf)","computed"), th("R\n(ft)","computed"),
      th("V design\n(fps)","computed"), th("V full\n(fps)","computed"),
      th("Q full\n(cfs)","computed"), th("t pipe\n(min)","computed"),
      th("Hf\n(ft)","computed"), th("Status","computed"),
    ];
    const rows = state.pipes.map(pipe=>{
      const fromSt = findStructure(pipe.fromStructureId);
      const toSt   = findStructure(pipe.toStructureId);
      const fromId = fromSt?(fromSt.structureId||fromSt.id):(pipe.fromStructureId||"—");
      const toId   = toSt  ?(toSt.structureId  ||toSt.id)  :(pipe.toStructureId  ||"—");
      const ca = computeContributingArea(pipe.fromStructureId);
      const i  = ca.controlTc>0
        ? lookupIntensity(ca.controlTc, rf.rainfallSource, storm, rf.county, rf.customNoaa||{})
        : 0;
      const designQ = pipeDesignQ(pipe, null, stormOverride);
      const geo = pipeGeometry(pipe);
      const n = parseFloat(pipe.n), S = parseFloat(pipe.slope), L = parseFloat(pipe.length);
      const front = [
        el("td",{},fromId), el("td",{},toId),
        tdN(ca.sumA,2), tdN(ca.sumCA,3),
        el("td",{class:"out computed-cell"},ca.controlTc>0?fmt(ca.controlTc,1):"—"),
        el("td",{class:"out computed-cell"},i>0?fmt(i,2):"—"),
        tdN(designQ,2),
        el("td",{},pipe.size||"—"),
        el("td",{},pipe.shape==="circular"?"Circular":"Elliptical"),
        el("td",{},isFinite(n)?fmt(n,3):"—"),
        el("td",{},isFinite(S)?fmt(S*100,3):"—"),
        el("td",{},isFinite(L)?fmt(L,0):"—"),
      ];
      if(!geo||!isFinite(n)||!isFinite(S)||S<=0){
        return front.concat([
          el("td",{},"—"),el("td",{},"—"),el("td",{},"—"),el("td",{},"—"),
          el("td",{},"—"),el("td",{},"—"),el("td",{},"—"),
          el("td",{class:"out computed-cell"},"—"),
        ]);
      }
      const {R, V:Vfull, Qfull} = manningFullFlow(n, geo.areaSf, geo.equivDiamIn, S);
      const Vdesign = geo.areaSf>0 ? designQ/geo.areaSf : 0;
      const SfD = frictionSlope(designQ, n, geo.areaSf, R);
      const HfD = SfD*(isFinite(L)?L:0);
      const tPipe = (isFinite(L)&&Vdesign>0) ? (L/Vdesign)/60 : null;
      const pass = Qfull>=designQ;
      return front.concat([
        tdN(geo.areaSf,3), tdN(R,3), tdN(Vdesign,2), tdN(Vfull,2),
        tdN(Qfull,2),
        el("td",{class:"out computed-cell"}, tPipe!=null?fmt(tPipe,2):"—"),
        tdN(HfD,3),
        el("td",{class:"out computed-cell",style:pass?"":"color:#e05;font-weight:700;"},
          pass?"PASS":"FAIL"),
      ]);
    });
    const title = stormOverride==="25yr"
      ? "Pipe Sizing & Capacity — 25-yr Detail"
      : "Pipe Sizing & Capacity — Detail";
    return makeDetailSheet(title, heads, rows);
  }
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 3: add buildPipesDetailSheet with contributing area accumulation"
  ```

---

## Task 4: Add `buildInletDetailSheet()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (still before `printTableSheet`)

- [ ] **Step 1: Insert `buildInletDetailSheet`**

  ```js
  function buildInletDetailSheet(){
    if(!state.inletSpacing.length) return null;
    const s = state.inletSpacingSettings;
    const chain = computeInletChain(state.inletSpacing, s);
    const comp = chain.results;
    const th = (t,c)=>el("th",c?{class:c}:{},t);
    const tdN = (v,d=2)=>el("td",{class:"out computed-cell"},fmt(v,d));
    const heads = [
      th("Label"), th("Linked Struct"), th("L\n(ft)"), th("Area\n(ac)"), th("C"),
      th("Tc\n(min)"), th("i\n(in/hr)","computed"), th("Q\n(cfs)","computed"),
      th("S"), th("Sx"), th("W\n(ft)"), th("a\n(ft)"), th("n"),
      th("SxEff","computed"), th("Spread T\n(ft)","computed"), th("Allow T\n(ft)"),
      th("Lt\n(ft)","computed"), th("Pickup %","computed"),
      th("Bypass To"), th("Bypass CA","computed"), th("Bypass Q\n(cfs)","computed"),
      th("Pass?","computed"),
    ];
    const rows = state.inletSpacing.map(row=>{
      const cc = comp[row.id]||{};
      const rif = resolvedInletFields(row);
      const lbl = resolvedInletLabel(row);
      const linkedSt = row.linkedStructureId ? findStructure(row.linkedStructureId) : null;
      const warnStyle = cc.warn ? "color:#e05;font-weight:700;" : "";
      return [
        el("td",{},lbl||"—"),
        el("td",{},linkedSt?(linkedSt.structureId||linkedSt.id):"Custom"),
        el("td",{},row.L!=null&&row.L!==""?row.L:"—"),
        el("td",{},rif.area!=null&&rif.area!==""?rif.area:"—"),
        el("td",{},rif.C!=null&&rif.C!==""?rif.C:"—"),
        el("td",{},rif.tc!=null&&rif.tc!==""?rif.tc:"—"),
        tdN(cc.i,2), tdN(cc.Q,2),
        el("td",{},cc.isSump?"SUMP":(row.S!=null&&row.S!==""?row.S:"—")),
        el("td",{},row.Sx!=null&&row.Sx!==""?row.Sx:"—"),
        el("td",{},row.W!=null&&row.W!==""?row.W:"—"),
        el("td",{},row.a!=null&&row.a!==""?row.a:"—"),
        el("td",{},row.n!=null&&row.n!==""?row.n:"—"),
        el("td",{class:"out computed-cell"},cc.SxEff!=null?fmt(cc.SxEff,4):"—"),
        el("td",{class:"out computed-cell"},cc.isSump?"SUMP":(cc.T!=null?fmt(cc.T,2):"—")),
        el("td",{},(row.allowableSpread!=null&&row.allowableSpread!=="")?row.allowableSpread:
          (s.allowableSpread!=null&&s.allowableSpread!==""?s.allowableSpread:"—")),
        el("td",{class:"out computed-cell"},cc.Lt!=null?fmt(cc.Lt,1):"—"),
        tdN(cc.pickupPct,1),
        el("td",{},row.bypassTo||"—"),
        tdN(cc.bypassCA,3), tdN(cc.bypassQ,2),
        el("td",{class:"out computed-cell",style:warnStyle},
          cc.cycle?"CYCLE":cc.isSump?"SUMP":(cc.warn?"✗ SPREAD":"✓")),
      ];
    });
    return makeDetailSheet("Inlet Spacing — Detail", heads, rows);
  }
  ```

- [ ] **Step 2: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 4: add buildInletDetailSheet"
  ```

---

## Task 5: Add `buildHglDetailSheet(stormOverride)`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (still before `printTableSheet`)

- [ ] **Step 1: Insert `buildHglDetailSheet`**

  ```js
  function buildHglDetailSheet(stormOverride){
    if(!state.pipes.length) return null;
    const th = (t,c)=>el("th",c?{class:c}:{},t);
    const tdN = (v,d=2)=>el("td",{class:"out computed-cell"},fmt(v,d));
    const heads = [
      th("From"), th("To"),
      th("Q design\n(cfs)","computed"), th("Q full\n(cfs)","computed"),
      th("Size\n(in)"), th("Type"), th("n"),
      th("A\n(sf)","computed"), th("R\n(ft)","computed"),
      th("So\n(ft/ft)"),
      th("Sf design\n(ft/ft)","computed"), th("Sf full\n(ft/ft)","computed"),
      th("V design\n(fps)","computed"), th("V full\n(fps)","computed"),
      th("L\n(ft)"),
      th("Hf design\n(ft)","computed"), th("Hf full\n(ft)","computed"),
      th("Angle\n(°)"), th("Kb","computed"), th("Hb\n(ft)","computed"),
      th("D/S HGL\n(ft)","computed"), th("U/S HGL\n(ft)","computed"),
      th("Crown\n(ft)"), th("Crown Chk","computed"),
      th("Rim\n(ft)"),   th("Rim Chk","computed"),
    ];
    const rows = state.pipes.map(pipe=>{
      const fromSt = findStructure(pipe.fromStructureId);
      const toSt   = findStructure(pipe.toStructureId);
      const calcFrom = computeStructureCalc(pipe.fromStructureId, null, stormOverride);
      const calcTo   = computeStructureCalc(pipe.toStructureId,   null, stormOverride);
      const geo = pipeGeometry(pipe);
      const designQ = pipeDesignQ(pipe, null, stormOverride);
      const fromId = fromSt?(fromSt.structureId||fromSt.id):(pipe.fromStructureId||"—");
      const toId   = toSt  ?(toSt.structureId  ||toSt.id)  :(pipe.toStructureId  ||"—");
      const S = parseFloat(pipe.slope), n = parseFloat(pipe.n), L = parseFloat(pipe.length);
      const angle = parseFloat(pipe.angle)||0;
      const dsHGL = calcTo   ? calcTo.elevation   : null;
      const usHGL = calcFrom ? calcFrom.elevation  : null;
      const crown = parseFloat(fromSt ? fromSt.crown : "");
      const rim   = parseFloat(fromSt ? fromSt.rim   : "");
      const crownPass = (isFinite(usHGL)&&isFinite(crown)) ? usHGL<=crown+1.0 : null;
      const rimPass   = (isFinite(usHGL)&&isFinite(rim))   ? usHGL<=rim-1.0   : null;
      const crownStyle = crownPass===false ? "color:#e05;font-weight:700;" : "";
      const rimStyle   = rimPass  ===false ? "color:#e05;font-weight:700;" : "";

      if(!geo||!isFinite(n)||!isFinite(S)||S<=0){
        return [
          el("td",{},fromId), el("td",{},toId),
          tdN(designQ,2), el("td",{},"—"),
          el("td",{},pipe.size||"—"),
          el("td",{},pipe.shape==="circular"?"Circular":"Elliptical"),
          el("td",{},isFinite(n)?fmt(n,3):"—"),
          el("td",{},"—"), el("td",{},"—"),
          el("td",{},isFinite(S)?fmt(S,4):"—"),
          el("td",{},"—"), el("td",{},"—"), el("td",{},"—"), el("td",{},"—"),
          el("td",{},isFinite(L)?fmt(L,0):"—"),
          el("td",{},"—"), el("td",{},"—"),
          el("td",{},fmt(angle,0)),
          el("td",{},"—"), el("td",{},"—"),
          tdN(dsHGL,2), tdN(usHGL,2),
          el("td",{},isFinite(crown)?fmt(crown,2):"—"),
          el("td",{class:"out computed-cell",style:crownStyle},crownPass===null?"—":crownPass?"✓":"✗"),
          el("td",{},isFinite(rim)?fmt(rim,2):"—"),
          el("td",{class:"out computed-cell",style:rimStyle},rimPass===null?"—":rimPass?"✓":"✗ FLOOD"),
        ];
      }

      const {R, V:Vfull, Qfull} = manningFullFlow(n, geo.areaSf, geo.equivDiamIn, S);
      const Vdesign = geo.areaSf>0 ? designQ/geo.areaSf : 0;
      const SfD = frictionSlope(designQ, n, geo.areaSf, R);
      const SfF = frictionSlope(Qfull,   n, geo.areaSf, R);
      const HfD = SfD*(isFinite(L)?L:0), HfF = SfF*(isFinite(L)?L:0);
      const kb = calcFrom ? calcFrom.kb  : null;
      const Hb = calcFrom ? calcFrom.Hb  : 0;

      return [
        el("td",{},fromId), el("td",{},toId),
        tdN(designQ,2), tdN(Qfull,2),
        el("td",{},pipe.size||"—"),
        el("td",{},pipe.shape==="circular"?"Circular":"Elliptical"),
        el("td",{},fmt(n,3)),
        tdN(geo.areaSf,3), tdN(R,3),
        el("td",{},isFinite(S)?fmt(S,4):"—"),
        el("td",{class:"out computed-cell"},fmt(SfD,5)),
        el("td",{class:"out computed-cell"},fmt(SfF,5)),
        tdN(Vdesign,2), tdN(Vfull,2),
        el("td",{},isFinite(L)?fmt(L,0):"—"),
        el("td",{class:"out computed-cell"},fmt(HfD,3)),
        el("td",{class:"out computed-cell"},fmt(HfF,3)),
        el("td",{},fmt(angle,0)),
        el("td",{class:"out computed-cell"},kb!=null?fmt(kb,2):"—"),
        tdN(Hb,3),
        tdN(dsHGL,2), tdN(usHGL,2),
        el("td",{},isFinite(crown)?fmt(crown,2):"—"),
        el("td",{class:"out computed-cell",style:crownStyle},crownPass===null?"—":crownPass?"✓":"✗"),
        el("td",{},isFinite(rim)?fmt(rim,2):"—"),
        el("td",{class:"out computed-cell",style:rimStyle},rimPass===null?"—":rimPass?"✓":"✗ FLOOD"),
      ];
    });
    const title = stormOverride==="25yr"
      ? "HGL — 25-yr Detail"
      : "HGL — Primary Design Storm Detail";
    return makeDetailSheet(title, heads, rows);
  }
  ```

- [ ] **Step 2: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 5: add buildHglDetailSheet with full friction/velocity/HGL chain"
  ```

---

## Task 6: Add `printDetailTableSheet()` and `printAllDetailSheets()` dispatchers

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (after `printAllTableSheets`, before `window.addEventListener("afterprint"...)`)

- [ ] **Step 1: Locate insertion point**

  Find `window.addEventListener("afterprint", ()=>{`. Insert immediately before it.

- [ ] **Step 2: Insert both dispatcher functions**

  ```js
  function printDetailTableSheet(viewId, title){
    if(viewId==="view-outlet"){
      const nodes = buildOutletTablePrintSheet();
      if(!nodes.length){ toast("No outlet data to print yet.", true); return; }
      printNodes(nodes, true); return;
    }
    let sheet = null;
    if     (viewId==="view-drainage")       sheet = buildDrainageDetailSheet();
    else if(viewId==="view-structures")     sheet = buildStructuresDetailSheet();
    else if(viewId==="view-pipes")          sheet = buildPipesDetailSheet();
    else if(viewId==="view-inlet-spacing")  sheet = buildInletDetailSheet();
    else if(viewId==="view-hgl")            sheet = buildHglDetailSheet();
    else if(viewId==="view-pipe-sizing-25") sheet = buildPipesDetailSheet("25yr");
    else if(viewId==="view-hgl-25")         sheet = buildHglDetailSheet("25yr");
    if(!sheet){ toast("No rows to print yet.", true); return; }
    printNodes([sheet], true);
  }

  function printAllDetailSheets(){
    const nodes = [];
    const drain   = buildDrainageDetailSheet();    if(drain)   nodes.push(drain);
    const structs = buildStructuresDetailSheet();  if(structs) nodes.push(structs);
    const pipes   = buildPipesDetailSheet();       if(pipes)   nodes.push(pipes);
    buildOutletTablePrintSheet().forEach(n=>nodes.push(n));
    const inlet   = buildInletDetailSheet();       if(inlet)   nodes.push(inlet);
    const hgl     = buildHglDetailSheet();         if(hgl)     nodes.push(hgl);
    const pipes25 = buildPipesDetailSheet("25yr"); if(pipes25) nodes.push(pipes25);
    const hgl25   = buildHglDetailSheet("25yr");   if(hgl25)   nodes.push(hgl25);
    if(!nodes.length){ toast("Nothing to print yet — add some rows first.", true); return; }
    printNodes(nodes, true);
  }
  ```

- [ ] **Step 3: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 6: add printDetailTableSheet and printAllDetailSheets dispatchers"
  ```

---

## Task 7: Add `📊 Detail Table` buttons to all 8 section heads

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (8 render functions)

All 8 changes: find the array that already contains a `"🖨 Print Table"` button and append the Detail button as the last element.

- [ ] **Step 1: Drainage Area — `renderDrainage()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-drainage","Drainage Area")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-drainage","Drainage Area")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-drainage","Drainage Area")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 2: Junction Structures — `renderStructures()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-structures","Junction Structures")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-structures","Junction Structures")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-structures","Junction Structures")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 3: Pipe Sizing & Capacity — `renderPipes()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipes","Pipe Sizing & Capacity")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipes","Pipe Sizing & Capacity")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-pipes","Pipe Sizing & Capacity")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 4: Outlet — `renderOutlet()` devSection**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-outlet","Outlet")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-outlet","Outlet")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-outlet","Outlet")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 5: Inlet Spacing — `renderInletSpacing()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-inlet-spacing","Inlet Spacing")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-inlet-spacing","Inlet Spacing")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-inlet-spacing","Inlet Spacing")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 6: HGL — `renderHgl()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl","HGL — Primary Design Storm")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl","HGL — Primary Design Storm")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-hgl","HGL — Primary Design Storm")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 7: Pipe Sizing 25-yr — `renderPipeSizing25()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipe-sizing-25","Pipe Sizing & Capacity — 25-yr")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-pipe-sizing-25","Pipe Sizing & Capacity — 25-yr")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-pipe-sizing-25","Pipe Sizing & Capacity — 25-yr")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 8: HGL 25-yr — `renderHgl25()`**

  Find:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl-25","HGL — 25-yr")}, "\u{1F5A8} Print Table")
  ```
  Replace with:
  ```js
    el("button",{class:"btn btn-sm", onclick:()=>printTableSheet("view-hgl-25","HGL — 25-yr")}, "\u{1F5A8} Print Table"),
    el("button",{class:"btn btn-sm", onclick:()=>printDetailTableSheet("view-hgl-25","HGL — 25-yr")}, "\u{1F4CA} Detail")
  ```

- [ ] **Step 9: Verify in browser** — navigate to each of the 8 tabs and confirm both "🖨 Print Table" and "📊 Detail" buttons appear side-by-side in the section header.

- [ ] **Step 10: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 7: add Detail Table button to all 8 section heads"
  ```

---

## Task 8: Add topbar `📊 Detail` button and wire in `init()`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` (HTML topbar + `init()`)

- [ ] **Step 1: Add the button to topbar HTML**

  Find:
  ```html
        <button class="btn btn-sm" id="printAllTablesBtn" title="Print all data tables as spreadsheet">&#128438; Tables</button>
        <div class="saves-wrap">
  ```
  Replace with:
  ```html
        <button class="btn btn-sm" id="printAllTablesBtn" title="Print all data tables as spreadsheet">&#128438; Tables</button>
        <button class="btn btn-sm" id="printAllDetailBtn" title="Print all detail tables">&#128202; Detail</button>
        <div class="saves-wrap">
  ```

- [ ] **Step 2: Wire in `init()`**

  Find in `init()`:
  ```js
    document.getElementById("printAllTablesBtn").addEventListener("click", printAllTableSheets);
  ```
  Insert immediately after:
  ```js
    document.getElementById("printAllDetailBtn").addEventListener("click", printAllDetailSheets);
  ```

- [ ] **Step 3: Full manual test**

  **Test A — Per-tab detail (Pipe Sizing with example data):**
  Click "📊 Detail" on Pipe Sizing tab. Print preview opens landscape. Columns: From, To, ΣA, ΣCA, Tc, i, Q design, Size, Type, n, So%, L, A, R, V design, V full, Q full, t pipe, Hf, Status. All values populated.

  **Test B — HGL Detail:**
  Click "📊 Detail" on HGL tab. Print preview shows pipe-centric rows: From, To, Q design, Q full, Size, n, A, R, So, Sf design, Sf full, V design, V full, L, Hf design, Hf full, Angle, Kb, Hb, D/S HGL, U/S HGL, Crown check, Rim check.

  **Test C — Drainage Area detail:**
  Click "📊 Detail" on Drainage Area. All storm intensities (i) shown alongside Q values.

  **Test D — Junction Structures detail:**
  Click "📊 Detail" on Junction Structures. Includes Hf, Kb, Hb, U/S HGL, crown/rim checks.

  **Test E — Inlet Spacing detail:**
  Click "📊 Detail" on Inlet Spacing. Shows SxEff, Lt, E (pickup%), bypass chain values.

  **Test F — Print All Detail (topbar):**
  Click "📊 Detail" in topbar. All tabs with data print in one landscape job. Tabs with no rows silently skipped.

  **Test G — 25-yr tabs:**
  Click "📊 Detail" on Pipe Sizing 25-yr and HGL 25-yr. Both use 25-yr flows.

  **Test H — Existing simple print unaffected:**
  Click "🖨 Print Table" on any tab. Still works as before.

  **Test I — Empty state:**
  With no rows in a tab, clicking "📊 Detail" toasts "No rows to print yet." No print dialog.

- [ ] **Step 4: Commit**
  ```
  git add drainage-calculator/storm-drain-design-calculator.html
  git commit -m "Task 8: add Print All Detail topbar button and init() wiring"
  ```

---

## Self-Review

**1. Spec coverage:**
- ✅ `computeContributingArea` — Task 1
- ✅ `makeDetailSheet` factory — Task 2
- ✅ `buildDrainageDetailSheet` — Task 2 (adds intensity per storm)
- ✅ `buildStructuresDetailSheet` — Task 2 (adds Hf, Kb, Hb, HGL, checks)
- ✅ `buildPipesDetailSheet(stormOverride)` — Task 3 (adds ΣA, ΣCA, Tc, i, R, Vdesign, Hf)
- ✅ `buildInletDetailSheet` — Task 4 (adds SxEff, Lt, E, bypass chain)
- ✅ `buildHglDetailSheet(stormOverride)` — Task 5 (pipe-centric, Sf/V/Hf design+full, HGL chain)
- ✅ Outlet reuses `buildOutletTablePrintSheet()` — dispatchers in Task 6
- ✅ 25-yr tabs: `buildPipesDetailSheet("25yr")` and `buildHglDetailSheet("25yr")` — Tasks 3, 5, 6
- ✅ `printDetailTableSheet` dispatcher — Task 6
- ✅ `printAllDetailSheets` — Task 6
- ✅ "📊 Detail" buttons on 8 section heads — Task 7
- ✅ Topbar "📊 Detail" button + `init()` wiring — Task 8

**2. Placeholder scan:** None — all tasks contain complete code.

**3. Type consistency:**
- `computeContributingArea` returns `{sumA, sumCA, controlTc}` — used exactly this way in `buildPipesDetailSheet` (Task 3).
- `makeDetailSheet(title, heads, dataRows)` — called consistently in all 5 builders (Tasks 2–5).
- `printDetailTableSheet(viewId, title)` — called from all 8 section-head buttons with matching viewId strings.
- `buildPipesDetailSheet(stormOverride)` and `buildHglDetailSheet(stormOverride)` — called with `undefined` (design storm) or `"25yr"` consistently in Tasks 6 and 7.

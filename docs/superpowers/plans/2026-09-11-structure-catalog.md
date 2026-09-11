# Structure Catalog & Standard Selection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an agency standard structure catalog (PG DER, MCDOT, MDSHA, MDOT) to the Junction Structures tab with a Mode/Agency/Catalog cascade picker, compute K_ah dynamically from HEC-22 Table 9.4, and remove the redundant `structureType` field from the Inlet Spacing tab.

**Architecture:** All changes live in the single-file app `drainage-calculator/storm-drain-design-calculator.html`. Three new helpers (`STRUCTURE_CATALOG`, `kAhFromAngle`, `resolveStructureCategory`) are added near existing constants. `computeStructureCalc` uses them when `structureMode` is set, falling back to the existing `interpKb` for legacy saves. Five new UI columns are added to `renderStructures`.

**Tech Stack:** Vanilla JS, JSDOM test harness (`node tests/run-tests.mjs`), SheetJS for Excel.

---

## File

- Modify: `drainage-calculator/storm-drain-design-calculator.html`
- Test: `tests/run-tests.mjs`

---

### Task 1: STRUCTURE_CATALOG + kAhFromAngle + resolveStructureCategory

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — near line 679 (after `STRUCTURE_TYPES` constant) and near line 1433 (after `interpKb`)
- Test: `tests/run-tests.mjs` — append new tests at end

- [ ] **Step 1: Write the failing tests**

Append to `tests/run-tests.mjs` before the final blank line:

```js
// ==================== kAhFromAngle ====================
test("kAhFromAngle: access_hole straight (0°) = 0.15", () => {
  isClose(sdc.kAhFromAngle("access_hole", 0), 0.15, 0.001);
});
test("kAhFromAngle: access_hole 90° = 1.00", () => {
  isClose(sdc.kAhFromAngle("access_hole", 90), 1.00, 0.01);
});
test("kAhFromAngle: access_hole 45° interpolated between 90°(1.00) and 135°(0.75)", () => {
  // 45° deflection → theta = 135°; between pts [135,0.75] and [90,1.00]
  // t = (135-135)/(135-90) = 0 → 0.75
  isClose(sdc.kAhFromAngle("access_hole", 45), 0.75, 0.001);
});
test("kAhFromAngle: inlet straight (0°) = 0.50", () => {
  isClose(sdc.kAhFromAngle("inlet", 0), 0.50, 0.001);
});
test("kAhFromAngle: inlet 90° = 1.50", () => {
  isClose(sdc.kAhFromAngle("inlet", 90), 1.50, 0.001);
});
test("kAhFromAngle: inlet 45° interpolated", () => {
  // theta = 135 → 0.50 + 1.00 * ((180-135)/90) = 0.50 + 0.50 = 1.00
  isClose(sdc.kAhFromAngle("inlet", 45), 1.00, 0.01);
});

// ==================== resolveStructureCategory ====================
test("resolveStructureCategory: standard pgder MH = access_hole", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48"
  }), "access_hole");
});
test("resolveStructureCategory: standard pgder inlet = inlet", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-inlet-typeE"
  }), "inlet");
});
test("resolveStructureCategory: custom inlet category", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"custom", structureCategory:"inlet"
  }), "inlet");
});
test("resolveStructureCategory: legacy (no structureMode) → access_hole", () => {
  assert.equal(sdc.resolveStructureCategory({}), "access_hole");
});
test("STRUCTURE_CATALOG has pgder entries", () => {
  assert.ok(sdc.STRUCTURE_CATALOG.pgder.length > 0, "pgder catalog empty");
  assert.ok(sdc.STRUCTURE_CATALOG.pgder.find(e=>e.id==="pgder-mh-48"), "pgder-mh-48 missing");
});
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd tests && node run-tests.mjs 2>&1 | tail -20
```

Expected: failures on all new `kAhFromAngle`, `resolveStructureCategory`, `STRUCTURE_CATALOG` tests with "sdc.kAhFromAngle is not a function" or similar.

- [ ] **Step 3: Add STRUCTURE_CATALOG constant after `STRUCTURE_TYPES` (~line 682)**

After the `const STRUCTURE_TYPES = [...]` block (ends around line 682), insert:

```js
const STRUCTURE_CATALOG = {
  mcdot: [],
  mdsha: [],
  mdot:  [],
  pgder: [
    { id:"pgder-mh-48",        label:"48-in MH (SD 21.1)",        category:"access_hole", shape:"round",       innerDiameter:4.0, innerWidth:null, innerLength:null },
    { id:"pgder-mh-60",        label:"60-in MH (SD 21.2)",        category:"access_hole", shape:"round",       innerDiameter:5.0, innerWidth:null, innerLength:null },
    { id:"pgder-mh-72",        label:"72-in MH (SD 21.3)",        category:"access_hole", shape:"round",       innerDiameter:6.0, innerWidth:null, innerLength:null },
    { id:"pgder-mh-84",        label:"84-in MH (SD 21.4)",        category:"access_hole", shape:"round",       innerDiameter:7.0, innerWidth:null, innerLength:null },
    { id:"pgder-mh-96",        label:"96-in MH (SD 21.5)",        category:"access_hole", shape:"round",       innerDiameter:8.0, innerWidth:null, innerLength:null },
    { id:"pgder-mhA-48",       label:"Type A MH, 4 ft (SD 20.0)", category:"access_hole", shape:"round",       innerDiameter:4.0, innerWidth:null, innerLength:null },
    { id:"pgder-mhA-60",       label:"Type A MH, 5 ft (SD 20.0)", category:"access_hole", shape:"round",       innerDiameter:5.0, innerWidth:null, innerLength:null },
    { id:"pgder-mhA-72",       label:"Type A MH, 6 ft (SD 20.0)", category:"access_hole", shape:"round",       innerDiameter:6.0, innerWidth:null, innerLength:null },
    { id:"pgder-mhA-84",       label:"Type A MH, 7 ft (SD 20.0)", category:"access_hole", shape:"round",       innerDiameter:7.0, innerWidth:null, innerLength:null },
    { id:"pgder-inlet-yardSD15", label:"Precast Yard Inlet (SD 15.0)", category:"inlet", shape:"square",       innerDiameter:null, innerWidth:4.0, innerLength:4.0 },
    { id:"pgder-inlet-typeE",    label:"Type E Inlet (SD 16.0)",       category:"inlet", shape:"square",       innerDiameter:null, innerWidth:5.0, innerLength:5.0 },
    { id:"pgder-inlet-typeK",    label:"Type K Inlet (SD 17.0)",       category:"inlet", shape:"square",       innerDiameter:null, innerWidth:3.0, innerLength:3.0 },
    { id:"pgder-inlet-typeA",    label:"Type A Drop Inlet (SD 10.0)",  category:"inlet", shape:"rectangular",  innerDiameter:null, innerWidth:null, innerLength:null },
    { id:"pgder-inlet-typeB",    label:"Type B Drop Inlet (SD 11.0)",  category:"inlet", shape:"rectangular",  innerDiameter:null, innerWidth:null, innerLength:null },
    { id:"pgder-inlet-typeCI",   label:"Type CI Inlet (SD 13.0)",      category:"inlet", shape:"rectangular",  innerDiameter:null, innerWidth:null, innerLength:null },
    { id:"pgder-inlet-typeD",    label:"Type D Inlet (SD 14.0)",       category:"inlet", shape:"rectangular",  innerDiameter:null, innerWidth:null, innerLength:null },
  ],
};
```

- [ ] **Step 4: Add `kAhFromAngle` and `resolveStructureCategory` after `interpKb` (~line 1433)**

After the closing `}` of `interpKb`, insert:

```js
function kAhFromAngle(structureCategory, deflectionDeg) {
  const d = isFinite(parseFloat(deflectionDeg)) ? parseFloat(deflectionDeg) : 0;
  const theta = 180 - d;  // interior angle; 180 = straight through
  if (structureCategory === "inlet") {
    // HEC-22 Table 9.4: straight→0.50, 90°→1.50; linear between
    return 0.50 + (1.50 - 0.50) * ((180 - theta) / 90);
  }
  // access_hole (manhole / junction box): piecewise linear, HEC-22 Table 9.4
  const pts = [[180, 0.15], [157.5, 0.45], [135, 0.75], [120, 0.85], [90, 1.00]];
  for (let i = 0; i < pts.length - 1; i++) {
    const [t1, k1] = pts[i], [t2, k2] = pts[i + 1];
    if (theta >= t2) {
      return k1 + (k2 - k1) * ((t1 - theta) / (t1 - t2));
    }
  }
  return 1.00;  // clamp for deflection > 90°
}

function resolveStructureCategory(s) {
  if ((s.structureMode === "standard" || s.structureMode === "custom") &&
      s.structureMode === "standard" && s.agency && s.standardStructureId) {
    const entry = (STRUCTURE_CATALOG[s.agency] || []).find(e => e.id === s.standardStructureId);
    return entry ? entry.category : "access_hole";
  }
  return s.structureCategory || "access_hole";
}
```

Note: `resolveStructureCategory` returns the catalog entry's category for standard mode, or `s.structureCategory` (user-set) for custom mode, or `"access_hole"` as the default (covers legacy saves with no `structureMode`).

- [ ] **Step 5: Expose on `__sdc` (~line 5885)**

In the `window.__sdc = { ... }` object (last line of the IIFE), add `kAhFromAngle, resolveStructureCategory, STRUCTURE_CATALOG` to the existing list. The line currently ends with `INLET_STRUCTURES, MOCO_KB_PRESET };`. Change to:

```js
  INLET_STRUCTURES, MOCO_KB_PRESET,
  kAhFromAngle, resolveStructureCategory, STRUCTURE_CATALOG };
```

- [ ] **Step 6: Run tests to verify they pass**

```
cd tests && node run-tests.mjs 2>&1 | tail -30
```

Expected: All new tests pass. Total pass count increases by 12.

- [ ] **Step 7: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 1: STRUCTURE_CATALOG, kAhFromAngle, resolveStructureCategory"
```

---

### Task 2: `computeStructureCalc` dynamic K_ah + new fields on `+ Add row`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — around line 1746 (`computeStructureCalc` Kb section) and line 2394 (`+ Add row` onclick)
- Test: `tests/run-tests.mjs` — append new tests

- [ ] **Step 1: Write the failing tests**

Append to `tests/run-tests.mjs`:

```js
// ==================== computeStructureCalc dynamic K_ah ====================
test("computeStructureCalc: standard structure uses kAhFromAngle, not interpKb", () => {
  // Build a minimal state: one structure (standard, access_hole) → one pipe → outfall
  const s0 = sdc.state;
  const origStructures = s0.structures, origPipes = s0.pipes;
  // Build isolated test state by temporarily replacing state arrays
  const outfallId = "tf-out";
  const structId  = "tf-st";
  s0.structures = [
    { id:outfallId, structureId:"TF-OUT", type:"outfall", forceElev:true, startElev:100,
      drainageAreaId:"", crown:"", rim:"", structureMode:"" },
    { id:structId, structureId:"TF-ST", type:"manhole", forceElev:false, startElev:"",
      drainageAreaId:"", crown:"", rim:"",
      structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48",
      structureCategory:"", shape:"", innerDiameter:"", innerWidth:"", innerLength:"" },
  ];
  s0.pipes = [
    { id:"tf-pipe1", fromStructureId:structId, toStructureId:outfallId,
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:"", downstreamInvert:"", splitRole:"" }
  ];
  const calc = sdc.computeStructureCalc(structId);
  s0.structures = origStructures;
  s0.pipes = origPipes;
  // pgder-mh-48 is access_hole; angle 0° → kAhFromAngle("access_hole",0) ≈ 0.15
  assert.ok(calc != null, "calc is null");
  isClose(calc.kb, 0.15, 0.01, "kb should be ~0.15 for access_hole straight run");
});

test("computeStructureCalc: legacy structure (no structureMode) uses interpKb", () => {
  const s0 = sdc.state;
  const origStructures = s0.structures, origPipes = s0.pipes, origKb = s0.kb;
  const outfallId = "tf-out2";
  const structId  = "tf-st2";
  s0.structures = [
    { id:outfallId, structureId:"TF-OUT2", type:"outfall", forceElev:true, startElev:100,
      drainageAreaId:"", crown:"", rim:"" },
    { id:structId, structureId:"TF-ST2", type:"manhole", forceElev:false, startElev:"",
      drainageAreaId:"", crown:"", rim:"" },
  ];
  s0.pipes = [
    { id:"tf-pipe2", fromStructureId:structId, toStructureId:outfallId,
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:"", downstreamInvert:"", splitRole:"" }
  ];
  s0.kb = [{ angle:0, inlet:0.99, manhole:0.99, bend:0.99 }];
  const calc = sdc.computeStructureCalc(structId);
  s0.structures = origStructures;
  s0.pipes = origPipes;
  s0.kb = origKb;
  // no structureMode → uses interpKb → 0.99 at angle 0
  isClose(calc.kb, 0.99, 0.01, "kb should be 0.99 from custom Kb table");
});
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd tests && node run-tests.mjs 2>&1 | grep -E "FAIL|pass|fail" | tail -10
```

Expected: 2 new failures.

- [ ] **Step 3: Update `computeStructureCalc` to use dynamic K_ah (~line 1746)**

Find the block starting with:
```js
  const kbColumn = KB_COLUMN_FOR_TYPE[st.type] || "bend";
  const inflowPipes = getIncomingPipes(structureId);
  let kb=0, Hb=0, controlling=null;
  if(inflowPipes.length===0){
    kb = interpKb(kbColumn, 0); // nominal entrance condition, no piped inflow to reference
  } else if(inflowPipes.length===1){
    const angle = parseFloat(inflowPipes[0].angle)||0;
    kb = interpKb(kbColumn, angle);
  } else if(inflowPipes.length===2){
    const [p1,p2] = inflowPipes;
    const a1 = parseFloat(p1.angle)||0, a2 = parseFloat(p2.angle)||0;
    const Q1 = pipeDesignQ(p1, null, stormOverride), Q2 = pipeDesignQ(p2, null, stormOverride);
    const A3 = geo ? geo.areaSf : 0;
    const V1_3 = A3>0? Q1/A3:0, V2_3 = A3>0? Q2/A3:0;
    const Kb1 = interpKb(kbColumn, a1), Kb2 = interpKb(kbColumn, a2);
    const Lv1 = Kb1*V1_3*V1_3/(2*G), Lv2 = Kb2*V2_3*V2_3/(2*G);
    const vc = Lv1>Lv2 ? a2 : a1;
    kb = interpKb(kbColumn, vc);
    controlling = { p1,p2,a1,a2,Q1,Q2,V1_3,V2_3,Kb1,Kb2,Lv1,Lv2,vc };
  } else {
```

Replace with:

```js
  const kbColumn = KB_COLUMN_FOR_TYPE[st.type] || "bend";
  const useCatalogKah = st.structureMode === "standard" || st.structureMode === "custom";
  function kbForAngle(angleDeg) {
    return useCatalogKah
      ? kAhFromAngle(resolveStructureCategory(st), angleDeg)
      : interpKb(kbColumn, angleDeg);
  }
  const inflowPipes = getIncomingPipes(structureId);
  let kb=0, Hb=0, controlling=null;
  if(inflowPipes.length===0){
    kb = kbForAngle(0);
  } else if(inflowPipes.length===1){
    const angle = parseFloat(inflowPipes[0].angle)||0;
    kb = kbForAngle(angle);
  } else if(inflowPipes.length===2){
    const [p1,p2] = inflowPipes;
    const a1 = parseFloat(p1.angle)||0, a2 = parseFloat(p2.angle)||0;
    const Q1 = pipeDesignQ(p1, null, stormOverride), Q2 = pipeDesignQ(p2, null, stormOverride);
    const A3 = geo ? geo.areaSf : 0;
    const V1_3 = A3>0? Q1/A3:0, V2_3 = A3>0? Q2/A3:0;
    const Kb1 = kbForAngle(a1), Kb2 = kbForAngle(a2);
    const Lv1 = Kb1*V1_3*V1_3/(2*G), Lv2 = Kb2*V2_3*V2_3/(2*G);
    const vc = Lv1>Lv2 ? a2 : a1;
    kb = kbForAngle(vc);
    controlling = { p1,p2,a1,a2,Q1,Q2,V1_3,V2_3,Kb1,Kb2,Lv1,Lv2,vc };
  } else {
```

Also add `useCatalogKah` to the returned object. Find the `return {` at the end of `computeStructureCalc` (~line 1775):
```js
  return {
    structure: st, totalFlow, captured: totalFlowInfo.captured, inflow: totalFlowInfo.inflow,
    outPipe, outPipeFlow, downstream, downstreamElev, Sf, Hf, kbColumn, kb, Hb, Vout,
    inflowCount: inflowPipes.length, inflowPipes, controlling,
```
Change to:
```js
  return {
    structure: st, totalFlow, captured: totalFlowInfo.captured, inflow: totalFlowInfo.inflow,
    outPipe, outPipeFlow, downstream, downstreamElev, Sf, Hf, kbColumn, kb, Hb, Vout,
    inflowCount: inflowPipes.length, inflowPipes, controlling, useCatalogKah,
```

- [ ] **Step 4: Update `+ Add row` onclick in `renderStructures` (~line 2394)**

Find:
```js
el("button",{class:"btn btn-sm", onclick:()=>{ state.structures.push({id:nextId(), structureId:"", desc:"", drainageAreaId:"", type:"manhole", forceElev:false, startElev:"", crown:"", rim:"", splitMethod:"capacity", splitCapacity:"", splitRatio:0.5}); renderAll(); }}, "+ Add row"),
```

Replace with:
```js
el("button",{class:"btn btn-sm", onclick:()=>{ state.structures.push({id:nextId(), structureId:"", desc:"", drainageAreaId:"", type:"manhole", forceElev:false, startElev:"", crown:"", rim:"", splitMethod:"capacity", splitCapacity:"", splitRatio:0.5, structureMode:"standard", agency:"", standardStructureId:"", structureCategory:"", shape:"", innerDiameter:"", innerWidth:"", innerLength:""}); renderAll(); }}, "+ Add row"),
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd tests && node run-tests.mjs 2>&1 | tail -15
```

Expected: All new tests pass (2 new passes).

- [ ] **Step 6: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 2: computeStructureCalc dynamic K_ah, new structure fields"
```

---

### Task 3: `renderStructures` — Mode / Agency / Catalog cascade UI

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — `renderStructures` function (~lines 2385–2492)

- [ ] **Step 1: Add 5 column headers to the table `<thead>` (~line 2401)**

Find the `el("thead"...)` block in `renderStructures`. The current header row ends with:
```js
    el("th",{},"Fixed?"), el("th",{},"Fixed/Start Elev"), el("th",{},"Crown (ft)"), el("th",{},"Rim/Grate (ft)"),
    el("th",{class:"computed"},"Captured Q"), el("th",{class:"computed"},"Inflow"), el("th",{class:"computed"},"Total Flow"),
    el("th",{},""), el("th",{},"")
```

Replace with:
```js
    el("th",{},"Fixed?"), el("th",{},"Fixed/Start Elev"), el("th",{},"Crown (ft)"), el("th",{},"Rim/Grate (ft)"),
    el("th",{},"Mode"), el("th",{},"Agency / Category"), el("th",{},"Structure / Shape"), el("th",{},"Inner Size"), el("th",{class:"computed"},"K_ah"),
    el("th",{class:"computed"},"Captured Q"), el("th",{class:"computed"},"Inflow"), el("th",{class:"computed"},"Total Flow"),
    el("th",{},""), el("th",{},"")
```

- [ ] **Step 2: Add the 5 new cells to each row in `state.structures.forEach` (~line 2411)**

Find the `tr` construction in the `state.structures.forEach` loop. Currently it starts:
```js
    const tr = el("tr",{},[
      el("td",{}, txt(row,"structureId",90)),
      ...
      el("td",{}, num(row,"rim",75)),
      el("td",{class:"out computed-cell"}, fmt(calc.captured,2)),
```

Insert after `el("td",{}, num(row,"rim",75)),`:
```js
      el("td",{}, modeToggle(row)),
      el("td",{}, isStandard ? agencySelect(row) : categorySelect(row)),
      el("td",{}, isStandard ? catalogSelect(row) : shapeSelect(row)),
      innerSizeCell(row),
      el("td",{class:"out computed-cell"}, kAhDisplay(row, calc)),
```

And add `const isStandard = (row.structureMode || "standard") === "standard";` at the top of the `forEach` callback, before `const calc = computeStructureCalc(row.id);`.

- [ ] **Step 3: Add the 5 helper functions inside `renderStructures` (before the closing `}`)**

Add after the existing `function checkBadge(...)` function (~line 2488):

```js
  function modeToggle(row) {
    const isStd = (row.structureMode || "standard") === "standard";
    const wrap = el("div",{style:"display:flex;gap:3px;"});
    const btnStd = el("button",{
      class:"btn btn-sm"+(isStd?" btn-active":""),
      onclick:()=>{
        row.structureMode="standard";
        row.structureCategory=""; row.shape="";
        row.innerDiameter=""; row.innerWidth=""; row.innerLength="";
        withFocusPreserved(renderStructures);
      }
    },"Std");
    const btnCust = el("button",{
      class:"btn btn-sm"+(!isStd?" btn-active":""),
      onclick:()=>{
        row.structureMode="custom";
        row.agency=""; row.standardStructureId="";
        withFocusPreserved(renderStructures);
      }
    },"Cust");
    wrap.appendChild(btnStd); wrap.appendChild(btnCust);
    return wrap;
  }

  function agencySelect(row) {
    const sel = el("select",{class:"cell-input",style:"width:90px",
      "data-focus-key":"structures:"+row.id+":agency",
      onchange:(e)=>{ row.agency=e.target.value; row.standardStructureId=""; withFocusPreserved(renderStructures); }});
    sel.appendChild(el("option",{value:""},"— pick —"));
    [["mcdot","MCDOT"],["mdsha","MDSHA"],["mdot","MDOT"],["pgder","PG DER"]].forEach(([v,l])=>{
      const o=el("option",{value:v},l); if(row.agency===v) o.selected=true; sel.appendChild(o);
    });
    return sel;
  }

  function catalogSelect(row) {
    const entries = (STRUCTURE_CATALOG[row.agency]||[]);
    const sel = el("select",{class:"cell-input",style:"width:160px",
      "data-focus-key":"structures:"+row.id+":standardStructureId",
      onchange:(e)=>{
        row.standardStructureId=e.target.value;
        const entry = entries.find(x=>x.id===e.target.value);
        if(entry){
          row.shape = entry.shape;
          row.innerDiameter = entry.innerDiameter != null ? String(entry.innerDiameter) : "";
          row.innerWidth = entry.innerWidth != null ? String(entry.innerWidth) : "";
          row.innerLength = entry.innerLength != null ? String(entry.innerLength) : "";
        }
        withFocusPreserved(renderStructures);
      }});
    sel.appendChild(el("option",{value:""},entries.length?"— select —":"— none —"));
    entries.forEach(e=>{
      const o=el("option",{value:e.id},e.label); if(row.standardStructureId===e.id) o.selected=true; sel.appendChild(o);
    });
    return sel;
  }

  function categorySelect(row) {
    const sel = el("select",{class:"cell-input",style:"width:110px",
      "data-focus-key":"structures:"+row.id+":structureCategory",
      onchange:(e)=>{ row.structureCategory=e.target.value; withFocusPreserved(renderStructures); }});
    [["","— category —"],["access_hole","Access Hole"],["inlet","Inlet"]].forEach(([v,l])=>{
      const o=el("option",{value:v},l); if((row.structureCategory||"")===v) o.selected=true; sel.appendChild(o);
    });
    return sel;
  }

  function shapeSelect(row) {
    const sel = el("select",{class:"cell-input",style:"width:100px",
      "data-focus-key":"structures:"+row.id+":shape",
      onchange:(e)=>{ row.shape=e.target.value; withFocusPreserved(renderStructures); }});
    [["","— shape —"],["round","Round"],["rectangular","Rectangular"],["square","Square"]].forEach(([v,l])=>{
      const o=el("option",{value:v},l); if((row.shape||"")===v) o.selected=true; sel.appendChild(o);
    });
    return sel;
  }

  function innerSizeCell(row) {
    const isStd = (row.structureMode||"standard") === "standard";
    if(isStd){
      const s = row.shape||"";
      let text = "—";
      if(s==="round" && row.innerDiameter) text = row.innerDiameter+" ft dia";
      else if((s==="square"||s==="rectangular") && row.innerWidth) {
        text = row.innerWidth+(row.innerLength && row.innerLength!==row.innerWidth ? "×"+row.innerLength : "")+" ft";
      }
      return el("td",{class:"out computed-cell"}, text);
    }
    const s = row.shape||"";
    const wrap = el("div",{style:"display:flex;gap:4px;align-items:center;"});
    if(s==="round"){
      wrap.appendChild(num(row,"innerDiameter",55)); wrap.appendChild(el("span",{},"ft dia"));
    } else if(s==="rectangular"){
      wrap.appendChild(num(row,"innerWidth",40)); wrap.appendChild(el("span",{},"×")); wrap.appendChild(num(row,"innerLength",40)); wrap.appendChild(el("span",{},"ft"));
    } else if(s==="square"){
      wrap.appendChild(num(row,"innerWidth",55)); wrap.appendChild(el("span",{},"ft sq"));
    }
    return el("td",{}, wrap);
  }

  function kAhDisplay(row, calc) {
    if(!calc || !calc.outPipe) return "—";
    const cat = resolveStructureCategory(row);
    const angle = parseFloat(calc.outPipe.angle)||0;
    return fmt(kAhFromAngle(cat, angle), 3);
  }
```

- [ ] **Step 4: Open app in browser, add a structure, select "Standard" → PG DER → 48-in MH**

Open `drainage-calculator/storm-drain-design-calculator.html` in a browser.
- Click Junction Structures tab
- Click "+ Add row"
- The new row should show Std/Cust buttons, Agency dropdown, Structure dropdown, Inner Size cell, K_ah cell
- Select "Std", pick Agency "PG DER", pick "48-in MH (SD 21.1)" → Inner Size should show "4 ft dia", K_ah should show "0.150"
- Switch to "Cust", pick "Access Hole", shape "Round" → K_ah should still compute from angle

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 3: renderStructures cascade picker — Mode/Agency/Catalog/Inner Size/K_ah"
```

---

### Task 4: `renderInletSpacing` — remove `structureType` column

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — `defaultInletSpacingRow` (~line 1273) and `renderInletSpacing` (~line 3478)
- Test: `tests/run-tests.mjs` — append new test

- [ ] **Step 1: Write the failing test**

Append to `tests/run-tests.mjs`:

```js
// ==================== Inlet Spacing structureType removal ====================
test("defaultInletSpacingRow has no structureType field", () => {
  const row = sdc.defaultInletSpacingRow();
  assert.equal("structureType" in row, false, "structureType should not exist on defaultInletSpacingRow");
});
```

- [ ] **Step 2: Run test to verify it fails**

```
cd tests && node run-tests.mjs 2>&1 | tail -10
```

Expected: 1 new failure — "structureType should not exist on defaultInletSpacingRow".

- [ ] **Step 3: Remove `structureType` from `defaultInletSpacingRow` (~line 1278)**

Find:
```js
    structureType: "",  // INLET_STRUCTURES id or ""
```
Delete this line entirely.

- [ ] **Step 4: Remove "Structure Type" column header from `renderInletSpacing` (~line 3572)**

Find in the `el("thead"...)` block:
```js
    el("th",{},"Structure"), el("th",{},"Label"), el("th",{},"Structure Type"), el("th",{},"L (ft)"),
```
Change to:
```js
    el("th",{},"Structure"), el("th",{},"Label"), el("th",{},"L (ft)"),
```

- [ ] **Step 5: Remove `stypeSelect(row)` from the `tbody.appendChild` row (~line 3635)**

Find the row building in `rows.forEach`:
```js
      el("td",{}, structureDropdown(row)),
      el("td",{}, labelCell),
      el("td",{}, stypeSelect(row)),
      el("td",{}, txtCell(row,"L",60)),
```
Change to:
```js
      el("td",{}, structureDropdown(row)),
      el("td",{}, labelCell),
      el("td",{}, txtCell(row,"L",60)),
```

- [ ] **Step 6: Remove the `stypeSelect` function definition from inside `renderInletSpacing` (~line 3669)**

Find and delete the entire `function stypeSelect(row){...}` block (~lines 3669–3688):
```js
  function stypeSelect(row){
    const sel = el("select",{class:"cell-input",style:"width:150px",
      "data-focus-key":"is:"+row.id+":stype",
      onchange:(e)=>{
        row.structureType=e.target.value;
        const preset = INLET_STRUCTURES.find(st=>st.id===e.target.value);
        if(preset){
          row.W = preset.W; row.a = preset.a; row.n = preset.n;
          if(row.L==="" || row.L==null) row.L = String(preset.Ls[0]);
        }
        withFocusPreserved(renderAll);
      }});
    sel.appendChild(el("option",{value:""},"— Select —"));
    INLET_STRUCTURES.forEach(st=>{
      const o = el("option",{value:st.id}, st.id+" "+st.label);
      if(row.structureType===st.id) o.selected=true;
      sel.appendChild(o);
    });
    return sel;
  }
```

- [ ] **Step 7: Run tests to verify they pass**

```
cd tests && node run-tests.mjs 2>&1 | tail -10
```

Expected: All tests pass (1 new pass).

- [ ] **Step 8: Visually verify in browser**

Open the Inlet Spacing tab. Confirm "Structure Type" column is gone. The W, a, n columns remain as editable text cells.

- [ ] **Step 9: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 4: remove structureType from inlet spacing"
```

---

### Task 5: Detail sheet updates — catalog name and K_ah source in `buildHglRowSheet` and `buildStructureSheet`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — `buildStructureSheet` (~line 3869) and `buildHglRowSheet` (~line 3954)

- [ ] **Step 1: Add catalog info to `buildStructureSheet` "Structure" section (~line 3869)**

Find the existing `csSection("Structure", csTable([...]))` block:
```js
  body.push(csSection("Structure", csTable([
    ["Type", (STRUCTURE_TYPES.find(t=>t[0]===st.type)||["","?"])[1]],
    ["Description", st.desc||"—"],
    ["Linked drainage area", st.drainageAreaId? ((findDrainage(st.drainageAreaId)||{}).structureId || st.drainageAreaId) : "none"],
  ])));
```

Replace with:
```js
  const catalogEntry = (st.structureMode==="standard" && st.agency && st.standardStructureId)
    ? (STRUCTURE_CATALOG[st.agency]||[]).find(e=>e.id===st.standardStructureId) : null;
  const catalogLabel = catalogEntry
    ? catalogEntry.label+" ("+({"mcdot":"MCDOT","mdsha":"MDSHA","mdot":"MDOT","pgder":"PG DER"}[st.agency]||st.agency)+")"
    : st.structureMode==="custom"
      ? "Custom — "+(st.shape||"?")+(st.shape==="round"&&st.innerDiameter?" ("+st.innerDiameter+" ft dia)":
          (st.innerWidth?" ("+st.innerWidth+(st.innerLength&&st.innerLength!==st.innerWidth?"×"+st.innerLength:"")+" ft)":""))
      : "— (legacy / Kb table)";
  const innerSizeRow = catalogEntry&&catalogEntry.shape==="round"&&catalogEntry.innerDiameter
    ? [["Inner diameter", catalogEntry.innerDiameter+" ft"]]
    : catalogEntry&&catalogEntry.innerWidth
      ? [["Inner size", catalogEntry.innerWidth+(catalogEntry.innerLength&&catalogEntry.innerLength!==catalogEntry.innerWidth?"×"+catalogEntry.innerLength:"")+" ft"]]
      : [];
  body.push(csSection("Structure", csTable([
    ["Type", (STRUCTURE_TYPES.find(t=>t[0]===st.type)||["","?"])[1]],
    ["Description", st.desc||"—"],
    ["Linked drainage area", st.drainageAreaId? ((findDrainage(st.drainageAreaId)||{}).structureId || st.drainageAreaId) : "none"],
    ["Catalog / mode", catalogLabel],
    ...innerSizeRow,
  ])));
```

- [ ] **Step 2: Update the K_ah source note in `buildHglRowSheet` (~line 3955)**

Find:
```js
    structLossBody.push(el("div",{class:"cs-note"}, "Inflow pipe count: "+calc.inflowCount+" — Kb column: "+(calc.kbColumn||"n/a")));
```

Replace with:
```js
    const kSourceNote = calc.useCatalogKah
      ? "Inflow pipe count: "+calc.inflowCount+" — Kₐₕ from HEC-22 Table 9.4 ("+resolveStructureCategory(st)+")"
      : "Inflow pipe count: "+calc.inflowCount+" — Kb column: "+(calc.kbColumn||"n/a")+" (legacy Kb table)";
    structLossBody.push(el("div",{class:"cs-note"}, kSourceNote));
```

Also update the `["Kb", ...]` table row at line ~3977 to use "K_ah / Kb" as the label:

Find:
```js
      structLossBody.push(csTable([
        ["Vout = Total Flow / A(outgoing pipe)", fmt(calc.Vout,2)+" fps"],
        ["Kb", fmt(calc.kb,3)],
      ]));
      structLossBody.push(csFormula(["Hb = Kb × Vout² / 2g = "+fmt(calc.kb,3)+" × "+fmt(calc.Vout,2)+"² / "+ (2*G).toFixed(1)]));
      structLossBody.push(csResult("Hb", fmt(calc.Hb,4)+" ft"));
```

Replace with:
```js
      const kLabel = calc.useCatalogKah ? "Kₐₕ (HEC-22 Approx.)" : "Kb";
      structLossBody.push(csTable([
        ["Vout = Total Flow / A(outgoing pipe)", fmt(calc.Vout,2)+" fps"],
        [kLabel, fmt(calc.kb,3)],
      ]));
      structLossBody.push(csFormula([kLabel+" × Vout² / 2g = "+fmt(calc.kb,3)+" × "+fmt(calc.Vout,2)+"² / "+ (2*G).toFixed(1)]));
      structLossBody.push(csResult("H_ah / Hb", fmt(calc.Hb,4)+" ft"));
```

- [ ] **Step 3: Run tests**

```
cd tests && node run-tests.mjs 2>&1 | tail -10
```

Expected: All tests still pass (no new failures).

- [ ] **Step 4: Visually verify in browser**

Open a junction structure with a standard catalog selection (e.g., PG DER 48-in MH). Click the detail (⤢) button on the HGL tab. The structure loss section should show "K_ah from HEC-22 Table 9.4 (access_hole)" instead of "Kb column: manhole". The buildStructureSheet detail should show "Catalog / mode: 48-in MH (SD 21.1) (PG DER)" and "Inner diameter: 4.0 ft".

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 5: detail sheets show catalog name and K_ah source"
```

---

### Task 6: Excel export — new Structure sheet columns, remove IS `structureType`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — `buildWorkbook` (~lines 5263–5338 for Structures, ~lines 5497–5537 for Inlet Spacing)

- [ ] **Step 1: Extend the Structures sheet header (~line 5263)**

Find:
```js
  const stHeader = ["Structure ID","Description","Drainage Area ID","Type","Force Fixed","Fixed-Start Elev (ft)","Crown Elev (ft)","Rim-Grate Elev (ft)",
    "Captured Q (cfs)","Q from Pipes (cfs)","Total Flow (cfs)","Outgoing Pipe ID","Hf (ft)","Kb","Hb (ft)","Vout (fps)","Upstream HGL (ft)","Downstream Structure ID","Crown Check","Rim Check",
    "Split Method","Split Capacity (cfs)","Split Ratio (0-1)"];
```

Replace with:
```js
  const stHeader = ["Structure ID","Description","Drainage Area ID","Type","Force Fixed","Fixed-Start Elev (ft)","Crown Elev (ft)","Rim-Grate Elev (ft)",
    "Captured Q (cfs)","Q from Pipes (cfs)","Total Flow (cfs)","Outgoing Pipe ID","Hf (ft)","Kb","Hb (ft)","Vout (fps)","Upstream HGL (ft)","Downstream Structure ID","Crown Check","Rim Check",
    "Split Method","Split Capacity (cfs)","Split Ratio (0-1)",
    "Structure Mode","Agency","Catalog ID","Category","Shape","Inner Dia (ft)","Inner W (ft)","Inner L (ft)"];
```

- [ ] **Step 2: Extend each structure data row (~line 5269)**

Find the line:
```js
      (s.crown===""||s.crown==null)?"":num(s.crown), (s.rim===""||s.rim==null)?"":num(s.rim),
      null,null,null,null,null,null,null,null,null,null,null,null,
      s.type==="splitter"?(s.splitMethod||"capacity"):"", s.type==="splitter"?num(s.splitCapacity):"", s.type==="splitter"?num(s.splitRatio,0.5):""]);
```

Replace with:
```js
      (s.crown===""||s.crown==null)?"":num(s.crown), (s.rim===""||s.rim==null)?"":num(s.rim),
      null,null,null,null,null,null,null,null,null,null,null,null,
      s.type==="splitter"?(s.splitMethod||"capacity"):"", s.type==="splitter"?num(s.splitCapacity):"", s.type==="splitter"?num(s.splitRatio,0.5):"",
      s.structureMode||"", s.agency||"", s.standardStructureId||"", s.structureCategory||"", s.shape||"",
      (s.innerDiameter===""||s.innerDiameter==null)?"":s.innerDiameter,
      (s.innerWidth===""||s.innerWidth==null)?"":s.innerWidth,
      (s.innerLength===""||s.innerLength==null)?"":s.innerLength]);
```

- [ ] **Step 3: Update column width array for Structures sheet (~line 5338)**

Find:
```js
  wsSt["!cols"] = Array(23).fill({wch:13});
```

Replace with:
```js
  wsSt["!cols"] = Array(31).fill({wch:13});
```

- [ ] **Step 4: Update the column comment (~line 5280)**

Find the comment:
```js
  //                U splitMethod V splitCapacity W splitRatio
```

Replace with:
```js
  //                U splitMethod V splitCapacity W splitRatio
  //                X structureMode Y agency Z catalogId AA category AB shape AC innerDia AD innerW AE innerL
```

- [ ] **Step 5: Remove "Structure Type" from Inlet Spacing export header (~line 5504)**

Find:
```js
    ["Linked Structure","Label","Structure Type","L (ft)","Area (ac)","C","Tc (min)","i Override (in/hr)",
     "S","Sx","W (ft)","a (ft)","n","Allowable Spread (ft)","Bypass To",
     "Q (cfs)","Spread T (ft)","Pickup (%)","Bypass CA out"],
```

Replace with:
```js
    ["Linked Structure","Label","L (ft)","Area (ac)","C","Tc (min)","i Override (in/hr)",
     "S","Sx","W (ft)","a (ft)","n","Allowable Spread (ft)","Bypass To",
     "Q (cfs)","Spread T (ft)","Pickup (%)","Bypass CA out"],
```

- [ ] **Step 6: Remove `r.structureType||""` from Inlet Spacing data rows (~line 5516)**

Find:
```js
      r.label||"", r.structureType||"",
```

Replace with:
```js
      r.label||"",
```

- [ ] **Step 7: Update Inlet Spacing column widths (~line 5535)**

Find:
```js
  wsIs["!cols"] = [{wch:14},{wch:14},{wch:18},{wch:8},{wch:10},{wch:7},{wch:9},{wch:16},
                   {wch:9},{wch:8},{wch:8},{wch:8},{wch:7},{wch:16},{wch:12},
                   {wch:10},{wch:12},{wch:11},{wch:14}];
```

Replace with (remove the `{wch:18}` that was Structure Type):
```js
  wsIs["!cols"] = [{wch:14},{wch:14},{wch:8},{wch:10},{wch:7},{wch:9},{wch:16},
                   {wch:9},{wch:8},{wch:8},{wch:8},{wch:7},{wch:16},{wch:12},
                   {wch:10},{wch:12},{wch:11},{wch:14}];
```

- [ ] **Step 8: Run tests**

```
cd tests && node run-tests.mjs 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Task 6: Excel export — Structure sheet new columns, remove IS structureType"
```

---

### Task 7: Excel import — read new Structure fields, drop IS `structureType`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html` — `importExcel` function, Structures import (~line 5656) and Inlet Spacing import (~line 5780)

- [ ] **Step 1: Write the failing test**

Append to `tests/run-tests.mjs`:

```js
// ==================== Excel round-trip: new Structure fields ====================
test("buildWorkbook: new structure fields present in Junction Structure sheet", () => {
  const s0 = sdc.state;
  const orig = s0.structures;
  s0.structures = [{
    id:"rt-st1", structureId:"RT-1", desc:"", drainageAreaId:"", type:"manhole",
    forceElev:false, startElev:"", crown:"", rim:"",
    splitMethod:"capacity", splitCapacity:"", splitRatio:0.5,
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48",
    structureCategory:"", shape:"round", innerDiameter:"4", innerWidth:"", innerLength:"",
  }];
  s0.pipes = [];
  const wb = sdc.buildWorkbook();
  s0.structures = orig;
  const ws = wb.Sheets["Junction Structure"];
  assert.ok(ws, "Junction Structure sheet missing");
  // Check header row has new columns (row 1 in 1-indexed = "1")
  // Find column X (index 24 = col X in 1-based Excel, but easier to check aoa)
  const { utils } = window.XLSX || {};  // may not be exposed — use sheet_to_json
  // Just verify the sheet has data rows with the right column count
  const keys = Object.keys(ws).filter(k => k !== "!ref" && k !== "!cols" && k.match(/^[A-Z]+1$/));
  assert.ok(keys.some(k => {
    const cell = ws[k];
    return cell && cell.v === "Structure Mode";
  }), "Structure Mode header missing");
});
```

- [ ] **Step 2: Run test to verify it fails**

```
cd tests && node run-tests.mjs 2>&1 | tail -10
```

Expected: 1 new failure.

- [ ] **Step 3: Add new structure fields to the import mapper (~line 5661)**

Find the structure import `return { ... }` block (inside `state.structures = st.map(r=>{...})`):
```js
          return {
            id, structureId: label, desc:r["Description"]||"",
            drainageAreaId: daLabel && daIdMap[daLabel] ? daIdMap[daLabel] : "",
            type: r["Type"]||"manhole",
            forceElev: String(r["Force Fixed"]).toUpperCase()==="TRUE",
            startElev: r["Fixed-Start Elev (ft)"]===""?"":r["Fixed-Start Elev (ft)"],
            crown: r["Crown Elev (ft)"]===""?"":r["Crown Elev (ft)"],
            rim: r["Rim-Grate Elev (ft)"]===""?"":r["Rim-Grate Elev (ft)"],
            splitMethod: r["Split Method"]||"capacity",
            splitCapacity: r["Split Capacity (cfs)"]===""?"":r["Split Capacity (cfs)"],
            splitRatio: r["Split Ratio (0-1)"]===""||r["Split Ratio (0-1)"]==null?0.5:r["Split Ratio (0-1)"],
          };
```

Replace with:
```js
          return {
            id, structureId: label, desc:r["Description"]||"",
            drainageAreaId: daLabel && daIdMap[daLabel] ? daIdMap[daLabel] : "",
            type: r["Type"]||"manhole",
            forceElev: String(r["Force Fixed"]).toUpperCase()==="TRUE",
            startElev: r["Fixed-Start Elev (ft)"]===""?"":r["Fixed-Start Elev (ft)"],
            crown: r["Crown Elev (ft)"]===""?"":r["Crown Elev (ft)"],
            rim: r["Rim-Grate Elev (ft)"]===""?"":r["Rim-Grate Elev (ft)"],
            splitMethod: r["Split Method"]||"capacity",
            splitCapacity: r["Split Capacity (cfs)"]===""?"":r["Split Capacity (cfs)"],
            splitRatio: r["Split Ratio (0-1)"]===""||r["Split Ratio (0-1)"]==null?0.5:r["Split Ratio (0-1)"],
            structureMode: r["Structure Mode"]||"",
            agency: r["Agency"]||"",
            standardStructureId: r["Catalog ID"]||"",
            structureCategory: r["Category"]||"",
            shape: r["Shape"]||"",
            innerDiameter: r["Inner Dia (ft)"]===""||r["Inner Dia (ft)"]==null?"":r["Inner Dia (ft)"],
            innerWidth: r["Inner W (ft)"]===""||r["Inner W (ft)"]==null?"":r["Inner W (ft)"],
            innerLength: r["Inner L (ft)"]===""||r["Inner L (ft)"]==null?"":r["Inner L (ft)"],
          };
```

- [ ] **Step 4: Remove `row.structureType` from Inlet Spacing import (~line 5780)**

Find:
```js
              row.structureType = String(g("Structure Type")||"");
```

Delete this line entirely.

- [ ] **Step 5: Run tests to verify they pass**

```
cd tests && node run-tests.mjs 2>&1 | tail -15
```

Expected: All tests pass including the new round-trip test.

- [ ] **Step 6: Verify export/import round-trip in browser**

1. Open the app, add a junction structure, set it to Standard / PG DER / 48-in MH.
2. Click Export. Open the resulting `.xlsx` in Excel — verify the "Junction Structure" sheet has "Structure Mode", "Agency", "Catalog ID", "Inner Dia (ft)" columns with correct values in row 2.
3. Verify the "Inlet Spacing" sheet has no "Structure Type" column.
4. Import the exported file back into the app — verify the structure still shows Standard / PG DER / 48-in MH with Inner Size 4 ft dia.

- [ ] **Step 7: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Task 7: Excel import — new Structure fields, drop IS structureType"
```

---

## Self-Review

**Spec coverage:**
- Section 1 Data Model — Tasks 1 + 2 (fields added, STRUCTURE_CATALOG constant)
- Section 2 UI — Task 3 (cascade picker, K_ah column)
- Section 3 K_ah + custom shape + inlet spacing — Tasks 1 (kAhFromAngle), 3 (shape/category for custom), 4 (structureType removed)
- Section 4 Data flow — Task 2 (computeStructureCalc), Task 5 (detail sheets), Tasks 6+7 (Excel)
- Section 5 STRUCTURE_CATALOG — Task 1

**Placeholder scan:** None — all steps contain complete code.

**Type consistency:** `kAhFromAngle(structureCategory, deflectionDeg)` used identically in Task 1 (definition), Task 2 (`kbForAngle` wrapper), Task 3 (`kAhDisplay`), Task 5 (detail sheet), and the K_ah display column. `resolveStructureCategory(s)` takes the structure object throughout. Field names (`structureMode`, `agency`, `standardStructureId`, `structureCategory`, `shape`, `innerDiameter`, `innerWidth`, `innerLength`) consistent across all tasks.

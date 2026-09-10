# Rainfall & IDF Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared "Rainfall & IDF" tab with NOAA Atlas 14 county validation link and IDF reference table; move rainfall settings out of inlet spacing into a new `state.rainfall` shared object; update the drainage area tab to show CA + Q₂/Q₁₀/Q₂₅ columns instead of a manual `i` field; add conditional 25-yr check tabs for pipe sizing and HGL.

**Architecture:** Single-file app — all changes go inside `drainage-calculator/storm-drain-design-calculator.html`. A new `state.rainfall` object replaces `inletSpacingSettings.rainfallSource/county/storm/customNoaa`. The drainage area's `calcDrainageRow()` returns `{CA, Qs, designQ}` instead of `{Q, i}`; `capturedQFor()` uses `designQ`; `computeTotalFlow()` gains an optional `stormOverride` arg to power two new read-only 25-yr check tabs. `const TABS` becomes `getTabs()` so tabs 11–12 appear/disappear based on `state.rainfall.pipe25Check`.

**Tech Stack:** Vanilla JS; SheetJS (already inline); Node + jsdom for `tests/run-tests.mjs`.

**Design doc:** `docs/superpowers/specs/2026-09-10-rainfall-idf-tab-design.md`

**Key facts:**
- Only file to edit: `drainage-calculator/storm-drain-design-calculator.html`
- Tests live in: `tests/run-tests.mjs` (existing Node/jsdom harness)
- Run tests: `cd tests && npm test`
- `withFocusPreserved(renderAll)` on every `oninput`; every input needs `data-focus-key`
- `el(tag, attrs, children)` helper is the DOM builder
- `bookSST: true` already set in `exportExcel()` — do not remove
- No localStorage; no CDN; no external files
- Per project rules: no Co-Authored-By trailer in commit messages

---

### Task 1 — State model: add `state.rainfall`, strip inlet spacing settings, update drainage row defaults

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add `defaultRainfallSettings()` and `availableStorms()` just before `defaultInletSpacingSettings()` (≈ line 1147)**

```js
function defaultRainfallSettings() {
  return {
    rainfallSource: "noaa",
    county: "Montgomery",
    customNoaa: { 5:"", 10:"", 15:"", 30:"", 60:"" },
    pipeStorm:   "10yr",
    pipe25Check: false,
    inletStorm:  "2yr",
  };
}

function availableStorms(src) {
  return src === "moco" ? ["2yr","5yr","10yr"] : ["2yr","10yr","25yr"];
}
```

- [ ] **Step 2: Replace `defaultInletSpacingSettings()` body — keep only `street` and `allowableSpread`**

Replace:
```js
function defaultInletSpacingSettings() {
  return {
    street: "",
    rainfallSource: "noaa",     // "noaa"|"mdsha"|"moco"
    county: "Montgomery",       // key in NOAA_ATLAS14 or "Custom"
    storm: "10yr",              // "2yr"|"5yr"|"10yr"|"25yr"
    allowableSpread: 8,
    customNoaa: { 5:"", 10:"", 15:"", 30:"", 60:"" },
  };
}
```
With:
```js
function defaultInletSpacingSettings() {
  return {
    street: "",
    allowableSpread: 8,
  };
}
```

- [ ] **Step 3: Add `rainfall: defaultRainfallSettings()` to `const state = { ... }` (≈ line 1175)**

In `const state = { ... }`, add after `inletSpacingSettings: defaultInletSpacingSettings(),`:
```js
rainfall: defaultRainfallSettings(),
```

- [ ] **Step 4: Update `seedExample()` drainage rows — remove `i:` field, add `iOverride:""`**

In `seedExample()`, change DA-1 push (≈ line 1199) from:
```js
state.drainage.push({id:da1, structureId:"DA-1", desc:"Roof + lawn area to St.1", area:1.4, C:0.55, i:6.8, tc:91.65, cf:1.0, tcMethod:"tr55",
```
To:
```js
state.drainage.push({id:da1, structureId:"DA-1", desc:"Roof + lawn area to St.1", area:1.4, C:0.55, iOverride:"", tc:91.65, cf:1.0, tcMethod:"tr55",
```

Change DA-2 push (≈ line 1206) from:
```js
state.drainage.push({id:da2, structureId:"DA-2", desc:"Parking area to St.2", area:0.9, C:0.85, i:6.8, tc:8, cf:1.0, tcMethod:"direct", tr55:{segments:[]}});
```
To:
```js
state.drainage.push({id:da2, structureId:"DA-2", desc:"Parking area to St.2", area:0.9, C:0.85, iOverride:"", tc:8, cf:1.0, tcMethod:"direct", tr55:{segments:[]}});
```

- [ ] **Step 5: Update `+ Add row` drainage default (≈ line 1958) — remove `i:""`, add `iOverride:""`**

Change:
```js
state.drainage.push({id:nextId(), structureId:"", desc:"", area:"", C:"", i:"", tc:"", cf:1.0, tcMethod:"direct", tr55:{segments:[]}});
```
To:
```js
state.drainage.push({id:nextId(), structureId:"", desc:"", area:"", C:"", iOverride:"", tc:"", cf:1.0, tcMethod:"direct", tr55:{segments:[]}});
```

- [ ] **Step 6: Verify the app still loads without console errors**

Open `drainage-calculator/storm-drain-design-calculator.html` in a browser. Check the console — no errors. The Inlet Spacing and Drainage Area tabs may look broken (we haven't updated the render functions yet) but the app should not crash.

---

### Task 2 — Dynamic `getTabs()` replacing static `const TABS`

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `const TABS = [...]` (≈ line 1870) with `getTabs()` function**

Replace:
```js
const TABS = [
  {id:"overview",   label:"Overview"},
  {id:"drainage",   label:"Drainage Area (Q=CiA)"},
  {id:"structures", label:"Junction Structures"},
  {id:"pipes",      label:"Pipe Sizing"},
  {id:"outlet",     label:"Outlet Structure"},
  {id:"formulas",   label:"Formulas & Examples"},
  {id:"table46",    label:"Table 4-6 Reference"},
  {id:"kb",         label:"Kb Coefficients"},
  {id:"inlet-spacing", label:"Inlet Spacing"},
];
```
With:
```js
function getTabs() {
  const tabs = [
    {id:"overview",       label:"Overview"},
    {id:"rainfall",       label:"Rainfall & IDF"},
    {id:"drainage",       label:"Drainage Area (Q=CiA)"},
    {id:"structures",     label:"Junction Structures"},
    {id:"pipes",          label:"Pipe Sizing"},
    {id:"outlet",         label:"Outlet Structure"},
    {id:"formulas",       label:"Formulas & Examples"},
    {id:"table46",        label:"Table 4-6 Reference"},
    {id:"kb",             label:"Kb Coefficients"},
    {id:"inlet-spacing",  label:"Inlet Spacing"},
  ];
  const r = state.rainfall;
  if (r.pipe25Check && r.pipeStorm !== "25yr") {
    tabs.push({id:"pipe-sizing-25",  label:"Pipe Sizing — 25-yr"});
    tabs.push({id:"structures-25",   label:"Junction Structures — 25-yr"});
  }
  return tabs;
}
```

- [ ] **Step 2: Update `renderNav()` — replace all `TABS` references with `getTabs()`**

In `renderNav()` (≈ line 1885), change:
```js
  TABS.forEach((t,i)=>{
```
to:
```js
  const tabs = getTabs();
  tabs.forEach((t,i)=>{
```
And change:
```js
  document.getElementById("tabLabel").textContent = TABS.find(t=>t.id===state.active).label;
```
to:
```js
  const activeTab = tabs.find(t=>t.id===state.active);
  document.getElementById("tabLabel").textContent = activeTab ? activeTab.label : "";
```

- [ ] **Step 3: Guard `state.active` at top of `renderNav()` — reset if active tab is now hidden**

Add at the very start of `renderNav()`, before `const nav = ...`:
```js
  const tabs = getTabs();
  if (!tabs.find(t => t.id === state.active)) state.active = "pipes";
```
Then remove the duplicate `const tabs = getTabs();` from Step 2 (the forEach line already uses `tabs`).

- [ ] **Step 4: Add view divs for the two new tabs and the Rainfall tab (≈ line 491, after `view-inlet-spacing`)**

After `<div class="view" id="view-inlet-spacing"></div>`, add:
```html
      <div class="view" id="view-rainfall"></div>
      <div class="view" id="view-pipe-sizing-25"></div>
      <div class="view" id="view-structures-25"></div>
```

- [ ] **Step 5: Verify tabs appear correctly**

Open the browser. The tab bar should now show "Rainfall & IDF" as tab 2 between Overview and Drainage Area. The 25-yr tabs should NOT appear yet (pipe25Check is false). Click every tab — no crashes.

---

### Task 3 — `renderRainfall()` skeleton + wire into `renderAll()`

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add `renderRainfall()` stub after `renderKb()` (≈ line 2670)**

```js
function renderRainfall() {
  const c = document.getElementById("view-rainfall");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Rainfall & IDF"));
  c.appendChild(el("p", {class:"view-desc"}, "Stub — see Task 4."));
}
```

- [ ] **Step 2: Add stubs for 25-yr tabs immediately after `renderRainfall()`**

```js
function renderPipeSizing25() {
  const c = document.getElementById("view-pipe-sizing-25");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Pipe Sizing — 25-yr Check"));
  c.appendChild(el("p", {class:"view-desc"}, "Stub — see Task 10."));
}

function renderStructures25() {
  const c = document.getElementById("view-structures-25");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Junction Structures — 25-yr Check"));
  c.appendChild(el("p", {class:"view-desc"}, "Stub — see Task 11."));
}
```

- [ ] **Step 3: Add all three render calls to `renderAll()` (≈ line 2923)**

In `renderAll()`, add after `renderInletSpacing();`:
```js
  renderRainfall();
  renderPipeSizing25();
  renderStructures25();
```

- [ ] **Step 4: Verify**

Browser — click "Rainfall & IDF" tab — shows stub text. No console errors.

---

### Task 4 — Rainfall tab: settings section + design storms + NOAA link

**File:** `drainage-calculator/storm-drain-design-calculator.html`

Replace the `renderRainfall()` stub with the full implementation in two steps (settings first, IDF table in Task 5).

- [ ] **Step 1: Write tests for `availableStorms()`**

In `tests/run-tests.mjs`, add:
```js
test("availableStorms: moco returns 3 storms", () => {
  assert.deepEqual(sdc.availableStorms("moco"), ["2yr","5yr","10yr"]);
});
test("availableStorms: noaa returns 3 storms", () => {
  assert.deepEqual(sdc.availableStorms("noaa"), ["2yr","10yr","25yr"]);
});
test("availableStorms: mdsha returns 3 storms", () => {
  assert.deepEqual(sdc.availableStorms("mdsha"), ["2yr","10yr","25yr"]);
});
```

Expose `availableStorms` in `window.__sdc` (≈ line 4452) — add `availableStorms,` to the object. Run tests:
```powershell
cd tests; npm test
```
Expected: new tests pass.

- [ ] **Step 2: Replace `renderRainfall()` with full settings + storms + NOAA link**

```js
function renderRainfall() {
  const c = document.getElementById("view-rainfall");
  if (!c) return;
  c.innerHTML = "";
  const r = state.rainfall;

  c.appendChild(el("h1", {}, "Rainfall & IDF"));
  c.appendChild(el("p", {class:"view-desc"},
    "Shared rainfall settings for the entire project. Pipe & HGL tabs use the Pipe design storm; " +
    "Inlet Spacing uses the Inlet design storm. The IDF table shows intensities at standard Tₜ values."));

  // ---- Settings section ----
  const settingsSec = el("div", {class:"section"});
  settingsSec.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Project Rainfall Settings")]));
  const sRow = el("div", {style:"display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;padding:12px 0;"});

  // Source
  const srcField = el("div", {class:"field"});
  srcField.appendChild(el("label", {}, "Rainfall Source"));
  const srcSel = el("select", {class:"cell-input", style:"width:200px;",
    "data-focus-key":"rf:source",
    onchange: (e) => {
      r.rainfallSource = e.target.value;
      const valid = availableStorms(r.rainfallSource);
      if (!valid.includes(r.pipeStorm))  r.pipeStorm  = "10yr";
      if (!valid.includes(r.inletStorm)) r.inletStorm = "2yr";
      withFocusPreserved(renderAll);
    }});
  [["noaa","NOAA Atlas 14 (per county)"],["mdsha","MDSHA Agency Table"],["moco","MoCo Agency Table"]].forEach(([v,l]) => {
    const o = el("option", {value:v}, l);
    if (r.rainfallSource === v) o.selected = true;
    srcSel.appendChild(o);
  });
  srcField.appendChild(srcSel);
  sRow.appendChild(srcField);

  // County (NOAA only)
  if (r.rainfallSource === "noaa") {
    const ctyField = el("div", {class:"field"});
    ctyField.appendChild(el("label", {}, "County"));
    const ctySel = el("select", {class:"cell-input", style:"width:180px;",
      "data-focus-key":"rf:county",
      onchange: (e) => { r.county = e.target.value; withFocusPreserved(renderAll); }});
    NOAA_COUNTY_LIST.forEach(cty => {
      const o = el("option", {value:cty}, cty);
      if (r.county === cty) o.selected = true;
      ctySel.appendChild(o);
    });
    const oCustom = el("option", {value:"Custom"}, "Custom (enter below)");
    if (r.county === "Custom") oCustom.selected = true;
    ctySel.appendChild(oCustom);
    ctyField.appendChild(ctySel);
    sRow.appendChild(ctyField);
  }

  settingsSec.appendChild(sRow);

  // Custom NOAA intensity inputs
  if (r.rainfallSource === "noaa" && r.county === "Custom") {
    const customRow = el("div", {style:"display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;padding:8px 0;"});
    customRow.appendChild(el("span", {style:"font-size:0.85em;opacity:0.7;align-self:center;"}, "Custom intensities (in/hr):"));
    [5,10,15,30,60].forEach(d => {
      const f = el("div", {class:"field"});
      f.appendChild(el("label", {}, d+"-min"));
      f.appendChild(el("input", {class:"cell-input", type:"text", inputmode:"decimal", style:"width:70px;",
        "data-focus-key":"rf:custom:"+d,
        value: (r.customNoaa && r.customNoaa[d] !== undefined) ? r.customNoaa[d] : "",
        oninput: (e) => {
          r.customNoaa = Object.assign({}, r.customNoaa);
          r.customNoaa[d] = e.target.value;
          withFocusPreserved(renderAll);
        }}));
      customRow.appendChild(f);
    });
    settingsSec.appendChild(customRow);
  }

  // NOAA validation link + county point note
  if (r.rainfallSource === "noaa" && r.county !== "Custom" && NOAA_ATLAS14[r.county]) {
    const entry = NOAA_ATLAS14[r.county];
    const statename = r.county === "DC" ? "dc" : "maryland";
    const href = "https://hdsc.nws.noaa.gov/pfds/pfds_point_cu.html?lat=" + entry.lat +
                 "&lon=" + entry.lon + "&data=intensity&units=us&series=pds";
    const noteDiv = el("div", {style:"padding:6px 0 4px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;"});
    noteDiv.appendChild(el("a", {href, target:"_blank", style:"font-size:0.9em;"}, "Validate on NOAA Atlas 14 ↗"));
    noteDiv.appendChild(el("span", {style:"font-size:0.8em;opacity:0.6;"},
      "Represents lat " + entry.lat + ", lon " + entry.lon +
      " (county centroid, pulled 2026-09-09). Values vary within the county; use Custom for project-specific accuracy."));
    settingsSec.appendChild(noteDiv);
  }

  c.appendChild(settingsSec);

  // ---- Design Storms section ----
  const stormSec = el("div", {class:"section"});
  stormSec.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Design Storms")]));
  const stRow = el("div", {style:"display:flex;align-items:flex-end;gap:20px;flex-wrap:wrap;padding:12px 0;"});

  const storms = availableStorms(r.rainfallSource);
  const stormLabels = {"2yr":"2-year","5yr":"5-year","10yr":"10-year","25yr":"25-year"};

  // Pipe & HGL storm
  const pipeStormField = el("div", {class:"field"});
  pipeStormField.appendChild(el("label", {}, "Pipe & HGL Design Storm"));
  const pipeSel = el("select", {class:"cell-input", style:"width:130px;",
    "data-focus-key":"rf:pipeStorm",
    onchange: (e) => { r.pipeStorm = e.target.value; withFocusPreserved(renderAll); }});
  storms.forEach(s => {
    const o = el("option", {value:s}, stormLabels[s]||s);
    if (r.pipeStorm === s) o.selected = true;
    pipeSel.appendChild(o);
  });
  pipeStormField.appendChild(pipeSel);
  stRow.appendChild(pipeStormField);

  // Inlet storm
  const inletStormField = el("div", {class:"field"});
  inletStormField.appendChild(el("label", {}, "Inlet Design Storm"));
  const inletSel = el("select", {class:"cell-input", style:"width:130px;",
    "data-focus-key":"rf:inletStorm",
    onchange: (e) => { r.inletStorm = e.target.value; withFocusPreserved(renderAll); }});
  storms.forEach(s => {
    const o = el("option", {value:s}, stormLabels[s]||s);
    if (r.inletStorm === s) o.selected = true;
    inletSel.appendChild(o);
  });
  inletStormField.appendChild(inletSel);
  stRow.appendChild(inletStormField);

  // 25-yr check checkbox (hidden when pipeStorm is already 25yr)
  if (r.pipeStorm !== "25yr") {
    const chkField = el("div", {class:"field"});
    chkField.appendChild(el("label", {}, " "));
    const chkLabel = el("label", {style:"display:flex;align-items:center;gap:8px;cursor:pointer;"});
    const chk = el("input", {type:"checkbox",
      "data-focus-key":"rf:pipe25Check",
      onchange: (e) => { r.pipe25Check = e.target.checked; withFocusPreserved(renderAll); }});
    chk.checked = r.pipe25Check;
    chkLabel.appendChild(chk);
    chkLabel.appendChild(document.createTextNode("Also compute 25-yr pipe & HGL check"));
    chkField.appendChild(chkLabel);
    stRow.appendChild(chkField);
  }

  stormSec.appendChild(stRow);
  c.appendChild(stormSec);

  // IDF table placeholder — rendered in renderRainfallIdfTable() called below
  renderRainfallIdfTable(c);
}
```

- [ ] **Step 3: Verify browser**

Open browser, click "Rainfall & IDF". Source dropdown, county dropdown (when NOAA), NOAA validation link, design storm dropdowns, and 25-yr checkbox should all render. Changing source coerces storms. Checking the 25-yr box causes the two extra tabs to appear. No console errors.

---

### Task 5 — Rainfall tab: IDF reference table

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add `renderRainfallIdfTable(container)` function just after `renderRainfall()`**

```js
function renderRainfallIdfTable(c) {
  const r = state.rainfall;
  const storms = availableStorms(r.rainfallSource);
  const pipeAccent = "#4a9eff";
  const inletAccent = "#f0a500";

  const idfSec = el("div", {class:"section"});
  const srcLabels = {noaa:"NOAA Atlas 14", mdsha:"MDSHA Agency Table", moco:"MoCo Agency Table"};
  const subtitle = r.rainfallSource === "noaa" && r.county !== "Custom"
    ? srcLabels.noaa + " — " + r.county
    : srcLabels[r.rainfallSource] || r.rainfallSource;
  idfSec.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Intensity Reference — " + subtitle)]));

  const tableWrap = el("div", {class:"table-wrap"});
  const tbl = el("table", {class:"data"});

  // Header row
  const headRow = el("tr", {});
  headRow.appendChild(el("th", {}, "Tc (min)"));
  storms.forEach(s => {
    const isPipe  = s === r.pipeStorm;
    const isInlet = s === r.inletStorm;
    const accent  = isPipe ? pipeAccent : (isInlet ? inletAccent : "");
    const lbl = {" 2yr":"2-yr","10yr":"10-yr","25yr":"25-yr","5yr":"5-yr"}[s] || s;
    const tag = isPipe && isInlet ? " (Pipe & Inlet)" : isPipe ? " (Pipe)" : isInlet ? " (Inlet)" : "";
    headRow.appendChild(el("th", {style: accent ? "background:"+accent+"22;color:"+accent+";" : ""}, lbl + tag + "\ni (in/hr)"));
  });
  tbl.appendChild(el("thead", {}, headRow));

  const tbody = el("tbody", {});
  const stdTcs = [5, 7, 10, 15, 20, 30, 60];
  stdTcs.forEach(tc => {
    const tr = el("tr", {});
    tr.appendChild(el("td", {}, String(tc)));
    storms.forEach(s => {
      const isPipe  = s === r.pipeStorm;
      const isInlet = s === r.inletStorm;
      const accent  = isPipe ? pipeAccent : (isInlet ? inletAccent : "");
      const i = lookupIntensity(tc, r.rainfallSource, s, r.county, r.customNoaa || {});
      tr.appendChild(el("td", {
        class:"out computed-cell",
        style: accent ? "background:"+accent+"11;font-weight:"+(isPipe||isInlet?"600":"400")+";" : ""
      }, (i > 0 ? i.toFixed(2) : "—")));
    });
    tbody.appendChild(tr);
  });

  // Custom Tc row
  const customTc = r._customIdfTc || "";
  const customTr = el("tr", {});
  const tcInput = el("input", {
    class:"cell-input", type:"text", inputmode:"decimal", style:"width:70px;",
    "data-focus-key":"rf:customTc",
    value: customTc,
    placeholder:"custom",
    oninput: (e) => { r._customIdfTc = e.target.value; withFocusPreserved(renderAll); }
  });
  const tcTd = el("td", {});
  tcTd.appendChild(tcInput);
  customTr.appendChild(tcTd);
  const parsedTc = parseFloat(customTc);
  storms.forEach(s => {
    const isPipe  = s === r.pipeStorm;
    const isInlet = s === r.inletStorm;
    const accent  = isPipe ? pipeAccent : (isInlet ? inletAccent : "");
    const i = (isFinite(parsedTc) && parsedTc > 0)
      ? lookupIntensity(parsedTc, r.rainfallSource, s, r.county, r.customNoaa || {})
      : null;
    customTr.appendChild(el("td", {
      class:"out computed-cell",
      style: accent ? "background:"+accent+"11;" : ""
    }, i !== null ? i.toFixed(2) : "—"));
  });
  tbody.appendChild(customTr);

  tbl.appendChild(tbody);
  tableWrap.appendChild(tbl);
  idfSec.appendChild(tableWrap);
  c.appendChild(idfSec);
}
```

- [ ] **Step 2: Verify IDF table in browser**

Open Rainfall & IDF tab. Table should show rows for Tc = 5, 7, 10, 15, 20, 30, 60 min with intensity values. Pipe-storm column shows blue tint; inlet-storm column shows amber tint. Custom Tc input at bottom — type "12" and values interpolate live. Switch county — values update. Switch to MDSHA source — columns change to 2yr/10yr/25yr, intensities match MDSHA table (at 5min: 5.016/6.684/7.572 in/hr respectively). No console errors.

- [ ] **Step 3: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Add Rainfall & IDF tab: shared settings, design storm selectors, NOAA validation link, IDF table"
```

---

### Task 6 — `calcDrainageRow` revision + `capturedQFor` update + tests

**File:** `drainage-calculator/storm-drain-design-calculator.html`, `tests/run-tests.mjs`

- [ ] **Step 1: Write failing tests for new `calcDrainageRow` return shape**

In `tests/run-tests.mjs`, add:
```js
// calcDrainageRow new shape tests
test("calcDrainageRow: returns CA, Qs, designQ", () => {
  // Set up state with known rainfall settings
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.pipeStorm = "10yr";
  const row = { area:"1.0", C:"0.8", iOverride:"", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  // CA = 0.8
  assert.ok(Math.abs(result.CA - 0.8) < 0.001, "CA should be 0.8");
  // Qs should have keys for each available storm
  assert.ok(result.Qs["10yr"] !== undefined, "Qs should have 10yr key");
  assert.ok(result.Qs["2yr"]  !== undefined, "Qs should have 2yr key");
  // designQ = Qs[pipeStorm]
  assert.ok(Math.abs(result.designQ - result.Qs["10yr"]) < 0.001, "designQ should match pipeStorm Q");
  // MDSHA 10yr at Tc=10 is 5.340 in/hr → Q = 1*0.8*1.0*5.340 = 4.272
  assert.ok(Math.abs(result.Qs["10yr"] - 4.272) < 0.01, "Q10 ≈ 4.272 cfs");
});

test("calcDrainageRow: iOverride overrides all storm Qs", () => {
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.pipeStorm = "10yr";
  const row = { area:"1.0", C:"0.8", iOverride:"5.0", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  // With iOverride=5.0, all Qs should use 5.0 in/hr
  ["2yr","10yr","25yr"].forEach(s => {
    assert.ok(Math.abs(result.Qs[s] - 0.8*5.0) < 0.001, s + " Q should use iOverride");
  });
});

test("calcDrainageRow: zero CA when area blank", () => {
  const row = { area:"", C:"0.8", iOverride:"", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  assert.equal(result.CA, 0, "CA should be 0 when area is blank");
  assert.equal(result.designQ, 0, "designQ should be 0");
});
```

Run: `cd tests && npm test`
Expected: new tests FAIL (function still returns old shape).

- [ ] **Step 2: Replace `calcDrainageRow` (≈ line 1315)**

Replace:
```js
function calcDrainageRow(row){
  const A=parseFloat(row.area)||0, C=parseFloat(row.C)||0, i=parseFloat(row.i)||0, cf=parseFloat(row.cf)||1;
  return { Q: cf*C*i*A, A, C, i, cf };
}
```
With:
```js
function calcDrainageRow(row) {
  const A  = parseFloat(row.area) || 0;
  const C  = parseFloat(row.C)    || 0;
  const cf = parseFloat(row.cf)   || 1;
  const tc = parseFloat(row.tc);
  const CA = C * A;
  const r  = state.rainfall;

  const iOverridden = row.iOverride !== "" && row.iOverride != null && isFinite(Number(row.iOverride));

  function intensityFor(storm) {
    if (iOverridden) return Number(row.iOverride);
    if (!isFinite(tc) || tc <= 0) return 0;
    return lookupIntensity(tc, r.rainfallSource, storm, r.county, r.customNoaa || {});
  }

  const storms = availableStorms(r.rainfallSource);
  const Qs = {};
  storms.forEach(s => { Qs[s] = cf * CA * intensityFor(s); });

  return { CA, cf, A, C, Qs, storms, designQ: Qs[r.pipeStorm] || 0, iOverridden };
}
```

- [ ] **Step 3: Update `capturedQFor` (≈ line 1442) — use `designQ` instead of `.Q`**

Change:
```js
  return da ? calcDrainageRow(da).Q : 0;
```
To:
```js
  return da ? calcDrainageRow(da).designQ : 0;
```

- [ ] **Step 4: Run tests**

```powershell
cd tests; npm test
```
Expected: all tests pass including new ones.

- [ ] **Step 5: Verify app — structures and pipes still compute correctly**

Open browser. Seed example should show non-zero Q in Junction Structures (Total Flow) and Pipe Sizing (Design Q). If Q is 0, check the browser console for errors in calcDrainageRow.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Revise calcDrainageRow: CA + multi-storm Qs, pipeStorm-driven designQ"
```

---

### Task 7 — Drainage Area table UI: new columns

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Update `renderDrainage()` table header (≈ line 1963)**

Replace:
```js
    el("th",{},"ID"), el("th",{},"Description"), el("th",{},"Area A (ac)"),
    el("th",{},"C"), el("th",{},"i (in/hr)"), el("th",{},"Tc (min)"), el("th",{},"Cf"),
    el("th",{class:"computed"},"Q (cfs)"), el("th",{},""), el("th",{},"")
```
With (storms are dynamic — build headers from `availableStorms`):
```js
    el("th",{},"ID"), el("th",{},"Description"), el("th",{},"Area A (ac)"),
    el("th",{},"C"),
    el("th",{class:"computed"},"CA"),
    el("th",{},"i override\n(in/hr)"),
    el("th",{},"Tc (min)"), el("th",{},"Cf"),
    ...availableStorms(state.rainfall.rainfallSource).map(s => {
      const isPipe  = s === state.rainfall.pipeStorm;
      const isInlet = s === state.rainfall.inletStorm;
      const accent  = isPipe ? "#4a9eff" : (isInlet ? "#f0a500" : "");
      const lbl = {"2yr":"Q₂","10yr":"Q₁₀","25yr":"Q₂₅","5yr":"Q₅"}[s] || ("Q "+s);
      return el("th", {class:"computed", style: accent?"color:"+accent+";":""}, lbl+"\n(cfs)");
    }),
    el("th",{},""), el("th",{},"")
```

- [ ] **Step 2: Update the `tbody` row build inside `renderDrainage()` (≈ line 1969)**

Replace the `tbody.appendChild(el("tr",{},[` block with:
```js
    const calc = calcDrainageRow(row);
    const iOverrideCell = el("input", {
      class:"cell-input" + (calc.iOverridden ? " i-override" : ""),
      type:"text", inputmode:"decimal", style:"width:65px;",
      "data-focus-key":"drainage:"+row.id+":iOverride",
      value: row.iOverride !== undefined ? row.iOverride : "",
      placeholder: calc.iOverridden ? "" : "auto",
      oninput: (e) => { row.iOverride = e.target.value; withFocusPreserved(renderAll); }
    });
    tbody.appendChild(el("tr", {}, [
      el("td",{}, txt(row,"structureId",90)),
      el("td",{}, txt(row,"desc",160)),
      el("td",{}, num(row,"area",70)),
      el("td",{}, num(row,"C",60)),
      el("td",{class:"out computed-cell"}, fmt(calc.CA, 3)),
      el("td",{class: calc.iOverridden ? "i-override" : ""}, iOverrideCell),
      el("td",{}, tcCell(row)),
      el("td",{}, num(row,"cf",55)),
      ...calc.storms.map(s => {
        const isPipe  = s === state.rainfall.pipeStorm;
        const isInlet = s === state.rainfall.inletStorm;
        const accent  = isPipe ? "#4a9eff" : (isInlet ? "#f0a500" : "");
        return el("td", {
          class:"out computed-cell",
          style: accent ? "font-weight:600;border-bottom:2px solid "+accent+";" : ""
        }, fmt(calc.Qs[s], 2));
      }),
      el("td",{}, detailBtn(()=>openDetailModal(buildDrainageSheet(row)))),
      el("td",{}, delBtn(()=>{ state.drainage=state.drainage.filter(r=>r!==row); renderAll(); }))
    ]));
```

- [ ] **Step 3: Add `.i-override` CSS rule to the `<style>` block**

Find the existing `.i-override` rule (added for inlet spacing) — if absent, add inside `<style>`:
```css
.i-override input, .i-override { border-color: #f90 !important; }
```

- [ ] **Step 4: Fix the TR-55 inline update (≈ line 2013)**

The old code `tr.children[7].textContent = ...` targeted Q by index. With new columns the index is wrong. Replace the entire inline update block:

Find and replace:
```js
  const idx = state.drainage.indexOf(row);
  const tr = document.querySelectorAll("#view-drainage tbody tr")[idx];
  if(tr){ tr.children[7].textContent = fmt(calcDrainageRow(row).Q,2); }
```
With a full re-render call:
```js
  renderDrainage();
```

- [ ] **Step 5: Verify in browser**

Drainage Area tab should show: ID, Description, Area, C, CA, i override, Tc, Cf, Q₂, Q₁₀, Q₂₅ (or Q₂/Q₅/Q₁₀ for MoCo). Q columns for the pipe design storm are highlighted in blue. Typing into i override gives an orange border. Changing the pipe storm in the Rainfall tab causes the Q column highlight to move. TR-55 edit still updates the row correctly.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "Update drainage area table: CA column, multi-storm Q columns, i override field"
```

---

### Task 8 — Drainage Area detail sheet update

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `buildDrainageSheet(row)` (≈ line 2960)**

Replace the entire function:
```js
function buildDrainageSheet(row) {
  const calc = calcDrainageRow(row);
  const r    = state.rainfall;
  const srcLabel = r.rainfallSource === "noaa"
    ? "NOAA Atlas 14 — " + r.county
    : r.rainfallSource === "moco" ? "MoCo Agency Table" : "MDSHA Agency Table";

  const iRows = calc.iOverridden
    ? [["Intensity source", "Manual override"],
       ["i used (all storms)", fmt(Number(row.iOverride), 3) + " in/hr ⚠ verify against source"]]
    : [["Intensity source", srcLabel],
       ["Time of concentration, Tc", (row.tc !== "" && row.tc != null ? fmt(parseFloat(row.tc), 1) + " min" : "—")]];

  const qRows = calc.storms.map(s => {
    const label = {"2yr":"Q₂","10yr":"Q₁₀","25yr":"Q₂₅","5yr":"Q₅"}[s] || ("Q "+s);
    const tag = s === r.pipeStorm ? " ← pipe design storm" : s === r.inletStorm ? " ← inlet design storm" : "";
    return [label, fmt(calc.Qs[s], 3) + " cfs" + tag];
  });

  const body = [
    csSection("Inputs", csTable([
      ["Tributary area, A", fmt(calc.A, 2) + " ac"],
      ["Runoff coefficient, C", fmt(calc.C, 2)],
      ["CA = C × A", fmt(calc.CA, 3)],
      ["Frequency correction, Cf", fmt(calc.cf, 2)],
      ...iRows,
    ])),
    csSection("Rational Method — Q = Cf × CA × i", el("div", {}, [
      csTable(qRows),
    ])),
  ];
  return sheetWrapper("drainage", "Drainage Area — " + (row.structureId || row.id),
    row.desc || "Rational Method (Q = Cf·C·i·A)", body);
}
```

- [ ] **Step 2: Verify detail sheet**

Open browser, click ⤢ Detail on a drainage area row. The calc sheet should show CA, all Q values labeled by storm, and the pipe/inlet design storm tagged. iOverride note appears when set.

---

### Task 9 — Inlet Spacing rewiring

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Write failing test for rewired inlet intensity**

In `tests/run-tests.mjs`, add:
```js
test("inlet spacing uses state.rainfall.inletStorm", () => {
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.inletStorm = "2yr";
  const row = {
    id:"r-inlet-test", label:"I-T", S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"10",
    area:"0.2", C:"1", tc:"5", iOverride:"", allowableSpread:"", bypassTo:""
  };
  const is = sdc.state.inletSpacingSettings;
  const r = sdc.computeInletRow(row, is, 0, 0);
  // MDSHA 2yr at Tc=5 = 5.016 in/hr → Q = 0.2 * 5.016 = 1.003
  assert.ok(Math.abs(r.Q - 1.003) < 0.05, "inlet Q uses inletStorm=2yr: " + r.Q);
});
```

Run: `cd tests && npm test`  
Expected: test FAILS (inlet spacing still reads old settings fields).

- [ ] **Step 2: Strip rainfall fields from global controls in `renderInletSpacing()` (≈ line 2700)**

In `renderInletSpacing()`, remove the following blocks entirely:
- The Rainfall Source field + srcSel select + its `onchange` handler
- The County field + countySel select (NOAA-only block)
- The Custom NOAA inputs block (`if(s.rainfallSource==="noaa" && s.county==="Custom")`)
- The county note paragraph (`else if(s.rainfallSource==="noaa" && NOAA_ATLAS14[s.county])`)
- The Storm field + stormSel

Keep in the global controls row: Street input and Default Allowable Spread input only.

- [ ] **Step 3: Update `computeInletRow` call sites in `renderInletSpacing()` to pass rainfall context**

Find where `computeInletChain` is called inside `renderInletSpacing()`. It currently passes `s` (which was `state.inletSpacingSettings`). Build a merged context object:

```js
const inletCtx = {
  street:          s.street,
  allowableSpread: s.allowableSpread,
  rainfallSource:  state.rainfall.rainfallSource,
  county:          state.rainfall.county,
  storm:           state.rainfall.inletStorm,
  customNoaa:      state.rainfall.customNoaa || {},
};
```

Replace every `computeInletChain(rows, s)` call with `computeInletChain(rows, inletCtx)`.

- [ ] **Step 4: Update `buildInletSpacingSheet` caller to pass the same context**

Where `buildInletSpacingSheet(row, comp, s)` is called in the ⤢ detail button, change `s` to `inletCtx` (same object built above — make sure it's in scope, or rebuild it at that call site).

- [ ] **Step 5: Update `buildInletSpacingSheet` to show `inletStorm` and rainfall source**

Inside `buildInletSpacingSheet(row, comp, settings)`, the section "Project Settings" shows `s.rainfallSource` and `s.county`. Since `settings` is now `inletCtx` which has those fields, this section should work unchanged. Verify it shows the correct source/county/storm.

- [ ] **Step 6: Run tests**

```powershell
cd tests; npm test
```
Expected: all tests pass including the new inlet storm test.

- [ ] **Step 7: Verify in browser**

Inlet Spacing tab global controls show only Street and Allowable Spread. Change county in Rainfall tab — inlet spacing i values update. Change inletStorm — pickup percentages change.

- [ ] **Step 8: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Rewire inlet spacing to shared state.rainfall; strip duplicate rainfall settings from inlet tab"
```

---

### Task 10 — `computeTotalFlow` storm override (foundation for 25-yr tabs)

**File:** `drainage-calculator/storm-drain-design-calculator.html`, `tests/run-tests.mjs`

- [ ] **Step 1: Write failing test**

```js
test("computeTotalFlow stormOverride: Q25 > Q10 for same structure", () => {
  // Requires seed example to be loaded.  If state.structures is empty, skip.
  const structs = sdc.state.structures;
  if (!structs.length) { return; } // skip if no seed data
  const firstInlet = structs.find(s => s.type === "inlet");
  if (!firstInlet) { return; }
  sdc.state.rainfall.rainfallSource = "noaa";
  sdc.state.rainfall.pipeStorm = "10yr";
  const q10 = sdc.computeTotalFlow(firstInlet.id, null, "10yr").Q;
  const q25 = sdc.computeTotalFlow(firstInlet.id, null, "25yr").Q;
  assert.ok(q25 >= q10, "Q25 should be >= Q10 (higher rainfall = higher flow)");
});
```

Run: `cd tests && npm test`  
Expected: test FAILS — `computeTotalFlow` does not accept a third argument yet.

- [ ] **Step 2: Add `stormOverride` parameter to `capturedQFor` (≈ line 1439)**

Replace:
```js
function capturedQFor(structure){
  if(!structure || !structure.drainageAreaId) return 0;
  const da = findDrainage(structure.drainageAreaId);
  return da ? calcDrainageRow(da).designQ : 0;
}
```
With:
```js
function capturedQFor(structure, stormOverride) {
  if (!structure || !structure.drainageAreaId) return 0;
  const da = findDrainage(structure.drainageAreaId);
  if (!da) return 0;
  const calc = calcDrainageRow(da);
  return stormOverride ? (calc.Qs[stormOverride] || 0) : calc.designQ;
}
```

- [ ] **Step 3: Add `stormOverride` parameter to `computeTotalFlow` and `pipeDesignQ` (≈ line 1466)**

Replace `function computeTotalFlow(structureId, seen){` and `function pipeDesignQ(pipeRow, seen){` with:

```js
function computeTotalFlow(structureId, seen, stormOverride) {
  seen = seen || new Set();
  const st = findStructure(structureId);
  if (!st) return {Q:0, captured:0, inflow:[], error:null};
  if (seen.has(structureId)) return {Q:0, captured:0, inflow:[], error:"circular"};
  const nextSeen = new Set(seen);
  nextSeen.add(structureId);
  const captured = capturedQFor(st, stormOverride);
  const inflowPipes = getIncomingPipes(structureId);
  const inflow = inflowPipes.map(p => {
    const q = pipeDesignQ(p, nextSeen, stormOverride);
    return { pipe:p, fromId:p.fromStructureId, Q:q, error:null };
  });
  const sum = inflow.reduce((a,b) => a + (isFinite(b.Q) ? b.Q : 0), 0);
  return { Q: captured + sum, captured, inflow, error:null };
}

function pipeDesignQ(pipeRow, seen, stormOverride) {
  if (!pipeRow || !pipeRow.fromStructureId) return 0;
  const fromSt = findStructure(pipeRow.fromStructureId);
  const totalFlow = computeTotalFlow(pipeRow.fromStructureId, seen, stormOverride).Q;
  if (fromSt && fromSt.type === "splitter") {
    const split = computeSplitterSplit(fromSt, totalFlow);
    if (pipeRow.splitRole === "primary")   return split.primaryQ;
    if (pipeRow.splitRole === "secondary") return split.secondaryQ;
    return 0;
  }
  return totalFlow;
}
```

- [ ] **Step 4: Run tests**

```powershell
cd tests; npm test
```
Expected: all tests pass.

- [ ] **Step 5: Verify primary tabs still work**

Browser — Junction Structures and Pipe Sizing tabs show same values as before. No regression.

---

### Task 11 — 25-yr Pipe Sizing tab

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `renderPipeSizing25()` stub with full read-only implementation**

```js
function renderPipeSizing25() {
  const c = document.getElementById("view-pipe-sizing-25");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Pipe Sizing — 25-yr Check"));
  c.appendChild(el("p", {class:"view-desc"},
    "25-yr check — read only. Pipe geometry is unchanged from the primary Pipe Sizing tab. " +
    "Design Q uses Q₂₅ from each linked drainage area."));

  const section = el("div", {class:"section"});
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Pipe capacity check — 25-yr storm")]));
  const tableWrap = el("div", {class:"table-wrap"});
  const table = el("table", {class:"data"});
  table.appendChild(el("thead", {}, el("tr", {}, [
    el("th",{},"From"), el("th",{},"To"), el("th",{},"Shape / Size"),
    el("th",{class:"computed"},"Design Q₂₅\n(cfs)"),
    el("th",{class:"computed"},"Q₟ᵤᴸᴸ (cfs)"),
    el("th",{class:"computed"},"V (fps)"),
    el("th",{class:"computed"},"Pass?"),
  ])));
  const tbody = el("tbody");
  state.pipes.forEach(row => {
    const geo   = pipeGeometry(row);
    const q25   = pipeDesignQ(row, null, "25yr");
    const n     = parseFloat(row.n);
    const S     = parseFloat(row.slope);
    let qfull = null, v = null, pass = null;
    if (geo && isFinite(n) && isFinite(S) && S > 0) {
      const mf = manningFullFlow(n, geo.areaSf, geo.equivDiamIn, S);
      qfull = mf.Qfull; v = mf.V;
      pass = isFinite(q25) && isFinite(qfull) ? q25 <= qfull : null;
    }
    const fromSt = findStructure(row.fromStructureId);
    const toSt   = findStructure(row.toStructureId);
    const sizeLabel = row.shape === "elliptical"
      ? (row.size || "?") + " ellip."
      : (row.size || "?") + '" circ.';
    tbody.appendChild(el("tr", {}, [
      el("td",{}, fromSt ? (fromSt.structureId||fromSt.id) : (row.fromStructureId||"?")),
      el("td",{}, toSt   ? (toSt.structureId||toSt.id)     : (row.toStructureId||"?")),
      el("td",{}, sizeLabel),
      el("td",{class:"out computed-cell"}, isFinite(q25)   ? fmt(q25,2)   : "—"),
      el("td",{class:"out computed-cell"}, isFinite(qfull) ? fmt(qfull,2) : "—"),
      el("td",{class:"out computed-cell"}, isFinite(v)     ? fmt(v,2)     : "—"),
      el("td",{class:"out computed-cell", style: pass===false?"color:#e05;font-weight:700;":""},
        pass===null ? "—" : pass ? "✓" : "✗ OVER"),
    ]));
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  section.appendChild(tableWrap);
  if (state.pipes.length === 0) section.appendChild(el("p",{class:"hint"},"No pipes defined."));
  c.appendChild(section);
}
```

- [ ] **Step 2: Verify in browser**

Enable the 25-yr check checkbox on the Rainfall tab. Click "Pipe Sizing — 25-yr" tab. Table shows pipes with Q₂₅ design flows — Q₂₅ values should be larger than Q₁₀ values for the same pipes. "Pass?" column shows ✓ or ✗ OVER. No console errors.

---

### Task 12 — 25-yr Junction Structures tab

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `renderStructures25()` stub with full read-only implementation**

```js
function renderStructures25() {
  const c = document.getElementById("view-structures-25");
  if (!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1", {}, "Junction Structures — 25-yr Check"));
  c.appendChild(el("p", {class:"view-desc"},
    "25-yr check — read only. Structure geometry and elevations are unchanged from the primary " +
    "Junction Structures tab. HGL is propagated with Q₂₅ flows."));

  const section = el("div", {class:"section"});
  section.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "HGL check — 25-yr storm")]));
  const tableWrap = el("div", {class:"table-wrap"});
  const table = el("table", {class:"data"});
  table.appendChild(el("thead", {}, el("tr", {}, [
    el("th",{},"Structure ID"), el("th",{},"Type"), el("th",{},"Crown (ft)"), el("th",{},"Rim (ft)"),
    el("th",{class:"computed"},"Total Flow Q₂₅\n(cfs)"),
    el("th",{class:"computed"},"Upstream HGL\n(ft)"),
    el("th",{class:"computed"},"Crown\nCheck"),
    el("th",{class:"computed"},"Rim\nCheck"),
  ])));
  const tbody = el("tbody");
  state.structures.forEach(row => {
    const tf   = computeTotalFlow(row.id, null, "25yr");
    const calc = computeStructureCalc(row, "25yr");
    const hgl  = calc ? calc.elevation : null;
    const crown = parseFloat(row.crown);
    const rim   = parseFloat(row.rim);
    const crownCheck = (isFinite(hgl) && isFinite(crown)) ? hgl <= crown + 1.0 : null;
    const rimCheck   = (isFinite(hgl) && isFinite(rim))   ? hgl <= rim  - 1.0 : null;
    const crownStyle = crownCheck === false ? "color:#e05;font-weight:700;" : "";
    const rimStyle   = rimCheck   === false ? "color:#e05;font-weight:700;" : "";
    tbody.appendChild(el("tr", {}, [
      el("td",{}, row.structureId||row.id),
      el("td",{}, row.type||""),
      el("td",{}, isFinite(crown) ? fmt(crown,2) : "—"),
      el("td",{}, isFinite(rim)   ? fmt(rim,2)   : "—"),
      el("td",{class:"out computed-cell"}, isFinite(tf.Q) ? fmt(tf.Q,2) : "—"),
      el("td",{class:"out computed-cell"}, isFinite(hgl)  ? fmt(hgl,2)  : "—"),
      el("td",{class:"out computed-cell", style:crownStyle},
        crownCheck === null ? "—" : crownCheck ? "✓" : "✗ > crown+1"),
      el("td",{class:"out computed-cell", style:rimStyle},
        rimCheck === null ? "—" : rimCheck ? "✓" : "✗ FLOOD"),
    ]));
  });
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  section.appendChild(tableWrap);
  if (state.structures.length === 0) section.appendChild(el("p",{class:"hint"},"No structures defined."));
  c.appendChild(section);
}
```

- [ ] **Step 2: Update `computeStructureCalc` to accept `stormOverride` (≈ where it's defined)**

Find `function computeStructureCalc(row)`. It calls `computeTotalFlow(row.id)` internally. Add a `stormOverride` parameter and thread it through:

```js
function computeStructureCalc(row, stormOverride) {
```
And inside, change:
```js
  const totalFlowInfo = computeTotalFlow(row.id, null);
```
to:
```js
  const totalFlowInfo = computeTotalFlow(row.id, null, stormOverride);
```
(Find the exact call site — search for `computeTotalFlow(row.id` inside `computeStructureCalc`.)

- [ ] **Step 3: Verify in browser**

Enable 25-yr check. Click "Junction Structures — 25-yr". Structures list with Q₂₅ total flows and HGL elevations. HGL values should be higher than the 10-yr values on the primary tab (more flow → more head loss). Rim check cells show red ✗ FLOOD if the 25-yr HGL exceeds rim−1 ft. No console errors.

- [ ] **Step 4: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Add 25-yr check tabs: read-only pipe sizing and HGL with Q25 flows"
```

---

### Task 13 — Excel export / import

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add "Rainfall Settings" sheet to `buildWorkbook()` — insert just after Overview sheet (≈ line 3840)**

After `XLSX.utils.book_append_sheet(wb, wsOv, "Overview");`, add:
```js
  // ---- Rainfall Settings ----
  const rf = state.rainfall;
  const rfAoa = [
    ["Rainfall Source",          rf.rainfallSource||"noaa"],
    ["County",                   rf.county||"Montgomery"],
    ["Pipe & HGL Design Storm",  rf.pipeStorm||"10yr"],
    ["25-yr Check",              rf.pipe25Check ? "TRUE" : "FALSE"],
    ["Inlet Design Storm",       rf.inletStorm||"2yr"],
    ["Custom NOAA 5-min (in/hr)",  (rf.customNoaa&&rf.customNoaa[5]!=null)?rf.customNoaa[5]:""],
    ["Custom NOAA 10-min (in/hr)", (rf.customNoaa&&rf.customNoaa[10]!=null)?rf.customNoaa[10]:""],
    ["Custom NOAA 15-min (in/hr)", (rf.customNoaa&&rf.customNoaa[15]!=null)?rf.customNoaa[15]:""],
    ["Custom NOAA 30-min (in/hr)", (rf.customNoaa&&rf.customNoaa[30]!=null)?rf.customNoaa[30]:""],
    ["Custom NOAA 60-min (in/hr)", (rf.customNoaa&&rf.customNoaa[60]!=null)?rf.customNoaa[60]:""],
  ];
  const wsRf = XLSX.utils.aoa_to_sheet(rfAoa);
  wsRf["!cols"] = [{wch:30},{wch:20}];
  XLSX.utils.book_append_sheet(wb, wsRf, "Rainfall Settings");
```

- [ ] **Step 2: Update Drainage Area sheet export (≈ line 3841) — remove `i`, add CA / iOverride / Q columns**

Replace the existing Drainage Area export block:
```js
  // ---- Drainage Area ----
  const daHeader = ["ID","Description","Area A (ac)","C","i (in/hr)","Tc (min)","Cf","Q (cfs)","Tc Method"];
  const daRows = [daHeader];
  state.drainage.forEach(r=>{
    daRows.push([r.structureId||r.id, r.desc||"", num(r.area), num(r.C), num(r.i), num(r.tc), num(r.cf,1), null, r.tcMethod||"direct"]);
  });
  const wsDa = XLSX.utils.aoa_to_sheet(daRows);
  state.drainage.forEach((r,i)=>{
    const row=i+2, calc=calcDrainageRow(r);
    setFormula(wsDa, "H"+row, "=C"+row+"*D"+row+"*E"+row+"*G"+row, round(calc.Q,4));
  });
  wsDa["!cols"] = [{wch:12},{wch:26},{wch:11},{wch:8},{wch:10},{wch:9},{wch:7},{wch:10},{wch:11}];
  XLSX.utils.book_append_sheet(wb, wsDa, "Drainage Area");
```
With:
```js
  // ---- Drainage Area ----
  const rfSrc   = state.rainfall.rainfallSource;
  const daStorms = availableStorms(rfSrc);
  const daQHeaders = daStorms.map(s => "Q_" + s + " (cfs)");
  const daHeader = ["ID","Description","Area A (ac)","C","CA","i Override (in/hr)","Tc (min)","Cf","Tc Method", ...daQHeaders];
  const daRows = [daHeader];
  state.drainage.forEach(r => {
    const calc = calcDrainageRow(r);
    const qVals = daStorms.map(s => round(calc.Qs[s] || 0, 3));
    daRows.push([
      r.structureId||r.id, r.desc||"",
      num(r.area), num(r.C),
      round(calc.CA, 3),
      (r.iOverride !== "" && r.iOverride != null) ? num(r.iOverride) : "",
      num(r.tc), num(r.cf, 1),
      r.tcMethod||"direct",
      ...qVals
    ]);
  });
  const wsDa = XLSX.utils.aoa_to_sheet(daRows);
  wsDa["!cols"] = [{wch:12},{wch:26},{wch:11},{wch:8},{wch:8},{wch:14},{wch:9},{wch:7},{wch:11},
    ...daStorms.map(()=>({wch:10}))];
  XLSX.utils.book_append_sheet(wb, wsDa, "Drainage Area");
```

- [ ] **Step 3: Update Inlet Spacing sheet export — remove rainfall settings rows**

In the Inlet Spacing export block (≈ line 4129), remove these push lines:
```js
    ["Rainfall Source", is.rainfallSource||"noaa"],
    ...
    ["# County", is.county||"Montgomery"],
    ["# Storm", is.storm||"10yr"],
    ["# Custom NOAA 5-min", ...],
    ...
```
Keep only `# Project Street` and `# Default Allowable Spread` settings rows. Remove the `pastHeader` check for rainfall rows in the corresponding import block too (Step 6).

- [ ] **Step 4: Read "Rainfall Settings" in `importExcel()` — add before Drainage Area read (≈ line 4208)**

After `const wb = XLSX.read(...)`, add:
```js
      // ---- Rainfall Settings ----
      const rfWs = wb.Sheets["Rainfall Settings"];
      if (rfWs) {
        const rfAoaRaw = XLSX.utils.sheet_to_json(rfWs, {header:1, raw:true, defval:""});
        const rfMap = {};
        rfAoaRaw.forEach(r => { if (r[0]) rfMap[String(r[0]).trim()] = r[1]; });
        const newRf = defaultRainfallSettings();
        if (rfMap["Rainfall Source"])         newRf.rainfallSource = rfMap["Rainfall Source"];
        if (rfMap["County"])                  newRf.county         = rfMap["County"];
        if (rfMap["Pipe & HGL Design Storm"]) newRf.pipeStorm      = rfMap["Pipe & HGL Design Storm"];
        if (rfMap["25-yr Check"])             newRf.pipe25Check    = rfMap["25-yr Check"] === "TRUE";
        if (rfMap["Inlet Design Storm"])      newRf.inletStorm     = rfMap["Inlet Design Storm"];
        [5,10,15,30,60].forEach(d => {
          const v = rfMap["Custom NOAA "+d+"-min (in/hr)"];
          if (v !== "" && v != null) newRf.customNoaa[d] = v;
        });
        state.rainfall = newRf;
      }
```

- [ ] **Step 5: Update Drainage Area import to read new column names**

In the `const da = sheetToRows(wb, "Drainage Area")` block (≈ line 4208), change the row mapping:

Replace:
```js
            id, structureId: label, desc:r["Description"]||"", area:r["Area A (ac)"]||"", C:r["C"]||"", i:r["i (in/hr)"]||"", tc:r["Tc (min)"]||"", cf: r["Cf"]===""||r["Cf"]==null?1:r["Cf"],
```
With:
```js
            id, structureId: label, desc:r["Description"]||"", area:r["Area A (ac)"]||"", C:r["C"]||"",
            iOverride: (()=>{
              // Migration: if old export had 'i (in/hr)' and no 'i Override', copy it
              const override = r["i Override (in/hr)"];
              if (override !== "" && override != null) return String(override);
              const oldI = r["i (in/hr)"];
              if (oldI !== "" && oldI != null && isFinite(Number(oldI))) return String(oldI);
              return "";
            })(),
            tc:r["Tc (min)"]||"", cf: r["Cf"]===""||r["Cf"]==null?1:r["Cf"],
```

- [ ] **Step 6: Update Inlet Spacing import — remove rainfall-specific row parsers**

In the Inlet Spacing import block, remove the `else if` branches that read `# Rainfall Source`, `# County`, `# Storm`, `# Custom NOAA ...`. Keep only `# Project Street` and `# Default Allowable Spread`.

- [ ] **Step 7: Test Excel round-trip**

Add to `tests/run-tests.mjs`:
```js
test("buildWorkbook: Rainfall Settings sheet exists", () => {
  const wb = sdc.buildWorkbook();
  assert.ok(wb.SheetNames.includes("Rainfall Settings"), "Rainfall Settings sheet missing");
});
test("buildWorkbook: Drainage Area has CA column, no i column", () => {
  const wb = sdc.buildWorkbook();
  const ws = wb.Sheets["Drainage Area"];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  const headers = aoa[0] || [];
  assert.ok(headers.includes("CA"), "CA header missing");
  assert.ok(!headers.includes("i (in/hr)"), "old i column should be removed");
  assert.ok(headers.includes("i Override (in/hr)"), "iOverride column missing");
});
```

Run: `cd tests && npm test`  
Expected: all tests pass.

- [ ] **Step 8: Manual round-trip browser test**

Export to Excel. Open file — verify "Rainfall Settings" sheet (second sheet) and updated "Drainage Area" columns. Import back — all settings restore. Inlet Spacing rows restore correctly.

- [ ] **Step 9: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/run-tests.mjs
git commit -m "Excel export/import: Rainfall Settings sheet, updated Drainage Area columns, inlet spacing cleanup"
```

---

### Task 14 — `window.__sdc` exposure + overview update + final commit

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add new functions to `window.__sdc` (≈ line 4452)**

Add to the `window.__sdc = { ... }` object:
```js
defaultRainfallSettings, availableStorms, getTabs,
```

- [ ] **Step 2: Update the Overview tab step list — add new step for Rainfall tab**

In `renderOverview()` (≈ line 1906), find the `steps` array. Add a new step (adjust step numbers if needed):
```js
["2", "Rainfall & IDF — Shared Project Rainfall Settings",
 "Select rainfall source (NOAA Atlas 14 county, MDSHA agency, or MoCo agency), design storms (pipe/HGL storm and inlet storm independently), and optionally unlock 25-yr check tabs. The IDF table shows intensities at standard Tₜ values for all return periods. NOAA county entries include a validation link to the NOAA Atlas 14 PFDS viewer.",
 "", ""],
```
(Re-number subsequent steps: the former step 2 becomes step 3, etc.)

- [ ] **Step 3: Run full test suite**

```powershell
cd tests; npm test
```
Expected: all tests pass. Zero failures.

- [ ] **Step 4: Full browser integration checklist**

Walk through:
1. Rainfall tab — source/county/storm controls, NOAA link opens NOAA PFDS in new tab at correct lat/lon, IDF table updates when county changes, 25-yr check checkbox shows/hides conditional tabs
2. Drainage Area — CA column, i override (orange border when set, "auto" placeholder when not), Q₂/Q₁₀/Q₂₅ columns, pipeStorm column highlighted in blue; changing pipeStorm on Rainfall tab moves the blue highlight; detail sheet shows all Q values
3. Junction Structures + Pipe Sizing — unaffected; Q values driven by pipeStorm
4. Inlet Spacing — source/county/storm controls gone from global section; i values change when switching county or inletStorm on Rainfall tab
5. Pipe Sizing — 25-yr + Junction Structures — 25-yr: visible only when checkbox on; Q₂₅ > Q₁₀; red ✗ cells for exceedances
6. Export → Excel: Rainfall Settings sheet present; Drainage Area has new columns; import round-trips all settings

- [ ] **Step 5: Push to remote**

```bash
git push origin main
```

---

## Self-Review

**Spec coverage:**
- §2.1 `state.rainfall` → Task 1 Step 1–3 ✓
- §2.2 strip `inletSpacingSettings` → Task 1 Step 2 ✓
- §2.3 drainage row `iOverride` → Task 1 Steps 4–5 ✓
- §3 Rainfall tab settings + NOAA link → Task 4 ✓
- §3.3 IDF table + Custom Tc row → Task 5 ✓
- §4.1 `calcDrainageRow` → Task 6 ✓
- §4.2 table columns + pipeStorm highlight → Task 7 ✓
- §4.3 `+ Add row` default → Task 1 Step 5 ✓
- §4.4 `computeTotalFlow` uses `designQ` → Task 6 Step 3 (capturedQFor) ✓
- §4.5 detail sheet → Task 8 ✓
- §5.1–5.4 inlet spacing rewiring → Task 9 ✓
- §6 25-yr check tabs (gated by getTabs) → Tasks 2, 10, 11, 12 ✓
- §7 tab order → Task 2 (getTabs) ✓
- §8.1 Rainfall Settings sheet → Task 13 Steps 1, 4 ✓
- §8.2 Drainage Area export changes → Task 13 Steps 2, 5 ✓
- §8.3 Inlet Spacing export/import cleanup → Task 13 Steps 3, 6 ✓

**Migration (old `i` field → `iOverride`):** Task 13 Step 5 handles import migration for existing files that had `i (in/hr)` column. ✓

**`computeStructureCalc` stormOverride:** Task 12 Step 2 adds the parameter so 25-yr HGL propagates correctly. ✓

**`getTabs()` active-tab guard:** Task 2 Step 3 resets `state.active` to `"pipes"` if the active tab becomes hidden. ✓

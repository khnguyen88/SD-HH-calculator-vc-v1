# Drainage Area Storm Column Selection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users pick which storm-event Q columns appear in the Drainage Area table (default: 2-yr + 10-yr; 25-yr auto-forced when pipe25Check is on; pipe/inlet design storms always pinned), with the same checkbox controls mirrored in both the Rainfall & IDF tab and the Drainage Area tab. Also remove the unused "Load MoCo preset" Kb button and its backing constant.

**Architecture:** All changes are in the single app file. Two new helpers (`visibleDaStorms`, `renderDaStormColCheckboxes`) are added near their peers. `state.rainfall.daStormCols` is the sole new state field; it persists automatically because the Excel export/import serialises the full `state.rainfall` object as JSON.

**Tech Stack:** Vanilla JS, single HTML file (`drainage-calculator/storm-drain-design-calculator.html`), no build step.

---

### Task 1: Remove the MoCo Kb preset button and its backing data

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Delete the `MOCO_KB_PRESET` constant (lines ~1055–1150)**

Find and delete the block starting with `// MoCo Kb preset` through the closing `];`:

```
// MoCo Kb preset — from "Kb Values MoCo" sheet of bburg-p-c.xlsx.
// Inlet: 0.50 at 0° → 0.98 at 38°; Manhole: 0.15→0.66; Bend: 0.01→0.16.
// Full table covers 0°–90°.
const MOCO_KB_PRESET = [
  ...96 rows...
];
```

Delete the entire block (comment + const, ~96 lines total). The next non-blank line after the deletion should be `/* ----- Inlet Spacing ... */`.

- [ ] **Step 2: Delete the "Load MoCo preset" button element (in `renderKb()`)**

Find this block (the middle button in the section-head `el("div",[...])`):

```js
      el("button",{class:"btn btn-sm", style:"margin-right:8px;", title:"Overwrites current table with MoCo Kb values from bburg-p-c.xlsx (Tables sheet). Generic AASHTO seed is the fresh-load default.",
        onclick:()=>{
          state.kb = MOCO_KB_PRESET.map(r=>({angle:r[0], inlet:r[1], manhole:r[2], bend:r[3]}));
          renderAll();
          toast("Kb table loaded from MoCo preset (bburg-p-c.xlsx Tables sheet).");
        }}, "Load MoCo preset"),
```

Delete only those 6 lines. The remaining children of that `el("div")` should be:
```js
      el("button",{class:"btn btn-sm", onclick:()=>{ state.kb.push(...); renderKb(); }}, "+ Add row"),
      el("button",{class:"btn btn-sm btn-ghost", onclick:()=>{ state.kb=defaultKbRows(); renderAll(); toast("Kb table reset to default values."); }}, "Reset to default")
```

- [ ] **Step 3: Remove `MOCO_KB_PRESET` from the bottom exports list**

Find this line near the end of the file (~line 6466):
```js
  MDSHA_INTENSITY, MOCO_INTENSITY, NOAA_ATLAS14, NOAA_COUNTY_LIST, INLET_STRUCTURES, MOCO_KB_PRESET,
```

Change it to:
```js
  MDSHA_INTENSITY, MOCO_INTENSITY, NOAA_ATLAS14, NOAA_COUNTY_LIST, INLET_STRUCTURES,
```

- [ ] **Step 4: Open the file in a browser, navigate to Kb Coefficients tab**

Verify: only two buttons remain in the section header — `+ Add row` and `Reset to default`. No MoCo button. No JS errors in the console.

- [ ] **Step 5: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: remove Load MoCo preset Kb button and MOCO_KB_PRESET constant"
```

---

### Task 2: Add `daStormCols` to state and add `visibleDaStorms` helper

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add `daStormCols` to `defaultRainfallSettings()`**

Find `defaultRainfallSettings()` (around line 1420). Add the new field after `inletStorm`:

```js
function defaultRainfallSettings() {
  return {
    rainfallSource: "noaa",
    county: "Montgomery",
    customNoaa: { 5:"", 10:"", 15:"", 30:"", 60:"" },
    noaaFetchInput: "",
    noaaProxyUrl:  "",
    fetchedNoaa: null,
    pipeStorm:   "10yr",
    pipe25Check: false,
    inletStorm:  "2yr",
    daStormCols: ["2yr", "10yr"],
  };
}
```

- [ ] **Step 2: Add `visibleDaStorms(r)` immediately after `availableStorms()`**

Find the `availableStorms` function (around line 1434) and add the new function directly after its closing brace:

```js
function visibleDaStorms(r) {
  const available = availableStorms(r.rainfallSource);
  const cols = new Set(r.daStormCols || ["2yr", "10yr"]);
  cols.add(r.pipeStorm);
  cols.add(r.inletStorm);
  if (r.pipe25Check && available.includes("25yr")) cols.add("25yr");
  const order = ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"];
  return order.filter(s => available.includes(s) && cols.has(s));
}
```

- [ ] **Step 3: Open the browser console and smoke-test the function**

With the file open, paste into the console:
```js
// Should return ["2yr","10yr"] with default settings
console.log(visibleDaStorms({rainfallSource:"noaa", pipeStorm:"10yr", inletStorm:"2yr", pipe25Check:false, daStormCols:["2yr","10yr"]}));

// Should return ["2yr","10yr","25yr"] — 25yr forced by pipe25Check
console.log(visibleDaStorms({rainfallSource:"noaa", pipeStorm:"10yr", inletStorm:"2yr", pipe25Check:true, daStormCols:["2yr","10yr"]}));

// Should return ["2yr","10yr","50yr"] — 50yr user-selected, pipeStorm pinned
console.log(visibleDaStorms({rainfallSource:"noaa", pipeStorm:"10yr", inletStorm:"2yr", pipe25Check:false, daStormCols:["2yr","50yr"]}));

// MoCo source — 50yr not available, should be silently dropped → ["2yr","10yr"]
console.log(visibleDaStorms({rainfallSource:"moco", pipeStorm:"10yr", inletStorm:"2yr", pipe25Check:false, daStormCols:["2yr","50yr"]}));
```

Expected outputs:
- `["2yr","10yr"]`
- `["2yr","10yr","25yr"]`
- `["2yr","10yr","50yr"]`
- `["2yr","10yr"]`

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add daStormCols state field and visibleDaStorms helper"
```

---

### Task 3: Wire the Drainage Area table to use `visibleDaStorms`

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Replace `availableStorms` with `visibleDaStorms` in `renderDrainage()`**

Find this line in `renderDrainage()` (around line 2501):
```js
  const storms = availableStorms(state.rainfall.rainfallSource);
```

Change it to:
```js
  const storms = visibleDaStorms(state.rainfall);
```

That is the only change needed — the header and body Q columns are already driven by `storms`.

- [ ] **Step 2: Open the browser, check the Drainage Area tab**

With a NOAA rainfall source and default settings, the table should show exactly two Q columns: Q₂ (2-yr) and Q₁₀ (10-yr), highlighted with their usual accent colours. No 1yr, 5yr, 50yr, 100yr, 500yr columns.

Enable "Also compute 25-yr pipe & HGL check" in the Rainfall tab → Drainage Area table should immediately gain a Q₂₅ column.

- [ ] **Step 3: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: filter drainage area Q columns to visibleDaStorms"
```

---

### Task 4: Add `renderDaStormColCheckboxes` helper and wire into Rainfall & IDF tab

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add the `renderDaStormColCheckboxes(r)` helper**

Add this function just before `renderRainfall()` (around line 3526). It returns a `<div>` with one labelled checkbox per available storm:

```js
function renderDaStormColCheckboxes(r) {
  const available = availableStorms(r.rainfallSource);
  const shortLbl = {"1yr":"1-yr","2yr":"2-yr","5yr":"5-yr","10yr":"10-yr",
                    "25yr":"25-yr","50yr":"50-yr","100yr":"100-yr","500yr":"500-yr"};
  const wrap = el("div", {style:"display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:6px 0;"});
  available.forEach(s => {
    const isPipe     = s === r.pipeStorm;
    const isInlet    = s === r.inletStorm;
    const is25forced = s === "25yr" && r.pipe25Check;
    const pinned     = isPipe || isInlet || is25forced;
    const isChecked  = pinned || (r.daStormCols || ["2yr","10yr"]).includes(s);
    const tip = isPipe     ? "Always shown — pipe design storm"
              : isInlet    ? "Always shown — inlet design storm"
              : is25forced ? "Always shown — 25-yr check enabled"
              : "";
    const chkEl = el("input", {
      type: "checkbox",
      "data-focus-key": "rf:daStormCols:" + s,
      title: tip,
      disabled: pinned ? "disabled" : null,
      onchange: pinned ? null : (e) => {
        const cols = new Set(r.daStormCols || ["2yr","10yr"]);
        if (e.target.checked) cols.add(s); else cols.delete(s);
        r.daStormCols = [...cols];
        withFocusPreserved(renderAll);
      }
    });
    chkEl.checked = isChecked;
    wrap.appendChild(
      el("label", {style:"display:flex;gap:5px;align-items:center;font-size:0.85em;"
                        + (pinned ? "opacity:0.55;cursor:default;" : "cursor:pointer;")},
        [chkEl, shortLbl[s] || s])
    );
  });
  return wrap;
}
```

- [ ] **Step 2: Add the "Drainage Area Q columns" row inside `renderRainfall()`**

Find the end of the Design Storms section in `renderRainfall()`. After:
```js
  stormSec.appendChild(stRow);
  c.appendChild(stormSec);
```

Add a new section immediately before `renderRainfallIdfTable(c)`:

```js
  // Drainage Area column selector
  const daColSec = el("div", {class:"section"});
  daColSec.appendChild(el("div", {class:"section-head"}, [el("h2", {}, "Drainage Area Q columns")]));
  const daColRow = el("div", {style:"padding:8px 0;"});
  daColRow.appendChild(el("p", {class:"view-desc", style:"margin:0 0 6px;"},
    "Select which storm-event Q columns appear in the Drainage Area table. " +
    "The pipe and inlet design storms are always shown."));
  daColRow.appendChild(renderDaStormColCheckboxes(r));
  daColSec.appendChild(daColRow);
  c.appendChild(daColSec);

  renderRainfallIdfTable(c);
```

- [ ] **Step 3: Open the browser, go to Rainfall & IDF tab**

Verify: a "Drainage Area Q columns" section appears between the Design Storms row and the IDF table. For NOAA source, 8 checkboxes appear. 2-yr and 10-yr are checked. Pipe (10-yr) and Inlet (2-yr) checkboxes show with reduced opacity and are not clickable. Checking 50-yr updates the Drainage Area table immediately.

- [ ] **Step 4: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add DA Q column checkboxes to Rainfall & IDF tab"
```

---

### Task 5: Mirror the checkbox row on the Drainage Area tab

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add the checkbox row above the table in `renderDrainage()`**

Find where `tableWrap` is created in `renderDrainage()` (around line 2499):
```js
  const tableWrap = el("div",{class:"table-wrap"});
```

Insert the checkbox strip between `section.appendChild(el("div",{class:"section-head"},[...]))` and `const tableWrap`:

```js
  // Storm column selector — mirrors Rainfall & IDF tab
  const colSelRow = el("div", {style:"padding:6px 12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;"});
  colSelRow.appendChild(el("span", {style:"color:#aaa;font-size:0.82em;white-space:nowrap;"}, "Show Q columns:"));
  colSelRow.appendChild(renderDaStormColCheckboxes(state.rainfall));
  section.appendChild(colSelRow);

  const tableWrap = el("div",{class:"table-wrap"});
```

- [ ] **Step 2: Open the browser, go to the Drainage Area tab**

Verify: "Show Q columns:" label appears above the table with the same checkboxes. Toggling a checkbox here immediately changes the visible columns and also reflects the same checked state when you switch to the Rainfall tab (they share state).

Switch rainfall source from NOAA to MDSHA — checkboxes should update to show only 2-yr, 10-yr, 25-yr. Any NOAA-only storms previously checked simply don't appear (they're filtered by `availableStorms`).

- [ ] **Step 3: Commit**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: mirror DA Q column checkboxes on Drainage Area tab"
```

---

### Task 6: End-to-end verification

**Files:** None (manual verification only)

- [ ] **Step 1: Default state — NOAA source**

Fresh load (or reset state). Drainage Area table shows Q₂ and Q₁₀ only. Rainfall tab "Drainage Area Q columns" shows 2-yr and 10-yr checked; 10-yr and 2-yr are pinned (pipe/inlet design storms). IDF table still shows all storms.

- [ ] **Step 2: Enable 25-yr check**

In Rainfall tab, check "Also compute 25-yr pipe & HGL check". Drainage Area table immediately gains Q₂₅ column. In the DA column checkboxes, 25-yr is now checked + pinned with reduced opacity. Turn off pipe25Check → Q₂₅ column disappears; 25-yr checkbox is interactive again.

- [ ] **Step 3: User-select extra storms**

Check 100-yr in either tab. Both tabs reflect it checked. Drainage Area table shows Q₂, Q₁₀, Q₁₀₀. Uncheck 2-yr — it cannot be unchecked (it is the inlet design storm, pinned). Uncheck 100-yr → column disappears.

- [ ] **Step 4: Change pipe design storm**

Change pipe storm from 10-yr to 50-yr. Q₅₀ column appears (pinned). The 50-yr checkbox is now checked + disabled. The former 10-yr checkbox becomes interactive (it stays checked because 10-yr was in `daStormCols`; user can now uncheck it if desired).

- [ ] **Step 5: Switch to MDSHA source**

Switch rainfallSource to MDSHA. Available storms are 2-yr, 10-yr, 25-yr — only 3 checkboxes show. Any NOAA-only entries in `daStormCols` (e.g. 100-yr) are silently dropped from the rendered columns but remain in `daStormCols`; switching back to NOAA restores them.

- [ ] **Step 6: Excel round-trip**

Export to `.xlsx`. Re-import. Verify `daStormCols` is preserved (same columns visible after import as before).

- [ ] **Step 7: LocalStorage round-trip**

Save a snapshot (quick-save). Reload the page. Restore the snapshot. Verify `daStormCols` is preserved.

- [ ] **Step 8: Final commit if any fixes were needed**

```
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "fix: <describe any issue found during verification>"
```

Skip this step if no fixes were needed.

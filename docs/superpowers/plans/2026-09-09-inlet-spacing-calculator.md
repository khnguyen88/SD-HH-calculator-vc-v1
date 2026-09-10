# Inlet Spacing Calculator — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone Inlet Spacing tab to the storm drain design calculator implementing HEC-22-style grate-inlet spacing with MDSHA/MoCo structure library, NOAA Atlas 14 county rainfall, SHA/MoCo agency intensity curves, bypass carryover chain, on-grade spread, grate interception efficiency, and per-row detail sheets. Also add a MoCo Kb preset button to the Kb Coefficients tab, and integrate the new tab into Excel export/import and Print All.

**Architecture:** All additions are inline JS/CSS in `drainage-calculator/storm-drain-design-calculator.html` — the single-file offline app constraint is absolute. A new `tests/` directory (Node + jsdom) is created for the oracle test harness; it does NOT ship in the HTML. The NOAA Atlas 14 county data is compiled once (Task 2) and stored as a JS constant in the HTML.

**Tech Stack:** Vanilla JS; SheetJS (already bundled inline in the HTML); Node + jsdom + node:test for `tests/` (new).

**Design doc:** `docs/superpowers/specs/2026-09-09-inlet-spacing-calculator-design.md`

**Key facts for the executor:**

- **Single-file rule:** Every byte of new code goes inside `drainage-calculator/storm-drain-design-calculator.html` (between the existing `<script>` tags in the IIFE), except `tests/`. Never add a CDN link or external file reference.
- **File size:** ~618 KB before these changes; target < 700 KB after (NOAA data is ~50 KB of JS constants).
- **withFocusPreserved pattern (line 1262):** Every `oninput` that mutates state must call `withFocusPreserved(renderAll)`. Every new input element needs `data-focus-key` attribute with a unique string, e.g. `"is:"+row.id+":"+fieldName`.
- **State (line 608):** `const state = { project, active, drainage, structures, pipes, kb, outletStructures, outletDevices, activeOutletId, outletShowGeometryDetail }` — add `inletSpacing: []` and `inletSpacingSettings: defaultInletSpacingSettings()`.
- **TABS array (line 1301):** Currently 8 entries ending with `{id:"kb", label:"Kb Coefficients"}`. Append `{id:"inlet-spacing", label:"Inlet Spacing"}` as entry 9.
- **View div (line 490):** After `<div class="view" id="view-kb"></div>`, add `<div class="view" id="view-inlet-spacing"></div>`.
- **renderAll() (line 2098):** After `renderKb();` add `renderInletSpacing();`.
- **printAllSheets() (line 2815):** After outlet rows, add inlet spacing rows.
- **buildWorkbook() (line 2845):** After Kb sheet, append "Inlet Spacing" sheet.
- **importExcel() (line 3195):** After Kb import, read "Inlet Spacing" sheet.
- **renderKb() (line 2053):** Add "Load MoCo preset" button to the section-head div.
- **window.__sdc (line 3397):** Expose new computation functions.
- **Excel MUST use `bookSST: true`** (line 3171, already set in `exportExcel()`).
- **No localStorage** — all state comes from import; default state from `defaultInletSpacingSettings()` + empty `[]`.
- **el() helper:** Already defined; use it for all DOM construction. Pattern: `el("tag", {attrs}, children)`.
- **csSection() (line 2114):** Use for calc-sheet sections inside detail modals.
- **openDetailModal(sheetNode) (line 2619):** Use to show inlet row detail sheets.
- **Oracle test file location:** The executor may also run a script against `docs/bburg-p-c.xlsx` to extract/verify formula values if needed.

---

### Task 1 — Set up Node test harness

**Files:** `tests/package.json` (new), `tests/run-tests.mjs` (new)

- [ ] **Step 1: Create `tests/package.json`**

```json
{
  "name": "storm-drain-tests",
  "type": "module",
  "scripts": {
    "test": "node --test run-tests.mjs"
  },
  "dependencies": {
    "jsdom": "^25.0.0",
    "xlsx": "^0.18.5"
  }
}
```

- [ ] **Step 2: Run `npm install` from `tests/`**

```powershell
cd tests && npm install
```

- [ ] **Step 3: Create `tests/run-tests.mjs` with the harness loader**

The harness must:
1. Read `../drainage-calculator/storm-drain-design-calculator.html` as text.
2. Create a jsdom DOM with the HTML (use `runScripts: "dangerously"` to execute the inline JS).
3. Wait for `DOMContentLoaded` to fire so `init()` runs and `window.__sdc` is populated.
4. Import computation functions from `window.__sdc` (those already there plus the new inlet-spacing ones after Task 4).

Starter harness (paste this verbatim — adapt later as functions are added):

```js
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { test } from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(
  new URL("../drainage-calculator/storm-drain-design-calculator.html", import.meta.url),
  "utf8"
);

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
});
const { window } = dom;

// Give DOMContentLoaded time to fire
await new Promise(r => setTimeout(r, 200));

const sdc = window.__sdc;

// --- Smoke test ---
test("__sdc is populated", () => {
  assert.ok(sdc, "__sdc not exposed on window");
});
```

- [ ] **Step 4: Run and confirm smoke test passes**

```powershell
cd tests && npm test
```

Expected: 1 passing test, no JS errors from the HTML parse. If there are parse errors, fix them before proceeding (they indicate a problem with the existing file, not with the new code).

---

### Task 2 — Compile NOAA Atlas 14 data

**Files:** Produces the `NOAA_ATLAS14` constant to embed in the HTML (Task 5 step inserts it).

This task has no file changes until Task 5; the output is a JS object literal you will paste into the HTML.

The NOAA Atlas 14 PFDS (Point Precipitation Frequency Data Server) provides the data. For each of the 25 jurisdictions below, fetch the 5/10/15/30/60-min precipitation depths for 2-yr, 10-yr, and 25-yr recurrence intervals, then convert to intensity (in/hr = depth_in / (duration_min/60)).

**Representative coordinates (county seat / centroid — record these in the provenance block):**

| Jurisdiction | Lat | Lon |
|---|---|---|
| Allegany | 39.6529 | -78.7625 |
| Anne Arundel | 38.9784 | -76.4922 |
| Baltimore City | 39.2904 | -76.6122 |
| Baltimore County | 39.3951 | -76.6017 |
| Calvert | 38.5401 | -76.5858 |
| Caroline | 38.8890 | -75.8283 |
| Carroll | 39.5757 | -76.9958 |
| Cecil | 39.6062 | -75.8333 |
| Charles | 38.5287 | -76.9750 |
| Dorchester | 38.5632 | -76.0788 |
| Frederick | 39.4143 | -77.4105 |
| Garrett | 39.4062 | -79.4067 |
| Harford | 39.5351 | -76.3483 |
| Howard | 39.2673 | -76.7983 |
| Kent | 39.2090 | -76.0650 |
| Montgomery | 39.0840 | -77.1528 |
| Prince George's | 38.8179 | -76.7497 |
| Queen Anne's | 39.0390 | -76.0688 |
| Saint Mary's | 38.2918 | -76.6358 |
| Somerset | 38.1979 | -75.6927 |
| Talbot | 38.7743 | -76.0763 |
| Washington | 39.6418 | -77.7199 |
| Wicomico | 38.3607 | -75.5994 |
| Worcester | 38.1771 | -75.3927 |
| DC | 38.9072 | -77.0369 |

**How to fetch (use WebFetch or curl):**

NOAA PFDS API URL (returns a page with a JSON block you can parse):
```
https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py?type=pf&units=us&series=pds&statename=maryland&lat=LAT&lon=LON
```
For DC: `statename=dc`. The response JSON contains a `data` array indexed by duration and ARI. Extract columns for ARI=2, 10, 25 and rows for duration 5, 10, 15, 30, 60 min (durations are labeled "5-min", "10-min", etc. in the NOAA response). Values are precipitation depths in inches (PDS, US customary).

**Convert depths to intensities:**
```
i (in/hr) = depth (in) / (duration_min / 60)
```
Example: if 5-min depth = 0.42 in → i = 0.42 / (5/60) = 5.04 in/hr.

**Do NOT invent any values.** If a county lookup fails, note it explicitly in the provenance comment.

**Required JS output format** (paste into Task 5):
```js
// NOAA Atlas 14 PDS intensities (in/hr).
// Source: NOAA PFDS API, PDS series, US customary.
// Coordinates: county seat or centroid listed below per jurisdiction.
// Pull date: <DATE_YOU_PULLED_THIS>
// Values vary within each county; users needing project-specific intensity use Custom mode.
const NOAA_ATLAS14 = {
  "Allegany": {
    lat: 39.6529, lon: -78.7625,
    // intensities in/hr keyed by storm → duration(min) → value
    "2yr":  { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
    "10yr": { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
    "25yr": { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
  },
  // ... (all 25 jurisdictions in alphabetical order, DC last)
  "DC": {
    lat: 38.9072, lon: -77.0369,
    "2yr":  { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
    "10yr": { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
    "25yr": { 5: X.XX, 10: X.XX, 15: X.XX, 30: X.XX, 60: X.XX },
  },
};
// Jurisdictions in the dropdown (order: MD counties alphabetical, then DC):
const NOAA_COUNTY_LIST = [
  "Allegany","Anne Arundel","Baltimore City","Baltimore County",
  "Calvert","Caroline","Carroll","Cecil","Charles","Dorchester",
  "Frederick","Garrett","Harford","Howard","Kent","Montgomery",
  "Prince George's","Queen Anne's","Saint Mary's","Somerset",
  "Talbot","Washington","Wicomico","Worcester","DC"
];
```

**Provenance spot-check (after compiling):** Pull 2–3 values from NOAA's web tool at the same coordinates and record them in a comment beside the constant as the "published spot-check" so future readers can verify the data wasn't corrupted.

---

### Task 3 — Data constants: intensity curves, structure library, MoCo Kb

**File:** `drainage-calculator/storm-drain-design-calculator.html` (inside the IIFE `<script>`, before the `State` block at line 602)

These constants define the agency intensity curves, the structure preset library, and the MoCo Kb table. Paste them together in one block just **before** the line `const KB_COLUMN_FOR_TYPE = ...` (line 600).

- [ ] **Step 1: MDSHA intensity breakpoints**

```js
// MDSHA (SHA Intensity sheet, bburg-p-c.xlsx). Intensities in/hr.
// Clamp below Tc=5 → use 5-min value; clamp above last breakpoint → use last value.
const MDSHA_INTENSITY = {
  "2yr":  [[5, 5.016], [10, 4.788], [15, 3.364]],
  "10yr": [[5, 6.684], [10, 5.340], [15, 4.520], [30, 3.260]],
  "25yr": [[5, 7.572], [10, 6.000], [15, 5.080], [30, 3.780]],
};
```

- [ ] **Step 2: MoCo intensity breakpoints**

```js
// MoCo (Intensity sheet, bburg-p-c.xlsx). 2YR/5YR/10YR; no 25-yr column.
const MOCO_INTENSITY = {
  "2yr":  [[5, 5.52], [10, 4.28], [15, 3.54], [20, 3.04], [30, 2.40], [60, 1.52]],
  "5yr":  [[5, 6.39], [10, 5.16], [15, 4.36], [20, 3.78], [30, 3.02], [60, 1.93]],
  "10yr": [[5, 7.07], [10, 5.85], [15, 5.00], [20, 4.37], [30, 3.49], [60, 2.19]],
};
```

- [ ] **Step 3: Structure library**

Open `docs/bburg-p-c.xlsx` and `docs/category3.pdf` to confirm grate dimensions before inserting. Until confirmed, use workbook-derived seed values (L options = 5/10/15/20 ft, W=1.33 ft, a=0.0833 ft, n=0.013) and add a `seedOnly: true` flag. The UI will show a disclosure note for seedOnly entries.

```js
// MDSHA Book of Standards Category III — grate inlet library.
// L options from workbook seeds; W/a/n from workbook (W=1.33, a=0.0833 ft, n=0.013).
// seedOnly:true = dimensions are workbook-derived seeds, not confirmed from standard sheet.
// Verify against governing standard sheet before submittal.
const INLET_STRUCTURES = [
  { id:"MD 374.01", label:"Curb Opening Inlet (Sh. 1)",        Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.02", label:"Curb Opening Inlet (Sh. 2)",        Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.11", label:"Combination Inlet (Sh. 1)",         Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.12", label:"Combination Inlet (Sh. 2)",         Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.21", label:"Grate Inlet Structures (Sh. 1)",    Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.22", label:"Grate Inlet Structures (Sh. 2)",    Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.31", label:"Standard COG Grate Inlet (Sh. 1)",  Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.32", label:"Standard COG Grate Inlet (Sh. 2)",  Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.41", label:"Combination Inlet COG (Sh. 1)",     Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.42", label:"Combination Inlet COG (Sh. 2)",     Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.51", label:"Precast Sq/Rect COG Inlet",         Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.52", label:"Precast Sq/Rect COS Inlet (1)",     Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.61", label:"Precast Sq/Rect COS Inlet (2)",     Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 374.63", label:"Precast Circular COS Inlet",        Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 375.01", label:"C-1a Precast Curb Inlet (Sh. 1)",   Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 375.02", label:"C-1a Precast Curb Inlet (Sh. 2)",   Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 375.21", label:"C-1c Precast Curb Inlet (Sh. 1)",   Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 375.22", label:"C-1c Precast Curb Inlet (Sh. 2)",   Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 376.01", label:"Inlet Structure Type A (Sh. 1)",    Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 376.02", label:"Inlet Structure Type A (Sh. 2)",    Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 376.11", label:"Inlet Structure Type E",            Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
  { id:"MD 378.01", label:"Precast Concrete Junction Box",     Ls:[5,10,15,20], W:1.33, a:0.0833, n:0.013, seedOnly:true },
];
```

- [ ] **Step 4: Extract MoCo Kb table from workbook**

Open `docs/bburg-p-c.xlsx`. The MoCo Kb data is in the sheet internally named "MoCoIntensity" (which is actually the Kb/TABLES sheet per the workbook structure). Extract the full angle table for Inlet, Manhole, and Bend columns (angles 0°–38° or whatever breakpoints appear). Format as:

```js
// MoCo Kb preset — from TABLES sheet of bburg-p-c.xlsx.
// Inlet: 0.50 at 0° → 0.98 at 38°; Manhole: 0.15→0.66; Bend: 0.01→0.16.
// Load via "Load MoCo preset" button on the Kb Coefficients tab.
const MOCO_KB_PRESET = [
  // { angle: DEG, inlet: VAL, manhole: VAL, bend: VAL },
  // ... (fill all rows from the workbook table)
];
```

---

### Task 4 — Core computation functions

**File:** `drainage-calculator/storm-drain-design-calculator.html` (inside the IIFE, after the constants from Task 3, before the `State` block)

These pure functions have no DOM or state dependencies; they can be tested in the jsdom harness.

- [ ] **Step 1: Piecewise-linear intensity interpolation**

```js
// Piecewise-linear interpolation over [[tc,i], ...] breakpoints.
// Clamps at both ends (no extrapolation).
function interpolatePL(tc, breakpoints) {
  if (!breakpoints || breakpoints.length === 0) return 0;
  if (tc <= breakpoints[0][0]) return breakpoints[0][1];
  for (let j = 1; j < breakpoints.length; j++) {
    const [t0, i0] = breakpoints[j-1];
    const [t1, i1] = breakpoints[j];
    if (tc <= t1) return i0 + (i1-i0)*((tc-t0)/(t1-t0));
  }
  return breakpoints[breakpoints.length-1][1]; // clamp at upper end
}
```

- [ ] **Step 2: Intensity lookup routing**

```js
// Returns intensity (in/hr) for given tc (min), source, storm, county (for NOAA),
// and optional customNoaa object { 5:, 10:, 15:, 30:, 60: }.
// source: "mdsha" | "moco" | "noaa"
// storm:  "2yr" | "5yr" | "10yr" | "25yr"
// county: a key in NOAA_ATLAS14 (only used when source==="noaa")
function lookupIntensity(tc, source, storm, county, customNoaa) {
  if (source === "noaa") {
    if (county === "Custom") {
      // customNoaa keys are 5,10,15,30,60
      const pts = [[5,customNoaa[5]],[10,customNoaa[10]],[15,customNoaa[15]],[30,customNoaa[30]],[60,customNoaa[60]]]
        .filter(([,v]) => v !== "" && v != null && isFinite(Number(v)))
        .map(([t,v]) => [t, Number(v)]);
      return interpolatePL(tc, pts);
    }
    const entry = NOAA_ATLAS14[county];
    if (!entry) return 0;
    const stormData = entry[storm] || entry["10yr"];
    // Convert object {5:v, 10:v, 15:v, 30:v, 60:v} to sorted breakpoint array
    const pts = [5,10,15,30,60].map(d => [d, stormData[d]]);
    return interpolatePL(tc, pts);
  }
  if (source === "moco") {
    const curve = MOCO_INTENSITY[storm] || MOCO_INTENSITY["10yr"];
    return interpolatePL(tc, curve);
  }
  // default: "mdsha"
  const curve = MDSHA_INTENSITY[storm] || MDSHA_INTENSITY["10yr"];
  return interpolatePL(tc, curve);
}
```

- [ ] **Step 3: Composite gutter effective cross-slope**

Formula extracted from the reference workbook (bburg-p-c.xlsx, "Inlet Spacing_10-yr" helper columns):
```
V = (a + Sx·W) / W                          [composite gutter slope]
Qw = (0.56/n) · V^1.667 · S^0.5 · W^2.667  [gutter section flow at full spread W]
W_ratio = (a / (a + Sx·W)) · (Qw / Q)      [depression-weighted gutter fraction]
Sx_eff = Sx + (a/W) · W_ratio
```
If Q ≤ 0 or W ≤ 0 or a ≤ 0, return Sx (no depression adjustment).

```js
function computeSxEff(Sx, a, W, Q, S, n) {
  if (!(Q > 0) || !(W > 0) || !(a > 0)) return Sx;
  const V    = (a + Sx * W) / W;
  const Qw   = (0.56 / n) * Math.pow(V, 1.667) * Math.pow(S, 0.5) * Math.pow(W, 2.667);
  const Wratio = (a / (a + Sx * W)) * (Qw / Q);
  return Sx + (a / W) * Wratio;
}
```

- [ ] **Step 4: On-grade spread**

```js
// HEC-22 on-grade spread.  Returns T in feet.  Returns 0 on bad inputs.
function computeSpread(Q, n, SxEff, S) {
  if (!(Q > 0) || !(SxEff > 0) || !(S > 0)) return 0;
  return Math.pow((Q * n) / (0.56 * Math.pow(SxEff, 1.67) * Math.pow(S, 0.5)), 0.3745);
}
```

- [ ] **Step 5: Grate required flow length and interception efficiency**

k selection rule (from spec §1.3):
- k = 0.60 when a = 0 (no gutter depression)
- k = 0.54 when L ≥ 15 ft
- k = 0.58 when L < 15 ft

```js
// Returns { Lt, E, bypass_frac }
function computeInterception(L, Q, S, n, SxEff, a) {
  if (!(Q > 0) || !(S > 0) || !(SxEff > 0)) return { Lt: 0, E: 1, bypass_frac: 0 };
  const k = (!(a > 0)) ? 0.60 : (L >= 15 ? 0.54 : 0.58);
  const Lt = k * Math.pow(Q, 0.42) * Math.pow(S, 0.3) * Math.pow(1 / (n * SxEff), 0.6);
  if (L >= Lt) return { Lt, E: 1, bypass_frac: 0 };
  const E = 1 - Math.pow(1 - L / Lt, 1.8);
  return { Lt, E, bypass_frac: 1 - E };
}
```

- [ ] **Step 6: Single-inlet computation**

```js
// Computes all derived values for one inlet row.
// bypassQIn = sum of Q_bypass from upstream inlets pointing to this row.
// bypassCAIn = sum of bypass CA from upstream inlets.
// Returns computed result object (does not mutate row).
function computeInletRow(row, settings, bypassQIn, bypassCAIn) {
  const isSump = String(row.S).toUpperCase() === "SUMP";
  const tc = Number(row.tc);
  const area = Number(row.area);
  const C    = Number(row.C);
  const S    = isSump ? 0 : Number(row.S);
  const Sx   = Number(row.Sx);
  const W    = Number(row.W);
  const a    = Number(row.a);
  const n    = Number(row.n);
  const L    = Number(row.L);
  const allowT = Number(row.allowableSpread || settings.allowableSpread);

  // Intensity: iOverride wins, else computed from curve
  const iComputed = (isFinite(tc) && tc > 0)
    ? lookupIntensity(tc, settings.rainfallSource, settings.storm, settings.county, settings.customNoaa)
    : 0;
  const i = (row.iOverride !== "" && row.iOverride != null && isFinite(Number(row.iOverride)))
    ? Number(row.iOverride)
    : iComputed;

  const localCA = isFinite(C * area) ? C * area : 0;
  const localQ  = localCA * i;
  const Q       = localQ + (isFinite(bypassQIn) ? bypassQIn : 0);
  const totalCA = localCA + (isFinite(bypassCAIn) ? bypassCAIn : 0);

  if (isSump) {
    return { i, iComputed, Q, totalCA, isSump: true,
             SxEff: null, T: null, Lt: null, E: 1, bypassFrac: 0,
             bypassQ: 0, bypassCA: 0, pickupPct: 100, allowT,
             warn: false };
  }

  const SxEff = (isFinite(Sx) && Sx > 0 && isFinite(W) && W > 0)
    ? computeSxEff(Sx, a, W, Q, S, n)
    : (isFinite(Sx) ? Sx : 0);
  const T     = (Q > 0 && SxEff > 0 && S > 0) ? computeSpread(Q, n, SxEff, S) : 0;
  const { Lt, E, bypass_frac } = (Q > 0 && isFinite(L) && L > 0)
    ? computeInterception(L, Q, S, n, SxEff, a)
    : { Lt: 0, E: 1, bypass_frac: 0 };
  const bypassQ  = Q * bypass_frac;
  const bypassCA = totalCA * bypass_frac;

  return {
    i, iComputed, Q, totalCA, isSump: false,
    SxEff, T, Lt, E, bypassFrac: bypass_frac,
    bypassQ, bypassCA,
    pickupPct: E * 100,
    allowT,
    warn: allowT > 0 && T > allowT,
  };
}
```

- [ ] **Step 7: Add oracle tests to `tests/run-tests.mjs`**

Add these tests **after** the smoke test. They verify the oracle rows from spec §5 (global params: W=1.33, a=0.0833, n=0.013, allowableSpread=8 ft; source=mdsha, storm=10yr):

```js
// Helper
function isClose(actual, expected, tol=0.01, msg="") {
  assert.ok(Math.abs(actual-expected) <= tol,
    `${msg}: expected ${expected}, got ${actual} (tol ${tol})`);
}

const W=1.33, a=0.0833, n=0.013;
const settings10 = { rainfallSource:"mdsha", storm:"10yr", county:"Montgomery",
                     allowableSpread:8, customNoaa:{} };

// --- interpolatePL ---
test("interpolatePL: exact breakpoint MDSHA 10yr at Tc=5", () => {
  isClose(sdc.lookupIntensity(5,"mdsha","10yr","",""), 6.684, 0.001, "i(5min,mdsha,10yr)");
});
test("interpolatePL: clamp below Tc=5", () => {
  isClose(sdc.lookupIntensity(3,"mdsha","10yr","",""), 6.684, 0.001, "clamped below");
});
test("interpolatePL: linear between MDSHA 10yr Tc=7", () => {
  // Between 5 (6.684) and 10 (5.340): 6.684 + (5.340-6.684)*((7-5)/(10-5)) = 6.684-0.5376=6.146
  isClose(sdc.lookupIntensity(7,"mdsha","10yr","",""), 6.146, 0.01);
});
test("interpolatePL: clamp above MDSHA 2yr Tc=60", () => {
  // MDSHA 2yr last breakpoint is 15min→3.364; clamp at 3.364
  isClose(sdc.lookupIntensity(60,"mdsha","2yr","",""), 3.364, 0.001);
});

// --- Oracle row I-1 ---
// L=5, CA=0.14289, bypassCA=0, Tc=7, i=6.15 (per spec, Tc=7 → i≈6.15), S=0.044, Sx=0.01
// Expected: T=4.10, Pickup=99.25%, bypassCA=0.00107
test("I-1: spread T=4.10", () => {
  const row = { S:"0.044", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"", C:"", tc:"7", iOverride:"6.15", allowableSpread:"" };
  // With iOverride=6.15, Q = 0.14289 * 6.15 = 0.8788
  const r = sdc.computeInletRow(
    { ...row, area:"0.14289", C:"1" },
    settings10, 0, 0
  );
  isClose(r.T, 4.10, 0.05, "I-1 spread");
});
test("I-1: pickup 99.25%", () => {
  const row = { S:"0.044", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.pickupPct, 99.25, 0.1, "I-1 pickup%");
});
test("I-1: bypassCA=0.00107", () => {
  const row = { S:"0.044", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.bypassCA, 0.00107, 0.001, "I-1 bypassCA");
});

// --- EX-I-1 (SUMP) ---
test("EX-I-1 SUMP: pickup=100, bypassCA=0", () => {
  const row = { S:"SUMP", Sx:"", W:1.33, a:0.0833, n:0.013, L:"11.1",
                area:"0.04667", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0.29169*6.68, 0.29169);
  assert.equal(r.pickupPct, 100, "SUMP pickup 100");
  assert.equal(r.bypassQ, 0, "SUMP bypassQ 0");
  isClose(r.Q, 2.260, 0.05, "EX-I-1 Q");
});

// --- Oracle rows I-2, I-3, I-6 ---
// Note: if T oracle values don't match within ±0.05 ft, open docs/bburg-p-c.xlsx
// and verify the spread formula columns (the workbook may use FlowMaster or a
// different gutter-depression shortcut). Adjust computeSxEff if needed.
test("I-2: pickup=100, bypassCA=0", () => {
  const row = { S:"0.0219", Sx:"0.0212", W:1.33, a:0.0833, n:0.013, L:"15",
                area:"0.18013", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.pickupPct, 100, 1, "I-2 pickup");
  isClose(r.bypassCA, 0, 0.001, "I-2 bypassCA");
});
test("I-6: spread≈5.20, pickup≈93.59%", () => {
  // Bypass CA in = 0.01004 (from upstream). Estimate bypass Q at i=5.34:
  const bypassQ = 0.01004 * 5.34;
  const row = { S:"0.026", Sx:"0.007", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.15669", C:"1", tc:"10", iOverride:"5.34", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, bypassQ, 0.01004);
  isClose(r.T, 5.20, 0.1, "I-6 spread");
  isClose(r.pickupPct, 93.59, 1, "I-6 pickup%");
});
```

Run with `cd tests && npm test`. Debug any failures against the workbook formulas before proceeding to the UI.

- [ ] **Step 8: Expose functions in `window.__sdc` (line 3397)**

Add to the `window.__sdc` object: `lookupIntensity, interpolatePL, computeSxEff, computeSpread, computeInterception, computeInletRow`. (Full list added after Task 11.)

---

### Task 5 — State model extension + tab skeleton

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Insert NOAA constants**

After the structure library constants (Task 3), insert the `NOAA_ATLAS14` and `NOAA_COUNTY_LIST` constants compiled in Task 2. Verify the object has exactly 25 keys and each has 3 storm entries with 5 duration values each.

- [ ] **Step 2: Extend `state` (line 608)**

In `const state = { ... }`, add after `outletShowGeometryDetail`:
```js
inletSpacing: [],
inletSpacingSettings: defaultInletSpacingSettings(),
```

- [ ] **Step 3: Add `defaultInletSpacingSettings()`**

Paste just before `const state = {` (line 608):
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

function defaultInletSpacingRow() {
  return {
    id: nextId(),
    label: "",
    structureType: "",  // INLET_STRUCTURES id or ""
    area: "",
    C: "",
    tc: "",
    iOverride: "",      // non-empty string overrides computed i
    S: "",              // longitudinal slope or "SUMP"
    Sx: "",
    W: 1.33,
    a: 0.0833,
    n: 0.013,
    L: "",
    allowableSpread: "", // blank = use global default
    bypassTo: "",        // label of downstream inlet to which bypass flows
  };
}
```

- [ ] **Step 4: Add the view div (line 490)**

After `<div class="view" id="view-kb"></div>`, add:
```html
<div class="view" id="view-inlet-spacing"></div>
```

- [ ] **Step 5: Add tab to TABS (line 1309)**

After `{id:"kb", label:"Kb Coefficients"}`, add:
```js
,{id:"inlet-spacing", label:"Inlet Spacing"}
```

- [ ] **Step 6: Add `renderInletSpacing()` call to `renderAll()` (line 2108)**

After `renderKb();` add:
```js
renderInletSpacing();
```

- [ ] **Step 7: Add `renderInletSpacing()` stub**

Add after `renderKb()` (line 2093):
```js
function renderInletSpacing(){
  const c = document.getElementById("view-inlet-spacing");
  if(!c) return;
  c.innerHTML = "";
  c.appendChild(el("h1",{}, "Inlet Spacing"));
  c.appendChild(el("p",{class:"view-desc"}, "Stub — see Task 6."));
}
```

- [ ] **Step 8: Verify the tab appears**

Open the HTML in a browser. Click tab 9 "Inlet Spacing" — it should show the stub text. Fix any errors in the browser console before continuing.

---

### Task 6 — Full Inlet Spacing UI

**File:** `drainage-calculator/storm-drain-design-calculator.html` — replace the `renderInletSpacing()` stub from Task 5 with the full implementation.

Build the function in sub-sections. The full function signature is:
```js
function renderInletSpacing() {
  const c = document.getElementById("view-inlet-spacing");
  c.innerHTML = "";
  const s = state.inletSpacingSettings;
  const rows = state.inletSpacing;
  // ... [all sections below go here in order]
}
```

- [ ] **Step 1: Page header + street input**

```js
c.appendChild(el("h1",{}, "Inlet Spacing"));
c.appendChild(el("p",{class:"view-desc"},
  "HEC-22 grate-inlet on-grade spacing with bypass carryover. Each inlet’s " +
  "total flow = local CA×i + upstream bypass Q. Spread and pickup efficiency " +
  "use the composite gutter method. Click ⤡ Detail for full calculation sheets."));

const globalSec = el("div",{class:"section"});
const globalHead = el("div",{class:"section-head"});
globalHead.appendChild(el("h2",{}, "Global Settings"));
```

- [ ] **Step 2: Global controls row (inside globalSec)**

Controls: Project Street (text input), Rainfall Source (select), County (select, visible only when source=noaa), Storm (select, options depend on source), Default Allowable Spread (number input). When source=noaa and county=Custom, show 5 custom i inputs for 5/10/15/30/60 min.

All inputs use pattern:
```js
el("input", {
  "data-focus-key": "is:global:FIELD",
  oninput: (e) => { s.FIELD = e.target.value; withFocusPreserved(renderAll); }
})
```

Rainfall source options: `[["noaa","NOAA Atlas 14 (per county)"],["mdsha","MDSHA Agency Table"],["moco","MoCo Agency Table"]]`

Storm options depend on source:
- noaa or mdsha: `[["2yr","2-year"],["10yr","10-year"],["25yr","25-year"]]`
- moco: `[["2yr","2-year"],["5yr","5-year"],["10yr","10-year"]]`

If `s.storm` is not valid for the current source (e.g., "5yr" when source is "mdsha"), default to "10yr" before rendering.

When county="Custom", show a sub-row with 5 number inputs labeled "5-min", "10-min", "15-min", "30-min", "60-min" for `s.customNoaa[5]` through `s.customNoaa[60]`.

When source="noaa" and county≠"Custom", show a note: `"County: [county] — intensities represent [lat,lon], pulled [date]. Values vary within the county; for project-specific accuracy use Custom."` (Pull lat/lon and date from `NOAA_ATLAS14[county]`.)

- [ ] **Step 3: Add row button**

```js
globalHead.appendChild(el("button",{class:"btn btn-sm", onclick:()=>{
  state.inletSpacing.push(defaultInletSpacingRow());
  withFocusPreserved(renderAll);
}}, "+ Add Inlet"));
globalSec.appendChild(globalHead);
// ... append global controls form ...
c.appendChild(globalSec);
```

- [ ] **Step 4: Inlet table**

Build the results chain first (bypass accumulation), then render. Call `computeInletChain(rows, s)` (written in Task 7) to get computed results for every row in topological order.

**Table columns (in order):**

| # | Column | Input/Output | Width |
|---|---|---|---|
| 1 | Label | Input text | 80px |
| 2 | Structure Type | Select (INLET_STRUCTURES + blank) | 140px |
| 3 | L (ft) | Input number | 60px |
| 4 | Area (ac) | Input number | 70px |
| 5 | C | Input number | 50px |
| 6 | Tc (min) | Input number | 60px |
| 7 | i (in/hr) | Input number (override), show computed in placeholder or secondary span | 80px |
| 8 | Q (cfs) | Output | 70px |
| 9 | S | Input text ("SUMP" or number) | 65px |
| 10 | Sx | Input number | 60px |
| 11 | W (ft) | Input number | 60px |
| 12 | a (ft) | Input number | 60px |
| 13 | n | Input number | 60px |
| 14 | Spread T (ft) | Output ("—" for SUMP) | 70px |
| 15 | Allowable T (ft) | Input number (blank = global) | 70px |
| 16 | Pickup % | Output | 65px |
| 17 | Bypass To | Select (other inlet labels + "—") | 100px |
| 18 | Bypass CA | Output | 70px |
| 19 | ⤢ Detail | Button | — |
| 20 | Del | Button | — |

**Row styling:** If `computed.warn` (T > allowable T), add class `"warn-row"` to the `<tr>` (you can add a CSS rule `.warn-row { background: rgba(220,50,50,0.12); }` in the `<style>` block).

**i column behavior:**
- If `row.iOverride` is non-empty: show its value in the input, add class `"i-override"` to the cell (add CSS `.i-override input { border-color: #f90; }`), and show the computed value as dim secondary text: `"auto: X.XX"`.
- If empty: show the computed i in the input's placeholder and leave value empty (so clearing always reverts).
- `oninput`: set `row.iOverride = e.target.value` then `withFocusPreserved(renderAll)`.

**Structure type selection:**
```js
el("select", {
  "data-focus-key": "is:"+row.id+":structureType",
  onchange: (e) => {
    row.structureType = e.target.value;
    const preset = INLET_STRUCTURES.find(s=>s.id===e.target.value);
    if (preset) {
      row.W = preset.W; row.a = preset.a; row.n = preset.n;
      if (preset.Ls && preset.Ls.length) row.L = String(preset.Ls[0]);
    }
    withFocusPreserved(renderAll);
  }
}, [el("option",{value:""},"— Select —"), ...INLET_STRUCTURES.map(s=>
  el("option",{value:s.id, selected:row.structureType===s.id},s.id+" "+s.label)
)])
```

**Bypass To dropdown:** Options are `"—"` (no bypass) plus the label of every OTHER inlet row. Store the target label (not id) so export/import round-trips correctly. On render, map label to downstream row for accumulation.

- [ ] **Step 5: Cycle warning banner**

After the table, if `computeInletChain` returns any cycle warnings, render them:
```js
const { cycles } = computeInletChain(rows, s);
cycles.forEach(msg => c.appendChild(el("div",{class:"note warn"}, msg)));
```

- [ ] **Step 6: Seed-only disclosure note**

After the table section, append:
```js
c.appendChild(el("div",{class:"note"},
  "Structure dimensions (L, W, a, n) are workbook-derived seed values and must be " +
  "verified against the governing MDSHA Book of Standards sheet before submittal."));
```

---

### Task 7 — Bypass chain computation + cycle detection

**File:** `drainage-calculator/storm-drain-design-calculator.html` (add alongside the computation functions from Task 4)

- [ ] **Step 1: `computeInletChain`**

```js
// Returns { results: Map<id, computedObj>, order: [id...], cycles: [string...] }
// Results are computed in topological order (upstream before downstream).
// Bypass Q and bypass CA accumulate correctly even across multi-hop chains.
function computeInletChain(rows, settings) {
  const byLabel = {};
  rows.forEach(r => { if(r.label) byLabel[r.label] = r; });

  // Build adjacency: row.id → downstream row.id (via bypassTo label)
  const downstream = {};  // id → id | null
  const upstream   = {};  // id → Set<id>
  rows.forEach(r => { upstream[r.id] = new Set(); });
  rows.forEach(r => {
    const tgt = r.bypassTo && byLabel[r.bypassTo];
    downstream[r.id] = tgt ? tgt.id : null;
    if (tgt) upstream[tgt.id].add(r.id);
  });

  // Kahn's topological sort with cycle detection
  const indegree = {};
  rows.forEach(r => indegree[r.id] = 0);
  rows.forEach(r => { const d = downstream[r.id]; if(d) indegree[d]++; });

  const queue = rows.filter(r => indegree[r.id] === 0).map(r => r.id);
  const order = [];
  while (queue.length) {
    const id = queue.shift();
    order.push(id);
    const d = downstream[id];
    if (d != null) {
      indegree[d]--;
      if (indegree[d] === 0) queue.push(d);
    }
  }

  // Nodes not in order are in a cycle
  const inOrder = new Set(order);
  const cycles = [];
  rows.forEach(r => {
    if (!inOrder.has(r.id)) {
      cycles.push(`Cycle detected involving inlet "${r.label||r.id}": bypass chain loops back.`);
    }
  });

  // Compute results in topological order
  const bypassQAcc  = {};  // id → accumulated bypass Q arriving
  const bypassCAAcc = {};  // id → accumulated bypass CA arriving
  rows.forEach(r => { bypassQAcc[r.id] = 0; bypassCAAcc[r.id] = 0; });

  const results = {};
  order.forEach(id => {
    const row = rows.find(r => r.id === id);
    if (!row) return;
    const comp = computeInletRow(row, settings, bypassQAcc[id], bypassCAAcc[id]);
    results[id] = comp;
    const d = downstream[id];
    if (d != null) {
      bypassQAcc[d]  += comp.bypassQ;
      bypassCAAcc[d] += comp.bypassCA;
    }
  });

  // For cyclic nodes, produce a zero placeholder so the UI doesn't crash
  rows.forEach(r => {
    if (!results[r.id]) {
      results[r.id] = { i:0, Q:0, isSump:false, SxEff:0, T:0, Lt:0, E:0,
                        bypassFrac:0, bypassQ:0, bypassCA:0, pickupPct:0,
                        allowT:0, warn:false, _cycle:true };
    }
  });

  return { results, order, cycles };
}
```

- [ ] **Step 2: Add test for chaining + cycle detection**

In `tests/run-tests.mjs`:

```js
test("bypass chain: 2-inlet chain conserves bypass CA", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"I-1", S:"0.044", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5",
               area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"", bypassTo:"I-2" };
  const r2 = { id:"r2", label:"I-2", S:"0.044", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"15",
               area:"0.1", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"", bypassTo:"" };
  const { results, cycles } = sdc.computeInletChain([r1,r2], s);
  assert.equal(cycles.length, 0, "no cycles");
  // r2 receives r1's bypass
  isClose(results["r2"].Q,
    (results["r1"].bypassQ + 0.1*6.15), 0.05,
    "r2 Q includes r1 bypass Q");
});

test("cycle detection flags circular chain", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"I-A", bypassTo:"I-B", S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5", area:"0.1", C:"1", tc:"5", iOverride:"", allowableSpread:"" };
  const r2 = { id:"r2", label:"I-B", bypassTo:"I-A", S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"5", area:"0.1", C:"1", tc:"5", iOverride:"", allowableSpread:"" };
  const { cycles } = sdc.computeInletChain([r1,r2], s);
  assert.ok(cycles.length > 0, "cycle should be flagged");
});

test("zero-area zero-bypass inlet: no NaN", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const row = { id:"r0", label:"I-0", bypassTo:"", S:"0.04", Sx:"0.02", W:1.33, a:0.0833, n:0.013, L:"10", area:"", C:"", tc:"5", iOverride:"", allowableSpread:"" };
  const r = sdc.computeInletRow(row, s, 0, 0);
  assert.ok(isFinite(r.Q) || r.Q===0, "Q must be finite or 0");
  assert.ok(!isNaN(r.T), "T must not be NaN");
});
```

---

### Task 8 — Per-inlet detail sheets

**File:** `drainage-calculator/storm-drain-design-calculator.html` (add alongside the print functions, after `buildPipeSheet`)

- [ ] **Step 1: `buildInletSpacingSheet(row, comp, settings)`**

```js
function buildInletSpacingSheet(row, comp, settings) {
  const s = settings;
  const title = "Inlet Spacing — " + (row.label || row.id);
  const root = el("div",{class:"calc-sheet"});
  root.appendChild(el("div",{class:"cs-title"}, title));

  // ---- Section 1: Global settings ----
  root.appendChild(csSection("Project Settings", el("div",{class:"cs-body"},[
    el("p",{}, "Project Street: " + (s.street||"—")),
    el("p",{}, "Rainfall Source: " + s.rainfallSource.toUpperCase() +
      (s.rainfallSource==="noaa" ? " (" + s.county + ")" : "")),
    el("p",{}, "Storm: " + s.storm),
    el("p",{}, "Default Allowable Spread: " + s.allowableSpread + " ft"),
  ])));

  // ---- Section 2: Inlet inputs ----
  root.appendChild(csSection("Inlet Inputs", el("div",{class:"cs-body"},[
    el("p",{}, "Label: " + (row.label||"—")),
    el("p",{}, "Structure Type: " + (row.structureType||"(none)")),
    el("p",{}, "Drainage Area: " + (row.area||"—") + " ac, C = " + (row.C||"—")),
    el("p",{}, "Tc = " + (row.tc||"—") + " min"),
    el("p",{}, "Grate: L = " + (row.L||"—") + " ft, W = " + row.W + " ft, a = " + row.a + " ft, n = " + row.n),
    el("p",{}, "S (longitudinal) = " + row.S + (comp.isSump ? " (SUMP)" : "")),
    el("p",{}, comp.isSump ? "Sx: N/A (sump)" : ("Sx (cross-slope) = " + row.Sx)),
    el("p",{}, "Allowable Spread: " + (row.allowableSpread || s.allowableSpread + " ft (global default)")),
    el("p",{}, "Bypass To: " + (row.bypassTo || "none")),
  ])));

  // ---- Section 3: Intensity ----
  const iOverridden = row.iOverride !== "" && row.iOverride != null && isFinite(Number(row.iOverride));
  root.appendChild(csSection("Design Intensity", el("div",{class:"cs-body"},[
    el("p",{}, "Source: " + (iOverridden ? "Manual override" : s.rainfallSource.toUpperCase()) +
      (iOverridden ? "" : (", Tc=" + row.tc + " min → curve → i_computed=" + comp.iComputed.toFixed(3) + " in/hr"))),
    el("p",{class: iOverridden?"note":""}, "i used = " + comp.i.toFixed(3) + " in/hr" +
      (iOverridden ? " (OVERRIDDEN — verify against NOAA/agency source)" : "")),
  ])));

  // ---- Section 4: Flow ----
  root.appendChild(csSection("Design Flow", el("div",{class:"cs-body"},[
    el("p",{}, "Q = (C × A) × i + Q_bypass_upstream"),
    el("p",{}, "Q = (" + (row.C||0) + " × " + (row.area||0) + ") × " + comp.i.toFixed(3) +
      " + " + (comp.Q - (Number(row.C||0)*Number(row.area||0)*comp.i)).toFixed(4)),
    el("p",{}, "Q = " + comp.Q.toFixed(4) + " cfs"),
  ])));

  if (comp.isSump) {
    root.appendChild(csSection("Sump Inlet", el("div",{class:"cs-body"},[
      el("p",{}, "Sump (S=SUMP): treated as 100% pickup, bypass = 0."),
      el("p",{}, "Spread: computed by FlowMaster or similar external tool, not shown here."),
    ])));
    return root;
  }

  // ---- Section 5: Composite gutter Sx_eff ----
  root.appendChild(csSection("Composite Gutter — Effective Cross-Slope", el("div",{class:"cs-body"},[
    el("p",{}, "V = (a + Sx·W)/W = (" + row.a + " + " + row.Sx + "×" + row.W + ")/" + row.W),
    el("p",{}, "Qw = (0.56/n)·V^1.667·S^0.5·W^2.667"),
    el("p",{}, "W_ratio = (a/(a+Sx·W))·(Qw/Q)"),
    el("p",{}, "Sx_eff = Sx + (a/W)·W_ratio = " + (comp.SxEff||0).toFixed(5)),
  ])));

  // ---- Section 6: Spread ----
  root.appendChild(csSection("On-Grade Spread (HEC-22)", el("div",{class:"cs-body"},[
    el("p",{}, "T = ((Q·n)/(0.56·Sx_eff^1.67·S^0.5))^0.3745"),
    el("p",{}, "T = ((" + comp.Q.toFixed(4) + "×" + row.n + ")/(0.56×" +
      (comp.SxEff||0).toFixed(5) + "^1.67×" + row.S + "^0.5))^0.3745"),
    el("p",{}, "T = " + (comp.T||0).toFixed(2) + " ft"),
    el("p",{class: comp.warn?"note warn":""},
      "Allowable T = " + comp.allowT + " ft — " + (comp.warn ? "⚠ EXCEEDS ALLOWABLE" : "OK")),
  ])));

  // ---- Section 7: Interception ----
  const k = !(Number(row.a)>0) ? 0.60 : (Number(row.L)>=15 ? 0.54 : 0.58);
  root.appendChild(csSection("Grate Interception", el("div",{class:"cs-body"},[
    el("p",{}, "k = " + k + " (L" + (Number(row.L)>=15?"≥15":"<15") + " ft" +
      (!(Number(row.a)>0)?", no depression":"")+")"),
    el("p",{}, "Lt = k·Q^0.42·S^0.3·(1/(n·Sx_eff))^0.6"),
    el("p",{}, "Lt = " + k + "×" + comp.Q.toFixed(4) + "^0.42×" +
      row.S + "^0.3×(1/(" + row.n + "×" + (comp.SxEff||0).toFixed(5) + "))^0.6"),
    el("p",{}, "Lt = " + (comp.Lt||0).toFixed(2) + " ft"),
    el("p",{}, Number(row.L) >= (comp.Lt||0) ?
      "L (≥ Lt) → E = 100% (no bypass)" :
      "E = 1 − (1 − L/Lt)^1.8 = 1 − (1 − " + (Number(row.L)/(comp.Lt||1)).toFixed(4) + ")^1.8 = " + (comp.E*100).toFixed(2) + "%"),
    el("p",{}, "Bypass Q = Q×(1−E) = " + comp.bypassQ.toFixed(4) + " cfs"),
    el("p",{}, "Bypass CA = CA_total×(1−E) = " + comp.bypassCA.toFixed(5)),
    el("p",{}, "Bypass To: " + (row.bypassTo||"none")),
  ])));

  return root;
}
```

- [ ] **Step 2: Wire ⤢ Detail button in the table row (from Task 6)**

In the inlet table, add a detail button (using the existing `detailBtn()` helper):
```js
detailBtn(() => {
  const comp = computedResults[row.id];
  openDetailModal(buildInletSpacingSheet(row, comp, s));
})
```

---

### Task 9 — Excel export + import

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add "Inlet Spacing" sheet to `buildWorkbook()` (after the Kb sheet, line ~3162)**

```js
// ---- Inlet Spacing ----
const isS = state.inletSpacingSettings;
const isRows = state.inletSpacing;
const isChain = computeInletChain(isRows, isS);
const isHeader = ["Label","Structure Type","L (ft)","Area (ac)","C","Tc (min)",
  "i Override (in/hr)","S","Sx","W (ft)","a (ft)","n","Allowable T (ft)","Bypass To",
  "Rainfall Source","County","Storm","Default Allowable Spread (ft)",
  // computed (exported as values for reference, ignored on import)
  "Computed i (in/hr)","Q (cfs)","Sx_eff","Spread T (ft)","Lt (ft)","Pickup %","Bypass CA out"];
const isAoa = [
  // Settings rows (prefix "# " so sheetToRows filters them out as header)
  ["# Project Street", isS.street],
  ["# Rainfall Source", isS.rainfallSource],
  ["# County", isS.county],
  ["# Storm", isS.storm],
  ["# Default Allowable Spread (ft)", isS.allowableSpread],
  ["# Custom NOAA 5-min", isS.customNoaa[5]||""],
  ["# Custom NOAA 10-min", isS.customNoaa[10]||""],
  ["# Custom NOAA 15-min", isS.customNoaa[15]||""],
  ["# Custom NOAA 30-min", isS.customNoaa[30]||""],
  ["# Custom NOAA 60-min", isS.customNoaa[60]||""],
  [], // blank row
  isHeader,
];
isRows.forEach(row => {
  const comp = isChain.results[row.id] || {};
  isAoa.push([
    row.label||"", row.structureType||"", row.L||"",
    row.area||"", row.C||"", row.tc||"", row.iOverride||"",
    row.S||"", row.Sx||"", row.W||"", row.a||"", row.n||"",
    row.allowableSpread||"", row.bypassTo||"",
    "","","","",  // rainfall source / county / storm / allowable spread: blank (stored in settings rows)
    round(comp.i||0,3), round(comp.Q||0,4), round(comp.SxEff||0,5),
    comp.isSump ? "" : round(comp.T||0,2),
    round(comp.Lt||0,2), round(comp.pickupPct||0,2), round(comp.bypassCA||0,5),
  ]);
});
const wsIs = XLSX.utils.aoa_to_sheet(isAoa);
wsIs["!cols"] = [{wch:10},{wch:14},{wch:7},{wch:8},{wch:5},{wch:7},{wch:14},
  {wch:7},{wch:7},{wch:7},{wch:7},{wch:6},{wch:12},{wch:10},
  {wch:0},{wch:0},{wch:0},{wch:0}, // hidden settings columns
  {wch:10},{wch:8},{wch:8},{wch:8},{wch:8},{wch:9},{wch:12}];
XLSX.utils.book_append_sheet(wb, wsIs, "Inlet Spacing");
```

- [ ] **Step 2: Read "Inlet Spacing" sheet in `importExcel()` (after the Kb import block, line ~3344)**

```js
// ---- Inlet Spacing ----
const isSheet = wb.Sheets["Inlet Spacing"];
if (isSheet) {
  const isAoaRaw = XLSX.utils.sheet_to_json(isSheet, {header:1, raw:true, defval:""});
  // Parse settings rows (rows starting with "# ")
  const newSettings = defaultInletSpacingSettings();
  const dataRows = [];
  let pastHeader = false;
  const headerCols = ["Label","Structure Type","L (ft)","Area (ac)"];
  isAoaRaw.forEach(r => {
    if (!pastHeader) {
      const cell0 = String(r[0]||"");
      if (cell0.startsWith("# Project Street")) newSettings.street = String(r[1]||"");
      else if (cell0.startsWith("# Rainfall Source")) newSettings.rainfallSource = r[1]||"noaa";
      else if (cell0.startsWith("# County")) newSettings.county = r[1]||"Montgomery";
      else if (cell0.startsWith("# Storm")) newSettings.storm = r[1]||"10yr";
      else if (cell0.startsWith("# Default Allow")) newSettings.allowableSpread = r[1]||8;
      else if (cell0.startsWith("# Custom NOAA 5")) newSettings.customNoaa[5] = r[1]||"";
      else if (cell0.startsWith("# Custom NOAA 10")) newSettings.customNoaa[10] = r[1]||"";
      else if (cell0.startsWith("# Custom NOAA 15")) newSettings.customNoaa[15] = r[1]||"";
      else if (cell0.startsWith("# Custom NOAA 30")) newSettings.customNoaa[30] = r[1]||"";
      else if (cell0.startsWith("# Custom NOAA 60")) newSettings.customNoaa[60] = r[1]||"";
      else if (String(r[0]||"").trim() === "Label") { pastHeader = true; } // data header row
    } else {
      if (r.some(v => v !== "" && v != null)) dataRows.push(r);
    }
  });
  if (pastHeader) {
    state.inletSpacingSettings = newSettings;
    state.inletSpacing = dataRows.map(r => {
      const row = defaultInletSpacingRow();
      row.label          = String(r[0]||"");
      row.structureType  = String(r[1]||"");
      row.L              = String(r[2]||"");
      row.area           = String(r[3]||"");
      row.C              = String(r[4]||"");
      row.tc             = String(r[5]||"");
      row.iOverride      = String(r[6]||"");
      row.S              = String(r[7]||"");
      row.Sx             = String(r[8]||"");
      row.W              = r[9]!==""&&r[9]!=null?r[9]:1.33;
      row.a              = r[10]!==""&&r[10]!=null?r[10]:0.0833;
      row.n              = r[11]!==""&&r[11]!=null?r[11]:0.013;
      row.allowableSpread= String(r[12]||"");
      row.bypassTo       = String(r[13]||"");
      return row;
    });
  }
}
```

- [ ] **Step 3: Add OOXML / round-trip tests in `tests/run-tests.mjs`**

```js
import XLSX from "xlsx";

test("buildWorkbook: Inlet Spacing sheet exists", () => {
  const wb = sdc.buildWorkbook();
  assert.ok(wb.SheetNames.includes("Inlet Spacing"), "Inlet Spacing sheet missing");
});
test("buildWorkbook: sharedStrings (bookSST)", () => {
  // bookSST produces shared strings; verify no t='str' without formula
  const wb = sdc.buildWorkbook();
  // We can't easily check SharedStrings here without actually writing to file,
  // so check that no cell has t='str' without an f property
  wb.SheetNames.forEach(name => {
    const ws = wb.Sheets[name];
    Object.keys(ws).filter(k=>!k.startsWith("!")).forEach(addr => {
      const cell = ws[addr];
      if (cell.t === "str" && !cell.f) {
        assert.fail(`Sheet "${name}" cell ${addr}: t='str' without formula (spec violation)`);
      }
    });
  });
});
```

---

### Task 10 — Kb tab MoCo preset button

**File:** `drainage-calculator/storm-drain-design-calculator.html` — modify `renderKb()` (line 2053)

- [ ] **Step 1: Insert "Load MoCo preset" button**

In `renderKb()`, in the section-head div where the "Reset to default" button is (line 2064), add a "Load MoCo preset" button before "Reset to default":

```js
el("button",{
  class:"btn btn-sm",
  style:"margin-right:8px;",
  title:"Overwrites the current Kb table with MoCo angle vs. Kb values (0°–38°). "+
        "Generic AASHTO seed remains the fresh-load default.",
  onclick:()=>{
    state.kb = MOCO_KB_PRESET.map(r=>({
      angle: String(r.angle), inlet: String(r.inlet),
      manhole: String(r.manhole), bend: String(r.bend)
    }));
    renderAll();
    toast("Kb table loaded with MoCo preset values (0°–38°). Edit as needed.");
  }
}, "Load MoCo preset"),
```

- [ ] **Step 2: Verify button appears and loads correct values**

Open the browser, navigate to Kb Coefficients tab, click "Load MoCo preset". Verify the table replaces with the MoCo values (angles 0°–38°, Inlet ~0.50–0.98, Manhole ~0.15–0.66, Bend ~0.01–0.16). Click "Reset to default" to confirm that still restores the AASHTO seed. Export to Excel; import back; verify MoCo values round-trip.

---

### Task 11 — Print All, Overview description, and `__sdc` exposure

**File:** `drainage-calculator/storm-drain-design-calculator.html`

- [ ] **Step 1: Add inlet spacing sheets to `printAllSheets()` (line 2815)**

After the outlet structure rows:
```js
if (state.inletSpacing.length) {
  const chain = computeInletChain(state.inletSpacing, state.inletSpacingSettings);
  state.inletSpacing.forEach(row => {
    const comp = chain.results[row.id];
    if (comp) nodes.push(buildInletSpacingSheet(row, comp, state.inletSpacingSettings));
  });
}
```

- [ ] **Step 2: Add step 8 to `renderOverview()` (line 1338)**

In the `steps` array inside `renderOverview()`, append:
```js
,["8","Inlet Spacing — HEC-22 Grate Inlet Analysis",
  "Standalone inlet spacing tab: enter tributary CA, Tc, longitudinal/cross slope, and grate dimensions per inlet. Chooses intensity from NOAA Atlas 14 (county-selectable), MDSHA, or MoCo agency curves — or a per-row manual override. Computes spread, grate interception efficiency, and bypass carryover through a chain of inlets. SUMP inlets get 100% pickup. Spread > allowable is flagged.",
  "", ""]
```

- [ ] **Step 3: Expose new functions in `window.__sdc` (line 3397)**

Extend the `window.__sdc` object to include:
```js
lookupIntensity, interpolatePL, computeSxEff, computeSpread,
computeInterception, computeInletRow, computeInletChain,
buildInletSpacingSheet, MDSHA_INTENSITY, MOCO_INTENSITY,
NOAA_ATLAS14, NOAA_COUNTY_LIST, INLET_STRUCTURES, MOCO_KB_PRESET,
defaultInletSpacingSettings, defaultInletSpacingRow
```

---

### Task 12 — Full oracle test run + final integration check

- [ ] **Step 1: Run all tests**

```powershell
cd tests && npm test
```

All tests must pass. For any failing oracle test, open `docs/bburg-p-c.xlsx`, navigate to the "Inlet Spacing_10-yr" sheet, and inspect the relevant formula column (Cols U–Z for spread/Lt/E). If the workbook uses FlowMaster-supplied spread (not a formula), note it in a comment in the code.

**Known risk:** Oracle rows I-2 and I-3 have large Sx values (0.0212 and 0.08 respectively). If T oracle values don't match within ±0.05 ft, the spread formula may need adjustment. Investigate the actual workbook spread formula before changing the implementation.

- [ ] **Step 2: Edge-case tests (add to `tests/run-tests.mjs`)**

```js
// Edge case: grate L >= Lt → exactly 100%, no divide-by-zero
test("L >= Lt → E=1, bypass_frac=0", () => {
  const row = { S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"50",
                area:"0.1", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  assert.equal(r.E, 1, "E should be 1 when L>=Lt");
  assert.equal(r.bypassFrac, 0);
  assert.equal(r.bypassCA, 0);
});

// Edge case: SUMP mid-chain gets downstream bypass passed through (bypassCA=0 from sump)
test("SUMP mid-chain: downstream gets 0 bypass from SUMP", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"I-S", S:"SUMP", Sx:"", W:1.33, a:0.0833, n:0.013, L:"10",
               area:"0.1", C:"1", tc:"5", iOverride:"6.68", bypassTo:"I-2", allowableSpread:"" };
  const r2 = { id:"r2", label:"I-2", S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"10",
               area:"0.1", C:"1", tc:"5", iOverride:"6.68", bypassTo:"", allowableSpread:"" };
  const { results } = sdc.computeInletChain([r1,r2], s);
  assert.equal(results["r1"].bypassCA, 0, "sump bypass CA = 0");
  assert.equal(results["r1"].bypassQ, 0, "sump bypass Q = 0");
  assert.ok(isFinite(results["r2"].T), "downstream T is finite");
});

// NOAA county switching
test("NOAA: switching county changes computed i", () => {
  const iA = sdc.lookupIntensity(10,"noaa","10yr","Montgomery",{});
  const iB = sdc.lookupIntensity(10,"noaa","10yr","Garrett",{});
  assert.notEqual(iA, iB, "different counties should give different intensities");
});

// NOAA: all 25 jurisdictions present with 3 storms × 5 durations
test("NOAA data completeness: 25 jurisdictions, 3 storms, 5 durations", () => {
  const jursCount = Object.keys(sdc.NOAA_ATLAS14).length;
  assert.equal(jursCount, 25, `expected 25, got ${jursCount}`);
  for (const [county, data] of Object.entries(sdc.NOAA_ATLAS14)) {
    ["2yr","10yr","25yr"].forEach(storm => {
      assert.ok(data[storm], `${county} missing ${storm}`);
      [5,10,15,30,60].forEach(d => {
        assert.ok(isFinite(data[storm][d]) && data[storm][d] > 0,
          `${county} ${storm} ${d}-min: ${data[storm][d]}`);
      });
    });
  }
});
```

- [ ] **Step 3: Manual browser integration check**

Open the HTML file locally. Walk through this checklist:
1. Navigate to Inlet Spacing tab — tab appears, stub or full UI shows with no console errors.
2. Add 3 inlets; set I-1 bypass to I-2, I-2 bypass to I-3. Verify bypass CA propagates (I-3 shows non-zero incoming bypass).
3. Create a cycle (I-3 bypass to I-1) — warning banner appears, no browser hang.
4. Set one inlet to SUMP — Spread column shows "—", Pickup shows "100%".
5. Select NOAA source, pick a county, change storm — i values in table change.
6. Select MDSHA source — county dropdown hides.
7. Enter i override on one row — cell shows yellow border, "auto: X.XX" dim text appears.
8. Click ⤢ Detail on a non-SUMP row — calc sheet modal opens with full formula trace.
9. Click ⤢ Detail → "Print all" — inlet spacing sheets appear in print set.
10. Export to Excel — file downloads; open it, verify "Inlet Spacing" sheet has settings rows and data rows with computed columns filled.
11. Import the file back — state restores correctly (street, county, all row inputs, bypass chain).
12. Kb Coefficients tab → "Load MoCo preset" — table replaces; "Reset to default" restores AASHTO seed.
13. Overview tab — shows step 8 for Inlet Spacing.

- [ ] **Step 4: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator.html tests/package.json tests/run-tests.mjs
git commit -m "Add inlet spacing calculator: HEC-22 grate inlet, NOAA Atlas 14, SHA/MoCo curves, bypass chain, detail sheets, Excel export/import"
```

(Per project memory: no Co-Authored-By trailer in the commit message.)

---

## Self-Review

- **Spec coverage:** Design §1 (hydrology/flow) → Tasks 3–4; §1.1 intensity → Task 3; §1.2 spread → Task 4 step 3–4; §1.3 interception → Task 4 step 5; §2 structure library → Task 3 step 3; §3.1 tab layout → Task 6; §3.2 chaining → Task 7; §3.3 detail sheets → Task 8; Excel export → Task 9; Kb preset → Task 10; §4 integration → Task 11.
- **Oracle tests:** Spec §5 oracle rows covered in Task 4 step 7 (I-1 T/pickup/bypassCA; EX-I-1 SUMP Q/pickup/bypass; I-2 and I-6 pickup); edge cases covered in Task 12 step 2.
- **Single-file rule:** All JS/CSS changes go inside the IIFE in the HTML. Tests in `tests/` are not part of the deliverable HTML.
- **withFocusPreserved:** Every `oninput` in Task 6 uses it. Every input has `data-focus-key`.
- **bookSST:** `exportExcel()` already passes `{ bookSST: true }` at line 3171; no change needed.
- **No localStorage:** Default state from `defaultInletSpacingSettings()` and `[]`; persistence via export/import only.
- **NOAA provenance:** Task 2 requires recording lat/lon and pull date in the constant; spot-check requirement documented.
- **Dimension disclosure:** `seedOnly: true` flag on all library entries; UI shows disclosure note (Task 6 step 6).
- **MoCo storm mismatch:** When source="moco", storm selector only shows 2yr/5yr/10yr; 25yr option removed. When switching away from moco while storm="5yr", revert to "10yr".

# Rainfall & IDF Tab — Design Spec

## 1. Goal

Add a shared "Rainfall & IDF" tab that centralizes all rainfall settings for the project. Extract
source/county/storm settings from `inletSpacingSettings` into a new `state.rainfall` shared object.
Update the Drainage Area tab to show CA + multi-return-period Q values (Q₂, Q₁₀, Q₂₅) computed from
the shared settings rather than a manual `i` field. Add an optional 25-yr check that gates two new
read-only tabs (Pipe Sizing — 25-yr, Junction Structures — 25-yr). The existing Pipe Sizing and
Junction Structures tabs remain the primary 10-yr design and are unchanged in behavior.

---

## 2. State Changes

### 2.1 New `state.rainfall`

```js
function defaultRainfallSettings() {
  return {
    rainfallSource: "noaa",    // "noaa" | "mdsha" | "moco"
    county: "Montgomery",      // key in NOAA_ATLAS14 or "Custom"
    customNoaa: { 5:"", 10:"", 15:"", 30:"", 60:"" },
    pipeStorm:   "10yr",       // primary pipe/HGL design storm
    pipe25Check: false,        // true = unlock 25-yr check tabs
    inletStorm:  "2yr",        // inlet spacing design storm
  };
}
```

Add to `const state = { ... }`:
```js
rainfall: defaultRainfallSettings(),
```

### 2.2 Strip `inletSpacingSettings`

Remove from `defaultInletSpacingSettings()`: `rainfallSource`, `county`, `storm`, `customNoaa`.
Keep: `street`, `allowableSpread`.

### 2.3 Drainage area row model

Remove field: `i` (was manual intensity input).
Add field: `iOverride: ""` — non-empty string overrides auto-computed intensity for that row.

**Import migration:** if an imported row has a numeric `i` and no `iOverride`, move `i` → `iOverride`
so no existing calculation breaks silently.

---

## 3. Rainfall & IDF Tab

**Tab ID:** `"rainfall"` — inserted as tab 2 (after Overview, before Drainage Area).

### 3.1 Settings section

- **Rainfall Source** dropdown: `[["noaa","NOAA Atlas 14 (per county)"],["mdsha","MDSHA Agency Table"],["moco","MoCo Agency Table"]]`
- **County** dropdown (NOAA only): `NOAA_COUNTY_LIST` + `"Custom"` option at bottom
- **Custom intensity inputs** (NOAA + Custom only): 5 number inputs labeled 5-min, 10-min, 15-min, 30-min, 60-min (in/hr), stored in `customNoaa`
- **NOAA validation link** (NOAA, non-Custom only):
  ```html
  <a href="https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py?type=pf&units=us&series=pds&statename=STATE&lat=LAT&lon=LON" target="_blank">
    Validate on NOAA Atlas 14 ↗
  </a>
  ```
  `LAT`/`LON` from `NOAA_ATLAS14[county].lat/lon`; `statename=dc` when county="DC", `statename=maryland` otherwise. Link updates live as county changes.
- **County point note** (NOAA, non-Custom): dim secondary text — `"Represents lat LAT, lon LON (county centroid, pulled 2026-09-09). Values vary within the county; use Custom for project-specific accuracy."`

### 3.2 Design Storms section

Two labeled dropdowns side by side, then a checkbox:

| Control | Field | Available options |
|---|---|---|
| Pipe & HGL Design Storm | `pipeStorm` | NOAA/MDSHA: 2yr, 10yr, 25yr · MoCo: 2yr, 5yr, 10yr |
| Inlet Design Storm | `inletStorm` | same filtering as pipeStorm |
| Also compute 25-yr pipe & HGL check | `pipe25Check` (checkbox) | hidden when `pipeStorm === "25yr"` |

**Storm coercion on source change:** if `pipeStorm` or `inletStorm` is not valid for the new source
(e.g., "5yr" when switching away from MoCo), reset to "10yr".

### 3.3 IDF Reference Table

**Header:** `"Intensity Reference — [source label] / [county or agency]"`

**Rows:** standard Tc values `[5, 7, 10, 15, 20, 30, 60]` min, plus one user-editable "Custom Tc"
row at the bottom (number input; row hidden until user types a value).

**Columns:** one per storm available for the active source:
- NOAA / MDSHA: 2-yr, 10-yr, 25-yr
- MoCo: 2-yr, 5-yr, 10-yr

Each cell value: `lookupIntensity(tc, source, storm, county, customNoaa).toFixed(2)` in/hr.

**Column accent styling:**
- `pipeStorm` column header: blue accent (`#4a9eff` or theme blue)
- `inletStorm` column header: amber accent (`#f0a500`)
- If both storms are the same column, use blue only

---

## 4. Drainage Area Tab Changes

### 4.1 `calcDrainageRow` — revised

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
    return lookupIntensity(tc, r.rainfallSource, storm, r.county, r.customNoaa);
  }

  const storms = availableStorms(r.rainfallSource);
  const Qs = {};
  storms.forEach(s => { Qs[s] = cf * CA * intensityFor(s); });

  return { CA, cf, A, C, Qs, storms, designQ: Qs[r.pipeStorm] || 0, iOverridden };
}

// Returns storm list for a source
function availableStorms(src) {
  return src === "moco" ? ["2yr","5yr","10yr"] : ["2yr","10yr","25yr"];
}
```

### 4.2 Table columns (revised)

Remove: `i (in/hr)` input column.

New column order after C:

| Column | Type | Notes |
|---|---|---|
| CA | computed | C × A, read-only |
| i override | input, 60px | blank = auto; non-empty = orange border, placeholder "auto" |
| Q₂ (cfs) | computed | |
| Q₁₀ (cfs) | computed | or Q₅ for MoCo |
| Q₂₅ (cfs) | computed | or Q₁₀ for MoCo |

The `pipeStorm` Q column header gets a blue-tinted background to indicate it drives downstream flow.
If `iOverride` is set, all Q columns show the override intensity; a dim note "i overridden" appears.

### 4.3 `+ Add row` default

```js
{ id:nextId(), structureId:"", desc:"", area:"", C:"", iOverride:"", tc:"", cf:1.0,
  tcMethod:"direct", tr55:{segments:[]} }
```

No `i` field.

### 4.4 Structure total flow

`computeTotalFlow()` calls `calcDrainageRow(da).Q` → change to `calcDrainageRow(da).designQ`.
No other change needed — everything downstream (pipe sizing, HGL) updates automatically.

### 4.5 Detail sheet update

Replace the single "Rainfall intensity, i = X in/hr" line with:
- Source, county, design storm used
- Computed i at row Tc (or "overridden" note)
- CA value
- Mini table of all Q values (Q₂, Q₁₀, Q₂₅)
- Highlighted design Q = `Q_{pipeStorm}`

---

## 5. Inlet Spacing Tab Changes

### 5.1 Remove from global settings UI

Strip from `renderInletSpacing()` global controls row: source dropdown, county dropdown, storm
dropdown, custom NOAA inputs, county note. Keep only: Street input, Default Allowable Spread input.

### 5.2 Rewire computation calls

`computeInletRow` and `computeInletChain` currently read `settings.rainfallSource/county/storm/customNoaa`.
Pass `state.rainfall` with `storm` overridden to `state.rainfall.inletStorm`:

```js
const inletRainfallCtx = {
  rainfallSource: state.rainfall.rainfallSource,
  county:         state.rainfall.county,
  customNoaa:     state.rainfall.customNoaa,
  storm:          state.rainfall.inletStorm,
  allowableSpread: state.inletSpacingSettings.allowableSpread,
};
// pass inletRainfallCtx as settings to computeInletChain / computeInletRow
```

### 5.3 Detail sheet

Update "Rainfall Source" and "Storm" lines to read from `state.rainfall`, showing `inletStorm`.

### 5.4 Excel export / import for Inlet Spacing sheet

Remove settings rows (`# Rainfall Source`, `# County`, `# Storm`, `# Custom NOAA …`) — these now
live in the Rainfall Settings sheet. Import reads rainfall from that sheet first.

---

## 6. 25-yr Check Tabs

Visible only when `state.rainfall.pipe25Check === true` AND `state.rainfall.pipeStorm !== "25yr"`.

**Tab IDs / labels:**
- `"pipe-sizing-25"` → `"Pipe Sizing — 25-yr"`
- `"structures-25"` → `"Junction Structures — 25-yr"`

Both tabs are entirely read-only (no inputs, no detail buttons). A banner at the top of each:
`"25-yr check — read only. Geometry is unchanged from the primary design tab."`

### 6.1 Pipe Sizing — 25-yr

Mirrors the existing Pipe Sizing table. Design Q for each pipe uses `calcDrainageRow(da).Qs["25yr"]`
accumulated through `computeTotalFlow` (a new overload that accepts a storm override argument, or a
thin wrapper that temporarily reads `Qs["25yr"]`). All pipe geometry (n, slope, length, shape, size)
is identical to the primary tab.

**Implementation approach for Q₂₅ accumulation:** add an optional `stormOverride` parameter to
`computeTotalFlow(structureId, seen, stormOverride)`. When provided, `calcDrainageRow(da)` is called
with a temporary context that reads `Qs[stormOverride]` instead of `designQ`. The 25-yr tab calls
`computeTotalFlow(structureId, seen, "25yr")`. The primary tab continues to call it with no override.

Show: Design Q, capacity, velocity, friction slope, Hf — same columns as primary tab.

### 6.2 Junction Structures — 25-yr

Mirrors the existing Junction Structures table. HGL propagation uses Q₂₅ flows. Same structure
elevations, crown, rim.

Pass/fail checks:
- HGL > crown + 1.0 ft → warn (pipe pressurized)
- HGL > rim − 1.0 ft → red error cell (surface flooding under 25-yr)

Show same columns as primary tab.

---

## 7. Tab Order (complete)

| # | ID | Label | Visibility |
|---|---|---|---|
| 1 | overview | Overview | always |
| 2 | rainfall | Rainfall & IDF | always |
| 3 | drainage | Drainage Area (Q=CiA) | always |
| 4 | structures | Junction Structures | always |
| 5 | pipes | Pipe Sizing | always |
| 6 | outlet | Outlet Structure | always |
| 7 | formulas | Formulas & Examples | always |
| 8 | table46 | Table 4-6 Reference | always |
| 9 | kb | Kb Coefficients | always |
| 10 | inlet-spacing | Inlet Spacing | always |
| 11 | pipe-sizing-25 | Pipe Sizing — 25-yr | `pipe25Check && pipeStorm !== "25yr"` |
| 12 | structures-25 | Junction Structures — 25-yr | `pipe25Check && pipeStorm !== "25yr"` |

**`TABS` becomes a computed function** — replace the static `const TABS = [...]` with
`function getTabs()` that returns the array, appending tabs 11–12 only when conditions are met.
All callers of `TABS` (tab bar render, `renderAll`, label lookup) switch to `getTabs()`.
View divs for tabs 11–12 (`<div class="view" id="view-pipe-sizing-25">` and
`<div class="view" id="view-structures-25">`) are always present in the HTML; only their
tab buttons are conditional. If `state.active` is a hidden tab when conditions change,
reset `state.active` to `"pipes"` before re-rendering.

---

## 8. Excel Export / Import

### 8.1 New "Rainfall Settings" sheet

Key-value pairs (2 columns):

| Key | Value |
|---|---|
| Rainfall Source | noaa |
| County | Montgomery |
| Pipe & HGL Design Storm | 10yr |
| 25-yr Check | FALSE |
| Inlet Design Storm | 2yr |
| Custom NOAA 5-min (in/hr) | |
| Custom NOAA 10-min (in/hr) | |
| Custom NOAA 15-min (in/hr) | |
| Custom NOAA 30-min (in/hr) | |
| Custom NOAA 60-min (in/hr) | |

Inserted as the second sheet in the workbook (after the existing Project Info sheet if present, before Drainage Area).

### 8.2 Drainage Area sheet changes

- Remove `i (in/hr)` column
- Add `CA` column (computed, static export value)
- Add `i Override (in/hr)` column (input; blank = auto)
- Add storm Q columns: `Q_2yr (cfs)`, `Q_10yr (cfs)`, `Q_25yr (cfs)` (or `Q_5yr` for MoCo) — static values for reference

Import: if a row has `i` column with a numeric value and `i Override` is blank, move value to `i Override`.

### 8.3 Inlet Spacing sheet changes

Remove settings rows: `# Rainfall Source`, `# County`, `# Storm`, `# Custom NOAA ...`.
Import reads those from the Rainfall Settings sheet instead.

---

## 9. Known Limitations (out of scope)

- **Cumulative CA + pipe travel time Tc:** Proper rational-method pipe sizing for a networked system
  uses a composite system Tc (longest upstream flow path + pipe travel times). The tool sums individual
  drainage area Q values at their own per-row Tc. Not addressed in this feature.
- **25-yr check tabs:** No detail sheets, no Print All integration, no Excel export of 25-yr results.
  Can be added in a follow-on pass.
- **MDSHA breakpoint clamping:** MDSHA has breakpoints only at 5/10/15 min (2-yr) and 5/10/15/30 min
  (10-yr, 25-yr). Tc values outside these ranges clamp at the nearest endpoint per `interpolatePL`.

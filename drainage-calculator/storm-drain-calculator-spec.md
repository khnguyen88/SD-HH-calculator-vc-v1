# Storm Drain Design Calculator — Build Specification

A single-file, offline HTML/CSS/JS engineering tool covering storm drain conveyance design (Rational Method → TR-55 time of concentration → Manning's → hydraulic grade line) and BMP/SWM/ESD outlet control structure rating curves, with two-way Excel export/import and a printable calculation-sheet system.

This spec is written as a sequence of buildable phases, not one giant prompt. Feed them to a coding agent one at a time, letting each phase get tested before starting the next — that's how this tool was actually built, and the phased approach is what let real bugs get caught early instead of compounding. Section 8 lists the specific bugs that came up during the real build; skipping straight to the full spec without testing in between is the most likely way to reintroduce them.

---

## 0. Non-negotiable constraints (state these up front, every phase)

- **Single HTML file.** Inline `<style>` and inline `<script>` blocks. No build step, no bundler, no CDN references of any kind — the file must open by double-clicking it with no internet connection.
- **Vanilla JS only.** No React/Vue/framework. DOM built via a small hand-rolled helper (Section 3).
- **Excel support via SheetJS, bundled inline as raw JS text inside a `<script>` tag** — not loaded from a CDN. Use the **`xlsx.full.min.js`** distributable, not `xlsx.core.min.js` (Section 7 explains why the core build silently produces invalid files).
- **No localStorage/sessionStorage.** Persistence is via explicit Export/Import to `.xlsx` only.
- **Dark, data-dense, professional engineering-tool aesthetic** — this is a calc-sheet browser, not a marketing page. Monospace font for all numeric values and inputs. System font stack only (no web fonts — offline requirement).
- Every computed value shown anywhere in the app must be traceable to one governing equation, and that equation must be the same one used to build the Excel export. Never let the two drift.

---

## Phase 1 — Core conveyance network: Drainage Area → Junction Structure → Pipe

### 1.1 Data model

**Drainage Area** (one row per catchment)
```
id, structureId (user label), desc, area (ac), C, i (in/hr), tc (min), cf (default 1.0)
Q = Cf × C × i × A
```

**Junction Structure** (one row per physical structure — the network's nodes)
```
id, structureId, desc, drainageAreaId (optional link to a Drainage Area),
type: inlet | manhole | bend | junction | outfall,
forceElev (bool), startElev, crown, rim
```
- `drainageAreaId` links a structure to its own local catchment for "captured" runoff.
- `forceElev` + `startElev`: this structure's elevation is fixed (used for the outfall, or any point with a known tailwater, e.g. connection to an existing system or a SWM pond).
- **Total Flow = Captured Q (from linked Drainage Area, 0 if none) + Σ(Q carried by every pipe whose To-Structure is this structure).** This is computed recursively — see 1.3.

**Pipe** (connects exactly two structures — this is the key modeling decision)
```
id, fromStructureId, toStructureId, angle (deg), shape: circular | elliptical,
size (in, or "SPANxRISE" for elliptical), n, slope (ft/ft), length (ft)
```
- `angle` is the deflection this pipe makes **entering its To-structure**, relative to whatever continues out of that structure — this is what drives structure-loss calculations at the To-structure, not a property of the structure itself.
- **Design Q is never typed in manually.** It's pulled live as the From-structure's Total Flow (Phase 3 modifies this for flow splitters).
- A structure normally has **one** outgoing pipe (the standard converging storm-drain tree) and **any number** of incoming pipes.

### 1.2 Manning's Equation (pipe sizing)
```
A = π/4 × D²                         (D in ft; for elliptical, look up from Table 4-6, Section 1.5)
R = D/4                              (hydraulic radius, full flow)
V = (1.486/n) × R^(2/3) × S^(1/2)    (full-flow velocity)
Qfull = V × A
Adequate if Qfull ≥ Design Q
```

### 1.3 Recursive Total Flow (implement with cycle protection)
```js
function computeTotalFlow(structureId, seen = new Set()) {
  if (seen.has(structureId)) return { Q: 0, error: "circular" };  // guard against bad data
  const nextSeen = new Set(seen); nextSeen.add(structureId);
  const captured = capturedQFor(structure);
  const inflow = incomingPipes(structureId).map(p => pipeDesignQ(p, nextSeen));
  return { Q: captured + sum(inflow), captured, inflow };
}
```
`pipeDesignQ(pipe, seen)` normally just returns `computeTotalFlow(pipe.fromStructureId, seen).Q` — Phase 3 adds a branch for flow-splitter sources. **This indirection matters**: an earlier, buggier version called `computeTotalFlow` directly instead of going through `pipeDesignQ`, which silently double-counted flow once splitters existed. Route every inflow contribution through `pipeDesignQ`, never around it.

### 1.4 Hydraulic Grade Line / structure loss — the controlling-angle method

Friction loss along a pipe (uses that pipe's own carried Q, not the structure's total):
```
Sf = ( Q×n / (1.486 × A × R^(2/3)) )²
Hf = Sf × L
```

Structure loss depends on how many pipes flow **into** the structure:
- **0 inflow pipes** (headwater): `Kb` evaluated at 0° (nominal entrance condition).
- **1 inflow pipe**: `Kb` at that pipe's own angle.
- **2 inflow pipes** — the controlling-angle method:
  ```
  V1/3 = Q1 / Aout        V2/3 = Q2 / Aout        (Aout = area of the structure's outgoing pipe)
  Lv1 = Kb(θ1) × V1/3² / 2g
  Lv2 = Kb(θ2) × V2/3² / 2g
  if Lv1 > Lv2:  θc = θ2      else:  θc = θ1       (the SMALLER loss's angle controls — not the larger)
  Vout = TotalFlow / Aout
  Hb = Kb(θc) × Vout² / 2g
  ```
- **>2 inflow pipes**: not supported by this method — flag it, don't guess.

`Kb` comes from an editable Angle-vs-Kb lookup table (see 1.6), linearly interpolated, with separate columns for Inlet / Manhole / Bend structure types (a "Junction" type reuses the Bend column).

Elevation propagates upstream recursively: a structure with `forceElev` (or no outgoing pipe) uses its own `startElev`; otherwise `elevation = computeStructureCalc(downstreamStructure).elevation + Hf + Hb`. Check against `elevation ≤ crown + 1.0 ft` and `elevation ≤ rim − 1.0 ft`.

### 1.5 Table 4-6 — Elliptical/Circular pipe equivalency (static reference data)
A fixed lookup table: circular diameter (in) / circular area (sf) / elliptical span×rise (in) / elliptical area (sf). Used to size elliptical pipes by nearest-match, pulling both area and an equivalent circular diameter (for computing R in Manning's equation). Ship the actual AASHTO/state-DOT-style table values; don't invent them. A representative excerpt (full table has ~24 rows from 15" to 144"):

| Circular Dia (in) | Circular Area (sf) | Elliptical Span×Rise (in) | Elliptical Area (sf) |
|---|---|---|---|
| 18 | 1.77 | 23×14 | 1.8 |
| 30 | 4.91 | 38×24 | 6.3 |
| 60 | 19.63 | 76×48 | 20.5 |
| 96 | 50.27 | 121×77 | 52.4 |

### 1.6 Kb Coefficients (editable reference table)
Angle (deg) vs Kb for Inlet / Manhole / Bend, linearly interpolated between rows, clamped at the table's endpoints. Seed **all three columns with the same standard AASHTO bend-loss curve** (12 rows, 5°→0.06 through 90°→0.70) — Inlet, Manhole, and Bend alike — and let the user override every cell. The as-built default is deliberately conservative: it does not silently pretend the agency-specific differences between inlet, manhole, and bend losses are known; the UI says so explicitly and the user is expected to enter their governing Appendix B chart's values per column before relying on results for submittal. Column use: Inlet reads `inlet`, Manhole reads `manhole`, Bend and Junction read `bend`, Flow Splitter reads `manhole`, Outfall has no structure loss. — different governing agencies publish different values, and the tool should never silently assume its defaults are correct for the user's jurisdiction. Say so in the UI.

### 1.7 Tabs for this phase
Overview, Drainage Area, Junction Structures, Pipe Sizing, Table 4-6 Reference, Kb Coefficients.

(The full tool ends with 8 tabs — the six above, plus **Outlet Structure** and **Formulas & Examples**, added by Phases 3–6 — but Phase 1 builds only the six listed here.)

---

## Phase 1B — TR-55 Segmental Time of Concentration

NRCS TR-55 (1986) Chapter 3 / Worksheet 3. Each Drainage Area row gets a Tc method toggle:

- `tcMethod: "direct" | "tr55"`. `direct` (default) = user types Tc in minutes.
  `tr55` = Tc is computed from a per-row segment list and becomes read-only
  in the main table (with an "Edit TR-55" button to reopen the modal and a
  "⇠ Direct entry" button to discard segments and revert).

### 1B.1 Segments
`row.tr55.segments` — an ordered array; each segment is one reach of the flow
path, matching the real worksheet's arbitrary AB, BC, CD chain (not "exactly
one of each type"). Segment types:
```
sheet:    { type, n, L, s, P2 }        n = sheet-flow Manning's n (Table 3-1 lookup),
                                        P2 = 2-yr 24-hr rainfall (in), s = slope (ft/ft)
shallow:  { type, L, s, surface }       surface = shallow-concentrated lookup key
channel:  { type, L, s, n, area, wp }  area & wp = channel cross-section area (sf) and
                                        wetted perimeter (ft)
```

### 1B.2 Travel-time equations
```
sheet:    Tt = 0.007 × (n·L)^0.8 / (P2^0.5 × s^0.4)        (hours)
shallow:  V = Cp × √s        Tt = L / (3600·V)             (Cp from surface lookup)
channel:  R = area / wp                                    (ft)
          V = (1.49/n) × R^(2/3) × √s                      (ft/s)
          Tt = L / (3600·V)
Tc = Σ Tt over all segments, reported in minutes (×60).
```
Every function returns 0 — not NaN — when its inputs are incomplete, so a
partially-filled worksheet still shows a sensible running total instead of
breaking.

### 1B.3 Reference lookups (editable dropdowns, not free text)
- **`TR55_SHEET_N`** — TR-55 Table 3-1 roughness coefficients: smooth 0.011,
  fallow 0.05, cultivated ≤20% residue 0.06, cultivated >20% residue 0.17,
  short grass prairie 0.15, dense grasses 0.24, Bermuda grass 0.41,
  range 0.13, woods light underbrush 0.40, woods dense underbrush 0.80.
- **`TR55_SHALLOW_CP`** — shallow-concentrated velocity coefficients:
  paved 20.328, unpaved/grassed waterway (urban) 16.1345, nearly bare untilled
  9.965, cultivated straight-row 8.762, prairie short-grass 6.962, minimum
  tillage/woodlands 5.032, forest heavy litter 2.516.
- **`TR55_CHANNEL_N`** — typical open-channel Manning's n (Chow-style starting
  points, disclosed in the UI as editable and needing site-specific judgment):
  smooth pipe 0.011, concrete trowel/RCP 0.013, corrugated metal 0.024,
  concrete unfinished 0.017, earth clean straight 0.022, riprap 0.035,
  earth grassed 0.035, natural stream clean straight 0.030, natural stream
  weedy winding 0.050.

### 1B.4 UI — interactive modal, not a static worksheet
`openTr55Modal(row)` opens the shared modal: intro text explaining the
segmental method, per-segment numbered cards with a type `<select>`
(sheet/shallow/channel) that swaps which fields that segment shows, add and
remove buttons, a live running total, and per-segment velocity/hydraulic-radius
outputs where meaningful. The computed total is written back to `row.tc`
(displayed to 0.1 min) and the row shows it as a read-only value with the
Edit button.

### 1B.5 Sanity warnings
- More than one sheet-flow segment → warning (sheet flow normally occurs once,
  at the very start).
- A sheet-flow segment appearing after any shallow/channel segment → warning
  (flow doesn't revert to sheet once concentrated).
Warnings are advisory only — the computation still runs, because the real
worksheet allows the user to describe what the flow path actually is.

### 1B.6 Detail sheet
The modal's segments get a Detail/Print calc sheet like every other computed
output (Phase 7 helpers): per-segment inputs, the governing formula with
substituted numbers, per-segment travel time, and the summed Tc.

---

## Phase 2 — Flow Splitter

A structure `type: "splitter"` is a diversion structure (manhole or prefab) that divides its Total Flow between **two** outgoing pipes instead of one — everywhere else in the model, one outgoing pipe is assumed.

**Structure fields added:** `splitMethod: "capacity" | "ratio"`, `splitCapacity` (cfs), `splitRatio` (0–1).

```
capacity method:  Primary = MIN(TotalFlow, Capacity)     Secondary = TotalFlow − Primary
ratio method:     Primary = TotalFlow × Ratio             Secondary = TotalFlow − Primary
```

**Pipe field added:** `splitRole: "" | "primary" | "secondary"` — only meaningful when the pipe's From-structure is a splitter. Require exactly one Primary and one Secondary outgoing pipe from a splitter; flag it if that's not satisfied.

`pipeDesignQ` gets a branch: if the From-structure is a splitter, return the Primary or Secondary share instead of the full Total Flow. The splitter's **own** friction loss (Hf) uses only the Primary pipe's carried flow — its structure loss (Hb) still uses the full Total Flow, since that governs the turbulence of the merging inflow before the split happens. The Secondary path is a fully independent downstream chain; it doesn't feed back into the splitter's own elevation.

---

## Phase 3 — Outlet Control Structure (single facility first)

A **separate concept** from the conveyance network above — this builds a stage-discharge rating curve for a BMP/SWM/ESD outlet structure (a pond riser), not a peak-flow capacity check.

### 3.1 Data model
```
Outlet Structure (facility): id, label, desc, startElev, endElev,
  coarseIncrement, fineIncrement, fineBand,
  twMode: none | fixed | linked, twFixed, twStructureId

Outlet Device: id, outletStructureId, label, type: orifice | weir | pipe,
  invert (orifice/pipe) or crest (weir), diameter (in, orifice/pipe),
  length (ft, weir), weirShape: rect | vnotch, notchAngle (deg), cd/coef
```
Multiple devices on one facility all discharge at the same shared headwater and their flows simply **add together** — that's the whole point of a composite rating curve.

### 3.2 Circular segment geometry — exact, not approximated
For a circular orifice or pipe (treat "pipe" here as a large orifice/short culvert barrel, not a full HDS-5 inlet/outlet-control analysis — say so explicitly), flowing to depth `h` above its invert, radius `R`:
```
α = cos⁻¹(1 − h/R)                              (half-angle)
A = R²(2α − sin 2α) / 2                          (exact wetted area)
centroid_above_invert = R − 4R·sin³α / (3(2α − sin 2α))
hc = h − centroid_above_invert                   (head to the wetted area's own centroid)
```
Verify this against the classical semicircle result before trusting it: at `h = R` (half full), this must give `A = πR²/2` exactly and `hc = 4R/(3π)` exactly. If it doesn't reproduce that closed-form at half-full, the derivation has a sign error somewhere — don't ship it.

**Known limitation worth disclosing in the UI**: this method (driving head = head to the area's *centroid*) is the standard industry approach, but it's not literally exact — because √h is concave, it's a small, real overestimate of the true integrated flow (Jensen's inequality: the average of √h over the area is always ≤ √(average h)). The error is exactly zero at the empty and full boundaries and small in between. This is standard practice (matches HydroCAD/PondPack-style tools), not a defect — just don't claim it's more rigorous than it is.

### 3.3 Orifice/Pipe — three flow regimes
```
if HW ≤ invert:                    Q = 0                              (dry)
if invert < HW < invert + 2R:      Q = Cd × A(h) × √(2g × hc)          (partial — use 3.2)
if HW ≥ invert + 2R:
    if TW active and TW > invert+2R:   H = HW − TW                    (submerged, differential head)
    else:                               H = HW − (invert + R)          (full, free discharge)
    Q = Cd × A × √(2g × H),  A = πR²
```
This must be **continuous** at the partial→full boundary: verify `hc → R` as `h → 2R` in the partial branch, matching the full-flow formula's `H = HW − (invert+R)` exactly at that point.

### 3.4 Weir — two flow regimes
```
if HW ≤ crest:  Q = 0
H1 = HW − crest
rectangular:  Qfree = C × L × H1^1.5
V-notch:      Qfree = C × tan(θ/2) × H1^2.5

if TW active and TW > crest:
    H2 = TW − crest
    if H2 ≥ H1: Q = 0   (drowned)
    else:
      n = 1.5 (rect) or 2.5 (V-notch)
      factor = [1 − (H2/H1)^n]^0.385         (Villemonte submergence correction)
      Q = Qfree × factor
else: Q = Qfree
```

### 3.5 Stage-list generation
Given `startElev`/`endElev`, walk in `coarseIncrement` steps across the whole range, then insert `fineIncrement`-spaced points within `±fineBand` of every device's invert, top-of-opening, and crest (and of the resolved tailwater elevation, if any) — that's where the governing equation switches and the curve bends the most. Dedupe and sort. Cap total rows (e.g. 2000) and thin evenly if exceeded, with a warning shown to the user rather than silently freezing the browser.

### 3.6 Tailwater
- `none`: ignore TW entirely (free discharge assumption everywhere).
- `fixed`: a constant elevation the user types in.
- `linked`: resolves to a **Junction Structure's live computed Upstream HGL** from Phase 1 — this is the payoff for building the two systems in the same app. It's a single resolved elevation (not a stage-dependent curve), since the linked structure's Total Flow is a fixed design value, not itself a function of the pond's stage.

---

## Phase 4 — Multiple independent Outlet Structures

**The trap to avoid**: if devices from two different ponds/BMPs ever end up in one flat list with one shared stage range and one shared tailwater setting, their flows get silently summed together into one meaningless combined curve. Each outlet structure needs its own devices, its own stage range/precision, and its own tailwater — never shared.

- `state.outletStructures`: array of facilities (the fields from 3.1).
- `state.outletDevices`: flat array, each tagged with `outletStructureId`.
- `state.activeOutletId`: which facility's devices/curve is currently shown.
- UI: a facility selector (dropdown + Add/Delete) at the top of the tab; everything below — devices table, settings, rating curve — filtered to the active facility only.
- Write a test that edits a device on Facility A and asserts Facility B's rating curve is byte-for-byte unchanged. This is the single most important regression test for this phase.

---

## Phase 5 — Per-device precision & unit polish

### 5.1 Precision mode
Facility-level toggle: `precisionMode: "uniform" | "individual"`.
- `uniform` (sensible default for new facilities): every device uses the facility's default fine increment/band; per-device override UI is hidden entirely.
- `individual`: an explicit **checkbox** per device — "Custom" — reveals two number fields (increment, band). Unchecked = fields shown disabled, pre-filled with the facility default as a preview (not editable). This checkbox pattern is much clearer than a blank-field-means-default convention — don't use the blank-field convention; it's genuinely ambiguous to a user (is 0 different from blank? what does blank even mean without reading a tooltip?).
- Setting a device's band override to `0` is a legitimate, meaningful choice — it means "skip fine refinement near this device's critical elevation entirely" (useful for something like a rarely-active emergency spillway). Don't conflate "0" with "unset."

### 5.2 Geometry units
Per-device unit toggle (`in`/`ft`) next to Diameter (orifice/pipe) and Length (weir) fields. **Store the canonical value in a fixed unit always** (inches for diameter, feet for length, matching what the calculation functions expect) — the unit field only controls the displayed/entered number; convert on display and on input, never change what's stored based on the toggle alone. This keeps every downstream formula unit-agnostic.

### 5.3 Number input polish
- Hide native spinner arrows via CSS (`input[type=number]::-webkit-inner-spin-button/outer-spin-button { -webkit-appearance:none }`, `-moz-appearance:textfield`) — they clutter narrow table cells.
- Stop scroll-wheel from silently changing a focused number input's value: blur it on wheel event while focused (`passive:true` listener at the document level).

---

## Phase 6 — Formulas & Examples reference tab

A dedicated tab documenting every equation used elsewhere in the tool (Rational Method, Manning's, friction loss, controlling-angle structure loss, flow splitter, circular segment geometry, orifice/pipe regimes, both weir regimes), each with a **worked numeric example**. The one exception: the TR-55 segment equations (Phase 1B) are documented on the row's own TR-55 calc sheet (1B.6) rather than duplicated here — a TR-55 row's worked example is its own segment list.

**Critical implementation rule**: compute every example number live, from the actual current project data, through the same functions the rest of the app uses — never hand-type a result into the documentation. Write a test that greps the rendered example text for `liveFunction(...).toFixed(n)` and asserts it appears verbatim. This is what keeps a reference document from silently going stale the moment someone edits the seed data or a formula.

Style it as a printable "calc sheet" (see Phase 7) with its own Print button, kept separate from the bulk "Print All" — it's methodology documentation, not per-project computed output, same as the static reference tables.

---

## Phase 7 — Detail sheets, modal, and print system

Every row that represents a **computed output** (a Drainage Area's Q, a Structure's Total Flow/Hb/elevation, a Pipe's capacity check, an Outlet Structure's rating-curve row) gets a small "⤢ Detail" button. Clicking it opens a modal showing a full calc-sheet breakdown for that one row: inputs, the governing formula, the formula with numbers substituted in, and the result — reuse a small set of composable helpers (`csSection`, `csTable`, `csFormula`, `csResult`, `csWarn`) everywhere rather than hand-building markup per sheet type.

Static reference tables (Table 4-6, Kb Coefficients) do **not** get Detail buttons — they're inputs, not computed outputs.

**Print mechanism** (works for both "print this one row" and "print everything"):
```
#printArea { display:none; }                          /* always empty/hidden on screen */
body.print-mode .app { display:none; }
body.print-mode #printArea { display:block; }
```
To print: populate `#printArea` with one or more calc-sheet nodes, add `print-mode` to `<body>`, call `window.print()`. On the browser's `afterprint` event, remove the class and clear `#printArea`. "Print All" compiles every Drainage Area/Structure/Pipe/rating-curve-stage sheet in one pass, with `page-break-after: always` on each sheet except the last — warn the user this can genuinely run to 100+ pages with a fine stage increment across multiple facilities, since that's a real, unsurprising consequence of the feature, not a bug.

Calc sheets render as light-background/dark-text "paper" regardless of the app's dark theme (print output should look like a normal printed page).

---

## Section A — Frontend architecture (apply from Phase 1 onward)

### A.1 The `el()` DOM helper
```js
function el(tag, attrs, children){
  const e = document.createElement(tag);
  if(attrs) for(const k in attrs){
    const v = attrs[k];
    if(k==="class") e.className=v;
    else if(k==="html") e.innerHTML=v;
    else if(k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if(v===null || v===undefined) { /* skip: do NOT setAttribute(k, null) */ }
    else e.setAttribute(k, v);
  }
  if(children) (Array.isArray(children)?children:[children]).forEach(c=>{
    if(c==null) return;
    e.appendChild((c instanceof Node) ? c : document.createTextNode(String(c)));
  });
  return e;
}
```
**The null/undefined skip is not optional.** `Element.setAttribute(name, null)` stringifies to the literal text `"null"` — it does NOT remove or skip the attribute. For boolean attributes (`checked`, `disabled`, `selected`, `required`), the attribute's mere *presence* — any value, including the string `"null"` — makes the browser treat the condition as true. Writing `checked: someCondition ? "checked" : null` without this guard in `el()` produces a checkbox that renders checked **regardless of `someCondition`**, every single time, on every re-render. This is a real bug that shipped and had to be found and fixed — build the guard into the helper itself from day one rather than remembering to special-case every checkbox call site.

### A.2 Focus preservation across full re-renders
Every table is rebuilt from scratch (`container.innerHTML = ""` then re-append) on almost every data change — simpler and far less bug-prone than fine-grained DOM patching, but it means the DOM node the user was just typing into gets destroyed and recreated, and focus silently reverts to `<body>` after the very next keystroke.

Fix: tag every input/select/checkbox that can trigger a re-render with a stable `data-focus-key` (e.g. `"structures:"+row.id+":"+fieldName`), and route every state-mutating handler through:
```js
function withFocusPreserved(renderFn){
  const active = document.activeElement;
  const key = active && active.dataset && active.dataset.focusKey;
  renderFn();
  if(key){
    const match = document.querySelector('[data-focus-key="'+CSS.escape(key)+'"]');
    if(match){ match.focus(); if(match.setSelectionRange) try{ match.setSelectionRange(active.selectionStart, active.selectionEnd); }catch(e){} }
  }
}
```
Apply this to **every** `oninput` and `onchange` handler that calls a render function — text inputs, number inputs, `<select>` dropdowns, and checkboxes alike. It's easy to apply it consistently to text inputs (where the pain is obvious — you can't type more than one character) and then forget selects and checkboxes (where the pain is subtler — losing keyboard-Tab flow, not an unusable field). Audit for it explicitly at the end of each phase: search for every `onchange:` and `oninput:` handler and confirm each one that calls a render function is wrapped.

### A.3 Row identity, not array index, for stable keys
Every data-model row needs a stable `id` (a simple incrementing counter is fine) generated once at creation and never recomputed — used for `data-focus-key`, for row lookups after Excel import, and for cross-references (e.g. a Pipe's `fromStructureId`/`toStructureId`). The one exception in this tool was the Kb Coefficients table (no natural per-row identity beyond its position) — there, array index is an acceptable focus-key component precisely because editing a value never reorders that array; don't generalize this shortcut to tables where rows can be reordered or filtered.

---

## Section B — Excel export/import

### B.1 The single most important setting
```js
XLSX.write(workbook, { bookType: "xlsx", type: "array", bookSST: true })
```
**Without `bookSST: true`, every exported file is spec-invalid** and Excel will show "We found a problem with some content... Do you want us to try to recover as much as we can?" on open. What actually happens without it: SheetJS writes every string-valued cell — headers, IDs, plain text, not just formula results — with cell type `t="str"`, which per the OOXML spec is reserved for a *formula's* string result and requires an accompanying `<f>` element. A plain data cell with `t="str"` and no formula is a spec violation that Excel's strict parser rejects on sight. `bookSST: true` makes SheetJS build a real `sharedStrings.xml` table and use `t="s"` (shared-string index) correctly for ordinary text. Verify this directly after building the export function, before building anything else Excel-related: write a test that unzips the generated `.xlsx`, confirms `xl/sharedStrings.xml` exists, and asserts zero cells anywhere in the workbook have `t="str"` without a sibling `<f>` element.

### B.2 Formula cells need a cached value, not just a formula string
```js
function setFormula(ws, addr, formula, value){
  const isStr = typeof value === "string";
  ws[addr] = { t: isStr?"s":"n", f: formula.replace(/^=/,""), v: isStr?value:(isFinite(value)?value:0) };
}
```
A cell object with only `{f: "...", t:"n"}` and no `.v` gets **silently dropped entirely** by SheetJS's writer — not written with a blank value, just absent from the output file. Every formula you write must carry the value the app already computed for that cell, so (a) the formula survives the write at all, and (b) the file shows correct numbers immediately on open, before Excel's own recalculation pass runs.

### B.3 Column grouping vs. hiding — a second, subtler corruption risk
If a feature needs "hide these columns, but let the user reveal them again" (e.g., detail columns the user can toggle), the tempting approach is Excel's native outline/grouping (`{wch, level: 1}` on a `!cols` entry, giving a clickable +/- above the column headers). **Don't** — SheetJS emits both a non-standard `level="1"` attribute *and* the correct `outlineLevel="1"` attribute on the `<col>` element, and the redundant `level` attribute crashes strict OOXML readers (confirmed: openpyxl raises `TypeError: ColumnDimension.__init__() got an unexpected keyword argument 'level'` trying to parse it — real Excel may well tolerate it, but that's not a bet worth making). Use plain column hiding instead: `{wch, hidden: true}` emits only the valid `hidden` attribute and works everywhere. It's a strictly worse interaction (no inline +/- button — the user needs Format → Hide & Unhide) but it never corrupts the file.

### B.4 Verification: don't trust round-tripping through the same library that wrote the file
Reading an exported file back with the exact same JS library (SheetJS) that wrote it will happily "verify" a file that real Excel rejects — the writer and reader share the same lenient assumptions about what's valid. Validate with genuinely independent tools instead:
- **openpyxl** (Python) — stricter than SheetJS about attribute/schema correctness; good at catching exactly the two bugs above.
- **LibreOffice headless** (`soffice --headless --convert-to xlsx file.xlsx --outdir /tmp`) — a fully independent OOXML implementation; a clean round-trip through it is a strong (if not 100%) signal.
- **`xmllint --noout`** on every unzipped XML part, to catch raw well-formedness issues (unescaped entities, mismatched tags) that neither of the above always surfaces clearly.

Run all three after *any* change to the export code, not just once at the start.

### B.5 Multi-sheet structure and cross-sheet live formulas
Roughly: Overview (prose), Drainage Area, TR-55 Segments (flat, tagged by Drainage Area — a variable-length list per row, same pattern as Outlet Devices), Junction Structure, Pipe Sizing, Outlet Structures (facility list), Outlet Devices (flat, tagged by facility), one `Rating - <facility label>` sheet per facility, Table 4-6 Reference, Kb Coefficients.

Cross-sheet references use `INDEX/MATCH` keyed on the user-facing label column (not the internal row id, which is meaningless outside the app) — e.g. a structure's Captured Q:
```
=IF(C2="",0,IFERROR(INDEX('Drainage Area'!H:H,MATCH(C2,'Drainage Area'!A:A,0)),0))
```
For a value that depends on *which specific row* matches a compound condition (e.g. "the pipe whose From-structure is X **and** whose Role is Primary"), build a helper column concatenating a key (`=B2&"|"&IF(O2="","primary",O2)`) and `MATCH` against that instead of trying to express AND-conditions inline.

Sheet names are capped at 31 characters and can't contain `\ / ? * [ ] :` — write a `safeSheetName()` helper that strips/truncates and de-duplicates (append `~2`, `~3`, ...) before calling `book_append_sheet`, since facility labels are free-text user input.

### B.6 What to make live vs. what to export as a value
Make live (formula, recalculates in Excel as inputs change): anything that's a straightforward arithmetic/lookup chain — Total Flow, Design Q (including split shares), friction loss, a rating curve's Total-Q-per-row sum, tailwater linked to another sheet.
Export as a static value with a clear note that it's app-computed and editable-to-override: anything whose branching logic would require an unreasonably long or fragile nested-IF/lookup formula to reproduce — Kb (interpolated + controlling-angle selection), the orifice/weir regime math (partial/full/submerged branching with real trig). Don't force everything to be "live" for its own sake; a wall of 2000-character nested formulas is itself a reliability risk.

---

## Section C — Testing approach

Build a small jsdom-based test harness (Node + `jsdom` + the real `xlsx` npm package for independent read-back) and grow it alongside every phase, not after the fact:

1. **Unit-level formula checks** — for anything with a known closed form (the circular-segment centroid, the friction-slope equation), assert the implementation matches an independently-computed reference value to a tight tolerance (`1e-9` for pure geometry, `0.01` for anything that round-trips through Excel's own floating point). TR-55 segment equations — sheet flow against the published Worksheet 3 closed form, shallow velocity against Cp·√s, channel velocity against Manning's, and Σ-Tt against a hand-summed multi-segment example.
2. **Network/integration checks** — seed a small representative project (a two-inflow controlling-angle junction, a flow splitter with both branches, two independent outlet facilities) and assert conservation of mass, correct regime selection, and correct elevation propagation end-to-end.
3. **DOM/UI checks** — actually click things: dispatch real `input`/`change`/`click` events on the rendered DOM and assert both the underlying state *and* the re-rendered DOM reflect it — this is what catches the `checked`-always-true class of bug, which a pure data-layer test would never see (the data layer was correct the whole time; only the rendering was wrong).
4. **Export/import round-trip** — build the workbook, write it, read it back (with the real `xlsx` package, not just SheetJS reading its own output — see B.4), and assert every computed value matches the live app to within tolerance; then wipe state, import the same file, and assert the row counts and key values are restored exactly.
5. **OOXML structural checks** — run B.4's independent-tool checks as an automated, permanent part of the suite, not a one-off manual step, specifically re-asserting "no `t=str` cell without a formula" and "no non-standard `level` attribute" — these are exactly the two defect classes that shipped once already.

A reasonable target by the end of Phase 7 is on the order of 150–250 assertions across these five categories. That sounds like a lot for a single-file tool, but every one of them traces back to a bug that actually happened during this build — the count is a byproduct of taking each one seriously, not a target to hit for its own sake.

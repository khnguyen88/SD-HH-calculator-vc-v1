# HGL/EGL Visualizer — Design Spec

A standalone single-file offline HTML companion to the Storm Drain Design
Calculator (`storm-drain-design-calculator.html`). It imports a designed storm-drain
network from the main app, visualizes it in isometric plan view and 2D elevation
profile, and walks the user through the energy equation step-by-step so the math
behind the HGL/EGL balance is legible — and so the user can tweak values in a
local sandbox to see what happens, without mutating the main app's state.

The spec is organized as ten sections. Each section is independently
implementable. Section 7 names the pure-math functions that are the backbone
of the implementation; Section 10 shows the plan-directory layout that
decomposes those into atomic flash-model-runnable tasks.

---

## 0. Non-negotiable constraints (state these every phase)

- **Single HTML file.** `drainage-calculator/storm-drain-visualizer.html` is the
  built artifact; users open it by double-click. Edits happen in
  `storm-drain-visualizer-dev.html`. `drainage-calculator/build-visualizer.js`
  inlines SheetJS and produces the built file — exactly like the main app.
- **Offline.** No CDN, no network. SheetJS `xlsx.full.min.js` bundled inline
  (same source as `drainage-calculator/lib/sheetjs-bundle.js`).
- **Vanilla JS only.** Same `el()` DOM helper with the null/undefined guard
  (main spec §A.1). Same `withFocusPreserved` pattern (main spec §A.2) around
  every `oninput`/`onchange` handler that triggers a render.
- **Dark engineering aesthetic.** Monospace font for every numeric value and
  input. System font stack only. Visual grammar matches the main app so the
  two tools feel like one product.
- **Read-only first, edit-mode second.** Opening a fresh import = read-only
  exploration. Entering edit mode is a deliberate user action (toolbar toggle).
  Edits are session-only; "Export tweaked JSON" writes a sidecar file.
- **Governing-equation parity with the main app.** Every computed value in the
  visualizer uses the same formula as the main app. Section 8 drift-test
  enforces this on every build.
- **This spec file is reference material; it does not direct implementation.**
  Implementation is directed by the small task-MD files produced by the
  writing-plans skill (Section 10). The spec explains the *why*; the task MDs
  explain the *what*.

---

## 1. Overview

**Purpose.** Help a user — typically the engineer who designed the network in
the main app, or a reviewer, or a student — understand *why* the HGL and EGL
look the way they do. The main app answers "did my network pass?" The
visualizer answers "where did the losses come from, and what would change if I
tweaked this slope / this bend / this tailwater?"

**Dual-mode UX.** Opens read-only (explore). The user can walk the cursor
through the network, see the ledger accumulate, and inspect every formula.
Then — only on explicit toggle — enters edit mode, where key fields become
editable and the ledger / HGL / EGL curves respond in real time. Edits never
write back to the imported file.

**Not goals (v1).** See Section 9 for the full deferred list — most notably
flow splitters, outlet rating curves, TR-55, printable calc-sheets.

---

## 2. Data model & import

### 2.1 Accepted input formats

Two formats, auto-detected by file extension.

**(A) The main app's `.xlsx` export.** Already defined by main spec §B.
Only four sheets are consumed:

- `Drainage Area` — to resolve each structure's "captured" Q.
- `Junction Structure` — structure roster, elevations, rim, crown, type.
- `Pipe Sizing` — pipe roster, Q, Hf, slope, length, angle.
- `Outlet Structures` (optional) — to resolve linked tailwater elevations if
  the main app's Outlet tab was used.

Every other sheet is ignored (Overview, TR-55 Segments, Outlet Devices, per-
facility Rating, Table 4-6, Kb Coefficients — though the embedded Kb table is
used indirectly via the visualizer's own copy of the seed values).

The computed `Q_total`, `Hf`, `Hb`, `elevation` columns are read verbatim as
reference values for the drift test (§8.2) and for a non-blocking
"imported value differs by X" badge on any ledger row where the import and
local recompute disagree by more than 0.001 ft. **The ledger always displays
the locally-recomputed value, not the imported value** — this is required for
edit mode to be meaningful (overridden fields must propagate). The imported
values exist only as a consistency check.

**(B) A JSON sidecar.** New, lightweight format. Added to the main app in a
small follow-up task (task group `10-import` in the plan).

```json
{
  "schemaVersion": 1,
  "exportedAt": "2026-11-07T14:30:00Z",
  "sourceApp": "storm-drain-design-calculator",
  "sourceAppVersion": "<built-file hash or label>",
  "config": {
    "stormLabel": "10-yr Rational",
    "units": "us-customary",
    "hglMethod": "hec22"
  },
  "structures": [
    { "id": "S-01", "label": "MH-A", "type": "manhole",
      "x": 0, "y": 0,
      "rim": 102.5, "startElev": 98.4, "crown": 97.6,
      "forceElev": false,
      "capturedQ": 1.2, "totalQ": 8.4,
      "Hb": 0.08, "elevation": 100.39 }
  ],
  "pipes": [
    { "id": "P-02", "fromId": "S-01", "toId": "S-02",
      "shape": "circular", "size": 18, "n": 0.013,
      "slope": 0.005, "length": 120, "angle": 30,
      "designQ": 8.4, "Hf": 0.494 }
  ],
  "kbTable": [ { "angleDeg": 0, "inlet": 0.0, "manhole": 0.0, "bend": 0.0 },
               { "angleDeg": 5, "inlet": 0.06, "manhole": 0.06, "bend": 0.06 }, ...],
  "outfall": { "structureId": "S-00", "tailwaterElev": 100.00 }
}
```

- `x, y` come from the main app's structure positions if present. If absent
  (older exports), the visualizer runs a layered-graph auto-layout (§2.3) so
  rendering still works.
- `elevation` is the upstream EGL at that structure per the main app.
- `hglMethod` is `"hec22"` (default) or `"legacy-both-crown"` — matches the
  bburg template's toggle so the visualizer can reproduce either convention.
- `kbTable` is a complete copy of the editable Kb lookup from the main app.
  If absent, the visualizer falls back to its own hard-coded seed (same 12-row
  AASHTO curve as main spec §1.6).

### 2.2 In-memory state shape

```js
state = {
  imported:   { structures, pipes, outfall, config, kbTable },  // immutable
  overrides:  { byId: { "P-02": { slope: 0.006 }, ... } },      // edits only
  cursor:     { kind: "structure"|"pipe", id, pathStack },
  ui:         { view: "iso"|"profile",
                mode: "explore"|"edit",
                hglMethod: "hec22"|"legacy-both-crown",
                freeRoam: false,
                branchChoices: { byStructureId: "pipeId" } }   // remembered picks
}
```

**Everything derived from `resolvedState = merge(imported, overrides)` is
computed on demand** — no second source of truth for computed values. This is
how we avoid the drift class of bug the main spec warns about in §A.3.

### 2.3 Auto-layout when x/y are missing

Layered-graph layout:

1. Compute hop-distance from the outfall for every structure (breadth-first).
2. Assign `y = -hopDistance * 100` (feet in world units; negative so upstream is
   up on screen).
3. Within each hop level, order structures left-to-right by the order their
   downstream pipe was first visited; assign `x = index * 80 - (levelCount-1)*40`.
4. Any disconnected component gets rendered as a separate row offset below.

Auto-layout coordinates are stored in `state.imported.structures[i].x/y` so iso
rendering is unchanged after that point — Shift+Arrow nudging (§5) still works.

---

## 3. View system (top half)

A single top-half frame; `[ ISO | PROFILE ]` toggle in the top-right swaps
renderings. Both share the same selection state: select a pipe in iso, switch
to profile, the same pipe is highlighted.

### 3.1 Iso (plan) view

Stylized isometric projection — not a true 3D camera. Fixed transform:

```
screen_x = (x - y) * cos(30°)
screen_y = (x + y) * sin(30°) - z * kZ        (kZ = 2.0 default)
```

- World `x, y` from structure positions (imported or auto-layout).
- World `z = structure.rim` so higher-rim structures sit visually higher.
- Depth-sort structures by `(x + y)` ascending (painter's).
- Symbols: rectangle = manhole, triangle = inlet, circle = junction, chevron =
  bend, double-circle = outfall.
- Pipes render as lines between centers. Line thickness proportional to pipe
  diameter (min 2 px, max 10 px, clamp). Arrow at midpoint shows flow
  direction.
- Selected element: yellow glow outline (SVG `filter: drop-shadow(0 0 4px gold)`).
- `Shift+Arrow` (edit mode only) nudges selected structure's world `x, y` by
  10 ft/step; overrides go into `state.overrides.byId[structureId].x/.y`.

### 3.2 Profile (elevation) view

X-axis = cumulative stationing along the currently-walked path (outfall = 0).
Y-axis = elevation (ft), autoscaled with 5% padding above max rim and below
min invert.

Rendered elements:

- Pipe profile: two polylines for crown (upper) and invert (lower) along the
  path; structures as vertical bars from invert to rim at their station.
- **HGL** — thick solid line connecting `EGL − V²/(2g)` at each node.
- **EGL** — thick dashed line, the running energy total; this is what the
  ledger is computing.
- Current cursor position: vertical highlighted band spanning the selected
  pipe or structure.

### 3.3 Overall screen layout

```
+----------------------------------------------------------------------------+
|  Storm Drain HGL/EGL Visualizer     [open .xlsx] [open .json] [?]   [mode] |
+----------------------------------------------------------------------------+
|  [ISO | PROFILE]  file: bburg-10yr.xlsx    cursor: Pipe P-02 (S-01 → S-02) |
|                                                                            |
|                       (one SVG view fills this area)                       |
|                                                                            |
+----------------------------------------------------------------------------+
|  Energy ledger (upstream walk from outfall)                [▸ edit mode]   |
|                                                                            |
|  Start: Outfall OUT       EGL = 100.00 ft  (tailwater)                     |
|  +Hf P-01                 +0.31            → 100.31                        |
|  +Hb S-A  (bend 30°)      +0.08            → 100.39                        |
|  ▼ +Hf P-02               +0.49            → 100.88    ← current           |
|      Sf = (Q·n / (1.486·A·R^(2/3)))² = 0.00412                             |
|      Hf = Sf·L = 0.00412 · 120 = 0.494 ft                                  |
|      EGL_up = EGL_dn + Hf = 100.39 + 0.49 = 100.88 ft                      |
|  ▸ +Hb S-B  (2 inflows)   +0.12            → 101.00                        |
|  ▸ +Hf P-03               +0.42            → 101.42                        |
|                                                                            |
+----------------------------------------------------------------------------+
```

---

## 4. Equation panel (bottom half)

Vertical list, one row per step in the current path. Current row expanded
inline showing full formula + substituted numbers + result. Prior rows
collapsed; click any to expand (collapsing the one that was open).

### 4.1 Row kinds and formulas

- **Start row (outfall / walk-start):**
  `EGL_start = TW_elev` — stated boundary, no formula.
- **+Hf row (a pipe):**
  ```
  A = pipeArea(shape, size)
  R = pipeRadius(shape, size)
  Sf = ( Q · n / (1.486 · A · R^(2/3)) )²
  Hf = Sf · L
  EGL_up = EGL_dn + Hf
  ```
- **+Hb row (a structure):** structure loss per main spec §1.4.
  - 0 inflows: `Kb` at 0°, nominal.
  - 1 inflow: `Kb` at that inflow pipe's angle.
  - 2 inflows: controlling-angle method. Expanded row shows **both** candidate
    losses and marks which one controlled (the smaller — teaching value).
  - >2 inflows: red flag row, no computation.
- **Branch row (splitter — v2+):** out of v1. If present in import, warning
  banner shown, only primary path walked (§9).
- **End row (upstream headwater):**
  `Total rise over path = EGL_end − EGL_start`.

### 4.2 HGL method toggle

Top-bar dropdown: `HEC-22 EGL (d/s crown floor)` (default) or
`Legacy both-end crown floor`. Both methods share full-flow Manning's Sf at
design Q, crown floor on HGL_dn, and Hb using the outflow pipe's velocity head.

- **HEC-22 EGL** — `HGL_up = HGL_dn + Hf`. No upstream crown floor.
- **Legacy both-end crown floor** — same, plus clamp `HGL_up = max(HGL_up,
  Crown_up)`.

Both modes compute `EGL_up` identically; the method only differs in how `HGL`
is derived from `EGL` at each step. The ledger's expanded row shows a note
when the Legacy clamp fires.

### 4.3 Walk kinetics

- Walk-start: `pathStack = [outfall]`, ledger = `[startRow]`.
- `↑`: advance to next-upstream element along the current branch. At a
  junction with >1 upstream pipes, open the branch popup first (§5).
- `↓`: pop last row. Previously-collapsed rows stay collapsed.
- `Enter`: expand/collapse current row.
- Free-roam mode: walk-start = first click after enabling free-roam; `↑/↓`
  move toward headwater / outfall; `←/→` cycle branches at any junction.

---

## 5. Navigation

### 5.1 Key bindings (document-level; ignored when a text input is focused)

| Key | Default (upstream walk) | Free-roam |
|---|---|---|
| `↑` | Advance upstream along current branch | Move toward headwater |
| `↓` | Pop last element (retreat) | Move toward outfall |
| `←` / `→` | At a multi-inflow junction, open the branch popup. Inside the popup: `↑/↓` cycle, `Enter` confirms | Same, also allowed mid-walk to re-pick a branch |
| `Enter` | Expand/collapse current ledger row; confirm branch popup | Same |
| `Esc` | Close branch popup without choosing; else reset walk | Same |
| `Tab` / `Shift+Tab` | Advance focus through ledger rows (collapse old, expand new) | Same |
| `Shift+↑↓←→` | **Edit mode only:** nudge selected structure's x/y by 10 ft/step | Same |
| `V` | Toggle iso ↔ profile view | Same |
| `E` | Toggle explore ↔ edit mode | Same |

### 5.2 Branch popup (modal)

```
+------------------------------------------+
|  Structure S-B has 2 upstream pipes.     |
|  Which branch do you want to follow?     |
|                                          |
|   ◉ P-02   from S-A   Q = 4.2 cfs        |
|   ○ P-03   from S-C   Q = 4.2 cfs        |
|                                          |
|        [ Enter: follow ]   [ Esc ]       |
+------------------------------------------+
```

- Uses the main app's modal pattern.
- `↑/↓` cycle, `Enter` confirms, `Esc` cancels.
- Chosen branch is remembered in `state.ui.branchChoices.byStructureId[sid]`
  for the session, so retracing doesn't re-prompt.
- Toolbar button "Reset branch choices" clears all remembered picks.

Branch popup never fires in free-roam mode — the user picks by clicking.

### 5.3 Walk-start selection

Default: the outfall structure (`type: "outfall"`, or lowest `elevation` if
multiple outfalls — explicit non-goal for v1 is multi-outfall UX; a toolbar
"Walk from…" selector lets the user override manually).

---

## 6. Edit mode

### 6.1 Mode toggle

Toolbar button `[▸ explore]` / `[▸ edit]` (also `E` hotkey). In edit mode:

- Every editable value in the ledger's **expanded** row becomes a monospace
  input. Imported value shown as placeholder; overridden value is bold.
- Editable fields per row kind:
  - **+Hf row:** `n`, `slope`, `length`, pipe `size` (dropdown of Table 4-6
    values, falls back to free numeric for custom).
  - **+Hb row:** structure `type` (dropdown), each inflow pipe's `angle`.
  - **Start row (outfall):** `TW_elev`.
- Overrides stored in `state.overrides.byId[elementId][fieldName] = newValue`.
  `state.imported` is never mutated.
- Every keystroke triggers `withFocusPreserved(renderAll)`; EGL/HGL curves
  shift in real time.

### 6.2 Override badge and reset

Toolbar badge: `X fields overridden`. Clicking opens a panel listing every
override with:

- Element ID, field name, original value, new value.
- Per-row "Revert this" button.
- Panel-level "Reset all" button.

### 6.3 Export tweaked JSON

Toolbar button, enabled when overrides exist. Writes a JSON with overrides
merged into field values plus a sibling `_overrides` array marking which
fields came from edits:

```json
{ "schemaVersion": 1, "exportedAt": "...",
  "sourceApp": "storm-drain-hgl-visualizer",
  "basedOn": { "sourceApp": "storm-drain-design-calculator",
               "exportedAt": "..." },
  "structures": [...], "pipes": [...], "outfall": {...},
  "kbTable": [...], "config": {...},
  "_overrides": [
    { "elementId": "P-02", "field": "slope",
      "originalValue": 0.005, "newValue": 0.006 }
  ]
}
```

Re-importing this file is lossless: the visualizer detects `_overrides`,
restores the original values into `state.imported`, puts those entries into
`state.overrides`, and enters edit mode automatically.

### 6.4 Explicit non-goal

No two-way sync with the main app. If the user wants edits in the main app,
they re-type them there. The visualizer is a scratchpad, not a design-
authority mutator.

---

## 7. Governing equations (local re-implementation)

Lives in one inline module in `storm-drain-visualizer-dev.html` between
`// ==== compute: begin ====` and `// ==== compute: end ====` sentinel
comments. Pure functions — no DOM reads, no state reads. Every function takes
explicit numeric inputs and returns a numeric result. This is what makes each
function atomically testable (one flash-model task per function).

### 7.1 Pipe geometry

```js
// Full-flow cross-sectional area for a circular pipe.
// d_in: pipe inside diameter in inches. Returns area in ft².
function pipeAreaCircular(d_in) {
  const D_ft = d_in / 12;
  return Math.PI * D_ft * D_ft / 4;
}

// Full-flow hydraulic radius for a circular pipe (R = D/4). d_in: inches.
// Returns R in ft.
function pipeRadiusCircular(d_in) { return (d_in / 12) / 4; }

// Elliptical: look up from Table 4-6 (same seed as main app §1.5).
function pipeAreaElliptical(spanRise)   { /* Table 4-6 lookup */ }
function pipeRadiusElliptical(spanRise) { /* R from Table 4-6 */ }

// Dispatch by shape.
function pipeArea(shape, size)   { ... }
function pipeRadius(shape, size) { ... }
```

### 7.2 Manning's friction

```js
// Friction slope at design Q (full-flow). Q cfs, n unitless, A ft², R ft.
// Returns Sf in ft/ft.
function frictionSlope(Q, n, A, R) {
  const num = Q * n;
  const den = 1.486 * A * Math.pow(R, 2/3);
  const ratio = num / den;
  return ratio * ratio;
}

// Hf = Sf · L.  L in ft.  Returns Hf in ft.
function frictionLoss(Sf, L) { return Sf * L; }
```

### 7.3 Velocity head and Hb (controlling-angle)

```js
const G_FT = 32.2;

function outletVelocity(Q_total_cfs, Aout_sf) {
  return Q_total_cfs / Aout_sf;
}

function velocityHead(V_fps) { return (V_fps * V_fps) / (2 * G_FT); }

// Linear interpolation over the Kb lookup; clamp at endpoints.
// structureType ∈ "inlet" | "manhole" | "bend".
function kbAt(angleDeg, structureType, kbTable) { ... }

// Structure loss per main spec §1.4.
// inflows: [{angleDeg, Qcfs}], length 0..2 (>2 returns {error}).
// Returns { Hb, kbUsed, thetaControlling, candidateLosses } — extra fields
// are what the expanded ledger row renders.
function structureLoss(inflows, Qtotal_cfs, Aout_sf, structureType, kbTable) {
  const Vout = outletVelocity(Qtotal_cfs, Aout_sf);
  const Hvout = velocityHead(Vout);
  if (inflows.length === 0) {
    const Kb = kbAt(0, structureType, kbTable);
    return { Hb: Kb * Hvout, kbUsed: Kb, thetaControlling: 0,
             candidateLosses: [] };
  }
  if (inflows.length === 1) {
    const Kb = kbAt(inflows[0].angleDeg, structureType, kbTable);
    return { Hb: Kb * Hvout, kbUsed: Kb,
             thetaControlling: inflows[0].angleDeg, candidateLosses: [] };
  }
  if (inflows.length === 2) {
    const [a, b] = inflows;
    const V1_3 = a.Qcfs / Aout_sf,  V2_3 = b.Qcfs / Aout_sf;
    const Lv1 = kbAt(a.angleDeg, structureType, kbTable) * velocityHead(V1_3);
    const Lv2 = kbAt(b.angleDeg, structureType, kbTable) * velocityHead(V2_3);
    const thetaC = (Lv1 > Lv2) ? b.angleDeg : a.angleDeg;   // smaller controls
    const Kb = kbAt(thetaC, structureType, kbTable);
    return { Hb: Kb * Hvout, kbUsed: Kb, thetaControlling: thetaC,
             candidateLosses: [{angle: a.angleDeg, Lv: Lv1},
                               {angle: b.angleDeg, Lv: Lv2}] };
  }
  return { error: "too-many-inflows" };
}
```

### 7.4 Ledger builder

```js
// Build the ledger from the current path. Returns an array of rows:
// { kind: "start"|"hf"|"hb"|"end", id, label, before, delta, after, detail }
// where `detail` carries the extra fields the expanded row renders
// (formulas with substituted numbers, candidate losses, controlling angle,
//  method-clamp note, etc.).
function buildLedger(path, resolvedState, kbTable, hglMethod) { ... }
```

### 7.5 Kb seed table

12 rows, 5°→0.06 through 90°→0.70, all three columns (`inlet`, `manhole`,
`bend`) seeded identically with the standard AASHTO bend-loss curve — the
same seed as main spec §1.6. Embedded verbatim from the main app's
`KB_SEED` constant (copy/paste, not re-derived) so the drift test (§8.2)
anchors against the same reference. Used when the imported `kbTable` is
absent. Editable via a modal settings panel (editing stores into
`state.overrides.kbTable` rather than per-element overrides).

---

## 8. Testing strategy

A jsdom harness sits in `drainage-calculator/visualizer-tests/`, mirroring the
main app's test layout. Node + `jsdom` + the real `xlsx` npm package for
independent read-back (main spec §B.4 — never verify the writer with itself).

### 8.1 Unit tests — pure math (per function from §7)

- `pipeAreaCircular(18)` ≈ `1.767...` ft²; tolerance `1e-9`.
- `pipeAreaCircular(d)` reproduces `π d²/(4·144)` symbolically for `d ∈ [12..96]`.
- `frictionSlope(8.4, 0.013, 1.767, 0.375)` matches hand-calculated reference to
  `1e-9`.
- `structureLoss` with 2 inflows: feed the specific counter-example cited in
  main spec §1.4 (smaller loss controls — not the larger) and assert the
  correct θc comes back.
- `structureLoss` with 0 inflows uses Kb at 0°.
- `structureLoss` with 1 inflow uses Kb at that pipe's angle.
- `structureLoss` with 3 inflows returns `{error: "too-many-inflows"}`.
- `kbAt(37.5, "manhole", seed)` between 35° and 40° returns linear interp to
  `1e-9`.
- `kbAt(0, *, seed)` and `kbAt(90, *, seed)` return the endpoint value.
- `kbAt(-5, *, seed)` and `kbAt(200, *, seed)` clamp at endpoints.

### 8.2 Drift test — parity with the main app (central guarantee)

Fixture `drainage-calculator/visualizer-tests/fixtures/main-app-export.xlsx`
is checked into the repo. Generated once by exporting a representative project
from the main app (two-inflow controlling-angle junction, elliptical pipe on
one leg, known tailwater). The test:

1. Load fixture `.xlsx` with the real `xlsx` npm package.
2. Parse into the visualizer's in-memory shape.
3. For every pipe: compute Hf locally with §7 functions; assert
   `|local - exported| ≤ 0.001 ft`.
4. For every structure: compute Hb locally; assert
   `|local - exported| ≤ 0.001 ft`.
5. Compute end-to-end EGL at each structure by walking from outfall; assert
   `|local - exported.elevation| ≤ 0.01 ft` (accumulated tolerance).

Any formula drift between the two apps breaks this test immediately.

### 8.3 Import round-trip — JSON

Build a representative JSON fixture. Import it; assert the cursor lands on
the outfall, the ledger starts at tailwater. Edit a pipe's slope via a
simulated input event. Export tweaked JSON. Re-import. Assert the override
survives, is loaded into `state.overrides`, and edit mode is re-entered
automatically.

### 8.4 DOM/UI — actual event dispatch

- `keydown` `↑` with cursor at outfall: cursor moves to first upstream pipe;
  ledger has 2 rows.
- At a 2-inflow junction, `↑`: branch popup opens; `↑/↓` cycle; `Enter`
  closes and advances onto chosen pipe.
- In edit mode, `input` event on a pipe-slope field: `state.overrides`
  updated, ledger re-rendered, profile view's Hf column shows new value.
- Focus-preservation audit (main spec §A.2): every `oninput`/`onchange`
  handler that calls a render routes through `withFocusPreserved` — grep
  the dev HTML for violations.

### 8.5 SVG integrity

- Select a pipe in iso; press `V` to switch to profile; assert same
  `pipe.id` highlighted.
- Verify no absent-attribute footguns (main spec §A.1 null/undefined guard)
  — grep for `setAttribute` with potentially-null values.
- Depth-sort correctness: structures with larger `(x + y)` render earlier
  (behind) in the SVG document order.

### 8.6 Coverage target

**80–120 assertions by v1.** The count is a byproduct of taking each class
of bug seriously, not a target to hit for its own sake.

---

## 9. v1 scope — what ships, what defers

### 9.1 In scope for v1

- Import of main app's `.xlsx` export AND the JSON sidecar.
- Structure types: inlet, manhole, bend, junction, outfall.
- Pipes: circular AND elliptical (via Table 4-6).
- Energy equation walk from outfall upstream: Hf (Manning), Hb (controlling-
  angle for ≤2 inflows), Vout²/(2g), tailwater seeding.
- Both HGL methods (HEC-22 EGL default, Legacy both-end crown floor) with
  live toggle. The pedagogical payoff of seeing both methods on the same
  network in the same ledger is a v1 priority.
- Explore + edit modes; export tweaked JSON.
- Iso + profile views with toggle, Shift+Arrow repositioning.
- Dark aesthetic, monospace numerics, system fonts.
- Full test matrix per §8.

### 9.2 Deferred (explicit non-goals for v1)

- **Flow splitters.** Visualizer assumes a converging tree (one outgoing pipe
  per structure). If an imported file contains a splitter, show a non-
  blocking warning banner and render only the primary path. Splitter
  branching in a cursor-walk interface is a real UX problem of its own and
  needs its own brainstorm.
- **Outlet rating curves / BMP devices.** Separate pedagogical story; main
  app's Outlet tab already handles it.
- **TR-55 segment visualization.** Main app's TR-55 modal already walks this.
- **Inlet spacing** (gutter flow).
- **Multiple simultaneous outfalls.** Toolbar "Walk from…" dropdown lets the
  user pick manually; auto-detection of multiple outfalls is deferred.
- **Printable calc-sheets for the visualizer's ledger.** Main app already
  prints per-row sheets; defer.
- **Two-way sync back into the main app.** Explicit non-goal.

### 9.3 Explicit assumption

The visualizer relies on each pipe's `angle` field from the import to compute
Hb. If the field is missing or 0 for a non-straight pipe, the ledger row
flags a warning but still computes with angle = 0.

---

## 10. Plan structure, build, and deployment

### 10.1 Plan directory (produced by writing-plans skill, task #8)

```
docs/superpowers/plans/2026-11-07-hgl-egl-visualizer/
├── plan.md                          # top-level index, ordered task list
├── 00-scaffold/
│   ├── group.md
│   ├── task-01-dev-html-skeleton.md
│   ├── task-02-build-script.md
│   └── task-03-el-helper-and-focus.md
├── 10-import/
│   ├── group.md
│   ├── task-04-json-schema-validator.md
│   ├── task-05-json-importer.md
│   ├── task-06-xlsx-importer-sheets.md
│   └── task-07-autolayout-no-coords.md
├── 20-compute/
│   ├── group.md
│   ├── task-08-pipe-geometry.md
│   ├── task-09-manning-friction.md
│   ├── task-10-kb-interpolation.md
│   ├── task-11-structure-loss.md
│   ├── task-12-ledger-builder.md
│   └── task-13-hgl-method-toggle.md
├── 30-views/
│   ├── group.md
│   ├── task-14-iso-projection.md
│   ├── task-15-iso-svg-render.md
│   ├── task-16-profile-svg-render.md
│   └── task-17-view-toggle-hotkey.md
├── 40-navigation/
│   ├── group.md
│   ├── task-18-cursor-state.md
│   ├── task-19-arrow-walk-upstream.md
│   ├── task-20-branch-popup.md
│   ├── task-21-free-roam-toggle.md
│   └── task-22-shift-arrow-nudge.md
├── 50-edit-mode/
│   ├── group.md
│   ├── task-23-overrides-store.md
│   ├── task-24-editable-ledger-fields.md
│   ├── task-25-override-badge-reset.md
│   └── task-26-export-tweaked-json.md
├── 60-ledger-render/
│   ├── group.md
│   ├── task-27-expanded-row-helpers.md
│   ├── task-28-row-formulas-hf.md
│   ├── task-29-row-formulas-hb.md
│   └── task-30-two-inflow-detail.md
├── 70-tests/
│   ├── group.md
│   ├── task-31-jsdom-harness.md
│   ├── task-32-unit-pipe-geometry.md
│   ├── task-33-unit-friction.md
│   ├── task-34-unit-structure-loss.md
│   ├── task-35-drift-test-fixture.md
│   ├── task-36-import-roundtrip.md
│   └── task-37-dom-event-tests.md
└── 90-deploy/
    ├── group.md
    ├── task-38-build-and-verify.md
    └── task-39-ghpages-publish.md
```

### 10.2 Task-file template (uniform)

Every `task-NN-*.md` is structured identically so a flash model can execute
it with minimal context. Each task file is ~50–150 lines, self-contained,
and names the exact file path, insert-point sentinels, function signatures,
and acceptance test.

```
# Task: <Short imperative>

## Context
- Why this task exists (1-2 sentences).
- Which section of the spec it implements (link + anchor).

## Preconditions
- Prior tasks completed: [task-NN, ...]
- Files that must exist with specific contents.

## Exact changes
- File: drainage-calculator/storm-drain-visualizer-dev.html
- Insert between sentinels: `// ==== compute: begin ====` / `// ==== compute: end ====`
- Code to add (exact function signature + body, or a precise edit).

## Acceptance test
- New test file: drainage-calculator/visualizer-tests/<name>.test.js
- Test code: ...
- Run: `node --test drainage-calculator/visualizer-tests/<name>.test.js`
- Must print: `pass 1`.

## Done when
- Build still succeeds: `node drainage-calculator/build-visualizer.js`.
- New test passes.
- No pre-existing tests regressed: `node --test drainage-calculator/visualizer-tests/`.
```

### 10.3 Build script

`drainage-calculator/build-visualizer.js` mirrors the main app's `build.js`:
reads `storm-drain-visualizer-dev.html`, inlines `lib/sheetjs-bundle.js` at a
`<!-- SHEETJS -->` sentinel comment, writes `storm-drain-visualizer.html`.

### 10.4 Deployment (GitHub Pages)

The main app lives at `/SD-HH-calculator-vc-v1/`; the visualizer lives
alongside it at `/SD-HH-calculator-vc-v1/visualizer.html`. A link from the
main app's toolbar opens the visualizer in a new tab; a "Back to calculator"
link in the visualizer's toolbar goes the other way. Links are relative so
both files work when served from disk, GitHub Pages, or any static host.

### 10.5 Deployment-runbook addendum

Added in task `90-deploy/task-38`:

1. Edit `storm-drain-visualizer-dev.html`; run
   `node drainage-calculator/build-visualizer.js`.
2. Commit both dev and built files to `main`.
3. On `gh-pages`, copy `storm-drain-visualizer.html` → `visualizer.html`.
4. Site: `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html`.

Never hand-edit `gh-pages`'s `visualizer.html` — always build from the dev
file (same rule as the main app).

---

## Appendix A — Cross-references to the main spec

| Visualizer concept | Main spec reference |
|---|---|
| `el()` DOM helper, null/undefined guard | §A.1 |
| `withFocusPreserved` pattern | §A.2 |
| Row identity, stable IDs | §A.3 |
| Manning's friction slope | §1.2 |
| Controlling-angle Hb | §1.4 |
| Kb lookup (editable table) | §1.6 |
| Table 4-6 (elliptical/circular equivalency) | §1.5 |
| HGL methods (HEC-22 vs. Legacy both-crown) | bburg user guide, HGL methods |
| Excel export schema (sheets consumed) | §B.1, §B.5 |
| `bookSST: true` requirement — if visualizer gains export | §B.1 |

## Appendix B — Deferred work (tracked, not planned yet)

- Splitter visualization (own brainstorm).
- Outlet rating curves (own brainstorm).
- TR-55 segment overlay on profile view.
- Multi-outfall auto-detection + walk-from switcher.
- Printable visualizer calc-sheets.
- Shared `compute.js` refactor between main app and visualizer (Approach 2
  from the brainstorm — eliminates the drift test by construction).
- Legacy-to-template .xlsx converter (separate app — user requested on
  2026-11-07 during this brainstorm; scoped out of this spec to keep the
  visualizer plan small and focused. Will get its own brainstorm and spec).

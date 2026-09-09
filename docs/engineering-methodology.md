# Storm Drain Design Calculator — Engineering Methodology

This is the engineering reference for every governing equation implemented in the tool. It documents the formula, variable definitions, units, and the regime/validity conditions under which each equation applies, plus the disclosed limitations and a traceability note explaining how the Formulas & Examples tab and the Excel export derive from the same functions documented here.

The user-facing walkthrough lives in `user-guide.md`. This document is deliberately more rigorous: equations, assumptions, boundaries — not "how to click buttons."

**Source of truth:** the as-built build spec (`drainage-calculator/storm-drain-calculator-spec.md`) and the implementation in `drainage-calculator/storm-drain-design-calculator.html`. Where a constant appears (1.486 for Manning's in US units; 1.49 for TR-55 channel flow; 32.2 ft/s² for g), it is the value actually used in the code.

**Units throughout:** US customary — cfs for flow, fps for velocity, ft for length/elevation, in for pipe diameter, in/hr for rainfall intensity, acres for tributary area.

---

## 1. Rational Method — peak runoff

```
Q = Cf × C × i × A
```

| Variable | Definition | Units |
|---|---|---|
| `Q` | Peak design flow from the catchment | cfs |
| `Cf` | Frequency correction factor (dimensionless); default 1.0. Applied for storms exceeding the 25-year return interval per standard practice. | — |
| `C` | Runoff coefficient (dimensionless), user-entered per catchment | — |
| `i` | Rainfall intensity for the design storm | in/hr |
| `A` | Tributary drainage area | acres |

**Validity / notes**

- The Rational Method is a peak-flow, small-catchment method. The tool does not check catchment size; the user is responsible for confirming it is appropriate for their project.
- `i` is supplied by the user (not computed from an IDF curve). The Tc on the same row is informational for the peak-flow calc — the user is expected to choose a design intensity consistent with their Tc and return interval.
- `Cf` defaults to 1.0 for every row. The column is editable; enter the value your agency's guidance specifies for the design storm frequency.

**Implementation:** `calcDrainageRow(row)` (HTML line ~746). `cf` defaults to 1 when not finite.

---

## 2. TR-55 Segmental Time of Concentration

NRCS TR-55 (1986), Chapter 3 / Worksheet 3. Tc is the sum of travel times across an arbitrary chain of flow-path segments (AB, BC, CD, …) — the tool does not assume "exactly one segment of each type." A row's Tc method is either `direct` (user types minutes) or `tr55` (computed from the segment list; main-table Tc becomes read-only with an "Edit TR-55" button).

### 2.1 Sheet flow

```
Tt = 0.007 × (n·L)^0.8 / (P2^0.5 × s^0.4)     [hours]
```

| Variable | Definition | Units |
|---|---|---|
| `Tt` | Travel time for the sheet-flow reach | hours |
| `n` | Sheet-flow Manning's n (TR-55 Table 3-1 lookup: smooth 0.011, fallow 0.05, cultivated ≤20% residue 0.06, cultivated >20% residue 0.17, short grass prairie 0.15, dense grasses 0.24, Bermuda grass 0.41, range 0.13, woods light underbrush 0.40, woods dense underbrush 0.80) | — |
| `L` | Sheet-flow length | ft |
| `P2` | 2-year, 24-hour rainfall | in |
| `s` | Land slope (ft/ft) | — |

**Validity / notes**

- The 1986 worksheet allows up to 300 ft; modern guidance caps sheet flow at 100 ft. Lengths over 100 ft draw an advisory warning. The computation still runs — the user decides what their agency expects.
- Returns 0 (not NaN) when any input is missing or non-positive, so a partially-filled worksheet shows a sensible running total.
- `Tc = Σ Tt` across all segments, reported in minutes (×60).

### 2.2 Shallow concentrated flow

```
V = Cp × √s                    [ft/s]
Tt = L / (3600 × V)            [hours]
```

| Variable | Definition | Units |
|---|---|---|
| `V` | Shallow-concentrated flow velocity | ft/s |
| `Cp` | Velocity coefficient from the surface lookup (paved 20.328; unpaved/grassed waterway (urban) 16.1345; nearly bare untilled 9.965; cultivated straight-row 8.762; prairie short-grass 6.962; minimum tillage/woodlands 5.032; forest heavy litter 2.516) | — |
| `s` | Watercourse slope (ft/ft) | — |
| `L` | Reach length | ft |

**Validity / notes**

- Returns 0 when `s` is missing or non-positive. Falls back to the unpaved coefficient if the surface key is not recognized.
- Travel time is `L / (3600·V)`, converting ft/s to hours.

### 2.3 Channel / pipe flow

```
R = area / wp                                   [ft]
V = (1.49 / n) × R^(2/3) × √s                   [ft/s]
Tt = L / (3600 × V)                             [hours]
```

| Variable | Definition | Units |
|---|---|---|
| `R` | Hydraulic radius | ft |
| `area` | Cross-sectional flow area | sf |
| `wp` | Wetted perimeter | ft |
| `n` | Open-channel Manning's n (Chow-style reference dropdown: smooth pipe 0.011, concrete trowel/RCP 0.013, corrugated metal 0.024, concrete unfinished 0.017, earth clean straight 0.022, riprap 0.035, earth grassed 0.035, natural stream clean straight 0.030, natural stream weedy winding 0.050) | — |
| `s` | Channel slope (ft/ft) | — |
| `L` | Reach length | ft |

**Validity / notes**

- Note the constant: **1.49**, not 1.486. This is the TR-55 channel-flow form; Manning's pipe equations elsewhere in the tool use 1.486. The spec and the HTML both use both values deliberately — do not "normalize" one to the other.
- The reference n values are starting points, disclosed in the UI as editable and requiring site-specific judgment.
- Returns 0 when any of `n`, `area`, `wp`, `s` is missing or non-positive.

### 2.4 Advisory warnings

- **More than one sheet-flow segment** → warning. Sheet flow normally occurs once, at the very start of the flow path.
- **A sheet-flow segment appearing after any shallow/channel segment** → warning. Flow does not revert to sheet once it has concentrated.

Warnings are advisory only — the computation still runs, because the real TR-55 worksheet allows the user to describe what the flow path actually is.

### 2.5 Detail sheet

Each TR-55 row's segment list gets its own Detail/Print calc sheet (per-segment inputs, governing formula with substituted numbers, per-segment travel time, summed Tc). The TR-55 equations are documented there rather than duplicated on the Formulas & Examples tab.

**Implementation:** `tr55SheetFlowTt`, `tr55ShallowVelocity`, `tr55TravelTime`, `tr55ChannelVelocity`, `tr55SegmentCalc`, `computeTr55` (HTML lines ~799–857).

---

## 3. Manning's Equation — full-flow pipe capacity

```
A = π/4 × D²                       (D in ft; for elliptical, look up from Table 4-6)
R = D/4                             (hydraulic radius, full flow)
V = (1.486 / n) × R^(2/3) × S^(1/2)  (full-flow velocity)
Qfull = V × A
Adequate if Qfull ≥ Design Q
```

| Variable | Definition | Units |
|---|---|---|
| `A` | Full cross-sectional area | sf |
| `D` | Diameter (circular) or equivalent circular diameter (elliptical, from Table 4-6) | ft |
| `R` | Hydraulic radius (full flow = D/4 for circular and for elliptical-via-equivalent-circular) | ft |
| `n` | Manning's roughness (user-entered, e.g. 0.013 for RCP) | — |
| `S` | Pipe slope | ft/ft |
| `V` | Full-flow velocity | fps |
| `Qfull` | Full-flow capacity | cfs |

**Validity / notes**

- Full-flow assumption. The tool sizes pipes by checking `Qfull ≥ Design Q`; it does not perform part-full capacity analysis on conveyance pipes (the outlet-structure orifice/pipe device, Section 8 below, is a separate calculation that does handle part-full flow).
- **Circular pipes:** diameter in inches (e.g. `24`); `A = π/4 × (D/12)²` and `R = (D/12)/4`.
- **Elliptical pipes:** enter `SPANxRISE` in inches (e.g. `38x24`). The tool matches the nearest Table 4-6 entry and uses that entry's published elliptical area and **equivalent circular diameter** for `R` in Manning's equation — not the geometric mean of span and rise.
- Constant: **1.486** (US units). This differs from the 1.49 used in TR-55 channel flow (Section 2.3); both are intentional and match the spec.

**Table 4-6 (static reference data).** A fixed lookup of circular diameter (in) / circular area (sf) / elliptical span×rise (in) / elliptical area (sf), 15″ through 144″. Representative rows:

| Circular Dia (in) | Circular Area (sf) | Elliptical Span×Rise (in) | Elliptical Area (sf) |
|---|---|---|---|
| 18 | 1.77 | 23×14 | 1.8 |
| 30 | 4.91 | 38×24 | 6.3 |
| 60 | 19.63 | 76×48 | 20.5 |
| 96 | 50.27 | 121×77 | 52.4 |

The table is editable reference data; the Pipe Sizing tab uses it automatically when an elliptical size is entered.

**Implementation:** `circularAreaSf`, `ellipticalLookup`, `pipeGeometry`, `manningFullFlow` (HTML lines ~684–720).

---

## 4. Friction Loss

```
Sf = ( Q × n / (1.486 × A × R^(2/3)) )²
Hf = Sf × L
```

| Variable | Definition | Units |
|---|---|---|
| `Sf` | Friction slope (head loss per unit length) | ft/ft |
| `Q` | Actual design flow carried by the pipe (not Qfull) | cfs |
| `n` | Manning's roughness | — |
| `A` | Full cross-sectional area | sf |
| `R` | Hydraulic radius (full flow) | ft |
| `Hf` | Total friction loss over the pipe length | ft |
| `L` | Pipe length | ft |

**Validity / notes**

- Uses the pipe's **carried design Q**, not its full-flow capacity. For a non-splitter structure, carried Q = the From-structure's Total Flow; for a splitter, the Primary or Secondary share (Section 7).
- Returns 0 when `A ≤ 0` or `R ≤ 0` (incomplete pipe geometry) — the structure calc flags this case with a warning rather than emitting NaN.
- Constant: **1.486**, matching Manning's equation in Section 3.

**Implementation:** `frictionSlope(Q, n, areaSf, R)` (HTML line ~722).

---

## 5. Structure Loss — Controlling-Angle Method

Structure loss depends on how many pipes flow **into** the structure. The structure's outgoing pipe is the reference — `Aout` is the full area of that outgoing pipe, and `Vout` is the structure's Total Flow divided by `Aout`.

### 5.1 Kb lookup

`Kb(θ)` comes from the editable Angle-vs-Kb table (Kb Coefficients tab), linearly interpolated between rows and clamped at the table's endpoints (5° through 90° as seeded). Separate columns for Inlet / Manhole / Bend. Column use by structure type:

| Structure type | Kb column |
|---|---|
| Inlet | `inlet` |
| Manhole | `manhole` |
| Bend | `bend` |
| Junction | `bend` |
| Flow Splitter | `manhole` |
| Outfall | none (no structure loss) |

**All three columns are seeded with the same published AASHTO bend-loss curve** (12 rows: 5°→0.06 through 90°→0.70). This default is deliberately conservative — it does not pretend to know agency-specific inlet-vs-manhole-vs-bend differences. The user is expected to enter their governing Appendix B chart's values per column before relying on results for submittal.

### 5.2 Inflow cases

**0 inflow pipes** (headwater / local-source-only structure):

```
Kb evaluated at 0° (nominal entrance condition)
Hb = Kb(0°) × Vout² / 2g
```

**1 inflow pipe:**

```
Kb at that pipe's own angle θ
Hb = Kb(θ) × Vout² / 2g
```

**2 inflow pipes — the controlling-angle method:**

```
V1/3 = Q1 / Aout        V2/3 = Q2 / Aout        (Aout = area of the outgoing pipe)
Lv1 = Kb(θ1) × V1/3² / 2g
Lv2 = Kb(θ2) × V2/3² / 2g

if Lv1 > Lv2:  θc = θ2
else:          θc = θ1        (the SMALLER loss's angle controls — not the larger)

Vout = TotalFlow / Aout
Hb = Kb(θc) × Vout² / 2g
```

| Variable | Definition | Units |
|---|---|---|
| `Q1, Q2` | Design flow carried by each inflow pipe (via `pipeDesignQ`) | cfs |
| `θ1, θ2` | Deflection angle of each inflow pipe entering this structure | deg |
| `Aout` | Full area of the outgoing pipe | sf |
| `V1/3, V2/3` | Approach velocity of each inflow, referenced to the outgoing pipe's area | fps |
| `Lv1, Lv2` | Hypothetical structure loss if each inflow's angle governed alone | ft |
| `θc` | Controlling angle — the angle belonging to the *smaller* of `Lv1`/`Lv2` | deg |
| `Vout` | Outgoing velocity = Total Flow / Aout (assumes near-full outflow pipe) | fps |
| `Hb` | Structure loss applied at this structure | ft |
| `g` | Gravitational acceleration = 32.2 ft/s² | ft/s² |

**The controlling angle is the smaller loss's angle, not the larger.** This is the key subtlety. The angle that would produce the smaller loss is the one that actually governs the merged flow.

**> 2 inflow pipes:** Not supported by this method. The tool **flags it with a warning** ("the controlling-angle method only supports up to 2. Hb not computed; verify manually") and does not compute Hb. It does not guess.

**Validity / notes**

- `Vout = TotalFlow / Aout` uses the *full* pipe area of the outgoing pipe. This assumes the outgoing pipe runs at or near full depth at the structure — a standard simplification, disclosed in the UI.
- The angle is a property of the *pipe entering the To-structure*, not of the structure itself. A structure with two incoming pipes at different angles uses both angles in the controlling-angle calc.

**Implementation:** `interpKb(columnKey, angleDeg)`, `computeStructureCalc` structure-loss branch (HTML lines ~729–744, 1004–1027).

---

## 6. Hydraulic Grade Line (HGL) Propagation

```
elevation = downstream elevation + Hf + Hb
```

Checked against:
```
elevation ≤ crown + 1.0 ft     (crown clearance)
elevation ≤ rim  − 1.0 ft      (rim/surcharge clearance)
```

| Variable | Definition | Units |
|---|---|---|
| `downstream elevation` | The To-structure's resolved Upstream HGL (computed recursively) | ft |
| `Hf` | Friction loss along this structure's outgoing pipe (Section 4) | ft |
| `Hb` | Structure loss at this structure (Section 5) | ft |
| `crown` | User-entered crown elevation of the outgoing pipe at this structure | ft |
| `rim` | User-entered rim/grate elevation at this structure | ft |

**Base-case (force-elevation) nodes.** A structure with `forceElev = true` (or with no outgoing pipe) is a base case: its elevation is its own `startElev`, full stop. `Sf = Hf = Hb = Vout = 0`. Use this for:

- The **outfall** (free discharge to a channel or receiving water).
- Any point with a **known tailwater** (connection to an existing system, a SWM pond normal pool, etc.).
- The Secondary outfall of a flow-splitter bypass.

**Recursion.** `computeStructureCalc` walks upstream from the outfall through each structure's outgoing pipe. Cycle protection: if a structure id reappears in the seen-set, the recursion returns `elevation = NaN` and flags a circular-reference warning. The chain goes through the **Primary** outgoing pipe of a splitter; the Secondary path is a fully independent downstream chain resolved on its own and does not feed back into the splitter's own elevation.

**Clearance checks.** Both checks are reported as OK / EXCEEDS badges on the structure row. If `crown` or `rim` is blank, that check is skipped (null) rather than failing.

**Implementation:** `computeStructureCalc(structureId, seen)` (HTML line ~945).

---

## 7. Flow Splitter

A structure `type: "splitter"` divides its Total Flow between **two** outgoing pipes — a Primary and a Secondary — instead of the standard one. The split method is per-structure: `capacity` or `ratio`.

```
capacity method:  Primary = MIN(TotalFlow, Capacity)     Secondary = TotalFlow − Primary
ratio method:     Primary = TotalFlow × Ratio             Secondary = TotalFlow − Primary
```

| Variable | Definition | Units |
|---|---|---|
| `TotalFlow` | The splitter's total inflow (captured + Σ inflow pipes), per Section 1.3 of the spec | cfs |
| `Capacity` | User-entered capacity limit on the Primary path (`splitCapacity`) | cfs |
| `Ratio` | User-entered fraction to the Primary path (`splitRatio`, clamped to 0–1) | — |

**Pipe role.** Each outgoing pipe from a splitter has `splitRole: "" | "primary" | "secondary"`. Exactly one Primary and one Secondary are required; if that is not satisfied, the row flags a warning and the split is not computed.

**Loss handling at the splitter itself.**

- **Hf** (friction loss) uses only the **Primary pipe's** carried flow. The Primary pipe is the one whose downstream chain continues the splitter's own elevation.
- **Hb** (structure loss) uses the **full Total Flow**, since that governs the turbulence of the merging inflow before the split happens.
- The Secondary path is a fully independent downstream chain; it does not feed back into the splitter's own elevation. Its own Hf and Hb are computed in its own `computeStructureCalc` call.

**Why this matters.** `pipeDesignQ` has a branch: if the From-structure is a splitter, it returns the Primary or Secondary share instead of the full Total Flow. Every inflow contribution everywhere in the network is routed through `pipeDesignQ` — never around it. Routing directly through `computeTotalFlow` would silently double-count flow once splitters exist.

**Implementation:** `computeSplitterSplit(st, totalFlow)`, `pipeDesignQ(pipeRow, seen)` (HTML lines ~878–924).

---

## 8. Outlet Structure Hydraulics

A **separate concept** from the conveyance network. This builds a stage-discharge rating curve for a BMP/SWM/ESD outlet structure (a pond riser), not a peak-flow capacity check. Multiple devices on one facility all discharge at the same shared headwater and their flows **add together** at every stage — that is the composite rating curve.

### 8.1 Circular segment geometry — exact, not approximated

For a circular orifice or pipe flowing to depth `h` above its invert, radius `R`:

```
α = cos⁻¹(1 − h/R)                                  (half-angle, radians)
A = R² × (2α − sin 2α) / 2                          (exact wetted area)
centroid_above_invert = R − 4R·sin³α / (3 × (2α − sin 2α))
hc = h − centroid_above_invert                      (head to the wetted area's own centroid)
```

| Variable | Definition | Units |
|---|---|---|
| `h` | Water depth above the opening's invert (clamped to 0…2R) | ft |
| `R` | Opening radius = diameter/2 | ft |
| `α` | Half-angle subtended at the center by the water surface | rad |
| `A` | Wetted (flow) area of the circular segment | sf |
| `centroid_above_invert` | Height of the wetted area's centroid above the invert | ft |
| `hc` | Head from the water surface down to the wetted area's centroid | ft |

**Half-full closed-form verification.** At `h = R` (half full), the equations must reproduce the classical semicircle results exactly:
- `A = πR²/2`
- `centroid_above_invert = 4R/(3π)` (i.e. `hc = R − 4R/(3π)`)

If a derivation does not reproduce these at half-full, it has a sign error — do not ship it. The implementation (`circularSegment`, HTML line ~1058) verifies this.

**Known limitation — centroid-head Jensen-inequality overestimate.** Driving head = head to the area's *centroid* is the standard industry approach, but it is not literally exact. Because `√h` is concave, the average of `√h` over the wetted area is always ≤ `√(average h)` (Jensen's inequality). The resulting overestimate is:

- **Exactly zero** at the empty boundary (`h = 0`) and at the full boundary (`h = 2R`).
- **Small in between** — typically low single-digit percent in the mid-range.
- **Standard practice** — matches HydroCAD/PondPack-style tools, not unique to this tool. Disclosed in the UI; not a defect.

### 8.2 Orifice / Pipe — flow regimes

Three regimes, continuous at the boundaries:

```
if HW ≤ invert:                                       Q = 0                              (dry)

if invert < HW < invert + 2R:                         Q = Cd × A(h) × √(2g × hc)         (partial — use 8.1)
                                                        A(h), hc from circularSegment

if HW ≥ invert + 2R:
    if TW active and TW > invert + 2R:                 H = HW − TW                        (submerged, differential head)
    else:                                              H = HW − (invert + R)              (full, free discharge)
    Q = Cd × A × √(2g × H),   A = πR²
```

| Variable | Definition | Units |
|---|---|---|
| `HW` | Headwater (stage) | ft |
| `TW` | Tailwater elevation (only active if `twMode ≠ "none"` and finite) | ft |
| `invert` | Opening invert elevation | ft |
| `R` | Opening radius | ft |
| `top` | `invert + 2R` — top of opening | ft |
| `Cd` | Discharge coefficient (default 0.6) | — |
| `A` | Wetted area (partial) or full area `πR²` (full/submerged) | sf |
| `hc` | Head to centroid (partial regime, Section 8.1) | ft |
| `H` | Driving head (full/submerged regime) | ft |
| `g` | 32.2 ft/s² | ft/s² |

**Continuity at the partial → full boundary.** As `h → 2R` in the partial branch, `hc → R`, so the partial formula `Cd × A × √(2g × hc)` approaches `Cd × πR² × √(2g × R)`, matching the full-flow formula's `H = HW − (invert + R)` exactly at that point. The implementation enforces this.

**"Pipe" device ≠ HDS-5 culvert analysis.** A "pipe" device here is treated as a large orifice / short culvert barrel (appropriate for a pond outlet barrel), not a full inlet/outlet-control culvert analysis per FHWA HDS-5. Disclosed in the UI.

### 8.3 Weir — free flow

```
if HW ≤ crest:                                   Q = 0

H1 = HW − crest
rectangular:  Qfree = C × L × H1^1.5
V-notch:      Qfree = C × tan(θ/2) × H1^2.5
```

| Variable | Definition | Units |
|---|---|---|
| `crest` | Weir crest elevation | ft |
| `H1` | Headwater head above crest | ft |
| `L` | Weir length | ft |
| `θ` | V-notch angle (full angle, degrees; converted to rad internally) | deg |
| `C` | Weir coefficient (default ≈ 3.1 rectangular, ≈ 2.5 V-notch) | — |

### 8.4 Weir — submerged flow (Villemonte correction)

```
if TW active and TW > crest:
    H2 = TW − crest
    if H2 ≥ H1:                       Q = 0                (drowned — no net driving head)
    else:
        n = 1.5 (rect) or 2.5 (V-notch)
        factor = [1 − (H2/H1)^n]^0.385               (Villemonte submergence correction)
        Q = Qfree × factor
else:
    Q = Qfree
```

| Variable | Definition | Units |
|---|---|---|
| `H2` | Tailwater head above crest | ft |
| `n` | Weir exponent: 1.5 rectangular, 2.5 V-notch | — |
| `factor` | Villemonte submergence reduction factor | — |
| `Qfree` | Unsubmerged discharge from 8.3 | cfs |

**Validity / notes**

- Submergence is only applied when `twMode ≠ "none"` and `TW` is finite. With `twMode = "none"`, free discharge is assumed everywhere.
- When `H2 ≥ H1` the weir is fully drowned and `Q = 0`.
- Villemonte's factor `[1 − (H2/H1)^n]^0.385` is the standard empirical submergence correction; the exponent 0.385 is fixed.

### 8.5 Composite curve

At every stage, each device's Q is computed per 8.2 (orifice/pipe) or 8.3–8.4 (weir), and the **Total Q = Σ Q across all devices** on that facility. Devices never share a stage range or tailwater across facilities — each facility has its own.

### 8.6 Stage-list generation

Given `startElev` / `endElev`, the tool walks in `coarseIncrement` steps across the whole range, then inserts `fineIncrement`-spaced points within `±fineBand` of every device's invert, top-of-opening, and crest (and of the resolved tailwater elevation, if any) — that is where the governing equation switches and the curve bends the most. Points are deduped and sorted. Total rows are capped at 2000; if exceeded, the table is thinned evenly for display and a warning is shown.

**Per-device precision (Phase 5).** Facility-level `precisionMode`:
- `uniform` — every device uses the facility's default fine increment/band.
- `individual` — each device gains a Custom checkbox and its own increment/band fields. A band override of `0` is legitimate and means "skip fine refinement near this device's critical elevation entirely" (useful for a rarely-active emergency spillway).

### 8.7 Tailwater modes

| Mode | Behavior |
|---|---|
| `none` | Free discharge — TW ignored everywhere. |
| `fixed` | A constant elevation the user types in. |
| `linked` | Resolves live to a Junction Structure's computed **Upstream HGL** from the conveyance network (Section 6). A single resolved elevation — not a stage-dependent curve — since the linked structure's Total Flow is a fixed design value, not itself a function of the pond's stage. |

The `linked` mode is the payoff for building the conveyance network and the outlet-structure rating curve in the same app.

**Implementation:** `circularSegment`, `orificeOrPipeQ`, `weirQ`, `deviceQ`, `resolveTailwater`, `generateStageList`, `computeRatingCurve` (HTML lines ~1058–1229).

---

## 9. Assumptions & Disclosed Limitations

Read before relying on results for submittal. These are standard industry simplifications, disclosed in the UI, not defects.

1. **Centroid-head Jensen-inequality overestimate (Section 8.1).** Partial-flow orifice/pipe discharge uses the exact wetted area and the head to that area's own centroid. Exact at the empty (`h = 0`) and full (`h = 2R`) boundaries; a small (typically low single-digit percent) overestimate in between, because `√h` is concave and the average of `√h` over the area is always ≤ `√(average h)` (Jensen's inequality). Matches HydroCAD/PondPack-style tools. Per-device fine increment/band override lets you tighten resolution exactly where it matters most — typically a small low-flow orifice — without changing the whole facility's precision.

2. **Outlet Structure "Pipe" device ≠ HDS-5 culvert analysis (Section 8.2).** A "pipe" device is treated as a large orifice / short culvert barrel (appropriate for a pond outlet barrel), not a full inlet/outlet-control culvert analysis per FHWA HDS-5.

3. **Kb defaults identical across structure-type columns (Section 5.1).** All three columns (Inlet / Manhole / Bend) are seeded with the same published AASHTO bend-loss curve. The default is deliberately conservative — it does not silently pretend agency-specific differences are known. The user is expected to enter their governing Appendix B chart's values per column before relying on structure losses for submittal. Column use: Inlet → `inlet`, Manhole → `manhole`, Bend → `bend`, Junction → `bend`, Flow Splitter → `manhole`, Outfall → none.

4. **Vout assumes near-full outflow pipe (Section 5.2).** `Vout = TotalFlow / Aout` uses the *full* pipe area of the outgoing pipe — i.e. it assumes the pipe runs at or near full depth at the structure. This is a standard simplification for converging storm-drain trees sized to carry their design flow at or near full capacity.

5. **Controlling-angle method supports up to 2 inflow pipes (Section 5.2).** Structures with more than 2 inflow pipes are flagged with a warning and Hb is not computed. The tool does not guess.

6. **One Primary outgoing pipe per structure (Section 7).** The standard converging storm-drain tree assumes one outgoing pipe per structure. A Flow Splitter is the one exception, with a Primary + Secondary pair.

7. **Rational Method is a peak-flow, small-catchment method (Section 1).** The tool does not check catchment size or applicability — the user is responsible for confirming it is appropriate for their project.

---

## 10. Traceability Note

Every computed value shown anywhere in the app — the main tables, the per-row **⤢ Detail** calc sheets, and the Excel export — derives from the same governing equations documented above, implemented by the same functions (`calcDrainageRow`, `manningFullFlow`, `frictionSlope`, `interpKb`, `computeStructureCalc`, `computeSplitterSplit`, `circularSegment`, `orificeOrPipeQ`, `weirQ`, `computeRatingCurve`, the TR-55 segment functions). The **Formulas & Examples tab** computes its worked examples **live from the current project data** through those exact functions — nothing in that reference is hand-typed, so it cannot drift out of sync with what the calculators actually do.

The **Excel export** uses the same equations either as **live formulas** (for the linear/lookup chains — Drainage Q, Captured Q, Q-from-pipes, Total Flow, Design Q including splitter shares, Hf, Vout, Hb, the chained Upstream HGL, each rating row's Total Q, the tailwater column) or as **cached static values** (for the trigonometric/branching ones — Kb with controlling-angle selection, the orifice/weir regime math with partial-full-submerged branching and Villemonte submergence, elliptical pipe areas). Cached values are computed by the same functions and written with a clear note that they are app-computed and editable-to-override; on import, only the input columns are read back and everything else is recomputed live. Cross-sheet links key on user-facing labels (Structure ID, drainage row ID, facility Label), not internal row ids.

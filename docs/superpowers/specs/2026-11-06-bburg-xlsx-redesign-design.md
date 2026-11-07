# bburg-p-c.xlsx Redesign — Reusable PG/MoCo/DC Storm-Drain Template

- **Date:** 2026-11-06
- **Status:** Design approved; awaiting user review before implementation plan
- **Author:** Khiem Hoang Nguyen (via Claude brainstorming)

## 1. Goals

Replace the broken project-specific `docs/bburg-p-c.xlsx` with a reusable, formula-driven template for PG/MoCo/DC storm-drain design. The template must:

1. Compute HGL and EGL end-to-end from a user-specified **starting tailwater** at the most-downstream pipe, propagating upstream through every pipe and structure using the HEC-22 EGL procedure (full-flow Manning's Sf with a crown floor on HGL_dn — appropriate for MDSHA, PG County, and MCDrainage reviews).
2. Let the user pick **county** (MoCo, PG, DC — more addable) and **storm frequency** from dropdowns, driving all IDF lookups.
3. Let the user pick **junction loss type** (inlet / manhole / bend / junction) per MCDrainage, with the Kb coefficient auto-looked-up by (angle, type).
4. Support **multiple drainage areas per inlet** via a long-table data source, with the familiar per-inlet Rational Method report view auto-filled from that table.
5. Eliminate all hard-coded inter-sheet cell references (`'Rationals-MCDOT'!D20` etc.) and all broken `#REF!` and external-workbook links.
6. Mirror the logic of `drainage-calculator/storm-drain-design-calculator-dev.html` so the two tools agree.

## 2. Non-goals

- Pond outlet-structure rating curves in Excel. Tailwater is a user-typed elevation per storm. If an engineer needs to compute pond stage, they do it externally (HydroCAD, the HTML calculator's outlet-structure rating, hand calc) and type the result in.
- Changes to the HTML calculator to link OUTFALL tailwater to a pond rating curve. That's a separate follow-on spec.
- Inlet spread hydraulics beyond what the current `Inlet Spacing_*` sheets do — only the referencing is rewired, not the computation.
- Preserving the three broken HGL sheets. They are deleted and replaced by one generalized `HGL` sheet.

## 3. Constraints

- Must open and work in Excel for Microsoft 365 (team's primary tool). Compatibility with LibreOffice is a stretch goal but not required.
- Each formula must be self-documenting (structured table references preferred over A1).
- Workbook produced by a reproducible builder script in the repo, not hand-edited.
- Legacy workbook `docs/bburg-p-c.xlsx` is preserved as `docs/bburg-p-c-legacy.xlsx` for diff reference.

## 4. High-level architecture

```
+----------+        +------------------+        +--------------+
| Config   | -----> | NOAA14 (county   | -----> | IDF_Lookup   |
|  County  |        |  x storm x dur)  |        | (Tc -> i)    |
|  Storm   |        +------------------+        +--------------+
+----------+                                            |
     |                                                  v
     v                                        +---------------------+
+----------------+  SUMIFS by Inlet_ID        | Rationals-MCDOT     |
| DA_Catchments  |----------------------------| (per-inlet report   |
| (long table)   |                            |  view, auto-filled) |
+----------------+                            +---------------------+
     |                                                  |
     | SUMIFS by Inlet_ID                               |
     v                                                  v
+------------------+                          +---------------------+
| Inlet Spacing_   |                          | Pipe Capacity (10, |
| 10-yr / 2-yr     |                          |  25 yr)            |
+------------------+                          +---------------------+
                                                        |
+--------------+     VLOOKUP by (angle,type)            v
| Kb_Values    |----------------------------->  +-------------+
| (MCDrainage) |                                |    HGL      |
+--------------+                                | (starts at  |
                                                |   TW input, |
+----------------+                              |   walks     |
| Pipe_Properties|----------------------------->|   upstream) |
+----------------+                              +-------------+
```

**Source of truth is always the long table or the lookup table.** Every downstream sheet derives via SUMIFS / VLOOKUP / INDEX-MATCH / XLOOKUP — never a hard-coded cell address.

## 5. Sheets — detailed specs

### 5.1 `Config` (new)

Scalar inputs that drive the whole workbook. Named ranges (workbook-scoped).

| Name | Value | Notes |
|---|---|---|
| `County_Selected` | dropdown: `Montgomery`, `Prince George's`, `DC`, … | data validation sourced from `NOAA14[County]` |
| `Storm_Primary` | dropdown: `2yr`, `10yr`, `25yr`, `100yr`, … | the storm the Inlet Spacing & HGL sheets default to |
| `HGL_Method` | dropdown: `HEC-22 EGL (d/s crown floor)` [default], `Legacy both-end crown floor` | drives the `HGL` sheet; see §5.13. Both methods use full-flow Sf at design Q |
| `Project_Name` | text |  |
| `Project_Number` | text |  |
| `Designer`, `Checker`, `Date_Computed` | text/date |  |
| `Manning_n_RCP` | 0.013 |  |
| `Manning_n_HDPE` | 0.012 |  |
| `Gravity_g` | 32.2 | ft/s² |
| `Rim_Freeboard` | 1.0 | ft, structure check limit |
| `Crown_Freeboard` | 1.0 | ft, pipe surcharge check |

**Default table seed sizes** (tables auto-extend when you type past the last row; these are initial blank-row counts shipped by the builder):

| Table | Default row count |
|---|---|
| `DA_Catchments` | 100 |
| `Structures` | 100 |
| `Pipes` | 200 |

### 5.2 `NOAA14` (new)

Excel Table `NOAA14` — all MD counties + DC. Columns:

`County | lat | lon | Storm | d5 | d10 | d15 | d30 | d60`

where `Storm` is one of `1yr … 500yr` and `d5` … `d60` are depths (in) at 5 / 10 / 15 / 30 / 60-minute durations. Initially populated for `Montgomery`, `Prince George's`, `DC`; rows for other counties present but blank (data from `drainage-calculator/storm-drain-design-calculator-dev.html` lines 1020–1134 is the authoritative seed source).

### 5.3 `IDF_Lookup` (new)

Replaces `SHA Intensity`, `MoCoIntensity`, `Intensity`.

Columns: `Tc_min | i_1yr | i_2yr | i_5yr | i_10yr | i_25yr | i_50yr | i_100yr | i_500yr`

Rows: Tc from 5 to 60 minutes in 0.1-min increments (matches current `SHA Intensity` / `MoCoIntensity` resolution).

Each intensity cell is a power-law fit using the two bracketing durations from `NOAA14` for `County_Selected`, matching the HTML calculator's `interpolatePL()` (dev HTML line 1178). Formula template:

```excel
i(Tc, storm) =
  LET( d_lo, INDEX(NOAA14[d5:d60], MATCH([@County]&storm, …), low_idx),
       d_hi, INDEX(…, high_idx),
       t_lo, duration_lo,
       t_hi, duration_hi,
       b,    LN(d_hi/d_lo) / LN(t_hi/t_lo),
       a,    d_lo / t_lo^b,
       60 * a * [@Tc_min]^b / [@Tc_min] )
```

Consumers read with a single `XLOOKUP([@Tc], IDF_Lookup[Tc_min], IDF_Lookup[i_{storm}])`.

### 5.4 `DA_Catchments` (new — source of truth for Rational Method)

Excel Table `DA_Catchments`. Columns:

`Inlet_ID | DA_ID | Soil | Slope | Landuse | Area_SF | C_2-10 | C_25 | Notes`

- `Inlet_ID` — data validation against `Structures[Structure_ID]`.
- `Soil` — dropdown: `A | B | C | D | ---`.
- `Slope` — dropdown: `0-2% | 2-7% | 7%+ | ---`.
- `Landuse` — dropdown from a `Landuse_Lookup` table (see 5.5).
- `C_2-10` and `C_25` — defaults auto-populated from `Landuse_Lookup` by `XLOOKUP(Landuse, …)`, user can override.
- `Area_SF` — raw square feet; conversion to acres happens in consumers.

One row per drainage subarea. An inlet with 3 subareas = 3 rows with the same `Inlet_ID`.

### 5.5 `Landuse_Lookup` (new)

Excel Table. Columns: `Landuse | C_2-10 | C_25 | Description`.

Seeded with the canonical set from `Rationals-MCDOT` (Impervious, Open Space, Woods, etc.) plus MCDOT/MDOT-SHA standards. Adds a column so `DA_Catchments` can XLOOKUP default C values.

### 5.6 `Structures` (new)

Excel Table. One row per physical structure. Columns:

`Structure_ID | Type | Description | Rim_Elev | Inv_In_Elev | Inv_Out_Elev | Angle_deg | Linked_Pond_TW`

- `Type` — dropdown: `inlet | manhole | bend | junction | splitter | outfall`. Matches HTML calc's `KB_COLUMN_FOR_TYPE` (dev HTML line 1434).
- `Angle_deg` — angle between inflow and outflow pipes, 0–180. Drives `Kb_Values` lookup.
- `Linked_Pond_TW` — optional: if non-blank for a structure of `Type = outfall`, the HGL sheet uses this value as the starting TW for the storm selected. Otherwise TW comes from the HGL sheet's own TW input cell.

### 5.7 `Pipes` (new)

Excel Table. One row per pipe reach. Columns:

`Pipe_ID | From_Structure | To_Structure | Length_ft | Size_in | Material | Manning_n | Slope_ftft`

- `From_Structure`, `To_Structure` — data validation against `Structures[Structure_ID]`.
- `Material` — dropdown: `RCP | HDPE | CMP | PVC | DIP | Other`.
- `Manning_n` — defaulted from `Material` via `XLOOKUP`, user-overrideable.
- `Size_in` — dropdown from `Pipe_Properties[Size]`.

### 5.8 `Pipe_Properties` (kept, extended)

Keep the existing `Size | Area | Perimeter | Hyd Radius` plus the partial-flow lookup `y/do | A/do² | AR^(2/3)/do^(8/3)`. Promote to Excel Table named `Pipe_Properties`. Partial-flow lookup promoted to a second table `PartialFlow`.

### 5.9 `Kb_Values` (renamed from `Kb Values MoCo`, extended)

Excel Table. Columns:

`Angle | Inlet | Manhole | Bend | Junction`

Values come from the current `Kb Values MoCo` and the MCDrainage design-criteria PDF (`docs/MCDrainageDesignCriteria10thRevised1Final.pdf`). The `Junction` column is new — per MCDrainage it equals the `Bend` column (same Kb curve applies to a flow-through junction where the dominant inflow aligns with the outflow). This is confirmed by the HTML calc's mapping (dev HTML line 1434: `junction:"bend"`).

Consumer formula:

```excel
Kb_at_structure =
  LET( t, [@Type],
       kb_col, SWITCH(t, "inlet", Kb_Values[Inlet],
                        "manhole", Kb_Values[Manhole],
                        "bend", Kb_Values[Bend],
                        "junction", Kb_Values[Junction],
                        "splitter", Kb_Values[Manhole],
                        0),
       XLOOKUP([@Angle], Kb_Values[Angle], kb_col, 0, -1) )
```

### 5.10 `Rationals-MCDOT` (kept — same look, auto-filled)

The per-inlet report view that engineers already read. Each block (one inlet) now auto-fills from `DA_Catchments`:

```
Inlet EX-I-1       BY: ... DATE: ...
----------------------------------------------------------------------
Soil  Slope  Landuse        Area_SF   C(2-10)  CA(2-10)  C(25)  CA(25)
D     2-7%   Impervious     2209.54   0.90     1988.6    0.90   1988.6
D     2-7%   Open Space      184.74   0.24       44.3    0.24     44.3
      TOTALS                 2394.3            2032.9           2032.9
      Composite C                               0.848            0.848
      Tc = [input]   min
      Rainfall intensity (in/hr): 2=4.01  10=6.68  25=7.93 (from IDF_Lookup)
      Q = CA * i / 43560 : 2=...  10=...  25=...
```

Each block reads from `DA_Catchments` by Inlet_ID:

- Row listing: a dynamic array `FILTER(DA_Catchments, DA_Catchments[Inlet_ID]=[@Inlet_ID])` produces the sub-table.
- Total Area: `SUMIFS(DA_Catchments[Area_SF], DA_Catchments[Inlet_ID], [@Inlet_ID])`.
- SumCA by storm: `SUMPRODUCT((DA_Catchments[Inlet_ID]=[@Inlet_ID]) * DA_Catchments[Area_SF] * DA_Catchments[C_x])`.
- Composite C: `SumCA / SumArea`.
- Intensity: `XLOOKUP(Tc_rounded, IDF_Lookup[Tc_min], IDF_Lookup[i_{storm}])`.

The current fixed-3-per-row horizontal layout is preserved so printed calc sheets keep their familiar look. The builder script generates one block per Inlet_ID found in `DA_Catchments`.

### 5.11 `Inlet Spacing_10-yr`, `Inlet Spacing_2-yr` (kept — rewired)

Same columns as today. All `='Rationals-MCDOT'!D20` style refs replaced with:

- `C (runoff coef)` → composite C via `SUMPRODUCT(...)/SUMIFS(Area,...)` on `DA_Catchments`.
- `CA` → `SUMPRODUCT(...)` on `DA_Catchments`.
- `Area (ac)` → `SUMIFS(DA_Catchments[Area_SF], ..., [@Inlet]) / 43560`.
- `Tc` → `XLOOKUP(Inlet, Tc_table[Inlet_ID], Tc_table[Tc_min])` (new small `Tc_table` sheet, or a column on `Structures`).
- `I10` / `I2` → `XLOOKUP([@Tc], IDF_Lookup[Tc_min], IDF_Lookup[i_10yr])` (or `i_2yr`).

Column headers, data validation, and print layout unchanged.

### 5.12 `10 Yr Pipe Capacity`, `25 Yr Pipe Capacity` (kept — rewired, SHA sheet renamed)

Same columns. `25 Yr SHA Pipe Capacity` → `25 Yr Pipe Capacity` (county-agnostic; reads `County_Selected`). All inter-sheet refs become SUMIFS by Inlet_ID into `DA_Catchments` and XLOOKUP into `IDF_Lookup` + `Pipe_Properties` + `Pipes`.

Two small additions:
- Column pulls `Manning_n` from `Pipes[Manning_n]` (which defaults from material), so you no longer type `0.013` on every row.
- Column pulls `Slope` from `Pipes[Slope_ftft]`.

### 5.13 `HGL` (new — single sheet, replaces three broken sheets)

The core new capability. One row per pipe reach, ordered downstream-to-upstream (or an `Order` column that sorts downstream-first).

**Two methods, user-selectable via `Config.HGL_Method`:**

1. **`HEC-22 EGL (d/s crown floor)` — DEFAULT.** Textbook HEC-22 procedure. Full-flow Manning's Sf at design Q. At the **downstream** end of each pipe, if the arriving HGL is below the crown of that pipe's d/s end, HGL_dn is raised to the crown. The upstream HGL is `HGL_dn + Hf` — no second floor at the u/s end. Reviewer-friendly; standard MDSHA/PG/MoCo practice.

2. **`Legacy both-end crown floor`.** Matches the behavior of the existing `10 Yr MoCo HGL` sheet in `bburg-p-c.xlsx` (which was the firm's apparent prior convention). Crown floor is applied at **both** the d/s AND u/s ends: `HGL_up = MAX(HGL_dn + Hf, Crown_up)`. More conservative — pins any gravity reach at its upstream crown too. Available for projects where the reviewer expects this historical behavior.

Both methods share:
- Full-flow Sf at design Q: `Sf = (Q·n / (1.486·A_full·R_full^(2/3)))²`
- `Hf = Sf · L`
- `Hb = Kb · Vh` using the velocity head of the **outflow** pipe (= this row's own Vh), per MCDrainage / HEC-22 §7.4
- Crown floor at d/s is always on (both methods)

Top-of-sheet inputs:
- `TW_Elev_Start` — starting tailwater at the most-d/s pipe for `Storm_Primary`. Default `=Soffit of last pipe` for free-discharge. Can be overridden by a `Structures[Linked_Pond_TW]` on the outfall row.
- `Storm_Selected` — dropdown, defaults to `Storm_Primary`.
- `Method_Selected` — reads `Config.HGL_Method`; shown at top of sheet for printed-record clarity.

Columns:

| Column | Source / Formula |
|---|---|
| Pipe_ID | `Pipes[Pipe_ID]` (sorted downstream-first) |
| From, To | `Pipes[From_Structure]`, `Pipes[To_Structure]` |
| Q (cfs) | from `{Storm} Yr Pipe Capacity` by Pipe_ID |
| Size (in) | `Pipes[Size_in]` |
| Length (ft) | `Pipes[Length_ft]` |
| n | `Pipes[Manning_n]` |
| Area (ft²) | `XLOOKUP(Size, Pipe_Properties[Size], Pipe_Properties[Area])` |
| R (ft) | `XLOOKUP(Size, Pipe_Properties[Size], Pipe_Properties[Hyd Radius])` |
| V (fps) | `Q / Area` |
| Vh = V²/(2g) | `V^2 / (2 * Gravity_g)` |
| Sf (ft/ft) | `(Q * n / (1.486 * Area * R^(2/3)))^2` |
| Hf (ft) | `Sf * Length` |
| Inv_dn (ft) | `XLOOKUP(From, Structures[Structure_ID], Structures[Inv_Out_Elev])` |
| Inv_up (ft) | `XLOOKUP(To, Structures[Structure_ID], Structures[Inv_In_Elev])` |
| Crown_dn (ft) | `Inv_dn + Size/12` |
| Crown_up (ft) | `Inv_up + Size/12` |
| Type (u/s struct) | `XLOOKUP(To, Structures[Structure_ID], Structures[Type])` |
| Angle (u/s struct) | `XLOOKUP(To, Structures[Structure_ID], Structures[Angle_deg])` |
| Kb | SWITCH + XLOOKUP into `Kb_Values` (see 5.9); Kb for the structure at the u/s face of **this** pipe |
| Hb (ft) | `Kb * Vh` — uses this row's own Vh |
| HGL_dn_raw (ft) | first (most-d/s) row: `TW_Elev_Start`. Subsequent rows: `EGL_dn − Vh` |
| HGL_dn (ft) | `MAX(HGL_dn_raw, Crown_dn)` — crown floor at d/s applied in both methods |
| EGL_dn (ft) | first (most-d/s) row: `HGL_dn + Vh`. Subsequent rows: `EGL_up of row below + Hb of row below` (row below = the pipe one closer to the outfall) |
| HGL_up_raw (ft) | `HGL_dn + Hf` |
| HGL_up (ft) | **If `HGL_Method = HEC-22 EGL (d/s crown floor)`:** `HGL_up_raw`. **If `HGL_Method = Legacy both-end crown floor`:** `MAX(HGL_up_raw, Crown_up)` |
| EGL_up (ft) | `HGL_up + Vh` |
| Regime | `IF(HGL_dn_raw >= Crown_dn, "Pressurized", "Gravity — d/s crown floor applied")`; a second annotation `"u/s crown floor also applied"` appears when `HGL_Method = Legacy` and `HGL_up_raw < Crown_up` |
| Rim (u/s) | `XLOOKUP(To, Structures[Structure_ID], Structures[Rim_Elev])` |
| Crown + 1 ft check | `IF(HGL_up > Crown_up + Crown_Freeboard, "FAIL", "OK")` |
| Rim − 1 ft check | `IF(HGL_up > Rim - Rim_Freeboard, "FAIL", "OK")` |

The TW cell seeds the walk; changing it ripples through every row above it automatically. Chain: `TW → HGL_dn (with crown floor) → +Vh = EGL_dn → +Hf (via EGL_up intermediate) → HGL_up → +Hb at structure → EGL_dn of next pipe upstream → ... → headwall`.

### 5.14 `HGL_Example` (new — educational step-by-step, both methods side-by-side)

Pre-populated worked example: a small network with 4 pipes and 5 structures (including an endwall as the downstream starting point). All numbers are **live formulas** off a small input block at the top — change the TW or a pipe size and every step re-computes. **Both HGL methods are computed and shown side-by-side** so engineers can see exactly how `HEC-22 EGL (d/s crown floor)` and `Legacy both-end crown floor` diverge.

**Example network shipped by default:**

```
 [S-1 inlet]--P-1(12",60')-->[S-2 manhole, 0°]--P-2(15",95')-->
   [S-3 bend, 15°]--P-3(18",110')-->[S-4 inlet, 0°]--P-4(24",80')-->[OUTFALL endwall]
```

**Sheet layout:**

Section 1 — **Inputs** (editable):
- Starting tailwater at endwall: `97.00` ft (default; user can change)
- Storm: `10-yr` (dropdown)
- Table of 4 pipes (Len, Size, n, Q, From/To, u/s structure type, angle)
- Table of 5 structures (Rim, Inv_in, Inv_out)

Section 2 — **Network sketch** (ASCII art in merged cells so engineers see the topology without a diagram).

Section 3 — **Step-by-step walk, downstream → upstream.** For each pipe one "block" with four columns:

- `Equation (symbolic)` — the formula with its variable names
- `Substituted values` — the formula with live numbers plugged in
- `HEC-22 (d/s floor)` — result under the DEFAULT method
- `Legacy both-end floor` — result under the alternative method (diverges where the crown floor is applied at the u/s end)

Rows per pipe block (~16 rows):

| Equation (symbolic) | Substituted values | HEC-22 (d/s floor) | Legacy both-end |
|---|---|---|---|
| `Area = π·(D/12)² / 4` | `π·(24/12)²/4` | `3.1416 ft²` | same |
| `V = Q / Area` | `9.5 / 3.1416` | `3.024 fps` | same |
| `Vh = V² / (2g)` | `3.024² / (2·32.2)` | `0.142 ft` | same |
| `R = D/4` | `24/12/4` | `0.500 ft` | same |
| `Sf = (Q·n / (1.486·A·R^(2/3)))²` | `(9.5·0.013 / (1.486·3.1416·0.5^0.667))²` | `0.00178 ft/ft` | same |
| `Hf = Sf · L` | `0.00178 · 80` | `0.142 ft` | same |
| `Crown_dn = Inv_dn + D/12` | `94.00 + 24/12` | `96.00 ft` | same |
| `Crown_up = Inv_up + D/12` | `94.56 + 24/12` | `96.56 ft` | same |
| `HGL_dn_raw = TW_input` (first pipe) | — | `97.00 ft` | same |
| `HGL_dn = MAX(HGL_dn_raw, Crown_dn)` | `MAX(97.00, 96.00)` | `97.00 ft (Pressurized)` | same |
| `EGL_dn = HGL_dn + Vh` | `97.00 + 0.142` | `97.142 ft` | same |
| `HGL_up_raw = HGL_dn + Hf` | `97.00 + 0.142` | `97.142 ft` | `97.142 ft` |
| **`HGL_up` (method-specific)** | HEC-22: `HGL_up_raw`. Legacy: `MAX(HGL_up_raw, Crown_up)` | `97.142 ft` | `MAX(97.142, 96.56) = 97.142 ft` |
| `EGL_up = HGL_up + Vh` | `97.142 + 0.142` | `97.284 ft` | `97.284 ft` |

**Where the two methods diverge:** The u/s crown floor only kicks in when `HGL_up_raw < Crown_up`. In the default example the first pipe is pressurized, so both methods give the same answer. To see divergence, lower `TW_input` to `93.00` and look at pipe P-2 or P-3 upstream: `HGL_up_raw` will fall below `Crown_up` in one of the gravity reaches, at which point the Legacy method pins `HGL_up` at `Crown_up` while HEC-22 keeps `HGL_up_raw`.

**Why Legacy was ever used:** Firm convention from the HGL-under-gravity-flow era, before HEC-22's streamlined EGL procedure became standard. Argument: "the water surface in a gravity pipe must be at least at the crown somewhere along the pipe (e.g., at a structure junction where energy builds up), so floor the reported HGL conservatively." Hydraulically weaker than the HEC-22 procedure, but reviewers who learned on legacy practice may still expect it.

**Regime annotations per pipe:**
- `Pressurized` — `HGL_dn_raw ≥ Crown_dn`
- `Gravity — d/s crown floor applied` — `HGL_dn_raw < Crown_dn` (both methods)
- `Gravity — u/s crown floor also applied` — only when Legacy method AND `HGL_up_raw < Crown_up`

Then at the **upstream structure** of that pipe, one block of ~6 rows. Note: per MCDrainage / HEC-22, `Hb` uses the velocity head of the pipe **leaving** the structure (= this pipe, the one we just walked up), **not** the next pipe upstream. Crown floor is re-checked on the next pipe's `HGL_dn`:

| Equation | Substituted | Result |
|---|---|---|
| `Kb = Kb_Values[Type=inlet, Angle=0]` | lookup | `0.50` |
| `Hb = Kb · Vh(this pipe)` | `0.50 · 0.142` | `0.071 ft` |
| `EGL_dn(next pipe up) = EGL_up(this pipe) + Hb` | `97.284 + 0.071` | `97.355 ft` |
| `Vh(next pipe up) = V(next pipe up)² / (2g)` | compute from Q, Size of next pipe | `0.247 ft` |
| `HGL_dn_raw(next pipe up) = EGL_dn − Vh(next pipe up)` | `97.355 − 0.247` | `97.108 ft` |
| `HGL_dn(next pipe up) = MAX(HGL_dn_raw, Crown_dn)` — crown floor | `MAX(97.108, Crown_dn_P3)` | depends on P-3 invert |

Repeat for P-3, S-3, P-2, S-2, P-1, S-1.

Section 4 — **Checks**: For each pipe/structure, show `HGL_up` vs `Crown + 1 ft` and `Rim − 1 ft` with a PASS/FAIL cell and a note explaining why the check matters.

Section 5 — **Try this**: five guided experiments as sentences with hyperlinks to input cells:
- "Raise TW to 100.0 — note that every HGL ticks up by at least 3 ft (pipes are now surcharged) and HEC-22 and Legacy methods give identical answers (no gravity reaches)."
- "Lower TW to 93.00 (below Crown_dn of P-4 = 96.00) — note P-4 switches to `Gravity — d/s crown floor applied` and HGL_dn pins to 96.00 under BOTH methods."
- "Lower TW to 93.00 AND notice upstream reaches — pipes above the outfall may now trigger `u/s crown floor also applied` under Legacy but not HEC-22. The HGL at upstream structures will diverge between the two columns."
- "Change S-3 from `bend 15°` to `manhole 0°` — note Kb drops from ~0.26 to ~0.15 and HGL at S-1 drops by ~0.03 ft under both methods."
- "Reduce P-2 from 15″ to 12″ — note V and Sf jump, Hf increases, upstream HGL rises under both methods; may also trigger `u/s crown floor` under Legacy if u/s HGL still ends below the smaller crown."

**Implementation note:** the sheet is generated by `build-bburg-template.py`. The "Equation (symbolic)" column is text (`="Area = π·(D/12)² / 4"`). The "Substituted values" column is text that assembles the formula string using `TEXT()` of the live inputs (`="π·("&TEXT(D,"0")&"/12)²/4"`). The "Result" column is a live formula. This gives engineers the live-recompute AND the readable substitution trail.

### 5.15 Sheets deleted

- `10 Yr MoCo HGL` — 303 `#REF!`s, non-functional.
- `25 Yr SHA HGL` — 301 `#REF!`s, non-functional.
- `HGL 25-yr` — 337 `#REF!`s + 583 broken external-workbook refs.
- `SHA Intensity`, `MoCoIntensity`, `Intensity` — subsumed by `NOAA14` + `IDF_Lookup`.

### 5.16 Legacy sheets dropped from the template

- `MD 410 Inlet Drainage Calcs` — project-specific; preserved untouched in the legacy file but not re-emitted by the template builder. If a future project needs an MD 410-style calc, we add a reusable "Project-Specific" sample sheet.
- `TABLES` — merged into `Kb_Values` + `PartialFlow`; original dropped from the template.

## 6. Builder script

New file: `drainage-calculator/build-bburg-template.py`.

Uses `openpyxl` to produce `docs/bburg-p-c-template.xlsx` from code. Script is organized as:

```
build-bburg-template.py
├── seed_data.py          # NOAA14 depths, Kb values, Landuse, Pipe_Properties
├── sheets/
│   ├── config.py
│   ├── noaa14.py
│   ├── idf_lookup.py
│   ├── da_catchments.py
│   ├── landuse_lookup.py
│   ├── structures.py
│   ├── pipes.py
│   ├── pipe_properties.py
│   ├── kb_values.py
│   ├── rationals_mcdot.py
│   ├── inlet_spacing.py
│   ├── pipe_capacity.py
│   └── hgl.py
└── main.py               # wires everything, saves xlsx
```

NOAA14 seed data read directly from `drainage-calculator/storm-drain-design-calculator-dev.html` lines 1020–1134 via a small parser helper, so there's one authoritative source for IDF depths.

Each sheet module:
- Creates the sheet, writes the Excel Table header + data rows.
- Applies styles (font, fill, borders) consistent with the current workbook look.
- Applies data validation (dropdowns) sourced from other tables.
- Writes formulas as raw strings (openpyxl doesn't evaluate them; Excel does when opened).

Builder reads a small `template_seed.yaml` (or just inline dicts) specifying how many blank rows per table ship by default.

## 7. Deliverables

1. `drainage-calculator/build-bburg-template.py` — the builder script.
2. `docs/bburg-p-c-template.xlsx` — the generated template, pre-populated with the Bladensburg SD-1 data as a worked example.
3. `docs/bburg-p-c-legacy.xlsx` — the current workbook, renamed and kept for reference.
4. `docs/bburg-xlsx-user-guide.md` — short usage guide: how to set `County_Selected` and `Storm_Primary`, how to add DAs, how to add pipes, how to read the HGL sheet, how to set TW.

## 8. Testing / verification plan

1. **Golden-file check:** Builder produces a workbook that opens in Excel 365 without repair prompts or formula errors (`#REF!`, `#NAME?`, `#VALUE!`).
2. **IDF cross-check:** For `County_Selected = Montgomery`, `Tc = 10 min`, `Storm = 10yr`, the computed intensity matches the HTML calc's `interpolatePL()` result to ≤ 0.01 in/hr.
3. **Rational Q cross-check:** For `EX-I-1` with the Bladensburg data, `Q_10` from the rebuilt `Rationals-MCDOT` matches the HTML calc's inlet Q on the same inputs.
4. **HGL cross-check:** For a 3-pipe test network with a known TW, the `HGL` sheet's HGL/EGL at every pipe matches the HTML calc's HGL walker to ≤ 0.01 ft.
5. **Junction-type check:** Changing a structure's `Type` from `manhole` to `bend` changes its Kb and propagates HGL/EGL upstream; validated against MCDrainage Table of Kb values.
6. **TW sensitivity:** Raising `TW_Elev_Start` by 1.0 ft raises HGL at every upstream structure by at least 1.0 ft (more if the pipes were pressurized).
7. **`HGL_Example` sanity:** With the default inputs (TW=97.00, 4 pipes, 5 structures), every step's result matches a hand-calc to ≤ 0.01 ft; changing TW to 100.0 raises `HGL_up` at S-1 by ≥ 3.0 ft.
8. **Crown-floor regime switch:** Setting `TW_Elev_Start` below the outfall soffit causes the d/s row to report `Regime = "Gravity — d/s crown floor applied"` and `HGL_dn` to pin to `Crown_dn`, not drop below it. Raising TW back above the soffit flips `Regime` to `"Pressurized"`.
9. **Method toggle divergence:** With the `HGL_Example` default inputs and `TW_Elev_Start = 93.00`, switching `HGL_Method` between `HEC-22 EGL (d/s crown floor)` and `Legacy both-end crown floor` produces identical results for pressurized reaches and ≥0.0 ft divergence on gravity reaches where `HGL_up_raw < Crown_up`. Both methods are documented and visible side-by-side on `HGL_Example`.

## 9. Out of scope / future

- HTML calculator change to let OUTFALL structures link TW to a pond outlet rating curve — **separate follow-on spec.**
- Minor-loss coefficients beyond MCDrainage's Kb at bends/manholes (e.g., FHWA HEC-22 exit loss, bend-at-manhole with multiple inflows). Can be added as additional loss columns on `HGL`.
- Pressurized-flow / surcharge full-fledged analysis (we only check `HGL ≤ Crown + 1 ft` — not full pressure-flow HGL with K-coefficients at every fitting).
- Pond rating-curve sheet in Excel.
- Two-phase pipe HGL (partial flow upstream, full flow at the outfall) using `PartialFlow` table — the template uses full-pipe velocity for Hf, consistent with current MCDOT/SHA practice and the HTML calc.

## 10. Open questions / assumptions

- **Assumption:** MCDrainage's `Junction` Kb equals its `Bend` Kb. The HTML calc makes this mapping (`junction:"bend"`). If MCDrainage specifies a different curve for junctions, the `Kb_Values` table can hold a separate `Junction` column; the SWITCH formula is already wired for it.
- **Assumption:** The legacy `25 Yr SHA` naming reflects a historical dual-criteria (SHA design storm = 25-yr, MoCo design storm = 10-yr) workflow. Template renames to county-neutral `25 Yr Pipe Capacity`.
- **Assumption:** `Tc` is a per-inlet input on `Rationals-MCDOT` (not computed from TR-55 within the workbook). Matches current practice. If we want TR-55 Tc inputs in the template, that's an extension.

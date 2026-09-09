# Design Spec: Inlet Spacing Calculator

## Overview
Add a standalone Inlet Spacing Calculator to the storm drain design tool. This feature replicates the HEC-22-style grate-inlet spacing analysis found in agency-standard workbooks (e.g., Stantec/MD 410 Bladensburg). It determines the required spacing of inlets to maintain a maximum allowable spread on-grade, calculating pickup efficiency and bypass carryover.

## 1. Governing Equations & Methodology
The calculator implements a linear-chain analysis where each inlet's total flow consists of its local contribution plus bypass from upstream inlets.

### 1.1 Hydrology & Flow
- **Total Flow ($Q_{total}$):**
  $$Q_{total} = (C_{local} \times A_{local}) \times i(T_c, \text{Agency, Storm}) + \sum Q_{bypass\_upstream}$$
- **Intensity ($i$):** Piecewise-linear interpolation from agency-specific $T_c$ vs $I$ tables (MoCo/MDSHA). Curve seed data, extracted from `docs/bburg-p-c.xlsx`:
  - **MDSHA** (sheet "SHA Intensity" — defined by rainfall depths at breakpoints, linearly interpolated between, exactly as the workbook does):
    | $T_c$ (min) | 2-yr | 10-yr | 25-yr |
    |---|---|---|---|
    | 5 | 5.016 | 6.684 | 7.572 |
    | 10 | 4.788 | 5.340 | 6.000 |
    | 15 | 3.364 | 4.520 | 5.080 |
    | 30 | — | 3.260 | 3.780 |
  - **MoCo** (sheet "Intensity" — full 1-min table, 5→60 min; 2YR/5YR/10YR columns. Breakpoints shown; store all 56 rows or the equivalent breakpoints that reproduce them):
    | $T_c$ (min) | 2-yr | 5-yr | 10-yr |
    |---|---|---|---|
    | 5 | 5.52 | 6.39 | 7.07 |
    | 10 | 4.28 | 5.16 | 5.85 |
    | 15 | 3.54 | 4.36 | 5.00 |
    | 20 | 3.04 | 3.78 | 4.37 |
    | 30 | 2.40 | 3.02 | 3.49 |
    | 60 | 1.52 | 1.93 | 2.19 |
  - Note: the workbook's own 2-yr spacing sheet used a project-specific flat 4.01 in/hr (not a curve) — the 2-yr curves above are the proper agency curves; manual override covers the flat-rate case.
  - Clamped at table endpoints; a row whose $T_c$ exceeds the range gets the end value plus a note on its detail sheet.
- **Manual Override:** Users can override the computed $i$ per row; an overridden cell is visibly marked and its detail sheet says so.

### 1.2 On-Grade Spread (HEC-22)
- **Spread ($T$):**
  $$T = \left( \frac{Q \cdot n}{0.56 \cdot S_x^{1.67} \cdot S^{0.5}} \right)^{0.3745}$$
- **Effective Cross-Slope ($S_{x\_eff}$):**
  Implements the workbook's helper logic accounting for gutter depression ($a$) and width ($W$).
  $$S_{x\_eff} = S_x + \frac{a}{W} \left( 1 - \frac{T_{partial}}{T} \right)$$
- **Sump Inlets:** Treated as weirs; flagged with 100% pickup.

### 1.3 Grate Interception & Pickup
- **Length of Flow ($L_t$):**
  $$L_t = k \cdot Q^{0.42} \cdot S^{0.3} \cdot \left( \frac{1}{n \cdot S_{x\_eff}} \right)^{0.6}$$
  - $k = 0.54$ for $L \ge 15\text{ ft}$
  - $k = 0.58$ for $L < 15\text{ ft}$
  - $k = 0.60$ for $a = 0$ (on-grade, no depression)
- **Interception Efficiency ($E$):**
  - If $L \ge L_t$, then $E = 1.0$ (100%)
  - Else, $E = 1 - (1 - L/L_t)^{1.8}$
- **Bypass Flow:** $Q_{bypass} = Q_{total} \times (1 - E)$

## 2. Structure Library
The library provides presets for MDSHA and MoCo standard structures. Selection auto-fills $L$, $W$, $a$, and $n$ (all remain editable — selection fills, it does not lock).

**Naming** follows the MDSHA Book of Standards Category III index (`docs/category3.pdf`):

| Standard # | Description |
|---|---|
| MD 374.01 | Standard Curb Inlet for Curb Opening Inlet Structures (Sheet 1) |
| MD 374.02 | Standard Curb Inlet for Curb Opening Inlet Structures (Sheet 2) |
| MD 374.11 | Standard Curb Inlet for Combination Inlet Structures (Sheet 1) |
| MD 374.12 | Standard Curb Inlet for Combination Inlet Structures (Sheet 2) |
| MD 374.21 | Standard Curb Inlet for Grate Inlet Structures (Sheet 1) |
| MD 374.22 | Standard Curb Inlet for Grate Inlet Structures (Sheet 2) |
| MD 374.31 | Standard Grate Inlets for COG Inlet Structures (Sheet 1) |
| MD 374.32 | Standard Grate Inlets for COG Inlet Structures (Sheet 2) |
| MD 374.41 | Standard Grate Inlets for Combination Inlet Structures (Sheet 1) |
| MD 374.42 | Standard Grate Inlets for Combination Inlet Structures (Sheet 2) |
| MD 374.51 | Standard Precast Square/Rectangular Grate Inlet Structure (COG) |
| MD 374.52 | Standard Precast Square/Rectangular Combination Inlet Structure (COS) |
| MD 374.61 | Standard Precast Square/Rectangular Combination Inlet Structure (COS) |
| MD 374.63 | Standard Precast Circular Combination Inlet Structure (COS) |
| MD 375.01 | Type C-1a Precast Curb Inlet Structure (COG) |
| MD 375.02 | Type C-1a Precast Curb Inlet Structure (COG) (Sheet 2) |
| MD 375.21 | Type C-1c Precast Curb Inlet Structure (COG) |
| MD 375.22 | Type C-1c Precast Curb Inlet Structure (COG) (Sheet 2) |
| MD 376.01 | Standard Inlet Structure Type A |
| MD 376.02 | Standard Inlet Structure Type A (Sheet 2) |
| MD 376.11 | Standard Inlet Structure Type E |
| MD 378.01 | Standard Precast Concrete Junction Box |

Each library entry stores: standard number, label, grate length options (ft), grate width (ft), gutter depression (ft), gutter Manning's n, and which interception regime it applies to (grate on-grade / sump). **Dimension seeds** come from (a) the reference workbook (grate lengths 5/10/15/20 ft, W = 1.33 ft, a = 0.0833 ft, n = 0.013) and (b) the MDSHA standard sheet details the user supplies. Where an exact published grate dimension is not yet confirmed, the entry ships with the workbook-derived seed values and the UI discloses that dimensions are editable and must be verified against the governing standard book before submittal — the same disclosure pattern the Kb tab already uses for its seeded AASHTO curve.

## 3. User Interface & Interaction

### 3.1 Tab Layout
- **Global Controls:** Project Street, Agency (MDSHA/MoCo), Storm (2, 10, 25-yr), Default Allowable Spread (ft).
- **Main Table:**
  - Columns: Label, Agency, Structure Type, Area (ac), C, $T_c$ (min), $i$ (in/hr), $Q$ (cfs), $S$ (longitudinal), $S_x$ (cross), $W$ (ft), $a$ (ft), $n$, Spread $T$ (ft), Allowable $T$, Pickup %, Bypass To (Label), Bypass CA.
- **Warning State:** Highlight row if Spread $T >$ Allowable $T$.
- **Sump Mode:** If $S$ is set to "SUMP", the spread column shows "—" and Pickup is 100%.

### 3.2 Chaining Logic
- **Bypass To:** A dropdown of existing inlet labels.
- **Bypass Carryover:** An inlet's $CA_{total}$ is the sum of its local $C \times A$ and the $Bypass\_CA$ of all inlets pointing to it.
- **Cycle Detection:** Flag circular references (e.g., I-1 $\to$ I-2 $\to$ I-1) with a warning.

### 3.3 Outputs
- **Detail Sheets:** Every row has a "⤢ Detail" button generating a printable calculation sheet showing the governing equation $\to$ substituted values $\to$ result.
- **Excel Export:** A new "Inlet Spacing" sheet. $Q$ is a live formula; Spread and Pickup are computed values. `bookSST: true` required.

## 4. Integration & Support
- **Kb Preset:** Add "Load MoCo preset" button to the Kb Coefficients tab to populate the 0°–38° angle table (Inlet 0.50→0.98, Manhole 0.15→0.66, Bend 0.01→0.16, values extracted from `docs/bburg-p-c.xlsx` "MoCoIntensity" / "TABLES" sheets). Overwrites current table values (tooltip says so); generic AASHTO seed remains the fresh-load default.
- **Persistence:** Shared with existing Excel import/export. No localStorage.
- **Scope guard:** grate-inlet on-grade + sump only. No curb-opening interception, no slotted drains, no combination-capture decomposition. Structure types whose standard is a combination/curb-opening inlet still appear in the library for their dimensions, but interception math treats every inlet as a grate.

## 5. Test Oracles (from `docs/bburg-p-c.xlsx`, "Inlet Spacing_10-yr" sheet)
Hard-code these rows in the test harness; the implementation must reproduce them to ±0.01 (spread, Lt, pickup %, bypass CA). Global params for that sheet: W = 1.33 ft, a = 0.0833 ft, n = 0.013, allowable spread = 8 ft.

| Inlet | L (ft) | CA local | Bypass CA in | $T_c$ | $i$ | Q (cfs) | $S$ | Sx (grade) | Spread T | Pickup % | Bypass CA out |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EX-I-1 | 11.1 | 0.04667 | 0.29169 | 5 | 6.68 | 2.260 | 0.055 | SUMP | 3.2* | 100 | 0 |
| I-1 | 5 | 0.14289 | 0 | 7 | 6.15 | 0.8788 | 0.044 | 0.01 | 4.10 | 99.25 | 0.00107 |
| I-2 | 15 | 0.18013 | 0 | 5 | 6.68 | 1.2033 | 0.0219 | 0.0212 | 4.90 | 100 | 0 |
| I-3 | 10 | 0.18525 | 0 | 10 | 5.34 | 0.9892 | 0.019 | 0.08 | 5.90 | 100 | 0 |
| I-6 | 5 | 0.15669 | 0.01004 | 10 | 5.34 | 0.8367 | 0.026 | 0.007 | 5.20 | 93.59 | 0.01004 |

\* EX-I-1 is SUMP; its workbook spread (3.2 ft) came from FlowMaster, not the on-grade formula — the oracle test for this row asserts Q, pickup 100%, and bypass 0 only; the sump path renders "—" for spread in the app.

Additional oracle: the workbook's helper-column math must reproduce EX-I-1's upstream-bypass accumulation (`R13+R19` → I-1's own row shows bypass arriving from I-1 and I-7 chains) — covered by the chaining tests below rather than a single-row oracle.

**Edge-case tests (from the approved design):**
1. Zero-area + zero-bypass inlet → blanks, not NaN.
2. Two- and three-inlet chains: bypass CA conservation (upstream Bypass CA = downstream incoming bypass).
3. Cycle (I-1 → I-2 → I-1) → flagged, no hang.
4. Grate length ≥ Lt → exactly 100% pickup, bypass 0, no divide-by-zero.
5. SUMP inlet mid-chain → downstream still receives its bypass (sump = 100% pickup means bypass 0; verify no NaN when a sump row has upstream inflow).
6. Deleting an inlet others bypass to → orphaned references flagged, treated as 0 with warning.
7. Intensity: exact at breakpoints, linear between, clamped beyond ends, per agency/storm.
8. Structure-type selection auto-fills L/W/a/n; editing afterward doesn't reset on re-render.
9. Export/import round-trip with the new sheet + standing OOXML checks (sharedStrings exists; no `t="str"` without `<f>`).

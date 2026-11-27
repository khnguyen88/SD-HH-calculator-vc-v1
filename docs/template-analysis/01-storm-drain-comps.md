# STORM DRAIN COMPS

## Purpose

Central hub sheet that computes Rational Method peak flows, Manning full-flow pipe capacity, friction slope, structure loss (Hx chain), and normal-depth partial-flow columns for every pipe run in the project.

## Headers & ranges

Occupied range: row 1 (project title) through row 98. Active data table: **Table4** at `A10:AR98` (88 pipe rows, 44 columns). Header rows: row 8 (dynamic formula-generated labels) and row 9 (static sub-labels). Rows 1–7 hold project metadata (jurisdiction dropdown at T3, storm-frequency dropdown at H3, project name at A1 linked from `INLET SPACING'!C4`).

## Inputs

User-typed cells (no formula — raw data entry within Table4):
- `A10:A98` — Drainage Row ID (from-node label; also used as row key by all downstream lookups)
- `B10:B98` — To-node ID (downstream structure)
- `N10:N98` — Pipe diameter (in), circular or elliptical size string
- `O10:O98` — Pipe length (ft)
- `P10:P98` — Upstream (U/S) invert elevation (ft)
- `Q10:Q98` — Downstream (D/S) invert elevation (ft)
- `R10:R98` — Angle Out of Pipe (Deg) — Whole # (row-8 header: `'Angle Out of Pipe (Deg) - Whole #'`). The deflection angle at which this pipe leaves the upstream structure, used by the controlling-angle junction-loss computation on columns AD/AE/AF.
- `S10:S98` — Manning's roughness coefficient n for the pipe (row-8 header: `'Manning Coeff'`). Default 0.013 (concrete pipe); user override permitted.
- `W10:W98` — Flow velocity override or design velocity (fps, user-typed)
- `AA10:AA98` — Structure type (Inlet / Manhole / Bend / Junction / Flow Splitter / Outfall)
- `AB10:AB98` — Top/opening elevation of the structure (rim elevation, ft)
- `AG10:AG98` — Inflow pipe 1 angle (degrees)
- `AH10:AH98` — Inflow pipe 2 angle (degrees)
- `AI10:AI98` — SHA 25-year normal depth (ft, Flowmaster output; used by HGL(25YEAR))
- `AK10:AK98` — Lateral / local captured flow (cfs, user-typed)
- `AL10:AL98` — Additional user input (project-specific field)
- `AS10:AS98` — user input field
- `AX10:AX98` — user input field

Dropdown sources:
- `T3` — jurisdiction selector (Montgomery County / Prince George's County / District of Columbia) sourced from `Select_County` defined name → `DATA!$C$1:$C$4`
- `H3` — design storm / return period sourced from `DATA` sheet IDF header row

Workbook-scoped named ranges read: `Select_County` (IDF jurisdiction selector).

## Formulas

### Columns C–H: Incremental Rational Method (engineering-methodology.md §1)

- `C10` Drainage area (acres) → `VLOOKUP(A10, C_FACTOR!$B$6:$V$88, 3, FALSE)` — pulls sub-basin area from C_FACTOR by Row ID
- `D10` Runoff coefficient C → `VLOOKUP(A10, C_FACTOR!$B$6:$V$88, 17, FALSE)` — pulls C from C_FACTOR
- `E10` Tc to inlet (min) → `VLOOKUP(A10, C_FACTOR!$B$6:$V$88, 21, FALSE)` — pulls time of concentration from C_FACTOR
- `F10` A×C incremental → `C10 * D10` — product of area and runoff coefficient (§1: `A` and `C` terms)
- `G10` Rainfall intensity i (in/hr) → multi-jurisdiction `INDEX/MATCH` into `DATA` IDF block keyed on E10 (Tc) and H3 (return period) — §1 `i` term; interpolates for non-integer Tc for MoCo and PG County
- `H10` Incremental Q (cfs) → `F10 * G10` — implements Q = C × i × A (§1; Cf defaults to 1.0)

### Columns I–M: Accumulated Rational Method + TR-55 pipe-time accumulation (engineering-methodology.md §1 and §2)

- `I10` Accumulated area ΣA (acres) → `C10 + SUMIF($B$10:$B$98, $A10, $I$10:$I$98)` — sums all upstream contributing areas routing through this pipe run
- `J10` Accumulated A×C → `F10 + SUMIF($B$10:$B$98, $A10, $J$10:$J$98)` — cumulative weighted runoff coefficient term
- `K10` Design Tc (min) → `MAX(MAX(IF($B$10:$B$98=A10, $K$10:$K$98 + $X$10:$X$98)), E10)` — maximum of (upstream pipe Tc + travel times) and local inlet Tc, per TR-55 §2 accumulated travel time
- `L10` Intensity for design Tc → `INDEX/MATCH` same IDF lookup as G10 but keyed on K10 (design Tc)
- `M10` Total Q (cfs) → `J10 * L10` — accumulated Q = ΣAC × i (§1 with accumulated AC and design Tc intensity)

### Column T: Full-flow pipe capacity Qfull (engineering-methodology.md §3)

- `T10` Qfull (cfs) → `1.486/S10 * (N10/(12*4))^(2/3) * (Z10)^(1/2) * PI()/4 * (N10/12)^2` — Manning's full-flow: `Q = (1.486/n) × A × R^(2/3) × S^(1/2)` where `A = π/4 × (D/12)²` and `R = D/48` (§3)

### Columns U–X: Velocity and time-in-pipe (engineering-methodology.md §3 and §4)

- `U10` Q/A ratio → `M10 / ((N10/24)^2 * 3.14)` — design Q divided by full-flow area (used for partial-flow Hx computation)
- `V10` Full-flow velocity Vf (fps) → `1.486/S10 * (N10/(12*4))^(2/3) * Z10^(1/2)` — Manning's full-flow velocity (§3 `V = (1.486/n) × R^(2/3) × S^(1/2)`)
- `X10` Time in pipe (min) → `O10 / V10 / 60` — travel time = L / V converted to minutes (§2.3 channel/pipe segment Tt)

### Column Y: Friction slope Sf (engineering-methodology.md §4)

- `Y10` Sf (ft/ft) → `ROUND(((4^(5/3) * M10 * S10) / (PI() * 1.486 * (N10/12)^(8/3)))^2, 6)` — Manning inversion: `Sf = (Q × n / (1.486 × A × R^(2/3)))²` where A and R expressed in terms of D (§4)

### Column Z: Actual pipe slope (user-design-criteria.md "Pipe slope")

- `Z10` Actual slope (ft/ft) → `(P10 - Q10) / O10` — rise over run from U/S and D/S inverts; template does not programmatically flag below-ideal slopes but `user-design-criteria.md` specifies ≥ 1.0% for D < 24" and ≥ 0.5% for D ≥ 24"

### Columns AA–AF: Structure loss — Hx chain (engineering-methodology.md §5; MDSHA Drainage Manual Ch. 5; MCDOT §4.3.2.3)

- `AA10` Structure type → user-typed (Inlet / Manhole / Bend / Junction / Flow Splitter / Outfall); controls Kb column selection per §5.1
- `AB10` Top/opening elevation → user-typed rim or grate elevation (ft)
- `AC10` Structure No. (From ID copy) → `IF(A10="","",A10)` — echoes the row ID for the Hx lookup key
- `AD10` Controlling angle (degrees) → `MAX(IF($AQ$10:$AQ$98 = $AR10, $R$10:$R$98))` — selects the inflow pipe angle corresponding to the controlling hypothesized loss (§5.2 controlling-angle selection)
- `AE10` Kb coefficient → `INDEX(DATA!$A$68:$D$159, MATCH(AD10, DATA!$A$68:$A$159, 0), MATCH(AA10, DATA!$A$68:$D$68, 0))` — linear interpolation into the Kb table keyed on structure type and controlling angle (§5.1 Kb lookup; MCDOT §4.3.2.3 Appendix B table)
- `AF10` Structure loss Hb (ft) → `MAX(0, AE10 * (U10^2 / (2 * 32.2)))` — `Hb = Kb × Vout² / 2g` (§5; MCDOT Eq. 4-8)

### Columns AM–AR: Downstream Hx chain (engineering-methodology.md §5 and §6)

- `AM10` Downstream structure type → `VLOOKUP(B10, $A$10:$AF$98, 27, FALSE)` — looks up AA column for the To-structure
- `AN10` Downstream Kb → `INDEX(DATA!$A$68:$D$159, MATCH(R10, ...), MATCH(AM10, ...))` — Kb for the downstream structure keyed on inflow angle and type
- `AO10` Downstream pipe diameter (in) → `MAX(IF($A$10:$A$98 = $B10, $N$10:$N$98))` — largest pipe flowing into the downstream structure
- `AP10` V1/3 (fps) → `T10 / (3.14159 * (AO10/12/2)^2)` — approach velocity of this pipe referenced to the outgoing pipe's area (§5.2 `V1/3 = Q1 / Aout`)
- `AQ10` Hypothesized loss Lv (ft) → `AN10 * (AP10)^2 / (2 * 32.2)` — `Lv = Kb(θ) × V1/3² / 2g` for controlling-angle selection (§5.2)
- `AR10` Max Hx (ft) → `MAX(IF($B$10:$B$98 = $A10, $AQ$10:$AQ$98))` — maximum hypothesized loss among all inflow pipes entering this structure; the controlling-angle procedure selects the angle belonging to the minimum Lv, but AR holds the maximum for the row display (§5.2)

### Columns AT–BD: Normal-depth / partial-flow computation (DATA2 lookup)

- `AT10` Design Q (cfs) → `Table4[[#This Row],[Column16]]` — design flow for partial-flow computation
- `AU10` Pipe slope S (ft/ft) → `Table4[[#This Row],[Column22]]`
- `AV10` Full-flow capacity Qfull (cfs) → `Table4[[#This Row],[Column12]]` — same as T10 via table reference
- `AW10` Diameter D (in) → `Table4[[#This Row],[Column13]]`
- `AY10` AR²/³ / Do^(8/3) dimensionless parameter → `((AV10 * AT10) / (1.49 * AU10^0.5)) / (AW10/12)^2.667` — normal-depth parameter per partial-flow equation
- `AZ10` Y/D0 ratio → `VLOOKUP(AY10, DATA2!$A$2:$D$101, 2)` — partial-flow depth ratio from DATA2 lookup table
- `BA10` Y normal depth (ft) → `AZ10 * AW10/12` — actual normal depth in feet
- `BB10` A/DO² ratio → `VLOOKUP(AY10, DATA2!$A$2:$D$101, 3)` — partial-flow area ratio from DATA2
- `BC10` Flow area A (sf) → `BB10 * (AW10/12)^2` — cross-sectional area at normal depth
- `BD10` Q/A velocity check → `AV10 / BC10` — velocity at normal depth (fps)

### Column AJ

- `AJ10` → `Table4[[#This Row],[Column43]]` — passes through a Table4 column (Column43 maps to column AJ within the table structure; exact semantic TBD from project data)

## Outputs

The following sheets read directly from STORM DRAIN COMPS by `INDEX/MATCH` or `XLOOKUP` keyed on the From-node Row ID (column A) and/or To-node ID (column B):

| Consumer sheet | Columns pulled | Lookup key |
|---|---|---|
| HGL | P, Q, N, O, Y, AF, AB | (A, B) pair via XLOOKUP |
| HGL(25YEAR) | A, N, J, K, S, AI (25-yr depth), AF | A via INDEX/MATCH |
| MCDOT HGL-DESIGN | B, J, K, L, M, N, S, Z, W, O, AH | A via INDEX/MATCH |
| MCDOT PIPE COMPS-DESIGN | multiple | A via INDEX/MATCH |
| MCDOT INLET COMPS-DESIGN | F, E, G, H | A via INDEX/MATCH |
| SHA SD-61.1-420-DESIGN | multiple | A via INDEX/MATCH |
| SHA (2-YR)SPREAD 61.1-491 | multiple | A via INDEX/MATCH |
| SHA (25-YR)HGL 61.1-493 | B, J, K, N, S, Z, V, O, AI, AE | A via INDEX/MATCH |

## Dependencies

| Source sheet | Data pulled | Lookup key |
|---|---|---|
| C_FACTOR | Drainage area (col 3), C (col 17), Tc (col 21) | Row ID (col A) via VLOOKUP |
| DATA | IDF intensity (MoCo, PG, DC blocks), Kb table (rows 68–159), dropdown sources | Tc, return period, structure type, angle |
| DATA2 | Y/D and A/D² partial-flow ratios | Dimensionless AY parameter via VLOOKUP |
| INLET SPACING | Project title (C4) linked to A1 | Direct reference |

## Issues found

None — STORM DRAIN COMPS has 0 `#REF!` errors and no broken cross-sheet references per `pass_a.json`.

## Fix plan

None. No repairs needed for this sheet.

---

> Correction landed in Spec 3 pre-work: an earlier version of this doc listed column R as "Manning's n." Verified empirically against the row-8 headers in both `template_wip_new.xlsx` and `template_golden.xlsx`.

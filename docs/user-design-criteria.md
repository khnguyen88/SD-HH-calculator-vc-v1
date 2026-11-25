# User Design Criteria

User-supplied design preferences and firm/reviewer conventions that are **not**
derivable from the governing equations or from the agency manuals
(`MCDrainageDesignCriteria10thRevised1Final.pdf`, `MDOTSHADrainageManual.pdf`,
`hif24006-hec22_v4.pdf`, etc.) already in `docs/`.

Use these as design targets when sizing storm drain systems. They are "ideal if
feasible" — site constraints (existing utilities, outfall elevation, cover
limits) may force deviation, which should be documented in the project record.

## Pipe slope (longitudinal)

| Pipe diameter | Ideal minimum slope | Notes |
|---|---|---|
| ≥ 24" | **0.5%** (0.005 ft/ft) | Larger pipe carries self-cleansing velocity at a flatter grade. |
| < 24" | **1.0%** (0.010 ft/ft) | Smaller pipe needs more grade to maintain self-cleansing velocity. |

Rationale: these are target minimums for self-cleansing velocity; the agency
manual's absolute minimum (typically governed by Manning's at design Q) may be
lower, but designs should aim for the above when feasible.

**Agency cross-reference:** MCDOT Drainage Design Criteria §4.3.3(k) requires "Pipe shall not be designed on a slope less than 0.5 percent. However, to enhance self-cleaning characteristics, 15 and 18 inch diameter pipe are to be designed on an actual slope of 1 percent or greater." PG County DPIE Storm Drain & Paving Design Review Checklist §G-6 states the same rule in the generalized form: "Pipes less than 24" shall be designed for a minimum slope of 1% and pipes 24" or greater may be designed with a minimum slope of 0.5%" — matching our rule verbatim. Our `< 24"` threshold here captures both: MCDOT's explicit 15/18-inch rule generalized to also catch 21" pipe (not explicitly named by MCDOT), and PG's exact threshold.

Calculator enforcement: the Pipe Sizing & Capacity tab shows a `↓ flat slope`
flag next to the Status badge when the effective slope is below the ideal
minimum for that pipe's equivalent circular diameter. Hover for the threshold
and actual value.

## Minimum cover below roadway

Top of pipe must be a **minimum of 9 inches below the gravel subbase** of the
roadway (i.e., 9" of clearance between the pipe crown and the bottom of the
gravel subbase layer, *not* 9" below finished pavement).

This is a structural/constructability criterion and is separate from the HGL
crown-clearance check (which is a hydraulic check — see
`engineering-methodology.md` §HGL).

## Crown matching at junctions

At every junction structure (manhole or inlet), the **crown of the upstream
pipe entering the structure must never be lower than the crown of the
downstream pipe leaving the structure**.

- Rule: `Crown_in ≥ Crown_out` at every structure, where
  - `Crown_in  = (incoming pipe downstream invert) + (incoming pipe diameter)`
  - `Crown_out = (outgoing pipe upstream invert) + (outgoing pipe diameter)`
- Prevents backwater and sediment deposition at the junction.
- When pipe sizes change (smaller u/s → larger d/s), the invert of the u/s pipe
  will sit higher than the invert of the d/s pipe — matching crowns, not
  inverts, is the correct convention.
- For flow splitters (one structure with Primary + Secondary outgoing pipes),
  the check compares each incoming pipe's crown against the **Primary**
  outgoing pipe's crown.

**Agency cross-reference:** PG County DPIE Checklist §G-10: "Equal crown or greater in structure for incoming and outgoing pipes" — matches our rule verbatim.

Calculator enforcement: the Pipe Sizing & Capacity tab shows a `⚠ low crown`
flag next to the Status badge when an incoming pipe's downstream crown falls
below the outgoing pipe's upstream crown at its destination structure. Hover
for the exact deficit.

Note: this is distinct from the HGL method toggle in the calculator
(HEC-22 vs. legacy both-end crown floor) — the HGL toggle governs *hydraulic
grade line* pinning, while this rule governs *physical pipe geometry* set
during design.

## Minimum pipe size

Main-line public storm-drain pipes are **15 inches minimum diameter**. ESD/SWM diversion pipes may be smaller.

Source: PG County DPIE Checklist §C-19. MCDOT §4.3.3(f) carries the same rule.

Calculator enforcement: not currently flagged by the HTML calculator. The user is responsible for selecting an acceptable minimum in the Pipe Sizing table.

## Minimum pipe cover (structural)

Vertical cover above the pipe crown:

| Pipe material | Minimum cover | Notes |
|---|---|---|
| RCP (rigid) | **1 ft** | Above the crown of the pipe. |
| Flexible (HDPE, CMP) | **2 ft** | Above the crown of the pipe. |

Source: PG County DPIE Checklist §G-8.

This is **distinct from** the "9 inch below the gravel subbase of the roadway" rule in the "Minimum cover below roadway" section above. The 9-inch rule governs clearance between the pipe crown and the bottom of the subbase layer in a roadway section; the G-8 rule is the general minimum cover above the crown anywhere along the pipe alignment. The more restrictive of the two governs at any given point.

Calculator enforcement: not currently flagged. A future pass could compare proposed crown elevation against proposed grade and emit a warning when cover drops below the above thresholds.

## Minimum drop through structure

Through every storm-drain structure, provide **≥ 0.1 ft drop** from U/S invert to D/S invert, or a slope of 1% through the structure — whichever yields the larger drop.

Source: PG County DPIE Checklist §G-9 ("A minimum drop of 0.1 foot shall be provided through the structure"); MCDOT §4.2.4(a) ("A minimum slope of 1 percent or 0.1 ft drop, whichever is greater").

Calculator enforcement: not currently flagged. The calculator tracks U/S and D/S inverts of each pipe; a future pass could compare incoming-pipe D/S invert against outgoing-pipe U/S invert at each structure.

## Maximum access structure spacing

Between manholes or access structures, the pipe run shall be ≤ 400 ft (PG). MCDOT allows longer runs for larger pipe per Table 4-5 below.

| Pipe size | MCDOT Table 4-5 max spacing | PG Checklist C-20 |
|---|---|---|
| 15" through 24" | 400 ft | 400 ft |
| 27" through 42" | 500 ft | 400 ft |
| ≥ 48" | 600 ft | 400 ft |

Sources: PG County DPIE Checklist §C-20; MCDOT §4.2.4(2) Table 4-5.

The reviewing agency controls. If MoCo reviews, MCDOT's size-based limits apply; if PG reviews, PG's flat 400 ft applies regardless of pipe size.

Calculator enforcement: not currently flagged.

## Pipe entry angle at flat-wall structures

A pipe entering a structure with a flat wall shall deflect no more than **45°** from the outgoing pipe's alignment.

Source: PG County DPIE Checklist §C-21.

This is a geometric clearance constraint for precast structures, not a hydraulic criterion. It constrains layout, not the Hb computation (which runs the controlling-angle method per `engineering-methodology.md` §5).

Calculator enforcement: not currently flagged. The Junction Structure tab already captures pipe deflection angles per `storm-drain-calculator-spec.md` §1.4; a future pass could flag any flat-wall-entering pipe with angle > 45°.

## Last pipe reach to outfall

The final pipe reach discharging to an outfall shall have **slope ≤ 1%**. Provide drop structures as needed to achieve this.

Source: PG County DPIE Checklist §H-6.

Rationale: a flatter last reach reduces exit velocity, limiting rip-rap requirements and erosion at the outfall.

Calculator enforcement: not currently flagged. The calculator knows which pipe is the outfall (`forceElev = true` on the downstream structure, or the structure with no outgoing pipe); a future pass could check the slope of the pipe immediately upstream of that node.

## Open-channel erosion velocity

For open-channel segments outside of pipe conveyance:

| Fill type | Threshold | Treatment if exceeded |
|---|---|---|
| Cut channel (stable existing material) | **5 fps** | Rip-rap or concrete required. |
| Fill channel (constructed on fill) | **4 fps** | Rip-rap or concrete required. |

Source: PG County DPIE Checklist §L-4.

Calculator enforcement: out of scope for the conveyance-pipe calculator. Document for completeness; the engineer evaluates open-channel segments separately.

## HGL clearance — jurisdictional note

| Agency | 10-yr HGL ceiling |
|---|---|
| MDSHA Ch. 5 / MCDOT §4.3.1 | `HGL ≤ crown + 1 ft` **AND** `HGL ≤ rim − 1 ft` (both checks). |
| PG County SWM Ch. 8 / DPIE Checklist §I-2 | `HGL ≤ rim − 12 inches` only. No explicit crown ceiling — pipes may run surcharged within the structure as long as HGL stays ≥ 1 ft below the grate or bottom of curb. |

The HTML calculator currently enforces the MDSHA/MCDOT rule (both checks). The PG rule allows more surcharge above the pipe crown. This divergence is analogous to the `junctionAngleRule` controlling-angle divergence documented in `engineering-methodology.md` §5 — different agencies, different rules in force.

A future Spec 3 may add a project-level `hglCrownCeilingRule` toggle: `"crown-plus-1ft"` (default — MDSHA/MCDOT) vs `"rim-only"` (PG). For now the stricter MDSHA/MCDOT rule is applied uniformly and a PG-reviewed project that fails the MDSHA crown check should document that the PG rim-only rule is the governing criterion.

Calculator enforcement: MDSHA/MCDOT rule only. See `engineering-methodology.md` §6 (HGL propagation) for the clearance checks.

## Time of concentration — small drainage areas

For drainage areas **≤ 2.0 acres**, Tc may be selected from a lookup keyed on the drainage area's composite runoff coefficient:

| Composite C | Tc (minutes) |
|---|---|
| ≥ 0.80 | 5 |
| 0.65 – 0.79 | 7 |
| 0.40 – 0.64 | 10 |
| ≤ 0.39 | 15 |

Source: MCDOT Drainage Design Criteria §3.2.1 Table 3-3 "Small Drainage Area Time of Concentration". PG County SWM Ch. 8 §8.2.2 carries the same two-track approach (lookup for small areas, segmental TR-55 for larger).

For drainage areas **> 2.0 acres**, compute Tc using TR-55 segmental (sheet flow + shallow concentrated + channel flow) or an equivalent method. MCDOT Eq. 3-1 gives the trailing travel-time segment: `Tc = Tt + (L − 100) / (60 V)`, with `V = 7 fps` for average drainage-area slope ≤ 7 % and `V = 10 fps` for slope > 7 %.

Calculator enforcement: the HTML calculator's Drainage Area tab accepts Tc as either a direct user entry or a TR-55 segmental computation per `engineering-methodology.md` §2. For small areas (≤ 2 acres), the user may enter Tc per the Table 3-3 lookup directly. A future pass could add a Tc-method option that auto-selects the lookup when the entered drainage area is ≤ 2 acres.

## Weighted composite runoff coefficient (C)

For a drainage area composed of multiple land-use subareas, the composite C used in the Rational Method is the area-weighted average:

```
C_composite = Σ (Cx × Ax) / Σ Ax
```

where `Cx` is the tabulated runoff coefficient for subarea x (impervious, lawns, woods, etc.) and `Ax` is its area.

Sources: MCDOT §3.4 "Runoff Coefficients" — states the weighting formula explicitly and provides Table 3-5 of C values by land cover. PG County SWM Ch. 8 §8.2.1 — "C factors for development shall represent a weighted average based upon the proportion of the surface area covered by impervious materials, lawns, or woods." Table 8-1 in PG Ch. 8 lists the Rational Method C values by land use.

The composite C feeds the small-area Tc lookup above and the Rational Method `Q = C i A` (`engineering-methodology.md` §1).

Calculator enforcement: the HTML calculator's Drainage Area tab accepts C as a single value per row. For catchments with multiple land uses, enter the composite C computed per the formula above. The WIP xlsx template (`docs/template_wip_new.xlsx`) implements the composite C computation on its `C_FACTOR` sheet (column M across up to eight land-use subareas). A future pass could add a subarea-breakdown UI to the HTML calculator that computes the composite C automatically.

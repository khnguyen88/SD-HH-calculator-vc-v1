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

Calculator enforcement: the Pipe Sizing & Capacity tab shows a `⚠ low crown`
flag next to the Status badge when an incoming pipe's downstream crown falls
below the outgoing pipe's upstream crown at its destination structure. Hover
for the exact deficit.

Note: this is distinct from the HGL method toggle in the calculator
(HEC-22 vs. legacy both-end crown floor) — the HGL toggle governs *hydraulic
grade line* pinning, while this rule governs *physical pipe geometry* set
during design.

# Calculator ↔ xlsx Import/Export Contract

**Contract-Version:** 1

Specifies how the HTML calculator (and the companion visualizer) read from and
write to the two xlsx shapes shipped by this project:

- **Latest sample template** — `docs/template_wip_new.xlsx` (Spec-1 repaired
  WIP; 16 sheets; no `Config` sheet).
- **Golden template** — `docs/template_golden.xlsx` (Spec-2 output; 17 sheets
  with `Config` last).

Spec 3 is the first consumer of this contract. Spec 2 ships the contract as a
doc so the read/write surface is agreed before any code is written.

---

## 1. Shape detection

On import, the calculator reads `wb.defined_names` (via SheetJS equivalent).

- `junctionAngleRule` present → **golden** shape. Read all three toggles from
  their named ranges.
- `junctionAngleRule` absent → **legacy** shape. Apply the three toggle
  defaults.

One branch. No heuristic sniffing (no "guess by sheet count," no "guess by
header text").

## 2. Toggle values

### Golden

| Named range | Values (first is default) |
|---|---|
| `junctionAngleRule` | `smaller-loss` \| `larger-loss` |
| `hglCrownCeilingRule` | `crown-plus-1ft` \| `rim-only` |
| `hglMethod` | `HEC-22 EGL (d/s crown floor)` \| `legacy both-end crown floor` |

### Legacy

Named ranges absent. Calculator uses the same defaults a golden file would
carry out of the box:

- `junctionAngleRule = "smaller-loss"`
- `hglCrownCeilingRule = "crown-plus-1ft"`
- `hglMethod = "HEC-22 EGL (d/s crown floor)"`

## 3. Pipe-row read path (both shapes — identical)

Sheet: `STORM DRAIN COMPS`, Excel Table `Table4`, rows 10–98.
Jurisdiction / design-storm cells: `T3` / `H3` on the same sheet.

| Source | Calculator field |
|---|---|
| `STORM DRAIN COMPS!A{row}` | `fromId` |
| `STORM DRAIN COMPS!B{row}` | `toId` |
| `STORM DRAIN COMPS!N{row}` | `pipeDiameterIn` |
| `STORM DRAIN COMPS!O{row}` | `pipeLengthFt` |
| `STORM DRAIN COMPS!P{row}` | `invertUsFt` |
| `STORM DRAIN COMPS!Q{row}` | `invertDsFt` |
| `STORM DRAIN COMPS!R{row}` | `inflowAngleDeg` — "Angle Out of Pipe (Deg)" |
| `STORM DRAIN COMPS!S{row}` | `manningN` |
| `STORM DRAIN COMPS!AA{row}` | `structureType` (Inlet/Manhole/Bend/Junction/Flow Splitter/Outfall) |
| `STORM DRAIN COMPS!AB{row}` | `rimElevFt` |
| `STORM DRAIN COMPS!AG{row}` | `inflowAngle1Deg` (2-inflow structures) |
| `STORM DRAIN COMPS!AH{row}` | `inflowAngle2Deg` (2-inflow structures) |
| `STORM DRAIN COMPS!AK{row}` | `lateralFlowCfs` (user-typed) |
| `STORM DRAIN COMPS!T3` | `jurisdiction` |
| `STORM DRAIN COMPS!H3` | `designStormYr` |

Rows where `A{row}` is blank are skipped.

**Note:** Spec-1's analysis doc `01-storm-drain-comps.md` lists column `R` as
"Manning's n." The actual header-row label is "Angle Out of Pipe (Deg) -
Whole #", and the AD/AN controlling-angle formulas reference it as an angle.
Spec-3 implementers: read the live header row, not the analysis doc.

## 4. Drainage-area read path (both shapes — identical)

Sheet: `C_FACTOR`, rows 6–88.

| Source | Calculator field |
|---|---|
| `C_FACTOR!B{row}` | `rowId` (join key to `STORM DRAIN COMPS!A`) |
| `C_FACTOR!C{row}` | `areaSf` |
| `C_FACTOR!M{row}` | `compositeC` (prefers user override on `R` via existing `IFERROR`) |
| `C_FACTOR!V{row}` | `tcMin` — authoritative |

**Advisory columns the calculator MUST NOT read as authoritative:**
- `C_FACTOR!W{row}` (Table 3-3 small-area Tc lookup; golden only) — informational.

## 5. HGL sheets are not read on import

The calculator computes HGL internally from the imported pipe rows. `HGL`,
`HGL(25YEAR)`, and all six print-report sheets are review artifacts, not
persistence. Never round-trip HGL numbers through them.

## 6. Sheets the calculator ignores on import

- All six print-report sheets (`MCDOT PIPE COMPS-DESIGN`, `MCDOT INLET
  COMPS-DESIGN`, `MCDOT HGL-DESIGN`, `SHA SD-61.1-420-DESIGN`, `SHA
  (2-YR)SPREAD 61.1-491`, `SHA (25-YR)HGL 61.1-493`).
- `PIPE SCHEDULE`, `STRUCTURE SCHEDULE` (hand-maintained inventories).
- `DATA`, `DATA2` (static lookup tables).
- `EQUATIONS + INSTRUCTIONS` (reference text).
- `INLET SPACING` (inlet-spread hydraulics stay in xlsx; the calculator
  doesn't own them).

## 7. Export (calculator → xlsx)

The calculator writes back into **input columns only** on `STORM DRAIN COMPS`
and `C_FACTOR`:

- `STORM DRAIN COMPS!A, B, N, O, P, Q, R, S, AA, AB, AG, AH, AK` plus `T3`
  and `H3`.
- `C_FACTOR!B, C, V`. (Composite C is computed by the xlsx formula on `M`
  from land-use sub-areas; the calculator writes `R` if the project uses the
  simple two-zone composite override, otherwise leaves `R` blank.)
- `Config!B3, B4, B5` on the golden shape only — writes the three toggle
  values. Does not touch columns `C` (citations), `E:G` (dropdown helpers),
  or row 1 (header).

The calculator **never writes to any formula-driven column** (C_FACTOR M, O,
P; STORM DRAIN COMPS C, D, E, F, G, H, I, J, K, L, M, T–BD, and the Edit-2
helper column; any HGL sheet cell; any print-report cell). Reopening the file
in Excel recomputes every derived value from the inputs.

## 8. Versioning

Any change to the read set, the write set, or the detection rule bumps
`Contract-Version` in this file. Spec 3's calculator import/export reads this
header and either supports both versions or documents the migration path in
a new section here.

# Calculator ↔ xlsx Import/Export Contract

**Contract-Version:** 2

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

On import, the calculator and visualizer use the shared `detectShape` helper
in `drainage-calculator/lib/xlsx-shape-reader.js`:

```
1. wb.SheetNames contains "STORM DRAIN COMPS"?
     a. ALSO contains "Outlet Structures"? → "robust"
     b. Else                                → "simple"
2. Else                                     → "unknown" (toast error)
```

Returns one of three values:
- **`simple`** — STORM DRAIN COMPS present, Outlet Structures absent. Covers
  both legacy WIP (`template_wip_new.xlsx`) and golden (`template_golden.xlsx`).
- **`robust`** — STORM DRAIN COMPS AND Outlet Structures both present.
  Calculator-native export format.
- **`unknown`** — Neither STORM DRAIN COMPS nor Outlet Structures present.
  Reader toasts an error and aborts.

Sheet-presence detection (rather than named-range detection) is used because
openpyxl and SheetJS expose `defined_names` differently, and the legacy WIP
has no named ranges. Sheet-presence is reliable across both libraries.

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

> As of Spec 3 Task 18, `hglMethod` drives the actual HGL formulas on
> `HGL!G/K/M` and `HGL(25YEAR)!G/K/M` via `IF(hglMethod="legacy both-end crown floor", <legacy>, <hec22>)` branching. Only column K's two branches differ semantically (strips the `D{r}` us_crown term in HEC-22); G and M wrap defensively.

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

## 3a. Pipe-row read path — Robust shape

Robust is `Simple + extras`. The Simple pipe-row read path (§3) applies
verbatim: rows 10-98 of STORM DRAIN COMPS, same columns A/B/N/O/P/Q/R/S/
AA/AB/AG/AH/AK. Shape detection returns "robust" only when the
STORM DRAIN COMPS sheet AND the Outlet Structures sheet are both present.

Robust-ONLY sheets layered on top of the Simple read:

| Sheet | Rows | Role |
|---|---|---|
| `TR-55 Segments` | 2+ (header on row 1) | Per-drainage-area travel-time segments. Flat, tagged by `Drainage Area` column. |
| `Outlet Structures` | 2+ | BMP/SWM facility list with stage/tailwater config. |
| `Outlet Devices` | 2+ | All orifice/weir/pipe devices, tagged by `Outlet Structure` column. |
| `Rating - <label>` (one per facility) | 2+ | Stage/tailwater/per-device-Q/total-Q rating curve. Not read on import; computed from the facility+devices. |
| `Rainfall Settings` | 1+ (key/value pairs in cols A/B) | Rainfall source, county, storm, custom NOAA overrides, fetched NOAA metadata. |

Rating sheets are not round-tripped — the calculator recomputes them on
import from the Outlet Structures + Outlet Devices rows.

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

## 4a. Drainage-area read path — Robust shape

Robust uses C_FACTOR (same as Simple) for the drainage-area row data.
TR-55 segment detail is read from the `TR-55 Segments` sheet (see §3a).

| Source | Calculator field |
|---|---|
| `C_FACTOR!B{row}` | `structureId` (join key) |
| `C_FACTOR!C{row}` | `area` |
| `C_FACTOR!M{row}` | `C` (composite) |
| `C_FACTOR!V{row}` | `tc` (authoritative) |
| `TR-55 Segments` rows | `drainage[].tr55.segments[]` (per-DA segment list) |

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

The calculator has two write paths, selected via `state.exportShape`:

### 7.1 Simple writer (`buildSimpleWorkbook`)

Loads the embedded `template_golden.xlsx` bytes as a styled base, writes:
- `STORM DRAIN COMPS!A, B, N, O, P, Q, R, S, AA, AB, AK` (pipe rows 10+)
- `STORM DRAIN COMPS!T3` (jurisdiction), `H3` (design storm)
- `C_FACTOR!B, C, V` (drainage rows 6+)
- `Config!B1` project name, `B2` export timestamp, `B3:B5` toggles,
  `B6 = "simple"`, `B7 = 2` (Contract-Version)

Does NOT write Robust-only sheets. State for outlet structures, TR-55
segments, custom NOAA, splitter metadata is silently dropped on export
(the calculator surfaces a lossy-export toast when `hasRobustState()`
returns true).

### 7.2 Robust writer (`buildRobustWorkbook`)

Loads the same golden base, writes everything 7.1 writes PLUS:
- `Config!B6 = "robust"` (shape marker)
- Appends sheets: `TR-55 Segments`, `Outlet Structures`, `Outlet Devices`,
  one `Rating - <label>` per facility, `Rainfall Settings`.
- Header row of each Robust-only sheet inherits the style from
  `STORM DRAIN COMPS!A8` for visual consistency with Simple sheets.

Neither writer touches formula-driven cells on STORM DRAIN COMPS or
C_FACTOR. Excel recomputes HGL and print sheets on open (iterate=True
is wired by Spec 2).

## 8. Versioning

Any change to the read set, the write set, or the detection rule bumps
`Contract-Version` in this file. Spec 3's calculator import/export reads this
header and either supports both versions or documents the migration path in
a new section here.

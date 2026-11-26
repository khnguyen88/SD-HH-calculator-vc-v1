# Spec 3 precondition — shape #1 (calculator native xlsx) audit

**Status:** precondition research for Spec 3 (three-shape calculator ↔ xlsx compatibility). Documents what the HTML calculator currently emits on "Export to xlsx" and reads back on "Import." No code changed by this audit.

**Reading context:** `docs/template-analysis/calculator-import-contract.md` (Contract-Version 1) specs only shape #2 (legacy WIP) and shape #3 (golden). Shape #1 — the calculator's own round-trip format — is undocumented there. This audit fills that gap so Spec 3 can be scoped against a known-good description of all three shapes.

**Source:** `drainage-calculator/storm-drain-design-calculator-dev.html` — `buildWorkbook()` at L6082, `exportExcel()` at L6530, `importExcel()` at L6739.

---

## 1. Sheet inventory (native export)

Order matches `XLSX.utils.book_append_sheet` call order in `buildWorkbook()`.

| # | Sheet name | Purpose | Row-1 is header? | Per-row source |
|---|---|---|---|---|
| 1 | `Overview` | Project name + narrative prose (28 rows, col A). | No (`[1][1]` = project name) | n/a |
| 2 | `Rainfall Settings` | Key/value settings in A/B. Variable-length (static 11 rows, +3 fetched-NOAA metadata rows, +40 fetched-NOAA data rows when a NOAA location is fetched). | No (each row is `[label, value]`) | `state.rainfall` |
| 3 | `Drainage Area` | 10 static cols + N variable storm-Q cols. | Yes (row 1) | `state.drainage` |
| 4 | `TR-55 Segments` | Flat table tagged by Drainage Area ID. | Yes | `state.drainage[].tr55.segments` |
| 5 | `Junction Structure` | 32 cols. Carries live formulas for cols I–U (hydraulics). | Yes | `state.structures` |
| 6 | `Pipe Sizing` | 18 cols. Live formulas for L, M (non-circular is value), N, O, P, R. | Yes | `state.pipes` |
| 7 | `Outlet Structures` | 12 cols, one row per BMP/SWM facility. | Yes | `state.outletStructures` |
| 8 | `Outlet Devices` | 17 cols, flat list tagged by Outlet Structure. | Yes | `state.outletDevices` |
| 9..M | `Rating - <label>` (one per outlet structure) | Stage/tailwater/per-device Q + total. Column count varies (2 + 6·nDevices + 1). Mix of values and formulas. | Yes | `computeRatingCurve(os.id)` |
| M+1 | `Table 4-6 Reference` | Static circular/elliptical area lookup. | Yes | `TABLE46` constant |
| M+2 | `Kb Coefficients` | Angle / inlet / manhole / bend (0–180°, 5° steps). | Yes | `state.kb` |
| M+3 | `Inlet Spacing` | Settings rows (Street, default spread) + blank + header + rows. Header is at variable position (sentinel: first col 0 cell = "Linked Structure" or "Label"). | Mixed (header is at the first row whose A = "Label" or "Linked Structure") | `state.inletSpacing` |

Written via `XLSX.writeFile(wb, name + ".xlsx", { bookSST: true })` at L6534.

## 2. Column layout per sheet (native)

The in-code comment at L6244–L6250 is authoritative. Reproduced here for Spec 3 reference:

### Drainage Area (row 1 = header)
`A` ID · `B` Description · `C` Area A (ac) · `D` C · `E` CA · `F` i Override (in/hr) · `G` Tc (min) · `H` Cf · `I` Tc Method · `J` Structure · `K..` Q_<storm> (cfs) — one per storm in `availableStorms(rfSrc)`.

Values only — no formulas on this sheet.

### Junction Structure (row 1 = header, 32 cols)
`A` Structure ID · `B` Description · `C` Drainage Area ID · `D` Type · `E` Force Fixed (TRUE/FALSE text) · `F` Fixed-Start Elev (ft) · `G` Pipe Crown (ft, computed value) · `H` Rim-Grate Elev (ft) · `I` Captured Q (formula) · `J` Q from Pipes (SUMIF) · `K` Total Flow (= I+J) · `L` Outgoing Pipe ID (INDEX/MATCH of the From|Role helper) · `M` Hf (formula) · `N` Kb (editable numeric value) · `O` Hb (= N·P²/64.4) · `P` Vout (= K/area) · `Q` Upstream HGL (conservative or hec22 branch) · `R` Upstream EGL (= Q+P²/64.4) · `S` Downstream Structure ID · `T` Crown Check · `U` Rim Check · `V` Split Method · `W` Split Capacity (cfs) · `X` Split Ratio (0–1) · `Y` Structure Mode · `Z` Agency · `AA` Catalog ID · `AB` Category · `AC` Shape · `AD` Inner Dia (ft) · `AE` Inner W (ft) · `AF` Inner L (ft).

**Hydraulics formulas (L6272–L6324):**
- `I{r} = IF(C{r}="",0,IFERROR(INDEX('Drainage Area'!H:H,MATCH(C{r},'Drainage Area'!A:A,0)),0))`
- `J{r} = SUMIF('Pipe Sizing'!C:C,A{r},'Pipe Sizing'!L:L)`
- `K{r} = I{r}+J{r}`
- `L{r} = IFERROR(INDEX('Pipe Sizing'!A:A,MATCH(A{r}&"|primary",'Pipe Sizing'!R:R,0)),"")`
- Base (outfall/sink) rows: `M=0, O=0, P=0, Q=F{r}, R=Q{r}+P{r}^2/64.4, S=""`, `N` written as numeric 0.
- Non-base rows: `M` = Manning Hf via INDEX/MATCH lookups into Pipe Sizing cols M/G/K/L; `P` = `K{r}/area`; `O = N·P²/64.4`; `S` = INDEX/MATCH of pipe's To column; `Q` = conservative or hec22 (see §3 below); `R = Q+P²/64.4`.
- `T` crown check = `IF(G="","",IF(Q<=G+1,"OK","EXCEEDS"))`; `U` rim check = `IF(H="","",IF(Q<=H-1,"OK","EXCEEDS"))`.

### Pipe Sizing (row 1 = header, 18 cols)
`A` ID · `B` From Structure · `C` To Structure · `D` Angle (deg) · `E` Shape · `F` Size (in or SPANxRISE) · `G` n · `H` US Invert (ft) · `I` DS Invert (ft) · `J` Slope (ft/ft) · `K` Length (ft) · `L` Design Q (formula) · `M` Area (sf) · `N` Qfull (= O·M) · `O` Velocity (formula) · `P` Status (PASS/FAIL) · `Q` Split Role · `R` From|Role Key (= `B&"|"&IF(Q="","primary",Q)`).

**Formulas (L6329–L6346):**
- `L{r}` design Q with splitter branch (`IF(xlFromType(B)="splitter", ...)`).
- `M{r} = PI()/4*(F/12)^2` for circular; **value only** for elliptical (SheetJS cell numeric, no formula).
- `O{r}` = Manning velocity; different formula per shape (elliptical substitutes the equivalent diameter as a literal numeric into the formula string).
- `N{r} = O{r}*M{r}`; `P{r} = IF(N>=L,"PASS","FAIL")`.

### Outlet Structures, Outlet Devices, Rating curves
Values only on Outlet Structures and Outlet Devices. Rating sheets have per-row total formula (`=Q_dev1+Q_dev2+…`) and a tailwater formula when `twMode="linked"` (XLOOKUP into Junction Structure col Q).

## 3. HGL method persistence (native shape)

Native export persists `hglMethod` in two places, both consumed on import:

1. **`Rainfall Settings` row** — `["HGL Method", "Conservative" | "HEC-22"]` at L6133. Import reads this at L6758 via `hglMethodFromLabel(rfMap["HGL Method"])`.
2. **`Junction Structure!Q{r}` formula branch** — L6314–L6316 emits a different formula depending on which method was active at export time:
   - `conservative`: `IF(OR(E="TRUE",S=""),F,IF('Rainfall Settings'!B(HGL Method row)="Conservative",MAX(chain,G),chain))`
   - `hec22`: `IF(OR(E="TRUE",S=""),F,chain)` (no crown pin)

**Critical difference vs template shapes:** The native export's HGL formula actively honors the toggle (reads `'Rainfall Settings'!$B:$B` at eval time, matched against the string "Conservative"). On the template shapes this is Spec 3's unfinished work — xlsx HGL walking logic still uses legacy both-end crown floor regardless of `hglMethod`.

**Round-trip caveat:** If a user exports with method = Conservative, then flips the Rainfall Settings cell to "HEC-22" in Excel directly, Excel will recompute HGL using whichever branch the formula emitted at export (because the Conservative-branch formula bakes in a `MAX(chain, G)` check that keys off the cell lookup; the HEC-22-branch formula omits that logic entirely). So flipping the cell post-export only partially switches methods — toggling in the calculator and re-exporting is the supported path.

## 4. Named ranges / shape markers

**Native export emits zero named ranges.** Verified by grep — no `Workbook.Names`, no `defined_names`, no `DefinedName` anywhere in `storm-drain-design-calculator-dev.html`.

Shape-detection implications for Spec 3:
- `junctionAngleRule` named range present → **golden** (shape #3).
- Named range absent + sheet `STORM DRAIN COMPS` present → **legacy WIP** (shape #2).
- Named range absent + sheet `Junction Structure` + `Pipe Sizing` present → **calculator native** (shape #1).
- Any other combination → unknown, treat as import error.

The outstanding-todos note's suggested rule ("SDC + C_FACTOR layout matches WIP → legacy WIP; otherwise native") is equivalent to what's above and works. The explicit sheet-name check is slightly more readable; use whichever the Spec 3 author prefers.

## 5. Import tolerance / migration notes (shape #1 only)

Current importExcel() behaviors worth preserving in Spec 3:

- **`cellFormula: false`** on `XLSX.read()` (L6744) — formulas are discarded, only values round-trip. Shape #1 imports don't need formula preservation.
- **`'i (in/hr)'` → `i Override (in/hr)` migration** (L6796–L6799) — old exports had the pre-override column name. Preserve.
- **`county = "Fetched"` fallback** (L6780) — old files missing fetched-NOAA data get fallback county. Preserve.
- **ID remapping** via `daIdMap`, `stIdMap`, `osIdMap` — external labels (`r.structureId`) are the stable keys on xlsx; internal ids (`r.id`) are regenerated on import. Spec 3's three-shape reader must preserve this pattern.
- **Inlet Spacing header sentinel** (L6957–L6964) — header row is found by scanning column A for `"Label"` or `"Linked Structure"`. Rows 0 and 1 are settings; row 2 is blank; row 3 is header. Not row-position-based.

## 6. Delta vs. Contract-Version 1

Updates needed in `docs/template-analysis/calculator-import-contract.md` when Spec 3 lands:

1. **§1 Shape detection** — add the shape-#1 branch (above).
2. **New §3a: Native-shape pipe-row read path** — the calculator reads from `Junction Structure`, `Pipe Sizing` (not `STORM DRAIN COMPS`). Table should mirror the existing §3 template-shape table.
3. **New §4a: Native-shape drainage-area read path** — reads from `Drainage Area` sheet (not `C_FACTOR`).
4. **§7 Export** — add shape-#1 write targets: all sheets in §1 above. Explicit note that the calculator writes **values + live formulas** on the native shape, not just values.
5. **§8 Versioning** — bump Contract-Version to 2.

The §5 rule ("HGL sheets are not read on import") stays unchanged for all three shapes — HGL is always computed internally from pipe rows.

## 7. Spec 3's headline sub-item, revisited

The outstanding-todos note describes the Spec 3 headline as "wire `hglMethod` to actual xlsx HGL formulas." That statement is only true for shapes #2 and #3 (template shapes), where the pre-repair HGL formulas implement the legacy both-end crown floor and ignore Config!B5. On shape #1 (native) `hglMethod` already drives the exported HGL formula (§3 above). Spec 3's scope on this item:

- **Shape #1:** no change needed. Already method-aware.
- **Shape #2 + #3:** replace the pre-repair HGL walking formulas with two parallel formula families (HEC-22 EGL vs legacy both-end crown floor), selected via `Config!B5` on shape #3 or via the import-time default on shape #2.

## 8. Open questions for the Spec 3 author

- Shape-detection branch: explicit sheet-name probe (`"STORM DRAIN COMPS" in wb.SheetNames`) vs named-range-only (`"junctionAngleRule" in defined_names ? golden : "STORM DRAIN COMPS" in wb.SheetNames ? legacy : native`). Equivalent in outcome; pick one and document the else branch.
- Error messaging: current native-only importExcel() silently continues past missing sheets. Three-shape reader should surface which shape it detected (toast) and error out on shape-unknown rather than importing nothing.
- Round-trip loss on cross-shape import: if a user imports a legacy WIP xlsx and then exports, they get a shape-#1 file back (not a shape-#2 file). That's the current behavior and matches user intent (the calculator owns one native shape). Spec 3 should confirm this is the desired behavior rather than attempting shape-preserving export.
- Does the calculator need to **write** shape-#2 / shape-#3 compatible files, or only **read** them? The outstanding-todos note is ambiguous ("Calculator + visualizer three-shape compatibility" — but is write bidirectional?). Clarify before scoping.

---

**Session close:** this doc covers everything a Spec 3 brainstormer needs about shape #1. Shape #2 + #3 are already covered by `calculator-import-contract.md` §3–§4 plus the Spec 1 + Spec 2 design docs. Spec 3 can begin with brainstorming on top of this + the existing contract.

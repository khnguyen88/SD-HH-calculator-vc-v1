# HGL Method Toggle — Design Spec

**Date:** 2026-11-08
**App:** `drainage-calculator/storm-drain-design-calculator-dev.html` (~6 741 lines)
**Spec:** `drainage-calculator/storm-drain-calculator-spec.md`
**Status:** approved design — decisions below are binding for the implementation plan

---

## Goal

Add a global project setting that switches HGL computation between the current
**HEC-22** method (default) and a **conservative** method matching the agency
legacy workbook (`docs/bburg-p-c-legacy.xlsx`, sheet " 10 Yr MoCo HGL",
cells C54–C63 define the max(crown, HGL) rule). The conservative option gives
submittal-ready HGLs without duplicating the legacy loss model.

---

## Governing equation

All HGL values in the app originate from one function:
`computeStructureCalc(structureId, seen, stormOverride)` (~line 1940). Every
surface — HGL tab, HGL—25-yr tab, row detail sheets, print package, Excel
export — reads `calc.elevation` from it. The toggle changes the value at this
single point; no surface re-implements the rule.

- **HEC-22 (default, current behavior):**

  ```
  elevation = downstreamElev + Hf + Hb        (line 2031, unchanged)
  ```

- **Conservative (new):** keep the same Hf (friction) and Hb = Kb·V²/2g
  (structure loss), then pin to the outgoing pipe crown:

  ```
  crown     = outPipe upstream invert + equivDiamIn/12     (already line 2034)
  elevation = max(HEC-22 computed, crown)
  ```

  **Crown pin only.** Do NOT add the legacy workbook's A/B/C/D loss
  composition. No EGL computation — HGL/WSEL only.

The calc result object gains one new field, `pinned` (boolean), true when the
conservative method raised the computed elevation to the crown. `pinned` is
`false` under HEC-22 and for every fallback case below.

---

## Edge cases

| Case | Behavior |
|------|----------|
| Base structure (`forceElev` true, or no outgoing pipe — early return ~line 1965) | Never pinned. Elevation stays `startElev`. |
| Crown is null (missing upstream invert or incomplete pipe geometry) | Fall back to the unpinned HEC-22 value, `pinned` false. Surfaces keep their existing warn treatment — the crown cell already renders "— not computed" and the HGL value keeps any existing assumed/warn styling, so no new flag is introduced. |
| Crown from an **assumed** invert (`crownAssumed` true) | Pin to the assumed crown. Existing "assumed *" warn styling is unaffected. |
| Circular structure reference (elevation = NaN) | Untouched. |
| Upstream propagation | Automatic: raising `elevation` raises `downstream.elevation` for the next structure upstream via the existing recursion — no extra logic. |
| Crown+1 ft / Rim−1 ft checks | Use the final (possibly pinned) elevation. A pinned HGL sits exactly at crown, so the crown+1 check passes trivially — expected. |

---

## State and persistence

- New state field: `state.hydraulics = { hglMethod: "hec22" | "conservative" }`,
  initialized to `"hec22"` in the default state (~line 1517 area).
- **Quick-save snapshots:** add `hydraulics` to `captureState` (~line 2350) and
  `restoreState` (~line 2359): `state.hydraulics = snap.hydraulics || { hglMethod: "hec22" };`
- **Excel export** (`exportExcel`, "Rainfall Settings" sheet, `rfAoa` ~line 6005):
  add row `["HGL Method", "HEC-22" | "Conservative"]` beside the existing
  storm rows.
- **Excel import** (`importExcel`, `rfMap` block ~line 6429): read
  `rfMap["HGL Method"]`; map `"Conservative"` (case-insensitive) to
  `"conservative"`, `"HEC-22"` to `"hec22"`; any missing/unknown value falls
  back to `"hec22"`.
- Old exports without the row import as HEC-22 — no migration needed.

---

## UI

- Location: **Rainfall & IDF tab → Project Rainfall Settings** section, in the
  same settings row as "Pipe & HGL Design Storm" (~lines 3920–3932).
- Control: a `<select>` with two options — `HEC-22 (standard)` and
  `Conservative (crown-pin)` — styled and sized like the adjacent storm
  selectors. Handler: `state.hydraulics.hglMethod = e.target.value;
  withFocusPreserved(renderAll);` (all state-mutating input handlers route
  through `withFocusPreserved`, per spec §A.2).
- Add one sentence to the tab help text (line 2545 block): the conservative
  method pins each structure's HGL to the outgoing pipe crown for
  submittal-safe profiles.

---

## Display surfaces

- **HGL tab / HGL—25-yr tab:** values flow automatically from
  `calc.elevation`. Column headers unchanged. The pinned elevation propagates
  into the crown+1 and rim−1 pass/fail cells with no extra code.
- **Row detail sheet** (`buildHglRowSheet`, ~line 4684): when conservative is
  selected, the sheet subtitle carries the method label
  `Method: Conservative (crown-pinned HGL)`. When a row is pinned, the
  "Upstream HGL" section shows the pin explicitly:
  `computed X.XX ft → pinned to pipe crown Y.YY ft`.
- **Print detail** (`buildHglDetailSheet`, ~line 5756): same method label in the
  sheet header.
- **Excel "Junction Structure" sheet:** the cached U/S HGL value is
  `calc.elevation`, but the live Q-column formula itself implements the
  conditional pin under the Conservative method: the HEC-22 chain expression
  (`INDEX(Q:Q,MATCH(...))+M+O`) is wrapped in
  `IF(INDEX('Rainfall Settings'!$B:$B,MATCH("HGL Method",'Rainfall Settings'!$A:$A,0))="Conservative", MAX(<chain>, G<row>), <chain>)`,
  so Excel's on-open recalc (the workbook ships without a calcChain) cannot
  silently revert pinned HGLs to HEC-22 values. The method label lives on the
  Rainfall Settings sheet row. Under HEC-22 the plain chain formula is exported
  unchanged. Cross-feature interaction: linked-tailwater outlet structures
  resolve their tailwater from the (possibly pinned) upstream HGL, so
  Conservative shifts BMP/outlet rating curves consistently with this
  single-source-of-truth design.
- **Selected method only.** Never show both methods side by side in tables —
  no dual HGL columns anywhere.

---

## Testing (`tests/run-tests.mjs`)

Per the agreed test list:

1. **Pin below crown:** computed HEC-22 HGL < crown → elevation equals crown,
   `pinned` true.
2. **Unchanged above crown:** computed HGL ≥ crown → elevation equals
   computed, `pinned` false.
3. **HEC-22 non-regression:** with `hglMethod: "hec22"`, results identical to
   current output (existing 76-test suite must pass unchanged).
4. **Upstream propagation:** a pinned elevation at a downstream structure
   raises the HGL of the structure upstream of it (which now computes from the
   pinned downstream elevation).
5. **25-yr override:** the same method applies to the HGL—25-yr chain
   (`stormOverride: "25yr"`).
6. **Export/import round-trip:** `HGL Method` row survives
   export → import with both values; missing row imports as `"hec22"`.
7. **Base/forceElev never pinned:** outfall and fixed-elevation structures
   keep `startElev` under the conservative method.
8. **Missing crown fallback:** structure with null crown keeps the HEC-22
   value, `pinned` false.

---

## Scope boundaries

- **Main calculator only.** The separate HGL/EGL visualizer app (`/visualizer`)
  is out of scope; it keeps its current behavior. Track a follow-up to decide
  whether the visualizer should honor the exported method label.
- No per-structure override of the method — one global project setting.
- No EGL computation, no legacy A/B/C/D loss composition, no dual-method
  display.
- Detail sheets, print sheets, and Excel always show the **selected** method
  with a label — never silently mixed.

---

## Implementation notes

- After every dev-file edit, run `node drainage-calculator/build.js` and commit
  both files together.
- Commit format: `feat(calculator): <slug>` / `test(calculator): <slug>`;
  never add LLM attribution trailers.
- One logical change per commit; keep the `computeStructureCalc` diff minimal —
  the pin is ~4 lines after line 2031 plus the `pinned` field.

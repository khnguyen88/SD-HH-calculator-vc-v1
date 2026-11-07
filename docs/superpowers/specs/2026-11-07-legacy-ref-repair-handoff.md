# Handoff: Legacy workbook `#REF!` repair

**Status:** COMPLETE 2026-11-07. The legacy workbook now has zero external
links and zero `#REF!`/`#NAME?` cells. See "Workaround applied" below.

## Goal

1. `docs/bburg-p-c-template.xlsx` opens in Excel 365 with no `#NAME?`/`#REF!`,
   seeded from the legacy 10-yr network.
2. `docs/bburg-p-c-legacy.xlsx` has no `#REF!`/`#NAME?`.

Both are true: the legacy `HGL 25-yr` external references now resolve to a
hidden local cache, and the package contains no external-link parts.

## Verified current state (2026-11-07)

### Template — DONE
- Rebuilt by `python drainage-calculator/build_bburg_template.py`.
- Excel full recalc: **0 error cells**.
- HGL two-chain walk works (Chain A p8→p1, Chain B p12→p10, separate TWs).
- Seed network extracted from `docs/bburg-p-c-legacy.xlsx` (not the import file):
  9 DA rows, 14 structures (outfalls CULVERT-A/CULVERT-B), 12 pipes p1–p12.

### Legacy — DONE
- `openpyxl` audit: **formula-text `#REF!` = 0, `#NAME?` = 0**, 14 sheets
  (13 original + hidden `_Ext10yrCache`).
- Excel audit: **0 `#REF!`, 0 `#NAME?`**. Remaining legacy noise:
  `#VALUE!` 1273, `#DIV/0!` 763 (10 are the hidden cache), `#N/A` 2.
- ` 10 Yr MoCo HGL`: recoverable rows restored and verified:
  rows 20, 22, 23, 25, 26, 29, 34, 35 all show `Ok!` with sensible HGL/freeboard.
  Rows whose `C`/`D` referenced deleted cells were cleared (unrecoverable).
- `HGL 25-yr`: 328 unrecoverable external `#REF!` cells and 9 internal
  `'10 Yr Pipe Capacity'!#REF!` cells were cleared. **255 external references with
  valid addresses remain** (e.g. `'[3]Storm Sewer -10yr'!M18`) — see workaround.

## Critical pitfalls learned (do not repeat)

1. **Never save this legacy workbook with openpyxl.** Its repackaging drops
   external links/defined names and Excel refuses it: *"Unable to get the Open
   property of the Workbooks class."* Use **Excel COM** to edit and save.
   A known-good backup is at
   `C:\Users\khngu\AppData\Local\Temp\bburg-p-c-legacy.bak.xlsx`.
2. **Do not blindly clear all error cells.** Cascading formulas (e.g. `Y=X+G/12`
   when `X` is `#REF!`) evaluate to errors but are recoverable once the root is
   fixed. Clearing by evaluated error wiped recoverable rows the first time;
   they were later restored from the backup.
3. The MoCo HGL fix is **VLOOKUP index 17 → 15** (`'10 Yr Pipe Capacity'!B..:Q..`).
   Index 15 = column P = upstream invert; index 16 = Q = downstream invert;
   17 = R = rim and is out of range for `B:Q`. Do not extend the range to R.
4. `_xlfn.` prefixes are an OOXML storage artifact. When setting formulas via
   COM use the plain name (`MAXIFS`); when writing with openpyxl the builder
   normalizer (`bburg_template_builder/xlfn.py`) adds them.
5. PowerShell `$PID` is read-only; use `$pipeId`.
6. **`Workbooks.Open(..., ReadOnly:=$true)` can still rewrite the file** (Excel
   updates calc-chain/metadata; observed as a 1-byte change). Verify against a
   copy in `%TEMP%`, or restore the committed artifact afterward.

## Workaround applied (2026-11-07)

`HGL 25-yr` is a legacy sheet copied from a separate Baltimore project. Its
last-known external values are **cached inside the xlsx** at
`xl/externalLinks/externalLink3.xml`, sheetId 4 (`Storm Sewer -10yr`):

- All **153 distinct** referenced addresses are cached in the external-link XML
  (74 real values, 10 `#DIV/0!`, 69 blank). The earlier hand-written
  `_ext_cache.json` had only the 74 real values; parsing the XML directly gave
  complete coverage.
- 255 formulas referenced the Fenton workbook; all now point at the hidden
  `_Ext10yrCache` sheet.
- 328 `'[3]Storm Sewer -10yr'!#REF!` cells and 9 internal
  `'10 Yr Pipe Capacity'!#REF!` cells remain cleared (unrecoverable).

What was done (Excel COM, script kept out of the repo):

1. Copied `_Ext10yrCache` values from a parser run over `externalLink3.xml`.
2. Added hidden `_Ext10yrCache` (Visible = 0) with 74 values, 10 `=1/0` cells
   (faithful to the original `#DIV/0!`), and 69 blanks.
3. **Key gotcha:** Excel displays external refs as the *resolved full path*,
   e.g. `'U:\...\[Fenton_StormDrain_Comps - Existing.xlsx]Storm Sewer -10yr'!C18`,
   not the stored `[3]` index form that openpyxl shows. A `Range.Replace` on the
   `[3]` string silently matches nothing. The fix was to walk formula cells and
   regex-replace `'[^']*\]Storm Sewer -10yr'!` → `_Ext10yrCache!` (255 cells).
4. Deleted the 18 unused `_DUR*`/`_INT*` defined names that pointed at
   `HOCO_Rational_Inlets.xls` (links [1]/[2]) and the 7 broken `#REF!` names.
   Excel then dropped all three external-link parts from the package.
5. `CalculateFullRebuild()`, save via COM.

Verified after save:
- openpyxl: external refs = 0, formula-text `REF`/`NAME` = 0, external-link
  parts = 0.
- Excel: **0 `#REF!`, 0 `#NAME?`**; remaining legacy noise is `#VALUE!` 1273,
  `#DIV/0!` 763 (10 are the hidden cache), `#N/A` 2.
- `HGL 25-yr` values match the pre-change backup except 27 last-bit float
  differences; formula text and computed values otherwise identical.

## Files touched this session

- `drainage-calculator/bburg_template_builder/seed_data.py` — legacy seed network.
- `drainage-calculator/bburg_template_builder/sheets/hgl.py` — two-chain HGL.
- `drainage-calculator/bburg_template_builder/sheets/da_catchments.py` — literal C
  for legacy rows, numeric-zero formulas otherwise.
- `drainage-calculator/bburg_template_builder/sheets/pipes.py` — `Design_Q_cfs`.
- `drainage-calculator/bburg_template_builder/xlfn.py` — `_xlfn` prefix normalizer.
- `drainage-calculator/bburg_template_builder/tests/*` — updated expectations.
- `drainage-calculator/repair_legacy_workbook.py` — deleted; its openpyxl save
  produced an unopenable file.

## Remaining tasks

All done 2026-11-07:

- [x] Apply the `_Ext10yrCache` workaround via COM.
- [x] Delete obsolete `drainage-calculator/repair_legacy_workbook.py`.
- [x] Remove temp dumps `_legacy_dump*.txt`, `_legacy_hgl_formulas.txt`,
      `_hgl_restore.json`, `_ext_cache.json`.
- [x] `pytest drainage-calculator/bburg_template_builder/tests` — 81 passed.
- [x] Template re-verified in Excel — 0 error cells.
- [ ] Commit the legacy workbook change (do not commit `CLAUDE.md`; no LLM
      attribution trailers).

## Useful commands

```powershell
# Rebuild template
python drainage-calculator/build_bburg_template.py

# Formula-text audit (safe, read-only)
python -c "from openpyxl import load_workbook; wb=load_workbook('docs/bburg-p-c-legacy.xlsx'); print(sum(1 for sh in wb.sheetnames for r in wb[sh].iter_rows() for c in r if isinstance(c.value,str) and '#REF' in c.value))"
```

Excel COM is required for any write to `docs/bburg-p-c-legacy.xlsx`.

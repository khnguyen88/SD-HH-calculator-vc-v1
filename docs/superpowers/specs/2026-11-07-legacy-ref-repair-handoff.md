# Handoff: Legacy workbook `#REF!` repair

**Status:** paused mid-task on 2026-11-07. Next session should resume from
"The workaround we were about to try" below.

## Goal

1. `docs/bburg-p-c-template.xlsx` opens in Excel 365 with no `#NAME?`/`#REF!`,
   seeded from the legacy 10-yr network.
2. `docs/bburg-p-c-legacy.xlsx` has no `#REF!`/`#NAME?`.

Both are currently true for formula text, but the legacy HGL-25yr sheet still
contains 255 external-workbook references that Excel will re-resolve on open.

## Verified current state (2026-11-07)

### Template — DONE
- Rebuilt by `python drainage-calculator/build_bburg_template.py`.
- Excel full recalc: **0 error cells**.
- HGL two-chain walk works (Chain A p8→p1, Chain B p12→p10, separate TWs).
- Seed network extracted from `docs/bburg-p-c-legacy.xlsx` (not the import file):
  9 DA rows, 14 structures (outfalls CULVERT-A/CULVERT-B), 12 pipes p1–p12.

### Legacy — mostly done
- `openpyxl` audit: **formula-text `#REF!` = 0, `#NAME?` = 0**, 13 sheets.
- Cached errors remaining (pre-existing, not REF/NAME):
  `#VALUE!` 1273, `#DIV/0!` 941, `#N/A` 2.
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

## The workaround we were about to try (NOT applied)

`HGL 25-yr` is a legacy sheet copied from a separate Baltimore project. Its
last-known external values are **cached inside the xlsx** at
`xl/externalLinks/externalLink3.xml`, sheetId 4 (`Storm Sewer -10yr`):

- Cached cells: 74, columns `B,C,J,M,N,R,S,T,W,AM`, rows `13,15,16,17,18,20,22,23`.
- 255 current formulas reference valid external addresses; 138 distinct refs.
  Of those, **69 are uncached** (all rows 25–43) because the source rows were
  blank/`#DIV/0!` there.
- 328 cells already cleared had `'[3]Storm Sewer -10yr'!#REF!` (deleted source
  cell, no address) — truly unrecoverable.
- 9 internal `'10 Yr Pipe Capacity'!#REF!` — also unrecoverable.

Proposed design (user suggested a hidden helper column/sheet):

1. Add a hidden worksheet `_Ext10yrCache`, mirroring the cached cell addresses
   and values (write `docs/_ext_cache.json`, already generated, 74 cells).
2. Use Excel `Range.Replace` with `LookAt:=xlPart`:
   `'[3]Storm Sewer -10yr'!` → `_Ext10yrCache!` across all sheets.
3. Leave uncached helper cells blank (faithful to the source, which was blank).
4. Hide the sheet (`Visible = 0`), `CalculateFullRebuild()`, save via COM.
5. Audit: formula-text `REF`/`NAME` = 0; report cached `#DIV/0!`/`#VALUE!` as
   expected legacy noise.

The COM command to do this was written but **the user rejected it** before it
ran, to pause the task. No changes from that command are in the file.

## Files touched this session

- `drainage-calculator/bburg_template_builder/seed_data.py` — legacy seed network.
- `drainage-calculator/bburg_template_builder/sheets/hgl.py` — two-chain HGL.
- `drainage-calculator/bburg_template_builder/sheets/da_catchments.py` — literal C
  for legacy rows, numeric-zero formulas otherwise.
- `drainage-calculator/bburg_template_builder/sheets/pipes.py` — `Design_Q_cfs`.
- `drainage-calculator/bburg_template_builder/xlfn.py` — `_xlfn` prefix normalizer.
- `drainage-calculator/bburg_template_builder/tests/*` — updated expectations.
- `drainage-calculator/repair_legacy_workbook.py` — **obsolete/misleading**: its
  openpyxl save produces an unopenable file. Either rewrite with COM or delete.

## Remaining tasks

1. Decide on `HGL 25-yr` workaround (above) and apply via COM, or accept the
   cleared state.
2. Delete/rewrite `drainage-calculator/repair_legacy_workbook.py`; it documents
   the wrong approach.
3. Remove temp dumps: `docs/_legacy_dump.txt`, `docs/_legacy_dump2.txt`,
   `docs/_legacy_hgl_formulas.txt`, `docs/_hgl_restore.json`,
   `docs/_ext_cache.json` (keep the JSON if resuming the workaround).
4. Re-run `python -m pytest drainage-calculator/bburg_template_builder/tests`
   (last known: 81 passed).
5. Re-verify the template in Excel after any further edits.
6. Do not commit `CLAUDE.md` (gitignored) and do not add LLM attribution
   trailers to commits.

## Useful commands

```powershell
# Rebuild template
python drainage-calculator/build_bburg_template.py

# Formula-text audit (safe, read-only)
python -c "from openpyxl import load_workbook; wb=load_workbook('docs/bburg-p-c-legacy.xlsx'); print(sum(1 for sh in wb.sheetnames for r in wb[sh].iter_rows() for c in r if isinstance(c.value,str) and '#REF' in c.value))"
```

Excel COM is required for any write to `docs/bburg-p-c-legacy.xlsx`.

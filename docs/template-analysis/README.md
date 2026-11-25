# WIP Template Analysis

Per-tab analysis of `docs/template_wip_new.xlsx` — the new "legacy" reference template for PG / MoCo / DC storm-drain design. Produced as Spec 1 of the three-part series (audit → golden template → calculator compatibility). See `docs/superpowers/specs/2026-11-25-template-wip-audit-design.md` for the design.

## Dependency diagram

```
  DATA (IDF tables, dropdowns)          DATA2 (Y/D partial-flow table)
  (pure static)                         (pure static) --> SDC cols AZ-BD
        |                                      |
        |  (jurisdiction-switched IDF)         |
        v                                      |
  INLET SPACING <-- C_FACTOR             STORM DRAIN COMPS (Table4, A10:AR98)
  (10-yr inlet Tc,  (composite C,        (hub for all pipe-level engineering)
   gutter spread)    Table 3-3 Tc,            ^           |
                     365 formulas)            |           |
                          |                  |           |
                          +---> VLOOKUPs ----+           |
                          |    (D, M/R, V cols)          |
                          |                              |
                          v                              |
                  STRUCTURE SCHEDULE             +-------+--------+--------+
                  (B3:B8 ← C_FACTOR             |       |        |        |
                   B9:B14; rows 9-52            HGL   HGL(25YEAR) PIPE    MCDOT
                   user-typed)               (10-yr) (cols K,G   SCHEDULE HGL-
                                                      undamaged; (derived  DESIGN
                                                      other cols  view, not
                                                      #REF!)     a lookup)
                                                 |         |
                                                 |         |
                                                 v         v
                                           MCDOT HGL-DESIGN
                                           MCDOT PIPE COMPS-DESIGN
                                           MCDOT INLET COMPS-DESIGN <-- C_FACTOR (col D)
                                                                     <-- SDC (cols F,E,G,H)
                                           SHA SD-61.1-420-DESIGN    <-- SDC
                                           SHA (2-YR)SPREAD 61.1-491 <-- INLET SPACING, SDC
                                           SHA (25-YR)HGL 61.1-493   <-- HGL(25YEAR) K,G
                                                                     <-- SDC, DATA (25-yr IDF)

  EQUATIONS + INSTRUCTIONS (reference text only — no cross-sheet reads or writes)
```

STORM DRAIN COMPS is the hub for pipe-level data. C_FACTOR is the hub for runoff data. Every HGL sheet and every printable report derives from one or both.

## Sheet roles

| Role | Sheets | Notes |
|---|---|---|
| Working engine (4) | STORM DRAIN COMPS, HGL, HGL(25YEAR), INLET SPACING | Formula-rich; the real engineering lives here |
| Data sources (6) | C_FACTOR, DATA, DATA2, PIPE SCHEDULE, STRUCTURE SCHEDULE, EQUATIONS + INSTRUCTIONS | DATA and DATA2 are pure static. C_FACTOR (365 formulas: composite C + Table 3-3 Tc), PIPE SCHEDULE (52 formulas: pulls From/To/diameter/length from SDC), and STRUCTURE SCHEDULE (6 formulas: pulls Row IDs from C_FACTOR B9:B14) are "data sources that also compute" — they derive values from other sheets. EQUATIONS + INSTRUCTIONS is reference text only. |
| Printable reports (6) | MCDOT PIPE COMPS-DESIGN, MCDOT INLET COMPS-DESIGN, MCDOT HGL-DESIGN, SHA SD-61.1-420-DESIGN, SHA (2-YR)SPREAD 61.1-491, SHA (25-YR)HGL 61.1-493 | Agency submittal forms that pull from the working engine via INDEX/MATCH |

## Per-tab docs

- [01 STORM DRAIN COMPS](01-storm-drain-comps.md)
- [02 HGL](02-hgl.md)
- [03 HGL(25YEAR)](03-hgl-25year.md)
- [04 INLET SPACING](04-inlet-spacing.md)
- [05 C_FACTOR](05-c-factor.md)
- [06 DATA](06-data.md)
- [07 DATA2](07-data2.md)
- [08 MCDOT PIPE COMPS-DESIGN](08-mcdot-pipe-design.md)
- [09 MCDOT INLET COMPS-DESIGN](09-mcdot-inlet-design.md)
- [10 MCDOT HGL-DESIGN](10-mcdot-hgl-design.md)
- [11 SHA SD-61.1-420-DESIGN](11-sha-sd-420.md)
- [12 SHA (2-YR)SPREAD 61.1-491](12-sha-2yr-spread.md)
- [13 SHA (25-YR)HGL 61.1-493](13-sha-25yr-hgl.md)
- [14 PIPE SCHEDULE](14-pipe-schedule.md)
- [15 STRUCTURE SCHEDULE](15-structure-schedule.md)
- [16 EQUATIONS + INSTRUCTIONS](16-equations-instructions.md)

## Scripts

- `extract.py` — Pass A automated JSON dump. Committed output: `pass_a.json`.
- `repair.py` — applies R1–R5 from the Spec-1 design doc. Reads `../template_wip_new_pre-repair.xlsx`, writes `../template_wip_new.xlsx`.
- `test_extract.py`, `test_repair.py` — pytest suites.

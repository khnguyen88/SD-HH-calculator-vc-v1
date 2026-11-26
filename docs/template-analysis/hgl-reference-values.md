# HGL reference values (pre-repair cache)

Snapshot of the cached computed values from `docs/template_wip_new_pre-repair.xlsx` as of the last time Excel saved the file. Use this as a baseline to verify any downstream edits (repair.py, build_golden.py, or user edits) do not change what Excel computes for the same input data.

**How to verify:** open `docs/template_wip_new.xlsx` in Excel, press Ctrl+Alt+F9 to force full recompute, then compare G/K/M columns row-by-row against the HGL table below. Divergences point at a regression. Expected: identical values (formulas have been preserved verbatim through every repair / Spec-2 edit).

**HGL(25YEAR) is intentionally omitted.** The pre-repair cache for that sheet is all `#REF!` because Spec 1 R1 rebuilt its broken columns. For 25-year values, the current WIP (post-R1) is itself the reference going forward.

**M=`--` on rows where L=`-`** is by design: the M formula is `IF(L="-","",...)`, so outfall-type rows (no structure loss) leave M blank. Do NOT treat blank M on these rows as a regression.

## STORM DRAIN COMPS — key output columns that feed HGL

| row | A (From) | B (To) | K (design Tc) | L (intensity) | M (total Q) | X (travel time) | Y (friction slope) | AF (Hb) |
|---|---|---|---|---|---|---|---|---|
| 10 | I-3 | MH-4 | 10 | 5.34 | 0.9911 | 0.0868 | 0.0008 | - |
| 11 | MH-4 | MH-3 | 10.0868 | 5.3261 | 0.9958 | 0.2072 | 0.0008 | 0.007 |
| 12 | MH-3 | I-2 | 10.294 | 5.293 | 0.9896 | 0.3843 | 0.0008 | 0.0069 |
| 13 | I-1 | I-2 | 7 | 6.17 | 0.8725 | 0.0801 | 0.0006 | - |
| 14 | I-2 | MH-2 | 10.6783 | 5.2315 | 2.6709 | 0.1196 | 0.0017 | 0.095 |
| 15 | MH-2 | MH-1 | 10.798 | 5.2123 | 2.6611 | 0.1354 | 0.0017 | 0.0205 |
| 16 | EX-I-2 | MH-1 | 10 | 5.34 | 6.3054 | 0.0109 | 0.0016 | - |
| 17 | MH-1 | EX-I-1 | 10.9334 | 5.1907 | 8.785 | 0.0548 | 0.0015 | 0.0997 |
| 18 | EX-I-1 | CULVERT | 10.9883 | 5.1819 | 9.0122 | 0.0349 | 0.0016 | 0.0755 |
| 20 | I-7 | CULVERT | 10 | 5.34 | 7.649 | 0.0542 | 0.0011 | - |
| 22 | I-6 | I-5 | 10 | 5.34 | 0.8373 | 0.1177 | 0.0006 | - |
| 23 | I-5 | EX-I-3 | 10.1177 | 5.3212 | 3.17 | 0.0592 | 0.0009 | 0.0295 |
| 24 | EX-I-3 | CULVERT | 10.1769 | 5.3117 | 3.5208 | 0.09 | 0.0011 | 0.0623 |

## HGL (10-year) — all computed columns

| row | A (From) | B (To) | C (U/S inv) | D (U/S crown) | E (D/S inv) | F (D/S crown) | G (HGL at D/S) | H (pipe L) | I (Sf) | J (Hf) | K (HGL at U/S) | L (Hb) | M (HGL in FROM) | N (rim) | O (freeboard) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 7 | I-3 | MH-4 | 72.13 | 73.13 | 71.9 | 72.9 | 72.9 | 23.412 | 0.0008 | 0.0181 | 73.13 | - | -- | 76.38 | 3.25 |
| 8 | MH-4 | MH-3 | 70.35 | 71.35 | 69.79 | 70.79 | 70.79 | 56.27 | 0.0008 | 0.0439 | 71.35 | 0.007 | 71.357 | 75.5 | 4.15 |
| 9 | MH-3 | I-2 | 69.69 | 70.69 | 69.36 | 70.36 | 70.605 | 71.21 | 0.0008 | 0.0549 | 70.69 | 0.0069 | 70.6969 | 75.33 | 4.64 |
| 10 | I-1 | I-2 | 69.96 | 70.96 | 69.75 | 70.75 | 70.75 | 21.53 | 0.0006 | 0.0129 | 70.96 | - | -- | 73.02 | 2.06 |
| 11 | I-2 | MH-2 | 69.26 | 70.51 | 68.73 | 69.98 | 69.98 | 42.3 | 0.0017 | 0.0723 | 70.51 | 0.095 | 70.605 | 73.14 | 2.63 |
| 12 | MH-2 | MH-1 | 67.43 | 68.68 | 67.28 | 68.53 | 69.2797 | 30.16 | 0.0017 | 0.0512 | 69.3308 | 0.0205 | 69.3513 | 72.84 | 3.5092 |
| 13 | EX-I-2 | MH-1 | 67.46 | 69.21 | 67.42 | 69.17 | 69.2797 | 4.2 | 0.0016 | 0.0067 | 69.2863 | - | -- | 72.16 | 2.8737 |
| 14 | MH-1 | EX-I-1 | 67.18 | 69.18 | 67.1 | 69.1 | 69.1 | 16.5 | 0.0015 | 0.0249 | 69.18 | 0.0997 | 69.2797 | 72.5 | 3.32 |
| 15 | EX-I-1 | CULVERT | 67 | 69 | 66.87 | 68.87 | 68.87 | 14.36 | 0.0016 | 0.0228 | 69 | 0.0755 | 69.0755 | 71.93 | 2.93 |
| 17 | I-7 | CULVERT | 67.1 | 69.1 | 66.87 | 68.87 | 68.87 | 23.2878 | 0.0011 | 0.0266 | 69.1 | - | -- | 72.77 | 3.67 |
| 19 | I-6 | I-5 | 72.41 | 73.41 | 72.09 | 73.09 | 73.5195 | 32.03 | 0.0006 | 0.0177 | 73.5374 | - | -- | 75.74 | 2.2026 |
| 20 | I-5 | EX-I-3 | 71.99 | 73.49 | 71.41 | 72.91 | 72.93 | 29.56 | 0.0009 | 0.0269 | 73.49 | 0.0295 | 73.5195 | 74.76 | 1.27 |
| 21 | EX-I-3 | CULVERT | 71.3677 | 72.8677 | 71.04 | 72.54 | 72.54 | 32.31 | 0.0011 | 0.0363 | 72.8677 | 0.0623 | 72.93 | 74.83 | 1.9623 |

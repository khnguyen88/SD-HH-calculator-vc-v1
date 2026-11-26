# Outstanding TODOs — as of 2026-11-26

Status snapshot at the close of the Spec 1 + Spec 2 implementation session. Grouped by priority. Each item is self-contained enough that you (or Claude in a future session) can pick it up without rereading the full session.

---

## 1. Next big deliverable

### Spec 3 — Calculator + visualizer two-template compatibility

Per `docs/template-analysis/calculator-import-contract.md` (Spec-2 output).

- HTML calculator (`drainage-calculator/storm-drain-design-calculator-dev.html`) learns to import both shapes:
  - **Legacy WIP** (`template_wip_new.xlsx`, no `Config` sheet) → apply the three toggle defaults.
  - **Golden** (`template_golden.xlsx`, `Config` sheet with named ranges) → read actual toggle values.
- Visualizer parity for the same.
- **Most important sub-item:** wire `hglMethod` to actual xlsx HGL formulas. In Spec 2 it's **label-only** — the Config sheet stores the setting and the top-of-sheet stamp displays it, but xlsx HGL computation still uses whatever method the pre-repair formulas implemented (legacy both-end crown floor). Spec 3 is where the xlsx HGL walking logic actually honors the toggle.
- `junctionAngleRule` and `hglCrownCeilingRule` already drive xlsx formulas (Spec 2 Edits 2 and 3) — Spec 3 just needs calculator/visualizer to read them on import and write them on export.

Needs brainstorming → spec → plan → implementation. Follow the same superpowers flow we used for Spec 1 and Spec 2.

---

## 2. Verification pending

### Manual Excel-365 verification of Spec 2 (§8 steps 1–5)

1. Open `template_golden.xlsx` in Excel 365 — no repair prompts.
2. Flip `Config!B3` (`junctionAngleRule`) to `larger-loss`. On `STORM DRAIN COMPS` with a 2-inflow structure populated, observe `AD` column value change. Flip back to `smaller-loss`.
3. Flip `Config!B4` (`hglCrownCeilingRule`) to `rim-only`. On `HGL`, observe `Clearance Governing` change on a row where `Crown+1ft Check = FAIL` but `Rim−1ft Check = OK`. Flip back.
4. Flip `Config!B5` (`hglMethod`). Confirm the `P3` stamp on HGL updates. Confirm HGL numbers themselves do **not** change (label-only in Spec 2).
5. Populate a 3-pipe sample (copy rows 10–12 from `template_wip_new_pre-repair.xlsx`'s pre-populated I-3 → MH-4 → MH-3 chain). Confirm every sheet computes cleanly.

### HGL on-open populate verification

Confirmed fix: `iterate=True` is now set on both WIP and golden (committed `113b750`). Confirm after a fresh Excel open that `HGL` tab columns G/K/M fill in without any manual recompute. If anything stays blank, the fix needs more investigation.

### HGL reference-value regression check

Open `template_wip_new.xlsx` in Excel. Compare `HGL` tab values row-by-row against `docs/template-analysis/hgl-reference-values.md` (the pre-repair cache baseline). Any divergence flags a repair/edit that silently changed Excel's answer. Expected: identical — formulas and inputs are preserved verbatim.

---

## 3. Known limitations (documented; revisit if they bite)

### K-column XLOOKUP single-match on junctions

`STORM DRAIN COMPS!K{r}` (design Tc accumulation) uses XLOOKUP, which returns the **first** matching upstream row. For junction structures with 2+ inflow pipes, the design Tc may understate the controlling inflow's Tc (and thus overstate design intensity i and Q).

- **Current mitigation:** disclosure note on `EQUATIONS + INSTRUCTIONS` telling the user to manually verify K at junctions with multiple materially-different inflow Tc values.
- **Why not FILTER+MAX:** we tried; Excel's static circular-reference detector trips on `FILTER($K$10:$K$98+$X$10:$X$98, ...)` because the filter range includes the current cell. Even with `iterate=True`, the FILTER variant left HGL columns stale. XLOOKUP's explicit `IF(ROW()=ROW(),"",...)` row exclusion is the pattern Excel accepts.
- **Possible future direction:** a non-array LET+LAMBDA formula that recursively evaluates matching upstream rows one at a time. Non-trivial; not urgent.

### `hglMethod` is label-only in the xlsx until Spec 3

See Spec 3 above.

---

## 4. Template hygiene (optional cleanup)

### DATA2 dead columns

- **Columns E–H** carry a duplicate of the Kb-coefficient table. **0 formulas reference them workbook-wide** — the live Kb table is on `DATA!A68:D159`.
- **Columns J–L** are a re-keyed duplicate of DATA2 A–C (same partial-flow numbers, columns reordered). **0 references.**
- Both safe to delete. Mostly cosmetic — reduces workbook size and removes maintenance confusion.

### Per-tab analysis doc corrections

- **`docs/template-analysis/01-storm-drain-comps.md`** labels column `R` as "Manning's n" at `R10:R98`. Empirical check: the actual row-8 header is `"Angle Out of Pipe (Deg) - Whole #"`. Column S is Manning's n. The `AD`/`AN` controlling-angle formulas reference R as an angle column, confirming the header. Correct the doc.
- **`docs/template-analysis/05-c-factor.md` / Spec 1 U7**: U7 claimed `C_FACTOR` column I held a Table 3-3 Tc lookup. Column I is actually "C-Soil Group Impervious Area" (consumed by composite-C on column M). Spec 2 Edit 5 placed the Tc lookup on column W instead. Add a one-line correction to U7's citation note or to `05-c-factor.md`.

---

## 5. Tooling / session noise

### WIP SHA pin drift

`docs/template-analysis/conftest.py` carries `WIP_SHA256` as a drift signal for `template_wip_new.xlsx`. Every pytest session that hits the `repaired_wb` fixture overwrites WIP (that's Spec-1's design contract), so the SHA keeps drifting. Current approach: re-pin after any intentional WIP change.

Options to reduce noise:
- **(a)** Accept frequent re-pinning as session noise (current).
- **(b)** Switch `repair.py` to write to a tmp path instead of mutating WIP in place. Clean, but breaks the Spec-1 contract that `test_repair.py` verifies ("does repair.py produce a correct file at the WIP path").
- **(c)** Remove the pin entirely; rely on per-task control tests (e.g., `test_junction_wip_has_max_pattern_originally`) for semantic drift detection.

### `pass_a.json` drift

`docs/template-analysis/pass_a.json` is Spec 1's Pass A automated extraction. Committed as a reference artifact, but test runs regenerate it. Consider `.gitignore`-ing it and regenerating on demand, or accepting the churn.

### Ephemeral Excel lock files

`~$template_wip_new.xlsx` and similar lock files appear when Excel has the file open. Consider adding a `.gitignore` pattern `~$*.xlsx` so they never accidentally get staged.

---

## 6. Prior unresolved items from earlier in the project

### Column-letter prediction vs reality on HGL clearance columns

Spec 2 plan Task 3 predicted the three new HGL clearance columns would land at `S/T/U`. Actual placement: `V/W/X` because row-6 range `R6:U6` is a merged header. The implementer correctly scanned past the merged cells. **No contract depends on the letters** — nothing to fix. Documented here so future Spec 3 implementers don't get confused if they see the plan's letters vs the actual sheet.

---

**Session close summary:** main is at `113b750` (plus any tiny trailing cleanup commits after these notes). 64/64 pytest tests pass. Spec 1 + Spec 2 shipped. Both WIP and golden templates carry `iterate=True` so HGL populates on open without manual recompute. Push state reflects local.

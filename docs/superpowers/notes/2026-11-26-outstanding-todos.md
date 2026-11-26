# Outstanding TODOs — as of 2026-11-26

Status snapshot at the close of the Spec 1 + Spec 2 implementation session. Grouped by priority. Each item is self-contained enough that you (or Claude in a future session) can pick it up without rereading the full session.

---

## 1. Next big deliverable

### Spec 3 — Calculator + visualizer three-shape compatibility

Per `docs/template-analysis/calculator-import-contract.md` (Spec-2 output). Scope expanded to **three** xlsx shapes:

1. **Calculator's native export format** — whatever the HTML calculator's current `buildWorkbook()` produces on "Export to xlsx." This is the shape the calculator currently round-trips (export → open in Excel → import back). The import side must stay compatible — users with existing project files in this shape must keep working. Review `drainage-calculator/storm-drain-design-calculator-dev.html`'s current export function and document its actual sheet/column layout before touching import logic.
2. **Legacy WIP** (`template_wip_new.xlsx`, 16 sheets, no `Config`) → apply the three toggle defaults on import.
3. **Golden** (`template_golden.xlsx`, 17 sheets with `Config` named ranges) → read actual toggle values on import.

Shape detection is via `wb.defined_names`:
- `junctionAngleRule` present → golden
- SDC + C_FACTOR layout matches WIP → legacy WIP
- Otherwise → calculator's native format

Three-way branch with explicit precedence. No heuristic sniffing beyond that.

Visualizer parity for the same three shapes.

**Most important sub-item:** wire `hglMethod` to actual xlsx HGL formulas. In Spec 2 it's **label-only** — the Config sheet stores the setting and the top-of-sheet stamp displays it, but xlsx HGL computation still uses whatever method the pre-repair formulas implemented (legacy both-end crown floor). Spec 3 is where the xlsx HGL walking logic actually honors the toggle.

`junctionAngleRule` and `hglCrownCeilingRule` already drive xlsx formulas (Spec 2 Edits 2 and 3) — Spec 3 just needs calculator/visualizer to read them on import and write them on export.

Needs brainstorming → spec → plan → implementation. Follow the same superpowers flow we used for Spec 1 and Spec 2.

**Before Spec 3 scoping:** audit `storm-drain-design-calculator-dev.html` to understand the calculator's current native export. Specifically — what sheets does it emit? What columns per sheet? What cell layout? Does it carry any named ranges? That audit is Spec-3's precondition — it tells us what "shape 1" actually looks like and whether the calculator-import-contract needs updating to cover it.

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

### Junction-loss controlling-angle rule — engineering verification

Confirm that STORM DRAIN COMPS and HGL actually implement the junction-loss controlling-angle procedure (per MDSHA Ch. 5 / MCDOT §4.3.2.3) correctly after Spec 2 Edit 2. The Edit-2 behavior change flipped the default from the raw WIP's PG-style (MAX-of-Lv's-angle) to MDSHA's `smaller-loss` (MIN-of-Lv's-angle), and the implementation uses a helper column (`BE`) carrying the MIN hypothesized Lv.

Procedure on `template_wip_new.xlsx` or `template_golden.xlsx`:

1. Pick a structure that has 2 inflow pipes (e.g., `I-2` in the pre-repair sample data — rows where `B = I-2` are `12` and `13`).
2. Confirm `AD{r}` (controlling angle) at the pipe row **leaving** that junction (A = I-2 → row 14) picks the angle belonging to the smaller `AQ` (hypothesized loss Lv) of the two inflows.
3. Confirm `AE{r}` (Kb coefficient) and `AF{r}` (Hb = Kb × Vout²/2g) propagate from that angle.
4. On `Config`, flip `junctionAngleRule` to `larger-loss`. Confirm `AD`, `AE`, `AF` flip to the other inflow's values (angle belonging to the MAX `AQ`).
5. Confirm HGL `L{r}` (which XLOOKUPs `SDC!AF` by (From, To) pair) reflects the new Hb on the affected rows.
6. Flip back. Values revert.

Also spot-check against Spec 1 citation sources: MDSHA Drainage Manual Ch. 5 p. 5-26 (Sept 2023) Fig 5-8 worked example, and PG SWM Ch. 8 Appendix 8-15 sample calculation. The template should produce the MDSHA example's numbers under `smaller-loss` and the PG example's under `larger-loss`.

If anything looks off, the fix is in `STORM DRAIN COMPS!AD{r}` (Spec 2 Edit 2) and the `BE` helper column. Re-reading `docs/superpowers/specs/2026-11-25-golden-template-design.md` §5.2 is the entry point.

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

### DATA2 sheet — purpose, references, and auto-calculation options

Workbook-wide scan of `DATA2` references (session log):

| Block | What it is | References | Can auto-compute from formulas? |
|---|---|---|---|
| **A–C** (active) | Canonical circular-pipe partial-flow table. A = `AR^(2/3)/d₀^(8/3)` (Manning parameter), B = `y/d₀` (depth ratio), C = `A/d₀²` (area ratio). | **178 VLOOKUPs** from `STORM DRAIN COMPS` cols AT–BD (normal-depth and partial-flow area computation per pipe reach). | **Yes** — closed-form geometry given `y/d₀`: half-angle `θ = ACOS(1−2y/d₀)`; `A/d₀² = (2θ−sin(2θ))/8`; `R/d₀ = (A/d₀²)/(P/d₀)`; `AR^(2/3)/d₀^(8/3) = (A/d₀²)·(R/d₀)^(2/3)`. Keep `B` as the 0.01-step input; derive A and C as formulas. |
| **D** | Unused 4th column (possibly a top-width ratio, undocumented). | **0 references.** | — |
| **E–H** | Duplicate Kb-coefficient table (angle vs inlet/manhole/`bend-or-junction`). | **0 references.** Live Kb table is on `DATA!A68:D159`. | N/A — safe to delete. |
| **J–L** | Re-keyed duplicate of A–C: same partial-flow numbers with columns reordered so `y/d₀` is the key (for lookups in the opposite direction). | **0 references.** | Same formulas as A–C. |

**Why A–C are needed:** Manning's equation for a full pipe is `Q = (1.486/n)·A·R^(2/3)·S^(1/2)`. For partial flow, you're given Q and want `y` (normal depth). Rearranging gives `A·R^(2/3)/d₀^(8/3) = Q·n/(1.486·S^(1/2)·d₀^(8/3))` — the left side is a pure function of `y/d₀`, so a lookup table (column A keyed to column B) sidesteps the need for an iterative solver. The VLOOKUP is on A to find the corresponding B, then B times diameter gives real depth.

**Whether to convert A–C to formulas:** trade-off — static values match the canonical published table (Chaudhry, HDS-5, AASHTO drainage) reviewers recognize; formulas are auditable and typo-proof but look "coded" instead of "canonical." No consensus answer; leave as values for now unless you want to change the resolution (0.01 → 0.001 step) or hand-audit the geometry.

**Whether to delete D, E–H, J–L:** D and E–H and J–L are all unreferenced. Safe to delete. Purely cosmetic (reduces workbook size, removes maintenance confusion). If deleted, nothing on `STORM DRAIN COMPS` or any print sheet needs to change (the VLOOKUP range `DATA2!$A$2:$D$101` stays valid even if D has no data, and D is not read by any formula index).

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

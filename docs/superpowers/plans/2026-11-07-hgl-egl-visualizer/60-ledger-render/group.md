# Group 60: Ledger render — expanded-row formulas

**Purpose:** Build the ledger DOM. Prior groups computed the ledger *data*; this group renders the collapsed one-line view and the expanded formula-with-substituted-numbers view for each row kind.

**Tasks:**
- `task-27-expanded-row-helpers.md` — `csSection`, `csFormula`, `csResult`, `csWarn` helpers (visual grammar matching main app print sheets)
- `task-28-row-formulas-hf.md` — expanded render for `+Hf` rows (Sf, Hf, EGL_up formulas with numbers)
- `task-29-row-formulas-hb.md` — expanded render for `+Hb` rows (Vout, V²/2g, Kb·V²/2g)
- `task-30-two-inflow-detail.md` — the two-candidate-losses detail inside a 2-inflow Hb row + the "smaller controls" visual cue

**Group acceptance criteria:**
- Collapsed row shows: label · delta · arrow · new EGL. Each on its own column with monospace alignment.
- Expanded Hf row shows R, Sf (with substituted numbers), Hf, EGL_up — exactly the four lines in §4.1 of the spec.
- Expanded Hb row (0 inflow): "nominal entrance condition, Kb at 0°".
- Expanded Hb row (2 inflow) shows both candidate losses `Lv1`, `Lv2`, with the smaller marked `← controls` and the larger marked `(not used)`.
- Expanded Hb row (3+ inflow): red warning `csWarn` panel stating "3 inflows at structure <id>; controlling-angle method supports ≤2" and no further computation.
- All numeric values formatted to 3 decimal places (spec convention); angles to 1 decimal.

**Spec references:** §4 (equation panel), §4.1 (row kinds), main spec §1.4 (controlling-angle detail).

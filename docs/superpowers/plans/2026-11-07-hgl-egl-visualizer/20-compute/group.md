# Group 20: Compute — pure-math core

**Purpose:** Implement every formula from §7 of the spec as pure functions inside the `// ==== compute: begin ==== / end ====` sentinel block. No DOM reads, no state reads — explicit numeric inputs, numeric returns.

**Tasks:**
- `task-08-pipe-geometry.md` — `pipeAreaCircular`, `pipeRadiusCircular`, Table 4-6 lookup, `pipeArea`, `pipeRadius`
- `task-09-manning-friction.md` — `frictionSlope`, `frictionLoss`
- `task-10-kb-interpolation.md` — `KB_SEED`, `kbAt`
- `task-11-structure-loss.md` — `outletVelocity`, `velocityHead`, `structureLoss` (0/1/2/>2 inflows)
- `task-12-ledger-builder.md` — `buildLedger(path, resolvedState, kbTable, hglMethod)`
- `task-13-hgl-method-toggle.md` — HEC-22 vs Legacy both-crown HGL derivation inside the ledger

**Group acceptance criteria:**
- Every function in §7 of the spec has a matching JS implementation between the sentinel comments.
- `pipeAreaCircular(18)` returns `1.767145867644259` (tolerance `1e-9`).
- `structureLoss` with 2 inflows returns the correct θc per main spec §1.4 (the SMALLER loss's angle controls).
- `buildLedger` on a 3-pipe path returns an array of 7 rows (start, hf, hb, hf, hb, hf, end) with monotonically-increasing `after` values when all losses are positive.
- All unit tests in group 70 pass.

**Spec references:** §7 (equations), main spec §1.2 (Manning), §1.4 (controlling-angle Hb), §1.5 (Table 4-6), §1.6 (Kb seed).

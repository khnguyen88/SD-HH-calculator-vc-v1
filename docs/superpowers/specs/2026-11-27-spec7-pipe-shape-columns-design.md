# Spec 7 — Pipe Shape Columns on STORM DRAIN COMPS (Path B)

- **Date:** 2026-11-27
- **Status:** Finalized. Path B chosen (append columns at end; no mid-schema insertion).
- **Scope:** Add Pipe Shape / Width / # (barrel count) columns to STORM DRAIN COMPS. Make full-flow + friction-slope + partial-flow formulas shape-aware and multi-barrel aware.

## Rationale

Current SDC col N assumes circular; no shape, width, or barrel-count fields. Calculator's native format supports circular + elliptical but not rectangular or multi-barrel. User project needs all three shapes + multi-barrel runs.

## Path B (chosen, this spec)

Append new columns at **BF/BG/BH/BI/BJ/BK** (last used column on SDC is BE). Zero break of existing references. Formulas on T, V, Y, AV, AW (and by extension AY/AZ/BA/BB/BC/BD) rewrite to pull from shape-aware helpers.

Path A (mid-schema insertion) comes AFTER Path B verification — compare the two files side-by-side to confirm hydraulic results match before migrating.

## Column assignments

| Col | Header | Semantics | Default |
|---|---|---|---|
| N | **Size/Height (in)** (renamed from "Size (In)") | diameter for circular; rise (vertical) for elliptical; height for rectangular | user-entered |
| BF | Pipe Shape | `circular` \| `elliptical` \| `rectangular` | `circular` |
| BG | Width (in) | blank for circular; span (horizontal) for elliptical; width for rectangular | blank |
| BH | # | barrel count (positive integer) | `1` |
| BI | Area A (sf per barrel) | shape-aware, derived from BF/N/BG | formula |
| BJ | Hydraulic radius R (ft per barrel) | shape-aware | formula |
| BK | Equivalent diameter (in) | for DATA2 partial-flow lookup | formula |

## Helper formulas (per pipe row `{r}`)

```
BI{r} = IF(BF="rectangular", N*BG/144,
        IF(BF="elliptical", PI()*N*BG/(4*144),
                            PI()*N^2/(4*144)))

BJ{r} = BK{r}/48      (R = D_hyd/4, inches→ft via /12)

BK{r} = IF(BF="rectangular", 2*BG*N/(BG+N),
        IF(BF="elliptical", SQRT(N*BG),
                            N))
```

- **Circular:** D = N, standard.
- **Elliptical:** D_eq = sqrt(span × rise) (area-equivalent). Matches published Table 4-6 values to ~1% on small standard sizes (verify before committing to this approximation for large pipes).
- **Rectangular:** D_eq = 2WH/(W+H) (hydraulic-diameter equivalent).

## Full-flow formulas (per pipe row)

**Total Full-Flow Capacity (col T) — all barrels combined:**
```
T{r} = BH * (1.486/S) * BJ{r}^(2/3) * sqrt(Z) * BI{r}
```

**Manning Velocity full (col V) — per-barrel, same for all barrels:**
```
V{r} = (1.486/S) * BJ{r}^(2/3) * sqrt(Z)
```

**Friction Slope (col Y) — based on design Q per barrel:**
```
Y{r} = ((M/BH * S) / (1.486 * BI{r} * BJ{r}^(2/3)))^2
```

## Partial-flow block (AT–BD)

**AW (effective diameter for DATA2 lookup) — replaces Table4 column reference:**
```
AW{r} = BK{r}
```

**AV (Q per barrel) — replaces direct Q total:**
```
AV{r} = M{r} / BH
```

Rest of the partial-flow block (AY/AZ/BA/BB/BC/BD) unchanged — operates on the new per-barrel Q (AV) and equivalent diameter (AW) via DATA2. For non-circular, this is an **equivalent-D approximation**.

Accuracy note (in `EQUATIONS + INSTRUCTIONS` disclosure):
> Partial-flow for non-circular pipes uses an equivalent-diameter approximation via DATA2 (circular table). Accuracy is best for elliptical pipes at small standard sizes (≤36" rise; matches MDSHA Drainage Manual Table 4-6 equivalent-D values to ~1%). For rectangular box culverts, review partial-flow depth independently against HDS-5 Chart 10. Per-shape partial-flow tables (HDS-5 Chart 24 for elliptical) are not yet in the template — future Spec 7b.

## Multi-barrel semantics

Each barrel is treated as hydraulically independent carrying `Q_design / #` at the same slope, with identical geometry. The reported `T` (full-flow capacity) is the combined capacity of all barrels; `V`, `R`, `A` are per-barrel.

## Calculator changes

1. **buildSimpleWorkbook / buildRobustWorkbook:** write BF/BG/BH per pipe row (defaults circular/blank/1).
2. **Simple reader:** parse BF/BG/BH into state.pipes.
3. **state.pipes[].shape:** accepts `circular | elliptical | rectangular` (extend the existing circular|elliptical enum).
4. **state.pipes[].width:** new field (inches).
5. **state.pipes[].barrelCount:** new field (int, default 1).
6. **UI:** Pipe table gets Shape dropdown (3 options), Width input, # input.

## Visualizer changes

Minor — pass through the new fields via the shared reader. Visualizer's HGL walk already uses equivalent-D internally; feed the shape-aware D from the reader.

## Follow-up (Spec 7b, not this commit)

- Per-shape elliptical partial-flow lookup (HDS-5 Chart 24, digitized into a DATA3 sheet).
- Rectangular partial-flow via iterate=TRUE Newton (or digitized HDS-5 Chart 10).
- Comparison report: for each standard elliptical size, the equivalent-D approximation vs. per-shape table. Default the production formulas to whichever is closer to HDS-5 published values.
- Path A migration: move BF/BG/BH columns to natural position (after N), rewrite all dependent formulas, compare Path B vs Path A xlsx outputs row-by-row to confirm identity.

## Testing

- `test_pipe_shape_columns.py` — asserts BF/BG/BH headers present; BF default = `circular`; BH default = `1`; BI/BJ/BK formulas have the IF(BF=...) branches.
- Update Simple-reader pytest to assert new fields round-trip.
- Visualizer: no new tests required; the shape field just rides through.

## Non-goals

- Renumbering mid-schema (deferred to Path A migration).
- Per-shape partial-flow lookups (Spec 7b).
- Rectangular partial-flow iterative solve (Spec 7b).
- Pipe schedule / structure schedule sheet shape columns (stay as-is; they're inventories, not computation sheets).

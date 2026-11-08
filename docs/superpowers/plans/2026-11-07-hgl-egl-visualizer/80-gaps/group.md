# Group 80: Gap fills

Covers spec requirements that have no implementation task in the original 39-task plan,
plus the highest-priority follow-up noted in `plan.md`. Execute after group 70 (all tests
pass) before task-38 (final build + verify).

## Why these gaps exist

The original 39 tasks are complete for the happy path, but five items slipped through:
one v1 UI requirement (HGL method dropdown), two test-coverage gaps (§8.1 and §8.5),
one spec-compliance gap (Enter key), and one known user-confusion risk (splitter banner).

## Tasks

| Task | Implements | Priority |
|------|-----------|----------|
| task-40 | HGL method dropdown in topbar (spec §4.2) | v1 required |
| task-41 | Kb interpolation node tests (spec §8.1) | test coverage |
| task-42 | SVG integrity node tests (spec §8.5) | test coverage |
| task-43 | Enter key expands/collapses ledger rows (spec §4.3, §5.1) | spec compliance |
| task-44 | Splitter detection + non-blocking warning banner (spec §9.2) | follow-up #1 |

## Dependency order

```
task-40 (views block) → no other gap task depends on it
task-41 (pure test)   → independent
task-42 (pure test)   → independent
task-43 (ledger-render + state) → independent of 40/41/42
task-44 (import block + DOM)   → independent of 40–43
```

All five tasks can be executed in parallel by separate workers; none depends on another.

## Group acceptance criteria

- `node --test visualizer/visualizer-tests/` passes, now including
  `kb-interpolation.test.js` (8 tests) and `svg-integrity.test.js` (4 tests).
- Opening the built file: HGL method `<select>` is visible in the topbar.
- Switching the select between "HEC-22 EGL" and "Legacy both-crown" changes the
  EGL/HGL curves on the profile view in real time.
- Pressing `Enter` on the highlighted ledger row collapses it; pressing `Enter` again
  expands it.
- Loading `fixtures/main-app-export.xlsx` shows no splitter banner (clean network).
- Loading a fixture that contains a structure with two outgoing pipes shows the
  yellow-on-dark splitter banner below the topbar.

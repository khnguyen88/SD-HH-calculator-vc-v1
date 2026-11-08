# Group 40: Validation / Test Coverage

Three tasks fill gaps in `tests/run-tests.mjs` mandated by spec Section C.

A test harness already exists: `tests/run-tests.mjs` loads the built HTML via jsdom,
polls for `window.__sdc`, and runs with `cd tests && node --test run-tests.mjs`.

## Tasks

| Task | Spec ref | What it adds |
|------|----------|--------------|
| task-40-01 | §C.1 | Unit tests: circularSegment half-full boundary, frictionSlope, TR-55 equations |
| task-40-02 | §B.4, §C.5 | OOXML structural check: bookSST + no t="str" without formula |
| task-40-03 | §C.4 | Export/import round-trip: build → export → wipe state → import → assert restored |

Execute in order (all three modify the same file).

## Group acceptance

`cd tests && node --test run-tests.mjs` passes with zero failures and the new test
descriptions visible in output.

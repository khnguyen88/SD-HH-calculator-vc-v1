# Group 70: Tests — jsdom harness, unit tests, drift test, DOM tests

**Purpose:** Build the test harness in `visualizer/visualizer-tests/` and populate it with the five classes of tests from §8 of the spec. Can start in parallel with group 00 (harness task) but most tests depend on earlier groups.

**Tasks:**
- `task-31-jsdom-harness.md` — set up `visualizer/visualizer-tests/` with `package.json`, install `jsdom` and `xlsx`, write a loader that boots the dev HTML into jsdom
- `task-32-unit-pipe-geometry.md` — `pipeAreaCircular`, `pipeRadiusCircular`, Table 4-6 lookup
- `task-33-unit-friction.md` — `frictionSlope`, `frictionLoss`
- `task-34-unit-structure-loss.md` — 0/1/2/3+ inflow branches; the main-spec §1.4 counter-example
- `task-35-drift-test-fixture.md` — check in `fixtures/main-app-export.xlsx`, assert local recompute matches exported values to ≤0.001 ft
- `task-36-import-roundtrip.md` — JSON import → edit → export → re-import, assert override survives
- `task-37-dom-event-tests.md` — dispatch real `keydown`/`input` events, assert state changes

**Group acceptance criteria:**
- `node --test visualizer/visualizer-tests/` prints `pass N / fail 0` with N ≥ 80.
- Drift test runs against the fixture xlsx; every pipe's Hf and every structure's Hb match the exported value within 0.001 ft; end-to-end EGL at each structure matches within 0.01 ft.
- Focus-preservation audit: grep across the dev file finds zero `onchange:` or `oninput:` handlers that call a render function without going through `withFocusPreserved`.

**Spec references:** §8 (testing strategy), main spec §C (testing approach).

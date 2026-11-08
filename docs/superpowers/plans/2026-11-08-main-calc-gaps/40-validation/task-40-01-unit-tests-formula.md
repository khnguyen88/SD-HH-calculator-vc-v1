# task-40-01 — Unit tests: circularSegment, frictionSlope, TR-55 equations

## Context

Spec §C.1 requires unit tests for every function with a known closed form, naming
specifically: circular-segment centroid, friction-slope equation, and TR-55 segment
equations (sheet flow, shallow, channel). None of these are in `tests/run-tests.mjs`.

## Preconditions

- `tests/run-tests.mjs` exists (the existing test harness).
- `tests/node_modules/` is populated (`cd tests && npm install` if not).

## Exact changes

### Step 1 — Expose `frictionSlope` on `window.__sdc`

**File:** `drainage-calculator/storm-drain-design-calculator-dev.html`

Find the `window.__sdc = {` block (~line 6724). Add `frictionSlope` to the object:

```js
window.__sdc = { state, buildWorkbook, computeTotalFlow, computeStructureCalc, calcPipeRow,
  pipeEffectiveSlope, frictionSlope, calcDrainageRow, findStructure, findDrainage, findPipe,
```

(Only the first line of the object changes — the rest is unchanged.)

Then rebuild:
```
node drainage-calculator/build.js
```

### Step 2 — Add tests

**File:** `tests/run-tests.mjs`

Append the following block at the **end of the file** (after the last existing `test(…)` call):

```js
// ==================== circularSegment — spec §3.2 boundary verification ====================
test("circularSegment: h=0 → A=0, hc=0", () => {
  const r = 1.0;
  const seg = sdc.circularSegment(0, r);
  assert.ok(Math.abs(seg.A) < 1e-12, "A at h=0 must be 0");
  assert.ok(Math.abs(seg.hc) < 1e-12, "hc at h=0 must be 0");
});

test("circularSegment: h=r (half full) → A = π·r²/2, hc = 4r/(3π)", () => {
  const r = 1.5;
  const seg = sdc.circularSegment(r, r);   // h=r → half full
  const expectedA  = Math.PI * r * r / 2;
  const expectedHc = 4 * r / (3 * Math.PI);
  assert.ok(Math.abs(seg.A  - expectedA)  < 1e-9, `A at half-full: got ${seg.A}, expected ${expectedA}`);
  assert.ok(Math.abs(seg.hc - expectedHc) < 1e-9, `hc at half-full: got ${seg.hc}, expected ${expectedHc}`);
});

test("circularSegment: h=2r (full) → A = π·r², hc = r", () => {
  const r = 0.75;
  const seg = sdc.circularSegment(2 * r, r);
  const expectedA  = Math.PI * r * r;
  const expectedHc = r;
  assert.ok(Math.abs(seg.A  - expectedA)  < 1e-9, `A at full: got ${seg.A}, expected ${expectedA}`);
  assert.ok(Math.abs(seg.hc - expectedHc) < 1e-9, `hc at full: got ${seg.hc}, expected ${expectedHc}`);
});

// ==================== frictionSlope — spec §1.4 ====================
test("frictionSlope: known reference value (Q=1.0, n=0.013, 24-in circular)", () => {
  // 24-in circular pipe: A = π/4*(2)² = π ft², R = D/4 = 0.5 ft
  const A = Math.PI;        // sf
  const R = 0.5;            // ft
  const n = 0.013;
  const Q = 1.0;            // cfs
  // Sf = (Q*n/(1.486*A*R^(2/3)))^2
  const Sf_expected = Math.pow(Q * n / (1.486 * A * Math.pow(R, 2/3)), 2);
  const Sf_actual   = sdc.frictionSlope(Q, n, A, R);
  isClose(Sf_actual, Sf_expected, 1e-12, "frictionSlope mismatch");
});

test("frictionSlope: zero area returns 0", () => {
  assert.equal(sdc.frictionSlope(5, 0.013, 0, 0.5), 0);
});

// ==================== TR-55 equations — spec §1B.2 ====================
test("tr55SheetFlowTt: matches closed-form formula", () => {
  // Tt = 0.007*(n*L)^0.8 / (P2^0.5 * s^0.4)
  const n=0.24, L=100, s=0.02, P2=3.5;
  const expected = 0.007 * Math.pow(n*L, 0.8) / (Math.pow(P2, 0.5) * Math.pow(s, 0.4));
  isClose(sdc.tr55SheetFlowTt(n, L, s, P2), expected, 1e-10, "sheet flow Tt");
});

test("tr55SheetFlowTt: returns 0 for zero length", () => {
  assert.equal(sdc.tr55SheetFlowTt(0.24, 0, 0.02, 3.5), 0);
});

test("tr55TravelTime (shallow): Tt = L/(3600*V)", () => {
  // V = 16.1345 * sqrt(0.04) = 16.1345 * 0.2 = 3.2269 fps
  const surface = "unpaved";
  const s = 0.04, L = 500;
  const V = sdc.tr55ShallowVelocity(surface, s);
  const Tt = sdc.tr55TravelTime(L, V);
  const expectedTt = L / (3600 * V);
  isClose(Tt, expectedTt, 1e-10, "shallow Tt");
  assert.ok(V > 0, "shallow velocity must be positive");
});

test("tr55 channel velocity: V = (1.49/n)*R^(2/3)*s^0.5", () => {
  // Manning's for a channel: n=0.030, area=25sf, wp=15ft, s=0.001
  // R = 25/15 = 1.6667; V = (1.49/0.030)*1.6667^(2/3)*0.001^0.5
  const n=0.030, area=25, wp=15, s=0.001;
  const R = area/wp;
  const expected = (1.49/n) * Math.pow(R, 2/3) * Math.sqrt(s);
  isClose(sdc.tr55ChannelVelocity(n, area, wp, s), expected, 1e-10, "channel V");
});

test("computeTr55: multi-segment Tc = sum of segment Tt", () => {
  const row = {
    tr55: { segments: [
      { type:"sheet",   n:0.24, L:100, s:0.02, P2:3.5 },
      { type:"shallow", surface:"unpaved", L:500, s:0.04 },
      { type:"channel", n:0.030, area:25, wp:15, s:0.001, L:800 },
    ]}
  };
  const result = sdc.computeTr55(row);
  assert.equal(result.results.length, 3, "3 segment results");
  const sumTt = result.results.reduce((a,b) => a + (b.tt||0), 0);
  isClose(result.totalHr, sumTt, 1e-12, "totalHr = sum of segment Tt");
  assert.ok(result.totalMin > 0, "totalMin > 0");
  isClose(result.totalMin, result.totalHr * 60, 1e-10, "totalMin = totalHr*60");
});
```

## Run step

```
cd tests && node --test run-tests.mjs
```

Expected: all existing tests still pass, plus the 11 new tests listed above pass.

## Commit

```
git add tests/run-tests.mjs
git commit -m "test(calculator): unit tests for circularSegment, frictionSlope, TR-55 equations"
```

## Done when

`cd tests && node --test run-tests.mjs` exits 0 with no failures.

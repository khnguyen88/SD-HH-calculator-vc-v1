import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { test } from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(
  new URL("../drainage-calculator/storm-drain-design-calculator.html", import.meta.url),
  "utf8"
);

const dom = new JSDOM(html, {
  runScripts: "dangerously",  // safe: HTML is our own trusted source file
  resources: "usable",
  pretendToBeVisual: true,
});
const { window } = dom;

// Poll until __sdc is populated (DOMContentLoaded fires the init() call)
await new Promise((resolve, reject) => {
  const start = Date.now();
  const interval = setInterval(() => {
    if (window.__sdc) { clearInterval(interval); resolve(); }
    else if (Date.now() - start > 2000) { clearInterval(interval); reject(new Error("__sdc not populated after 2s")); }
  }, 20);
});

const sdc = window.__sdc;

// --- Smoke tests ---
test("__sdc is populated", () => {
  assert.ok(sdc, "__sdc not exposed on window");
});

test("__sdc exposes key functions", () => {
  assert.equal(typeof sdc.computeTotalFlow, "function", "computeTotalFlow missing");
  assert.equal(typeof sdc.buildWorkbook, "function", "buildWorkbook missing");
  assert.equal(typeof sdc.state, "object", "state missing");
});

test("state has expected shape", () => {
  assert.ok(Array.isArray(sdc.state.drainage), "state.drainage not array");
  assert.ok(Array.isArray(sdc.state.pipes), "state.pipes not array");
});

// ==================== Intensity interpolation ====================

const settings10 = { rainfallSource:"mdsha", storm:"10yr", county:"Montgomery",
                     allowableSpread:8, customNoaa:{} };

function isClose(actual, expected, tol, msg) {
  const t = tol ?? 0.01;
  if (Math.abs(actual - expected) > t) {
    throw new Error(`${msg ?? ""}: expected ${expected}, got ${actual} (tol ${tol})`);
  }
}

test("interpolatePL: MDSHA 10yr exact at Tc=5", () => {
  isClose(sdc.lookupIntensity(5, "mdsha", "10yr", "", {}), 6.684, 0.001);
});
test("interpolatePL: clamp below Tc=5 MDSHA 10yr", () => {
  isClose(sdc.lookupIntensity(3, "mdsha", "10yr", "", {}), 6.684, 0.001);
});
test("interpolatePL: linear interpolation MDSHA 10yr Tc=7", () => {
  // Between 5 (6.684) and 10 (5.340): 6.684 + (5.340-6.684)*((7-5)/(10-5)) = 6.1456
  isClose(sdc.lookupIntensity(7, "mdsha", "10yr", "", {}), 6.146, 0.01);
});
test("interpolatePL: clamp above MDSHA 2yr Tc=60", () => {
  // MDSHA 2yr last breakpoint 15min=3.364 → clamp
  isClose(sdc.lookupIntensity(60, "mdsha", "2yr", "", {}), 3.364, 0.001);
});
test("lookupIntensity: MoCo 10yr at Tc=15 exact", () => {
  isClose(sdc.lookupIntensity(15, "moco", "10yr", "", {}), 5.00, 0.001);
});
test("lookupIntensity: NOAA Montgomery 10yr at Tc=5", () => {
  const i = sdc.lookupIntensity(5, "noaa", "10yr", "Montgomery", {});
  assert.ok(i > 5 && i < 8, `Montgomery NOAA 10yr 5-min should be 5-8 in/hr, got ${i}`);
});

// ==================== Oracle row I-1 (workbook formula chain) ====================
// From bburg-p-c.xlsx "Inlet Spacing_10-yr" row 13, with column meanings confirmed
// from the live-formula 2-yr sheet: GRADE col = longitudinal S, XSLOPE col = Sx.
// (The design spec's oracle table had S/Sx swapped.)
// I-1 actual inputs: grate L=5, S=0.010 (grade), Sx=0.044 (cross), Q=0.8788,
// global W=1.33, a=0.0833, n=0.013.
// The workbook's own frozen helper cells for this row:
//   V=0.1066 (composite gutter V), X=0.0532 (Sx_eff), Lt=10.8573, E=0.6707.
// NOTE: the sheet's displayed Spread (4.10) and Pickup (99.25%) were manually
// typed in from FlowMaster ("Formulas have been voided and flowmaster has been
// used and results manually inputted" per the sheet note) and are NOT what the
// workbook's own formula chain computes. The oracle asserts the formula chain.

test("I-1: composite gutter helper V and SxEff match workbook X col", () => {
  const row = { S:"0.010", Sx:"0.044", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.Q, 0.8788, 0.002, "I-1 Q");
  isClose(r.SxEff, 0.0532, 0.002, "I-1 SxEff (workbook X13=0.0532)");
});
test("I-1: Lt and E match workbook Y/AB cols", () => {
  const row = { S:"0.010", Sx:"0.044", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.Lt, 10.857, 0.01, "I-1 Lt (workbook Y13=10.8573)");
  isClose(r.E, 0.6707, 0.005, "I-1 E (workbook AB13=0.6707)");
});
test("I-1: bypassCA = CA_total x (1-E)", () => {
  const row = { S:"0.010", Sx:"0.044", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.bypassCA, 0.14289 * (1 - 0.6707), 0.003, "I-1 bypassCA");
});

// ==================== Oracle row EX-I-1 (SUMP) ====================
test("EX-I-1 SUMP: pickup=100, bypassQ=0, Q≈2.260", () => {
  const row = { S:"SUMP", Sx:"", W:1.33, a:0.0833, n:0.013, L:"11.1",
                area:"0.04667", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"" };
  // Upstream bypass CA=0.29169, bypass Q ≈ 0.29169*6.68 (approximate)
  const bypassQ = 0.29169 * 6.68;
  const r = sdc.computeInletRow(row, settings10, bypassQ, 0.29169);
  assert.equal(r.pickupPct, 100, "SUMP pickup must be 100");
  assert.equal(r.bypassQ, 0, "SUMP bypassQ must be 0");
  assert.equal(r.bypassCA, 0, "SUMP bypassCA must be 0");
  assert.equal(r.isSump, true, "isSump flag");
  isClose(r.Q, 2.260, 0.05, "EX-I-1 Q");
});

// ==================== Oracle row I-6 (workbook formula chain) ====================
// Row 18 of "Inlet Spacing_10-yr": grate L=5, S=0.007 (grade), Sx=0.026 (cross),
// Q=0.8367 (= local CA 0.15669 x 5.34; NO upstream bypass — G18 empty, H18=F18),
// W=1.33, a=0.0833, n=0.013. Frozen workbook helpers:
//   V=0.0886, X=0.0332, Lt=12.6924, E=0.5940, bypass CA out R18=0.01004.
test("I-6: SxEff and Lt match workbook, E≈0.594", () => {
  const row = { S:"0.007", Sx:"0.026", W:1.33, a:0.0833, n:0.013, L:"5",
                area:"0.15669", C:"1", tc:"10", iOverride:"5.34", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.Q, 0.8367, 0.005, "I-6 Q");
  isClose(r.SxEff, 0.0332, 0.002, "I-6 SxEff (workbook X18=0.0332)");
  isClose(r.Lt, 12.692, 0.05, "I-6 Lt (workbook Y18=12.6924)");
  isClose(r.E, 0.594, 0.01, "I-6 E (workbook AB18=0.5940)");
  // Bypass CA out is self-consistent with E: totalCA*(1-E). (The workbook's
  // R18=0.01004 uses the manually-typed FlowMaster pickup 93.59%, not the
  // formula chain — not reproducible by a parametric calculator.)
  isClose(r.bypassCA, 0.15669 * (1 - 0.594), 0.003, "I-6 bypass CA out");
});

// ==================== Oracle row I-3 (100% pickup: L < Lt but near) ====================
// Row 15: grate L=10, S=0.080 (grade), Sx=0.019 (cross), Q=0.9892.
// Frozen helpers: V=0.0816, W=0.3103, X=0.0384, Lt=25.8922, E=0.5846.
test("I-3: SxEff≈0.0384, Lt≈25.89", () => {
  const row = { S:"0.080", Sx:"0.019", W:1.33, a:0.0833, n:0.013, L:"10",
                area:"0.18525", C:"1", tc:"10", iOverride:"5.34", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.Q, 0.9892, 0.002, "I-3 Q");
  isClose(r.SxEff, 0.0384, 0.002, "I-3 SxEff");
  isClose(r.Lt, 25.892, 0.05, "I-3 Lt");
  isClose(r.E, 0.5846, 0.005, "I-3 E");
});

// ==================== Oracle row I-7 (L=15 uses k=0.54) ====================
// Row 19: grate L=15, S=0.0162 (grade), Sx=0.0291 (cross), Q=7.5924.
// Frozen helpers: Z (k=0.58 branch shown as 0.0917 is W-col; actual):
//   W=0.0197, X=0.0303, Y=40.5046 (k=0.54 since L=15>=15), E=0.5651.
test("I-7: L=15 selects k=0.54, Lt≈40.50", () => {
  const row = { S:"0.0162", Sx:"0.0291", W:1.33, a:0.0833, n:0.013, L:"15",
                area:"1.42181", C:"1", tc:"10", iOverride:"5.34", allowableSpread:"" };
  const r = sdc.computeInletRow(row, settings10, 0, 0);
  isClose(r.Q, 7.5924, 0.01, "I-7 Q");
  isClose(r.Lt, 40.505, 0.05, "I-7 Lt (k=0.54, workbook Y19)");
  isClose(r.E, 0.5651, 0.005, "I-7 E (workbook AB19)");
});

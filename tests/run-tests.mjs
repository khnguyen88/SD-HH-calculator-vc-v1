import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { test } from "node:test";
import assert from "node:assert/strict";
import XLSX_NODE from "xlsx";

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

// ==================== Inlet spacing state model wiring ====================
test("inlet spacing state model wired", () => {
  assert.equal(typeof sdc.defaultInletSpacingRow, "function", "defaultInletSpacingRow missing");
  assert.ok(Array.isArray(sdc.state.inletSpacing), "state.inletSpacing not array");
  // Rainfall settings now live in state.rainfall, not inletSpacingSettings
  assert.equal(sdc.state.rainfall.rainfallSource, "noaa", "state.rainfall default source");
  assert.equal(sdc.state.rainfall.county, "Montgomery", "state.rainfall default county");
  assert.equal(typeof sdc.state.rainfall.inletStorm, "string", "state.rainfall.inletStorm is a string");
  // inletSpacingSettings no longer carries rainfall fields
  assert.equal(sdc.state.inletSpacingSettings.rainfallSource, undefined, "inletSpacingSettings has no rainfallSource");
});

// ==================== Bypass chain ====================
test("chain: bypass CA conservation, 2-inlet chain", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"A", S:"0.010", Sx:"0.044", W:1.33, a:0.0833, n:0.013, L:"5",
               area:"0.14289", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"", bypassTo:"B" };
  const r2 = { id:"r2", label:"B", S:"0.010", Sx:"0.044", W:1.33, a:0.0833, n:0.013, L:"15",
               area:"0.1", C:"1", tc:"7", iOverride:"6.15", allowableSpread:"", bypassTo:"" };
  const { results, cycles } = sdc.computeInletChain([r1,r2], s);
  assert.equal(cycles.length, 0, "no cycles expected");
  // r1's bypass CA out must equal r2's bypass CA in
  // r2 Q = (local CA 0.1 + bypass CA in) * 6.15
  const r1out = results["r1"].bypassCA;
  const expectedQ2 = (0.1 + r1out) * 6.15;
  isClose(results["r2"].Q, expectedQ2, 0.001, "r2 Q = (local+bypass CA) * own i");
});

test("chain: cycle detection", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"A", S:"0.01", Sx:"0.04", W:1.33, a:0.0833, n:0.013, L:"5",
               area:"0.1", C:"1", tc:"5", iOverride:"", allowableSpread:"", bypassTo:"B" };
  const r2 = { id:"r2", label:"B", S:"0.01", Sx:"0.04", W:1.33, a:0.0833, n:0.013, L:"5",
               area:"0.1", C:"1", tc:"5", iOverride:"", allowableSpread:"", bypassTo:"A" };
  const { cycles, results } = sdc.computeInletChain([r1,r2], s);
  assert.ok(cycles.length > 0, "cycle must be flagged");
  assert.ok(results["r1"], "cyclic rows still get placeholder results");
});

test("chain: SUMP mid-chain passes 0 bypass downstream", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"S", S:"SUMP", Sx:"", W:1.33, a:0.0833, n:0.013, L:"10",
               area:"0.1", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"", bypassTo:"B" };
  const r2 = { id:"r2", label:"B", S:"0.01", Sx:"0.04", W:1.33, a:0.0833, n:0.013, L:"10",
               area:"0.1", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"", bypassTo:"" };
  const { results } = sdc.computeInletChain([r1,r2], s);
  assert.equal(results["r1"].bypassCA, 0, "sump bypass out = 0");
  isClose(results["r2"].Q, 0.1 * 6.68, 0.001, "r2 Q = local only");
});

test("chain: orphan bypassTo flagged", () => {
  const s = { rainfallSource:"mdsha", storm:"10yr", allowableSpread:8, county:"", customNoaa:{} };
  const r1 = { id:"r1", label:"A", S:"0.01", Sx:"0.04", W:1.33, a:0.0833, n:0.013, L:"5",
               area:"0.1", C:"1", tc:"5", iOverride:"6.68", allowableSpread:"", bypassTo:"GHOST" };
  const { orphans } = sdc.computeInletChain([r1], s);
  assert.ok(orphans.length === 1, "orphan must be flagged");
});

test("availableStorms: moco returns 3 storms", () => {
  assert.deepEqual([...sdc.availableStorms("moco")], ["2yr","5yr","10yr"]);
});
test("availableStorms: noaa returns 8 storms", () => {
  assert.deepEqual([...sdc.availableStorms("noaa")], ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"]);
});
test("NOAA_ATLAS14: every county has 8 storms with 5 durations", () => {
  const storms = ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"];
  for (const cty of sdc.NOAA_COUNTY_LIST) {
    const entry = sdc.NOAA_ATLAS14[cty];
    assert.ok(entry, "missing county: " + cty);
    for (const s of storms) {
      assert.ok(entry[s], cty + " missing " + s);
      for (const d of [5,10,15,30,60]) {
        assert.ok(isFinite(entry[s][d]) && entry[s][d] > 0, cty + " " + s + " " + d + "min invalid");
      }
    }
  }
});
test("NOAA_ATLAS14: PG 25yr 5-min intensity matches PDF (7.56)", () => {
  assert.equal(sdc.NOAA_ATLAS14["Prince George's"]["25yr"][5], 7.56);
});
test("NOAA_ATLAS14: MoCo 100yr 60-min intensity matches PDF (3.12)", () => {
  assert.equal(sdc.NOAA_ATLAS14["Montgomery"]["100yr"][60], 3.12);
});
test("parseNoaaResponse: parses NOAA API text into 8-storm intensities", () => {
  // 19 durations × 10 return periods, single-quoted strings, only first 5 rows matter
  const row = (a,b,c,d,e,f,g,h,j,k) => `'${a}', '${b}', '${c}', '${d}', '${e}', '${f}', '${g}', '${h}', '${j}', '${k}'`;
  const quantiles = [
    row(0.34,0.42,0.50,0.55,0.62,0.68,0.73,0.78,0.85,0.88),
    row(0.53,0.66,0.79,0.88,0.99,1.08,1.16,1.24,1.34,1.39),
    row(0.64,0.80,0.96,1.07,1.21,1.32,1.42,1.51,1.63,1.69),
    row(0.89,1.11,1.33,1.48,1.67,1.82,1.96,2.09,2.25,2.33),
    row(1.10,1.37,1.64,1.83,2.07,2.25,2.43,2.59,2.80,2.90),
  ];
  // pad remaining 14 rows so shape is 19×10 (values irrelevant)
  for (let i = 0; i < 14; i++) quantiles.push(row(1,1,1,1,1,1,1,1,1,1));
  const text = "quantiles = [[" + quantiles.join("],[") + "]]\nupper = []";
  const res = sdc.parseNoaaResponse(text);
  // 2yr = col 1; 5-min: 0.42 × 12 = 5.04
  assert.equal(res["2yr"][5], 5.04);
  // 10yr = col 3; 10-min: 0.88 × 6 = 5.28
  assert.equal(res["10yr"][10], 5.28);
  // 500yr = col 8; 60-min: 2.80 × 1 = 2.8
  assert.equal(res["500yr"][60], 2.8);
  // 8 storm keys present
  assert.deepEqual(Object.keys(res).sort(), ["10yr","100yr","1yr","25yr","2yr","500yr","50yr","5yr"].sort());
});
test("parseNoaaResponse: throws on malformed text", () => {
  assert.throws(() => sdc.parseNoaaResponse("no quantiles here"), /Unexpected NOAA response/);
});
test("lookupIntensity: Fetched county uses site-specific data", () => {
  const fetched = {
    lat: 38.9, lon: -77.1, displayName: "Test Site",
    "1yr": {5:4,10:3,15:2,30:1,60:0.8},
    "2yr": {5:5,10:4,15:3,30:2,60:1.5},
    "5yr": {5:6,10:5,15:4,30:3,60:2},
    "10yr": {5:6.65,10:5.31,15:4.48,30:3.24,60:2.11},
    "25yr": {5:7.51,10:5.99,15:5.04,30:3.74,60:2.49},
    "50yr": {5:8.16,10:6.48,15:5.48,30:4.12,60:2.8},
    "100yr": {5:8.8,10:6.96,15:5.88,30:4.5,60:3.1},
    "500yr": {5:10.14,10:8.04,15:6.72,30:5.36,60:3.84},
  };
  const i = sdc.lookupIntensity(10, "noaa", "10yr", "Fetched", {}, fetched);
  assert.ok(Math.abs(i - 5.31) < 0.01);
  // falls back to normal county path when fetchedNoaa null
  const i2 = sdc.lookupIntensity(10, "noaa", "10yr", "Fetched", {}, null);
  assert.equal(i2, 0);
});
test("availableStorms: mdsha returns 3 storms", () => {
  assert.deepEqual([...sdc.availableStorms("mdsha")], ["2yr","10yr","25yr"]);
});

// ==================== calcDrainageRow — multi-storm shape ====================
test("calcDrainageRow: returns CA, Qs, designQ", () => {
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.pipeStorm = "10yr";
  const row = { area:"1.0", C:"0.8", iOverride:"", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  assert.ok(Math.abs(result.CA - 0.8) < 0.001, "CA should be 0.8");
  assert.ok(result.Qs["10yr"] !== undefined, "Qs should have 10yr key");
  assert.ok(result.Qs["2yr"]  !== undefined, "Qs should have 2yr key");
  assert.ok(Math.abs(result.designQ - result.Qs["10yr"]) < 0.001, "designQ should match pipeStorm Q");
  // MDSHA 10yr at Tc=10 is 5.340 in/hr → Q = 1*0.8*1.0*5.340 = 4.272
  assert.ok(Math.abs(result.Qs["10yr"] - 4.272) < 0.01, "Q10 ≈ 4.272 cfs: " + result.Qs["10yr"]);
});

test("calcDrainageRow: iOverride overrides all storm Qs", () => {
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.pipeStorm = "10yr";
  const row = { area:"1.0", C:"0.8", iOverride:"5.0", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  ["2yr","10yr","25yr"].forEach(s => {
    assert.ok(Math.abs(result.Qs[s] - 0.8*5.0) < 0.001, s + " Q should use iOverride: " + result.Qs[s]);
  });
});

test("calcDrainageRow: zero CA when area blank", () => {
  const row = { area:"", C:"0.8", iOverride:"", tc:"10", cf:"1.0", tcMethod:"direct", tr55:{segments:[]} };
  const result = sdc.calcDrainageRow(row);
  assert.equal(result.CA, 0, "CA should be 0 when area is blank");
  assert.equal(result.designQ, 0, "designQ should be 0");
});

test("inlet spacing uses state.rainfall.inletStorm", () => {
  sdc.state.rainfall.rainfallSource = "mdsha";
  sdc.state.rainfall.inletStorm = "2yr";
  const row = {
    id:"r-inlet-test", label:"I-T", S:"0.04", Sx:"0.01", W:1.33, a:0.0833, n:0.013, L:"10",
    area:"0.2", C:"1", tc:"5", iOverride:"", allowableSpread:"", bypassTo:""
  };
  const is = sdc.state.inletSpacingSettings;
  const r = sdc.computeInletRow(row, is, 0, 0);
  // MDSHA 2yr at Tc=5 = 5.016 in/hr → Q = 0.2 * 5.016 = 1.003
  assert.ok(Math.abs(r.Q - 1.003) < 0.05, "inlet Q uses inletStorm=2yr: " + r.Q);
});

test("computeTotalFlow stormOverride: Q25 > Q10 for same structure", () => {
  const structs = sdc.state.structures;
  if (!structs.length) { return; }
  const firstInlet = structs.find(s => s.type === "inlet");
  if (!firstInlet || !firstInlet.drainageAreaId) { return; }
  sdc.state.rainfall.rainfallSource = "noaa";
  sdc.state.rainfall.pipeStorm = "10yr";
  const q10 = sdc.computeTotalFlow(firstInlet.id, null, "10yr").Q;
  const q25 = sdc.computeTotalFlow(firstInlet.id, null, "25yr").Q;
  // Q25 must be strictly greater than Q10 (different storm intensities, no iOverride)
  assert.ok(q25 > q10, "Q25 should be > Q10 (stormOverride not wired): q10=" + q10 + " q25=" + q25);
});

// ==================== Excel export: Rainfall Settings sheet ====================
test("buildWorkbook: Rainfall Settings sheet exists with correct keys", () => {
  const wb = sdc.buildWorkbook();
  assert.ok(wb.SheetNames.includes("Rainfall Settings"), "Rainfall Settings sheet missing");
  const ws = wb.Sheets["Rainfall Settings"];
  const XLSX = window.XLSX;
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  const keys = aoa.map(r => r[0]);
  assert.ok(keys.includes("Rainfall Source"), "Rainfall Source row missing");
  assert.ok(keys.includes("Pipe & HGL Design Storm"), "Pipe storm row missing");
  assert.ok(keys.includes("Inlet Design Storm"), "Inlet storm row missing");
});

test("buildWorkbook: Drainage Area has CA column, no old i column", () => {
  const wb = sdc.buildWorkbook();
  const XLSX = window.XLSX;
  const ws = wb.Sheets["Drainage Area"];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  const headers = aoa[0] || [];
  assert.ok(headers.includes("CA"), "CA header missing");
  assert.ok(!headers.includes("i (in/hr)"), "old i column should be gone");
  assert.ok(headers.includes("i Override (in/hr)"), "iOverride header missing");
});

test("resolvedInletFields: returns row values when no linkedStructureId", () => {
  const row = { linkedStructureId:"", area:"0.5", C:"0.8", tc:"10" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "0.5");
  assert.equal(r.areaFromDA, false);
});

test("resolvedInletFields: auto-fills blank area/C/tc from linked DA", () => {
  const daId = sdc.state.drainage[0] && sdc.state.drainage[0].id;
  const st = sdc.state.structures[0];
  if (!st || !daId) return;
  const origLinked = st.drainageAreaId;
  st.drainageAreaId = daId;
  const da = sdc.findDrainage(daId);
  da.area = "1.2"; da.C = "0.7"; da.tc = "15";
  const row = { linkedStructureId: st.id, area:"", C:"", tc:"" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "1.2");
  assert.equal(r.C,    "0.7");
  assert.equal(r.tc,   "15");
  assert.equal(r.areaFromDA, true);
  assert.equal(r.CFromDA,    true);
  assert.equal(r.tcFromDA,   true);
  st.drainageAreaId = origLinked;
});

test("resolvedInletFields: non-blank row field is kept as override", () => {
  const daId = sdc.state.drainage[0] && sdc.state.drainage[0].id;
  const st = sdc.state.structures[0];
  if (!st || !daId) return;
  const origLinked = st.drainageAreaId;
  st.drainageAreaId = daId;
  const da = sdc.findDrainage(daId);
  da.area = "1.2"; da.C = "0.7"; da.tc = "15";
  const row = { linkedStructureId: st.id, area:"0.5", C:"", tc:"" };
  const r = sdc.resolvedInletFields(row);
  assert.equal(r.area, "0.5");
  assert.equal(r.areaFromDA, false);
  assert.equal(r.C, "0.7");
  assert.equal(r.CFromDA, true);
  st.drainageAreaId = origLinked;
});

test("buildWorkbook: Inlet Spacing sheet has Linked Structure column", () => {
  const wb = sdc.buildWorkbook();
  const XLSX = window.XLSX;
  const ws = wb.Sheets["Inlet Spacing"];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  // Find the data header row (first row where first cell is "Linked Structure" OR second cell is "Label")
  const headerRow = aoa.find(r => r[0] === "Linked Structure" || r[1] === "Label");
  assert.ok(headerRow, "Linked Structure column header row not found");
  assert.equal(headerRow[0], "Linked Structure", "First column should be Linked Structure");
});

test("computeInletRow uses linkedStructureId DA auto-fill for area/C/tc", () => {
  const da = sdc.state.drainage[0];
  const st = sdc.state.structures[0];
  if (!da || !st) return;
  const origDA = st.drainageAreaId;
  da.area = "1.0"; da.C = "0.9"; da.tc = "8";
  st.drainageAreaId = da.id;
  const row = {
    id:"test-linked", linkedStructureId: st.id,
    area:"", C:"", tc:"",       // all blank → auto-fill from DA
    iOverride:"", S:"0.04", Sx:"0.02", W:1.33, a:0.0833, n:0.013, L:"10",
    allowableSpread:"", bypassTo:""
  };
  const is = sdc.state.inletSpacingSettings;
  const result = sdc.computeInletRow(row, is, 0, 0);
  // area=1.0, C=0.9 → localCA=0.9
  assert.ok(result.totalCA >= 0.89 && result.totalCA <= 0.91,
    "totalCA should be ~0.9 (got " + result.totalCA + ")");
  st.drainageAreaId = origDA;
});

// ==================== pipeEffectiveSlope ====================
test("pipeEffectiveSlope: computes (US-DS)/L when both inverts and length set", () => {
  // US=105.0, DS=104.0, L=200 → (105-104)/200 = 0.005
  const pipe = { upstreamInvert:"105.0", downstreamInvert:"104.0", slope:"0.001", length:"200" };
  isClose(sdc.pipeEffectiveSlope(pipe), 0.005, 0.00001, "invert-derived slope");
});
test("pipeEffectiveSlope: falls back to slope field when both inverts absent", () => {
  const pipe = { upstreamInvert:"", downstreamInvert:"", slope:"0.007", length:"200" };
  isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "manual slope fallback");
});
test("pipeEffectiveSlope: falls back to slope field when one invert absent", () => {
  const pipe = { upstreamInvert:"105.0", downstreamInvert:"", slope:"0.007", length:"200" };
  isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "partial invert fallback");
});
test("pipeEffectiveSlope: falls back to slope field when length absent", () => {
  const pipe = { upstreamInvert:"105.0", downstreamInvert:"104.0", slope:"0.007", length:"" };
  isClose(sdc.pipeEffectiveSlope(pipe), 0.007, 0.00001, "no length fallback");
});
test("buildWorkbook: Pipe Sizing sheet has US Invert and DS Invert columns", () => {
  const wb = sdc.buildWorkbook();
  const XLSX = window.XLSX;
  const ws = wb.Sheets["Pipe Sizing"];
  const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
  const headers = aoa[0] || [];
  assert.ok(headers.includes("US Invert (ft)"), "US Invert (ft) column missing from Pipe Sizing sheet");
  assert.ok(headers.includes("DS Invert (ft)"), "DS Invert (ft) column missing from Pipe Sizing sheet");
});

// ==================== kAhFromAngle ====================
test("kAhFromAngle: access_hole straight (0°) = 0.15", () => {
  isClose(sdc.kAhFromAngle("access_hole", 0), 0.15, 0.001);
});
test("kAhFromAngle: access_hole 90° = 1.00", () => {
  isClose(sdc.kAhFromAngle("access_hole", 90), 1.00, 0.01);
});
test("kAhFromAngle: access_hole 45° interpolated between 90°(1.00) and 135°(0.75)", () => {
  // 45° deflection → theta = 135°; between pts [135,0.75] and [90,1.00]
  // t = (135-135)/(135-90) = 0 → 0.75
  isClose(sdc.kAhFromAngle("access_hole", 45), 0.75, 0.001);
});
test("kAhFromAngle: inlet straight (0°) = 0.50", () => {
  isClose(sdc.kAhFromAngle("inlet", 0), 0.50, 0.001);
});
test("kAhFromAngle: inlet 90° = 1.50", () => {
  isClose(sdc.kAhFromAngle("inlet", 90), 1.50, 0.001);
});
test("kAhFromAngle: inlet 45° interpolated", () => {
  // theta = 135 → 0.50 + 1.00 * ((180-135)/90) = 0.50 + 0.50 = 1.00
  isClose(sdc.kAhFromAngle("inlet", 45), 1.00, 0.01);
});

// ==================== resolveStructureCategory ====================
test("resolveStructureCategory: standard pgder MH = access_hole", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48"
  }), "access_hole");
});
test("resolveStructureCategory: standard pgder inlet = inlet", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-inlet-typeE"
  }), "inlet");
});
test("resolveStructureCategory: custom inlet category", () => {
  assert.equal(sdc.resolveStructureCategory({
    structureMode:"custom", structureCategory:"inlet"
  }), "inlet");
});
test("resolveStructureCategory: legacy (no structureMode) → access_hole", () => {
  assert.equal(sdc.resolveStructureCategory({}), "access_hole");
});
test("STRUCTURE_CATALOG has pgder entries", () => {
  assert.ok(sdc.STRUCTURE_CATALOG.pgder.length > 0, "pgder catalog empty");
  assert.ok(sdc.STRUCTURE_CATALOG.pgder.find(e=>e.id==="pgder-mh-48"), "pgder-mh-48 missing");
});

// ==================== computeStructureCalc dynamic K_ah ====================
test("computeStructureCalc: standard structure uses kAhFromAngle, not interpKb", () => {
  const s0 = sdc.state;
  const origStructures = s0.structures, origPipes = s0.pipes;
  const outfallId = "tf-out";
  const structId  = "tf-st";
  s0.structures = [
    { id:outfallId, structureId:"TF-OUT", type:"outfall", forceElev:true, startElev:100,
      drainageAreaId:"", crown:"", rim:"", structureMode:"" },
    { id:structId, structureId:"TF-ST", type:"manhole", forceElev:false, startElev:"",
      drainageAreaId:"", crown:"", rim:"",
      structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48",
      structureCategory:"", shape:"", innerDiameter:"", innerWidth:"", innerLength:"" },
  ];
  s0.pipes = [
    { id:"tf-pipe1", fromStructureId:structId, toStructureId:outfallId,
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:"", downstreamInvert:"", splitRole:"" }
  ];
  const calc = sdc.computeStructureCalc(structId);
  s0.structures = origStructures;
  s0.pipes = origPipes;
  assert.ok(calc != null, "calc is null");
  isClose(calc.kb, 0.15, 0.01, "kb should be ~0.15 for access_hole straight run");
});

test("computeStructureCalc: legacy structure (no structureMode) uses interpKb", () => {
  const s0 = sdc.state;
  const origStructures = s0.structures, origPipes = s0.pipes, origKb = s0.kb;
  const outfallId = "tf-out2";
  const structId  = "tf-st2";
  s0.structures = [
    { id:outfallId, structureId:"TF-OUT2", type:"outfall", forceElev:true, startElev:100,
      drainageAreaId:"", crown:"", rim:"" },
    { id:structId, structureId:"TF-ST2", type:"manhole", forceElev:false, startElev:"",
      drainageAreaId:"", crown:"", rim:"" },
  ];
  s0.pipes = [
    { id:"tf-pipe2", fromStructureId:structId, toStructureId:outfallId,
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:"", downstreamInvert:"", splitRole:"" }
  ];
  s0.kb = [{ angle:0, inlet:0.99, manhole:0.99, bend:0.99 }];
  const calc = sdc.computeStructureCalc(structId);
  s0.structures = origStructures;
  s0.pipes = origPipes;
  s0.kb = origKb;
  isClose(calc.kb, 0.99, 0.01, "kb should be 0.99 from custom Kb table");
});

// ==================== Inlet Spacing structureType removal ====================
test("defaultInletSpacingRow has no structureType field", () => {
  const row = sdc.defaultInletSpacingRow();
  assert.equal("structureType" in row, false, "structureType should not exist on defaultInletSpacingRow");
});

// ==================== Excel round-trip: new Structure fields ====================
test("buildWorkbook: new structure fields present in Junction Structure sheet", () => {
  const s0 = sdc.state;
  const orig = s0.structures;
  const origPipes = s0.pipes;
  s0.structures = [{
    id:"rt-st1", structureId:"RT-1", desc:"", drainageAreaId:"", type:"manhole",
    forceElev:false, startElev:"", crown:"", rim:"",
    splitMethod:"capacity", splitCapacity:"", splitRatio:0.5,
    structureMode:"standard", agency:"pgder", standardStructureId:"pgder-mh-48",
    structureCategory:"", shape:"round", innerDiameter:"4", innerWidth:"", innerLength:"",
  }];
  s0.pipes = [];
  const wb = sdc.buildWorkbook();
  s0.structures = orig;
  s0.pipes = origPipes;
  const ws = wb.Sheets["Junction Structure"];
  assert.ok(ws, "Junction Structure sheet missing");
  const keys = Object.keys(ws).filter(k => k !== "!ref" && k !== "!cols" && k.match(/^[A-Z]+1$/));
  assert.ok(keys.some(k => ws[k] && ws[k].v === "Structure Mode"), "Structure Mode header missing");
});

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
  const Sf_expected = Math.pow(Q * n / (1.486 * A * Math.pow(R, 2/3)), 2);
  const Sf_actual   = sdc.frictionSlope(Q, n, A, R);
  isClose(Sf_actual, Sf_expected, 1e-12, "frictionSlope mismatch");
});

test("frictionSlope: zero area returns 0", () => {
  assert.equal(sdc.frictionSlope(5, 0.013, 0, 0.5), 0);
});

// ==================== TR-55 equations — spec §1B.2 ====================
test("tr55SheetFlowTt: matches closed-form formula", () => {
  const n=0.24, L=100, s=0.02, P2=3.5;
  const expected = 0.007 * Math.pow(n*L, 0.8) / (Math.pow(P2, 0.5) * Math.pow(s, 0.4));
  isClose(sdc.tr55SheetFlowTt(n, L, s, P2), expected, 1e-10, "sheet flow Tt");
});

test("tr55SheetFlowTt: returns 0 for zero length", () => {
  assert.equal(sdc.tr55SheetFlowTt(0.24, 0, 0.02, 3.5), 0);
});

test("tr55TravelTime (shallow): Tt = L/(3600*V)", () => {
  const surface = "unpaved";
  const s = 0.04, L = 500;
  const V = sdc.tr55ShallowVelocity(surface, s);
  const Tt = sdc.tr55TravelTime(L, V);
  const expectedTt = L / (3600 * V);
  isClose(Tt, expectedTt, 1e-10, "shallow Tt");
  assert.ok(V > 0, "shallow velocity must be positive");
});

test("tr55 channel velocity: V = (1.486/n)*R^(2/3)*s^0.5", () => {
  const n=0.030, area=25, wp=15, s=0.001;
  const R = area/wp;
  const expected = (1.486/n) * Math.pow(R, 2/3) * Math.sqrt(s);
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

// ==================== OOXML structural checks — spec §B.4, §C.5 ====================
test("OOXML: no t='str' cell without a formula (bookSST compliance)", () => {
  const wb = sdc.buildWorkbook();
  const buf = window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true });
  const wbRead = XLSX_NODE.read(buf, { type: "array" });
  const violations = [];
  for (const sheetName of wbRead.SheetNames) {
    const ws = wbRead.Sheets[sheetName];
    for (const addr of Object.keys(ws)) {
      if (addr.startsWith("!")) continue;
      const cell = ws[addr];
      if (cell.t === "str" && !cell.f) {
        violations.push(`${sheetName}!${addr}`);
      }
    }
  }
  assert.deepEqual(violations, [],
    "Cells with t='str' and no formula (spec-invalid): " + violations.slice(0,5).join(", "));
});

test("OOXML: shared-string cells present (bookSST:true worked)", () => {
  const wb = sdc.buildWorkbook();
  const buf = window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true });
  const wbRead = XLSX_NODE.read(buf, { type: "array" });
  let foundSst = false;
  outer: for (const sheetName of wbRead.SheetNames) {
    const ws = wbRead.Sheets[sheetName];
    for (const addr of Object.keys(ws)) {
      if (addr.startsWith("!")) continue;
      if (ws[addr].t === "s") { foundSst = true; break outer; }
    }
  }
  assert.ok(foundSst, "No shared-string (t='s') cells found — bookSST may not be active");
});

// ==================== Export/import round-trip — spec §C.4 ====================
test("round-trip: exported row counts match live state", async () => {
  const before = {
    drainage:  sdc.state.drainage.length,
    structures: sdc.state.structures.length,
    pipes:      sdc.state.pipes.length,
    outletStructures: sdc.state.outletStructures.length,
    outletDevices:    sdc.state.outletDevices.length,
  };
  assert.ok(before.drainage > 0,   "pre-condition: drainage rows must exist");
  assert.ok(before.structures > 0, "pre-condition: structure rows must exist");
  assert.ok(before.pipes > 0,      "pre-condition: pipe rows must exist");

  const wb  = sdc.buildWorkbook();
  const buf = window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true });
  const wbCheck = window.XLSX.read(new Uint8Array(buf), { type: "array", cellFormula: false });
  const daWs = wbCheck.Sheets["Drainage Area"];
  const stWs = wbCheck.Sheets["Junction Structure"];
  const piWs = wbCheck.Sheets["Pipe Sizing"];
  assert.ok(daWs, "Drainage Area sheet missing from exported workbook");
  assert.ok(stWs, "Junction Structure sheet missing from exported workbook");
  assert.ok(piWs, "Pipe Sizing sheet missing from exported workbook");

  const daRows = window.XLSX.utils.sheet_to_json(daWs, { header:1, defval:"" });
  const stRows = window.XLSX.utils.sheet_to_json(stWs, { header:1, defval:"" });
  const piRows = window.XLSX.utils.sheet_to_json(piWs, { header:1, defval:"" });

  assert.equal(daRows.length - 1, before.drainage,   `Drainage Area: exported ${daRows.length-1}, expected ${before.drainage}`);
  assert.equal(stRows.length - 1, before.structures, `Junction Structure: exported ${stRows.length-1}, expected ${before.structures}`);
  assert.equal(piRows.length - 1, before.pipes,      `Pipe Sizing: exported ${piRows.length-1}, expected ${before.pipes}`);
});

test("round-trip: exported HGL elevation matches live computed value", () => {
  const wb  = sdc.buildWorkbook();
  const wbCheck = window.XLSX.read(
    window.XLSX.write(wb, { bookType: "xlsx", type: "array", bookSST: true }),
    { type: "array", cellFormula: false }
  );
  const stWs   = wbCheck.Sheets["Junction Structure"];
  const stRows = window.XLSX.utils.sheet_to_json(stWs, { header:1, raw:true, defval:"" });
  const headers = stRows[0];
  const hglCol  = headers.indexOf("Upstream HGL (ft)");
  assert.ok(hglCol >= 0, "Upstream HGL (ft) column not found in Junction Structure header");
  let checked = 0;
  for (let i = 1; i < stRows.length; i++) {
    const row   = stRows[i];
    const label = String(row[0]);
    const st    = sdc.state.structures.find(s => (s.structureId||s.id) === label);
    if (!st) continue;
    const calc  = sdc.computeStructureCalc(st.id);
    if (!calc || !isFinite(calc.elevation)) continue;
    const exported = parseFloat(row[hglCol]);
    if (!isFinite(exported)) continue;
    isClose(exported, calc.elevation, 0.001,
      `HGL mismatch for ${label}: exported=${exported} live=${calc.elevation}`);
    checked++;
  }
  assert.ok(checked > 0, "expected at least one structure HGL value to be verified");
});

// ==================== HGL method toggle — conservative crown pin ====================
function pinFixture(outfallElev){
  const s0 = sdc.state;
  const saved = { structures: s0.structures, pipes: s0.pipes, hydraulics: s0.hydraulics };
  s0.structures = [
    { id:"pin-out", structureId:"PIN-OUT", type:"outfall", forceElev:true,
      startElev: outfallElev, drainageAreaId:"", rim:"" },
    { id:"pin-st",  structureId:"PIN-ST",  type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
  ];
  s0.pipes = [
    { id:"pin-pipe", fromStructureId:"pin-st", toStructureId:"pin-out",
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:99, downstreamInvert:98, splitRole:"" },
  ];
  return function restore(){ s0.structures = saved.structures; s0.pipes = saved.pipes; s0.hydraulics = saved.hydraulics; };
}

test("HGL method: conservative pins HGL below crown to crown", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-st");
  restore();
  assert.ok(calc != null, "calc is null");
  isClose(calc.hec22Elevation, 100.00, 0.001, "HEC-22 value should stay 100.00");
  isClose(calc.crown, 101.00, 0.001, "crown should be 99 + 24/12 = 101.00");
  isClose(calc.elevation, 101.00, 0.001, "HGL must be pinned to crown");
  assert.equal(calc.pinned, true, "pinned flag must be true");
});

test("HGL method: HEC-22 leaves below-crown HGL unchanged", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "hec22" };
  const calc = sdc.computeStructureCalc("pin-st");
  restore();
  isClose(calc.elevation, 100.00, 0.001, "HEC-22 HGL must stay at 100.00");
  assert.equal(calc.pinned, false, "pinned flag must be false under HEC-22");
});

test("HGL method: conservative leaves above-crown HGL unchanged", () => {
  const restore = pinFixture(102);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-st");
  restore();
  isClose(calc.elevation, 102.00, 0.001, "HGL above crown must not be lowered");
  assert.equal(calc.pinned, false, "pinned flag must be false when computed >= crown");
});

function chainFixture(){
  const s0 = sdc.state;
  const saved = { structures: s0.structures, pipes: s0.pipes, hydraulics: s0.hydraulics };
  s0.structures = [
    { id:"pin-out", structureId:"PIN-OUT", type:"outfall", forceElev:true,
      startElev: 100, drainageAreaId:"", rim:"" },
    { id:"pin-b",   structureId:"PIN-B",   type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
    { id:"pin-a",   structureId:"PIN-A",   type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
  ];
  s0.pipes = [
    { id:"pipe-b", fromStructureId:"pin-b", toStructureId:"pin-out",
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:99, downstreamInvert:98, splitRole:"" },
    { id:"pipe-a", fromStructureId:"pin-a", toStructureId:"pin-b",
      angle:0, shape:"circular", size:12, n:0.013, slope:0.01, length:100,
      upstreamInvert:100.5, downstreamInvert:99.5, splitRole:"" },
  ];
  return function restore(){ s0.structures = saved.structures; s0.pipes = saved.pipes; s0.hydraulics = saved.hydraulics; };
}

test("HGL method: pinned elevation propagates upstream", () => {
  const restore = chainFixture();
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calcB = sdc.computeStructureCalc("pin-b");
  const calcA = sdc.computeStructureCalc("pin-a");
  restore();
  isClose(calcB.elevation, 101.00, 0.001, "B pinned to its crown 99 + 24/12");
  assert.equal(calcB.pinned, true);
  // A now computes from B's PINNED elevation: 101.00 < A's crown (100.5 + 12/12 = 101.5)
  isClose(calcA.elevation, 101.50, 0.001, "A pinned to its crown, computed from B's pinned HGL");
  assert.equal(calcA.pinned, true);
  isClose(calcA.hec22Elevation, 101.00, 0.001, "A must compute from B's PINNED elevation");
});

test("HGL method: HEC-22 chain unchanged in same fixture", () => {
  const restore = chainFixture();
  sdc.state.hydraulics = { hglMethod: "hec22" };
  const calcA = sdc.computeStructureCalc("pin-a");
  restore();
  isClose(calcA.elevation, 100.00, 0.001, "HEC-22 chain: outfall 100 + 0 + 0");
});

test("HGL method: conservative applies to 25-yr override chain", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-st", null, "25yr");
  restore();
  isClose(calc.elevation, 101.00, 0.001, "25-yr chain must also be pinned");
  assert.equal(calc.pinned, true);
});

test("HGL method: base/forceElev structures are never pinned", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-out");
  restore();
  assert.equal(calc.isBase, true);
  isClose(calc.elevation, 100.00, 0.001, "outfall keeps its fixed elevation");
  assert.equal(calc.pinned, false, "base structures must never be pinned");
});

test("HGL method: missing crown falls back to unpinned HEC-22 value", () => {
  const s0 = sdc.state;
  const saved = { structures: s0.structures, pipes: s0.pipes, hydraulics: s0.hydraulics };
  s0.structures = [
    { id:"pin-out", structureId:"PIN-OUT", type:"outfall", forceElev:true,
      startElev: 100, drainageAreaId:"", rim:"" },
    { id:"pin-st", structureId:"PIN-ST", type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
  ];
  s0.pipes = [
    { id:"pin-pipe", fromStructureId:"pin-st", toStructureId:"pin-out",
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:"", downstreamInvert:"", splitRole:"" },
  ];
  s0.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-st");
  s0.structures = saved.structures; s0.pipes = saved.pipes; s0.hydraulics = saved.hydraulics;
  assert.equal(calc.crown, null, "fixture must produce a null crown");
  isClose(calc.elevation, 100.00, 0.001, "no crown -> keep HEC-22 value");
  assert.equal(calc.pinned, false);
});

test("HGL method: assumed-invert crown is still pinned and flagged", () => {
  const s0 = sdc.state;
  const saved = { structures: s0.structures, pipes: s0.pipes, hydraulics: s0.hydraulics };
  s0.structures = [
    { id:"pin-out", structureId:"PIN-OUT", type:"outfall", forceElev:true,
      startElev: 100, drainageAreaId:"", rim:"" },
    { id:"pin-st", structureId:"PIN-ST", type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
  ];
  s0.pipes = [
    { id:"pin-pipe", fromStructureId:"pin-st", toStructureId:"pin-out",
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      // No upstream invert: pipeInvertState assumes usInvert = DS + 0.1 = 98.1, assumed:true
      upstreamInvert:"", downstreamInvert:98, splitRole:"" },
  ];
  s0.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("pin-st");
  s0.structures = saved.structures; s0.pipes = saved.pipes; s0.hydraulics = saved.hydraulics;
  assert.equal(calc.crownAssumed, true, "fixture must produce an assumed crown");
  isClose(calc.crown, 100.10, 0.001, "assumed crown = 98.1 + 24/12");
  isClose(calc.elevation, 100.10, 0.001, "pin to the assumed crown");
  assert.equal(calc.pinned, true);
});

// ==================== HGL method toggle — UI ====================
test("renderRainfall: HGL method selector present and bound to state", () => {
  const s0 = sdc.state;
  const orig = s0.hydraulics;
  s0.hydraulics = { hglMethod: "conservative" };
  try {
    sdc.renderRainfall();
    const view = window.document.getElementById("view-rainfall");
    const sel = view.querySelector('select[data-focus-key="rf:hglMethod"]');
    assert.ok(sel, "HGL method select missing from Project Rainfall Settings");
    assert.equal(sel.options.length, 2, "selector must offer exactly two methods");
    assert.equal(sel.options[0].value, "hec22");
    assert.equal(sel.options[0].textContent, "HEC-22 (standard)");
    assert.equal(sel.options[1].value, "conservative");
    assert.equal(sel.options[1].textContent, "Conservative (crown-pin)");
    assert.equal(sel.value, "conservative", "selector must reflect current state");
  } finally {
    s0.hydraulics = orig;
    sdc.renderRainfall();
  }
});

// ==================== HGL method toggle — persistence ====================
test("hglMethodFromLabel: maps Excel labels to state values", () => {
  assert.equal(sdc.hglMethodFromLabel("Conservative"), "conservative");
  assert.equal(sdc.hglMethodFromLabel("conservative"), "conservative");
  assert.equal(sdc.hglMethodFromLabel("  CONSERVATIVE  "), "conservative");
  assert.equal(sdc.hglMethodFromLabel("HEC-22"), "hec22");
  assert.equal(sdc.hglMethodFromLabel(""), "hec22");
  assert.equal(sdc.hglMethodFromLabel(undefined), "hec22");
  assert.equal(sdc.hglMethodFromLabel("Nonsense"), "hec22");
});

test("round-trip: HGL Method row exported on Rainfall Settings sheet", () => {
  const s0 = sdc.state;
  const orig = s0.hydraulics;
  s0.hydraulics = { hglMethod: "conservative" };
  const wb = sdc.buildWorkbook();
  s0.hydraulics = orig;
  const ws = wb.Sheets["Rainfall Settings"];
  assert.ok(ws, "Rainfall Settings sheet missing");
  const rows = window.XLSX.utils.sheet_to_json(ws, {header:1, raw:false, defval:""});
  const row = rows.find(r => String(r[0]).trim() === "HGL Method");
  assert.ok(row, "HGL Method row missing from Rainfall Settings sheet");
  assert.equal(String(row[1]).trim(), "Conservative");
});

test("round-trip: snapshot and restore carry hglMethod", () => {
  const s0 = sdc.state;
  const orig = s0.hydraulics;
  s0.hydraulics = { hglMethod: "conservative" };
  const snap = JSON.parse(JSON.stringify(sdc.captureState()));
  s0.hydraulics = { hglMethod: "hec22" };
  sdc.restoreState(snap, "HGL Method Snapshot Test");
  assert.equal(s0.hydraulics.hglMethod, "conservative", "restore must reinstate conservative method");
  // restore an old-style snapshot without hydraulics -> default hec22
  const oldSnap = JSON.parse(JSON.stringify(sdc.captureState()));
  delete oldSnap.hydraulics;
  sdc.restoreState(oldSnap, "HGL Method Snapshot Test");
  assert.equal(s0.hydraulics.hglMethod, "hec22", "missing hydraulics in snapshot must default to hec22");
  s0.hydraulics = orig;
});

// ==================== HGL method toggle — display surfaces ====================
test("buildHglRowSheet: method label and pin note under conservative", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const sheet = sdc.buildHglRowSheet("pin-st");
  restore();
  const text = sheet.textContent;
  assert.ok(text.includes("Method: Conservative (crown-pinned HGL)"), "method label missing");
  assert.ok(text.includes("computed 100.00 ft → pinned to pipe crown 101.00 ft"),
    "pin note must show computed value and crown value");
});

test("buildHglRowSheet: no pin note under HEC-22", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "hec22" };
  const sheet = sdc.buildHglRowSheet("pin-st");
  restore();
  assert.ok(!sheet.textContent.includes("pinned to pipe crown"), "no pin note under HEC-22");
});

test("buildHglDetailSheet: title carries method label", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const sheet = sdc.buildHglDetailSheet();
  restore();
  assert.ok(sheet, "detail sheet is null — state.pipes must be non-empty (fixture provides one)");
  assert.ok(sheet.textContent.includes("Conservative (crown-pinned HGL)"),
    "print detail header must carry the method label");
});

// ==================== HGL method toggle — Excel export no-drift ====================
// The Junction Structure sheet exports "Upstream HGL (ft)" (column Q) as a live
// formula. The workbook has no calcChain, so Excel recalculates formulas on
// open. Under the Conservative method the cached value is the crown-pinned
// elevation; the live formula must implement the same pin (conditional on the
// Rainfall Settings "HGL Method" row) or Excel silently reverts pinned HGLs to
// the HEC-22 chain — a drift violation.
function jsStructRowFor(wb, label){
  const ws = wb.Sheets["Junction Structure"];
  assert.ok(ws, "Junction Structure sheet missing from workbook");
  const rows = window.XLSX.utils.sheet_to_json(ws, { header:1, raw:true, defval:null });
  const idx = rows.findIndex(r => String(r[0]).trim() === label);
  assert.ok(idx >= 0, "structure row " + label + " missing from Junction Structure sheet");
  return idx + 1; // rows[0] is the header (Excel row 1), so data starts at idx+1
}

test("Excel export: conservative HGL formula implements the conditional crown pin", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const wb = sdc.buildWorkbook();
  restore();
  const row = jsStructRowFor(wb, "PIN-ST");
  const cell = wb.Sheets["Junction Structure"]["Q"+row];
  assert.ok(cell, "Upstream HGL (ft) cell missing for PIN-ST");
  const f = String(cell.f);
  assert.ok(f.includes('MATCH("HGL Method"'),
    "formula must look up the HGL Method row by name: " + f);
  assert.ok(f.includes("'Rainfall Settings'"),
    "formula must read the method from the Rainfall Settings sheet: " + f);
  assert.ok(f.includes('"Conservative"'),
    "formula must branch on the Conservative label: " + f);
  assert.ok(f.includes("MAX("),
    "Conservative branch must MAX the chain result with the crown cell: " + f);
  assert.ok(f.includes("G"+row),
    "pin branch must reference this row's crown column G: " + f);
  // HEC-22 chain mechanics must be preserved verbatim inside the wrapper.
  assert.ok(f.includes("INDEX(Q:Q,MATCH(R"+row+",A:A,0))"),
    "downstream HGL INDEX chain must be preserved: " + f);
  assert.ok(f.includes("M"+row) && f.includes("O"+row),
    "Hf (M) and Hb (O) cell references must be preserved: " + f);
});

test("Excel export: HEC-22 export keeps the plain chain formula, no pin branch", () => {
  const restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "hec22" };
  const wb = sdc.buildWorkbook();
  restore();
  const row = jsStructRowFor(wb, "PIN-ST");
  const cell = wb.Sheets["Junction Structure"]["Q"+row];
  assert.ok(cell, "Upstream HGL (ft) cell missing for PIN-ST");
  const f = String(cell.f);
  assert.ok(!f.includes('MATCH("HGL Method"'),
    "HEC-22 export must not carry the Conservative pin branch: " + f);
  assert.ok(!f.includes("MAX("), "HEC-22 export must not MAX with the crown: " + f);
  assert.ok(f.includes("M"+row) && f.includes("O"+row),
    "HEC-22 chain formula must keep its Hf/Hb references: " + f);
});

test("Excel export: cached HGL value is the pinned 101.00 (conservative) and 100.00 (HEC-22)", () => {
  let restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "conservative" };
  let wb = sdc.buildWorkbook();
  let row = jsStructRowFor(wb, "PIN-ST");
  let v = wb.Sheets["Junction Structure"]["Q"+row].v;
  restore();
  isClose(v, 101.00, 0.001, "conservative cached HGL must be the pinned crown 101.00");

  restore = pinFixture(100);
  sdc.state.hydraulics = { hglMethod: "hec22" };
  wb = sdc.buildWorkbook();
  row = jsStructRowFor(wb, "PIN-ST");
  v = wb.Sheets["Junction Structure"]["Q"+row].v;
  restore();
  isClose(v, 100.00, 0.001, "HEC-22 cached HGL must stay at the computed chain value 100.00");
});

// Fixture whose Formulas & Examples worked example (section 4 picks the first
// structure with exactly two inflow pipes) is a pinned structure, so the
// printed HGL sum and the printed result disagree unless the pin note appears.
function twoInflowPinFixture(){
  const s0 = sdc.state;
  const saved = { structures: s0.structures, pipes: s0.pipes, hydraulics: s0.hydraulics };
  s0.structures = [
    { id:"ti-out", structureId:"TI-OUT", type:"outfall", forceElev:true,
      startElev: 100, drainageAreaId:"", rim:"" },
    { id:"ti-j",   structureId:"TI-J",   type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
    { id:"ti-u1",  structureId:"TI-U1",  type:"manhole", forceElev:false,
      startElev:"", drainageAreaId:"", rim:"" },
  ];
  s0.pipes = [
    { id:"ti-out-pipe", fromStructureId:"ti-j", toStructureId:"ti-out",
      angle:0, shape:"circular", size:24, n:0.013, slope:0.01, length:100,
      upstreamInvert:99, downstreamInvert:98, splitRole:"" },
    { id:"ti-in1", fromStructureId:"ti-u1", toStructureId:"ti-j",
      angle:45, shape:"circular", size:12, n:0.013, slope:0.01, length:50,
      upstreamInvert:100, downstreamInvert:99.5, splitRole:"" },
    { id:"ti-in2", fromStructureId:"ti-u1", toStructureId:"ti-j",
      angle:90, shape:"circular", size:12, n:0.013, slope:0.01, length:50,
      upstreamInvert:100, downstreamInvert:99.5, splitRole:"" },
  ];
  return function restore(){ s0.structures = saved.structures; s0.pipes = saved.pipes; s0.hydraulics = saved.hydraulics; };
}

test("buildFormulasReferenceSheet: conservative pin note when the worked example pins", () => {
  const restore = twoInflowPinFixture();
  sdc.state.hydraulics = { hglMethod: "conservative" };
  const calc = sdc.computeStructureCalc("ti-j");
  const sheet = sdc.buildFormulasReferenceSheet();
  restore();
  assert.ok(sheet, "formulas reference sheet must build");
  assert.equal(calc.pinned, true, "fixture must actually pin the two-inflow example structure");
  isClose(calc.elevation, 101.00, 0.001, "example structure HGL must be pinned to crown 99 + 24/12");
  const text = sheet.textContent;
  assert.ok(text.includes("computed 100.00 ft → pinned to pipe crown 101.00 ft"),
    "pin note must disclose computed vs pinned values in the worked example");
});

test("buildFormulasReferenceSheet: no pin note under HEC-22", () => {
  const restore = twoInflowPinFixture();
  sdc.state.hydraulics = { hglMethod: "hec22" };
  const sheet = sdc.buildFormulasReferenceSheet();
  restore();
  assert.ok(sheet, "formulas reference sheet must build");
  assert.ok(!sheet.textContent.includes("pinned to pipe crown"),
    "no pin note under HEC-22");
});

// ==================== Visualizer handoff (transfer spec Feature B) ====================

// Boots the visualizer DEV file headless with the Node xlsx module injected,
// so its real validateImportedJson/applyImportedJson/importFromXlsxFile run.
function loadVisualizerWindow(){
  const vizHtml = readFileSync(new URL("../visualizer/storm-drain-visualizer-dev.html", import.meta.url), "utf8");
  const vizDom = new JSDOM(vizHtml, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(w){ w.XLSX = XLSX_NODE; }
  });
  return vizDom.window;
}

test("buildVisualizerPayload passes the visualizer's validateImportedJson", () => {
  const payload = sdc.buildVisualizerPayload();
  assert.equal(typeof payload, "object", "payload must be an object");
  const viz = loadVisualizerWindow();
  try {
    const result = viz.validateImportedJson(payload);
    // deepEqual against [] would fail on cross-realm prototype identity
    // (errors is an Array of the visualizer's jsdom realm), so check length.
    assert.ok(Array.isArray(result.errors) && result.errors.length === 0,
      "schema validation errors: " + result.errors.join("; "));
    assert.equal(result.valid, true);
  } finally {
    viz.close();
  }
});

test("payload config maps HGL method to visualizer method names", () => {
  const prev = sdc.state.hydraulics.hglMethod;
  try {
    sdc.state.hydraulics.hglMethod = "hec22";
    assert.equal(sdc.buildVisualizerPayload().config.hglMethod, "hec22");
    sdc.state.hydraulics.hglMethod = "conservative";
    assert.equal(sdc.buildVisualizerPayload().config.hglMethod, "legacy-both-crown",
      "calculator Conservative must map to legacy-both-crown, never the literal 'conservative'");
  } finally {
    sdc.state.hydraulics.hglMethod = prev;
  }
});

// Compare what the visualizer state holds after importing the JSON payload
// vs after importing the xlsx export of the SAME state. Numbers rounded to
// 5 decimals to absorb float noise; JSON round-trip puts both sides in the
// Node realm. x/y and pipe Hf are excluded (xlsx fills 0, payload omits —
// auto-layout assigns real coordinates either way).
function curatedImported(imported){
  return JSON.parse(JSON.stringify({
    structures: imported.structures.map(s=>({
      id:s.id, label:s.label, type:s.type, rim:s.rim, startElev:s.startElev, crown:s.crown,
      forceElev:s.forceElev, capturedQ:s.capturedQ, totalQ:s.totalQ, Hb:s.Hb,
      elevation:s.elevation, outPipeId:s.outPipeId })),
    pipes: imported.pipes.map(p=>({
      id:p.id, fromId:p.fromId, toId:p.toId, shape:p.shape, size:p.size, n:p.n,
      slope:p.slope, length:p.length, angle:p.angle, designQ:p.designQ,
      usInvert:p.usInvert, dsInvert:p.dsInvert, splitRole:p.splitRole })),
    outfall: imported.outfall,
    config: { hglMethod: imported.config.hglMethod },
    drainageAreas: imported.drainageAreas,
    tr55Segments: imported.tr55Segments
  }), (k,v)=> (typeof v==="number" && isFinite(v)) ? Number(v.toFixed(5)) : v);
}

// `window` here is the CALCULATOR's jsdom window (module top of this file);
// window.XLSX is the SheetJS bundled inside the BUILT calculator. Write the
// workbook in that realm, then wrap the bytes in a plain object (name +
// arrayBuffer) so the visualizer's importer runs its real code path without
// needing a jsdom File.
async function importExportedWorkbook(viz){
  const ab = window.XLSX.write(sdc.buildWorkbook(), { bookType:"xlsx", type:"array", bookSST:true });
  // XLSX.write may hand back an ArrayBuffer or a Buffer/Uint8Array depending
  // on realm; normalize to a true ArrayBuffer so the importer's read path
  // sees what a real File would provide.
  const fakeFile = { name:"drift.xlsx", arrayBuffer: async () => new Uint8Array(ab).slice().buffer };
  await viz.importFromXlsxFile(fakeFile);
}

test("visualizer payload matches xlsx import (drift guard, HEC-22)", async () => {
  // Pin the method explicitly rather than relying on ambient seed state.
  const prev = sdc.state.hydraulics.hglMethod;
  sdc.state.hydraulics.hglMethod = "hec22";
  const viz = loadVisualizerWindow();
  try {
    const payload = sdc.buildVisualizerPayload();
    await importExportedWorkbook(viz);
    const viaXlsx = curatedImported(viz.state.imported);
    viz.applyImportedJson(payload, "(test)");
    const viaJson = curatedImported(viz.state.imported);
    assert.deepEqual(viaJson, viaXlsx, "JSON payload drifted from the xlsx serialization");
    assert.equal(viaXlsx.config.hglMethod, "hec22");
  } finally {
    sdc.state.hydraulics.hglMethod = prev;
    viz.close();
  }
});

test("visualizer payload matches xlsx import (drift guard, Conservative)", async () => {
  const prev = sdc.state.hydraulics.hglMethod;
  sdc.state.hydraulics.hglMethod = "conservative";
  const viz = loadVisualizerWindow();
  try {
    const payload = sdc.buildVisualizerPayload();
    await importExportedWorkbook(viz);
    const viaXlsx = curatedImported(viz.state.imported);
    viz.applyImportedJson(payload, "(test)");
    const viaJson = curatedImported(viz.state.imported);
    // config.hglMethod is excluded until Task 5 lands (xlsx importer does
    // not yet read the Rainfall Settings HGL Method row); a dedicated
    // method-mapping assertion covers the payload side. curatedImported
    // shapes config as { hglMethod } only, so dropping config removes
    // exactly that field.
    const { config: _x, ...viaXlsxData } = viaXlsx;
    const { config: _j, ...viaJsonData } = viaJson;
    assert.deepEqual(viaJsonData, viaXlsxData, "Conservative payload drifted from the xlsx serialization");
    assert.equal(viaJson.config.hglMethod, "legacy-both-crown");
  } finally {
    sdc.state.hydraulics.hglMethod = prev;
    viz.close();
  }
});

test("hash handoff encoding round-trips the payload", () => {
  const payload = sdc.buildVisualizerPayload();
  const enc = sdc.encodeVisualizerHandoff(payload);
  assert.equal(typeof enc, "string", "seed payload must fit under the guard");
  assert.ok(enc.length <= sdc.VISUALIZER_HASH_MAX);
  assert.deepEqual(JSON.parse(decodeURIComponent(enc)), JSON.parse(JSON.stringify(payload)));
});

test("hash handoff size guard trips on oversized payloads", () => {
  const big = sdc.buildVisualizerPayload();
  big.structures[0].label = "x".repeat(70000);
  assert.equal(sdc.encodeVisualizerHandoff(big), null, "oversized payload must return null");
});

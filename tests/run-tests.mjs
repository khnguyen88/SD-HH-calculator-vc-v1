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
test("availableStorms: noaa returns 3 storms", () => {
  assert.deepEqual([...sdc.availableStorms("noaa")], ["2yr","10yr","25yr"]);
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

/**
 * Generate a calculator-compatible Excel import file for the Bladensburg SD-1 sample project.
 * Uses the calculator's own buildWorkbook() so the format is guaranteed importable.
 *
 * Run: node tests/generate-bburg-import.mjs
 * Output: docs/bburg-sd1-import.xlsx
 */
import { readFileSync, writeFileSync } from "node:fs";
import { JSDOM } from "jsdom";

const html = readFileSync(
  new URL("../drainage-calculator/storm-drain-design-calculator.html", import.meta.url),
  "utf8"
);

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
});
const { window } = dom;

await new Promise((resolve, reject) => {
  const start = Date.now();
  const interval = setInterval(() => {
    if (window.__sdc) { clearInterval(interval); resolve(); }
    else if (Date.now() - start > 3000) { clearInterval(interval); reject(new Error("__sdc timeout")); }
  }, 20);
});

const sdc = window.__sdc;
const state = sdc.state;

// ---------------------------------------------------------------------------
// 1. Rainfall
// ---------------------------------------------------------------------------
state.rainfall = {
  rainfallSource: "moco",
  county: "Montgomery",
  customNoaa: { 5: "", 10: "", 15: "", 30: "", 60: "" },
  pipeStorm: "10yr",
  pipe25Check: false,
  inletStorm: "10yr",   // original inlet spacing sheet uses MoCo 10-yr
};

// ---------------------------------------------------------------------------
// 2. Drainage Areas
// All areas from Rationals-MCDOT sheet, converted from SF to AC (÷43560).
// Tc from Rationals Tc rows and inlet spacing sheet.
// ---------------------------------------------------------------------------
state.drainage = [
  { id:"da1", structureId:"EX-I-1", desc:"Existing Inlet EX-I-1", area:"0.0550", C:"0.8491", iOverride:"", tc:"5",  cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da2", structureId:"EX-I-2", desc:"Existing Inlet EX-I-2", area:"2.0137", C:"0.5821", iOverride:"", tc:"10", cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da3", structureId:"I-1",    desc:"Inlet I-1",              area:"0.1859", C:"0.7686", iOverride:"", tc:"7",  cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da4", structureId:"I-2",    desc:"Inlet I-2",              area:"0.2143", C:"0.8404", iOverride:"", tc:"5",  cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da5", structureId:"I-3",    desc:"Inlet I-3",              area:"0.3315", C:"0.5588", iOverride:"", tc:"10", cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da6", structureId:"I-4",    desc:"Inlet I-4",              area:"0.0771", C:"0.8698", iOverride:"", tc:"5",  cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da7", structureId:"I-5",    desc:"Inlet I-5",              area:"0.6656", C:"0.6542", iOverride:"", tc:"7",  cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da8", structureId:"I-6",    desc:"Inlet I-6",              area:"0.2576", C:"0.6082", iOverride:"", tc:"10", cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
  { id:"da9", structureId:"I-7",    desc:"Inlet I-7",              area:"2.4604", C:"0.5779", iOverride:"", tc:"10", cf:1.0, tcMethod:"direct", tr55:{segments:[]} },
];

// ---------------------------------------------------------------------------
// 3. Junction Structures
// crown = upstream invert + pipe diameter(ft) at that structure.
// rim   = not available from pipe capacity sheet; using large sentinel values.
// Start elevation on outfalls = downstream pipe invert (tailwater assumption).
// Kb = 0.5 for all inlets/manholes (generic).
// ---------------------------------------------------------------------------
// System A: I-3 → MH-3 → MH-2 → I-2 ← I-1;  I-2 → MH-1 ← EX-I-2;
//           MH-1 → EX-I-1 → CULVERT-A ← I-7
// System B: I-6 → I-5 → I-4 → CULVERT-B
state.structures = [
  // — System A —
  { id:"st1",  structureId:"I-3",      desc:"Inlet I-3",           type:"inlet",   drainageAreaId:"da5", crown:"71.0",  rim:"313.1",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st2",  structureId:"MH-3",     desc:"Manhole MH-3",        type:"manhole", drainageAreaId:"",    crown:"70.8",  rim:"300.0",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st3",  structureId:"MH-2",     desc:"Manhole MH-2",        type:"manhole", drainageAreaId:"",    crown:"70.1",  rim:"300.0",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st4",  structureId:"I-1",      desc:"Inlet I-1",           type:"inlet",   drainageAreaId:"da3", crown:"69.5",  rim:"314.2",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st5",  structureId:"I-2",      desc:"Inlet I-2",           type:"inlet",   drainageAreaId:"da4", crown:"69.5",  rim:"313.2",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st6",  structureId:"EX-I-2",   desc:"Existing Inlet EX-I-2", type:"inlet", drainageAreaId:"da2", crown:"69.2",  rim:"313.2",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st7",  structureId:"MH-1",     desc:"Manhole MH-1",        type:"manhole", drainageAreaId:"",    crown:"69.3",  rim:"315.2",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st8",  structureId:"EX-I-1",   desc:"Existing Inlet EX-I-1", type:"inlet", drainageAreaId:"da1", crown:"69.1",  rim:"312.5",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st9",  structureId:"I-7",      desc:"Inlet I-7",           type:"inlet",   drainageAreaId:"da9", crown:"69.1",  rim:"312.1",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st10", structureId:"CULVERT-A", desc:"Outfall Culvert A",  type:"outfall", drainageAreaId:"",    crown:"68.9",  rim:"999.0",  startElevation:"66.87", kb:0, forceStart:true },
  // — System B —
  { id:"st11", structureId:"I-6",      desc:"Inlet I-6",           type:"inlet",   drainageAreaId:"da8", crown:"73.4",  rim:"313.4",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st12", structureId:"I-5",      desc:"Inlet I-5",           type:"inlet",   drainageAreaId:"da7", crown:"73.5",  rim:"313.4",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st13", structureId:"I-4",      desc:"Inlet I-4",           type:"inlet",   drainageAreaId:"da6", crown:"72.9",  rim:"308.3",  startElevation:"", kb:0.5, forceStart:false },
  { id:"st14", structureId:"CULVERT-B", desc:"Outfall Culvert B",  type:"outfall", drainageAreaId:"",    crown:"72.5",  rim:"999.0",  startElevation:"71.04", kb:0, forceStart:true },
];

// ---------------------------------------------------------------------------
// 4. Pipes
// slope stored as decimal fraction (0.009824 = 0.9824%).
// size in inches. shape = "circle". n = 0.013 (RCP).
// ---------------------------------------------------------------------------
state.pipes = [
  // System A
  { id:"p1",  fromStructureId:"st1",  toStructureId:"st2",  shape:"circular", size:"12", n:"0.013", slope:"0.009824", length:"23.41" },
  { id:"p2",  fromStructureId:"st2",  toStructureId:"st3",  shape:"circular", size:"12", n:"0.013", slope:"0.009952", length:"56.27" },
  { id:"p3",  fromStructureId:"st3",  toStructureId:"st5",  shape:"circular", size:"12", n:"0.013", slope:"0.009971", length:"71.21" },
  { id:"p4",  fromStructureId:"st4",  toStructureId:"st5",  shape:"circular", size:"12", n:"0.013", slope:"0.009754", length:"21.53" },
  { id:"p5",  fromStructureId:"st5",  toStructureId:"st7",  shape:"circular", size:"15", n:"0.013", slope:"0.009998", length:"80.02" },
  { id:"p6",  fromStructureId:"st6",  toStructureId:"st7",  shape:"circular", size:"21", n:"0.013", slope:"0.010135", length:"5.92"  },
  { id:"p7",  fromStructureId:"st7",  toStructureId:"st8",  shape:"circular", size:"24", n:"0.013", slope:"0.010199", length:"19.61" },
  { id:"p8",  fromStructureId:"st8",  toStructureId:"st10", shape:"circular", size:"24", n:"0.013", slope:"0.010000", length:"14.36" },
  { id:"p9",  fromStructureId:"st9",  toStructureId:"st10", shape:"circular", size:"24", n:"0.013", slope:"0.009876", length:"23.29" },
  // System B
  { id:"p10", fromStructureId:"st11", toStructureId:"st12", shape:"circular", size:"12", n:"0.013", slope:"0.009991", length:"32.03" },
  { id:"p11", fromStructureId:"st12", toStructureId:"st13", shape:"circular", size:"18", n:"0.013", slope:"0.019621", length:"29.56" },
  { id:"p12", fromStructureId:"st13", toStructureId:"st14", shape:"circular", size:"18", n:"0.013", slope:"0.010142", length:"32.31" },
];

// ---------------------------------------------------------------------------
// 5. Inlet Spacing (10-yr MoCo — from Inlet Spacing_10-yr sheet)
// W=1.33 ft (from original: "GUTTER WIDTH = 1.33 FEET")
// a=0.0833 ft (depression "a" = 1 inch = 0.0833 ft from original: 0.0833 ft)
// n=0.013 (from original: "N = 0.013")
// For SUMP inlets: Sx is set to a negative value or use structureType="SUMP"
// structureType: "" = on-grade, "SUMP" = sump
// ---------------------------------------------------------------------------
state.inletSpacing = [
  { id:"is1",  linkedStructureId:"", label:"EX-I-1", structureType:"SUMP",     area:"0.0550", C:"0.8491", tc:"5",  iOverride:"", S:"0.055",  Sx:"0.001",  W:1.33, a:0.0833, n:0.013, L:"11.1", allowableSpread:"8", bypassTo:"" },
  { id:"is2",  linkedStructureId:"", label:"EX-I-2", structureType:"SUMP",     area:"2.0137", C:"0.5821", tc:"10", iOverride:"", S:"0.040",  Sx:"0.001",  W:1.33, a:0.0833, n:0.013, L:"15",   allowableSpread:"8", bypassTo:"" },
  { id:"is3",  linkedStructureId:"", label:"I-1",    structureType:"",         area:"0.1859", C:"0.7686", tc:"7",  iOverride:"", S:"0.044",  Sx:"0.01",   W:1.33, a:0.0833, n:0.013, L:"5",    allowableSpread:"8", bypassTo:"EX-I-1" },
  { id:"is4",  linkedStructureId:"", label:"I-2",    structureType:"",         area:"0.2143", C:"0.8404", tc:"5",  iOverride:"", S:"0.0219", Sx:"0.0212", W:1.33, a:0.0833, n:0.013, L:"15",   allowableSpread:"8", bypassTo:"" },
  { id:"is5",  linkedStructureId:"", label:"I-3",    structureType:"",         area:"0.3315", C:"0.5588", tc:"10", iOverride:"", S:"0.019",  Sx:"0.08",   W:1.33, a:0.0833, n:0.013, L:"10",   allowableSpread:"8", bypassTo:"" },
  { id:"is6",  linkedStructureId:"", label:"I-4",    structureType:"SUMP",     area:"0.0771", C:"0.8698", tc:"5",  iOverride:"", S:"0.027",  Sx:"0.001",  W:1.33, a:0.0833, n:0.013, L:"5",    allowableSpread:"8", bypassTo:"" },
  { id:"is7",  linkedStructureId:"", label:"I-5",    structureType:"SUMP",     area:"0.6656", C:"0.6542", tc:"7",  iOverride:"", S:"0.054",  Sx:"0.001",  W:1.33, a:0.0833, n:0.013, L:"5",    allowableSpread:"8", bypassTo:"" },
  { id:"is8",  linkedStructureId:"", label:"I-6",    structureType:"",         area:"0.2576", C:"0.6082", tc:"10", iOverride:"", S:"0.026",  Sx:"0.007",  W:1.33, a:0.0833, n:0.013, L:"5",    allowableSpread:"8", bypassTo:"I-5" },
  { id:"is9",  linkedStructureId:"", label:"I-7",    structureType:"",         area:"2.4604", C:"0.5779", tc:"10", iOverride:"", S:"0.0291", Sx:"0.0162", W:1.33, a:0.0833, n:0.013, L:"15",   allowableSpread:"8", bypassTo:"EX-I-1" },
];

state.inletSpacingSettings = {
  street: "Second Avenue / MD 410",
  allowableSpread: "8",
};

// ---------------------------------------------------------------------------
// 6. Project info
// ---------------------------------------------------------------------------
state.projectInfo = {
  title: "Bladensburg SD-1 — Storm Drain Design",
  date: "2026-09-10",
  by: "Sample Import",
  jobNo: "203403586",
  desc: "MD 410 storm sewer — imported from Stantec Bladensburg SD-1 drainage calculations",
};

// ---------------------------------------------------------------------------
// 7. Generate workbook and write file
// ---------------------------------------------------------------------------
const wb = sdc.buildWorkbook();
const XLSX = window.XLSX;
const buf = XLSX.write(wb, { bookType: "xlsx", type: "buffer", bookSST: true });
writeFileSync(new URL("../docs/bburg-sd1-import.xlsx", import.meta.url), buf);

console.log("✓ Wrote docs/bburg-sd1-import.xlsx");
console.log("\n--- Pipe sizing results (design Q vs capacity) ---");
console.log("System A: I-3 → MH-3 → MH-2 → I-2 ← I-1 → MH-1 ← EX-I-2 → EX-I-1 → CULVERT-A ← I-7");
console.log("System B: I-6 → I-5 → I-4 → CULVERT-B");
console.log("");

// Print pipe results using the calculator's calcPipeRow
const structs = state.structures;
const findSt = id => structs.find(s => s.id === id);

for (const pipe of state.pipes) {
  const fromSt = findSt(pipe.fromStructureId);
  const toSt   = findSt(pipe.toStructureId);
  const fromName = fromSt ? fromSt.structureId : pipe.fromStructureId;
  const toName   = toSt   ? toSt.structureId   : pipe.toStructureId;

  // Use computeTotalFlow to get design Q at the "from" structure
  const flow  = sdc.computeTotalFlow(pipe.fromStructureId);
  const calcRow = sdc.calcPipeRow(pipe);

  const Q_design = flow ? flow.Q : NaN;
  const Q_cap    = calcRow ? calcRow.Qfull : NaN;
  const V_full   = calcRow ? calcRow.V : NaN;
  const adequacy = Q_design <= Q_cap ? "OK  " : "FAIL";
  console.log(
    `${adequacy}  ${String(fromName).padEnd(8)} → ${String(toName).padEnd(10)}` +
    `  size=${String(pipe.size).padStart(2)}"  Q_design=${isFinite(Q_design)?Q_design.toFixed(3).padStart(6):"  N/A "} cfs` +
    `  Q_cap=${isFinite(Q_cap)?Q_cap.toFixed(3).padStart(6):"  N/A "} cfs` +
    `  V_full=${isFinite(V_full)?V_full.toFixed(2).padStart(5):"  N/A"} fps`
  );
}

// Also show original spreadsheet reference Q values for comparison
console.log("\n--- Original spreadsheet Q values (for comparison) ---");
const origQ = [
  ["I-3→MH-3",   0.989, 3.54],
  ["MH-3→MH-2",  0.995, 3.56],
  ["MH-2→I-2",   1.007, 3.57],
  ["I-1→I-2",    0.953, 3.53],
  ["I-2→MH-1",   3.396, 6.48],
  ["EX-I-2→MH-1",6.260,15.99],
  ["MH-1→EX-I-1",8.974,22.91],
  ["EX-I-1→CULV",11.261,22.68],
  ["I-7→CULV",   7.592,22.54],
  ["I-6→I-5",    0.837, 3.57],
  ["I-5→I-4",    3.861,14.75],
  ["I-4→CULV-B", 4.397,10.61],
];
origQ.forEach(([name,Q,cap]) => {
  console.log(`  ${String(name).padEnd(18)}  Q_orig=${Q.toFixed(3).padStart(6)} cfs   Q_cap=${cap.toFixed(2).padStart(6)} cfs`);
});

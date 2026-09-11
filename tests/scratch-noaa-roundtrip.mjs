// Scratch verification: export/import round-trip for fetchedNoaa (not a permanent test).
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

const html = readFileSync(
  new URL("../drainage-calculator/storm-drain-design-calculator.html", import.meta.url),
  "utf8"
);
const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true });
const { window } = dom;
await new Promise((res, rej) => {
  const t0 = Date.now();
  const iv = setInterval(() => {
    if (window.__sdc) { clearInterval(iv); res(); }
    else if (Date.now() - t0 > 2000) { clearInterval(iv); rej(new Error("__sdc timeout")); }
  }, 20);
});
const sdc = window.__sdc;
const XLSX = window.XLSX;

// 1. Set fetched data in state
sdc.state.rainfall.fetchedNoaa = {
  lat: 39.0123, lon: -77.4567, displayName: "Bethesda, Montgomery County, Maryland",
  "1yr": {5:4.1,10:3.1,15:2.2,30:1.3,60:0.9},
  "2yr": {5:5.1,10:4.1,15:3.2,30:2.3,60:1.6},
  "5yr": {5:6.1,10:5.1,15:4.2,30:3.3,60:2.2},
  "10yr": {5:6.65,10:5.31,15:4.48,30:3.24,60:2.11},
  "25yr": {5:7.51,10:5.99,15:5.04,30:3.74,60:2.49},
  "50yr": {5:8.16,10:6.48,15:5.48,30:4.12,60:2.8},
  "100yr": {5:8.8,10:6.96,15:5.88,30:4.5,60:3.1},
  "500yr": {5:10.14,10:8.04,15:6.72,30:5.36,60:3.84},
};
sdc.state.rainfall.county = "Fetched";

// 2. Export
const wb = sdc.buildWorkbook();
const ws = wb.Sheets["Rainfall Settings"];
const aoa = XLSX.utils.sheet_to_json(ws, {header:1, defval:""});
const rfMap = {};
aoa.forEach(r => { if (r[0]) rfMap[String(r[0]).trim()] = r[1]; });

console.log("Fetched NOAA Lat:", rfMap["Fetched NOAA Lat"]);
console.log("Fetched NOAA Lon:", rfMap["Fetched NOAA Lon"]);
console.log("Fetched NOAA Name:", rfMap["Fetched NOAA Name"]);
console.log("Fetched 1-yr 5-min:", rfMap["Fetched 1-yr 5-min (in/hr)"]);
console.log("Fetched 500-yr 60-min:", rfMap["Fetched 500-yr 60-min (in/hr)"]);

// 3. Simulate the import path (replicating the importExcel logic on the exported map)
const newRf = sdc.defaultRainfallSettings();
const fLat = parseFloat(rfMap["Fetched NOAA Lat"]);
const fLon = parseFloat(rfMap["Fetched NOAA Lon"]);
console.log("fLat finite:", Number.isFinite(fLat), "fLon finite:", Number.isFinite(fLon));
if (Number.isFinite(fLat) && Number.isFinite(fLon)) {
  const fData = { lat: fLat, lon: fLon, displayName: rfMap["Fetched NOAA Name"] || "" };
  const stormLabels = {"1yr":"1-yr","2yr":"2-yr","5yr":"5-yr","10yr":"10-yr","25yr":"25-yr",
                       "50yr":"50-yr","100yr":"100-yr","500yr":"500-yr"};
  for (const s of ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"]) {
    fData[s] = {};
    for (const d of [5,10,15,30,60]) {
      const v = parseFloat(rfMap["Fetched " + stormLabels[s] + " " + d + "-min (in/hr)"]);
      fData[s][d] = Number.isFinite(v) ? v : "";
    }
  }
  const orig = sdc.state.rainfall.fetchedNoaa;
  let allMatch = JSON.stringify(fData) === JSON.stringify({lat: fLat, lon: fLon, displayName: orig.displayName, ...orig});
  // compare manually (key order)
  allMatch = fData.lat === orig.lat && fData.lon === orig.lon && fData.displayName === orig.displayName;
  for (const s of ["1yr","2yr","5yr","10yr","25yr","50yr","100yr","500yr"]) {
    for (const d of [5,10,15,30,60]) {
      if (fData[s][d] !== orig[s][d]) { allMatch = false; console.log("MISMATCH", s, d, fData[s][d], orig[s][d]); }
    }
  }
  console.log("Round-trip all values match:", allMatch);
}

// 4. lookupIntensity with Fetched county works end-to-end in state
const i = sdc.lookupIntensity(10, "noaa", "10yr", "Fetched", {}, sdc.state.rainfall.fetchedNoaa);
console.log("lookupIntensity(10min, 10yr, Fetched):", i, "(expect 5.31)");
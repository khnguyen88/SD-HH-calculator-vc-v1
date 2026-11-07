#!/usr/bin/env node
/*
 * Regenerate fixtures/main-app-export.xlsx from the MAIN app's own code.
 *
 * The main calculator wraps everything in `(function(){ "use strict"; ... })()`,
 * so `state`, `seedExample`, and `buildWorkbook` are private. To drive it
 * headlessly we inject a single export line immediately after "use strict";
 * and then load the dev HTML in jsdom with the Node `xlsx` package standing in
 * for the in-page SheetJS bundle. The resulting workbook is produced by the
 * main app itself — no hand-authored data, no schema re-implementation here.
 *
 * Usage (from this directory):
 *   node generate-fixture.js
 *
 * jsdom and xlsx are dev-only dependencies of visualizer-tests (see
 * ../package.json). They are never shipped with either app.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { JSDOM } = require(path.join(__dirname, "..", "node_modules", "jsdom"));
const XLSX = require(path.join(__dirname, "..", "node_modules", "xlsx"));

const MAIN_DEV_HTML = path.join(
  __dirname, "..", "..", "storm-drain-design-calculator-dev.html"
);
const OUT_PATH = path.join(__dirname, "main-app-export.xlsx");

function buildInstrumentedHtml() {
  const html = fs.readFileSync(MAIN_DEV_HTML, "utf8");
  const marker = '"use strict";';
  const idx = html.indexOf(marker);
  if (idx < 0) {
    throw new Error('Could not find `"use strict";` in ' + MAIN_DEV_HTML);
  }
  const injection =
    marker +
    "\nglobalThis.__getApp = () => ({ state, buildWorkbook, seedExample });";
  return html.slice(0, idx) + injection + html.slice(idx + marker.length);
}

function main() {
  const html = buildInstrumentedHtml();

  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(window) {
      // Stand in for the inlined SheetJS bundle (dev HTML has only a sentinel).
      window.XLSX = XLSX;
      // init() observes the nav element; jsdom has no ResizeObserver.
      window.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
      };
    }
  });

  const app = dom.window.__getApp();
  if (!app || typeof app.seedExample !== "function") {
    throw new Error("Instrumentation failed: __getApp() did not expose the app");
  }

  app.seedExample();
  const wb = app.buildWorkbook();

  const required = ["Pipe Sizing", "Junction Structure"];
  for (const name of required) {
    if (!wb.SheetNames.includes(name)) {
      throw new Error("Workbook missing required sheet: " + name);
    }
  }

  XLSX.writeFile(wb, OUT_PATH, { bookSST: true });
  console.log("Wrote " + OUT_PATH);
  console.log("Sheets: " + wb.SheetNames.join(", "));
  dom.window.close();
}

main();

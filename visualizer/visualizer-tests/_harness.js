// Shared test harness: boots the dev HTML in jsdom and exposes its globals.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const DEV_HTML_PATH = path.join(__dirname, "..", "storm-drain-visualizer-dev.html");

function loadVisualizer(extraHeadScripts, opts) {
  opts = opts || {};
  const html = fs.readFileSync(DEV_HTML_PATH, "utf8");
  // Replace the SHEETJS sentinel with an inlined bundle when needed; tests pass
  // extraHeadScripts to inject the real `xlsx` module into globalThis.
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    url: opts.url,
    virtualConsole: opts.virtualConsole,
    beforeParse(window) {
      if (extraHeadScripts && extraHeadScripts.XLSX) window.XLSX = extraHeadScripts.XLSX;
    }
  });
  return {
    dom,
    window: dom.window,
    document: dom.window.document,
    // Grab any inlined function by name from window scope.
    fn: (name) => dom.window[name]
  };
}

module.exports = { loadVisualizer, DEV_HTML_PATH };

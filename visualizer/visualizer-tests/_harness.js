// Shared test harness: boots the dev HTML in jsdom and exposes its globals.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const DEV_HTML_PATH = path.join(__dirname, "..", "storm-drain-visualizer-dev.html");
const SHAPE_READER_PATH = path.join(__dirname, "..", "..",
  "drainage-calculator", "lib", "xlsx-shape-reader.js");

function loadVisualizer(extraHeadScripts, opts) {
  opts = opts || {};
  let html = fs.readFileSync(DEV_HTML_PATH, "utf8");

  // Spec 5 fix: jsdom can't resolve <script src="../drainage-calculator/...">
  // because the dev file lives at an unusual relative path. Inline the
  // shape reader source directly into the HTML so jsdom never has to fetch
  // it. The build-visualizer.js prod inliner does the same thing; this
  // harness just performs it eagerly for tests.
  const shapeReaderSrc = fs.readFileSync(SHAPE_READER_PATH, "utf8");
  html = html.replace(
    /<script src="\.\.\/drainage-calculator\/lib\/xlsx-shape-reader\.js"><\/script>/,
    "<script>\n" + shapeReaderSrc + "\n</script>"
  );

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

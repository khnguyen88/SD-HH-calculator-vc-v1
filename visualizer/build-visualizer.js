#!/usr/bin/env node
// Builds storm-drain-visualizer.html from the dev HTML by inlining SheetJS.
// Run: node visualizer/build-visualizer.js

const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname);
const DEV = path.join(ROOT, "storm-drain-visualizer-dev.html");
const OUT = path.join(ROOT, "storm-drain-visualizer.html");
// Shared with the main app build; the visualizer does not carry its own copy.
const SHEETJS = path.join(ROOT, "..", "drainage-calculator", "lib", "sheetjs-bundle.js");
// Spec 3 Task 22: share the Simple/Robust xlsx reader with the calculator.
const SHAPE_READER = path.join(ROOT, "..", "drainage-calculator", "lib", "xlsx-shape-reader.js");
const SENTINEL = "<!-- SHEETJS -->";

function build() {
  if (!fs.existsSync(DEV)) throw new Error("dev HTML not found: " + DEV);
  if (!fs.existsSync(SHEETJS)) throw new Error("sheetjs bundle not found: " + SHEETJS);
  if (!fs.existsSync(SHAPE_READER)) throw new Error("shape reader not found: " + SHAPE_READER);

  const html = fs.readFileSync(DEV, "utf8");
  if (!html.includes(SENTINEL)) throw new Error("sentinel not found in dev HTML: " + SENTINEL);

  const bundle = fs.readFileSync(SHEETJS, "utf8");
  const scriptTag = "<script>\n/* ==== SheetJS (inlined by build-visualizer.js) ==== */\n"
                  + bundle
                  + "\n/* ==== end SheetJS ==== */\n</script>";
  // Use a function replacer so `$&` / `$$` sequences inside the minified bundle
  // are not interpreted as replacement patterns (the main build.js escapes `$`
  // for the same reason).
  let out = html.replace(SENTINEL, () => scriptTag);

  // Spec 3 Task 22: inline the shape reader after SheetJS so
  // window.__xlsxShapeReader is available before bootstrap. Match the
  // placeholder comment AND the dev-mode <script src="..."> that follows,
  // so the built file does not try to fetch the external file. Mirrors the
  // pattern in drainage-calculator/build.js (its xlsx-shape-reader inline).
  const shapeReaderSrc = fs.readFileSync(SHAPE_READER, "utf8");
  const shapeReaderRe = /<!--\s*XLSX_SHAPE_READER_PLACEHOLDER\s*-->[\s\S]*?<script src="\.\.\/drainage-calculator\/lib\/xlsx-shape-reader\.js"><\/script>/;
  if (!shapeReaderRe.test(out)) {
    throw new Error("XLSX_SHAPE_READER_PLACEHOLDER marker not found in dev HTML");
  }
  out = out.replace(
    shapeReaderRe,
    () => "<script>\n/* ==== xlsx-shape-reader (inlined by build-visualizer.js) ==== */\n"
        + shapeReaderSrc
        + "\n/* ==== end xlsx-shape-reader ==== */\n</script>"
  );

  fs.writeFileSync(OUT, out, "utf8");
  const kb = Math.round(fs.statSync(OUT).size / 1024);
  console.log("visualizer: built OK (" + kb + " KB) -> " + OUT);
}

try { build(); }
catch (err) { console.error("visualizer build failed:", err.message); process.exit(1); }

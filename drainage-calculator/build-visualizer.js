#!/usr/bin/env node
// Builds storm-drain-visualizer.html from the dev HTML by inlining SheetJS.
// Run: node drainage-calculator/build-visualizer.js

const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname);
const DEV = path.join(ROOT, "storm-drain-visualizer-dev.html");
const OUT = path.join(ROOT, "storm-drain-visualizer.html");
const SHEETJS = path.join(ROOT, "lib", "sheetjs-bundle.js");
const SENTINEL = "<!-- SHEETJS -->";

function build() {
  if (!fs.existsSync(DEV)) throw new Error("dev HTML not found: " + DEV);
  if (!fs.existsSync(SHEETJS)) throw new Error("sheetjs bundle not found: " + SHEETJS);

  const html = fs.readFileSync(DEV, "utf8");
  if (!html.includes(SENTINEL)) throw new Error("sentinel not found in dev HTML: " + SENTINEL);

  const bundle = fs.readFileSync(SHEETJS, "utf8");
  const scriptTag = "<script>\n/* ==== SheetJS (inlined by build-visualizer.js) ==== */\n"
                  + bundle
                  + "\n/* ==== end SheetJS ==== */\n</script>";
  // Use a function replacer so `$&` / `$$` sequences inside the minified bundle
  // are not interpreted as replacement patterns (the main build.js escapes `$`
  // for the same reason).
  const out = html.replace(SENTINEL, () => scriptTag);

  fs.writeFileSync(OUT, out, "utf8");
  const kb = Math.round(fs.statSync(OUT).size / 1024);
  console.log("visualizer: built OK (" + kb + " KB) -> " + OUT);
}

try { build(); }
catch (err) { console.error("visualizer build failed:", err.message); process.exit(1); }

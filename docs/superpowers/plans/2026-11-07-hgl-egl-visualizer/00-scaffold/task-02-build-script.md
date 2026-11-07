# Task 02: Create the build script

## Context

Create `drainage-calculator/build-visualizer.js` that reads the dev HTML, replaces the `<!-- SHEETJS -->` sentinel with an inlined `<script>…</script>` block containing the SheetJS bundle, and writes `storm-drain-visualizer.html`. Mirrors the main app's `build.js`.

Implements spec §0 (single-file offline) and §10.3 (build script).

## Preconditions

- Prior tasks: task-01.
- `drainage-calculator/lib/sheetjs-bundle.js` exists (same file the main app uses).
- Node 18+ installed.

## Exact changes

**Create** `drainage-calculator/build-visualizer.js` with these exact contents:

```js
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
  const out = html.replace(SENTINEL, scriptTag);

  fs.writeFileSync(OUT, out, "utf8");
  const kb = Math.round(fs.statSync(OUT).size / 1024);
  console.log("visualizer: built OK (" + kb + " KB) -> " + OUT);
}

try { build(); }
catch (err) { console.error("visualizer build failed:", err.message); process.exit(1); }
```

Make the file executable-readable; no chmod needed on Windows but safe on Unix:

```
(Windows: skip. On Unix: chmod +x drainage-calculator/build-visualizer.js — optional.)
```

## Acceptance test

Run:

```
node drainage-calculator/build-visualizer.js
```

Expected output:

```
visualizer: built OK (<N> KB) -> <absolute-path>/storm-drain-visualizer.html
```

Verify:

1. `drainage-calculator/storm-drain-visualizer.html` exists.
2. Its size is ≥ 800 KB (SheetJS bundle is ~900 KB).
3. The string `<!-- SHEETJS -->` is **NOT** in the built file (it was replaced).
4. The built file opens by double-click, same dark page as the dev file.
5. Second run (re-run the build command): still produces a working file, same size (idempotent).

**PowerShell one-liner to check** (runs after build):

```
$built = "drainage-calculator/storm-drain-visualizer.html"
if (-not (Test-Path $built)) { throw "built file missing" }
$size = (Get-Item $built).Length
if ($size -lt 800*1024) { throw "built file too small: $size bytes" }
$content = Get-Content $built -Raw
if ($content.Contains("<!-- SHEETJS -->")) { throw "sentinel not replaced" }
Write-Host "visualizer build check: OK ($size bytes)"
```

## Done when

- `drainage-calculator/build-visualizer.js` exists with exactly the content above.
- Running `node drainage-calculator/build-visualizer.js` prints `visualizer: built OK` and exits 0.
- Built file passes the PowerShell check above.
- Commit: `feat(visualizer): task-02 build script inlines SheetJS`.

# Token Efficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut LLM context cost per editing session by extracting SheetJS from the dev file, adding section markers, and deduplicating shared input helpers.

**Architecture:** A new `storm-drain-design-calculator-dev.html` (SheetJS replaced by 1-line placeholder) becomes the file Claude edits. A `build.js` script inlines SheetJS back to produce `storm-drain-design-calculator.html` — the user-facing file, unchanged for end users. Section markers and deduplicated helpers go in the dev file and propagate to the built file.

**Tech Stack:** Vanilla JS/HTML, Node.js `fs` for the build script (no npm deps).

**Spec correction:** The design spec estimated 800–1,400 lines from render compression. After auditing, `delBtn`/`detailBtn` are already extracted; `buildXxx` detail sheets already share `makeDetailSheet`. Real duplication is 5 instances of `txt`/`num`/`txtInput`/`numInput` (~46 lines). Primary win remains SheetJS extraction (~437 KB / 56%).

---

### Task 1: Extract SheetJS to `lib/sheetjs-bundle.js`

**Files:**
- Create: `drainage-calculator/lib/sheetjs-bundle.js`

- [ ] **Step 1: Extract the SheetJS script content (everything between the script tags, not the tags themselves)**

```bash
sed -n '606,621p' drainage-calculator/storm-drain-design-calculator.html > drainage-calculator/lib/sheetjs-bundle.js
```

- [ ] **Step 2: Verify the extracted file starts and ends correctly**

```bash
head -c 60 drainage-calculator/lib/sheetjs-bundle.js
# Expected: /*! xlsx.js (C) 2013-present SheetJS -- http://sheetjs.com */
tail -c 40 drainage-calculator/lib/sheetjs-bundle.js
# Expected: ends with ...make_xlsx_lib(XLSX);
wc -c drainage-calculator/lib/sheetjs-bundle.js
# Expected: ~437000 bytes
```

- [ ] **Step 3: Commit**

```bash
git add drainage-calculator/lib/sheetjs-bundle.js
git commit -m "feat: extract SheetJS bundle to lib/sheetjs-bundle.js"
```

---

### Task 2: Create dev file with SheetJS placeholder

**Files:**
- Create: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 1: Copy the calculator to the dev file**

```bash
cp drainage-calculator/storm-drain-design-calculator.html drainage-calculator/storm-drain-design-calculator-dev.html
```

- [ ] **Step 2: Replace the SheetJS script block with the 1-line placeholder**

The block to replace is exactly:
```
<script>
[17 lines of minified SheetJS]
</script>
```

Run this to replace it:
```bash
node -e "
const fs = require('fs');
let s = fs.readFileSync('drainage-calculator/storm-drain-design-calculator-dev.html','utf8');
// SheetJS block starts with <script>\n/*! xlsx.js and ends with </script>
s = s.replace(/<script>\s*\/\*! xlsx\.js[\s\S]*?make_xlsx_lib\(XLSX\);\s*<\/script>/, '<script>/* SHEETJS_BUNDLE */<\/script>');
fs.writeFileSync('drainage-calculator/storm-drain-design-calculator-dev.html', s);
console.log('Done');
"
```

- [ ] **Step 3: Verify the replacement worked**

```bash
grep -n "SHEETJS_BUNDLE\|xlsx\.js" drainage-calculator/storm-drain-design-calculator-dev.html
# Expected: one line containing SHEETJS_BUNDLE, zero lines containing xlsx.js
wc -l drainage-calculator/storm-drain-design-calculator-dev.html
# Expected: ~2172 lines (6588 - 16)
wc -c drainage-calculator/storm-drain-design-calculator-dev.html
# Expected: ~344000 bytes
```

- [ ] **Step 4: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html
git commit -m "feat: create dev file with SheetJS placeholder"
```

---

### Task 3: Create and verify the build script

**Files:**
- Create: `drainage-calculator/build.js`

- [ ] **Step 1: Write the build script**

Create `drainage-calculator/build.js` with exactly this content:

```js
const fs = require('fs');
const path = require('path');

const dir = __dirname;
const devFile = path.join(dir, 'storm-drain-design-calculator-dev.html');
const bundleFile = path.join(dir, 'lib', 'sheetjs-bundle.js');
const outFile = path.join(dir, 'storm-drain-design-calculator.html');

const dev = fs.readFileSync(devFile, 'utf8');
const bundle = fs.readFileSync(bundleFile, 'utf8');

if (!dev.includes('/* SHEETJS_BUNDLE */')) {
  console.error('ERROR: placeholder not found in dev file');
  process.exit(1);
}

const built = dev.replace('/* SHEETJS_BUNDLE */', bundle);
fs.writeFileSync(outFile, built);

const inKB = Math.round(fs.statSync(devFile).size / 1024);
const outKB = Math.round(fs.statSync(outFile).size / 1024);
console.log(`Built: ${inKB} KB dev → ${outKB} KB dist`);
```

- [ ] **Step 2: Run the build and verify output matches the original**

```bash
# Save a hash of the original
node -e "const c=require('crypto'),fs=require('fs');console.log(c.createHash('md5').update(fs.readFileSync('drainage-calculator/storm-drain-design-calculator.html')).digest('hex'));"
# Run the build
node drainage-calculator/build.js
# Hash the output — must match
node -e "const c=require('crypto'),fs=require('fs');console.log(c.createHash('md5').update(fs.readFileSync('drainage-calculator/storm-drain-design-calculator.html')).digest('hex'));"
```

Both hashes must be identical. If they differ, check the sed extraction in Task 1 (the bundle may be missing a leading/trailing newline).

- [ ] **Step 3: Commit**

```bash
git add drainage-calculator/build.js
git commit -m "feat: add build.js to inline SheetJS bundle into dist file"
```

---

### Task 4: Add section markers to the dev file

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

Each marker goes on the line immediately before the function or block it labels.

- [ ] **Step 1: Confirm exact line numbers of each anchor point in the dev file**

```bash
grep -n "^function defaultPipeMaterials\|^function interpolatePL\|^function tr55SheetFlowTt\|^function findStructure\|^function pipeInvertState\|^function circularSegment\|^function el(\|^function getSaves\|^function renderOverview\|^function renderDrainage\|^function renderStructures\|^function renderPipes\|^function renderOutlet\|^function renderRainfall\|^function renderPipeSizing25\|^function renderHgl\b\|^function renderHgl25\|^function renderInletSpacing\|^function csSection\|^function printNodes\|^function num(v\|^function sheetToRows\|^function init(" drainage-calculator/storm-drain-design-calculator-dev.html
```

- [ ] **Step 2: Insert all section markers using Node**

Run this script (it inserts markers before the anchor functions found in Step 1):

```js
// save as drainage-calculator/add-markers.js, run once, then delete
const fs = require('fs');
const lines = fs.readFileSync('drainage-calculator/storm-drain-design-calculator-dev.html', 'utf8').split('\n');

const markers = [
  ['function defaultPipeMaterials()',          '// ====== SECTION: Data Tables ======'],
  ['function interpolatePL(',                  '// ====== SECTION: Hydrology / Rational Method ======'],
  ['function tr55SheetFlowTt(',                '// ====== SECTION: TR-55 Travel Time ======'],
  ['function findStructure(id)',               '// ====== SECTION: Network Graph / Flow ======'],
  ['function pipeInvertState(',                '// ====== SECTION: Pipe Hydraulics ======'],
  ['function circularSegment(',                '// ====== SECTION: Outlet Rating Curves ======'],
  ['function el(tag,',                         '// ====== SECTION: DOM Utilities ======'],
  ['function getSaves()',                       '// ====== SECTION: State / Persistence ======'],
  ['function renderOverview()',                 '// ====== SECTION: Render — Overview ======'],
  ['function renderDrainage()',                 '// ====== SECTION: Render — Drainage ======'],
  ['function renderStructures()',               '// ====== SECTION: Render — Structures ======'],
  ['function renderPipes()',                    '// ====== SECTION: Render — Pipes ======'],
  ['function renderOutlet()',                   '// ====== SECTION: Render — Outlet ======'],
  ['function renderRainfall()',                 '// ====== SECTION: Render — Rainfall ======'],
  ['function renderPipeSizing25()',             '// ====== SECTION: Render — Pipe Sizing ======'],
  ['function renderHgl()',                      '// ====== SECTION: Render — HGL ======'],
  ['function renderHgl25()',                    '// ====== SECTION: Render — HGL 25 ======'],
  ['function renderInletSpacing()',             '// ====== SECTION: Render — Inlet Spacing ======'],
  ['function csSection(',                       '// ====== SECTION: Calc Sheets ======'],
  ['function printNodes(',                      '// ====== SECTION: Print ======'],
  ['function num(v,def)',                       '// ====== SECTION: Excel Export ======'],
  ['function sheetToRows(',                     '// ====== SECTION: Excel Import ======'],
  ['function init()',                            '// ====== SECTION: Init ======'],
];

const inserted = new Set();
const out = [];
for (const line of lines) {
  const trimmed = line.trim();
  for (const [anchor, marker] of markers) {
    if (trimmed.startsWith(anchor) && !inserted.has(anchor)) {
      out.push(marker);
      inserted.add(anchor);
      break;
    }
  }
  out.push(line);
}
fs.writeFileSync('drainage-calculator/storm-drain-design-calculator-dev.html', out.join('\n'));
console.log('Inserted', inserted.size, 'markers');
```

Run it:
```bash
node drainage-calculator/add-markers.js
# Expected: Inserted 23 markers
```

- [ ] **Step 3: Verify markers were inserted**

```bash
grep -n "SECTION:" drainage-calculator/storm-drain-design-calculator-dev.html
# Expected: 23 lines, each with a unique section name
```

- [ ] **Step 4: Delete the one-off script and rebuild**

```bash
rm drainage-calculator/add-markers.js
node drainage-calculator/build.js
# Expected: Built: ~NNN KB dev → ~781 KB dist
```

- [ ] **Step 5: Verify built file still has the markers**

```bash
grep -c "SECTION:" drainage-calculator/storm-drain-design-calculator.html
# Expected: 23
```

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html
git commit -m "feat: add section markers to dev file for LLM navigation"
```

---

### Task 5: Extract shared `mkTxtInput` / `mkNumInput` helpers

**Files:**
- Modify: `drainage-calculator/storm-drain-design-calculator-dev.html`

- [ ] **Step 1: Add the two factory functions in the DOM Utilities section, immediately after `function el(tag, attrs, children)`**

Find line:
```
function el(tag, attrs, children){
```

After the closing `}` of `el`, insert:

```js
function mkTxtInput(focusNs, getRenderFn) {
  return function(row, field, w) {
    return el("input", {class:"cell-input txt", type:"text", style:"width:"+w+"px",
      value: row[field]||"",
      "data-focus-key": focusNs+":"+row.id+":"+field,
      oninput: (e) => { row[field]=e.target.value; withFocusPreserved(getRenderFn(row)); }});
  };
}
function mkNumInput(focusNs, getRenderFn) {
  return function(row, field, w) {
    return el("input", {class:"cell-input", type:"text", inputmode:"decimal", step:"any",
      style:"width:"+w+"px",
      value: row[field]===undefined||row[field]===null?"":row[field],
      "data-focus-key": focusNs+":"+row.id+":"+field,
      oninput: (e) => { row[field]=e.target.value; withFocusPreserved(getRenderFn(row)); }});
  };
}
```

- [ ] **Step 2: Replace the local helpers in `renderDrainage`**

Find and remove the two local function declarations at the bottom of `renderDrainage`:
```js
  function txt(row,field,w){
    return el("input",{class:"cell-input txt",type:"text",style:"width:"+w+"px",value:row[field]||"","data-focus-key":"drainage:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(()=>patchDrainageRow(row)); }});
  }
  function num(row,field,w){
    return el("input",{class:"cell-input",type:"text",inputmode:"decimal",step:"any",style:"width:"+w+"px",value:row[field]===undefined||row[field]===null?"":row[field],"data-focus-key":"drainage:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(()=>patchDrainageRow(row)); }});
  }
```

Add at the top of `renderDrainage` (after `const c = document.getElementById("view-drainage");`):
```js
  const txt = mkTxtInput("drainage", row=>()=>patchDrainageRow(row));
  const num = mkNumInput("drainage", row=>()=>patchDrainageRow(row));
```

- [ ] **Step 3: Replace the local helpers in `renderStructures`**

Find and remove:
```js
  function txt(row,field,w){
    return el("input",{class:"cell-input txt",type:"text",style:"width:"+w+"px",value:row[field]||"","data-focus-key":"structures:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderStructures); }});
  }
  function num(row,field,w){
    return el("input",{class:"cell-input",type:"text",inputmode:"decimal",step:"any",style:"width:"+w+"px",value:row[field]===undefined||row[field]===null?"":row[field],"data-focus-key":"structures:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderStructures); }});
  }
```

Add at the top of `renderStructures` (after `const c = document.getElementById("view-structures");`):
```js
  const txt = mkTxtInput("structures", ()=>renderStructures);
  const num = mkNumInput("structures", ()=>renderStructures);
```

- [ ] **Step 4: Replace the local helpers in `renderOutlet` (device block)**

Find and remove (around the outlet devices section, focus key `"outlet-dev:"`):
```js
  function txt(row,field,w){
    return el("input",{class:"cell-input txt",type:"text",style:"width:"+w+"px",value:row[field]||"","data-focus-key":"outlet-dev:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderOutlet); }});
  }
  function num(row,field,w){
    return el("input",{class:"cell-input",type:"text",inputmode:"decimal",step:"any",style:"width:"+w+"px",value:row[field]===undefined||row[field]===null?"":row[field],"data-focus-key":"outlet-dev:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderOutlet); }});
  }
```

Add 2-liner immediately before the outlet devices `state.outletDevices.forEach(` loop:
```js
  const txt = mkTxtInput("outlet-dev", ()=>renderOutlet);
  const num = mkNumInput("outlet-dev", ()=>renderOutlet);
```

- [ ] **Step 5: Replace the local helpers in `renderPipes`**

Find and remove:
```js
  function txtInput(row,field,w){
    return el("input",{class:"cell-input txt",type:"text",style:"width:"+w+"px",value:row[field]||"","data-focus-key":"pipes:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderAll); }});
  }
  function numInput(row,field,w){
    return el("input",{class:"cell-input",type:"text",inputmode:"decimal",step:"any",style:"width:"+w+"px",value:row[field]===undefined||row[field]===null?"":row[field],"data-focus-key":"pipes:"+row.id+":"+field,
      oninput:(e)=>{ row[field]=e.target.value; withFocusPreserved(renderAll); }});
  }
```

Add at top of `renderPipes` (after `const c = document.getElementById("view-pipes");`):
```js
  const txtInput = mkTxtInput("pipes", ()=>renderAll);
  const numInput = mkNumInput("pipes", ()=>renderAll);
```

- [ ] **Step 6: Replace the local helpers in `renderPipeN`**

Find and remove (focus key `"pipe-n:"`):
```js
  function txtInput(row, field, w) {
    return el("input", {class:"cell-input txt", type:"text", style:"width:"+w+"px",
      value: row[field] || "",
      "data-focus-key": "pipe-n:" + row.id + ":" + field,
      oninput: (e) => { row[field] = e.target.value; withFocusPreserved(renderAll); }});
  }
  function numInput(row, field, w) {
    return el("input", {class:"cell-input", type:"text", inputmode:"decimal", step:"any",
      style:"width:"+w+"px",
      value: row[field] === undefined || row[field] === null ? "" : row[field],
      "data-focus-key": "pipe-n:" + row.id + ":" + field,
      oninput: (e) => { row[field] = e.target.value; withFocusPreserved(renderAll); }});
  }
```

Add at top of `renderPipeN` (after `const c = document.getElementById("view-pipe-n");` or equivalent first line):
```js
  const txtInput = mkTxtInput("pipe-n", ()=>renderAll);
  const numInput = mkNumInput("pipe-n", ()=>renderAll);
```

- [ ] **Step 7: Rebuild**

```bash
node drainage-calculator/build.js
# Expected: Built: NNN KB dev → ~781 KB dist
```

- [ ] **Step 8: Commit**

```bash
git add drainage-calculator/storm-drain-design-calculator-dev.html drainage-calculator/storm-drain-design-calculator.html
git commit -m "refactor: extract mkTxtInput/mkNumInput shared helpers, remove 5 duplicate local closures"
```

---

### Task 6: Manual verification

**Files:** none modified — verification only

- [ ] **Step 1: Open `storm-drain-design-calculator.html` in a browser**

Double-click the file. Verify the **Overview** tab loads with no errors in the browser console (F12 → Console).

- [ ] **Step 2: Verify Drainage tab — input and focus**

Go to **Drainage Area** tab. Click **+ Add row**. Type an ID and area value. Tab to the next cell. Verify:
- The Q columns update as you type
- Focus does not jump to a different cell after typing

- [ ] **Step 3: Verify Structure tab — input and rendering**

Go to **Junction Structure** tab. Click **+ Add row**. Set Type to "Junction". Link a drainage area. Verify the Cap Q and Total Q columns populate.

- [ ] **Step 4: Verify Pipes tab**

Go to **Pipes** tab. Click **+ Add row**. Set From/To structures. Type a slope. Verify pass/fail badge updates.

- [ ] **Step 5: Verify Manning's n tab**

Go to **Manning's n** tab. Verify the pipe materials table renders with edit inputs.

- [ ] **Step 6: Verify Excel export**

Click **Export Excel** (or equivalent). Verify the file downloads and opens in Excel with all sheets populated.

- [ ] **Step 7: Verify Excel import round-trip**

Import the file just exported. Verify all values restore correctly.

- [ ] **Step 8: Confirm dev file does NOT work standalone (expected)**

Open `storm-drain-design-calculator-dev.html` directly in a browser. Confirm the page errors (SheetJS undefined) — this is the expected behavior for the dev file.

---

### Task 7: Update deployment runbook

**Files:**
- Modify: `docs/deployment-runbook.md`

- [ ] **Step 1: Add the build step to the Redeploy Procedure section**

Replace:
```markdown
## Redeploy Procedure

Run from the repo root on `main`. This copies the current calculator from `main` onto `gh-pages` as `index.html`, removes the stale `drainage-calculator/` directory from the `gh-pages` tree (if present), commits, and pushes.

```bash
git checkout main && git pull
git checkout gh-pages
git checkout main -- drainage-calculator/storm-drain-design-calculator.html
cp drainage-calculator/storm-drain-design-calculator.html index.html
rm -rf drainage-calculator
git add index.html && git commit -m "Redeploy calculator from main"
git push origin gh-pages
git checkout main
```
```

With:
```markdown
## Redeploy Procedure

Run from the repo root on `main`. Always run the build first — `storm-drain-design-calculator.html` is generated from `storm-drain-design-calculator-dev.html` and must not be hand-edited.

```bash
git checkout main && git pull
# Build the dist file from the dev file
node drainage-calculator/build.js
git add drainage-calculator/storm-drain-design-calculator.html
git commit -m "build: rebuild dist from dev file" --allow-empty
# Deploy to gh-pages
git checkout gh-pages
git checkout main -- drainage-calculator/storm-drain-design-calculator.html
cp drainage-calculator/storm-drain-design-calculator.html index.html
rm -rf drainage-calculator
git add index.html && git commit -m "Redeploy calculator from main"
git push origin gh-pages
git checkout main
```
```

Also update this line near the top of the file:
```markdown
its `index.html` is a byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from `main`.
```
To:
```markdown
its `index.html` is a byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from `main` (built from `storm-drain-design-calculator-dev.html` via `build.js` — never hand-edited).
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment-runbook.md
git commit -m "docs: update deployment runbook to include build step"
```

---

### Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the non-negotiable constraints block and key files block**

Replace the current constraints and key files sections with:

```markdown
## Non-negotiable constraints

- **Edit `storm-drain-design-calculator-dev.html`** — NOT the `.html` file. The `.html`
  file is built output; hand-edits will be overwritten.
- **Run `node drainage-calculator/build.js`** after every edit to regenerate
  `storm-drain-design-calculator.html` (the file users download and deploy).
- **The built file is ONE self-contained HTML** — all CSS/JS inline, SheetJS bundled
  inline, no CDN, no internet required, opens by double-clicking.
- **Never break the single-file/offline rule** in the built file.
- **This file (CLAUDE.md) must never exceed 200 lines.** Long-form docs live in /docs.

## Key files

- `drainage-calculator/storm-drain-design-calculator-dev.html` — **edit this** (no SheetJS, ~344 KB).
- `drainage-calculator/storm-drain-design-calculator.html` — built output for users; do not hand-edit.
- `drainage-calculator/build.js` — inlines SheetJS bundle; run after every dev-file change.
- `drainage-calculator/lib/sheetjs-bundle.js` — SheetJS source; never edit.
- `drainage-calculator/storm-drain-calculator-spec.md` — as-built build spec
  (phases, governing equations, known pitfalls). Read before changing the app.
- `docs/` — user guide, engineering methodology, deployment runbook.
- `docs/superpowers/specs|plans/` — design docs and implementation plans.
```

- [ ] **Step 2: Update the Deployment section**

Replace:
```markdown
## Deployment (GitHub Pages)

Full runbook: `docs/deployment-runbook.md`. In short:

1. Commit calculator changes to `main`; push.
2. `git checkout gh-pages`, copy the calculator to `index.html` (byte-identical),
   commit, push.
3. Site: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ (serves from
   the `gh-pages` branch, root).

Never hand-edit `gh-pages`'s `index.html` — always re-copy from main.
```

With:
```markdown
## Deployment (GitHub Pages)

Full runbook: `docs/deployment-runbook.md`. In short:

1. Edit `storm-drain-design-calculator-dev.html`; run `node drainage-calculator/build.js`.
2. Commit both dev and built files to `main`; push.
3. `git checkout gh-pages`, copy built file to `index.html`, commit, push.
4. Site: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/

Never hand-edit `gh-pages`'s `index.html` or `storm-drain-design-calculator.html` — always build from the dev file.
```

- [ ] **Step 3: Verify CLAUDE.md is under 200 lines**

```bash
wc -l CLAUDE.md
# Must be < 200
```

- [ ] **Step 4: Save (CLAUDE.md is gitignored — no commit needed)**

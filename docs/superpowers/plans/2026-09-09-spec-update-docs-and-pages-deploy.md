# Spec Update, Docs, and GitHub Pages Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the calculator's build spec to as-built (adding the undocumented TR-55 Tc feature), add user-facing docs, rewrite CLAUDE.md under 200 lines, and deploy the calculator to GitHub Pages via a `gh-pages` branch.

**Architecture:** Documentation-only changes to existing files on `main` (no calculator code changes), followed by a deploy that copies the calculator byte-identical to `index.html` on a new `gh-pages` branch. Pages serves the site from that branch.

**Tech Stack:** Markdown docs; git; `gh` CLI for Pages configuration; GitHub Pages static hosting.

**Design doc:** `docs/superpowers/specs/2026-09-09-spec-update-and-pages-deploy-design.md`

**Key facts the executor needs:**

- Calculator: `drainage-calculator/storm-drain-design-calculator.html` (~618KB single file, SheetJS inline, all 8 tabs implemented).
- Spec to update: `drainage-calculator/storm-drain-calculator-spec.md` (355 lines, phased build spec).
- As-built TR-55 feature (NOT in spec): `tcMethod:"direct"|"tr55"` per Drainage Area row; per-row `tr55.segments` array of `{type:"sheet"|"shallow"|"channel", ...}` segments; travel-time functions:
  - Sheet: `Tt = 0.007·(n·L)^0.8 / (P2^0.5 · s^0.4)` (TR-55 sheet flow, P2 = 2-yr 24-hr rainfall in in)
  - Shallow: `V = Cp·√s` with `TR55_SHALLOW_CP` lookup (paved 20.328, unpaved 16.1345, bare 9.965, cultivated 8.762, prairie 6.962, minTillage 5.032, forest 2.516)
  - Channel: Manning's `V = (1.49/n)·R^(2/3)·√s`, R = area/wetted-perimeter
  - `Tc = Σ Tt` in hours × 60 → minutes. All functions return 0 on incomplete input. Warnings for >1 sheet segment or sheet-after-concentrated segments.
  - Tables: `TR55_SHEET_N` (TR-55 Table 3-1, 10 surfaces), `TR55_CHANNEL_N` (9 Chow-style channel n values), editable lookup selects in a modal (`openTr55Modal`).
- Kb drift fix: spec §1.6 says "separate columns for Inlet / Manhole / Bend" seeded with "the standard AASHTO bend-loss curve (5°→0.06 through 90°→0.70)". As-built: the table HAS three columns, but `defaultKbRows()` seeds **all three with identical AASHTO bend-loss values** (0.06 at 5° … 0.70 at 90°, 12 rows); `KB_COLUMN_FOR_TYPE` maps inlet→inlet, manhole→manhole, bend/junction→bend, splitter→manhole, outfall→none. Fix: keep the three-column structure, correct the seeding description to say all three seed from the same AASHTO curve and the user is expected to differentiate them per their jurisdiction's chart.
- Tab-list drift: spec §1.7 lists 6 tabs; as-built has 8: Overview, Drainage Area, Junction Structures, Pipe Sizing, Outlet Structure, Formulas & Examples, Table 4-6 Reference, Kb Coefficients. Phase 1's tab list should say it starts with Overview/Drainage/Structures/Pipes/Table 4-6/Kb and grows in later phases.
- Pages URL: `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/`; remote: `https://github.com/khnguyen88/SD-HH-calculator-vc-v1.git`.
- CLAUDE.md hard cap: never longer than 200 lines.

---

### Task 1: Update the spec — add TR-55 phase and fix drift

**Files:**
- Modify: `drainage-calculator/storm-drain-calculator-spec.md`

- [ ] **Step 1: Insert a TR-55 phase after Phase 1 (numbered as needed) in the spec**

Insert a new phase section after the Phase 1 block (before the current "Phase 2 — Flow Splitter"), titled `## Phase 1B — TR-55 Segmental Time of Concentration`, with this content (adapt surrounding phase numbers' prose only where it references order — do not renumber every later heading):

````markdown
## Phase 1B — TR-55 Segmental Time of Concentration

NRCS TR-55 (1986) Chapter 3 / Worksheet 3. Each Drainage Area row gets a Tc method toggle:

- `tcMethod: "direct" | "tr55"`. `direct` (default) = user types Tc in minutes.
  `tr55` = Tc is computed from a per-row segment list and becomes read-only
  in the main table (with an "Edit TR-55" button to reopen the modal and a
  "⇠ Direct entry" button to discard segments and revert).

### 1B.1 Segments
`row.tr55.segments` — an ordered array; each segment is one reach of the flow
path, matching the real worksheet's arbitrary AB, BC, CD chain (not "exactly
one of each type"). Segment types:
```
sheet:    { type, n, L, s, P2 }        n = sheet-flow Manning's n (Table 3-1 lookup),
                                        P2 = 2-yr 24-hr rainfall (in), s = slope (ft/ft)
shallow:  { type, L, s, surface }       surface = shallow-concentrated lookup key
channel:  { type, L, s, n, area, wp }  area & wp = channel cross-section area (sf) and
                                        wetted perimeter (ft)
```

### 1B.2 Travel-time equations
```
sheet:    Tt = 0.007 × (n·L)^0.8 / (P2^0.5 × s^0.4)        (hours)
shallow:  V = Cp × √s        Tt = L / (3600·V)             (Cp from surface lookup)
channel:  R = area / wp                                    (ft)
          V = (1.49/n) × R^(2/3) × √s                      (ft/s)
          Tt = L / (3600·V)
Tc = Σ Tt over all segments, reported in minutes (×60).
```
Every function returns 0 — not NaN — when its inputs are incomplete, so a
partially-filled worksheet still shows a sensible running total instead of
breaking.

### 1B.3 Reference lookups (editable dropdowns, not free text)
- **`TR55_SHEET_N`** — TR-55 Table 3-1 roughness coefficients: smooth 0.011,
  fallow 0.05, cultivated ≤20% residue 0.06, cultivated >20% residue 0.17,
  short grass prairie 0.15, dense grasses 0.24, Bermuda grass 0.41,
  range 0.13, woods light underbrush 0.40, woods dense underbrush 0.80.
- **`TR55_SHALLOW_CP`** — shallow-concentrated velocity coefficients:
  paved 20.328, unpaved/grassed waterway (urban) 16.1345, nearly bare untilled
  9.965, cultivated straight-row 8.762, prairie short-grass 6.962, minimum
  tillage/woodlands 5.032, forest heavy litter 2.516.
- **`TR55_CHANNEL_N`** — typical open-channel Manning's n (Chow-style starting
  points, disclosed in the UI as editable and needing site-specific judgment):
  smooth pipe 0.011, concrete trowel/RCP 0.013, corrugated metal 0.024,
  concrete unfinished 0.017, earth clean straight 0.022, riprap 0.035,
  earth grassed 0.035, natural stream clean straight 0.030, natural stream
  weedy winding 0.050.

### 1B.4 UI — interactive modal, not a static worksheet
`openTr55Modal(row)` opens the shared modal: intro text explaining the
segmental method, per-segment numbered cards with a type `<select>`
(sheet/shallow/channel) that swaps which fields that segment shows, add and
remove buttons, a live running total, and per-segment velocity/hydraulic-radius
outputs where meaningful. The computed total is written back to `row.tc`
(displayed to 0.1 min) and the row shows it as a read-only value with the
Edit button.

### 1B.5 Sanity warnings
- More than one sheet-flow segment → warning (sheet flow normally occurs once,
  at the very start).
- A sheet-flow segment appearing after any shallow/channel segment → warning
  (flow doesn't revert to sheet once concentrated).
Warnings are advisory only — the computation still runs, because the real
worksheet allows the user to describe what the flow path actually is.

### 1B.6 Detail sheet
The modal's segments get a Detail/Print calc sheet like every other computed
output (Phase 7 helpers): per-segment inputs, the governing formula with
substituted numbers, per-segment travel time, and the summed Tc.
````

- [ ] **Step 2: Fix the §1.6 Kb seeding drift**

In the spec's §1.6 (Kb Coefficients), replace the sentence:

```markdown
Seed with the standard AASHTO bend-loss curve (5°→0.06 through 90°→0.70) and let the user override every cell
```

with:

```markdown
Seed **all three columns with the same standard AASHTO bend-loss curve** (12 rows, 5°→0.06 through 90°→0.70) — Inlet, Manhole, and Bend alike — and let the user override every cell. The as-built default is deliberately conservative: it does not silently pretend the agency-specific differences between inlet, manhole, and bend losses are known; the UI says so explicitly and the user is expected to enter their governing Appendix B chart's values per column before relying on results for submittal. Column use: Inlet reads `inlet`, Manhole reads `manhole`, Bend and Junction read `bend`, Flow Splitter reads `manhole`, Outfall has no structure loss.
```

- [ ] **Step 3: Fix the §1.7 tab-list drift**

In the spec's §1.7 ("Tabs for this phase"), append to the tab list sentence:

```markdown
(The full tool ends with 8 tabs — the six above, plus **Outlet Structure** and **Formulas & Examples**, added by Phases 3–6 — but Phase 1 builds only the six listed here.)
```

- [ ] **Step 4: Add TR-55 to the intro scope and testing sections**

- In the spec's opening paragraph (line 3), extend the scope sentence to mention "segmental TR-55 time of concentration" — e.g. change "covering storm drain conveyance design (Rational Method → Manning's → hydraulic grade line)" to "covering storm drain conveyance design (Rational Method → TR-55 time of concentration → Manning's → hydraulic grade line)".
- In Section C (testing), category 1 (unit-level formula checks), add: "TR-55 segment equations — sheet flow against the published Worksheet 3 closed form, shallow velocity against Cp·√s, channel velocity against Manning's, and Σ-Tt against a hand-summed multi-segment example."

- [ ] **Step 5: Read the full updated spec once for internal consistency**

Read `drainage-calculator/storm-drain-calculator-spec.md` end-to-end. Check: no phase references broken by the new Phase 1B, no remaining claims contradicted by the as-built app (tab lists, Kb seeding, TR-55). Fix anything found.

- [ ] **Step 6: Commit**

```bash
git add drainage-calculator/storm-drain-calculator-spec.md
git commit -m "Update spec to as-built: add TR-55 Tc phase, fix Kb and tab-list drift"
```

---

### Task 2: Write the user guide

**Files:**
- Create: `docs/user-guide.md`

- [ ] **Step 1: Write `docs/user-guide.md`**

A practical walkthrough of the tool, organized by tab. Content requirements (verify against the app while writing — the HTML is the source of truth; the spec also documents behavior):

- **Header**: title, one-paragraph what-it-is (single-file, offline, no install), link to the live Pages URL (`https://khnguyen88.github.io/SD-HH-calculator-vc-v1/`) and note the local copy can be opened by double-clicking the HTML file.
- **Quick start**: open the file → work the tabs left-to-right → Export to Excel to save; Import to restore.
- **Per-tab sections** (all 8 tabs from the app's `TABS` array): Overview, Drainage Area (Q=Cf·C·i·A; Tc by direct entry or TR-55 segments), Junction Structures (types incl. Flow Splitter; link a Drainage Area; Force fixed elevation), Pipe Sizing (From/To structures, angle, shape incl. elliptical via Table 4-6, Design Q pulled automatically; split Role for splitters), Outlet Structure (facilities, orifice/weir/pipe devices, composite rating curve, tailwater modes none/fixed/linked, precision uniform/individual with per-device Custom checkbox), Formulas & Examples (live-computed worked examples), Table 4-6 Reference (static input table, no detail buttons), Kb Coefficients (editable, seeded identical across columns — edit per your jurisdiction).
- **Detail sheets & printing**: the ⤢ Detail button on computed rows; print one sheet or Print All (warn: can exceed 100 pages with fine stage increments).
- **Excel export/import**: what's live-formula vs. exported as static value; hand-editing and re-importing.
- **Known limitations** (from the app's Overview notes): >2 inflow pipes at a structure flagged, not computed; outlet "Pipe" = large-orifice/short-culvert treatment; partial-flow orifice centroid-head method is a small overestimate mid-range (standard practice); Kb defaults must be overridden per governing chart.

Keep it task-oriented ("to size a pipe: …"), not a restatement of the spec.

- [ ] **Step 2: Commit**

```bash
git add docs/user-guide.md
git commit -m "Add user guide for the storm drain design calculator"
```

---

### Task 3: Write the engineering methodology doc

**Files:**
- Create: `docs/engineering-methodology.md`

- [ ] **Step 1: Write `docs/engineering-methodology.md`**

Reference documentation of every governing equation and its assumptions, sourced from the spec (Sections 1–7) and the app's Formulas & Examples tab. Must cover, each with the equation, variable definitions, units, and regime/validity conditions:

1. Rational Method: `Q = Cf·C·i·A` (with the frequency-factor Cf).
2. TR-55 segmental Tc: all three segment equations, the reference tables, the 0-on-incomplete-input rule, and the advisory warnings.
3. Manning's equation (full-flow pipe): `V = (1.486/n)·R^(2/3)·√S`, `R = D/4`, circular and elliptical (Table 4-6 equivalent circular diameter for R).
4. Friction loss: `Sf = (Q·n/(1.486·A·R^(2/3)))²`, `Hf = Sf·L`.
5. Structure loss — controlling-angle method: the 0/1/2/>2-inflow cases, `Kb(θ)·V²/2g`, the controlling angle = the smaller computed loss's angle, and the unsupported >2 case being flagged.
6. HGL propagation: `elevation = downstream elevation + Hf + Hb`, checked against crown+1.0 ft and rim−1.0 ft; force-elevation nodes (outfall, known tailwater).
7. Flow splitter: capacity and ratio methods, Primary/Secondary, Hf on primary only / Hb on total.
8. Outlet structure hydraulics: exact circular-segment wetted area and centroid (with the half-full closed-form verification `A=πR²/2`, `hc=4R/(3π)`), orifice/pipe dry/partial/full/submerged regimes with continuity at boundaries, weir rectangular/V-notch free flow, Villemonte submergence `[1−(H2/H1)^n]^0.385`, composite curve = sum of devices at shared headwater, tailwater modes.
9. **Assumptions & disclosed limitations section**: centroid-head Jensen-inequality overestimate (zero at boundaries, low-single-digit % mid-range, standard HydroCAD/PondPack practice); outlet "pipe" ≠ HDS-5 culvert analysis; Kb defaults identical across structure-type columns; Vout assumes near-full outflow pipe.
10. **Traceability note**: every computed value in the app, its detail sheet, and the Excel export derive from these same equations; the Formulas & Examples tab computes its worked examples live from current project data through the same functions.

- [ ] **Step 2: Commit**

```bash
git add docs/engineering-methodology.md
git commit -m "Add engineering methodology reference"
```

---

### Task 4: Write the deployment runbook and update the deployment note

**Files:**
- Create: `docs/deployment-runbook.md`
- Modify: `docs/deploying-to-github-pages.md`

- [ ] **Step 1: Write `docs/deployment-runbook.md`**

Operational runbook. Content:

- **Live URL**: `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/`
- **Repo**: `https://github.com/khnguyen88/SD-HH-calculator-vc-v1`
- **How Pages is wired**: serves from the `gh-pages` branch, root. The branch contains a single commit's worth of content: `index.html` (byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from main) and a small `README.md` pointing back at main.
- **Redeploy procedure** (exact commands, run from the repo root on `main`):
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
- **One-time Pages setup**: GitHub → repo → Settings → Pages → Source: *Deploy from a branch* → Branch: `gh-pages`, folder `/ (root)`. (Or `gh api` equivalent — see Task 6.)
- **Verification**: after push, wait for the Pages build (GitHub Actions/"Pages build and deployment"), then `curl -s https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ | head` should show the calculator's `<!DOCTYPE html>` markup; a browser visit should show the Overview tab.
- **Rollback**: `git checkout gh-pages && git revert <commit>` then push, or check out a known-good prior `index.html`.
- **Never** edit `gh-pages`'s `index.html` directly — always re-copy from main (the file is a build artifact of main's calculator).

- [ ] **Step 2: Replace `docs/deploying-to-github-pages.md` with a pointer**

Replace the file's entire content with:

```markdown
# Deploying to GitHub Pages

Remote repo: https://github.com/khnguyen88/SD-HH-calculator-vc-v1
Published site: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/

The site deploys from the `gh-pages` branch (calculator copied as `index.html`).
Full procedure, verification, and rollback: see [deployment-runbook.md](deployment-runbook.md).
```

- [ ] **Step 3: Commit**

```bash
git add docs/deployment-runbook.md docs/deploying-to-github-pages.md
git commit -m "Add deployment runbook; point deployment note at it"
```

---

### Task 5: Rewrite CLAUDE.md (under 200 lines)

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace CLAUDE.md content**

Replace the file with (target: well under 200 lines — roughly 40):

```markdown
# Storm Drain Design Calculator (SD-HH-calculator-vc-v1)

Single-file, offline storm drain design tool: Rational Method → TR-55 Tc →
Manning's pipe sizing → hydraulic grade line → BMP/SWM outlet rating curves,
with Excel export/import and printable calculation sheets.

## Non-negotiable constraints

- **The calculator is ONE HTML file** — `drainage-calculator/storm-drain-design-calculator.html`.
  All CSS/JS inline, SheetJS bundled inline, no CDN, no build step. It must open
  by double-clicking with no internet.
- **Never break the single-file/offline rule** when editing it.
- **This file (CLAUDE.md) must never exceed 200 lines.** Long-form docs live in /docs.

## Key files

- `drainage-calculator/storm-drain-design-calculator.html` — the app (edit this).
- `drainage-calculator/storm-drain-calculator-spec.md` — as-built build spec
  (phases, governing equations, known pitfalls). Read before changing the app.
- `docs/` — user guide, engineering methodology, deployment runbook.
- `docs/superpowers/specs|plans/` — design docs and implementation plans.

## Rules of the codebase (from the spec — details there)

- Every computed value traces to one governing equation, shared by the UI,
  the detail sheets, and the Excel export — never let them drift.
- Excel export MUST use `bookSST: true` (spec §B.1) or files are spec-invalid.
- All state-mutating input handlers route through `withFocusPreserved` (spec §A.2).
- Persistence is explicit Excel export/import only — no localStorage.
- Dark engineering aesthetic, monospace numerics, system fonts only.

## Deployment (GitHub Pages)

Full runbook: `docs/deployment-runbook.md`. In short:

1. Commit calculator changes to `main`; push.
2. `git checkout gh-pages`, copy the calculator to `index.html` (byte-identical),
   commit, push.
3. Site: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ (serves from
   the `gh-pages` branch, root).

Never hand-edit `gh-pages`'s `index.html` — always re-copy from main.
```

- [ ] **Step 2: Verify line count**

Run: `wc -l CLAUDE.md`
Expected: well under 200 (about 40).

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Rewrite CLAUDE.md with project context and deploy procedure"
```

---

### Task 6: Push main and deploy to gh-pages

**Files:**
- No working-tree file changes; creates the `gh-pages` branch on the remote.

- [ ] **Step 1: Push main**

```bash
git push origin main
```

Expected: main (with the spec, docs, CLAUDE.md commits) is on the remote.

- [ ] **Step 2: Create the gh-pages branch with the deploy content**

```bash
git checkout --orphan gh-pages
git rm -rf --cached . 2>/dev/null || true
rm -rf .git/index && git clean -fdx -e drainage-calculator 2>/dev/null || true
```

Then, keeping ONLY `index.html` and `README.md` in the branch:

```bash
cp drainage-calculator/storm-drain-design-calculator.html index.html
cat > README.md <<'EOF'
# SD-HH-calculator-vc-v1 — GitHub Pages

This branch is a deployment artifact. The calculator from `main`
(drainage-calculator/storm-drain-design-calculator.html) is copied here as
`index.html` to serve GitHub Pages. Do not edit `index.html` directly.

Live site: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/
Source of truth: `main` branch.
EOF
git add index.html README.md
git commit -m "Deploy calculator as index.html from main"
```

Note: the `rm -rf`/`git clean` steps clear the orphan branch's index; if `git clean` would delete untracked files you need, instead do the orphan dance in a temp worktree:
```bash
git worktree add ../gh-pages-deploy --orphan gh-pages 2>/dev/null || git worktree add ../gh-pages-deploy gh-pages
```
Either approach is acceptable as long as the resulting branch contains exactly `index.html` + `README.md` and `index.html` is byte-identical to main's calculator (verify with `git diff main gh-pages -- drainage-calculator/storm-drain-design-calculator.html` against a copy, or `cmp index.html drainage-calculator/storm-drain-design-calculator.html` before removing the original).

- [ ] **Step 3: Push gh-pages**

```bash
git push origin gh-pages
git checkout main
```

- [ ] **Step 4: Ensure Pages is configured to serve from gh-pages**

Check current config:
```bash
gh api repos/khnguyen88/SD-HH-calculator-vc-v1/pages
```
If it errors (404 = Pages not enabled) or `source.branch != "gh-pages"`, configure it:
```bash
gh api -X POST repos/khnguyen88/SD-HH-calculator-vc-v1/pages \
  -f "source[branch]=gh-pages" -f "source[path]=/" 2>/dev/null || \
gh api -X PUT repos/khnguyen88/SD-HH-calculator-vc-v1/pages \
  -f "source[branch]=gh-pages" -f "source[path]=/"
```
**This step changes the remote repo's settings — confirm with the user before running it if not already approved.** (The design doc records user approval for gh-pages-branch deployment, but ask if the API call itself is new information.)

- [ ] **Step 5: Wait for build and verify the live site**

Wait ~1–2 min, then:
```bash
curl -s https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ | head -c 400
```
Expected: starts with `<!DOCTYPE html>` and contains the calculator's `<title>` markup. If 404, check the Pages build status:
```bash
gh api repos/khnguyen88/SD-HH-calculator-vc-v1/pages/builds/latest
```

---

## Self-Review (already performed)

- **Spec coverage**: design §1 → Task 1; §2 → Tasks 2–4; §3 → Task 5; §4 → Task 6. CLAUDE.md 200-line cap enforced in Task 5 Step 2. Pages-config-if-unset handled in Task 6 Step 4.
- **Placeholders**: none — all doc contents are written out in full above.
- **Consistency**: TR-55 equations/tables copied from the as-built app code (lines 761–857 of the HTML); Kb seeding facts from `defaultKbRows()` (line 578); tab list from the `TABS` array (line 1301); URLs from `docs/deploying-to-github-pages.md`.
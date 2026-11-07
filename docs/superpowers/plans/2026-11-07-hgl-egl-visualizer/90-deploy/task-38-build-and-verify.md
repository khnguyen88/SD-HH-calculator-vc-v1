# Task 38: Build and verify end-to-end

## Context

Run the final build, open the built file, and walk through the acceptance scenarios: offline (no network), both views, import a fixture, ledger renders, edit mode works, export tweaked JSON downloads. Implements spec §10.4 and §10.5 (runbook).

## Preconditions

- Prior tasks: all task-01 through task-37.

## Exact changes

**Run** the full test suite first:

```powershell
npm --prefix drainage-calculator/visualizer-tests test
```

Expected output: `pass 40 / fail 0` (tasks 31–37). Note: `node --test <dir>` fails on
Node 22/Windows (it tries to require the directory); use `npm --prefix ... test` or run
`node --test` with no args from inside the tests dir.

**Then** build:

```powershell
node drainage-calculator/build-visualizer.js
```

Expected output: `visualizer: built OK (~510 KB)`. The original ≥800 KB estimate was wrong;
510 KB is correct. Verify self-containment instead: no `SHEETJS_BUNDLE` placeholder, zero
external `src|href="http(s)://` refs, no CDN hosts, SheetJS inlined.

The built `drainage-calculator/storm-drain-visualizer.html` stays **untracked** (regenerated
from the dev file); only the runbook change is committed.

**Then** manually verify the built file end-to-end:

1. Open `drainage-calculator/storm-drain-visualizer.html` by double-click (NOT via a local server).
2. Open browser DevTools (F12). Network tab, "Disable cache" checked.
3. Reload the page. **Assert**: only one request shown, for the `file://` URL itself. No other network activity.
4. Click `Open .xlsx`. Choose `drainage-calculator/visualizer-tests/fixtures/main-app-export.xlsx`.
5. **Assert**: iso view renders — at least one structure symbol and one pipe line visible.
6. Press `ArrowUp` once. **Assert**: ledger grows to 2 rows; iso view highlights one pipe yellow.
7. Press `V`. **Assert**: profile view appears with crown/invert/HGL/EGL polylines.
8. Press `V` again. Back to iso.
9. Press `E`. **Assert**: top-right button changes to `▸ edit`.
10. Click the expanded `+Hf` row's slope input; change value. **Assert**: ledger `delta` and the profile's EGL curve update immediately.
11. Click `export tweaked`. **Assert**: a `.json` file downloads.
12. Reload page, open the downloaded `.json`. **Assert**: edit mode is re-entered automatically and the override is present in the override panel.

**Finally**: update `docs/deployment-runbook.md` with a new section. Locate the end of the file and append:

```markdown
## HGL/EGL Visualizer (companion app)

Build and deploy mirror the main app's flow.

1. Edit `drainage-calculator/storm-drain-visualizer-dev.html`.
2. Run `node drainage-calculator/build-visualizer.js` to produce
   `drainage-calculator/storm-drain-visualizer.html`.
3. Run `node --test drainage-calculator/visualizer-tests/` — confirm `fail 0`.
4. Commit both dev and built files to `main`; push.
5. `git checkout gh-pages`, copy `drainage-calculator/storm-drain-visualizer.html`
   into the root as `visualizer.html`, commit, push.
6. Live at: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html

Never hand-edit `gh-pages`'s `visualizer.html` — always build from the dev file
(same rule as the main app).
```

## Acceptance test

Automated + headless: all tests pass, the build is self-contained, and a jsdom smoke of the
**built** file passes 12/12 (SheetJS inlined; fixture import → 6 structures/5 pipes; SVG
rendered; ArrowUp advances; V toggles iso↔profile; E enters edit; slope input records an
override; tweaked export contains `_overrides`).

Still manual (not reproducible headlessly): DevTools network tab showing zero outbound
requests; double-click `file://` launch; the real download dialog; visual inspection of
colors/layout/interaction feel.

## Done when

- All automated tests pass (40/40).
- Built file is self-contained (~510 KB) and the headless smoke passes.
- `docs/deployment-runbook.md` updated.
- Commit: `feat(visualizer): task-38 final build + runbook update`.
- Built `.html` left untracked (not committed).

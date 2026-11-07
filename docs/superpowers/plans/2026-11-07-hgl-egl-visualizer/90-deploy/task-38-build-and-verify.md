# Task 38: Build and verify end-to-end

## Context

Run the final build, open the built file, and walk through the acceptance scenarios: offline (no network), both views, import a fixture, ledger renders, edit mode works, export tweaked JSON downloads. Implements spec §10.4 and §10.5 (runbook).

## Preconditions

- Prior tasks: all task-01 through task-37.

## Exact changes

**Run** the full test suite first:

```powershell
cd drainage-calculator/visualizer-tests
npm install  # (one-time, if not already)
cd ../..
node --test drainage-calculator/visualizer-tests/
```

Expected output: `pass N / fail 0` with N ≥ 38 (sum of all tasks' test counts above).

**Then** build:

```powershell
node drainage-calculator/build-visualizer.js
```

Expected output: `visualizer: built OK (<NNN> KB)` — size ≥ 800 KB.

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

All 12 manual steps above produce the asserted outcome. No step fails.

Also: `git status` shows only intended files changed (`drainage-calculator/*visualizer*`, `docs/deployment-runbook.md`).

## Done when

- All automated tests pass.
- Built file ≥ 800 KB and opens offline by double-click.
- All 12 manual verification steps pass.
- `docs/deployment-runbook.md` updated.
- Commit: `feat(visualizer): task-38 final build + runbook update`.

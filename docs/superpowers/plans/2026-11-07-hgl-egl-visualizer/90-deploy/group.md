# Group 90: Deploy — build verification & GitHub Pages

**Purpose:** Verify the built file works end-to-end offline (no network, double-click open) and publish it to GitHub Pages.

**Tasks:**
- `task-38-build-and-verify.md` — run `build-visualizer.js`, open the built file in a browser with DevTools open, confirm zero network requests, import the fixture .xlsx, walk the ledger
- `task-39-ghpages-publish.md` — copy built file to `gh-pages` branch as `visualizer.html`, push, verify URL

**Group acceptance criteria:**
- `storm-drain-visualizer.html` opens by double-click with no internet connection.
- DevTools Network tab shows zero requests after the initial `file://` load.
- Importing the fixture .xlsx renders both views and populates the ledger.
- `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html` serves the built file.
- `docs/deployment-runbook.md` updated with the visualizer deploy steps.

**Spec references:** §10.4 (deployment), §10.5 (runbook addendum).

# Task 39: Publish to GitHub Pages

## Context

Publish the built visualizer to the `gh-pages` branch. Verify the live URL serves the file and all functionality works over HTTPS. Implements spec §10.4 (deployment).

## Status: local portion only (publishing pending authorization)

Done so far on `feature/hgl-egl-visualizer`: the main app's `topbar-right` now contains
`<a href="visualizer.html" target="_blank" rel="noopener">Open HGL Visualizer →</a>`, the main
app was rebuilt (`node drainage-calculator/build.js`), and the dev + built files were committed
as `feat(visualizer): task-39 toolbar link in main app`.

**NOT done:** the `gh-pages` worktree/publish steps and the remote `git push` below. Those touch
shared, public state and require explicit owner authorization. The built visualizer is available
locally at `visualizer/storm-drain-visualizer.html` for the deploy step.

## Preconditions

- Prior tasks: task-38 (build verified locally).
- Repo has a `gh-pages` branch already serving the main app's `index.html`.
- Write access to the GitHub remote.

## Exact changes

**IMPORTANT:** use a temp worktree for the gh-pages work to avoid destroying local state. Per the project memory, "prefer temp worktree over `git clean -fdx` for gh-pages-style deploys; preserves .claude/".

Steps (PowerShell):

```powershell
# 1. From repo root, create a temp worktree for gh-pages
$tempDir = Join-Path $env:TEMP "sd-hh-gh-pages-visualizer"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
git worktree add $tempDir gh-pages

# 2. Copy the built visualizer file into the worktree as visualizer.html
Copy-Item "visualizer/storm-drain-visualizer.html" "$tempDir/visualizer.html" -Force

# 3. Commit from inside the worktree
Set-Location $tempDir
git add visualizer.html
git commit -m "deploy(visualizer): publish built HGL/EGL visualizer"

# 4. Push gh-pages
git push origin gh-pages

# 5. Return to main worktree and remove the temp worktree
Set-Location (git rev-parse --show-toplevel)
git worktree remove $tempDir
```

**Verify the live URL** (allow ~1 minute for GitHub Pages to publish):

Open `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html` in a browser.

1. **Assert**: page loads with the dark Visualizer UI.
2. Open DevTools Network tab, reload. **Assert**: only the request for `visualizer.html` itself; no third-party requests (SheetJS is inlined).
3. Repeat the full task-38 manual verification (steps 4–12) against the live URL.

**Finally**: update the main app's toolbar to link to the visualizer. In `drainage-calculator/storm-drain-design-calculator-dev.html`, find the toolbar and add a link:

```html
<a href="visualizer.html" target="_blank" rel="noopener"
   style="margin-left:12px; color:inherit; font-size:13px;">Open HGL Visualizer →</a>
```

Then rebuild the main app:

```powershell
node drainage-calculator/build.js
```

And re-deploy the main app's updated `index.html` the same worktree way:

```powershell
$tempDir = Join-Path $env:TEMP "sd-hh-gh-pages-visualizer2"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
git worktree add $tempDir gh-pages
Copy-Item "drainage-calculator/storm-drain-design-calculator.html" "$tempDir/index.html" -Force
Set-Location $tempDir
git add index.html
git commit -m "deploy(calculator): add visualizer toolbar link"
git push origin gh-pages
Set-Location (git rev-parse --show-toplevel)
git worktree remove $tempDir
```

## Acceptance test

- `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html` loads and functions exactly as the local built file did in task-38.
- Main app at `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/` has a toolbar link labeled `Open HGL Visualizer →` that opens the visualizer in a new tab.
- Return trip: the visualizer's top-bar link labeled `← Back to Calculator` (optional nicety — add if time) returns to the main app.

## Done when

- `visualizer.html` deployed on `gh-pages` branch.
- Live URL serves the file and all task-38 manual checks pass over HTTPS.
- Main app rebuilt with visualizer link; main app redeployed.
- Commit `feat(visualizer): task-39 toolbar link in main app` on `main` for the dev-file link change.

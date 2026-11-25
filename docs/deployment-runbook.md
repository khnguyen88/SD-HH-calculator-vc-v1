# Deployment Runbook

Operational runbook for both apps deployed to GitHub Pages:

- **Storm drain design calculator** (`index.html` at root)
- **HGL/EGL visualizer** (`visualizer.html` at root)

Both are build artifacts of `main`: `gh-pages`'s files are byte-identical copies of the built HTML from `drainage-calculator/` and `visualizer/`, which are themselves built from the paired `-dev.html` files via `build.js` / `build-visualizer.js`. Never hand-edit `gh-pages` content — always re-copy from `main`.

## Live URLs

- Calculator: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/
- Visualizer: https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html

## Repo

https://github.com/khnguyen88/SD-HH-calculator-vc-v1

## How Pages Is Wired

GitHub Pages serves from the `gh-pages` branch, root (`/`). The branch contains:

- `index.html` — byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from `main`.
- `visualizer.html` — byte-identical copy of `visualizer/storm-drain-visualizer.html` from `main` (the latter is built locally and is not committed to `main`; only the dev source is).
- `README.md` — small file pointing back at `main` and explaining that `gh-pages` is an artifact branch.

No build step, no Actions workflow, no Jekyll. Pages serves the raw files at the site root.

## Redeploy Calculator

Run from the repo root on `main`. Always run the build first — `storm-drain-design-calculator.html` is generated from `storm-drain-design-calculator-dev.html` and must not be hand-edited.

```bash
git checkout main && git pull
# Build the dist file from the dev file
node drainage-calculator/build.js
git add drainage-calculator/storm-drain-design-calculator.html
git diff --cached --quiet || git commit -m "build: rebuild dist from dev file"
# Deploy to gh-pages
git checkout gh-pages
git checkout main -- drainage-calculator/storm-drain-design-calculator.html
cp drainage-calculator/storm-drain-design-calculator.html index.html
rm -rf drainage-calculator
git add index.html && git commit -m "Redeploy calculator from main"
git push origin gh-pages
git checkout main
```

Notes:
- Always run `node drainage-calculator/build.js` before deploying. The built file must be committed to `main` before being copied to `gh-pages`.
- `git checkout main -- drainage-calculator/storm-drain-design-calculator.html` stages main's built version into `gh-pages`'s index/worktree without switching branches' file state beyond that path.
- `rm -rf drainage-calculator` removes the directory if a prior redeploy left it behind; harmless if absent.
- The commit on `gh-pages` should be the only change; do not mix unrelated edits.

## Redeploy Visualizer

Unlike the calculator, the visualizer's built `storm-drain-visualizer.html` is **not** committed to `main` — only the dev source is tracked. Build locally on `main`, then copy the built file into `gh-pages`. A git worktree is used so `main`'s working tree (including `.claude/`, local caches, and the visualizer build artifact) is preserved during the deploy.

```bash
git checkout main && git pull
# Build the dist file from the dev file (produces visualizer/storm-drain-visualizer.html locally)
node visualizer/build-visualizer.js
npm --prefix visualizer/visualizer-tests test   # confirm "fail 0" before deploying
# Deploy via a temp worktree pinned to gh-pages
git worktree add ../ghp-visualizer gh-pages
cp visualizer/storm-drain-visualizer.html ../ghp-visualizer/visualizer.html
git -C ../ghp-visualizer add visualizer.html
git -C ../ghp-visualizer commit -m "Redeploy visualizer from main"
git -C ../ghp-visualizer push origin gh-pages
git worktree remove ../ghp-visualizer
```

Notes:
- Always run `node visualizer/build-visualizer.js` before copying. The built file is self-contained (SheetJS inlined, no CDN).
- The visualizer's test suite (`visualizer/visualizer-tests`) must pass; a red suite blocks deployment.
- The dev source (`visualizer/storm-drain-visualizer-dev.html`) is committed to `main`; the built artifact is not.
- The worktree approach keeps the current branch's working tree intact — do **not** `git checkout gh-pages` in-place for this app, or you'll lose the local build artifact and have to re-run `build-visualizer.js`.
- If `../ghp-visualizer` already exists from a prior run, `git worktree remove --force ../ghp-visualizer` first.

## Redeploy Both (combined)

If both apps need deploying together, build both first on `main`, then do a single `gh-pages` commit that stages both files. Using the worktree pattern (safe for the uncommitted visualizer artifact):

```bash
git checkout main && git pull
node drainage-calculator/build.js
git add drainage-calculator/storm-drain-design-calculator.html
git diff --cached --quiet || git commit -m "build: rebuild dist from dev file"
node visualizer/build-visualizer.js
npm --prefix visualizer/visualizer-tests test
git worktree add ../ghp-combined gh-pages
cp drainage-calculator/storm-drain-design-calculator.html ../ghp-combined/index.html
cp visualizer/storm-drain-visualizer.html ../ghp-combined/visualizer.html
git -C ../ghp-combined add index.html visualizer.html
git -C ../ghp-combined commit -m "Redeploy calculator and visualizer from main"
git -C ../ghp-combined push origin gh-pages
git worktree remove ../ghp-combined
```

## One-Time Pages Setup

GitHub UI: repo → **Settings** → **Pages** → **Source**: *Deploy from a branch* → **Branch**: `gh-pages`, folder `/ (root)`.

CLI equivalent (see Task 6 for the full script): use `gh api` to set the Pages source to the `gh-pages` branch at root. This is a one-time configuration; once set, every push to `gh-pages` triggers a Pages build and deployment.

## Verification

After `git push origin gh-pages`:

1. Wait for the GitHub Pages build. In the repo's **Actions** tab, look for **Pages build and deployment** to go green. Typical build time is under a minute.
2. Depending on what was redeployed:
   - Calculator: `curl -s https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ | head` should show the calculator's `<!DOCTYPE html>` markup, and a browser visit should land on the **Overview** tab.
   - Visualizer: `curl -s https://khnguyen88.github.io/SD-HH-calculator-vc-v1/visualizer.html | head` should show the visualizer's `<!DOCTYPE html>` markup, and a browser visit should render the empty visualizer with the topbar and sample-project loaders.

If the Actions build is red or curl returns old content, wait 30s and re-check (CDN cache). If still stale, see Rollback.

## Rollback

Two options, from the repo root:

```bash
# Option A: revert the latest redeploy commit
git checkout gh-pages
git revert <commit-sha>
git push origin gh-pages
git checkout main
```

```bash
# Option B: check out a known-good prior index.html
git checkout gh-pages
git checkout <known-good-commit> -- index.html
git commit -m "Roll back gh-pages index.html to <known-good-commit>"
git push origin gh-pages
git checkout main
```

`<commit-sha>` is the SHA of the redeploy commit to undo. `<known-good-commit>` is any prior `gh-pages` commit whose target file (`index.html` or `visualizer.html`) rendered correctly. For a single-file rollback, replace `index.html` in Option B with `visualizer.html` as needed.

## Never Hand-Edit `gh-pages`

`gh-pages`'s `index.html` and `visualizer.html` are build artifacts of `main`'s `drainage-calculator/storm-drain-design-calculator.html` and `visualizer/storm-drain-visualizer.html` respectively. Never edit them directly on `gh-pages` — any direct edit will be overwritten on the next redeploy and silently diverges the deployed site from `main`. To change what is deployed, edit the dev source on `main`, run the appropriate build script, then run the Redeploy procedure.

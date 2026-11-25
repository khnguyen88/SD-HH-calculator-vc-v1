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

## The `gh-pages` Worktree

Deploys use a **permanent** git worktree checked out at `../gh-pages-deploy`
(sibling of the main checkout), pinned to the `gh-pages` branch. All redeploy
commands below use `git -C ../gh-pages-deploy ...` and stay on `main` in the
primary checkout.

Why a persistent worktree and not an in-place `git checkout gh-pages`:
- The visualizer's built `storm-drain-visualizer.html` is **not** committed to
  `main` — only the dev source is tracked. A branch switch would hide it, and
  `rm`-style cleanup on `gh-pages` could discard it. A separate worktree keeps
  `main`'s working tree untouched.
- Faster than creating/removing a temp worktree each deploy.
- Preserves `.claude/` and other local tooling state.

Current worktrees can be listed with `git worktree list`.

First-time setup on a fresh clone (one-time, from the repo root):

```bash
git fetch origin gh-pages:gh-pages
git worktree add ../gh-pages-deploy gh-pages
```

After this, `../gh-pages-deploy` always holds the `gh-pages` tip. Never
`git worktree remove` it as part of a routine deploy.

## Redeploy Calculator

Run from the repo root on `main`. Always run the build first — `storm-drain-design-calculator.html` is generated from `storm-drain-design-calculator-dev.html` and must not be hand-edited.

```bash
git checkout main && git pull
# Build the dist file from the dev file
node drainage-calculator/build.js
git add drainage-calculator/storm-drain-design-calculator.html
git diff --cached --quiet || git commit -m "build: rebuild dist from dev file"
git push origin main
# Deploy into the persistent gh-pages worktree
cp drainage-calculator/storm-drain-design-calculator.html ../gh-pages-deploy/index.html
git -C ../gh-pages-deploy add index.html
git -C ../gh-pages-deploy diff --cached --quiet || git -C ../gh-pages-deploy commit -m "Redeploy calculator from main"
git -C ../gh-pages-deploy push origin gh-pages
```

Notes:
- The calculator's built file **is** committed to `main` (unlike the visualizer). Commit it on `main` before copying to the worktree so the deployed artifact is reproducible from the commit SHA.
- The `diff --cached --quiet` guard makes the commit a no-op when the built file didn't change (e.g., build was deterministic and nothing semantically changed).
- The commit on `gh-pages` should be the only change; do not mix unrelated edits.

## Redeploy Visualizer

Unlike the calculator, the visualizer's built `storm-drain-visualizer.html` is **not** committed to `main` — only the dev source is tracked. Build locally on `main`, then copy the built file into the gh-pages worktree.

```bash
git checkout main && git pull
# Build the dist file from the dev file (produces visualizer/storm-drain-visualizer.html locally)
node visualizer/build-visualizer.js
npm --prefix visualizer/visualizer-tests test   # confirm "fail 0" before deploying
# Deploy into the persistent gh-pages worktree
cp visualizer/storm-drain-visualizer.html ../gh-pages-deploy/visualizer.html
git -C ../gh-pages-deploy add visualizer.html
git -C ../gh-pages-deploy diff --cached --quiet || git -C ../gh-pages-deploy commit -m "Redeploy visualizer from main"
git -C ../gh-pages-deploy push origin gh-pages
```

Notes:
- Always run `node visualizer/build-visualizer.js` before copying. The built file is self-contained (SheetJS inlined, no CDN).
- The visualizer's test suite (`visualizer/visualizer-tests`) must pass; a red suite blocks deployment.
- The dev source (`visualizer/storm-drain-visualizer-dev.html`) is committed to `main`; the built artifact is not.
- If the build is deterministic and the dev source didn't change, the `diff --cached --quiet` guard turns the commit into a no-op.

## Redeploy Both (combined)

If both apps need deploying together, build both first on `main`, then do a single `gh-pages` commit that stages both files:

```bash
git checkout main && git pull
node drainage-calculator/build.js
git add drainage-calculator/storm-drain-design-calculator.html
git diff --cached --quiet || git commit -m "build: rebuild dist from dev file"
git push origin main
node visualizer/build-visualizer.js
npm --prefix visualizer/visualizer-tests test
cp drainage-calculator/storm-drain-design-calculator.html ../gh-pages-deploy/index.html
cp visualizer/storm-drain-visualizer.html ../gh-pages-deploy/visualizer.html
git -C ../gh-pages-deploy add index.html visualizer.html
git -C ../gh-pages-deploy diff --cached --quiet || git -C ../gh-pages-deploy commit -m "Redeploy calculator and visualizer from main"
git -C ../gh-pages-deploy push origin gh-pages
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

Two options, both run against the persistent `../gh-pages-deploy` worktree so `main`'s working tree is never touched:

```bash
# Option A: revert the latest redeploy commit
git -C ../gh-pages-deploy revert <commit-sha>
git -C ../gh-pages-deploy push origin gh-pages
```

```bash
# Option B: check out a known-good prior file
git -C ../gh-pages-deploy checkout <known-good-commit> -- index.html
git -C ../gh-pages-deploy commit -m "Roll back gh-pages index.html to <known-good-commit>"
git -C ../gh-pages-deploy push origin gh-pages
```

`<commit-sha>` is the SHA of the redeploy commit to undo. `<known-good-commit>` is any prior `gh-pages` commit whose target file (`index.html` or `visualizer.html`) rendered correctly. For a single-file rollback, replace `index.html` in Option B with `visualizer.html` as needed.

## Never Hand-Edit `gh-pages`

`gh-pages`'s `index.html` and `visualizer.html` are build artifacts of `main`'s `drainage-calculator/storm-drain-design-calculator.html` and `visualizer/storm-drain-visualizer.html` respectively. Never edit them directly on `gh-pages` — any direct edit will be overwritten on the next redeploy and silently diverges the deployed site from `main`. To change what is deployed, edit the dev source on `main`, run the appropriate build script, then run the Redeploy procedure.

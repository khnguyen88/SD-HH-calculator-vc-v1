# Deployment Runbook

Operational runbook for the storm drain design calculator deployed to GitHub Pages. Covers how Pages is wired, the redeploy procedure, verification, and rollback. The `gh-pages` branch is a build artifact: its `index.html` is a byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from `main`. Never hand-edit `gh-pages` content — always re-copy from `main`.

## Live URL

https://khnguyen88.github.io/SD-HH-calculator-vc-v1/

## Repo

https://github.com/khnguyen88/SD-HH-calculator-vc-v1

## How Pages Is Wired

GitHub Pages serves from the `gh-pages` branch, root (`/`). The branch contains a single commit's worth of content:

- `index.html` — byte-identical copy of `drainage-calculator/storm-drain-design-calculator.html` from `main`.
- `README.md` — small file pointing back at `main` and explaining that `gh-pages` is an artifact branch.

No build step, no Actions workflow, no Jekyll. Pages serves the raw `index.html` at the site root.

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

Notes:
- `git checkout main -- drainage-calculator/storm-drain-design-calculator.html` stages main's version into `gh-pages`'s index/worktree without switching branches' file state beyond that path.
- `rm -rf drainage-calculator` removes the directory if a prior redeploy left it behind; harmless if absent.
- The commit on `gh-pages` should be the only change; do not mix unrelated edits.

## One-Time Pages Setup

GitHub UI: repo → **Settings** → **Pages** → **Source**: *Deploy from a branch* → **Branch**: `gh-pages`, folder `/ (root)`.

CLI equivalent (see Task 6 for the full script): use `gh api` to set the Pages source to the `gh-pages` branch at root. This is a one-time configuration; once set, every push to `gh-pages` triggers a Pages build and deployment.

## Verification

After `git push origin gh-pages`:

1. Wait for the GitHub Pages build. In the repo's **Actions** tab, look for **Pages build and deployment** to go green. Typical build time is under a minute.
2. `curl -s https://khnguyen88.github.io/SD-HH-calculator-vc-v1/ | head` should show the calculator's `<!DOCTYPE html>` markup.
3. A browser visit to the live URL should show the **Overview** tab of the calculator.

If the Actions build is red or the curl returns the old content, wait 30s and re-check (CDN cache). If still stale, see Rollback.

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

`<commit-sha>` is the SHA of the redeploy commit to undo. `<known-good-commit>` is any prior `gh-pages` commit whose `index.html` rendered correctly.

## Never Hand-Edit `gh-pages`

`gh-pages`'s `index.html` is a build artifact of `main`'s `drainage-calculator/storm-drain-design-calculator.html`. Never edit it directly on `gh-pages` — any direct edit will be overwritten on the next redeploy and silently diverges the deployed site from `main`. To change what is deployed, edit the source on `main`, merge, then run the Redeploy Procedure.

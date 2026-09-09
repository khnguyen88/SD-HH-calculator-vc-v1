# Spec Update, Documentation, and GitHub Pages Deployment — Design

Date: 2026-09-09
Status: Approved by user

## Context

The repo contains a single-file storm drain design calculator (`drainage-calculator/storm-drain-design-calculator.html`, ~618KB, SheetJS bundled inline) built from a phased build spec (`drainage-calculator/storm-drain-calculator-spec.md`). The app is complete and implements everything in the spec, plus one major feature — **NRCS TR-55 segmental Time of Concentration** — that the spec does not document. All project files are currently untracked; nothing has been pushed to the remote (`khnguyen88/SD-HH-calculator-vc-v1`).

## Goals

1. Update the spec to match the as-built app (add TR-55, fix drift).
2. Add user-facing support documents to `/docs`.
3. Update `CLAUDE.md` with real project context.
4. Deploy the calculator to GitHub Pages via a `gh-pages` branch, calculator as `index.html`.

## Design

### 1. Spec update — as-built, in place

Update `drainage-calculator/storm-drain-calculator-spec.md`, keeping its phased build-plan style and bug-history narrative:

- **Add a new TR-55 phase** documenting the as-built feature:
  - `tcMethod: "direct" | "tr55"` per Drainage Area row; direct entry remains the default/fallback.
  - Segment list per row: sheet / shallow concentrated / channel flow segments, in order.
  - TR-55 Table 3-1 sheet-flow Manning's n values; shallow-concentrated velocity lookup (paved/unpaved via `TR55_SHALLOW_CP`); channel segments via Manning's velocity, Tc = Σ travel times.
  - Interactive modal (`openTr55Modal`) with add/remove segments, computed Tc written back to the row.
- **Fix drift**: Phase 1's tab list predates the Outlet Structure and Formulas & Examples tabs; Kb section says "separate columns for Inlet / Manhole / Bend" while the as-built app seeds a single AASHTO bend-loss curve applied to all types (Flow Splitter uses Manhole column) — correct the spec to match reality.
- Keep Sections A (frontend architecture), B (Excel export/import), C (testing) intact, extended as needed for TR-55.

### 2. Support documents in `/docs`

- `user-guide.md` — per-tab usage walkthrough (8 tabs), Excel export/import, detail sheets, printing.
- `engineering-methodology.md` — governing equations (Rational, Manning's, friction loss, controlling-angle structure loss, flow splitter, circular-segment orifice geometry, orifice/pipe regimes, weir free/submerged with Villemonte, TR-55 Tc), assumptions and disclosed limitations (centroid-head overestimate; "pipe" device = large-orifice/short-culvert treatment, not HDS-5).
- `deployment-runbook.md` — expands the existing 2-line note: Pages serves from `gh-pages` branch; URL `https://khnguyen88.github.io/SD-HH-calculator-vc-v1/`; redeploy procedure (commit main, copy calculator to `index.html` on gh-pages, push).
- Existing `docs/deploying-to-github-pages.md` content is absorbed into the runbook (or kept and updated to point at it).
- Updated spec remains in `drainage-calculator/` next to the app, referenced from docs.

### 3. CLAUDE.md

Replace the placeholder with: project purpose (single-file offline storm drain design calculator), the non-negotiable single-file constraint, key file locations, and the deploy procedure.

### 4. Deployment

- **Commits on main, in sequence**: (1) spec update, (2) docs, (3) CLAUDE.md, then push main.
- **gh-pages branch**: single commit containing the calculator copied as `index.html` plus a minimal README. Push `gh-pages`.
- **Pages configuration**: site must be set to deploy from the `gh-pages` branch (root). If not yet configured, enable via `gh api` (PUT `/repos/khnguyen88/SD-HH-calculator-vc-v1/pages` with `source[branch]=gh-pages`) — with user's confirmation — or instruct the user to flip it in GitHub Settings → Pages.
- **Verification**: fetch the published URL after the deploy and confirm the calculator HTML is served.

## Constraints

- Single HTML file, no CDN, offline-capable — never broken by the deployment process (gh-pages copy is byte-identical to main's calculator, just renamed).
- No changes to the calculator itself in this effort — spec/docs/deploy only.
- User-approved decisions: deploy from gh-pages branch; calculator as index.html; docs = user guide + methodology + runbook; spec updated as-built in place; sequential commits on main + one deploy commit.
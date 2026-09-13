# Mobile Responsive Topbar — Design Spec

**Date:** 2026-09-13
**Goal:** On mobile (≤760px), replace the sidebar nav with a three-section topbar: [Project Title] [☰ Menu] [Import | Export].

---

## Scope

- **Mobile only (≤760px):** three-section topbar, sidebar hidden, hamburger dropdown nav.
- **Desktop (>760px): no change.** Sidebar, topbar-left, and topbar-right are untouched.

---

## Section 1 — Layout & CSS

### Desktop (>760px)
Unchanged. `.topbar-center` is `display:none`.

### Mobile (≤760px)

```
┌─────────────────────────────────────────────────┐
│  [Project Title input]  [☰ Menu]  [↑ Import] [↓ Export] │
├─────────────────────────────────────────────────┤
│  (mobile nav panel — hidden by default)         │
│  01 Overview                                    │
│  02 Rainfall & IDF                              │
│  ...                                            │
└─────────────────────────────────────────────────┘
```

**CSS additions at `@media (max-width:760px)`:**
- `.sidebar { display:none; }` — hides sidebar entirely
- `.topbar { gap:8px; padding:10px 14px; }` — tighter on mobile
- `.topbar-center { display:flex; align-items:center; }` — reveals hamburger slot
- `.topbar-left { flex:1 1 auto; }` — project title takes available space
- `.topbar-right { flex:0 0 auto; }` — right section stays right
- `.mobile-hidden { display:none !important; }` — hides Save, Tables, Detail, Saves buttons

**New CSS classes (always present, not breakpoint-specific):**
```css
.topbar-center {
  display: none;
  align-items: center;
  flex: 0 0 auto;
}

.mobile-nav-panel {
  display: none;
  flex-direction: column;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 8px;
  gap: 2px;
}
.mobile-nav-panel.open {
  display: flex;
}
```

The `.mobile-nav-panel` nav buttons use the same `.nav-btn` styles as the sidebar nav.

---

## Section 2 — HTML Changes

### 1. Add `topbar-center` inside `.topbar` (between `.topbar-left` and `.topbar-right`)

```html
<div class="topbar-center">
  <button class="btn btn-sm" id="hamburgerBtn" aria-label="Open navigation menu">&#9776; Menu</button>
</div>
```

### 2. Add `mobile-hidden` class to secondary action buttons

Applied directly in HTML to these elements in `.topbar-right`:
- `#saveCompBtn` → add class `mobile-hidden`
- `#printAllTablesBtn` → add class `mobile-hidden`
- `#printAllDetailBtn` → add class `mobile-hidden`
- `.saves-wrap` div → add class `mobile-hidden`

`#importBtn` and `#exportBtn` remain visible on mobile (no class added).

### 3. Add `.mobile-nav-panel` immediately after `.topbar`, before `.content`

```html
<div class="mobile-nav-panel" id="mobileNavPanel">
  <nav id="mobileNav"></nav>
</div>
```

---

## Section 3 — JS Changes

### 1. `closeMobileNav()` utility

Add near `renderNav()` (in the State / Persistence or Render — Overview section):

```js
function closeMobileNav() {
  document.getElementById("mobileNavPanel").classList.remove("open");
}
```

### 2. Update `renderNav()` to also populate `#mobileNav`

After the existing loop that populates `#nav`, add a second loop for `#mobileNav`. Mobile nav buttons call `closeMobileNav()` before `renderAll()`:

```js
const mobileNav = document.getElementById("mobileNav");
mobileNav.innerHTML = "";
tabs.forEach((t, i) => {
  const btn = el("button", {
    class: "nav-btn" + (state.active === t.id ? " active" : ""),
    onclick: () => { state.active = t.id; closeMobileNav(); renderAll(); }
  }, [ el("span", {class:"nav-num"}, String(i+1).padStart(2,"0")), t.label ]);
  mobileNav.appendChild(btn);
});
```

### 3. Wire hamburger and outside-click in `init()`

Add alongside other button event-listener registrations in `init()`:

```js
document.getElementById("hamburgerBtn").addEventListener("click", (e) => {
  e.stopPropagation();
  document.getElementById("mobileNavPanel").classList.toggle("open");
});
document.addEventListener("click", () => closeMobileNav());
```

---

## Constraints

- No changes to desktop layout, sidebar, or existing topbar-left/right structure.
- No new design tokens — uses existing `var(--panel)`, `var(--border)`, `.btn`, `.nav-btn` styles.
- No `withFocusPreserved` needed — pure UI show/hide, no state mutation.
- `#importFile` (hidden file input) stays in `.topbar-right` — not affected.

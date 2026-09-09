# Storm Drain Design Calculator — User Guide

A browser-based tool for storm drain conveyance design: Rational Method peak flows, NRCS TR-55 time of concentration, Manning's pipe sizing, hydraulic grade line (HGL) with structure losses, flow splitters, and stage-discharge rating curves for BMP/SWM/ESD outlet structures. The entire application is a **single HTML file** that runs completely offline — no install, no server, no account. Nothing you type leaves your computer.

- **Live version:** <https://khnguyen88.github.io/SD-HH-calculator-vc-v1/>
- **Local copy:** `drainage-calculator/storm-drain-design-calculator.html` — just double-click the file to open it in your browser, with no internet connection.

The tool models your network as three linked pieces: **Drainage Areas** feed **Junction Structures**, **Pipes** connect one structure to another, and the HGL is walked upstream from the outfall automatically. The Outlet Structure tab builds rating curves for pond/BMP outlets, separate from the conveyance network.

---

## Quick start

1. **Open the tool** (URL above, or double-click the local HTML file). It loads with a small seeded example project — a two-inlet network, a flow splitter, and two outlet facilities — so you can see how everything links. Click the ✕ at the end of any row to delete it and start clean, or just overtype the example data.
2. **Work the tabs left to right:** define catchments on **Drainage Area**, structures on **Junction Structures**, then connect them on **Pipe Sizing**. Add outlet facilities on **Outlet Structure** as needed.
3. **Check any computed value** with its **⤢ Detail** button — a full calculation sheet with the formula, the substituted numbers, and the result.
4. **Save your work** with **↓ Export to Excel** (top-right). Nothing is saved until you export — there is no autosave, and refreshing the page resets to the seeded example. **↑ Import from Excel** reloads a previously exported (or hand-edited) file.

---

## Tab 1 — Overview

A one-screen map of the workflow and the tool's assumptions. Skim it once before your first project; come back to the **Assumptions & notes** section before relying on results for a submittal (see [Known limitations](#known-limitations--assumptions) below, which mirror it).

## Tab 2 — Drainage Area (Q = C·i·A)

One row per catchment. The computed **Q** is the Rational Method peak flow:

> **Q = Cf × C × i × A** — runoff coefficient C, design rainfall intensity i (in/hr), tributary area A (acres), frequency correction Cf (1.0 for storms ≤ 25-yr; the column defaults to 1.0).

**To add a catchment:** click **+ Add row**, type an ID (this is what other tabs reference), description, area, C, and i. Q updates as you type.

**Time of concentration (Tc)** — two ways:

- **Direct entry (default):** type Tc in minutes into the field. Tc is informational for the peak-flow calc (you supply the design intensity yourself), so the tool takes whatever you enter.
- **TR-55 segments:** click **Use TR-55 →** to open the TR-55 worksheet modal. Tc becomes read-only and is computed as the sum of travel times across segments. Add segments with **+ Add Sheet flow**, **+ Add Shallow concentrated flow**, or **+ Add Channel / pipe flow**, in any order and any count (the real TR-55 Worksheet 3 is an arbitrary AB, BC, CD… chain — nothing forces "one of each"). Reorder with ↑ / ↓, delete with ✕.

  - *Sheet flow:* Manning's n (the **Reference…** dropdown fills typical TR-55 Table 3-1 values — dense grass 0.24, woods 0.80, etc.), flow length L, land slope, and 2-yr 24-hr rainfall P2. Lengths over 100 ft draw a warning — modern guidance caps sheet flow at 100 ft (the 1986 worksheet allowed 300 ft); check what your agency expects.
  - *Shallow concentrated flow:* length, watercourse slope, and a surface pick (paved, unpaved/grassed waterway, bare, cultivated, prairie, minimum-tillage, forest) that sets the velocity coefficient.
  - *Channel / pipe flow:* length, slope, Manning's n (reference dropdown of typical values — verify against your actual channel), cross-sectional flow area, and wetted perimeter.

  The modal shows a running total (**Tc = Σ Tt**) in hours and minutes, plus per-segment velocity and hydraulic radius. Two sanity warnings appear if you describe an unusual flow path (more than one sheet segment, or sheet flow appearing after flow has already concentrated) — they're advisory; the computation still runs. To go back to typing Tc directly, click **⇠ Direct entry** (or, inside the modal, "Switch to direct entry") — the computed value becomes the editable starting point.

**To use this catchment in the network:** pick its ID in a structure's **Drainage Area** dropdown on the Junction Structures tab. That structure's Captured Q then equals this row's Q.

## Tab 3 — Junction Structures

One row per physical structure — inlets, manholes, bends, junctions, diversion structures, and the outfall(s). Types: **Inlet, Manhole, Bend, Junction, Flow Splitter, Outfall**.

**To set up the network skeleton:**

1. **+ Add row** per structure and give each a unique **Structure ID** — pipes reference structures by this ID.
2. **Link a Drainage Area** (dropdown) if the structure captures runoff locally. Captured Q = that row's Rational Q.
3. **Set elevations at the downstream end.** The outfall (or any structure with a known water surface, e.g. a connection to an existing system or a SWM pond) needs a fixed elevation: check the **Fixed?** box ("force fixed elevation") and type it into **Fixed/Start Elev**. Every other structure's elevation is then computed automatically as *(downstream structure's HGL) + Hf + Hb*, chaining all the way to the outfall through each structure's outgoing pipe.
4. Enter **Crown** and **Rim/Grate** elevations to enable the clearance checks.

**What's computed for you:**

- **Total Flow** = Captured Q + Σ(flow of every pipe whose *To* structure is this row). The tool finds those inflow pipes automatically from the Pipe Sizing tab — you never re-enter flows.
- **Hf** — friction loss along the outgoing pipe at its actual design flow.
- **Kb / Hb** — structure loss. With no piped inflow, Kb is evaluated at 0° (nominal entrance); with one inflow pipe, Kb is taken at that pipe's angle; with two inflow pipes, the **controlling-angle method** applies — the angle belonging to the *smaller* computed loss governs. Kb comes from the editable table on the Kb Coefficients tab (column depends on structure type).
- **Upstream HGL** — the structure's water-surface elevation; checked against **Crown + 1.0 ft** and **Rim − 1.0 ft** (badges: **OK** / **EXCEEDS**).

**Flow Splitter** — for a diversion manhole or prefab structure (typically just downstream of an outlet) that divides its Total Flow between two outgoing pipes. The **Split config** cell offers:

- **Cap.** (capacity-limited): Primary Q = MIN(Total Flow, Capacity); Secondary = the remainder. Type the capacity (cfs).
- **Ratio**: Primary Q = Total Flow × Ratio (0–1); Secondary = the remainder.

A splitter needs exactly one **Primary** and one **Secondary** outgoing pipe — assign each pipe's **Role** on the Pipe Sizing tab. The splitter's own friction loss uses only the Primary pipe's flow; its structure loss still uses the full Total Flow.

**Warnings** appear as a ⚠ next to the inflow count — open the row's **⤢ Detail** sheet to read them (more than one outgoing pipe on a non-splitter, missing Primary/Secondary at a splitter, circular references, more than two inflow pipes, incomplete outgoing-pipe geometry).

## Tab 4 — Pipe Sizing

Every pipe connects a **From** structure to a **To** structure. **Design Q is pulled automatically** — it's the From structure's Total Flow (or its Primary/Secondary share when the From structure is a Flow Splitter) — so you never type a flow here.

**To size a pipe:**

1. **+ Add row**, pick the From and To structures.
2. Enter the **Angle** — the deflection this pipe makes *entering the To structure* (this drives the structure-loss calculation there), the **Shape** and **Size**, **n** (Manning's roughness), **Slope** (ft/ft), and **Length** (ft).
3. Read **Qfull** (full-flow capacity by Manning's equation) against **Design Q**. The **Status** badge shows **PASS** when Qfull ≥ Design Q. Adjust size or slope until it passes.

**Sizes:**

- **Circular:** diameter in inches (e.g. `24`).
- **Elliptical:** enter **SPAN x RISE** in inches (e.g. `38x24`). The tool matches the nearest Table 4-6 entry and uses that entry's area and equivalent circular diameter (for hydraulic radius) in Manning's equation.

**Role** (Primary / Secondary) is only meaningful on pipes leaving a Flow Splitter — it selects which share of the splitter's Total Flow this pipe carries.

## Tab 5 — Outlet Structure

A stage-discharge rating curve builder for BMP/SWM/ESD facilities (pond risers, bioretention outlets). This is separate from the conveyance network: each facility has its own devices, stage range, precision, and tailwater — facilities never mix.

**To build a rating curve:**

1. Click **+ Add outlet structure**, give it a **Label** and description. Switch between facilities with the dropdown; delete the active one with **Delete this outlet structure**.
2. **Add devices** with **+ Add device** — as many as the facility has:
   - **Orifice** — invert elevation and diameter (in or ft; toggle the unit). Used for low-flow openings, underdrains.
   - **Weir** — crest elevation, length (ft or in), **Rect.** or **V-notch** (with notch angle), and weir coefficient (C ≈ 3.1 rectangular, ≈ 2.5 V-notch).
   - **Pipe** — invert and diameter, treated as a *large orifice / short culvert barrel* (appropriate for a pond outlet barrel), not a full inlet/outlet-control culvert analysis.

   All devices share one headwater; their flows add at every stage — that's the composite curve.
3. **Set the stage range & precision:** Start and End elevation, a **Coarse increment** for the whole range, plus a **fine increment** and **fine band ±** — fine-spaced points are inserted automatically around every device's invert, top-of-opening, or crest (and around the tailwater elevation), which is where the governing equation switches and the curve bends the most.
4. **Precision mode:**
   - **Uniform** — every device uses the facility defaults above. Simplest.
   - **Individual** — each device row gains a **Custom** checkbox and its own increment/band fields. Check **Custom** to tighten resolution around a small, sensitive low-flow orifice — or set its band to **0** to skip refinement entirely (e.g. a rarely-active emergency spillway).
5. **Tailwater (advanced)** — if the facility discharges into water that can submerge its devices:
   - **None — free discharge** (default);
   - **Fixed elevation** — a constant downstream water surface;
   - **Linked to a Junction Structure** — resolves live to that structure's computed **Upstream HGL** from the conveyance network (a single resolved elevation, since the design flow is fixed). The resolved value is displayed under the selector.

The **rating curve** table below shows, at every stage: the tailwater, each device's flow regime and Q (plus the full geometry — half-angle α, wetted area, centroid, head to centroid — if "Show full geometry detail" is checked), and the **Total Q** across all devices. Every stage row has a **⤢ Detail** sheet with each device's complete calculation. If your range/increment combination generates more than 2,000 rows, the table is thinned for display with a warning — widen the increments or narrow the range.

## Tab 6 — Formulas & Examples

Every governing equation used by the tool — Rational Method, Manning's, friction loss, the controlling-angle structure loss, flow splitter, circular-segment geometry, orifice/pipe regimes, and both weir regimes — each with a **worked numeric example computed live from your current project**. The examples update automatically as you edit the underlying data, so the reference can never drift out of sync with what the calculators actually do. (TR-55 equations are documented on each row's own TR-55 sheet instead.) Print it with **🖨 Print this reference**.

## Tab 7 — Table 4-6 Reference

A static, read-only equivalency table: circular pipe diameter/area alongside the elliptical span × rise of approximately the same cross-sectional area (15″ through 144″). It's reference data for picking elliptical sizes — the Pipe Sizing tab uses it automatically when you enter an elliptical size. It is not editable and has no Detail buttons.

## Tab 8 — Kb Coefficients

The structure-loss coefficient table: **Angle (°)** vs. **Kb** for the **Inlet**, **Manhole**, and **Bend** columns, linearly interpolated between rows and clamped at the endpoints (5° through 90° as seeded).

**Important:** all three columns are seeded with the *same* published AASHTO bend-loss curve (0.06 at 5° up to 0.70 at 90°). That default is deliberately conservative — it does not pretend to know your agency's inlet-vs-manhole-vs-bend differences. **Edit the cells to match your governing Appendix B chart before relying on structure losses for a submittal.** Each structure type reads its own column: Inlet → *Inlet*, Manhole → *Manhole*, Bend → *Bend*, Junction → *Bend*, Flow Splitter → *Manhole*, Outfall → none (no structure loss).

**+ Add row** inserts points; **Reset to default** restores the seeded curve.

---

## Detail calc sheets & printing

Every computed row — a drainage area's Q, a structure's Total Flow/Hb/HGL, a pipe's capacity check, and every rating-curve stage — has a **⤢ Detail** button. It opens a full calculation sheet: inputs, the governing formula, the formula with your numbers substituted in, and the result, plus any warnings. (Static reference tables — Table 4-6, Kb — don't get Detail buttons; they're inputs, not outputs.)

From the detail window:

- **🖨 Print this page** — prints just that one sheet.
- **🖨 Print all** — compiles every sheet in the project (all drainage areas, structures, pipes, and *every* rating-curve stage of every facility) into one print package, one sheet per page.

**Caution:** "Print all" includes one page per rating-curve stage row. With fine stage increments across multiple facilities, that can genuinely exceed 100 pages — narrow the stage range or widen the increments first if you want a manageable package.

Calc sheets print as light "paper" regardless of the app's dark theme. Close the window with the ✕ button, the Escape key, or a click outside it.

## Saving your work — Excel export & import

There is no autosave and no cloud storage; the **.xlsx export is your project file**.

**Export — ↓ Export to Excel** (top right): writes every table to a single `.xlsx` named after the project name in the top bar. Sheets: Overview (notes + project name), **Drainage Area**, **TR-55 Segments** (each segment as a row, tagged by drainage area), **Junction Structure**, **Pipe Sizing**, **Outlet Structures** (the facility list), **Outlet Devices** (all facilities' devices, tagged by facility), one **Rating — *facility*** sheet per outlet structure, plus **Table 4-6 Reference** and **Kb Coefficients**.

**What's live vs. what's a value:**

- *Live formulas that recalculate in Excel as you edit inputs:* Drainage Q, Captured Q, Q-from-pipes, Total Flow, Design Q (including splitter Primary/Secondary shares), friction loss Hf, Vout, Hb, the chained Upstream HGL, each rating row's Total Q, and the tailwater column.
- *Static values computed by the app (edit them to override):* the **Kb** cell on each structure row (the controlling-angle result — too branchy for a spreadsheet formula), each device's per-stage Q and regime on the Rating sheets (exact segment geometry and Villemonte submergence math), and elliptical pipe areas.

**Hand-editing and re-importing:** you can edit the exported file in Excel and bring it back with **↑ Import from Excel**. On import the app reads only the *input* columns (IDs, descriptions, geometry, coefficients, settings) and recomputes everything else live — hand-edited computed columns affect the spreadsheet only, not the app. Two cautions:

- Cross-sheet links in the workbook key on the user-facing labels — a pipe's From/To matches a **Structure ID**, a device's facility matches its **Label**, a structure's drainage area matches the drainage row's **ID**. Keep those unique and consistent when hand-editing, or links will silently drop.
- Import replaces each table with the version found in the file, so import a file that contains everything you care about.

---

## Known limitations & assumptions

Read before relying on results for submittal:

1. **Structure elevation** is either fixed (the outfall, or any structure with "Fixed?" checked — useful for a known tailwater or SWM pond connection) or computed as the downstream structure's elevation + friction loss (Hf) + this structure's own loss (Hb), chaining automatically to the outfall through each structure's Primary path.
2. **Velocity for structure loss (Vout)** uses Total Flow divided by the *full* pipe area of the outgoing pipe — i.e., it assumes the pipe runs at or near full depth at the structure.
3. **Kb coefficients** default to a single published AASHTO bend-loss curve applied to Inlet/Manhole/Bend alike (Flow Splitters use the Manhole curve). Edit the Kb Coefficients tab to match your governing Appendix B chart before relying on results for submittal.
4. **One Primary outgoing pipe per structure** is assumed (the standard converging storm-drain tree). A structure can have any number of incoming pipes, but the controlling-angle method only covers **up to 2** — rows with more are flagged and Hb is not computed. A Flow Splitter is the one exception, with a Primary + Secondary pair.
5. **Outlet Structure "Pipe" devices** are treated as a large orifice / short culvert barrel (appropriate for a pond outlet), not a full inlet/outlet-control culvert analysis per HDS-5.
6. **Partial-flow orifice/pipe discharge** uses the exact wetted area and the head to that area's own centroid — exact at the empty and full boundaries, but a small (typically low single-digit percent) overestimate in between, since √h is concave and the average of √h over the area is always ≤ √(average h). This is standard industry practice (it matches HydroCAD/PondPack-style tools), not unique to this tool. Each device's Fine incr./band override lets you tighten resolution exactly where it matters most — typically a small low-flow orifice — without changing the whole facility's precision.
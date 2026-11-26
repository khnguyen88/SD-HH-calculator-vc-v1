# Apply R1-R5 repairs from the Spec-1 design to the WIP xlsx.
#
# Usage: python repair.py <backup.xlsx> <output.xlsx>
#
# Reads <backup.xlsx> (the pre-repair snapshot), applies every repair
# deterministically, writes <output.xlsx>. Re-running on the same backup
# reproduces the output.
#
# Design reference: docs/superpowers/specs/2026-11-25-template-wip-audit-design.md
# Section 5.2.
import sys

import openpyxl


# These are literal defined-name strings. "\0", "\c", etc. are the two
# character names \0, \c, ... (backslash + letter/digit), NOT escape
# sequences. In Python source we double the backslash to keep them literal.
ORPHAN_NAMES = (
    ["\\0", "\\c", "\\e", "\\p", "\\r"]
    + [f"_DUR{i}" for i in range(1, 19)]
    + ["_INT1", "_INT2"]
)
DUPLICATE_NAME_TO_REMOVE = "SelectCounty"  # keep Select_County


def remove_defined_names(wb, names):
    # R3 + R4: remove orphan #REF! names and the SelectCounty duplicate.
    # Returns the sorted list of names actually removed, so callers (and
    # tests) can detect silent drift - e.g. if openpyxl surfaces a name
    # with different escaping than the orphan list expects.
    removed = []
    for name in list(wb.defined_names):
        if name in names:
            del wb.defined_names[name]
            removed.append(name)
    return sorted(removed)


def rebuild_hgl_25year(wb):
    # R1: rebuild ONLY the broken OFFSET-pattern columns on HGL(25YEAR):
    # A, B, C, D, E, F, H, L. Every other column on the sheet is intact
    # and must be left untouched:
    #   G, I, J, K, M = HGL chain (G propagates MAX; I computes 25-year
    #     friction slope from column U (25-year Q) and V (Manning n); J =
    #     Hf = H*I; K = upstream HGL floored at U/S crown; M = HGL in
    #     From Str = K + Hb).
    #   O = 10-year tailwater pull from HGL!Q.
    #   Q, R, S, T, U, V = 25-year auxiliary columns (pipe diameter from
    #     SDC N, A*C total from SDC J, pipe Tc from SDC K, 25-year
    #     intensity from DATA, 25-year Q = T*R, Manning n from SDC S).
    # The sheet already implements correct 25-year flow and friction
    # slope on-sheet, so R1 does not need to substitute a source-sheet
    # Y column - the existing I-column formula is correct as-is.
    ws = wb["HGL(25YEAR)"]
    _write_hgl25_broken_columns(ws, start=7, end=91)


def fix_inlet_spacing_ak(wb):
    # R2: resolve the AK #REF! formulas. Default: clear AK rows 11-96.
    # If the per-tab analysis in docs/template-analysis/04-inlet-spacing.md
    # recorded that AK is referenced by a downstream sheet, override this
    # function at that point and rebuild the EXACT(...) argument against
    # the recovered target cell.
    ws = wb["INLET SPACING"]
    for row in range(11, 97):
        cell = ws.cell(row=row, column=37)  # AK = column 37
        if isinstance(cell.value, str) and "#REF!" in cell.value:
            cell.value = None


def modernize_k_column_tc_formula(wb):
    # Rewrite STORM DRAIN COMPS!K10:K98 with an XLOOKUP that explicitly
    # excludes the current row from the lookup array, sidestepping Excel's
    # circular-reference detector.
    #
    # Semantics:
    #   K{r} =
    #     IF E{r} is blank -> blank
    #     ELSE MAX(E{r}, XLOOKUP(A{r}, B-array-with-self-row-blanked,
    #                            K{r'}+X{r'}, if-no-match=E{r}))
    #
    # Trade-off: XLOOKUP returns the FIRST matching row only. For junction
    # structures with 2+ inflow pipes, that silently picks one inflow and
    # ignores the others. If the un-picked inflow has a longer upstream Tc,
    # the result is a conservatively-too-low Tc (i.e. too-high design i and
    # Q). The user accepted this trade-off because (a) the pre-repair
    # FILTER+MAX alternative triggered Excel's circular-reference check and
    # broke downstream HGL formulas that depend on K via L-M-Y chain, and
    # (b) their networks are predominantly tree-structured. The disclosure
    # on EQUATIONS + INSTRUCTIONS documents the limitation.
    #
    # Idempotent: detects the "XLOOKUP(" marker in the K formula and skips
    # any already-modernized cell.
    ws = wb["STORM DRAIN COMPS"]
    marker = "XLOOKUP("
    for r in range(10, 99):
        cell = ws.cell(row=r, column=11)  # K = col 11
        existing = cell.value
        text = getattr(existing, "text", None) or (
            existing if isinstance(existing, str) else None
        )
        if text is None or not text.startswith("="):
            continue  # don't invent a formula where none existed
        if marker in text:
            continue  # already modernized
        cell.value = (
            f'=IF(E{r}="","",'
            f'MAX(XLOOKUP(A{r},'
            f'IF(ROW($B$10:$B$98)=ROW(),"",$B$10:$B$98),'
            f'$K$10:$K$98+$X$10:$X$98,E{r}),E{r}))'
        )


def update_equations_instructions(wb):
    # R5: append a note explaining the acyclic-pipe-network requirement.
    # Also append a Tc-aggregation note disclosing the XLOOKUP single-match
    # limitation (set by modernize_k_column_tc_formula).
    # Idempotent - if the notes are already present, do nothing.
    ws = wb["EQUATIONS + INSTRUCTIONS"]
    existing_text = "\n".join(
        str(cell.value) for row in ws.iter_rows() for cell in row
        if isinstance(cell.value, str)
    )
    need_acyclic = "acyclic pipe network" not in existing_text
    need_k_note = "K-column Tc aggregation" not in existing_text
    if not need_acyclic and not need_k_note:
        return
    note_row = ws.max_row + 2
    if need_acyclic:
        ws[f"A{note_row}"] = (
            "NOTE: From/To columns must describe an acyclic pipe network. "
            "Iterative calculation is intentionally OFF - a loop in the data "
            "will produce #VALUE!, not an iteratively settled answer. Check "
            "your From/To entries if you see unexpected errors on HGL or "
            "structure-loss columns."
        )
        note_row += 2
    if need_k_note:
        ws[f"A{note_row}"] = (
            "NOTE: K-column Tc aggregation uses XLOOKUP, which returns the "
            "FIRST matching upstream row. For junction structures with 2+ "
            "inflow pipes, the design Tc may understate the controlling "
            "inflow's Tc. If a junction has multiple inflows with materially "
            "different Tc values, manually verify K is set to the MAX of the "
            "inflows' (K+X) values."
        )


def _write_hgl25_broken_columns(ws, start, end):
    # Overwrites only the 8 broken columns on HGL(25YEAR) with the
    # XLOOKUP-pattern formulas used by the clean 10-year HGL sheet.
    # Broken columns: A, B (From/To), C (U/S invert), D (U/S crown), E
    # (D/S invert), F (D/S crown), H (pipe length), L (structure loss).
    # Every other column on the sheet is left untouched - the intact
    # 25-year formulas on G, I, J, K, M, O, Q-V remain in place.
    sdc = "'STORM DRAIN COMPS'"
    q = '""'  # empty-string literal inside a formula
    for r in range(start, end + 1):
        src = 10 + (r - start)  # STORM DRAIN COMPS data starts at row 10
        ws[f"A{r}"] = f"=IF({sdc}!A{src}={q},{q},{sdc}!A{src})"
        ws[f"B{r}"] = f"=IF({sdc}!B{src}={q},{q},{sdc}!B{src})"
        ws[f"C{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$P:$P))"
        )
        ws[f"D{r}"] = f"=IF(C{r}={q},{q},({sdc}!N{src}/12)+C{r})"
        ws[f"E{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$Q:$Q))"
        )
        ws[f"F{r}"] = f"=IF(E{r}={q},{q},{sdc}!N{src}/12+E{r})"
        ws[f"H{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$O:$O))"
        )
        ws[f"L{r}"] = (
            f"=IF(OR(A{r}={q},B{r}={q}),{q},"
            f"XLOOKUP(1,({sdc}!$A:$A=$A{r})*({sdc}!$B:$B=$B{r}),{sdc}!$AF:$AF))"
        )


def main(src, dst):
    wb = openpyxl.load_workbook(src, data_only=False)
    rebuild_hgl_25year(wb)
    fix_inlet_spacing_ak(wb)
    expected_removals = set(ORPHAN_NAMES) | {DUPLICATE_NAME_TO_REMOVE}
    removed = remove_defined_names(wb, expected_removals)
    skipped = sorted(expected_removals - set(removed))
    if skipped:
        # Idempotent re-runs legitimately skip already-removed names; only
        # warn so the first-run output still exits 0.
        print(f"warning: {len(skipped)} expected defined-name removals "
              f"were absent from the workbook (likely already removed): "
              f"{skipped[:5]}{'...' if len(skipped) > 5 else ''}")
    update_equations_instructions(wb)
    modernize_k_column_tc_formula(wb)
    wb.save(dst)
    print(f"wrote {dst}: removed {len(removed)} defined names")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: repair.py <backup.xlsx> <output.xlsx>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])

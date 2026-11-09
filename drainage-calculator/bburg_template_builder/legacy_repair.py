"""Repair the HGL chain in docs/bburg-p-c-legacy.xlsx (' 10 Yr MoCo HGL').

The original sheet never accumulated the grade line: column Z ("Col. C — D/S
HGL + Hb") was empty in every row, so no HGL crossed a structure boundary and
there was no tailwater seed at CULVERT. The crown floors were also wired to
the wrong pipe ends (X/Y held the u/s invert/crown but fed the d/s-side
columns), friction was added on top of the u/s crown instead of flooring the
accumulated chain, and the invert lookups were hand-tuned VLOOKUP ranges keyed
on the To structure — fragile wherever several pipes share a To (I-2, MH-1,
CULVERT each appear 2-3x in the capacity sheet).

The repair rewires each data row to the golden-tested template rules
(reference_calcs.hgl_walk_step, "Legacy both-end crown floor"):

    Z  (Col. C) = MAX(MAXIFS(HGL_up of reaches leaving the To structure),
                      tailwater when the To structure is terminal)
    AA (Col. D) = MAX(Z, d/s crown)          -- d/s crown floor
    AD (Col. G) = AA + Hf                    -- pipe friction (Sf at design Q * L)
    AE (Col. H) = MAX(AD, u/s crown)         -- u/s crown floor
    AF (Col. I) = AE                         -- HGL @ u/s structure, feeds the rim check

Inverts become direct capacity references (X = cap!Q d/s, AB = cap!P u/s),
matching the sheet's own idiom for every other column, and the four pipes the
original sheet skipped (MH-3->MH-2, MH-2->I-2, EX-I-2->MH-1, I-6->I-5) are
added so every branch chains. Hb (cols U/V/W) stays computed-but-informational,
exactly like the template — structure losses belong to the EGL walk there.

Writes go through Excel COM, not openpyxl: openpyxl's repackaging makes Excel
refuse this workbook (see docs/superpowers/specs/2026-11-07-legacy-ref-repair-handoff.md,
pitfall 1), and COM's CalculateFullRebuild + Save regenerates every cached
formula result. COM takes plain function names (MAXIFS), no _xlfn prefix.

Row 21 (I-7 -> CULVERT, the 44.5x33 elliptical) keeps its deliberate
approximations: 33-in rise for crowns, 44.5-in equal-area diameter for
friction, and Kb table column 3.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

SHEET = " 10 Yr MoCo HGL"
CAP = "10 Yr Pipe Capacity"
FIRST_ROW = 12
LAST_ROW = 37

# HGL-sheet data row -> '10 Yr Pipe Capacity' data row.
DATA_ROWS = {
    12: 14,  # I-3     -> MH-3
    13: 15,  # MH-3    -> MH-2   (added)
    14: 17,  # I-1     -> I-2
    15: 18,  # I-2     -> MH-1
    16: 16,  # MH-2    -> I-2    (added)
    17: 20,  # MH-1    -> EX-I-1
    18: 21,  # EX-I-1  -> CULVERT
    19: 19,  # EX-I-2  -> MH-1   (added)
    21: 23,  # I-7     -> CULVERT (44.5x33 elliptical)
    22: 25,  # I-6     -> I-5    (added)
    26: 26,  # I-5     -> I-4
    27: 27,  # I-4     -> CULVERT
}
NEW_ROWS = (13, 16, 19, 22)
STYLE_SOURCE_ROW = 12
STYLE_LAST_COL = "AI"

# Bend angle at the u/s (From) structure, per HGL row. Original inputs kept.
ANGLES = {12: 0, 13: 0, 14: 0, 15: 9, 16: 0, 17: 0, 18: 0, 19: 0,
          21: 0, 22: 0, 26: 0, 27: 4}

# Elliptical pipe (row 21): crowns use the rise, friction the equal-area dia,
# area comes from Pipe Properties, and the MoCo Kb table column differs.
RISE_IN_OVERRIDE = {21: 33.0}
EQ_DIA_IN_OVERRIDE = {21: 44.5}
KB_COL_OVERRIDE = {21: 3}

TAILWATER_LABEL = "D/S TAILWATER @ CULVERT (ft):"
TAILWATER_VALUE = 66.87
REPAIR_NOTE = (
    "Repair 2026-11-09: chain rewired to the bburg template rules - "
    "Col. C = MAX(MAXIFS(Col. H of reaches leaving the To structure), T/W when terminal); "
    "Hb (cols U-W) is tracked for the EGL walk, not added to the HGL."
)


def _row_formulas(row: int, cap: int) -> dict[str, str | int]:
    """All values/formulas for one HGL data row, keyed by column letter."""
    rise = RISE_IN_OVERRIDE.get(row)
    rise_q = f"={rise:g}/12" if rise else f"=G{row}/12"
    dia = EQ_DIA_IN_OVERRIDE.get(row)
    dia_ft = f"({dia:g}/12)" if dia else f"(G{row}/12)"
    kb_col = KB_COL_OVERRIDE.get(row, 2)
    hgl_up_range = f"$AE${FIRST_ROW}:$AE${LAST_ROW}"
    from_range = f"$C${FIRST_ROW}:$C${LAST_ROW}"
    return {
        "C": f"='{CAP}'!A{cap}",
        "D": f"='{CAP}'!B{cap}",
        "E": f"='{CAP}'!L{cap}",
        "F": f"='{CAP}'!X{cap}",
        "G": f"='{CAP}'!M{cap}",
        "H": "='Pipe Properties'!B15" if row in RISE_IN_OVERRIDE
             else f"=PI()*(G{row}/12)^2/(4)",
        "I": "=$E$6",
        "J": f"=VLOOKUP(G{row},'Pipe Properties'!$A$2:$D$13,4,0)",
        "K": f"='{CAP}'!T{cap}",
        "L": f"=((E{row}*I{row})/(0.463*{dia_ft}^2.67))^2",
        "M": f"=((F{row}*I{row})/(0.463*{dia_ft}^2.67))^2",
        "N": f"='{CAP}'!U{cap}",
        "O": f"='{CAP}'!V{cap}",
        "P": f"='{CAP}'!S{cap}",
        "Q": rise_q,
        "R": f"=P{row}*L{row}",
        "S": f"=Q{row}*M{row}",
        "T": ANGLES[row],
        "U": f"=VLOOKUP(T{row},'Kb Values MoCo'!$A$2:$D$92,{kb_col},FALSE)",
        "V": f"=(U{row}*N{row}*N{row})/64.4",
        "W": f"=(U{row}*O{row}*O{row})/64.4",
        # Inverts: X = d/s (cap Q), AB = u/s (cap P) - direct refs, no VLOOKUP.
        "X": f"='{CAP}'!Q{cap}",
        "Y": f"=X{row}+Q{row}",
        # Col. C: accumulated HGL at the To structure - junction max over the
        # reaches leaving it, tailwater seed when nothing does (the outfall).
        "Z": (f"=MAX(MAXIFS({hgl_up_range},{from_range},D{row}),"
              f"IF(COUNTIF({from_range},D{row})=0,$E$4,0))"),
        "AA": f"=MAX(Z{row},Y{row})",
        "AB": f"='{CAP}'!P{cap}",
        "AC": f"=AB{row}+Q{row}",
        "AD": f"=AA{row}+R{row}",
        "AE": f"=MAX(AD{row},AC{row})",
        "AF": f"=AE{row}",
        "AG": f"='{CAP}'!R{cap}",
        "AH": f"=AG{row}-AF{row}",
        "AI": '=IF(AH{r}>0, "Ok!", "Check!")'.format(r=row),
    }


def repair_workbook(path: Path | str) -> None:
    """Rewrite the ' 10 Yr MoCo HGL' chain in place via Excel COM (idempotent)."""
    import pythoncom
    import win32com.client

    path = Path(path).resolve()
    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    try:
        wb = app.Workbooks.Open(str(path))
        ws = wb.Sheets(SHEET)

        # Tailwater input cell (row 4 was empty in the original).
        ws.Range("B4").Value = TAILWATER_LABEL
        ws.Range("B4").Font.Bold = True
        ws.Range("E4").Value = TAILWATER_VALUE

        for row, cap in DATA_ROWS.items():
            for col, value in _row_formulas(row, cap).items():
                ws.Range(f"{col}{row}").Value = value
            if row in NEW_ROWS:
                src = ws.Range(
                    f"C{STYLE_SOURCE_ROW}:{STYLE_LAST_COL}{STYLE_SOURCE_ROW}")
                src.Copy()
                ws.Range(f"C{row}:{STYLE_LAST_COL}{row}").PasteSpecial(-4122)  # xlPasteFormats
                ws.Rows(f"{row}:{row}").RowHeight = \
                    ws.Rows(f"{STYLE_SOURCE_ROW}:{STYLE_SOURCE_ROW}").RowHeight
        app.CutCopyMode = False

        # Document the rewired mechanics next to the original legend.
        ws.Range("C64").Value = REPAIR_NOTE

        app.CalculateFullRebuild()
        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        app.Quit()
        pythoncom.CoUninitialize()


def evaluate_chain(path: Path | str) -> dict[tuple[str, str], float]:
    """Mirror of the repaired formulas, evaluated from cached capacity values.

    Used to verify the workbook's own data reproduces the golden HGL walk
    without needing Excel.
    """
    wb = load_workbook(path, data_only=True)
    cap = wb[CAP]

    def cap_label(crow: int, col: str) -> str:
        v = cap[f"{col}{crow}"].value
        if not isinstance(v, str):
            raise ValueError(f"capacity {col}{crow} is not a structure label: {v!r}")
        return v

    def cap_val(crow: int, col: str) -> float:
        v = cap[f"{col}{crow}"].value
        if v is None:
            raise ValueError(f"capacity {col}{crow} has no cached value")
        return float(v)

    rows = {}
    for row, crow in DATA_ROWS.items():
        frm = cap_label(crow, "A")
        to = cap_label(crow, "B")
        q_design = cap_val(crow, "L")
        size = cap_val(crow, "M")
        length = cap_val(crow, "S")
        inv_up = cap_val(crow, "P")
        inv_dn = cap_val(crow, "Q")
        rise = RISE_IN_OVERRIDE.get(row, size)
        dia = EQ_DIA_IN_OVERRIDE.get(row, size)
        sf = ((q_design * 0.013) / (0.463 * (dia / 12.0) ** 2.67)) ** 2
        rows[(frm, to, row)] = {
            "from": frm, "to": to,
            "crown_up": inv_up + rise / 12.0,
            "crown_dn": inv_dn + rise / 12.0,
            "hf": sf * length,
            "hgl_up": None,
        }

    def hgl_at(structure: str) -> float:
        """MAXIFS(HGL_up of reaches leaving `structure`), tailwater if terminal."""
        vals = [r["hgl_up"] for r in rows.values()
                if r["from"] == structure and r["hgl_up"] is not None]
        return max(vals) if vals else TAILWATER_VALUE

    for _ in range(len(rows) + 2):
        for r in rows.values():
            hgl_dn = max(hgl_at(r["to"]), r["crown_dn"])
            r["hgl_up"] = max(hgl_dn + r["hf"], r["crown_up"])

    return {(r["from"], r["to"]): r["hgl_up"] for r in rows.values()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", default="docs/bburg-p-c-legacy.xlsx")
    parser.add_argument("--verify", action="store_true",
                        help="print the chain evaluated from cached values; no writes")
    args = parser.parse_args()

    if not args.verify:
        repair_workbook(args.path)
        print(f"Repaired: {args.path}")

    results = evaluate_chain(args.path)
    print(f"{'pipe':<24}{'HGL @ u/s structure (ft)':>26}")
    for (frm, to), hgl_up in sorted(results.items()):
        print(f"{frm:>6} -> {to:<14}{hgl_up:>16.3f}")


if __name__ == "__main__":
    main()

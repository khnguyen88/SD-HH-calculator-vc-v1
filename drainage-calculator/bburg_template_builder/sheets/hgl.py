"""HGL sheet - generalized hydraulic grade line walker.

One row per pipe reach, ordered downstream-to-upstream. User sets TW_Elev_Start at
the top; the walk propagates upstream. HGL_Method dropdown picks:
  - "HEC-22 EGL (d/s crown floor)": HGL_up = HGL_dn + Hf (no u/s floor)
  - "Legacy both-end crown floor":   HGL_up = MAX(HGL_dn + Hf, Crown_up)
"""
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


COLUMNS = [
    "Pipe_ID", "From", "To", "Q", "Size", "Length", "n",
    "Area", "R", "V", "Vh", "Sf", "Hf",
    "Inv_dn", "Inv_up", "Crown_dn", "Crown_up",
    "Type_u/s", "Angle_u/s", "Kb", "Hb",
    "HGL_dn_raw", "HGL_dn", "EGL_dn", "HGL_up_raw", "HGL_up", "EGL_up",
    "Regime", "Rim_u/s", "Crown_check", "Rim_check",
]


def _col_index(name: str) -> int:
    return COLUMNS.index(name) + 1


def _ref(row: int, name: str) -> str:
    return f"{get_column_letter(_col_index(name))}{row}"


def build_hgl_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("HGL")

    # Top-of-sheet inputs
    ws["A1"] = "HGL SHEET - Hydraulic Grade Line Walker"
    ws["A3"] = "TW_Elev_Start (ft):"
    ws["C3"] = 62.0
    wb.defined_names["TW_Elev_Start"] = DefinedName(name="TW_Elev_Start", attr_text="HGL!$C$3")
    ws["A4"] = "Storm_Selected:"
    ws["C4"] = "=Storm_Primary"
    ws["A5"] = "HGL_Method:"
    ws["C5"] = "=HGL_Method"
    ws["A6"] = "Instructions: paste one row per pipe (downstream-first). Formulas walk upstream."

    # Column headers (row 8)
    for c, name in enumerate(COLUMNS, start=1):
        ws.cell(row=8, column=c, value=name)

    # Seed Pipe_IDs from Bladensburg so the walker opens with a working example.
    # Walk order is downstream-first: pipes closest to outfall at the top.
    from bburg_template_builder.seed_data import BLADENSBURG_PIPES
    # Reverse so d/s pipes (toward OUTFALL) come first
    for i, p in enumerate(reversed(BLADENSBURG_PIPES)):
        ws.cell(row=10 + i, column=1, value=p["Pipe_ID"])

    first_data_row = 10
    last_data_row = 60
    for r in range(first_data_row, last_data_row + 1):
        pipe_ref = f"$A{r}"
        from_ref = f"$B{r}"
        to_ref = f"$C{r}"

        # From/To lookups from Pipes
        ws.cell(row=r, column=_col_index("From"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[From_Structure]),"")')
        ws.cell(row=r, column=_col_index("To"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[To_Structure]),"")')
        # Q pulled from Pipe Capacity sheet by Pipe's From_Structure (matches legacy approach)
        ws.cell(row=r, column=_col_index("Q"),
                value=(f'=IFERROR(IF(Storm_Primary="25yr",'
                       f"INDEX('25 Yr Pipe Capacity'!$L:$L,MATCH({from_ref},'25 Yr Pipe Capacity'!$A:$A,0)),"
                       f"INDEX('10 Yr Pipe Capacity'!$L:$L,MATCH({from_ref},'10 Yr Pipe Capacity'!$A:$A,0))),0)"))
        # Size, Length, n from Pipes
        ws.cell(row=r, column=_col_index("Size"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Size_in]),"")')
        ws.cell(row=r, column=_col_index("Length"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Length_ft]),"")')
        ws.cell(row=r, column=_col_index("n"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Manning_n]),0.013)')

        size_ref = _ref(r, "Size")
        # Area / R from Pipe_Properties
        ws.cell(row=r, column=_col_index("Area"),
                value=f'=IFERROR(XLOOKUP({size_ref},Pipe_Properties[Size],Pipe_Properties[Area]),0)')
        ws.cell(row=r, column=_col_index("R"),
                value=f'=IFERROR(XLOOKUP({size_ref},Pipe_Properties[Size],Pipe_Properties[Hyd Radius]),0)')
        # V, Vh
        area_ref = _ref(r, "Area")
        q_ref = _ref(r, "Q")
        ws.cell(row=r, column=_col_index("V"), value=f'=IFERROR({q_ref}/{area_ref},0)')
        v_ref = _ref(r, "V")
        ws.cell(row=r, column=_col_index("Vh"), value=f'={v_ref}^2/(2*Gravity_g)')
        # Sf, Hf
        n_ref = _ref(r, "n")
        r_ref = _ref(r, "R")
        ws.cell(row=r, column=_col_index("Sf"),
                value=f'=IFERROR(({q_ref}*{n_ref}/(1.486*{area_ref}*{r_ref}^(2/3)))^2,0)')
        sf_ref = _ref(r, "Sf")
        len_ref = _ref(r, "Length")
        ws.cell(row=r, column=_col_index("Hf"), value=f'={sf_ref}*{len_ref}')

        # Inverts, crowns
        ws.cell(row=r, column=_col_index("Inv_dn"),
                value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Inv_Out_Elev]),0)')
        ws.cell(row=r, column=_col_index("Inv_up"),
                value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Inv_In_Elev]),0)')
        inv_dn_ref = _ref(r, "Inv_dn")
        inv_up_ref = _ref(r, "Inv_up")
        ws.cell(row=r, column=_col_index("Crown_dn"), value=f'={inv_dn_ref}+{size_ref}/12')
        ws.cell(row=r, column=_col_index("Crown_up"), value=f'={inv_up_ref}+{size_ref}/12')
        # Type/Angle u/s
        ws.cell(row=r, column=_col_index("Type_u/s"),
                value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Type]),"")')
        ws.cell(row=r, column=_col_index("Angle_u/s"),
                value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Angle_deg]),0)')
        # Kb: SWITCH on Type u/s + XLOOKUP into Kb_Values by Angle
        type_ref = _ref(r, "Type_u/s")
        angle_ref = _ref(r, "Angle_u/s")
        kb_formula = (
            f'=IFERROR(SWITCH({type_ref},'
            f'"inlet",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Inlet],0,-1),'
            f'"manhole",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Manhole],0,-1),'
            f'"bend",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Bend],0,-1),'
            f'"junction",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Junction],0,-1),'
            f'"splitter",XLOOKUP({angle_ref},Kb_Values[Angle],Kb_Values[Manhole],0,-1),'
            f'"outfall",0,'
            f'0),0)'
        )
        ws.cell(row=r, column=_col_index("Kb"), value=kb_formula)
        kb_ref = _ref(r, "Kb")
        vh_ref = _ref(r, "Vh")
        ws.cell(row=r, column=_col_index("Hb"), value=f'={kb_ref}*{vh_ref}')

        # HGL_dn_raw
        if r == first_data_row:
            ws.cell(row=r, column=_col_index("HGL_dn_raw"), value=f'=TW_Elev_Start')
        else:
            egl_dn_this = _ref(r, "EGL_dn")
            ws.cell(row=r, column=_col_index("HGL_dn_raw"), value=f'={egl_dn_this}-{vh_ref}')

        # HGL_dn (crown floor at d/s always)
        hgl_dn_raw_ref = _ref(r, "HGL_dn_raw")
        crown_dn_ref = _ref(r, "Crown_dn")
        ws.cell(row=r, column=_col_index("HGL_dn"),
                value=f'=MAX({hgl_dn_raw_ref},{crown_dn_ref})')

        # EGL_dn
        if r == first_data_row:
            hgl_dn_ref = _ref(r, "HGL_dn")
            ws.cell(row=r, column=_col_index("EGL_dn"), value=f'={hgl_dn_ref}+{vh_ref}')
        else:
            egl_up_below = _ref(r - 1, "EGL_up")
            hb_below = _ref(r - 1, "Hb")
            ws.cell(row=r, column=_col_index("EGL_dn"),
                    value=f'={egl_up_below}+{hb_below}')

        # HGL_up_raw, HGL_up (method-dependent), EGL_up
        hgl_dn_ref = _ref(r, "HGL_dn")
        hf_ref = _ref(r, "Hf")
        ws.cell(row=r, column=_col_index("HGL_up_raw"), value=f'={hgl_dn_ref}+{hf_ref}')
        hgl_up_raw_ref = _ref(r, "HGL_up_raw")
        crown_up_ref = _ref(r, "Crown_up")
        ws.cell(row=r, column=_col_index("HGL_up"),
                value=(f'=IF(HGL_Method="Legacy both-end crown floor",'
                       f'MAX({hgl_up_raw_ref},{crown_up_ref}),'
                       f'{hgl_up_raw_ref})'))
        hgl_up_ref = _ref(r, "HGL_up")
        ws.cell(row=r, column=_col_index("EGL_up"), value=f'={hgl_up_ref}+{vh_ref}')

        # Regime
        ws.cell(row=r, column=_col_index("Regime"),
                value=(f'=IF({hgl_dn_raw_ref}>={crown_dn_ref},"Pressurized",'
                       f'IF(AND(HGL_Method="Legacy both-end crown floor",{hgl_up_raw_ref}<{crown_up_ref}),'
                       f'"Gravity - u/s crown floor also applied",'
                       f'"Gravity - d/s crown floor applied"))'))

        # Rim and checks
        ws.cell(row=r, column=_col_index("Rim_u/s"),
                value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Rim_Elev]),0)')
        ws.cell(row=r, column=_col_index("Crown_check"),
                value=f'=IF({hgl_up_ref}>{crown_up_ref}+Crown_Freeboard,"FAIL","OK")')
        rim_ref = _ref(r, "Rim_u/s")
        ws.cell(row=r, column=_col_index("Rim_check"),
                value=f'=IF({hgl_up_ref}>{rim_ref}-Rim_Freeboard,"FAIL","OK")')

    # Pipe_ID dropdown
    dv_pipe = DataValidation(type="list",
                             formula1='=INDIRECT("Pipes[Pipe_ID]")',
                             allow_blank=True)
    dv_pipe.add(f"A{first_data_row}:A{last_data_row}")
    ws.add_data_validation(dv_pipe)

    # Column widths
    for i, name in enumerate(COLUMNS, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = 10
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14

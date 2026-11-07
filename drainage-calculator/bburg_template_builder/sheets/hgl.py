"""HGL sheet - network hydraulic grade line walker (branch-aware).

One row per pipe reach. Each row looks up the HGL at its downstream structure with
MAXIFS over every reach whose From_Structure equals this row's To_Structure, so
tributaries joining a junction are handled without depending on row order. A reach that
discharges to an outfall starts from its chain's tailwater.

Two tailwaters ship by default: Chain A (to CULVERT-A) and Chain B (to CULVERT-B).

Flow direction is From -> To, so for a given pipe:
  Inv_up = From structure's Inv_Out_Elev (pipe invert leaving the upstream structure)
  Inv_dn = To structure's Inv_In_Elev  (pipe invert entering the downstream structure)

HGL_Method dropdown picks:
  - "HEC-22 EGL (d/s crown floor)": HGL_up = HGL_dn + Hf (no u/s floor)
  - "Legacy both-end crown floor":   HGL_up = MAX(HGL_dn + Hf, Crown_up)
"""
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


COLUMNS = [
    "Pipe_ID", "Chain", "From", "To", "Q", "Size", "Length", "n",
    "Area", "R", "V", "Vh", "Sf", "Hf",
    "Inv_dn", "Inv_up", "Crown_dn", "Crown_up",
    "Type_u/s", "Angle_u/s", "Kb", "Hb",
    "HGL_dn_raw", "HGL_dn", "EGL_dn", "HGL_up_raw", "HGL_up", "EGL_up",
    "Regime", "Rim_u/s", "Crown_check", "Rim_check",
]

FIRST_DATA_ROW = 10
LAST_DATA_ROW = 60


def _col_index(name: str) -> int:
    return COLUMNS.index(name) + 1


def _ref(row: int, name: str) -> str:
    return f"{get_column_letter(_col_index(name))}{row}"


def build_hgl_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("HGL")

    # Top-of-sheet inputs
    ws["A1"] = "HGL SHEET - Hydraulic Grade Line Walker"
    ws["A3"] = "TW_Elev_Start (Chain A) (ft):"
    ws["C3"] = 66.87
    wb.defined_names["TW_Elev_Start"] = DefinedName(name="TW_Elev_Start", attr_text="HGL!$C$3")
    ws["A4"] = "Storm_Selected:"
    ws["C4"] = "=Storm_Primary"
    ws["A5"] = "HGL_Method:"
    ws["C5"] = "=HGL_Method"
    ws["A6"] = "Instructions: assign each pipe a Chain (A/B); a reach ending at an outfall starts from its chain tailwater."
    ws["A7"] = "TW_Elev_Chain_B (ft):"
    ws["C7"] = 71.04
    wb.defined_names["TW_Elev_Chain_B"] = DefinedName(name="TW_Elev_Chain_B", attr_text="HGL!$C$7")

    # Column headers (row 8)
    for c, name in enumerate(COLUMNS, start=1):
        ws.cell(row=8, column=c, value=name)

    # Seed the proposed 10-yr network, downstream-first within each chain.
    from bburg_template_builder.seed_data import BLADENSBURG_HGL_ORDER, BLADENSBURG_PIPES
    pipes_by_id = {p["Pipe_ID"]: p for p in BLADENSBURG_PIPES}
    for i, pipe_id in enumerate(BLADENSBURG_HGL_ORDER):
        row = FIRST_DATA_ROW + i
        ws.cell(row=row, column=_col_index("Pipe_ID"), value=pipe_id)
        ws.cell(row=row, column=_col_index("Chain"), value=pipes_by_id[pipe_id]["Chain"])

    hgl_up_col = get_column_letter(_col_index("HGL_up"))
    from_col = get_column_letter(_col_index("From"))
    hgl_up_range = f"${hgl_up_col}${FIRST_DATA_ROW}:${hgl_up_col}${LAST_DATA_ROW}"
    from_range = f"${from_col}${FIRST_DATA_ROW}:${from_col}${LAST_DATA_ROW}"

    for r in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
        pipe_ref = _ref(r, "Pipe_ID")
        chain_ref = _ref(r, "Chain")
        from_ref = _ref(r, "From")
        to_ref = _ref(r, "To")

        # From/To lookups from Pipes
        ws.cell(row=r, column=_col_index("From"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[From_Structure]),"")')
        ws.cell(row=r, column=_col_index("To"),
                value=f'=IFERROR(XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[To_Structure]),"")')

        # Q: per-pipe design flow from Pipes[Design_Q_cfs] if provided, else the
        # Rational Method result on the selected Pipe Capacity sheet by From structure.
        fallback_q = (
            f'IF(Storm_Primary="25yr",'
            f"INDEX('25 Yr Pipe Capacity'!$L:$L,MATCH({from_ref},'25 Yr Pipe Capacity'!$A:$A,0)),"
            f"INDEX('10 Yr Pipe Capacity'!$L:$L,MATCH({from_ref},'10 Yr Pipe Capacity'!$A:$A,0)))"
        )
        override_q = f'XLOOKUP({pipe_ref},Pipes[Pipe_ID],Pipes[Design_Q_cfs],0)'
        ws.cell(row=r, column=_col_index("Q"),
                value=f'=IFERROR(IF({override_q}>0,{override_q},{fallback_q}),0)')

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

        # Inverts, crowns (From is upstream, To is downstream)
        ws.cell(row=r, column=_col_index("Inv_dn"),
                value=f'=IFERROR(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Inv_In_Elev]),0)')
        ws.cell(row=r, column=_col_index("Inv_up"),
                value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Inv_Out_Elev]),0)')
        inv_dn_ref = _ref(r, "Inv_dn")
        inv_up_ref = _ref(r, "Inv_up")
        ws.cell(row=r, column=_col_index("Crown_dn"), value=f'={inv_dn_ref}+{size_ref}/12')
        ws.cell(row=r, column=_col_index("Crown_up"), value=f'={inv_up_ref}+{size_ref}/12')

        # Kb is a bend loss at the upstream structure (From)
        ws.cell(row=r, column=_col_index("Type_u/s"),
                value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Type]),"")')
        ws.cell(row=r, column=_col_index("Angle_u/s"),
                value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Angle_deg]),0)')
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

        # HGL at the downstream structure: the upstream HGL of whatever reach leaves that
        # structure; for an outfall, the chain tailwater.
        downstream_hgl = f'MAXIFS({hgl_up_range},{from_range},{to_ref})'
        outfall_tw = (
            f'IF(XLOOKUP({to_ref},Structures[Structure_ID],Structures[Type],"")="outfall",'
            f'IF({chain_ref}="B",TW_Elev_Chain_B,TW_Elev_Start),0)'
        )
        ws.cell(row=r, column=_col_index("HGL_dn_raw"),
                value=f'=MAX({downstream_hgl},{outfall_tw})')

        # HGL_dn (crown floor at d/s always)
        hgl_dn_raw_ref = _ref(r, "HGL_dn_raw")
        crown_dn_ref = _ref(r, "Crown_dn")
        ws.cell(row=r, column=_col_index("HGL_dn"),
                value=f'=MAX({hgl_dn_raw_ref},{crown_dn_ref})')

        # EGL_dn - energy at the d/s end
        hgl_dn_ref = _ref(r, "HGL_dn")
        ws.cell(row=r, column=_col_index("EGL_dn"), value=f'={hgl_dn_ref}+{vh_ref}')

        # HGL_up_raw, HGL_up (method-dependent), EGL_up
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

        # Rim and checks (rim belongs to the upstream structure)
        ws.cell(row=r, column=_col_index("Rim_u/s"),
                value=f'=IFERROR(XLOOKUP({from_ref},Structures[Structure_ID],Structures[Rim_Elev]),0)')
        ws.cell(row=r, column=_col_index("Crown_check"),
                value=f'=IF({hgl_up_ref}>{crown_up_ref}+Crown_Freeboard,"FAIL","OK")')
        rim_ref = _ref(r, "Rim_u/s")
        ws.cell(row=r, column=_col_index("Rim_check"),
                value=f'=IF({hgl_up_ref}>{rim_ref}-Rim_Freeboard,"FAIL","OK")')

    # Pipe_ID and Chain dropdowns
    dv_pipe = DataValidation(type="list",
                             formula1='=INDIRECT("Pipes[Pipe_ID]")',
                             allow_blank=True)
    dv_pipe.add(f"A{FIRST_DATA_ROW}:A{LAST_DATA_ROW}")
    ws.add_data_validation(dv_pipe)

    dv_chain = DataValidation(type="list", formula1='"A,B"', allow_blank=True)
    dv_chain.add(f"B{FIRST_DATA_ROW}:B{LAST_DATA_ROW}")
    ws.add_data_validation(dv_chain)

    # Column widths
    for i, name in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = 10
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 7
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14

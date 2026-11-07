"""HGL_Example - educational step-by-step HGL/EGL walk for a 4-pipe 5-structure network.

All numbers are live formulas off a tiny input block at the top; both HEC-22 and
Legacy methods are computed side-by-side so engineers can see how they diverge.

Network:
  [S-1 inlet]--P-1(12",60')-->[S-2 manhole,0]--P-2(15",95')-->
    [S-3 bend,15]--P-3(18",110')-->[S-4 inlet,0]--P-4(24",80')-->[OUTFALL endwall]

Walk order in the sheet: downstream-first (P-4 at the top block, P-1 at the bottom).
"""
from openpyxl import Workbook


# (ID, L_ft, D_in, n, Q_cfs, Inv_dn, Inv_up, u/s_struct_type, u/s_angle_deg)
PIPES = [
    ("P-4", 80.0,  24, 0.013, 9.5, 94.00, 94.56, "inlet",   0),
    ("P-3", 110.0, 18, 0.013, 7.2, 94.56, 95.66, "bend",    15),
    ("P-2", 95.0,  15, 0.013, 4.5, 95.66, 96.61, "manhole", 0),
    ("P-1", 60.0,  12, 0.013, 2.1, 96.61, 97.21, "inlet",   0),
]


def build_hgl_example_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("HGL_Example")

    # Title and inputs
    ws["A1"] = "HGL_Example - Educational step-by-step (both methods side-by-side)"
    ws["A3"] = "Starting tailwater at endwall (ft):"
    ws["C3"] = 97.00
    ws["A4"] = "HGL_Method (reads from Config):"
    ws["C4"] = "=HGL_Method"
    ws["A6"] = "Network: [S-1]-P-1->[S-2]-P-2->[S-3]-P-3->[S-4]-P-4->[OUTFALL]"
    ws["A7"] = "Walk order below: downstream-first (P-4 first, P-1 last)"

    # Side-by-side method headers (row 10)
    ws["A10"] = "Equation (symbolic)"
    ws["B10"] = "Substituted values"
    ws["C10"] = "HEC-22 (d/s floor)"
    ws["D10"] = "Legacy both-end"

    tw_cell = "$C$3"
    row = 12
    prev_egl_up_hec22 = None
    prev_egl_up_legacy = None
    prev_hb_hec22 = None
    prev_hb_legacy = None

    for idx, (pid, L, D, n, Q, inv_dn, inv_up, up_type, up_angle) in enumerate(PIPES):
        ws.cell(row=row, column=1, value=f"--- Pipe {pid} (D={D}\", L={L}, Q={Q} cfs) ---")
        row += 1

        # Area
        ws.cell(row=row, column=1, value="Area = pi*(D/12)^2/4")
        ws.cell(row=row, column=2, value=f"pi*({D}/12)^2/4")
        area_formula = f"PI()*({D}/12)^2/4"
        ws.cell(row=row, column=3, value=f"={area_formula}")
        ws.cell(row=row, column=4, value=f"={area_formula}")
        area_ref_hec22 = f"$C${row}"
        area_ref_legacy = f"$D${row}"
        row += 1

        # V
        ws.cell(row=row, column=1, value="V = Q / Area")
        ws.cell(row=row, column=2, value=f"{Q} / Area")
        ws.cell(row=row, column=3, value=f"={Q}/{area_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={Q}/{area_ref_legacy}")
        v_ref_hec22 = f"$C${row}"
        v_ref_legacy = f"$D${row}"
        row += 1

        # Vh
        ws.cell(row=row, column=1, value="Vh = V^2 / (2g)")
        ws.cell(row=row, column=2, value="V^2 / 64.4")
        ws.cell(row=row, column=3, value=f"={v_ref_hec22}^2/64.4")
        ws.cell(row=row, column=4, value=f"={v_ref_legacy}^2/64.4")
        vh_ref_hec22 = f"$C${row}"
        vh_ref_legacy = f"$D${row}"
        row += 1

        # R
        ws.cell(row=row, column=1, value="R = D/4 (full)")
        ws.cell(row=row, column=2, value=f"{D}/12/4")
        r_formula = f"({D}/12)/4"
        ws.cell(row=row, column=3, value=f"={r_formula}")
        ws.cell(row=row, column=4, value=f"={r_formula}")
        r_ref_hec22 = f"$C${row}"
        r_ref_legacy = f"$D${row}"
        row += 1

        # Sf
        ws.cell(row=row, column=1, value="Sf = (Q*n/(1.486*A*R^(2/3)))^2")
        ws.cell(row=row, column=2, value=f"({Q}*{n}/(1.486*A*R^(2/3)))^2")
        ws.cell(row=row, column=3, value=f"=({Q}*{n}/(1.486*{area_ref_hec22}*{r_ref_hec22}^(2/3)))^2")
        ws.cell(row=row, column=4, value=f"=({Q}*{n}/(1.486*{area_ref_legacy}*{r_ref_legacy}^(2/3)))^2")
        sf_ref_hec22 = f"$C${row}"
        sf_ref_legacy = f"$D${row}"
        row += 1

        # Hf
        ws.cell(row=row, column=1, value="Hf = Sf * L")
        ws.cell(row=row, column=2, value=f"Sf * {L}")
        ws.cell(row=row, column=3, value=f"={sf_ref_hec22}*{L}")
        ws.cell(row=row, column=4, value=f"={sf_ref_legacy}*{L}")
        hf_ref_hec22 = f"$C${row}"
        hf_ref_legacy = f"$D${row}"
        row += 1

        # Crown_dn
        ws.cell(row=row, column=1, value="Crown_dn = Inv_dn + D/12")
        ws.cell(row=row, column=2, value=f"{inv_dn} + {D}/12")
        crown_dn = inv_dn + D / 12.0
        ws.cell(row=row, column=3, value=crown_dn)
        ws.cell(row=row, column=4, value=crown_dn)
        crown_dn_ref_hec22 = f"$C${row}"
        crown_dn_ref_legacy = f"$D${row}"
        row += 1

        # Crown_up
        ws.cell(row=row, column=1, value="Crown_up = Inv_up + D/12")
        ws.cell(row=row, column=2, value=f"{inv_up} + {D}/12")
        crown_up = inv_up + D / 12.0
        ws.cell(row=row, column=3, value=crown_up)
        ws.cell(row=row, column=4, value=crown_up)
        crown_up_ref_hec22 = f"$C${row}"
        crown_up_ref_legacy = f"$D${row}"
        row += 1

        # HGL_dn_raw
        ws.cell(row=row, column=1, value="HGL_dn_raw")
        if idx == 0:
            ws.cell(row=row, column=2, value="= TW_input")
            ws.cell(row=row, column=3, value=f"={tw_cell}")
            ws.cell(row=row, column=4, value=f"={tw_cell}")
        else:
            ws.cell(row=row, column=2, value="EGL_dn - Vh (this pipe)")
            ws.cell(row=row, column=3,
                    value=f"={prev_egl_up_hec22}+{prev_hb_hec22}-{vh_ref_hec22}")
            ws.cell(row=row, column=4,
                    value=f"={prev_egl_up_legacy}+{prev_hb_legacy}-{vh_ref_legacy}")
        hgl_dn_raw_ref_hec22 = f"$C${row}"
        hgl_dn_raw_ref_legacy = f"$D${row}"
        row += 1

        # HGL_dn = MAX(HGL_dn_raw, Crown_dn)
        ws.cell(row=row, column=1, value="HGL_dn = MAX(HGL_dn_raw, Crown_dn)")
        ws.cell(row=row, column=2, value=f"MAX(HGL_dn_raw, {crown_dn:.2f})")
        ws.cell(row=row, column=3, value=f"=MAX({hgl_dn_raw_ref_hec22},{crown_dn_ref_hec22})")
        ws.cell(row=row, column=4, value=f"=MAX({hgl_dn_raw_ref_legacy},{crown_dn_ref_legacy})")
        hgl_dn_ref_hec22 = f"$C${row}"
        hgl_dn_ref_legacy = f"$D${row}"
        row += 1

        # EGL_dn
        ws.cell(row=row, column=1, value="EGL_dn = HGL_dn + Vh")
        ws.cell(row=row, column=2, value="HGL_dn + Vh")
        ws.cell(row=row, column=3, value=f"={hgl_dn_ref_hec22}+{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_dn_ref_legacy}+{vh_ref_legacy}")
        row += 1

        # HGL_up_raw
        ws.cell(row=row, column=1, value="HGL_up_raw = HGL_dn + Hf")
        ws.cell(row=row, column=2, value="HGL_dn + Hf")
        ws.cell(row=row, column=3, value=f"={hgl_dn_ref_hec22}+{hf_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_dn_ref_legacy}+{hf_ref_legacy}")
        hgl_up_raw_ref_hec22 = f"$C${row}"
        hgl_up_raw_ref_legacy = f"$D${row}"
        row += 1

        # HGL_up (method-dependent)
        ws.cell(row=row, column=1, value="HGL_up")
        ws.cell(row=row, column=2, value="HEC-22: HGL_up_raw; Legacy: MAX(HGL_up_raw, Crown_up)")
        ws.cell(row=row, column=3, value=f"={hgl_up_raw_ref_hec22}")
        ws.cell(row=row, column=4, value=f"=MAX({hgl_up_raw_ref_legacy},{crown_up_ref_legacy})")
        hgl_up_ref_hec22 = f"$C${row}"
        hgl_up_ref_legacy = f"$D${row}"
        row += 1

        # EGL_up
        ws.cell(row=row, column=1, value="EGL_up = HGL_up + Vh")
        ws.cell(row=row, column=2, value="HGL_up + Vh")
        ws.cell(row=row, column=3, value=f"={hgl_up_ref_hec22}+{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={hgl_up_ref_legacy}+{vh_ref_legacy}")
        egl_up_ref_hec22 = f"$C${row}"
        egl_up_ref_legacy = f"$D${row}"
        row += 1

        # Kb lookup
        ws.cell(row=row, column=1, value=f"Kb = Kb_Values[Type={up_type},Angle={up_angle}]")
        ws.cell(row=row, column=2, value=f"lookup for type={up_type}, angle={up_angle}")
        if up_type == "outfall":
            kb_formula = "0"
        else:
            kb_col = {"inlet": "Inlet", "manhole": "Manhole",
                      "bend": "Bend", "junction": "Junction",
                      "splitter": "Manhole"}[up_type]
            kb_formula = f"XLOOKUP({up_angle},Kb_Values[Angle],Kb_Values[{kb_col}],0,-1)"
        ws.cell(row=row, column=3, value=f"={kb_formula}")
        ws.cell(row=row, column=4, value=f"={kb_formula}")
        kb_ref_hec22 = f"$C${row}"
        kb_ref_legacy = f"$D${row}"
        row += 1

        # Hb = Kb * Vh (this pipe)
        ws.cell(row=row, column=1, value="Hb = Kb * Vh(this pipe)")
        ws.cell(row=row, column=2, value="Kb * Vh")
        ws.cell(row=row, column=3, value=f"={kb_ref_hec22}*{vh_ref_hec22}")
        ws.cell(row=row, column=4, value=f"={kb_ref_legacy}*{vh_ref_legacy}")
        hb_ref_hec22 = f"$C${row}"
        hb_ref_legacy = f"$D${row}"
        row += 1

        # Save state for next (upstream) pipe
        prev_egl_up_hec22 = egl_up_ref_hec22
        prev_egl_up_legacy = egl_up_ref_legacy
        prev_hb_hec22 = hb_ref_hec22
        prev_hb_legacy = hb_ref_legacy

        # Spacer between blocks
        row += 2

    # Try-this experiments
    ws.cell(row=row, column=1, value="TRY THIS:")
    row += 1
    experiments = [
        "Raise TW (C3) to 100.0 - all HGL rise by at least 3 ft; HEC-22 and Legacy give identical results (no gravity reaches).",
        "Lower TW (C3) to 93.00 - P-4 switches to 'Gravity' regime; HGL_dn pins at Crown_dn (96.00) under both methods.",
        "Lower TW to 93.00 AND watch P-3/P-2/P-1 - Legacy column may diverge from HEC-22 if HGL_up_raw drops below Crown_up for any upstream pipe.",
        "Change HGL_Method in Config - the C column keeps HEC-22; the D column shows Legacy. Both are always computed here for teaching.",
    ]
    for exp in experiments:
        ws.cell(row=row, column=1, value=exp)
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20

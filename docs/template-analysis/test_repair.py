# Tests for repair.py - applies R1-R5 to template_wip_new.xlsx. Shared
# fixture `repaired_wb` lives in conftest.py so T9-T13 can reuse it.
from pathlib import Path

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"


def test_script_runs_and_produces_file(repaired_wb):
    assert WIP.exists()
    assert len(repaired_wb.sheetnames) == 16


def test_r3_orphan_names_removed(repaired_wb):
    names = list(repaired_wb.defined_names)
    for orphan in ("\\0", "\\c", "\\e", "\\p", "\\r"):
        assert orphan not in names, f"orphan name {orphan!r} still present"
    for i in range(1, 19):
        assert f"_DUR{i}" not in names, f"_DUR{i} still present"
    assert "_INT1" not in names
    assert "_INT2" not in names


def test_r3_no_broken_names_remain(repaired_wb):
    for name in repaired_wb.defined_names:
        d = repaired_wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        assert "#REF!" not in val, f"name {name!r} still resolves to #REF!: {val!r}"


def test_r4_selectcounty_duplicate_removed(repaired_wb):
    names = list(repaired_wb.defined_names)
    assert "SelectCounty" not in names, "SelectCounty duplicate still present"
    assert "Select_County" in names, "Select_County (canonical) was removed by mistake"


def test_r4_no_duplicate_range_names(repaired_wb):
    seen = {}
    for name in repaired_wb.defined_names:
        d = repaired_wb.defined_names[name]
        val = getattr(d, "value", None) or str(d)
        seen.setdefault(val, []).append(name)
    dupes = {rng: names for rng, names in seen.items() if len(names) > 1}
    assert not dupes, f"duplicate-name ranges remain: {dupes}"


def test_r1_no_ref_errors_on_hgl_25year(repaired_wb):
    ws = repaired_wb["HGL(25YEAR)"]
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            text = v if isinstance(v, str) else getattr(v, "text", None)
            if isinstance(text, str):
                assert "#REF!" not in text, (
                    f"HGL(25YEAR)!{cell.coordinate} still contains #REF!: {text!r}"
                )


def test_r1_hgl_25year_broken_columns_use_xlookup(repaired_wb):
    # Every previously broken column is now an XLOOKUP against SDC.
    ws = repaired_wb["HGL(25YEAR)"]
    c7 = ws["C7"].value
    assert isinstance(c7, str) and "XLOOKUP" in c7 and "'STORM DRAIN COMPS'!$P:$P" in c7, (
        f"C7 should XLOOKUP U/S invert from SDC $P, got {c7!r}")
    e7 = ws["E7"].value
    assert isinstance(e7, str) and "XLOOKUP" in e7 and "'STORM DRAIN COMPS'!$Q:$Q" in e7, (
        f"E7 should XLOOKUP D/S invert from SDC $Q, got {e7!r}")
    h7 = ws["H7"].value
    assert isinstance(h7, str) and "XLOOKUP" in h7 and "'STORM DRAIN COMPS'!$O:$O" in h7, (
        f"H7 should XLOOKUP pipe length from SDC $O, got {h7!r}")
    l7 = ws["L7"].value
    assert isinstance(l7, str) and "XLOOKUP" in l7 and "'STORM DRAIN COMPS'!$AF:$AF" in l7, (
        f"L7 should XLOOKUP structure loss from SDC $AF, got {l7!r}")


def test_r1_hgl_25year_intact_columns_preserved(repaired_wb):
    # The on-sheet 25-year friction-slope and HGL chain formulas must be
    # left alone. The spec requires preserving the intact 25-year Sf
    # formula in column I (which computes Sf from column U = 25-year Q and
    # column V = Manning n), along with G/J/K/M (HGL chain) and Q-V
    # (25-year auxiliary data).
    ws = repaired_wb["HGL(25YEAR)"]
    i7 = ws["I7"].value
    assert isinstance(i7, str), f"I7 must still be a formula, got {type(i7).__name__}"
    # The intact I7 formula recomputes Sf using column U (25-year Q) and
    # column V (Manning n); it must NOT have been replaced by an SDC Y lookup.
    assert "U7" in i7 and "V7" in i7, (
        f"I7 should recompute 25-year Sf from U7 (25-yr Q) and V7 (Manning n), "
        f"got {i7!r}")
    assert "'STORM DRAIN COMPS'!$Y:$Y" not in i7, (
        f"I7 must NOT have been replaced by an SDC $Y (10-year) lookup; "
        f"got {i7!r}")
    # Spot-check the 25-year auxiliary columns Q-V still compute on-sheet.
    for col in ("Q7", "R7", "S7", "T7", "U7", "V7"):
        v = ws[col].value
        assert isinstance(v, str) and v.startswith("="), (
            f"{col} should still carry a formula, got {v!r}")


def test_r1_no_header_override_note(repaired_wb):
    # The earlier-approach override note is no longer appropriate because
    # the intact I-column computes a true 25-year Sf; verify nothing added
    # an obsolete "defaults to 10-year Sf" note on A4.
    ws = repaired_wb["HGL(25YEAR)"]
    a4 = (ws["A4"].value or "")
    assert "10-year Sf" not in a4, (
        f"A4 should not carry a 10-year-default note; got {a4!r}")


def test_r2_inlet_spacing_ak_has_no_ref_errors(repaired_wb):
    ws = repaired_wb["INLET SPACING"]
    for row in range(11, 97):
        cell = ws.cell(row=row, column=37)  # AK
        v = cell.value
        text = v if isinstance(v, str) else getattr(v, "text", None)
        if isinstance(text, str):
            assert "#REF!" not in text, (
                f"INLET SPACING!AK{row} still contains #REF!: {text!r}"
            )


def test_r5_acyclic_note_present(repaired_wb):
    ws = repaired_wb["EQUATIONS + INSTRUCTIONS"]
    found = False
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "acyclic pipe network" in cell.value:
                found = True
                break
        if found:
            break
    assert found, "R5 acyclic-network note not found on EQUATIONS + INSTRUCTIONS"


def test_workbook_has_no_ref_errors_anywhere(repaired_wb):
    hits = []
    for ws in repaired_wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str) and "#REF!" in text:
                    hits.append(f"{ws.title}!{cell.coordinate}")
    assert not hits, f"#REF! still present at: {hits[:10]}..."


def test_k_column_uses_filter_max_idiom(repaired_wb):
    # Every K{r} formula on STORM DRAIN COMPS rows 10-98 must carry the
    # FILTER+MAX pattern. Replaces the legacy CSE-array IF(MAX(...))
    # formula with a self-documenting Excel-365-native equivalent.
    ws = repaired_wb["STORM DRAIN COMPS"]
    marker_filter = "LET(upstream,FILTER("
    marker_max = "MAX(upstream,E"
    missing = []
    for r in range(10, 99):
        v = ws.cell(row=r, column=11).value
        text = getattr(v, "text", None) or (v if isinstance(v, str) else None)
        if not isinstance(text, str) or not text.startswith("="):
            continue  # row has no K formula; skip
        if marker_filter not in text or marker_max not in text:
            missing.append(r)
    assert not missing, (
        f"K column FILTER+MAX pattern missing on rows {missing[:10]}"
        f"{'...' if len(missing) > 10 else ''}"
    )


def test_workbook_has_no_external_links(repaired_wb):
    import re
    ext_pat = re.compile(r"'?\[[^\]]+\.xls[xmb]?\]")
    hits = []
    for ws in repaired_wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                text = v if isinstance(v, str) else getattr(v, "text", None)
                if isinstance(text, str) and ext_pat.search(text):
                    hits.append(f"{ws.title}!{cell.coordinate}")
    assert not hits, f"external workbook links remain: {hits[:10]}..."

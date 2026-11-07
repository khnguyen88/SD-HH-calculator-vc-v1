"""End-to-end tests for the full workbook build. Keeps a running list of required sheets."""


REQUIRED_SHEETS = [
    "Config",
    "NOAA14",
    "IDF_Lookup",
    "Landuse_Lookup",
    "Pipe_Properties",
    "Kb_Values",
    "DA_Catchments",
    "Structures",
    "Pipes",
    "Rationals-MCDOT",
    "Inlet Spacing_10-yr",
    "Inlet Spacing_2-yr",
    "10 Yr Pipe Capacity",
    "25 Yr Pipe Capacity",
    "HGL",
    "HGL_Example",
]


def test_workbook_builds_without_errors(built_wb):
    # Just constructing the workbook should not raise.
    assert built_wb is not None


def test_workbook_has_all_required_sheets(built_wb):
    actual = set(built_wb.sheetnames)
    missing = [s for s in REQUIRED_SHEETS if s not in actual]
    assert not missing, f"Missing sheets: {missing}"


def test_workbook_has_no_extra_sheets(built_wb):
    # Guard against accidentally re-adding legacy sheets.
    forbidden = {"10 Yr MoCo HGL", "25 Yr SHA HGL", "HGL 25-yr",
                 "SHA Intensity", "MoCoIntensity", "Intensity",
                 "25 Yr SHA Pipe Capacity", "TABLES", "Kb Values MoCo"}
    overlap = forbidden & set(built_wb.sheetnames)
    assert not overlap, f"Legacy sheets must not be emitted: {overlap}"


def test_bladensburg_seed_drives_rationals_block_1(built_wb):
    """Spot-check: Rationals block 1 has Area = SUMIFS formula on DA_Catchments."""
    rationals = built_wb["Rationals-MCDOT"]
    # Block 1 TOTALS row = 20, Area column = E (5)
    formula = str(rationals.cell(row=20, column=5).value)
    assert "SUMIFS" in formula and "DA_Catchments" in formula


def test_no_hard_coded_rationals_refs_anywhere(built_wb):
    """Guard: no sheet except Rationals-MCDOT may use `='Rationals-MCDOT'!A1` style refs."""
    import re
    forbidden = re.compile(r"'Rationals-MCDOT'![A-Z]+\d+(?!:)")
    for sheet_name in built_wb.sheetnames:
        if sheet_name == "Rationals-MCDOT":
            continue
        ws = built_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    hits = forbidden.findall(cell.value)
                    assert not hits, (
                        f"{sheet_name} {cell.coordinate}: hard-coded Rationals ref: {cell.value}"
                    )


def test_future_functions_are_xlfn_prefixed(built_wb):
    """Excel 365 shows #NAME? for bare post-2007 function names stored in OOXML."""
    import re
    bare = re.compile(r"(?<![\w.])(XLOOKUP|XMATCH|IFS|SWITCH|FILTER|MAXIFS|MINIFS)\(")
    for sheet_name in built_wb.sheetnames:
        ws = built_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    assert not bare.search(cell.value), (
                        f"{sheet_name} {cell.coordinate}: unprefixed function: {cell.value}"
                    )


def test_no_ref_errors_anywhere(built_wb):
    """Guard: no #REF!/#NAME? literals baked into the builder output."""
    for sheet_name in built_wb.sheetnames:
        ws = built_wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    assert "#REF" not in cell.value, f"{sheet_name} {cell.coordinate}: {cell.value}"
                    assert "#NAME" not in cell.value, f"{sheet_name} {cell.coordinate}: {cell.value}"


def test_build_script_produces_output_file():
    """Running build_bburg_template.py as a subprocess produces docs/bburg-p-c-template.xlsx."""
    import subprocess
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "drainage-calculator" / "build_bburg_template.py"
    output = repo_root / "docs" / "bburg-p-c-template.xlsx"
    if output.exists():
        output.unlink()
    result = subprocess.run([sys.executable, str(script)],
                            capture_output=True, text=True, cwd=str(repo_root))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert output.exists()

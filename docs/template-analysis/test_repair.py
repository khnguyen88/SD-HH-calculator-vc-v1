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

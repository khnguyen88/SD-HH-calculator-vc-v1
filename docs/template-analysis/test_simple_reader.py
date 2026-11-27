"""Simple-shape reader round-trip tests."""
from pathlib import Path
import openpyxl

HERE = Path(__file__).parent
WIP = HERE.parent / "template_wip_new.xlsx"
GOLDEN = HERE.parent / "template_golden.xlsx"


def read_simple_pipes_py(wb):
    """Mirror of readSimpleWorkbook's pipe-row loop in JS."""
    sdc = wb["STORM DRAIN COMPS"]
    pipes = []
    for r in range(10, 99):
        from_id = sdc[f"A{r}"].value
        to_id = sdc[f"B{r}"].value
        if from_id in (None, ""):
            continue
        pipes.append({
            "fromId": from_id,
            "toId": to_id,
            "size": sdc[f"N{r}"].value,
            "length": sdc[f"O{r}"].value,
            "usInvert": sdc[f"P{r}"].value,
            "dsInvert": sdc[f"Q{r}"].value,
            "angle": sdc[f"R{r}"].value,
            "n": sdc[f"S{r}"].value,
        })
    return pipes


def test_wip_has_populated_pipes():
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    assert len(pipes) >= 3, f"expected 3+ pipes, got {len(pipes)}"
    first = pipes[0]
    assert first["fromId"] not in (None, "")
    assert first["toId"] not in (None, "")


def test_wip_pipe_r_is_angle_not_manning():
    """Regression: col R is angle (Whole #), col S is Manning's n."""
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    for p in pipes:
        if p["angle"] is not None:
            assert isinstance(p["angle"], (int, float))
            if isinstance(p["angle"], float):
                assert p["angle"] == int(p["angle"]), (
                    f"Angle {p['angle']} should be whole; is R/S swapped?"
                )
        if p["n"] is not None:
            assert 0.005 <= p["n"] <= 0.03, (
                f"n={p['n']} out of range; is R/S swapped?"
            )


def materialize_structures_py(pipes):
    """Mirror of the JS structure-materialization pass."""
    seen = {}
    for p in pipes:
        for sid in (p["fromId"], p["toId"]):
            if sid and sid not in seen:
                seen[sid] = {
                    "structureId": sid, "type": "manhole",
                    "rim": "", "capturedQOverride": "",
                }
    by_from = {p["fromId"]: p for p in pipes}
    for sid, s in seen.items():
        source = by_from.get(sid)
        if source:
            if source.get("_structureType"):
                s["type"] = str(source["_structureType"]).lower()
            if source.get("_rim") not in (None, ""):
                s["rim"] = source["_rim"]
            if source.get("_capturedQOverride") not in (None, ""):
                s["capturedQOverride"] = source["_capturedQOverride"]
    all_from = {p["fromId"] for p in pipes}
    for sid, s in seen.items():
        if sid not in all_from and s["type"] == "manhole":
            s["type"] = "outfall"
    return list(seen.values())


def test_structures_materialized_from_pipes():
    import openpyxl
    wb = openpyxl.load_workbook(WIP, data_only=True)
    pipes = read_simple_pipes_py(wb)
    sdc = wb["STORM DRAIN COMPS"]
    for p, r_idx in zip(pipes, (r for r in range(10, 99)
                               if sdc[f"A{r}"].value not in (None, ""))):
        p["_structureType"] = sdc[f"AA{r_idx}"].value
        p["_rim"] = sdc[f"AB{r_idx}"].value
        p["_capturedQOverride"] = sdc[f"AK{r_idx}"].value
    structs = materialize_structures_py(pipes)
    all_ids = {s["structureId"] for s in structs}
    all_pipe_ids = {p["fromId"] for p in pipes} | {p["toId"] for p in pipes}
    assert all_ids == all_pipe_ids - {"", None}
    outfalls = [s for s in structs if s["type"] == "outfall"]
    assert len(outfalls) >= 1, "Simple reader must identify at least one outfall"

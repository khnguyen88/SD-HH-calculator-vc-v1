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

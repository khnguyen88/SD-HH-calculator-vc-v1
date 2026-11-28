"""Smoke: the shared reader module is inlined into the visualizer build."""
from pathlib import Path


def find_visualizer_build():
    # Walk up from this test file to the worktree root, then search for the
    # built visualizer. Using Path(".") would miss it because pytest runs
    # from docs/, one level below visualizer/.
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for p in parent.rglob("storm-drain-visualizer.html"):
            if "node_modules" in p.parts:
                continue
            if ".worktrees" in p.parts:
                # Skip stale builds in sibling feature worktrees.
                continue
            return p
        # Stop once we've reached the worktree root (has visualizer/ dir).
        if (parent / "visualizer").is_dir():
            break
    return None


def test_visualizer_has_shape_reader_inlined():
    v = find_visualizer_build()
    if v is None:
        import pytest
        pytest.skip("No visualizer build found")
    text = v.read_text(encoding="utf-8", errors="ignore")
    assert "window.__xlsxShapeReader" in text, (
        "Visualizer build missing inlined shape reader"
    )
    assert "detectShape" in text

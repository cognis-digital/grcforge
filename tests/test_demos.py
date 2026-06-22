"""Tests that every bundled demo is well-formed and actually produces output.

Each demo directory under demos/ carries a SCENARIO.md and (usually) an
implemented-controls JSON file. These tests load each demo through the real
engine so a broken demo fails CI rather than shipping.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grcforge.cli import main
from grcforge.crosswalk import Crosswalk

DEMOS = Path(__file__).resolve().parent.parent / "demos"


def _demo_dirs():
    return sorted(p for p in DEMOS.iterdir() if p.is_dir())


def test_demos_dir_exists():
    assert DEMOS.is_dir()
    assert len(_demo_dirs()) >= 5


@pytest.mark.parametrize("demo", _demo_dirs(), ids=lambda p: p.name)
def test_demo_has_scenario(demo):
    scenario = demo / "SCENARIO.md"
    assert scenario.is_file(), f"{demo.name} is missing SCENARIO.md"
    text = scenario.read_text(encoding="utf-8")
    assert "## Run it" in text, f"{demo.name} SCENARIO.md has no Run it section"


@pytest.mark.parametrize("demo", _demo_dirs(), ids=lambda p: p.name)
def test_demo_inputs_are_valid_json(demo):
    for jf in demo.glob("*.json"):
        data = json.loads(jf.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{jf} should be a JSON object"


@pytest.mark.parametrize("demo", _demo_dirs(), ids=lambda p: p.name)
def test_demo_custom_crosswalks_load(demo):
    cw_file = demo / "crosswalk.json"
    if cw_file.exists():
        cw = Crosswalk.load(cw_file)
        assert cw.frameworks
        assert cw.mappings


@pytest.mark.parametrize("demo", _demo_dirs(), ids=lambda p: p.name)
def test_demo_coverage_runs(demo):
    """Every demo with an implemented.json must produce a coverage report."""
    impl = demo / "implemented.json"
    if not impl.exists():
        pytest.skip(f"{demo.name} has no implemented.json (map-only demo)")
    cw_file = demo / "crosswalk.json"
    argv = []
    if cw_file.exists():
        argv += ["--crosswalk", str(cw_file)]
    argv += ["coverage", str(impl), "--format", "json"]
    rc = main(argv)
    assert rc == 0, f"coverage failed for demo {demo.name}"

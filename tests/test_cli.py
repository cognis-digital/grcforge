"""Tests for the grcforge CLI: exit codes, JSON output, error handling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grcforge.cli import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "examples" / "implemented.json")


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert "grcforge" in out


def test_map_text(capsys):
    rc = main(["map", "AC-2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "AC-2" in out
    assert "nist" in out


def test_map_json(capsys):
    rc = main(["map", "AC-2", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["query"] == "AC-2"
    assert data["matches"]


def test_map_no_match_returns_1(capsys):
    rc = main(["map", "ZZ-999"])
    assert rc == 1
    assert "No mapping" in capsys.readouterr().out


def test_list_all(capsys):
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nist" in out and "cis" in out and "soc2" in out


def test_list_framework(capsys):
    rc = main(["list", "--framework", "nist"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "AC-2" in out


def test_list_framework_json(capsys):
    rc = main(["list", "--framework", "cis", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["framework"] == "cis"
    assert any(c.startswith("CIS") for c in data["controls"])


def test_list_unknown_framework_errors(capsys):
    rc = main(["list", "--framework", "bogus"])
    assert rc == 2
    assert "Unknown framework" in capsys.readouterr().err


def test_coverage_text(capsys):
    rc = main(["coverage", EXAMPLE])
    assert rc == 0
    out = capsys.readouterr().out
    assert "%" in out and "nist" in out


def test_coverage_json(capsys):
    rc = main(["coverage", EXAMPLE, "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "frameworks" in data
    assert data["frameworks"]["nist"]["percent"] >= 0


def test_coverage_missing_file_errors(capsys):
    rc = main(["coverage", "does-not-exist.json"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_gaps_text(capsys):
    rc = main(["gaps", EXAMPLE, "--framework", "cis"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Gap analysis" in out


def test_gaps_json(capsys):
    rc = main(["gaps", EXAMPLE, "--framework", "cis", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["framework"] == "cis"
    assert "missing_controls" in data


def test_custom_crosswalk_override(tmp_path, capsys):
    cw = {
        "frameworks": {"nist": "NIST"},
        "mappings": [
            {"id": "C1", "topic": "T", "description": "d", "controls": {"nist": ["XX-1"]}}
        ],
    }
    p = tmp_path / "cw.json"
    p.write_text(json.dumps(cw), encoding="utf-8")
    rc = main(["--crosswalk", str(p), "map", "XX-1", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["matches"][0]["id"] == "C1"


def test_implemented_bare_mapping(tmp_path, capsys):
    # Accept a file that is a bare framework->controls object (no "implemented" key).
    p = tmp_path / "impl.json"
    p.write_text(json.dumps({"nist": ["AC-2"]}), encoding="utf-8")
    rc = main(["coverage", str(p), "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["frameworks"]["nist"]["satisfied"] >= 1


# ---- export formats (csv / markdown / format flag) ---------------------


def test_coverage_csv(capsys):
    rc = main(["coverage", EXAMPLE, "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert lines[0] == "framework,label,total,satisfied,percent"
    # one header + one row per framework (nist, cis, soc2)
    assert len(lines) == 4
    assert any(line.startswith("nist,") for line in lines[1:])


def test_coverage_markdown(capsys):
    rc = main(["coverage", EXAMPLE, "--format", "markdown"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Coverage report" in out
    assert "| Framework |" in out
    assert "| nist |" in out


def test_coverage_format_json_equals_json_flag(capsys):
    rc = main(["coverage", EXAMPLE, "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "frameworks" in data


def test_gaps_csv(capsys):
    rc = main(["gaps", EXAMPLE, "--framework", "soc2", "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert lines[0] == "framework,control,topic,mapping_id"
    assert len(lines) > 1
    assert all(line.startswith("soc2,") for line in lines[1:])


def test_gaps_markdown(capsys):
    rc = main(["gaps", EXAMPLE, "--framework", "soc2", "--format", "markdown"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Gap analysis" in out
    assert "| Control | Topic(s) |" in out


def test_format_conflicts_with_json_flag(capsys):
    rc = main(["coverage", EXAMPLE, "--json", "--format", "csv"])
    assert rc == 2
    assert "conflicts" in capsys.readouterr().err


def test_format_json_with_json_flag_agrees(capsys):
    # --json plus --format json is harmless (they agree).
    rc = main(["coverage", EXAMPLE, "--json", "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "frameworks" in data


def test_invalid_format_rejected(capsys):
    with pytest.raises(SystemExit) as e:
        main(["coverage", EXAMPLE, "--format", "xml"])
    assert e.value.code != 0

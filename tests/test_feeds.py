"""Tests for the edge/air-gap data-feed ingestion + enrichment layer.

These tests are strictly OFFLINE. They point ``COGNIS_FEEDS_CACHE`` at the
small trimmed fixtures committed under ``tests/fixtures/`` (real, trimmed
slices of the NIST OSCAL 800-53 rev5 catalog and the CTID ATT&CK<->800-53
mappings) and exercise every code path with ``offline=True`` / cache-only, so
the suite never touches the network.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from grcforge import datafeeds, enrich
from grcforge.cli import main
from grcforge.crosswalk import Crosswalk

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLE = str(Path(__file__).resolve().parent.parent / "examples" / "implemented.json")


@pytest.fixture(autouse=True)
def _offline_cache(monkeypatch):
    """Point the feed cache at the committed fixtures and hard-block sockets."""
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(FIXTURES))

    def _no_network(*a, **k):  # pragma: no cover - only fires on a bug
        raise AssertionError("network access attempted during an offline test")

    monkeypatch.setattr(socket, "socket", _no_network)
    # also block the high-level fetch as a second belt
    monkeypatch.setattr(datafeeds, "fetch", _no_network)


# ---- fixtures present + parseable -------------------------------------


def test_fixtures_exist():
    for fid in enrich.RELEVANT_FEEDS:
        assert (FIXTURES / f"{fid}.data").exists()
        assert (FIXTURES / f"{fid}.meta.json").exists()


def test_get_offline_oscal():
    doc = datafeeds.get("oscal-800-53-rev5-catalog", offline=True)
    assert "catalog" in doc
    assert doc["catalog"]["groups"]


def test_get_offline_mappings():
    doc = datafeeds.get("attack-nist-mappings", offline=True)
    assert doc["mapping_objects"]
    assert all(o["status"] == "complete" for o in doc["mapping_objects"])


# ---- id normalization join key ----------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AC-2", ("AC", 2, "")),
        ("ac-2", ("AC", 2, "")),
        ("AC-02", ("AC", 2, "")),
        ("AC-2(1)", ("AC", 2, "1")),
        ("ac-2.1", ("AC", 2, "1")),
        ("CIS 5.1", None),
        ("garbage", None),
    ],
)
def test_control_key(raw, expected):
    assert enrich.control_key(raw) == expected


# ---- real enrichment: OSCAL titles ------------------------------------


def test_oscal_titles_are_authoritative():
    titles = enrich.load_oscal_titles(offline=True)
    # AC-2's authoritative NIST title is "Account Management".
    assert titles[("AC", 2, "")]["title"] == "Account Management"
    assert titles[("AC", 2, "")]["family"] == "AC"
    assert titles[("IR", 4, "")]["title"]  # exists


def test_attack_mitigations_real_techniques():
    mitig = enrich.load_attack_mitigations(offline=True)
    ac2 = mitig[("AC", 2, "")]
    ids = {t["technique"] for t in ac2}
    # T1003 (OS Credential Dumping) is mitigated by AC-2 in the CTID mapping.
    assert "T1003" in ids
    assert all(t["technique"].startswith("T") for t in ac2)


# ---- end-to-end enrichment over the crosswalk -------------------------


def test_enrich_nist_controls():
    cw = Crosswalk.load()
    report = enrich.enrich_nist_controls(cw, offline=True)
    assert report["offline"] is True
    assert report["control_count"] > 0
    # every crosswalk NIST control resolved a real title from the OSCAL catalog
    assert report["titles_resolved"] == report["control_count"]
    assert report["threat_coverage"] > 0
    ac2 = next(c for c in report["controls"] if c["control"] == "AC-2")
    assert ac2["title"] == "Account Management"
    assert ac2["technique_count"] > 0


def test_threat_exposure_for_gaps():
    cw = Crosswalk.load()
    implemented = json.loads(Path(EXAMPLE).read_text(encoding="utf-8"))
    if isinstance(implemented, dict) and "implemented" in implemented:
        implemented = implemented["implemented"]
    report = enrich.threat_exposure_for_gaps(cw, implemented, "nist", offline=True)
    assert report["gap_count"] >= 0
    assert report["total_attack_techniques_exposed"] >= 0
    # detail is sorted by unmitigated count descending
    counts = [d["unmitigated_techniques"] for d in report["by_control"]]
    assert counts == sorted(counts, reverse=True)


# ---- CLI surface, offline ---------------------------------------------


def test_cli_feeds_list(capsys):
    rc = main(["feeds", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "oscal-800-53-rev5-catalog" in out
    assert "attack-nist-mappings" in out


def test_cli_feeds_get_offline(capsys):
    rc = main(["feeds", "get", "oscal-800-53-rev5-catalog", "--offline"])
    assert rc == 0
    assert "catalog" in capsys.readouterr().out


def test_cli_feeds_get_rejects_unlisted_feed(capsys):
    rc = main(["feeds", "get", "cisa-kev", "--offline"])
    assert rc == 2
    assert "not a feed this repo consumes" in capsys.readouterr().err


def test_cli_feeds_enrich_offline(capsys):
    rc = main(["feeds", "enrich", "--offline"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Account Management" in out


def test_cli_feeds_enrich_json(capsys):
    rc = main(["feeds", "enrich", "--offline", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["titles_resolved"] == data["control_count"]
    assert data["feeds"] == list(enrich.RELEVANT_FEEDS)


def test_cli_feeds_expose_offline(capsys):
    rc = main(["feeds", "expose", EXAMPLE, "--framework", "nist", "--offline", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "total_attack_techniques_exposed" in data

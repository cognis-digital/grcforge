"""Tests for the crosswalk engine: loading, lookups, coverage, gaps."""

from __future__ import annotations

import json

import pytest

from grcforge.crosswalk import Crosswalk, CrosswalkError, _normalize_control


# ---- fixtures ----------------------------------------------------------


@pytest.fixture
def builtin() -> Crosswalk:
    return Crosswalk.load()


SMALL = {
    "frameworks": {"nist": "NIST", "cis": "CIS"},
    "mappings": [
        {
            "id": "M1",
            "topic": "Accounts",
            "description": "account stuff",
            "controls": {"nist": ["AC-2"], "cis": ["CIS 5.1"]},
        },
        {
            "id": "M2",
            "topic": "MFA",
            "description": "mfa stuff",
            "controls": {"nist": ["IA-2"], "cis": ["CIS 6.3", "CIS 6.4"]},
        },
        {
            "id": "M3",
            "topic": "Physical",
            "description": "physical only nist",
            "controls": {"nist": ["PE-3"], "cis": []},
        },
    ],
}


@pytest.fixture
def small() -> Crosswalk:
    return Crosswalk.from_dict(SMALL)


# ---- loading -----------------------------------------------------------


def test_builtin_loads(builtin):
    assert builtin.frameworks
    assert len(builtin.mappings) >= 15
    assert "nist" in builtin.frameworks
    assert "cis" in builtin.frameworks
    assert "soc2" in builtin.frameworks


def test_load_from_file(tmp_path):
    p = tmp_path / "cw.json"
    p.write_text(json.dumps(SMALL), encoding="utf-8")
    cw = Crosswalk.load(p)
    assert len(cw.mappings) == 3


def test_load_missing_file(tmp_path):
    with pytest.raises(CrosswalkError, match="not found"):
        Crosswalk.load(tmp_path / "nope.json")


def test_load_bad_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(CrosswalkError, match="Invalid JSON"):
        Crosswalk.load(p)


def test_reject_missing_frameworks():
    with pytest.raises(CrosswalkError, match="frameworks"):
        Crosswalk.from_dict({"mappings": []})


def test_reject_duplicate_ids():
    data = {
        "frameworks": {"nist": "NIST"},
        "mappings": [
            {"id": "X", "controls": {"nist": ["AC-2"]}},
            {"id": "X", "controls": {"nist": ["AC-3"]}},
        ],
    }
    with pytest.raises(CrosswalkError, match="Duplicate"):
        Crosswalk.from_dict(data)


def test_reject_unknown_framework_in_mapping():
    data = {
        "frameworks": {"nist": "NIST"},
        "mappings": [{"id": "X", "controls": {"bogus": ["A"]}}],
    }
    with pytest.raises(CrosswalkError, match="unknown framework"):
        Crosswalk.from_dict(data)


def test_reject_non_string_control_ids():
    data = {
        "frameworks": {"nist": "NIST"},
        "mappings": [{"id": "X", "controls": {"nist": [123]}}],
    }
    with pytest.raises(CrosswalkError, match="list of strings"):
        Crosswalk.from_dict(data)


# ---- normalization -----------------------------------------------------


def test_normalize_control_case_and_space():
    assert _normalize_control("  cis  5.1 ") == "CIS 5.1"
    assert _normalize_control("ac-2") == "AC-2"


# ---- map / equivalents -------------------------------------------------


def test_find_by_control_case_insensitive(small):
    assert [m.id for m in small.find_by_control("ac-2")] == ["M1"]
    assert [m.id for m in small.find_by_control("AC-2")] == ["M1"]


def test_find_by_control_cross_framework(small):
    # Looking up the CIS id returns the same mapping that holds the NIST id.
    assert [m.id for m in small.find_by_control("CIS 5.1")] == ["M1"]


def test_find_by_control_no_match(small):
    assert small.find_by_control("ZZ-99") == []


def test_equivalents_structure(small):
    eq = small.equivalents("AC-2")
    assert eq["query"] == "AC-2"
    assert len(eq["matches"]) == 1
    m = eq["matches"][0]
    assert m["id"] == "M1"
    assert m["controls"]["cis"] == ["CIS 5.1"]
    assert "nist" in m["controls"] and "cis" in m["controls"]


def test_equivalents_empty(small):
    eq = small.equivalents("nope")
    assert eq["matches"] == []


# ---- list --------------------------------------------------------------


def test_controls_in_framework_distinct_and_ordered(small):
    assert small.controls_in_framework("nist") == ["AC-2", "IA-2", "PE-3"]
    assert small.controls_in_framework("cis") == ["CIS 5.1", "CIS 6.3", "CIS 6.4"]


def test_controls_in_framework_unknown(small):
    with pytest.raises(CrosswalkError, match="Unknown framework"):
        small.controls_in_framework("soc2")


# ---- coverage ----------------------------------------------------------


def test_coverage_full_nist(small):
    cov = small.coverage({"nist": ["AC-2", "IA-2", "PE-3"]})
    nist = cov["frameworks"]["nist"]
    assert nist["total"] == 3
    assert nist["satisfied"] == 3
    assert nist["percent"] == 100.0


def test_coverage_partial(small):
    cov = small.coverage({"nist": ["AC-2"]})
    nist = cov["frameworks"]["nist"]
    assert nist["satisfied"] == 1
    assert nist["total"] == 3
    assert nist["percent"] == round(100.0 / 3, 1)
    assert nist["satisfied_controls"] == ["AC-2"]


def test_coverage_cross_framework_credit(small):
    # Implementing the NIST control satisfies the mapping, which credits the
    # equivalent CIS control too.
    cov = small.coverage({"nist": ["AC-2"]})
    cis = cov["frameworks"]["cis"]
    assert "CIS 5.1" in cis["satisfied_controls"]


def test_coverage_satisfied_mappings(small):
    cov = small.coverage({"cis": ["CIS 6.3"]})
    assert "M2" in cov["satisfied_mappings"]
    assert cov["total_mappings"] == 3


def test_coverage_empty_implemented(small):
    cov = small.coverage({})
    for fw in cov["frameworks"].values():
        assert fw["satisfied"] == 0
        assert fw["percent"] == 0.0


def test_coverage_rejects_unknown_framework(small):
    with pytest.raises(CrosswalkError, match="unknown framework"):
        small.coverage({"soc2": ["CC6.1"]})


def test_coverage_rejects_bad_type(small):
    with pytest.raises(CrosswalkError):
        small.coverage(["not", "a", "dict"])


# ---- gaps --------------------------------------------------------------


def test_gaps_basic(small):
    g = small.gaps({"nist": ["AC-2"]}, "nist")
    assert g["framework"] == "nist"
    assert g["total"] == 3
    assert g["covered"] == 1
    assert g["gaps"] == 2
    missing = [m["control"] for m in g["missing_controls"]]
    assert "IA-2" in missing and "PE-3" in missing
    assert "AC-2" not in missing


def test_gaps_none_when_full(small):
    g = small.gaps({"cis": ["CIS 5.1", "CIS 6.3", "CIS 6.4"]}, "cis")
    assert g["gaps"] == 0
    assert g["missing_controls"] == []


def test_gaps_detail_carries_topics(small):
    g = small.gaps({}, "cis")
    detail = {d["control"]: d for d in g["missing_controls"]}
    assert detail["CIS 5.1"]["mappings"][0]["topic"] == "Accounts"


def test_gaps_unknown_framework(small):
    with pytest.raises(CrosswalkError, match="Unknown framework"):
        small.gaps({}, "bogus")


# ---- builtin sanity ----------------------------------------------------


def test_builtin_map_ac2(builtin):
    eq = builtin.equivalents("AC-2")
    assert eq["matches"], "AC-2 should map to at least one topic"
    # AC-2 should co-occur with a CIS account-management safeguard.
    all_cis = set()
    for m in eq["matches"]:
        all_cis.update(m["controls"].get("cis", []))
    assert any(c.startswith("CIS 5") for c in all_cis)


def test_builtin_coverage_runs(builtin):
    impl = {"nist": ["AC-2", "IA-2"], "cis": ["CIS 5.1"]}
    cov = builtin.coverage(impl)
    assert cov["frameworks"]["nist"]["satisfied"] >= 2
    assert cov["total_mappings"] == len(builtin.mappings)

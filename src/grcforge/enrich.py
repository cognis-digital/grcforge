"""grcforge.enrich — real feed-driven enrichment for the crosswalk engine.

This is the bridge between grcforge's framework-agnostic crosswalk model and two
authoritative, keyless, **edge/air-gap-deployable** data feeds (see
``data_feeds_2026.json`` and ``datafeeds.py`` bundled alongside this module):

  * ``oscal-800-53-rev5-catalog`` — NIST's own OSCAL JSON release of the
    SP 800-53 Rev. 5 control catalog. Used to resolve the bare control ids in a
    crosswalk (``AC-2``, ``IR-4``, ...) into their **authoritative control
    titles** and owning family, straight from NIST.

  * ``attack-nist-mappings`` — the Center for Threat-Informed Defense (CTID)
    Mappings Explorer crosswalk of MITRE ATT&CK techniques to the 800-53 Rev. 5
    controls that *mitigate* them. Used to attach the **real adversary
    techniques** each control defends against, so a GRC gap turns into a
    concrete threat-exposure statement ("this unimplemented control leaves N
    ATT&CK techniques unmitigated").

Both feeds are consumed through the bundled ``datafeeds`` module, so the same
disk-cache / ``offline=True`` / snapshot machinery applies: this enrichment runs
on disconnected gear once the cache (or a sneakernet snapshot) is in place.

Defensive / authorized-use intelligence only.

Note on id normalization: the three sources spell the *same* control three ways
— the crosswalk uses ``AC-2``, OSCAL uses ``ac-2``, and the CTID mappings use a
zero-padded ``AC-02``. ``control_key`` collapses all three to a single
comparable key so the data actually joins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from . import datafeeds
from .crosswalk import Crosswalk

# The only feed ids this repo is authorized to consume. Anything else is a bug.
RELEVANT_FEEDS = ("oscal-800-53-rev5-catalog", "attack-nist-mappings")


def control_key(control_id: str) -> Optional[tuple[str, int, str]]:
    """Collapse AC-2 / ac-2 / AC-02 / AC-2(1) to a single comparable key.

    Returns ``(FAMILY, number, enhancement)`` e.g. ``("AC", 2, "")`` or
    ``("AC", 2, "1")`` for the enhancement ``AC-2(1)``. Returns ``None`` for a
    string that does not look like an 800-53 control id.
    """
    s = str(control_id).strip().upper().replace(" ", "")
    if "-" not in s:
        return None
    fam, _, rest = s.partition("-")
    if not fam.isalpha():
        return None
    enh = ""
    # enhancement forms: AC-2(1)  or OSCAL  ac-2.1
    if "(" in rest:
        rest, _, tail = rest.partition("(")
        enh = tail.rstrip(")")
    elif "." in rest:
        rest, _, enh = rest.partition(".")
    if not rest.isdigit():
        return None
    return (fam, int(rest), enh)


# --------------------------------------------------------------------------- #
# OSCAL 800-53 rev5 catalog -> authoritative control titles
# --------------------------------------------------------------------------- #
def load_oscal_titles(*, offline: bool = False, cache_catalog: Optional[dict] = None) -> dict[tuple, dict]:
    """Return ``{control_key: {"id", "title", "family", "family_title"}}``.

    Pulls the NIST OSCAL SP 800-53 Rev. 5 catalog through the bundled feed
    (cache/offline aware) and walks its groups -> controls (and control
    enhancements) to extract authoritative titles.
    """
    doc = datafeeds.get("oscal-800-53-rev5-catalog", offline=offline, catalog=cache_catalog)
    catalog = doc.get("catalog", doc)
    out: dict[tuple, dict] = {}

    def _ingest(ctrl: dict, fam_id: str, fam_title: str) -> None:
        key = control_key(ctrl.get("id", ""))
        if key is not None:
            out[key] = {
                "id": ctrl.get("id", "").upper(),
                "title": ctrl.get("title", ""),
                "family": fam_id.upper(),
                "family_title": fam_title,
            }
        for child in ctrl.get("controls", []) or []:  # control enhancements
            _ingest(child, fam_id, fam_title)

    for group in catalog.get("groups", []) or []:
        fam_id = group.get("id", "")
        fam_title = group.get("title", "")
        for ctrl in group.get("controls", []) or []:
            _ingest(ctrl, fam_id, fam_title)
    return out


# --------------------------------------------------------------------------- #
# CTID ATT&CK <-> 800-53 mappings -> techniques mitigated by each control
# --------------------------------------------------------------------------- #
def load_attack_mitigations(*, offline: bool = False, cache_catalog: Optional[dict] = None) -> dict[tuple, list[dict]]:
    """Return ``{control_key: [{"technique", "name"}, ...]}``.

    Only ``status == "complete"`` "mitigates" rows are kept — the CTID feed also
    carries ``non_mappable`` placeholder rows which carry no real mapping.
    """
    doc = datafeeds.get("attack-nist-mappings", offline=offline, catalog=cache_catalog)
    objs = doc.get("mapping_objects") or doc.get("mappings") or []
    out: dict[tuple, list[dict]] = {}
    seen: dict[tuple, set[str]] = {}
    for o in objs:
        if o.get("status") != "complete":
            continue
        key = control_key(o.get("capability_id", ""))
        if key is None:
            continue
        # join at the base-control level (drop enhancement) so AC-2(1) rolls into AC-2
        base = (key[0], key[1], "")
        tid = o.get("attack_object_id", "")
        if not tid:
            continue
        s = seen.setdefault(base, set())
        if tid in s:
            continue
        s.add(tid)
        out.setdefault(base, []).append(
            {"technique": tid, "name": o.get("attack_object_name", "")}
        )
    for lst in out.values():
        lst.sort(key=lambda r: r["technique"])
    return out


# --------------------------------------------------------------------------- #
# Enrichment: join the crosswalk's NIST controls to both feeds
# --------------------------------------------------------------------------- #
def enrich_nist_controls(
    cw: Crosswalk,
    *,
    framework: str = "nist",
    offline: bool = False,
    cache_catalog: Optional[dict] = None,
) -> dict:
    """Enrich every NIST control referenced by a crosswalk with feed data.

    For each distinct control id in ``framework`` we attach:
      * ``title`` / ``family`` / ``family_title`` from the NIST OSCAL catalog
      * ``attack_techniques`` (id + name) that the control mitigates per CTID

    Returns a structured report; ``threat_coverage`` is the total count of
    distinct ATT&CK techniques mitigated by the crosswalk's NIST controls.
    """
    titles = load_oscal_titles(offline=offline, cache_catalog=cache_catalog)
    mitig = load_attack_mitigations(offline=offline, cache_catalog=cache_catalog)

    controls = cw.controls_in_framework(framework)
    enriched: list[dict] = []
    all_techniques: set[str] = set()
    resolved = 0
    for cid in controls:
        key = control_key(cid)
        base = (key[0], key[1], "") if key else None
        meta = titles.get(key) or (titles.get(base) if base else None) or {}
        techs = mitig.get(base, []) if base else []
        if meta.get("title"):
            resolved += 1
        for t in techs:
            all_techniques.add(t["technique"])
        enriched.append(
            {
                "control": cid,
                "title": meta.get("title", ""),
                "family": meta.get("family", ""),
                "family_title": meta.get("family_title", ""),
                "attack_techniques": techs,
                "technique_count": len(techs),
            }
        )

    return {
        "framework": framework,
        "controls": enriched,
        "control_count": len(enriched),
        "titles_resolved": resolved,
        "threat_coverage": len(all_techniques),
        "feeds": list(RELEVANT_FEEDS),
        "offline": offline,
    }


def threat_exposure_for_gaps(
    cw: Crosswalk,
    implemented: dict[str, list[str]],
    framework: str = "nist",
    *,
    offline: bool = False,
    cache_catalog: Optional[dict] = None,
) -> dict:
    """Turn an unmapped-control gap report into a real ATT&CK threat-exposure
    statement: which adversary techniques are left unmitigated by each gap.

    This is the load-bearing enrichment — it joins grcforge's existing gap
    analysis to the CTID ATT&CK mappings so a finding reads
    "AC-2 (Account Management) is not implemented -> 187 ATT&CK techniques
    unmitigated", instead of a bare control id.
    """
    gaps = cw.gaps(implemented, framework)
    mitig = load_attack_mitigations(offline=offline, cache_catalog=cache_catalog)
    titles = load_oscal_titles(offline=offline, cache_catalog=cache_catalog)

    exposed: set[str] = set()
    detail: list[dict] = []
    for gap in gaps["missing_controls"]:
        cid = gap["control"]
        key = control_key(cid)
        base = (key[0], key[1], "") if key else None
        techs = mitig.get(base, []) if base else []
        meta = titles.get(key) or (titles.get(base) if base else None) or {}
        for t in techs:
            exposed.add(t["technique"])
        detail.append(
            {
                "control": cid,
                "title": meta.get("title", ""),
                "unmitigated_techniques": len(techs),
                "techniques": [t["technique"] for t in techs],
            }
        )
    detail.sort(key=lambda d: d["unmitigated_techniques"], reverse=True)
    return {
        "framework": gaps["framework"],
        "gap_count": gaps["gaps"],
        "total_attack_techniques_exposed": len(exposed),
        "by_control": detail,
        "offline": offline,
    }

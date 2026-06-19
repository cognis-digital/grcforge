"""Crosswalk data model and analysis engine for grcforge.

Standard library only. All logic here is framework-agnostic: it operates on a
crosswalk document (a set of topical mappings, each pointing at one or more
control identifiers per framework).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_CROSSWALK = DATA_DIR / "crosswalk.json"


class CrosswalkError(Exception):
    """Raised when a crosswalk document is malformed or a query is invalid."""


@dataclass
class Mapping:
    """A single topical mapping across frameworks."""

    id: str
    topic: str
    description: str
    controls: dict[str, list[str]] = field(default_factory=dict)

    def controls_for(self, framework: str) -> list[str]:
        return list(self.controls.get(framework, []))

    def all_control_ids(self) -> list[str]:
        out: list[str] = []
        for ids in self.controls.values():
            out.extend(ids)
        return out


@dataclass
class Crosswalk:
    """An in-memory crosswalk document with lookup and analysis helpers."""

    frameworks: dict[str, str]
    mappings: list[Mapping]
    meta: dict = field(default_factory=dict)

    # ---- construction -------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "Crosswalk":
        if not isinstance(data, dict):
            raise CrosswalkError("Crosswalk root must be an object.")
        frameworks = data.get("frameworks")
        if not isinstance(frameworks, dict) or not frameworks:
            raise CrosswalkError("Crosswalk must define a non-empty 'frameworks' object.")
        raw_mappings = data.get("mappings")
        if not isinstance(raw_mappings, list):
            raise CrosswalkError("Crosswalk must define a 'mappings' list.")

        mappings: list[Mapping] = []
        seen_ids: set[str] = set()
        for i, raw in enumerate(raw_mappings):
            if not isinstance(raw, dict):
                raise CrosswalkError(f"Mapping at index {i} must be an object.")
            mid = raw.get("id")
            if not mid or not isinstance(mid, str):
                raise CrosswalkError(f"Mapping at index {i} is missing a string 'id'.")
            if mid in seen_ids:
                raise CrosswalkError(f"Duplicate mapping id: {mid}")
            seen_ids.add(mid)
            controls = raw.get("controls", {})
            if not isinstance(controls, dict):
                raise CrosswalkError(f"Mapping {mid} 'controls' must be an object.")
            norm_controls: dict[str, list[str]] = {}
            for fw, ids in controls.items():
                if fw not in frameworks:
                    raise CrosswalkError(
                        f"Mapping {mid} references unknown framework '{fw}'."
                    )
                if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
                    raise CrosswalkError(
                        f"Mapping {mid} controls for '{fw}' must be a list of strings."
                    )
                norm_controls[fw] = list(ids)
            mappings.append(
                Mapping(
                    id=mid,
                    topic=raw.get("topic", ""),
                    description=raw.get("description", ""),
                    controls=norm_controls,
                )
            )
        return cls(frameworks=frameworks, mappings=mappings, meta=data.get("meta", {}))

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Crosswalk":
        target = Path(path) if path else DEFAULT_CROSSWALK
        if not target.exists():
            raise CrosswalkError(f"Crosswalk file not found: {target}")
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CrosswalkError(f"Invalid JSON in {target}: {exc}") from exc
        return cls.from_dict(data)

    # ---- queries ------------------------------------------------------

    def framework_ids(self) -> list[str]:
        return list(self.frameworks.keys())

    def require_framework(self, framework: str) -> str:
        fw = framework.lower()
        if fw not in self.frameworks:
            known = ", ".join(self.frameworks)
            raise CrosswalkError(
                f"Unknown framework '{framework}'. Known frameworks: {known}"
            )
        return fw

    def find_by_control(self, control_id: str) -> list[Mapping]:
        """Return mappings whose control set contains the given identifier.

        Matching is case-insensitive and whitespace-tolerant.
        """
        needle = _normalize_control(control_id)
        out: list[Mapping] = []
        for m in self.mappings:
            for ids in m.controls.values():
                if any(_normalize_control(c) == needle for c in ids):
                    out.append(m)
                    break
        return out

    def controls_in_framework(self, framework: str) -> list[str]:
        """All distinct control identifiers used for a framework, in order."""
        fw = self.require_framework(framework)
        seen: set[str] = set()
        out: list[str] = []
        for m in self.mappings:
            for c in m.controls.get(fw, []):
                key = _normalize_control(c)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
        return out

    # ---- analysis -----------------------------------------------------

    def equivalents(self, control_id: str) -> dict:
        """Cross-framework equivalents for a control identifier.

        Returns a dict keyed by mapping id; each value carries the topic,
        description, and the per-framework control identifiers.
        """
        matches = self.find_by_control(control_id)
        result = {
            "query": control_id,
            "matches": [
                {
                    "id": m.id,
                    "topic": m.topic,
                    "description": m.description,
                    "controls": {fw: m.controls.get(fw, []) for fw in self.frameworks},
                }
                for m in matches
            ],
        }
        return result

    def coverage(self, implemented: dict[str, list[str]]) -> dict:
        """Compute framework coverage from the controls an org has implemented.

        ``implemented`` maps framework id -> list of implemented control ids.
        A framework's control is 'satisfied' when at least one mapping that
        references it has any implemented control in the SAME framework, OR an
        implemented control elsewhere that shares a mapping (cross-coverage).
        We report per-framework totals and the satisfied subset.
        """
        impl_norm = self._normalize_implemented(implemented)

        # Which mappings are considered "implemented" — a mapping is satisfied
        # if any of its control ids (in any framework) is implemented.
        satisfied_mappings: set[str] = set()
        for m in self.mappings:
            for fw, ids in m.controls.items():
                if any(_normalize_control(c) in impl_norm.get(fw, set()) for c in ids):
                    satisfied_mappings.add(m.id)
                    break

        per_framework: dict[str, dict] = {}
        for fw in self.frameworks:
            total_controls = self.controls_in_framework(fw)
            total_norm = [_normalize_control(c) for c in total_controls]
            satisfied: list[str] = []
            for orig, norm in zip(total_controls, total_norm):
                # control satisfied if any mapping containing it is satisfied
                for m in self.mappings:
                    if m.id not in satisfied_mappings:
                        continue
                    if norm in [_normalize_control(c) for c in m.controls.get(fw, [])]:
                        satisfied.append(orig)
                        break
            total = len(total_controls)
            count = len(satisfied)
            per_framework[fw] = {
                "total": total,
                "satisfied": count,
                "percent": round(100.0 * count / total, 1) if total else 0.0,
                "satisfied_controls": satisfied,
            }

        return {
            "frameworks": per_framework,
            "satisfied_mappings": sorted(satisfied_mappings),
            "total_mappings": len(self.mappings),
        }

    def gaps(self, implemented: dict[str, list[str]], framework: str) -> dict:
        """Identify framework control identifiers that are not yet satisfied."""
        fw = self.require_framework(framework)
        cov = self.coverage(implemented)
        fw_cov = cov["frameworks"][fw]
        satisfied_norm = {_normalize_control(c) for c in fw_cov["satisfied_controls"]}
        all_controls = self.controls_in_framework(fw)
        unmapped = [c for c in all_controls if _normalize_control(c) not in satisfied_norm]

        # For each gap, surface the mapping topics it belongs to (helps remediation).
        gap_detail = []
        for c in unmapped:
            norm = _normalize_control(c)
            topics = [
                {"id": m.id, "topic": m.topic}
                for m in self.mappings
                if norm in [_normalize_control(x) for x in m.controls.get(fw, [])]
            ]
            gap_detail.append({"control": c, "mappings": topics})

        return {
            "framework": fw,
            "total": len(all_controls),
            "gaps": len(unmapped),
            "covered": len(all_controls) - len(unmapped),
            "missing_controls": gap_detail,
        }

    # ---- helpers ------------------------------------------------------

    def _normalize_implemented(
        self, implemented: dict[str, list[str]]
    ) -> dict[str, set[str]]:
        if not isinstance(implemented, dict):
            raise CrosswalkError(
                "Implemented controls must be an object mapping framework -> [control ids]."
            )
        out: dict[str, set[str]] = {}
        for fw, ids in implemented.items():
            fw_l = fw.lower()
            if fw_l not in self.frameworks:
                raise CrosswalkError(
                    f"Implemented set references unknown framework '{fw}'."
                )
            if not isinstance(ids, list):
                raise CrosswalkError(
                    f"Implemented controls for '{fw}' must be a list."
                )
            out[fw_l] = {_normalize_control(str(c)) for c in ids}
        return out


def _normalize_control(control_id: str) -> str:
    """Normalize a control identifier for tolerant comparison."""
    return " ".join(str(control_id).strip().upper().split())

"""Command-line interface for grcforge.

Subcommands:
  map <control-id>            Show cross-framework equivalents for a control.
  coverage <implemented.json> Report framework coverage from implemented controls.
  gaps <implemented.json>     List unmapped requirements for a framework.
  list                        List the control identifiers in a framework.

Standard library only (argparse + json).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .crosswalk import Crosswalk, CrosswalkError


def _load_crosswalk(args: argparse.Namespace) -> Crosswalk:
    return Crosswalk.load(getattr(args, "crosswalk", None))


def _load_implemented(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise CrosswalkError(f"Implemented controls file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CrosswalkError(f"Invalid JSON in {p}: {exc}") from exc
    # Allow either a bare mapping or {"implemented": {...}}.
    if isinstance(data, dict) and "implemented" in data:
        data = data["implemented"]
    return data


def _emit_json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---- command handlers --------------------------------------------------


def cmd_map(args: argparse.Namespace) -> int:
    cw = _load_crosswalk(args)
    result = cw.equivalents(args.control_id)
    if args.json:
        _emit_json(result)
        return 0
    matches = result["matches"]
    if not matches:
        print(f"No mapping found for control '{args.control_id}'.")
        return 1
    print(f"Equivalents for '{args.control_id}':\n")
    for m in matches:
        print(f"  [{m['id']}] {m['topic']}")
        print(f"      {m['description']}")
        for fw in cw.framework_ids():
            ids = m["controls"].get(fw, [])
            label = cw.frameworks.get(fw, fw)
            shown = ", ".join(ids) if ids else "(none)"
            print(f"      - {fw} ({label}): {shown}")
        print()
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    cw = _load_crosswalk(args)
    implemented = _load_implemented(args.implemented)
    result = cw.coverage(implemented)
    if args.json:
        _emit_json(result)
        return 0
    print(
        f"Coverage report ({result['total_mappings']} mappings, "
        f"{len(result['satisfied_mappings'])} satisfied)\n"
    )
    for fw, info in result["frameworks"].items():
        label = cw.frameworks.get(fw, fw)
        print(
            f"  {fw} ({label}): {info['satisfied']}/{info['total']} "
            f"controls = {info['percent']}%"
        )
        if args.verbose and info["satisfied_controls"]:
            print("      satisfied: " + ", ".join(info["satisfied_controls"]))
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    cw = _load_crosswalk(args)
    implemented = _load_implemented(args.implemented)
    result = cw.gaps(implemented, args.framework)
    if args.json:
        _emit_json(result)
        return 0
    fw = result["framework"]
    label = cw.frameworks.get(fw, fw)
    print(
        f"Gap analysis for {fw} ({label}): "
        f"{result['gaps']} unmapped of {result['total']} "
        f"({result['covered']} covered)\n"
    )
    if not result["missing_controls"]:
        print("  No gaps — all known controls in this framework are satisfied.")
        return 0
    for gap in result["missing_controls"]:
        topics = "; ".join(t["topic"] for t in gap["mappings"]) or "(no topic)"
        print(f"  - {gap['control']}: {topics}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    cw = _load_crosswalk(args)
    if args.framework:
        controls = cw.controls_in_framework(args.framework)
        fw = cw.require_framework(args.framework)
        if args.json:
            _emit_json({"framework": fw, "controls": controls})
            return 0
        label = cw.frameworks.get(fw, fw)
        print(f"{fw} ({label}) — {len(controls)} controls:\n")
        for c in controls:
            print(f"  {c}")
        return 0
    # No framework: list all frameworks and mapping count.
    if args.json:
        _emit_json(
            {
                "frameworks": cw.frameworks,
                "mappings": [
                    {"id": m.id, "topic": m.topic} for m in cw.mappings
                ],
            }
        )
        return 0
    print("Frameworks:")
    for fw, label in cw.frameworks.items():
        n = len(cw.controls_in_framework(fw))
        print(f"  {fw}: {label} ({n} controls)")
    print(f"\nMappings ({len(cw.mappings)}):")
    for m in cw.mappings:
        print(f"  [{m.id}] {m.topic}")
    return 0


# ---- parser ------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grcforge",
        description="GRC control crosswalk engine: map controls across "
        "frameworks, measure coverage, and find gaps.",
    )
    parser.add_argument(
        "--version", action="version", version=f"grcforge {__version__}"
    )
    parser.add_argument(
        "--crosswalk",
        metavar="FILE",
        help="Path to a crosswalk JSON file (overrides the built-in starter).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_map = sub.add_parser("map", help="Show cross-framework equivalents.")
    p_map.add_argument("control_id", help="Control identifier, e.g. AC-2 or 'CIS 5.1'.")
    p_map.add_argument("--json", action="store_true", help="Emit JSON.")
    p_map.set_defaults(func=cmd_map)

    p_cov = sub.add_parser("coverage", help="Report framework coverage.")
    p_cov.add_argument("implemented", help="Path to implemented-controls JSON.")
    p_cov.add_argument("--json", action="store_true", help="Emit JSON.")
    p_cov.add_argument(
        "--verbose", action="store_true", help="List satisfied controls per framework."
    )
    p_cov.set_defaults(func=cmd_coverage)

    p_gap = sub.add_parser("gaps", help="List unmapped requirements for a framework.")
    p_gap.add_argument("implemented", help="Path to implemented-controls JSON.")
    p_gap.add_argument(
        "--framework", required=True, help="Framework id, e.g. nist, cis, soc2."
    )
    p_gap.add_argument("--json", action="store_true", help="Emit JSON.")
    p_gap.set_defaults(func=cmd_gaps)

    p_list = sub.add_parser("list", help="List frameworks or controls in a framework.")
    p_list.add_argument(
        "--framework", help="Framework id; omit to list all frameworks."
    )
    p_list.add_argument("--json", action="store_true", help="Emit JSON.")
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CrosswalkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

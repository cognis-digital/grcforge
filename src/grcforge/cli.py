"""Command-line interface for grcforge.

Subcommands:
  map <control-id>            Show cross-framework equivalents for a control.
  coverage <implemented.json> Report framework coverage from implemented controls.
  gaps <implemented.json>     List unmapped requirements for a framework.
  list                        List the control identifiers in a framework.
  feeds list|update|get|enrich|expose   Edge/air-gap data-feed ingestion + enrichment.

Standard library only (argparse + json).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from . import __version__, datafeeds, enrich
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


def _resolve_format(args: argparse.Namespace) -> str:
    """Decide the output format from --format / legacy --json.

    --json is kept as a backward-compatible alias for --format json. If both
    are given they must agree, otherwise it is a usage error.
    """
    fmt = getattr(args, "format", None)
    legacy_json = getattr(args, "json", False)
    if legacy_json:
        if fmt and fmt != "json":
            raise CrosswalkError(
                f"--json conflicts with --format {fmt}; pass only one."
            )
        return "json"
    return fmt or "table"


def _coverage_csv(result: dict, cw: Crosswalk) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["framework", "label", "total", "satisfied", "percent"])
    for fw, info in result["frameworks"].items():
        w.writerow(
            [
                fw,
                cw.frameworks.get(fw, fw),
                info["total"],
                info["satisfied"],
                info["percent"],
            ]
        )
    return buf.getvalue()


def _coverage_markdown(result: dict, cw: Crosswalk) -> str:
    lines = [
        f"# Coverage report",
        "",
        f"- Mappings: **{result['total_mappings']}**",
        f"- Satisfied mappings: **{len(result['satisfied_mappings'])}**",
        "",
        "| Framework | Label | Satisfied | Total | Percent |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for fw, info in result["frameworks"].items():
        label = cw.frameworks.get(fw, fw)
        lines.append(
            f"| {fw} | {label} | {info['satisfied']} | {info['total']} | "
            f"{info['percent']}% |"
        )
    return "\n".join(lines) + "\n"


def _gaps_csv(result: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["framework", "control", "topic", "mapping_id"])
    fw = result["framework"]
    for gap in result["missing_controls"]:
        if gap["mappings"]:
            for mp in gap["mappings"]:
                w.writerow([fw, gap["control"], mp["topic"], mp["id"]])
        else:
            w.writerow([fw, gap["control"], "", ""])
    return buf.getvalue()


def _gaps_markdown(result: dict, cw: Crosswalk) -> str:
    fw = result["framework"]
    label = cw.frameworks.get(fw, fw)
    lines = [
        f"# Gap analysis — {fw} ({label})",
        "",
        f"- Unmapped: **{result['gaps']}** of {result['total']} "
        f"({result['covered']} covered)",
        "",
        "| Control | Topic(s) |",
        "| --- | --- |",
    ]
    for gap in result["missing_controls"]:
        topics = "; ".join(t["topic"] for t in gap["mappings"]) or "(no topic)"
        lines.append(f"| {gap['control']} | {topics} |")
    return "\n".join(lines) + "\n"


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
    fmt = _resolve_format(args)
    if fmt == "json":
        _emit_json(result)
        return 0
    if fmt == "csv":
        sys.stdout.write(_coverage_csv(result, cw))
        return 0
    if fmt == "markdown":
        sys.stdout.write(_coverage_markdown(result, cw))
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
    fmt = _resolve_format(args)
    if fmt == "json":
        _emit_json(result)
        return 0
    if fmt == "csv":
        sys.stdout.write(_gaps_csv(result))
        return 0
    if fmt == "markdown":
        sys.stdout.write(_gaps_markdown(result, cw))
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


# ---- data-feed ingestion + enrichment ---------------------------------


def _feed_catalog() -> dict:
    """Catalog restricted to the feed ids this repo is authorized to consume."""
    full = datafeeds.load_catalog()
    feeds = [f for f in full.get("feeds", []) if f["id"] in enrich.RELEVANT_FEEDS]
    return {"feeds": feeds}


def cmd_feeds(args: argparse.Namespace) -> int:
    catalog = _feed_catalog()
    action = args.feeds_action

    if action == "list":
        for f in catalog["feeds"]:
            age = datafeeds.cached_age_hours(f["id"])
            fresh = "uncached" if age is None else f"{age:.1f}h old"
            print(f"  {f['id']:30} {f.get('domain',''):11} [{fresh}]  {f.get('name','')}")
        return 0

    if action == "update":
        ids = args.ids or [f["id"] for f in catalog["feeds"]]
        for fid in ids:
            if fid not in enrich.RELEVANT_FEEDS:
                print(f"  {fid}: not a feed this repo consumes", file=sys.stderr)
                continue
            try:
                p = datafeeds.update(fid, catalog=catalog)
                print(f"  updated {fid} -> {p} ({p.stat().st_size} bytes)")
            except (KeyError, ConnectionError) as e:
                print(f"  {fid}: {e}", file=sys.stderr)
        return 0

    if action == "get":
        if args.id not in enrich.RELEVANT_FEEDS:
            print(f"error: {args.id} is not a feed this repo consumes "
                  f"(allowed: {', '.join(enrich.RELEVANT_FEEDS)})", file=sys.stderr)
            return 2
        try:
            data = datafeeds.get(args.id, offline=args.offline, catalog=catalog)
        except (KeyError, FileNotFoundError, ConnectionError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        out = json.dumps(data, indent=2)[:4000] if isinstance(data, (dict, list)) else str(data)[:4000]
        print(out)
        return 0

    if action == "enrich":
        cw = _load_crosswalk(args)
        report = enrich.enrich_nist_controls(cw, offline=args.offline)
        if args.json:
            _emit_json(report)
            return 0
        print(f"NIST 800-53 control enrichment (offline={report['offline']}) — "
              f"{report['titles_resolved']}/{report['control_count']} titles resolved, "
              f"{report['threat_coverage']} ATT&CK techniques mitigated\n")
        for c in report["controls"]:
            title = c["title"] or "(title not in cached catalog)"
            print(f"  {c['control']:8} {title}")
            if c["family_title"]:
                print(f"           family: {c['family']} — {c['family_title']}")
            print(f"           mitigates {c['technique_count']} ATT&CK technique(s)")
        return 0

    if action == "expose":
        cw = _load_crosswalk(args)
        implemented = _load_implemented(args.implemented)
        report = enrich.threat_exposure_for_gaps(cw, implemented, args.framework,
                                                 offline=args.offline)
        if args.json:
            _emit_json(report)
            return 0
        print(f"ATT&CK threat exposure for {report['framework']} gaps "
              f"(offline={report['offline']}): {report['gap_count']} unmapped controls "
              f"leave {report['total_attack_techniques_exposed']} ATT&CK techniques "
              f"unmitigated\n")
        for d in report["by_control"]:
            title = d["title"] or ""
            print(f"  {d['control']:8} {title}")
            print(f"           {d['unmitigated_techniques']} unmitigated technique(s)")
        return 0

    return 2


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
    p_cov.add_argument(
        "--format",
        choices=["table", "json", "csv", "markdown"],
        help="Output format (default: table).",
    )
    p_cov.add_argument(
        "--json", action="store_true", help="Alias for --format json."
    )
    p_cov.add_argument(
        "--verbose", action="store_true", help="List satisfied controls per framework."
    )
    p_cov.set_defaults(func=cmd_coverage)

    p_gap = sub.add_parser("gaps", help="List unmapped requirements for a framework.")
    p_gap.add_argument("implemented", help="Path to implemented-controls JSON.")
    p_gap.add_argument(
        "--framework", required=True, help="Framework id, e.g. nist, cis, soc2."
    )
    p_gap.add_argument(
        "--format",
        choices=["table", "json", "csv", "markdown"],
        help="Output format (default: table).",
    )
    p_gap.add_argument(
        "--json", action="store_true", help="Alias for --format json."
    )
    p_gap.set_defaults(func=cmd_gaps)

    p_list = sub.add_parser("list", help="List frameworks or controls in a framework.")
    p_list.add_argument(
        "--framework", help="Framework id; omit to list all frameworks."
    )
    p_list.add_argument("--json", action="store_true", help="Emit JSON.")
    p_list.set_defaults(func=cmd_list)

    # feeds: edge/air-gap data-feed ingestion + real enrichment
    p_feeds = sub.add_parser(
        "feeds",
        help="Edge/air-gap data-feed ingestion (NIST OSCAL + ATT&CK mappings) "
        "and enrichment.",
    )
    p_feeds.set_defaults(func=cmd_feeds)
    fsub = p_feeds.add_subparsers(dest="feeds_action", required=True)

    fsub.add_parser("list", help="List the data feeds this repo consumes.")

    f_up = fsub.add_parser("update", help="Fetch + cache feed(s) (online).")
    f_up.add_argument("ids", nargs="*", help="Feed id(s); omit for all relevant feeds.")

    f_get = fsub.add_parser("get", help="Print a cached/fetched feed.")
    f_get.add_argument("id", help=f"One of: {', '.join(enrich.RELEVANT_FEEDS)}")
    f_get.add_argument("--offline", action="store_true",
                       help="Serve from cache only; never touch the network.")

    f_en = fsub.add_parser(
        "enrich",
        help="Resolve the crosswalk's NIST controls to authoritative OSCAL "
        "titles + the ATT&CK techniques they mitigate.",
    )
    f_en.add_argument("--offline", action="store_true", help="Cache-only.")
    f_en.add_argument("--json", action="store_true", help="Emit JSON.")

    f_ex = fsub.add_parser(
        "expose",
        help="Turn an unmapped-control gap report into a real ATT&CK "
        "threat-exposure statement.",
    )
    f_ex.add_argument("implemented", help="Path to implemented-controls JSON.")
    f_ex.add_argument("--framework", default="nist", help="Framework id (default: nist).")
    f_ex.add_argument("--offline", action="store_true", help="Cache-only.")
    f_ex.add_argument("--json", action="store_true", help="Emit JSON.")

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

# grcforge

A small, dependency-free **GRC control crosswalk engine**. Map a security or
compliance control to its equivalents across frameworks, measure how much
framework coverage your implemented controls give you, and find the
requirements you have not yet satisfied.

grcforge ships with an original starter crosswalk spanning three common
frameworks:

- **NIST SP 800-53 Rev. 5** control families
- **CIS Critical Security Controls v8** safeguards
- **AICPA SOC 2** Trust Services Criteria (Common Criteria)

The crosswalk is data-driven. Control *identifiers* (e.g. `AC-2`, `CIS 5.1`,
`CC6.1`) are factual references to public frameworks; every descriptive line in
the bundled crosswalk is written from scratch by Cognis Digital. No framework
prose is reproduced. Bring your own crosswalk with `--crosswalk file.json` to
extend or replace the starter set.

## Install

```bash
pip install -e .
```

Requires Python 3.10+. Standard library only — no runtime dependencies.

## Usage

### Map a control across frameworks

```bash
grcforge map AC-2
grcforge map "CIS 5.1" --json
```

Looking up any identifier returns every topical mapping that contains it,
including the equivalent identifiers in the other frameworks.

### Coverage report

Given a JSON file of the controls you have implemented, report what percentage
of each framework that satisfies. Because the crosswalk links equivalent
controls, implementing a NIST control credits its CIS and SOC 2 equivalents.

```bash
grcforge coverage examples/implemented.json
grcforge coverage examples/implemented.json --json --verbose
```

#### Export formats

`coverage` and `gaps` can emit machine-readable output for audit workpapers,
wikis, and downstream tooling via `--format {table,json,csv,markdown}` (default
`table`). `--json` remains as a backward-compatible alias for `--format json`.

```bash
grcforge coverage examples/implemented.json --format csv      > coverage.csv
grcforge coverage examples/implemented.json --format markdown > coverage.md
grcforge gaps examples/implemented.json --framework soc2 --format csv
```

CSV coverage is one row per framework (`framework,label,total,satisfied,percent`);
CSV gaps is one row per `framework,control,topic,mapping_id`.

`implemented.json` is a mapping of framework id to a list of control ids. Either
shape works:

```json
{
  "implemented": {
    "nist": ["AC-2", "IA-2"],
    "cis": ["CIS 5.1"],
    "soc2": ["CC6.1"]
  }
}
```

or the bare object without the `implemented` wrapper.

### Gap analysis

List the requirements in a framework that your implemented set does not yet
satisfy, annotated with the topic each gap belongs to.

```bash
grcforge gaps examples/implemented.json --framework cis
grcforge gaps examples/implemented.json --framework nist --json
```

### List

```bash
grcforge list                      # all frameworks + mappings
grcforge list --framework nist     # every control id used for NIST
```

## Custom crosswalks

Any subcommand accepts `--crosswalk path/to/file.json`. The file format is:

```json
{
  "meta": { "name": "my crosswalk", "maintainer": "..." },
  "frameworks": { "nist": "label", "cis": "label" },
  "mappings": [
    {
      "id": "GRC-001",
      "topic": "Account lifecycle management",
      "description": "Your own description here.",
      "controls": { "nist": ["AC-2"], "cis": ["CIS 5.1"] }
    }
  ]
}
```

Validation is strict: every mapping needs a unique `id`, control lists must be
strings, and any framework referenced in a mapping must be declared in
`frameworks`.

## Demos

The [`demos/`](demos/) directory holds worked, real-use-case scenarios. Each is a
self-contained folder with input files in the tool's real format and a
`SCENARIO.md` describing where the data came from, what to expect, the exact
command to run, and how to act on the result.

| Demo | Scenario |
| --- | --- |
| [01-soc2-type2-readiness](demos/01-soc2-type2-readiness) | SOC 2 Type II readiness check before the observation window |
| [02-fedramp-li-saas-gaps](demos/02-fedramp-li-saas-gaps) | NIST 800-53 gap analysis for a SaaS pursuing a federal authorization |
| [03-greenfield-startup](demos/03-greenfield-startup) | Day-zero startup: turn an empty control set into a themed roadmap |
| [04-cis-ig1-smb](demos/04-cis-ig1-smb) | SMB working through CIS Controls v8 essential cyber hygiene |
| [05-incident-response-crosswalk](demos/05-incident-response-crosswalk) | Align one incident-response control across NIST/CIS/SOC 2 with `map` |
| [06-post-merger-consolidation](demos/06-post-merger-consolidation) | Find the controls that fell through the cracks after a merger |
| [07-pci-dss-custom-crosswalk](demos/07-pci-dss-custom-crosswalk) | Bring-your-own crosswalk: fold PCI DSS v4.0 into the same model |
| [08-audit-evidence-export](demos/08-audit-evidence-export) | Export CSV/Markdown coverage and gaps for an audit workpaper |

## Scope

grcforge is a **defensive and analytical** tool for compliance and audit teams.
It does not assess, attack, or modify any system — it reasons over a crosswalk
data file you control. The bundled crosswalk is a starting point for discussion,
not authoritative compliance advice.

## Development

```bash
pip install -e .
pip install pytest
python -m pytest -v
```

On Windows, set `PYTHONUTF8=1` before running tests.

## License

License: COCL 1.0

Maintainer: Cognis Digital

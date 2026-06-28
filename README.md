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


<!-- cognis:example:start -->
## 🔎 Example output

Real, reproducible output from the tool — runs offline:

```console
$ grcforge --version
grcforge 1.0.0
```

```console
$ grcforge --help
usage: grcforge [-h] [--version] [--crosswalk FILE]
                {map,coverage,gaps,list,feeds} ...

GRC control crosswalk engine: map controls across frameworks, measure
coverage, and find gaps.

positional arguments:
  {map,coverage,gaps,list,feeds}
    map                 Show cross-framework equivalents.
    coverage            Report framework coverage.
    gaps                List unmapped requirements for a framework.
    list                List frameworks or controls in a framework.
    feeds               Edge/air-gap data-feed ingestion (NIST OSCAL + ATT&CK
                        mappings) and enrichment.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --crosswalk FILE      Path to a crosswalk JSON file (overrides the built-in
                        starter).
```

```console
$ grcforge list
Frameworks:
  nist: NIST SP 800-53 Rev. 5 control families (29 controls)
  cis: CIS Critical Security Controls v8 safeguards (40 controls)
  soc2: AICPA SOC 2 Trust Services Criteria (Common Criteria) (18 controls)

Mappings (24):
  [GRC-001] Account lifecycle management
  [GRC-002] Least-privilege access enforcement
  [GRC-003] Multi-factor authentication
  [GRC-004] Audit log generation
  [GRC-005] Audit log retention and protection
  [GRC-006] Vulnerability scanning and remediation
  [GRC-007] Patch and flaw remediation
  [GRC-008] Malware and endpoint protection
  [GRC-009] Hardware and software inventory
  [GRC-010] Secure configuration baselines
  [GRC-011] Data-at-rest encryption
  [GRC-012] Data-in-transit encryption
  [GRC-013] Backup and recovery
  [GRC-014] Incident response process
  [GRC-015] Security awareness training
  [GRC-016] Risk assessment
  [GRC-017] Vendor and third-party risk
  [GRC-018] Boundary and network protection
  [GRC-019] Physical access control
  [GRC-020] Change management
  [GRC-021] Access revocation on termination
  [GRC-022] System monitoring and alerting
  [GRC-023] Data inventory and classification
  [GRC-024] Contingency and continuity planning
```

> Blocks above are real `grcforge` output — reproduce them from a clone.

<!-- cognis:example:end -->

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

## Live data feeds (edge / air-gap)

`grcforge feeds` enriches the crosswalk with **real, authoritative, keyless**
data — and it is built to run on disconnected / edge gear. Every fetch is cached
to disk and can be re-served with `--offline`; a snapshot can be sneakernet'd
into an air-gapped enclave.

This repo consumes two feeds:

| Feed id | Source | URL |
| --- | --- | --- |
| `oscal-800-53-rev5-catalog` | NIST SP 800-53 Rev. 5 catalog (OSCAL JSON) | `https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json` |
| `attack-nist-mappings` | CTID Mappings Explorer: MITRE ATT&CK ⇄ 800-53 Rev. 5 | `https://raw.githubusercontent.com/center-for-threat-informed-defense/mappings-explorer/main/mappings/nist_800_53/attack-16.1/nist_800_53-rev5/enterprise/nist_800_53-rev5_attack-16.1-enterprise.json` |

Both are public and require no API key. The bundled
[`datafeeds.py`](src/grcforge/datafeeds.py) is standard-library only.

```bash
grcforge feeds list                                   # what this repo consumes
grcforge feeds update                                 # fetch + cache both feeds
grcforge feeds get oscal-800-53-rev5-catalog --offline

# REAL enrichment — resolve the crosswalk's NIST controls to their
# authoritative OSCAL titles + the ATT&CK techniques each control mitigates:
grcforge feeds enrich --offline

# Turn a gap report into a real ATT&CK threat-exposure statement:
grcforge feeds expose examples/implemented.json --framework nist --offline
```

`feeds enrich` does not invent anything: control titles such as *"AC-2 — Account
Management"* come straight from NIST's OSCAL catalog, and the per-control ATT&CK
technique lists come from the CTID crosswalk. `feeds expose` joins that to the
existing gap analysis so a finding reads *"SC-7 (Boundary Protection) not
implemented → N ATT&CK techniques unmitigated"* instead of a bare control id.

### Offline / air-gap workflow

1. On a connected staging box: `grcforge feeds update`.
2. Snapshot the cache for transfer:
   `python -m grcforge.datafeeds snapshot-export feeds.tar.gz`.
3. Carry `feeds.tar.gz` to the disconnected enclave and import it into the
   target cache: `python -m grcforge.datafeeds snapshot-import feeds.tar.gz`.
4. Run any `feeds` command with `--offline`; it serves only from cache and never
   touches the network.

The cache location is `COGNIS_FEEDS_CACHE` (default `~/.cache/cognis-feeds`).
The committed `tests/fixtures/` directory is exactly such a cache — a small,
trimmed, real slice of both feeds — which is why the test suite runs fully
offline.

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
| [09-attack-threat-exposure](demos/09-attack-threat-exposure) | Offline NIST OSCAL + ATT&CK feeds: turn control gaps into real adversary-technique exposure |

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

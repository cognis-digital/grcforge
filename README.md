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

# Demo 05 — Aligning one control across frameworks with `map`

## Situation

An organization runs both a SOC 2 program and an internal NIST 800-53 program,
and the two teams use different vocabularies. During an incident-response tabletop
the SOC 2 lead references CC7.3 and CC7.4; the infrastructure team only knows the
NIST IR family and the CIS safeguards their SOAR tooling implements. Before
writing the IR policy they want a single view that ties all three together so the
policy can be cited from any framework.

This demo uses no input file — it exercises the `map` subcommand directly against
the bundled starter crosswalk to show cross-framework equivalents for a control.

## What to expect

`map IR-4` (and the equivalents query for the SOC 2 / CIS identifiers) should
resolve to the incident-response topic and show the matched identifiers in every
framework: NIST IR-4 / IR-8, CIS 17.1 / 17.4, and SOC 2 CC7.3 / CC7.4. Looking up
any one of those identifiers returns the same mapping, which is the whole point —
they are equivalents.

## Run it

```bash
grcforge map IR-4
grcforge map "CIS 17.1"
grcforge map CC7.3 --json
```

## How to act

Use the matched topic as the anchor for a single IR policy document, and cite the
per-framework identifiers in the policy header. When an auditor asks "where do you
cover CC7.3?", you point at the same procedure that satisfies IR-4 and CIS 17.1 —
one control implemented, three frameworks credited.

# Demo 03 — Greenfield startup: the complete to-do list

## Situation

A four-person startup just closed a seed round and a prospective enterprise
customer has asked for a security questionnaire. They have effectively no formal
controls in place yet. The founder wants a single, ordered list of *everything*
to build, grouped by topic, so they can triage what matters for the first deal.

`implemented.json` is intentionally empty — it declares the three frameworks but
lists zero implemented controls. This is the "day zero" baseline.

## What to expect

Coverage will report 0% across every framework. The gap analysis for any
framework returns the full set of controls in the starter crosswalk, each
annotated with the topic it belongs to. That topic annotation is the value here:
it turns a flat list of control IDs into a themed roadmap (account lifecycle,
MFA, logging, vulnerability management, backups, incident response, and so on).

## Run it

```bash
grcforge coverage demos/03-greenfield-startup/implemented.json
grcforge gaps demos/03-greenfield-startup/implemented.json --framework cis
grcforge gaps demos/03-greenfield-startup/implemented.json --framework nist --json
```

## How to act

Sort the gap topics by deal impact. For a first enterprise sale the questionnaire
almost always probes MFA, access lifecycle, logging, encryption, and backups —
knock those out first. Re-run `coverage` after each sprint; the percentage climb
is a clean progress metric to show the customer and the board.

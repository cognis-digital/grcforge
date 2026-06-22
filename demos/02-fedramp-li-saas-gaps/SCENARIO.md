# Demo 02 — NIST 800-53 gap analysis for a SaaS pursuing a federal authorization

## Situation

A SaaS vendor wants to sell into U.S. federal agencies and has begun working
toward an authorization built on NIST SP 800-53. They have stood up the
"easy wins" first — identity and access management, configuration baselines,
network boundary protection, and encryption — but the program is young and the
operational-resilience and program-management control families are not in place
yet.

`implemented.json` lists the NIST control identifiers their engineering team has
implemented and verified, plus the CIS v8 safeguards their tooling enforces.
Because grcforge credits cross-framework equivalents, the CIS entries also help
satisfy the NIST mappings they share a topic with.

## What to expect

NIST coverage will be partial. The gap list should surface the families this
team has not yet addressed: contingency and backup (CP-2, CP-9, CP-10),
incident response (IR-4, IR-8), risk assessment (RA-3, RA-5), awareness training
(AT-2), audit-log protection/retention (AU-9, AU-11), vendor risk (SA-9), and
physical access (PE-3).

## Run it

```bash
grcforge coverage demos/02-fedramp-li-saas-gaps/implemented.json
grcforge gaps demos/02-fedramp-li-saas-gaps/implemented.json --framework nist
```

## How to act

Use the NIST gap list to drive a control-implementation backlog. Contingency
planning, incident response, and continuous monitoring (CP, IR, SI-4) are
typically the longest lead-time items because they require tested procedures and
running evidence, not just configuration — schedule them first.

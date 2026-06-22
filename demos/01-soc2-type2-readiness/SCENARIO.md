# Demo 01 — SOC 2 Type II readiness check

## Situation

A 60-person B2B SaaS company is six weeks out from the start of its first SOC 2
Type II observation window. The security lead has a list of the technical
controls already operating (MFA, centralized logging, EDR, encryption, patch
management) and wants to know, before the auditor walks in, how much of the SOC 2
Common Criteria those controls plausibly cover — and where the obvious holes are.

The implemented set in `implemented.json` was assembled from the team's control
matrix: NIST 800-53 identifiers for the technical controls, the corresponding
CIS v8 safeguards their MDM/EDR tooling enforces, and the SOC 2 criteria they
believe they can already produce evidence for.

## What to expect

The coverage report should show solid coverage of the access-control and
logging-related criteria, but a visible gap on the SOC 2 criteria that depend on
*process* rather than tooling — risk assessment (CC3.x), vendor management
(CC9.2), incident response (CC7.3/7.4), security awareness (CC2.2) and change
management (CC8.1) — none of which appear in the implemented set.

## Run it

```bash
grcforge coverage demos/01-soc2-type2-readiness/implemented.json --verbose
grcforge gaps demos/01-soc2-type2-readiness/implemented.json --framework soc2
```

## How to act

Treat the SOC 2 gaps list as the readiness punch list. The process-driven gaps
(CC2.2, CC3.1/3.2, CC7.3/7.4, CC8.1, CC9.2) are not solved by buying a tool —
they need a documented, operating procedure with evidence produced during the
window. Start those now so they have run time before the audit period closes.

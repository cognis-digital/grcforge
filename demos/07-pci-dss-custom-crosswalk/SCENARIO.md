# Demo 07 — Bring-your-own crosswalk: adding PCI DSS v4.0

## Situation

A payments-adjacent SaaS already runs a NIST/CIS/SOC 2 program and is now in scope
for PCI DSS v4.0 because it handles cardholder data. Rather than maintain a fourth
siloed checklist, the GRC team wants PCI requirements folded into the *same*
crosswalk so a single implemented control is credited everywhere it applies.

`crosswalk.json` is a custom, four-framework crosswalk authored for this demo. It
adds a `pci` framework and ten mappings that tie PCI DSS v4.0 requirement numbers
(e.g. 8.2, 8.4, 3.5, 4.2, 10.2) to the equivalent NIST / CIS / SOC 2 identifiers.
The PCI requirement numbers are factual references to public PCI DSS v4.0
numbering; all descriptive text is original.

`implemented.json` reflects what this team has built so far — strong on identity,
access, anti-malware and basic logging; weak on encryption-in-transit, log
review/retention, vulnerability management, and segmentation.

## What to expect

This demo shows three things at once: a custom crosswalk via `--crosswalk`,
cross-framework credit across *four* frameworks, and a PCI-specific gap list. The
PCI gaps should be in-transit encryption (4.2), audit log review/retention
(10.4, 10.5), and vulnerability management (6.3, 11.3). The segmentation
requirements (1.3, 1.4) do NOT appear as gaps even though no `pci` identifier for
them is implemented: the `CIS 13.4` entry in the implemented set credits them
through the shared mapping. That cross-framework credit is the whole point.

## Run it

```bash
grcforge --crosswalk demos/07-pci-dss-custom-crosswalk/crosswalk.json \
  coverage demos/07-pci-dss-custom-crosswalk/implemented.json --verbose

grcforge --crosswalk demos/07-pci-dss-custom-crosswalk/crosswalk.json \
  gaps demos/07-pci-dss-custom-crosswalk/implemented.json --framework pci

grcforge --crosswalk demos/07-pci-dss-custom-crosswalk/crosswalk.json \
  map "8.4"
```

## How to act

Maintain one crosswalk, not four. When you implement a control, record it under
whichever framework you naturally track, and let the crosswalk earn the credit in
the others. Use the PCI gap list as the QSA-facing remediation plan.

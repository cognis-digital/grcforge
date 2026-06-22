# Demo 04 — SMB working through CIS Controls v8 (essential cyber hygiene)

## Situation

A 30-person managed-services SMB has adopted the CIS Critical Security Controls
v8 as its baseline and has been knocking out the foundational safeguards: asset
and software inventory, data inventory, secure configuration, account and access
management, MFA, patching, logging, EDR, backups, and the first awareness-training
safeguard.

`implemented.json` here is a CIS-only set — the IT lead tracks the program purely
in CIS terms and does not maintain a NIST or SOC 2 mapping. grcforge accepts a
single-framework implemented set just fine.

## What to expect

CIS coverage will be high but not complete. The gap list should call out the
safeguards this team has skipped: log retention/protection (CIS 8.3, 8.10), the
additional vulnerability-management safeguards (CIS 7.1, 7.5, 7.6), data-at-rest
and in-transit encryption (CIS 3.11, 3.10), the incident-response safeguards
(CIS 17.1, 17.4), risk assessment (CIS 18.1), vendor management (CIS 15.1, 15.4),
boundary control (CIS 13.4, 4.4), and network monitoring (CIS 13.1, 8.11).

Note the cross-framework credit at work: the team implemented `CIS 10.1` and
`CIS 11.1`, and the starter crosswalk groups those with `CIS 10.2` and
`CIS 11.2/11.3` under the same topic — so those do **not** show up as gaps even
though they were never explicitly listed.

Because the implemented set is CIS-only, the NIST and SOC 2 coverage numbers in
the report will reflect only the cross-framework credit those CIS safeguards earn.

## Run it

```bash
grcforge coverage demos/04-cis-ig1-smb/implemented.json --verbose
grcforge gaps demos/04-cis-ig1-smb/implemented.json --framework cis
```

## How to act

The remaining CIS gaps are mostly the operational, "prove it keeps working"
safeguards — log retention, backup restore tests, incident response, vendor
review. These are exactly the items that separate basic hygiene from a defensible
program; turn them into recurring, scheduled tasks with retained evidence.

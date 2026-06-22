# Demo 09 — ATT&CK threat exposure of your control gaps (offline)

## Situation

A federal-adjacent platform team has implemented its identity and logging
controls but not yet its boundary-protection, configuration-management, or
malicious-code controls. Leadership does not want another spreadsheet of missing
NIST control ids — they want to know *what an attacker can actually do* because
of each gap.

This demo joins grcforge's existing gap analysis to two authoritative,
**keyless, air-gap-deployable** data feeds:

- `oscal-800-53-rev5-catalog` — NIST's OSCAL release of the SP 800-53 Rev. 5
  catalog, used to resolve each control id into its authoritative title.
- `attack-nist-mappings` — the Center for Threat-Informed Defense (CTID)
  ATT&CK ⇄ 800-53 Rev. 5 crosswalk, used to list the real MITRE ATT&CK
  techniques each unimplemented control would have mitigated.

The result reads "**SC-7 (Boundary Protection) is not implemented → N ATT&CK
techniques unmitigated**" instead of a bare control id.

## Offline / air-gap

This demo runs with `--offline`: it serves both feeds from the on-disk cache and
never touches the network. On a connected staging box, run `grcforge feeds
update` once, then `grcforge feeds snapshot-export feeds.tar.gz` and carry the
archive to the disconnected enclave (`snapshot-import`). The committed
`tests/fixtures/` slice is exactly such a cache.

## What to expect

`feeds enrich` shows the implemented set's NIST controls with their real titles
and the count of ATT&CK techniques each mitigates. `feeds expose` ranks the
*unmapped* controls by how many adversary techniques they leave open.

## Run it

```bash
# point the cache at the committed offline fixture (or your own snapshot)
export COGNIS_FEEDS_CACHE="$(pwd)/tests/fixtures"

# authoritative NIST titles + ATT&CK techniques mitigated, fully offline
grcforge feeds enrich --offline

# threat exposure of the gaps for this demo's implemented set
grcforge feeds expose demos/09-attack-threat-exposure/implemented.json \
  --framework nist --offline
```

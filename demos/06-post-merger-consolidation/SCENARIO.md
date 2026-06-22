# Demo 06 — Post-merger control consolidation

## Situation

Two companies have merged. The acquirer ran a NIST-anchored program; the acquired
company ran a CIS + SOC 2 program. The combined security team has built a unified
control inventory by taking the *union* of what both sides genuinely operate, then
deduplicating. They want to know where the merged organization actually stands and
which controls are still owned by nobody after the reorg.

`implemented.json` is that consolidated union across all three frameworks. It is
deliberately broad — this is a mature, combined program — so coverage should be
strong, and the remaining gaps are the interesting part.

## What to expect

Coverage across all three frameworks should be the highest of any demo here. The
residual gaps point at the controls that fell through the cracks during
integration. The same three themes surface in every framework: awareness
training (CC2.2 / AT-2), vendor and third-party risk (CC9.2 / SA-9), and physical
access control (CC6.4 / PE-3). Everything else is credited — including controls
that only one side ran — because the consolidated set plus cross-framework credit
covers the shared mappings.

## Run it

```bash
grcforge coverage demos/06-post-merger-consolidation/implemented.json --verbose
grcforge gaps demos/06-post-merger-consolidation/implemented.json --framework soc2
grcforge gaps demos/06-post-merger-consolidation/implemented.json --framework nist
```

## How to act

In a merger the gaps are almost always *ownership* problems, not capability
problems — both companies probably did vendor risk somewhere, but no one owns it
in the new org chart. Assign each remaining gap an owner before remediating, then
re-run coverage to confirm the consolidated number.

# Demo 08 — Exporting coverage and gaps for an audit workpaper

## Situation

An internal auditor needs to drop the current control-coverage status into an
audit workpaper (a spreadsheet) and into a Markdown status page in the team wiki.
Copy-pasting the terminal table by hand is error-prone, so they use grcforge's
machine-readable export formats: CSV for the spreadsheet, Markdown for the wiki,
and JSON if a downstream script needs to consume it.

`implemented.json` is a representative mid-maturity program across all three
frameworks.

## What to expect

`--format csv` emits a clean header row plus one row per framework for coverage,
or one row per (control, topic, mapping) for gaps — ready to open in Excel or pipe
to a file. `--format markdown` emits a titled section with a GitHub-flavored table
that pastes straight into a wiki or pull request. `--format json` is the existing
structured output (and `--json` remains a backward-compatible alias).

## Run it

```bash
# Coverage as a CSV workpaper
grcforge coverage demos/08-audit-evidence-export/implemented.json --format csv \
  > coverage.csv

# SOC 2 gaps as a Markdown status table
grcforge gaps demos/08-audit-evidence-export/implemented.json \
  --framework soc2 --format markdown > soc2-gaps.md

# Gaps as a flat CSV (one row per control/topic) for a remediation tracker
grcforge gaps demos/08-audit-evidence-export/implemented.json \
  --framework nist --format csv > nist-gaps.csv
```

## How to act

Wire these into a scheduled job. Running the CSV/Markdown exports on a cadence and
committing them gives you a dated, diff-able record of coverage over time — useful
both for management reporting and for showing an auditor that the program is being
actively monitored, not snapshotted once a year.

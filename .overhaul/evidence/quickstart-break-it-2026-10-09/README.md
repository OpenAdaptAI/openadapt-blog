# Evidence for the quickstart --break-it post (2026-10-09)

This folder backs the before/after table and the quoted report lines in
`content/posts/openadapt-quickstart-break-it/index.md`. Hugo doesn't publish
it, because it sits outside `content/` and `static/`.

All data is synthetic. MockMed is the fake clinic app that ships with
OpenAdapt, and its patients are made up.

## How it was produced

- Date: 2026-10-09, about 17:21 to 17:24 UTC.
- Packages: openadapt 1.16.0 with openadapt-flow 1.35.1 (receipt builder
  version in `run/receipt.json`), on Python 3.12 in a fresh virtual
  environment.
- Command: `openadapt quickstart --break-it`. The console output is in
  `run.log`. The log's local paths pointed at a temporary folder that no
  longer exists, so they're shortened to `<scratch>/`. Nothing else in the
  log changed.

## What each file shows

| File | What it shows |
|---|---|
| `run/REPORT.md`, `run/report.json` | The clean run: transaction outcome `VERIFIED` (done and checked), 2 of 2 effects confirmed by a separate read of the record. |
| `run/receipt.json`, `run/receipt.md` | The shareable receipt the clean run produced. |
| `run-broken/REPORT.md`, `run-broken/report.json` | The `--break-it` run: execution outcome `HALTED`, transaction outcome `RECONCILIATION_REQUIRED` (check the record). The post quotes the "Required contracts passed" and "[rest] record_written" lines from `REPORT.md`. |
| `run-broken/pending_escalation.json` | The pending item for a person, with the three choices the post lists. |
| `run*/steps/step_005_before.png`, `step_005_after.png` | The Save Encounter step. The two `step_005_after.png` files are byte-identical (sha256 `ba6033fa...b2d4`), so the screen looked the same in both runs. |

Files the run wrote that aren't copied here: the other step screenshots, the
checkpoints, the durable-run lock files, and the local attended-capability key,
which must never be committed.

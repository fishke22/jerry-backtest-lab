# Mobile-first workflow

The primary mobile control plane is the ChatGPT GitHub app, not a local terminal.

## Submit a backtest

Create a new JSON file under:

`requests/<unique_request_id>.json`

Use the structure in `requests/example_sma_walkforward.json`.

A push touching `requests/*.json` automatically starts the free GitHub Actions worker.

## Read the result

When the workflow finishes, read:

- `results/<request_id>.json` for machine-readable metrics
- `reports/<request_id>.md` for a compact human-readable report

The worker is limited to one concurrent job and 10 minutes per run.

## Cost guardrail

This repository uses only a standard GitHub-hosted Ubuntu runner. Do not change the workflow to a larger runner, GPU runner, or paid service without explicit approval.

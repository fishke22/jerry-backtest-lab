# Mobile Research Workflow Architecture

## Goal

Make ChatGPT on mobile the main control surface for repeatable research. The user gives a natural-language command; ChatGPT converts it into a versioned request; cloud workers run it; results are written back to the private repository and can be read through the GitHub app.

## Layers

1. **ChatGPT control plane**
   - Interprets the user's request.
   - Applies reusable Skills.
   - Selects connected apps/plugins.
   - Writes a deterministic request into GitHub.
   - Reads results and explains failures.

2. **Skill layer**
   - Reusable routing, validation, safety, and output rules.
   - Does not replace the computation engine.
   - The initial open-format skill is in `skills/mobile-research-orchestrator/SKILL.md`.

3. **App/plugin layer**
   - GitHub: durable requests, code, results, audit trail.
   - Future apps: Drive/Slack/Gmail/news/data providers/workflow products as needed.
   - Plugins can bundle skills and apps for more specialized workflows.

4. **Execution layer**
   - GitHub Actions standard hosted runner.
   - No local PC required.
   - No GPU or paid runner without explicit approval.

5. **Data layer**
   - Raw market/news downloads: cloud cache first; do not commit by default.
   - Derived features, manifests, checksums, and research results: private repo.
   - If datasets later become large, move durable cache to object storage rather than bloating Git history.

## Cloud cache policy

The workflow uses GitHub Actions cache for `.cache/market-data`.

- Cache key is daily, so the first run of a UTC day downloads the sources.
- Later runs that day restore the same cloud cache instead of downloading again.
- Raw cached files are not committed to Git.
- A request can set `force_refresh: true` when fresh data is required.
- Because Actions cache is not a permanent data lake, important research provenance is stored as source URLs, timestamps/checksums, and result files.

## Why not permanently commit every raw download?

- Some sources have redistribution/copyright restrictions.
- High-frequency data will eventually make the Git repository inefficient.
- Many sources change or revise historical observations.
- A cache + checksum + derived-results model is cheaper and cleaner.

## Future workflow families

- JNU/Nikkei quantitative research
- Taiwan-stock V28 research
- News/event collection and sentiment scoring
- Macro/cross-market condition research
- Filing/event monitoring
- Document/report production
- Data quality audits
- Other domains added as separate, versioned workflows rather than one monolithic automation

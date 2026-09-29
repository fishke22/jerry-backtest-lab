# JNU Three-Engine Integration v1

## Authority and separation

JNU Research is the semantic/research-governance source of truth. MARKET_AI_HUB is the local data/model/validation compute engine. ChatGPT supplies current external-market/event context and causal synthesis. ChatGPT memory is not a durable specification.

The machine-readable contract is `config/jnu_three_engine_analysis_contract_v1.json`.

## Non-negotiable rules

1. Do not merge the repositories merely to integrate them.
2. MARKET_AI_HUB consumes a pinned contract version and implements an adapter. It must not silently redefine JNU Research semantics.
3. Evidence fusion is not 2-of-3 voting. Preserve Structure, Quant, Macro, Event Risk and Data Quality separately.
4. Touch != Break != Acceptance. Acceptance requires an explicit level.
5. Do not fabricate support/resistance or true Volume Profile when provenance is insufficient.
6. Unvalidated model evidence cannot become calibrated probability, predictive gain or trading edge.
7. Forecast snapshots are immutable; outcomes append later; reanalysis is a separate record.
8. Anything needing local Yuanta/model/data runtime is LOCAL_VALIDATION_PENDING until the PC is available.

## ChatGPT context framework

For current JNU analysis, ChatGPT should add only sourced, timestamped context relevant to the existing nine-layer framework: Brent/WTI and energy-supply shocks; U.S. 2Y/10Y yields; USD/JPY and MOF intervention regime; Nasdaq/SOX/U.S. equity futures; BOJ/JGB and macro surprises; major geopolitical/policy events. World Monitor or similar aggregators are scenario/context inputs, never calibrated probability sources.

## Integration flow

JNU Research framework -> common contract -> MARKET_AI_HUB adapter
Current ChatGPT context ---------------------------> Evidence Fusion
MARKET_AI_HUB quant/true-Micro evidence ----------> Evidence Fusion
Evidence Fusion -> immutable forecast snapshot -> append-only outcomes -> regime/engine comparison

## Conflict policy

A fused result must retain each engine's original stance and evidence quality. A neutral/unvalidated quant engine does not veto a structural conditional view, but it prevents language implying validated quantitative edge. High event risk may reduce confidence or trigger abstention without casting a synthetic directional vote.

## Promotion policy

No new rule becomes directional alpha because the three engines agree once. Promotion requires preregistration and the existing OOS/true-target/forward-validation governance.

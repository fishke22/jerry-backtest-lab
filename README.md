# JNU Research

**JNU Research** is the research and validation system for Osaka Exchange Nikkei 225 Micro Futures (JNU).

The historical GitHub repository path remains `fishke22/jerry-backtest-lab` for compatibility and audit history, but the system's design identity and primary research scope are now **JNU Research**.

## Mandatory analysis entrypoint

Whenever the user asks for any of the following:

- 分析大阪微型日經期貨
- 分析大阪日經
- 分析 JNU / 分析JNU
- 分析週一／禮拜一的 JNU
- 今晚 JNU 怎麼走
- 大阪微型日經如何操作

the analysis must begin from:

1. `config/jnu_operational_framework_cross_session_memory_v1.json`
2. the authoritative framework named there, currently `config/jnu_operational_framework_current_v1_9.json`
3. `config/jnu_cross_session_precision_analysis_memory_v1.json`
4. `config/jnu_precision_feature_research_prereg_v1.json`
5. `config/jnu_research_analysis_output_protocol_v1.json`

The system identity and trigger contract are frozen in:

- `config/jnu_research_system_identity_v1.json`

The full historical-framework coverage audit is:

- `config/jnu_research_framework_coverage_audit_20260926_v1.json`

## Authoritative JNU analysis architecture

All nine original framework layers remain mandatory:

1. Market Regime
2. Event Risk State
3. Cross-Market Information
4. Dynamic Price Discovery
5. Intraday Price Path / Rejection
6. Positioning / Derivatives
7. Dynamic SQ Bias
8. Evidence Fusion
9. Decision Output

The framework lineage audit confirms that no layer item or historical top-level governance key from v1.0 through v1.9 was dropped.

## Precision layer

JNU Research additionally checks, when data are available:

- Nikkei breadth / component concentration
- Nikkei 225 VI local implied-volatility state
- JGB curve / BOJ surprise
- PIT-safe macro surprise magnitude
- order-flow / microprice / liquidity
- MOF FX-intervention regime
- session / time-of-day liquidity normalization
- U.S. economic-policy-uncertainty / Nikkei-futures liquidity regime

These are context, risk, evidence-quality or path refinements unless separately validated. They do not create extra directional votes.

## Research-only candidate

`LOWER_WICK_FAILED_BREAKDOWN_RECLAIM_CONFIRMATION` remains a preregistered **research candidate**, not a directional vote. Its specification is frozen; promotion requires true OSE Mini untouched OOS, incremental comparison against generic breakout, multiple-testing control, exact Micro validation and forward validation.

## Mandatory user-facing output

Every JNU analysis must provide:

- the most likely conditional directional bias;
- confidence limited by current validation status;
- expected path and secondary scenario;
- key support/resistance/trigger levels;
- invalidation and flip conditions;
- event/liquidity risks;
- a concrete conditional operation plan:
  - entry trigger;
  - stop / exit condition;
  - target or trailing-exit logic;
  - no-trade conditions;
  - response if the initial view is wrong.

Unavailable evidence must be labeled `UNKNOWN` / `UNAVAILABLE`, never guessed.

## Validation state

Current authoritative framework: **JNU Operational Framework v1.9**

Current directional state:

- validated directional modules: **0**
- decision engine: **NO_VALIDATED_DIRECTIONAL_EDGE**
- formal confidence: **LOW / MEDIUM only**
- terminal-failed families: **prohibited from directional voting or post-hoc rescue**

This does not prevent practical market analysis. It means practical bias and operation plans must be presented as evidence-based conditional judgments, not as guaranteed or calibrated probabilities.

## Internal construction status

All currently specified internal synthetic/read-only construction stages are complete through the crash-recovery journal/replay stage.

- crash-recovery selftest: **88 / 88 PASS**
- full integrity CI: **PASS**
- Actionlint: **PASS**
- public real ledger: **0 forecasts / 0 outcomes**
- production state mutation: **false**

Remaining progress is evidence/data driven: real entitlement, provider terms, authorized OSE history, PIT-safe consensus history and real forward validation.

See:

- `config/jnu_internal_construction_completion_checkpoint_20260926_v1.json`
- `config/jnu_private_selection_shadow_crash_recovery_checkpoint_v1.json`
- `research_notes/jnu_precision_feature_research_feasibility_20260926.md`

## Boundaries

JNU Research is not MARKET_AI_HUB. Mature, separately validated JNU findings may later be integrated downstream into MARKET_AI_HUB, but this repository's subject is JNU research and analysis.

No broker login, trading, order execution or live production capability is enabled by this repository unless a later explicit governance amendment authorizes it.

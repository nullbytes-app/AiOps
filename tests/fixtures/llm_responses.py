"""OpenRouter-like LLM API response fixtures used in tests.

Each fixture returns a dict shaped like real OpenRouter responses:

{
  "id": str,
  "choices": [{"message": {"content": str}}],
  "usage": {"prompt_tokens": int, "completion_tokens": int}
}

Use these to simulate complete, long, empty, and error responses without
calling the network.
"""

from typing import Any, Dict, Optional


def mock_openrouter_response(
    content: str,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    id: Optional[str] = None,
) -> Dict[str, Any]:
    """Factory for minimal OpenRouter-style responses.

    Parameters
    - content: The assistant message text to place in the first choice.
    - prompt_tokens: Token count attributed to the prompt.
    - completion_tokens: Token count attributed to the completion.
    - id: Optional response identifier; a deterministic default is used if omitted.

    Returns
    A dict with keys: ``id``, ``choices``, and ``usage`` matching the minimal
    structure of a successful OpenRouter completion.
    """

    response_id = id or "resp_mock_0001"
    return {
        "id": response_id,
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ],
        "usage": {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
        },
    }


def valid_enhancement_response() -> Dict[str, Any]:
    """Valid, concise enhancement written in Markdown (<500 words).

    Intended to represent a typical, successful enhancement response that is
    complete and comfortably under a 500-word validation threshold.
    """

    content = (
        "# Enhancement Proposal: Log Anomaly Detector\n\n"
        "## Summary\n"
        "Introduce a lightweight anomaly detector that learns normal log patterns and flags\n"
        "deviations in near real time. The goal is to reduce mean time to detect (MTTD),\n"
        "improve on-call signal quality, and provide actionable context for remediation.\n\n"
        "## Goals\n"
        "- Detect unusual error rate spikes and rare log sequences.\n"
        "- Correlate anomalies with deploys, infra events, and feature flags.\n"
        "- Produce low-noise alerts with rich, linkable context.\n\n"
        "## Non-Goals\n"
        "- Full root-cause analysis.\n"
        "- Predictive capacity planning.\n\n"
        "## Design\n"
        "1. Ingest structured logs via existing pipeline (e.g., OpenTelemetry).\n"
        "2. Build hourly baselines of key metrics (rate, latency, error codes).\n"
        "3. Train an online clustering model (e.g., incremental DBSCAN) per service.\n"
        "4. Trigger alerts when current windows diverge from baselines beyond thresholds.\n"
        "5. Attach context: recent deploys, error samples, dashboards, and runbooks.\n\n"
        "## Operations\n"
        "- Config as code: thresholds, dimensions, and suppression rules in Git.\n"
        "- Safeguards: cool-downs, deduplication, and auto-suppression during deploys.\n"
        "- Storage: 7–14 days of features for model warm-up and backtesting.\n\n"
        "## Rollout\n"
        "- Phase 1: Shadow-mode in staging; compare with existing alerts.\n"
        "- Phase 2: Limited services in production with human-in-the-loop feedback.\n"
        "- Phase 3: Expand coverage; add per-service tuning from feedback.\n\n"
        "## Success Metrics\n"
        "- ≥30% reduction in MTTD for log-driven incidents.\n"
        "- ≤5% false-positive rate during stable periods.\n"
        "- Time-to-triage under 5 minutes with attached context.\n"
    )

    return mock_openrouter_response(
        content,
        prompt_tokens=180,
        completion_tokens=320,
        id="resp_valid_enhancement_001",
    )


def truncated_enhancement_response() -> Dict[str, Any]:
    """Valid response that is intentionally long (simulates truncation handling).

    The content is a comprehensive Markdown plan that exceeds a typical 500-word
    threshold so tests can verify downstream truncation or summarization logic.
    """

    content = (
        "# Comprehensive Enhancement Plan: Observability and Auto-Remediation\n\n"
        "## Context\n"
        "Our platform operates a fleet of microservices with diverse traffic patterns,\n"
        "spanning critical user flows and batch workloads. Incidents often start as\n"
        "silent degradations and propagate across dependencies before conventional\n"
        "alerts fire. We need a proactive layer that detects early signals, provides\n"
        "clear triage context, and, when safe, performs auto-remediation.\n\n"
        "## Objectives\n"
        "- Shorten MTTD and MTTR by correlating logs, metrics, traces, and deploy data.\n"
        "- Deliver high-signal alerts with rich, actionable context and runbook links.\n"
        "- Offer guarded auto-remediation for well-understood, low-risk failure modes.\n\n"
        "## Functional Requirements\n"
        "1. Signal Ingestion: Unified pipeline for logs (structured), metrics (PromQL),\n"
        "   and traces (OTLP). Support tagging by service, version, region, and cluster.\n"
        "2. Feature Extraction: Windowed aggregations, error-rate deltas, rare pattern\n"
        "   detection, saturation indicators, and dependency health summaries.\n"
        "3. Anomaly Detection: Per-service baselines with seasonality adjustment;\n"
        "   ensemble methods combining statistical and ML techniques for robustness.\n"
        "4. Alerting: SLO-aware thresholds, deduplication, grouping, and adaptive\n"
        "   routing (PagerDuty, Slack) with escalation policies.\n"
        "5. Contextualization: Attach dashboard links, recent deploys, suspect commits,\n"
        "   error exemplars, and impacted endpoints with estimated user blast radius.\n"
        "6. Auto-Remediation: Safe actions behind feature flags (e.g., cache clear,\n"
        "   canary rollback, pod restart) with circuit breakers and approvals.\n\n"
        "## Non-Functional Requirements\n"
        "- Reliability: Controller availability ≥99.9%; no single point of failure.\n"
        "- Performance: End-to-end detection latency under 60 seconds at P95.\n"
        "- Security: Principle of least privilege; signed configs; auditable actions.\n"
        "- Cost: Storage tiering and sampling to keep monthly spend within budget.\n\n"
        "## Architecture\n"
        "- Ingestion: Use existing collectors; enforce schema via a versioned contract.\n"
        "- Processing: Stream-first with compact aggregates; backfill via batch jobs.\n"
        "- Modeling: Online learners with warm starts and periodic backtesting.\n"
        "- Controller: Event-driven orchestrator that evaluates policies and executes\n"
        "  remediations through vetted provider integrations.\n\n"
        "## Data Flow\n"
        "1. Collect signals and normalize with service metadata.\n"
        "2. Compute features per window; update baselines.\n"
        "3. Evaluate anomalies and correlate across layers and dependencies.\n"
        "4. Generate alerts with context bundles and suggested actions.\n"
        "5. If policy permits, execute auto-remediation and monitor outcomes.\n\n"
        "## Policies\n"
        "Policies define when to alert, notify, or remediate. They are declared as\n"
        "code, reviewed in PRs, validated in CI, and signed before deployment.\n"
        "Examples: rollback a canary if error rate > baseline + 4σ for 5 minutes;\n"
        "scale read replicas when p95 latency exceeds SLO by 20% during high QPS.\n\n"
        "## Edge Cases\n"
        "- Cold Starts: Suppress anomalies during initial warm-up to avoid noise.\n"
        "- Partial Outages: Correlate cross-service symptoms to prevent alert storms.\n"
        "- Deploy Storms: Auto-mute during coordinated releases unless hard SLOs are hit.\n"
        "- Data Gaps: Use imputation with explicit flags when signals are missing.\n\n"
        "## Rollout Plan\n"
        "- Phase 0: RFC + design review; identify pilot services.\n"
        "- Phase 1: Shadow mode in staging with synthetic failure drills.\n"
        "- Phase 2: Limited production rollout with human approval gates.\n"
        "- Phase 3: Expand coverage; enable auto-remediation for vetted playbooks.\n\n"
        "## Risks and Mitigations\n"
        "- False Positives: Ensemble models and SLO-aware thresholds to dampen noise.\n"
        "- False Negatives: Backtesting with incident retrospectives; add new features.\n"
        "- Remediation Safety: Circuit breakers, rate limits, and rapid rollback paths.\n"
        "- Drift: Periodic recalibration; anomaly budgets per service to bound actions.\n\n"
        "## Success Metrics\n"
        "- 40% MTTD reduction on P0/P1 incidents within two quarters.\n"
        "- 25% MTTR reduction for incidents covered by an automated playbook.\n"
        "- <5% noisy alerts after the first month of production tuning.\n\n"
        "## Open Questions\n"
        "- Preferred policy language and validation strategy?\n"
        "- Governance for on-call approval flows across teams?\n"
        "- Long-term data retention needs for compliance and analytics?\n"
    )

    return mock_openrouter_response(
        content,
        prompt_tokens=420,
        completion_tokens=980,
        id="resp_truncated_enhancement_001",
    )


def empty_enhancement_response() -> Dict[str, Any]:
    """Valid response envelope with an empty content string.

    Use this to test handling of blank or missing assistant messages while
    maintaining the expected OpenRouter response shape.
    """

    return mock_openrouter_response(
        "",
        prompt_tokens=100,
        completion_tokens=0,
        id="resp_empty_enhancement_001",
    )


def error_response() -> Dict[str, Any]:
    """Error-shaped response that still matches the OpenRouter structure.

    Simulates a 500/timeout failure where downstream code still receives a
    response-like envelope but the content contains an error indicator.
    """

    error_text = (
        "ERROR: 500 Internal Server Error — upstream timeout while generating "
        "completion. The request timed out after 30s. Please retry."
    )

    return mock_openrouter_response(
        error_text,
        prompt_tokens=100,
        completion_tokens=0,
        id="resp_error_500_timeout_001",
    )


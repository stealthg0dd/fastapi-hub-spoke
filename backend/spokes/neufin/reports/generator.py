"""
Neufin Report Generator
========================

Produces a professional Markdown client report from the outputs of the
BiasAnalysis profiler and the TradingBehaviorRisk assessor.

Report sections
---------------
1. Executive Summary          — one-paragraph overview (risk score + top bias)
2. Risk Profile               — behavioral risk score gauge + component breakdown
3. Detected Patterns          — revenge trade table + herding signal table
4. Cognitive Bias Analysis    — per-bias cards from BiasAnalysis
5. Talking Points for Client  — 3 advisor suggestions grounded in KnowledgeScanner
6. Compliance Check           — MAS regulation validation of each talking point

Architecture
------------
- Sections 1–4 are rendered purely from structured Pydantic data (no LLM call,
  deterministic output).
- Section 5 calls claude-sonnet-4-6 with KnowledgeScanner context injected to
  prevent hallucination of regulatory terms or bias definitions.
- Section 6 uses a PageIndex-style retrieval: filter the BM25 corpus to
  ``category="regulation"`` only, re-rank within that subset, and validate each
  talking point against the top-1 matching regulation.  Uses claude-sonnet-4-6
  with tool-use to force a structured compliance verdict per talking point.

Usage
-----
    from reports.generator import generate_report
    from agents.profiler import analyze_user_biases, assess_behavioral_risk

    bias_analysis  = await analyze_user_biases(user_id=uid, venture_id=vid, db=db)
    behavior_risk  = await assess_behavioral_risk(user_id=uid, venture_id=vid, db=db)

    report_md = await generate_report(
        bias_analysis=bias_analysis,
        behavior_risk=behavior_risk,
    )
    print(report_md)
"""

from __future__ import annotations

import logging
import textwrap
from datetime import datetime, timezone

import anthropic

from agents.profiler import BiasAnalysis, TradingBehaviorRisk
from core.config import settings
from graph.knowledge_scanner import KnowledgeDoc, KnowledgeResult, scanner

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"


# ── Section helpers (pure / no LLM) ──────────────────────────────────────────

def _risk_bar(score: float) -> str:
    """Render a simple ASCII gauge for the behavioral risk score."""
    filled = round(score)
    bar = "█" * filled + "░" * (10 - filled)
    label = (
        "LOW" if score < 3.5
        else "MODERATE" if score < 6.5
        else "HIGH"
    )
    return f"`[{bar}]` **{score:.1f}/10** ({label})"


def _section_executive_summary(
    bias: BiasAnalysis,
    risk: TradingBehaviorRisk,
) -> str:
    top = bias.top_biases[0] if bias.top_biases else None
    bias_line = (
        f"The primary pattern identified is **{top.bias_name.replace('_', ' ').title()}** "
        f"(confidence {top.confidence:.0%}, severity {top.severity})."
        if top
        else "No dominant bias pattern was identified in this analysis window."
    )
    revenge_line = (
        f"{len(risk.revenge_trades)} revenge trade(s) were detected"
        if risk.revenge_trades
        else "No revenge trading was detected"
    )
    herding_line = (
        f"{len(risk.herding_signals)} herding signal(s) were flagged."
        if risk.herding_signals
        else "no herding signals were flagged."
    )
    return f"""## Executive Summary

> *Prepared by Neufin Behavioral Intelligence — {datetime.now(timezone.utc).strftime('%d %b %Y')}*

This report analyses the trading behaviour of client `{bias.user_id}` based on
their {bias.analyzed_trades} most recent trades (bias profiling) and
{risk.analyzed_trades} most recent trades (behavioral risk assessment).

{bias_line}
{revenge_line.rstrip('.')} and {herding_line}

**Behavioral Risk Score: {_risk_bar(risk.behavioral_risk_score)}**

{bias.overall_risk_assessment}
"""


def _section_risk_profile(risk: TradingBehaviorRisk) -> str:
    revenge_count = len(risk.revenge_trades)
    herding_count = len(risk.herding_signals)
    return f"""## Risk Profile

| Component | Value |
|---|---|
| Behavioral Risk Score | {_risk_bar(risk.behavioral_risk_score)} |
| Revenge Trades Detected | {revenge_count} |
| Herding Signals Detected | {herding_count} |
| Trades Assessed | {risk.analyzed_trades} |

**Summary:** {risk.risk_summary}
"""


def _section_detected_patterns(risk: TradingBehaviorRisk) -> str:
    parts: list[str] = ["## Detected Patterns\n"]

    if risk.revenge_trades:
        parts.append("### Revenge Trading\n")
        parts.append(
            "| Loss Trade | Asset | Loss At | Follow-Up Trade | Follow-Up Asset | Hours Apart |\n"
            "|---|---|---|---|---|---|\n"
        )
        for r in risk.revenge_trades:
            loss_at = r.loss_at[:16].replace("T", " ")
            follow_at = r.followup_at[:16].replace("T", " ")
            parts.append(
                f"| `{r.loss_trade_id[:8]}…` | {r.loss_asset} | {loss_at} "
                f"| `{r.followup_trade_id[:8]}…` | {r.followup_asset} | {r.hours_apart:.1f}h |\n"
            )
        parts.append("\n")
    else:
        parts.append("### Revenge Trading\n\n*No revenge trades detected.*\n\n")

    if risk.herding_signals:
        parts.append("### Herding Signals\n\n")
        parts.append(
            "| Trade | Asset | Traded At | Sentiment | News Mood |\n"
            "|---|---|---|---|---|\n"
        )
        for h in risk.herding_signals:
            traded_at = h.traded_at[:16].replace("T", " ")
            parts.append(
                f"| `{h.trade_id[:8]}…` | {h.asset} | {traded_at} "
                f"| {h.sentiment_score:+.2f} | {h.news_mood.upper()} |\n"
            )
        parts.append("\n")
    else:
        parts.append("### Herding Signals\n\n*No herding signals detected.*\n\n")

    return "".join(parts)


def _section_bias_analysis(bias: BiasAnalysis) -> str:
    parts: list[str] = ["## Cognitive Bias Analysis\n\n"]
    for i, b in enumerate(bias.top_biases, start=1):
        parts.append(
            f"### {i}. {b.bias_name.replace('_', ' ').title()}\n\n"
            f"- **Severity:** {b.severity.upper()}  \n"
            f"- **Confidence:** {b.confidence:.0%}  \n\n"
            f"{b.description}\n\n"
            f"**Trade Evidence:**\n\n"
        )
        parts.append(
            "| Trade ID | Asset | Traded At | Price | Sentiment | Observation |\n"
            "|---|---|---|---|---|---|\n"
        )
        for ev in b.evidence:
            traded_at = ev.traded_at[:16].replace("T", " ")
            obs = ev.observation[:80] + "…" if len(ev.observation) > 80 else ev.observation
            parts.append(
                f"| `{ev.trade_id[:8]}…` | {ev.asset} | {traded_at} "
                f"| {ev.price:.4f} | {ev.sentiment_score:+.2f} | {obs} |\n"
            )
        parts.append("\n")
    return "".join(parts)


# ── Section 5: Talking Points (LLM + KnowledgeScanner) ───────────────────────

_TALKING_POINTS_SYSTEM = """\
You are a Neufin Wealth Manager advisor writing THREE specific, actionable
talking points for a client meeting.  Each talking point:
  1. Is grounded in the client's actual trade data provided below.
  2. Avoids jargon — explain concepts in plain English.
  3. Offers a concrete next step the client can take before the next trade.
  4. Is framed positively and constructively — never accusatory.

Write exactly 3 numbered talking points, each 2–4 sentences.
Use the verified definitions below to ensure accuracy.\
"""


async def _section_talking_points(
    bias: BiasAnalysis,
    risk: TradingBehaviorRisk,
) -> str:
    # Build knowledge context for the top biases + behavioral patterns
    combined_query = (
        " ".join(b.bias_name for b in bias.top_biases)
        + " revenge trading herding suitability obligation"
    )
    knowledge_context = scanner.augment_prompt(combined_query, k=4)

    bias_summary = "\n".join(
        f"  {i+1}. {b.bias_name.replace('_', ' ').title()} "
        f"(severity={b.severity}, confidence={b.confidence:.0%}): {b.description[:150]}…"
        for i, b in enumerate(bias.top_biases)
    )

    user_content = (
        f"{knowledge_context}\n\n"
        f"## Client Data\n\n"
        f"**Behavioral Risk Score:** {risk.behavioral_risk_score:.1f}/10\n"
        f"**Top Biases Identified:**\n{bias_summary}\n"
        f"**Behavioral Risk Summary:** {risk.risk_summary}\n\n"
        f"Write the 3 Talking Points for the Advisor's client meeting."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=600,
        system=_TALKING_POINTS_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    talking_points_text = response.content[0].text.strip()  # type: ignore[index]

    logger.info(
        "generator: talking points drafted (%d chars) for user=%s",
        len(talking_points_text),
        bias.user_id,
    )
    return f"## Talking Points for the Client\n\n{talking_points_text}\n"


# ── Section 6: Compliance Check (PageIndex-style regulation retrieval) ────────

_COMPLIANCE_TOOL: anthropic.types.ToolParam = {
    "name": "compliance_verdict",
    "description": (
        "For each of the 3 talking points, assess whether it complies with "
        "MAS investment advisory regulations. Return a structured verdict."
    ),
    "input_schema": {
        "type": "object",
        "required": ["verdicts"],
        "properties": {
            "verdicts": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["talking_point_number", "compliant", "regulation_cited", "notes"],
                    "properties": {
                        "talking_point_number": {"type": "integer", "minimum": 1, "maximum": 3},
                        "compliant": {
                            "type": "boolean",
                            "description": "True if the talking point complies with cited regulation.",
                        },
                        "regulation_cited": {
                            "type": "string",
                            "description": "Short name of the MAS regulation being applied.",
                        },
                        "notes": {
                            "type": "string",
                            "description": (
                                "One sentence: explain why compliant, or what specific "
                                "change is needed to achieve compliance."
                            ),
                        },
                    },
                },
            }
        },
    },
}

_COMPLIANCE_SYSTEM = """\
You are a MAS (Monetary Authority of Singapore) compliance officer reviewing
advisor talking points for regulatory compliance.

Your task: For each of the 3 talking points, determine whether it complies
with the MAS regulations provided below.  Apply ONLY the regulations given —
do not invent regulatory requirements not stated in the context.

Use the compliance_verdict tool to return a structured assessment.\
"""


def _regulation_search(query: str, k: int = 3) -> list[KnowledgeResult]:
    """
    PageIndex-style retrieval: restrict BM25 search to the 'regulation'
    category only, then re-rank within that filtered subset.

    This ensures compliance checks reference authoritative MAS documents
    rather than bias definitions or calculation formulas.
    """
    regulation_docs = [doc for doc in scanner._docs if doc.category == "regulation"]
    if not regulation_docs:
        return []

    # Re-rank within the filtered subset using the global BM25 index positions
    all_results = scanner.search(query, k=len(scanner._docs))
    reg_ids = {doc.id for doc in regulation_docs}
    return [r for r in all_results if r.doc.id in reg_ids][:k]


async def _section_compliance_check(talking_points_text: str, bias: BiasAnalysis) -> str:
    bias_query = " ".join(b.bias_name for b in bias.top_biases)
    reg_query = f"suitability obligation disclosure client best interest {bias_query}"
    reg_results = _regulation_search(reg_query, k=3)

    if not reg_results:
        return (
            "## Compliance Check\n\n"
            "*Compliance check skipped — no regulation documents matched the query.*\n"
        )

    reg_context = "## Applicable MAS Regulations\n\n" + "\n\n".join(
        f"### {r.doc.title}\n{r.doc.content}" for r in reg_results
    )

    user_content = (
        f"{reg_context}\n\n"
        f"## Talking Points Under Review\n\n{talking_points_text}\n\n"
        "Apply compliance_verdict for all 3 talking points."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_COMPLIANCE_SYSTEM,
        tools=[_COMPLIANCE_TOOL],
        tool_choice={"type": "tool", "name": "compliance_verdict"},
        messages=[{"role": "user", "content": user_content}],
    )

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_block is None:
        logger.warning("compliance_check: no tool_use block returned")
        return "## Compliance Check\n\n*Compliance assessment unavailable.*\n"

    verdicts: list[dict] = tool_block.input.get("verdicts", [])  # type: ignore[union-attr]

    lines: list[str] = ["## Compliance Check\n\n"]
    lines.append(
        "| Talking Point | Compliant | Regulation | Notes |\n"
        "|---|---|---|---|\n"
    )
    for v in verdicts:
        status = "✅ Yes" if v.get("compliant") else "⚠️ Review"
        lines.append(
            f"| #{v.get('talking_point_number', '?')} "
            f"| {status} "
            f"| {v.get('regulation_cited', 'N/A')} "
            f"| {v.get('notes', '')} |\n"
        )

    reg_refs = "\n".join(
        f"- **{r.doc.title}** (score={r.score:.2f}): {r.doc.content[:120]}…"
        for r in reg_results
    )
    lines.append(f"\n**Regulations consulted:**\n{reg_refs}\n")

    logger.info(
        "compliance_check: %d verdicts for user=%s", len(verdicts), bias.user_id
    )
    return "".join(lines)


# ── Public entry point ────────────────────────────────────────────────────────

async def generate_report(
    *,
    bias_analysis: BiasAnalysis,
    behavior_risk: TradingBehaviorRisk,
) -> str:
    """
    Generate a full Markdown client report combining bias profiling and
    behavioral risk assessment results.

    Sections 1–4 are rendered without LLM calls.
    Sections 5–6 call claude-sonnet-4-6 with grounded knowledge context.

    Parameters
    ----------
    bias_analysis:
        Output of ``analyze_user_biases()`` — top 3 biases with trade evidence.
    behavior_risk:
        Output of ``assess_behavioral_risk()`` — risk score, revenge trades,
        herding signals.

    Returns
    -------
    str
        Complete Markdown report ready to render or store.
    """
    logger.info(
        "generator: building report for user=%s venture=%s",
        bias_analysis.user_id,
        bias_analysis.venture_id,
    )

    # Sections 1–4: pure data rendering (fast, no LLM)
    s1 = _section_executive_summary(bias_analysis, behavior_risk)
    s2 = _section_risk_profile(behavior_risk)
    s3 = _section_detected_patterns(behavior_risk)
    s4 = _section_bias_analysis(bias_analysis)

    # Section 5: LLM-generated advisor talking points
    s5 = await _section_talking_points(bias_analysis, behavior_risk)

    # Section 6: Compliance check against MAS regulations
    s6 = await _section_compliance_check(s5, bias_analysis)

    divider = "\n---\n\n"
    report = (
        f"# Neufin Behavioral Intelligence Report\n\n"
        + divider.join([s1, s2, s3, s4, s5, s6])
        + "\n---\n\n"
        f"*Generated by Neufin · {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z*\n"
    )

    logger.info(
        "generator: report complete (%d chars) for user=%s",
        len(report),
        bias_analysis.user_id,
    )
    return report

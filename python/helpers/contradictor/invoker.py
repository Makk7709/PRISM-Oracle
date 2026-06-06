# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CONTRADICTOR — LLM invoker (single-turn JSON review)            ║
║                                                                              ║
║  Owns the call to an LLM with:                                               ║
║  - the user question,                                                        ║
║  - the agent's response under review,                                        ║
║  - the route context (board-level signal, intents, AI Act category),         ║
║  - a strict JSON-only output contract,                                       ║
║  - a hard timeout,                                                           ║
║  - dirty-JSON tolerant parsing,                                              ║
║  - strict schema validation.                                                 ║
║                                                                              ║
║  The orchestration layer (`orchestration.py`) decides whether to call this   ║
║  function and how to translate the result into audit logs and human-review  ║
║  decisions.                                                                  ║
║                                                                              ║
║  NO RESPONSIBILITY FOR ROUTING OR DECISION-MAKING beyond the LLM call.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from python.helpers.contradictor.schema import (
    ContradictorReview,
    ContradictorStatus,
    validate_contradictor_output,
)

logger = logging.getLogger("contradictor_invoker")


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATE (kept here because the prompt and the parser are tightly
# coupled; the agents/contradictor/_context.md mirrors this contract for the
# Agent Zero profile flow).
# ═══════════════════════════════════════════════════════════════════════════════


CONTRADICTOR_PROMPT_TEMPLATE = """Tu es le Contradictor Agent du systeme KOREV Evidence.

POSTURE
- Revue hostile, contradictoire et exigeante.
- Tu n'es PAS l'auteur de la reponse finale a l'utilisateur.
- Tu evalues une reponse produite par d'autres agents.

CONTEXTE DE ROUTAGE
{route_context}

QUESTION ORIGINALE DE L'UTILISATEUR
{user_question}

REPONSE A AUDITER (produite par les agents metiers)
{agent_response}

MISSION
Identifie:
  1. Les contradictions internes ou logiques.
  2. Les preuves manquantes pour soutenir les claims.
  3. Les hypotheses fragiles ou non testees.
  4. Les risques juridiques, metier, securite, audit (AI Act, RGPD,
     responsabilite contractuelle).
  5. Les modes d'echec realistes si la reponse est suivie a la lettre.
  6. Les ajustements concrets a apporter.

REGLE ABSOLUE DE SORTIE
Reponds UNIQUEMENT avec un objet JSON valide, sans prose autour. Pas de
markdown, pas de backticks. Le JSON DOIT respecter EXACTEMENT ce schema:

{{
  "verdict": "challenge" | "no_major_objection",
  "risk_level": "low" | "medium" | "high" | "critical",
  "contradictions": [string, ...],
  "missing_evidence": [string, ...],
  "failure_modes": [string, ...],
  "legal_or_audit_risks": [string, ...],
  "recommended_adjustments": [string, ...],
  "confidence": float (0.0..1.0)
}}

Si tu n'identifies aucun probleme majeur, retourne quand meme un objet
complet avec verdict="no_major_objection", risk_level="low" et des listes
vides (mais le champ DOIT exister). Confiance = ta certitude dans ton audit.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def _format_route_context(route_decision: Optional[Dict[str, Any]]) -> str:
    """Render the relevant routing context as a small block in the prompt."""
    if not route_decision:
        return "(route decision indisponible)"

    intents = route_decision.get("intents") or []
    intent_lines = []
    for i in intents:
        name = i.get("name") if isinstance(i, dict) else str(i)
        score = i.get("score") if isinstance(i, dict) else None
        score_part = f" (score={score:.2f})" if isinstance(score, (int, float)) else ""
        intent_lines.append(f"- {name}{score_part}")

    parts = [
        f"verdict: {route_decision.get('verdict')}",
        f"is_board_level: {route_decision.get('is_board_level')}",
        f"requires_contradictor: {route_decision.get('requires_contradictor')}",
        f"ai_act_category: {route_decision.get('ai_act_category')}",
        f"data_sensitivity: {route_decision.get('data_sensitivity')}",
        "intents:",
    ]
    parts.extend(intent_lines or ["- (aucun intent detecte)"])
    return "\n".join(parts)


def build_contradictor_prompt(
    *,
    user_question: str,
    agent_response: str,
    route_decision: Optional[Dict[str, Any]],
) -> str:
    """Build the final prompt string sent to the LLM."""
    return CONTRADICTOR_PROMPT_TEMPLATE.format(
        route_context=_format_route_context(route_decision),
        user_question=user_question.strip(),
        agent_response=agent_response.strip(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# JSON EXTRACTION (dirty-JSON tolerant)
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_json_text(raw: str) -> str:
    """Strip common LLM artifacts (markdown fences, prose, leading/trailing junk)."""
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
        text = text.strip()
    elif text.startswith("```"):
        text = text.split("```", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


def parse_contradictor_response(raw: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Try to parse the raw LLM output to a dict.

    Returns:
        (payload, error). On success: (dict, None). On failure: (None, "...").
    """
    text = _extract_json_text(raw)
    if not text:
        return None, "empty response"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        try:
            from python.helpers.dirty_json import try_parse  # local import

            payload = try_parse(text)
            if not isinstance(payload, dict):
                return None, f"non-dict after dirty parse: {type(payload).__name__}"
            return payload, None
        except Exception:
            return None, f"JSON decode error: {exc.msg} at pos {exc.pos}"
    if not isinstance(payload, dict):
        return None, f"top-level JSON value must be an object, got {type(payload).__name__}"
    return payload, None


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT LLM CALLABLE (production wiring; lazy-imported to keep tests fast)
# ═══════════════════════════════════════════════════════════════════════════════


async def _default_llm_callable(prompt: str) -> str:
    """
    Default production callable: use the existing collaborative-consensus
    arbiter wiring to talk to a configured LLM.

    Tests inject their own callable instead — this code path is exercised
    only in production.
    """
    from python.helpers import llm_provider  # local import to avoid boot cost

    provider, model = ("openrouter", "anthropic/claude-3.5-sonnet")
    wrapper = llm_provider.get_provider(provider, model)
    return await wrapper.generate(prompt=prompt, temperature=0.1, max_tokens=2000)


LLMCallable = Callable[[str], Awaitable[str]]


# PUBLIC: invoke_contradictor
# ═══════════════════════════════════════════════════════════════════════════════


async def invoke_contradictor(
    *,
    user_question: str,
    agent_response: str,
    route_decision: Optional[Dict[str, Any]],
    correlation_id: str,
    llm_callable: Optional[LLMCallable] = None,
    timeout_ms: int = 20_000,
) -> ContradictorReview:
    """
    Invoke the contradictor LLM once and return a strict ContradictorReview.

    Lifecycle:
        - TIMEOUT      -> latency=elapsed, schema_errors=[], error_message="timeout"
        - ERROR        -> any other LLM-side exception, captured in error_message
        - SCHEMA_FAIL  -> JSON could not be parsed or did not match the schema
        - SUCCESS      -> validated ContradictorOutput attached
    """
    call = llm_callable or _default_llm_callable
    start = time.perf_counter()
    prompt = build_contradictor_prompt(
        user_question=user_question,
        agent_response=agent_response,
        route_decision=route_decision,
    )

    try:
        raw = await asyncio.wait_for(call(prompt), timeout=timeout_ms / 1000.0)
    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(
            "[CONTRADICTOR] timeout | correlation_id=%s | latency_ms=%s | timeout_ms=%s",
            correlation_id,
            elapsed_ms,
            timeout_ms,
        )
        return ContradictorReview(
            status=ContradictorStatus.TIMEOUT,
            correlation_id=correlation_id,
            latency_ms=elapsed_ms,
            error_message=f"contradictor LLM timeout after {timeout_ms}ms",
        )
    except Exception as exc:  # noqa: BLE001 - we re-classify
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "[CONTRADICTOR] error | correlation_id=%s | latency_ms=%s | err=%s",
            correlation_id,
            elapsed_ms,
            exc,
        )
        return ContradictorReview(
            status=ContradictorStatus.ERROR,
            correlation_id=correlation_id,
            latency_ms=elapsed_ms,
            error_message=str(exc),
        )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    payload, parse_err = parse_contradictor_response(raw)
    if payload is None:
        logger.warning(
            "[CONTRADICTOR] schema_fail (parse) | correlation_id=%s | latency_ms=%s | err=%s",
            correlation_id,
            elapsed_ms,
            parse_err,
        )
        return ContradictorReview(
            status=ContradictorStatus.SCHEMA_FAIL,
            correlation_id=correlation_id,
            latency_ms=elapsed_ms,
            schema_errors=[parse_err or "unknown parse error"],
        )

    output, schema_errors = validate_contradictor_output(payload)
    if output is None:
        logger.warning(
            "[CONTRADICTOR] schema_fail (validation) | correlation_id=%s | latency_ms=%s | errors=%s",
            correlation_id,
            elapsed_ms,
            schema_errors,
        )
        return ContradictorReview(
            status=ContradictorStatus.SCHEMA_FAIL,
            correlation_id=correlation_id,
            latency_ms=elapsed_ms,
            schema_errors=schema_errors,
        )

    logger.info(
        "[CONTRADICTOR] success | correlation_id=%s | latency_ms=%s | verdict=%s | risk=%s | conf=%.2f",
        correlation_id,
        elapsed_ms,
        output.verdict.value,
        output.risk_level.value,
        output.confidence,
    )
    return ContradictorReview(
        status=ContradictorStatus.SUCCESS,
        correlation_id=correlation_id,
        output=output,
        latency_ms=elapsed_ms,
    )


def skipped_review(correlation_id: str) -> ContradictorReview:
    """Build a no-op review for cases where the contradictor was not required."""
    return ContradictorReview(
        status=ContradictorStatus.SKIPPED,
        correlation_id=correlation_id,
        latency_ms=0,
    )


__all__ = [
    "CONTRADICTOR_PROMPT_TEMPLATE",
    "LLMCallable",
    "build_contradictor_prompt",
    "parse_contradictor_response",
    "invoke_contradictor",
    "skipped_review",
]

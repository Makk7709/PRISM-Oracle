"""
SESSION 14 — Tests: Art. 13 Transparency Narrative (E-10).

Validates exhaustively:

  A. ReasoningOutcome.to_safe_narrative()
    1. Basic narrative with confidence, steps, duration
    2. Narrative includes backtrack info when present
    3. Narrative includes flag labels in plain language
    4. Narrative truncates trace steps to max 10
    5. Narrative handles empty trace gracefully
    6. Narrative handles zero-confidence edge case
    7. Narrative handles high-confidence edge case
    8. to_safe_dict() now contains "narrative" key

  B. MetaDecision.to_safe_narrative()
    9. Basic narrative with confidence level, escalation
    10. Narrative includes uncertainty reasons
    11. Narrative mentions retry recommendation
    12. Narrative handles SAFE_REFUSE escalation
    13. Narrative handles no signals gracefully
    14. to_safe_dict() now contains "narrative" key

  C. AuditReportRenderer transparency section
    15. Section present when tracker has activated agents
    16. Section includes agent names and roles in plain language
    17. Section includes validation narrative when document is set
    18. Section includes confidence narrative when route_decision is set
    19. Section includes reasoning_narrative when provided
    20. Section includes meta_narrative when provided
    21. Section absent when no transparency data is available
    22. has_narrative property is True with tracker
    23. has_narrative property is True with route_decision only
    24. has_narrative property is False when nothing set

  D. ComplianceGrid Art. 13 with has_narrative
    25. Art. 13 status is CONFORME when narrative + session_id + tracker
    26. Art. 13 status is PARTIEL when no narrative
    27. Art. 13 evidence mentions narrative section when has_narrative=True
    28. Art. 13 gaps are empty when narrative is present

  E. _20_audit_metadata_append narrative resolution
    29. _resolve_reasoning_narrative returns narrative from agent data
    30. _resolve_reasoning_narrative returns None when no data
    31. _resolve_meta_narrative returns narrative from agent data
    32. _resolve_meta_narrative returns None when no data
    33. _resolve_reasoning_narrative handles malformed data gracefully

  F. Integration
    34. Full render() includes transparency section between compliance and source taxonomy
    35. Full render() transparency section readable by non-technical user (no CoT, no prompt)
    36. Duration formatting uses minutes when >= 60s
    37. AI Act category labels are in plain French
    38. Confidence label mapping covers all ranges
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ============================================================================
# A. ReasoningOutcome.to_safe_narrative()
# ============================================================================

class TestReasoningOutcomeNarrative:

    def _make_outcome(self, **overrides):
        from python.helpers.reasoning_engine import (
            ReasoningOutcome, TraceStep, ReasoningFlag,
        )
        defaults = dict(
            answer="Test answer",
            trace=[
                TraceStep(
                    step_id="s1",
                    timestamp="2026-04-02T10:00:00Z",
                    action="Analyse des sources financieres",
                    outcome="42 sources identifiees",
                    confidence=0.85,
                    duration_ms=1200,
                ),
                TraceStep(
                    step_id="s2",
                    timestamp="2026-04-02T10:00:01Z",
                    action="Consolidation des resultats",
                    outcome="Synthese produite",
                    confidence=0.90,
                    duration_ms=800,
                ),
            ],
            confidence=0.78,
            flags=[],
            debug_id="dbg-001",
            subtasks_completed=3,
            subtasks_total=4,
            backtracks_used=0,
            tool_calls_made=5,
            total_duration_ms=15000,
        )
        defaults.update(overrides)
        return ReasoningOutcome(**defaults)

    def test_01_basic_narrative_content(self):
        outcome = self._make_outcome()
        narrative = outcome.to_safe_narrative()
        assert "2 etape(s) de raisonnement" in narrative
        assert "3/4 sous-taches completees" in narrative
        assert "15.0 secondes" in narrative
        assert "bonne" in narrative
        assert "78%" in narrative

    def test_02_backtrack_info_included(self):
        outcome = self._make_outcome(backtracks_used=3)
        narrative = outcome.to_safe_narrative()
        assert "reconsidere son approche 3 fois" in narrative

    def test_03_flag_labels_plain_language(self):
        from python.helpers.reasoning_engine import ReasoningFlag
        outcome = self._make_outcome(
            flags=[ReasoningFlag.UNCERTAIN, ReasoningFlag.NEEDS_HUMAN]
        )
        narrative = outcome.to_safe_narrative()
        assert "Incertitude detectee" in narrative
        assert "Verification humaine recommandee" in narrative
        assert "UNCERTAIN" not in narrative
        assert "NEEDS_HUMAN" not in narrative

    def test_04_trace_steps_truncated_at_10(self):
        from python.helpers.reasoning_engine import TraceStep
        steps = [
            TraceStep(
                step_id=f"s{i}",
                timestamp="2026-04-02T10:00:00Z",
                action=f"Action {i}",
                outcome=f"Result {i}",
                confidence=0.5,
                duration_ms=100,
            )
            for i in range(15)
        ]
        outcome = self._make_outcome(trace=steps)
        narrative = outcome.to_safe_narrative()
        assert "Action 9" in narrative
        assert "Action 10" not in narrative

    def test_05_empty_trace_graceful(self):
        outcome = self._make_outcome(trace=[])
        narrative = outcome.to_safe_narrative()
        assert "0 etape(s) de raisonnement" in narrative
        assert "Etapes principales" not in narrative

    def test_06_zero_confidence(self):
        outcome = self._make_outcome(confidence=0.0)
        narrative = outcome.to_safe_narrative()
        assert "faible" in narrative
        assert "0%" in narrative

    def test_07_high_confidence(self):
        outcome = self._make_outcome(confidence=0.95)
        narrative = outcome.to_safe_narrative()
        assert "elevee" in narrative
        assert "95%" in narrative

    def test_08_safe_dict_contains_narrative(self):
        outcome = self._make_outcome()
        safe = outcome.to_safe_dict()
        assert "narrative" in safe
        assert isinstance(safe["narrative"], str)
        assert len(safe["narrative"]) > 50


# ============================================================================
# B. MetaDecision.to_safe_narrative()
# ============================================================================

class TestMetaDecisionNarrative:

    def _make_decision(self, **overrides):
        from python.helpers.metacognition import (
            MetaDecision, ConfidenceAnalysis, ConfidenceLevel,
            EscalationType, MemoryHint,
        )
        defaults = dict(
            confidence=0.72,
            confidence_analysis=ConfidenceAnalysis(
                overall=0.72,
                level=ConfidenceLevel.MEDIUM,
                factors={"coherence": 0.8, "source_quality": 0.65},
                signals=[],
            ),
            uncertainty_reasons=["Donnees partiellement disponibles"],
            escalation=EscalationType.NONE,
            clarification_questions=[],
            memory_hints=[],
            should_retry=False,
            debug_id="meta-001",
        )
        defaults.update(overrides)
        return MetaDecision(**defaults)

    def test_09_basic_narrative(self):
        decision = self._make_decision()
        narrative = decision.to_safe_narrative()
        assert "moderee" in narrative
        assert "72%" in narrative
        assert "2 facteur(s) d'analyse" in narrative
        assert "Aucune escalade necessaire" in narrative

    def test_10_uncertainty_reasons_included(self):
        decision = self._make_decision(
            uncertainty_reasons=[
                "Donnees partiellement disponibles",
                "Sources contradictoires",
            ]
        )
        narrative = decision.to_safe_narrative()
        assert "Donnees partiellement disponibles" in narrative
        assert "Sources contradictoires" in narrative

    def test_11_retry_recommendation(self):
        decision = self._make_decision(should_retry=True)
        narrative = decision.to_safe_narrative()
        assert "nouvelle tentative" in narrative

    def test_12_safe_refuse_escalation(self):
        from python.helpers.metacognition import EscalationType
        decision = self._make_decision(escalation=EscalationType.SAFE_REFUSE)
        narrative = decision.to_safe_narrative()
        assert "Refus de traitement par mesure de precaution" in narrative

    def test_13_no_signals_graceful(self):
        decision = self._make_decision()
        narrative = decision.to_safe_narrative()
        assert "signal" not in narrative.lower() or "0 signal" in narrative.lower()

    def test_14_safe_dict_contains_narrative(self):
        decision = self._make_decision()
        safe = decision.to_safe_dict()
        assert "narrative" in safe
        assert isinstance(safe["narrative"], str)
        assert len(safe["narrative"]) > 30

    def test_14b_signals_count_mentioned_when_present(self):
        from python.helpers.metacognition import (
            ConfidenceAnalysis, ConfidenceLevel,
            UncertaintySignal, UncertaintyType,
        )
        analysis = ConfidenceAnalysis(
            overall=0.45,
            level=ConfidenceLevel.LOW,
            factors={"coherence": 0.5},
            signals=[
                UncertaintySignal(
                    type=UncertaintyType.CONTRADICTORY_DATA,
                    description="Sources divergent",
                    severity=0.8,
                    source="llm_response",
                ),
                UncertaintySignal(
                    type=UncertaintyType.MISSING_INFORMATION,
                    description="Donnees manquantes",
                    severity=0.6,
                    source="tool_execution",
                ),
            ],
        )
        decision = self._make_decision(confidence_analysis=analysis)
        narrative = decision.to_safe_narrative()
        assert "2 signal(aux)" in narrative

    def test_14c_human_review_escalation_label(self):
        from python.helpers.metacognition import EscalationType
        decision = self._make_decision(escalation=EscalationType.HUMAN_REVIEW)
        narrative = decision.to_safe_narrative()
        assert "Revue humaine requise avant validation" in narrative

    def test_14d_ask_clarify_escalation_label(self):
        from python.helpers.metacognition import EscalationType
        decision = self._make_decision(escalation=EscalationType.ASK_CLARIFY)
        narrative = decision.to_safe_narrative()
        assert "Demande de clarification" in narrative


# ============================================================================
# C. AuditReportRenderer transparency section
# ============================================================================

def _make_tracker(agents=None):
    from python.helpers.pipeline_tracker import PipelineTracker
    tracker = PipelineTracker()
    for name in (agents or ["researcher", "finance"]):
        tracker.start_step(name)
        tracker.complete_step(name)
    return tracker


def _make_envelope():
    from python.helpers.session_envelope import SessionEnvelope
    return SessionEnvelope(
        session_id="KRV-TEST-001",
        username="testuser",
        organization="TestOrg",
    )


def _make_route_decision():
    from python.helpers.router.routing_contract import (
        RouteDecision, RouteVerdict, RouteIntent, IntentName, AIActCategory,
    )
    return RouteDecision(
        verdict=RouteVerdict.PROCEED,
        intents=[RouteIntent(name=IntentName.FINANCE, score=0.9)],
        routing_strength=0.85,
        is_board_level=True,
        reasons=["Strategic pipeline: financial analysis", "103 sources, PASS"],
        route_id="test-corr",
        ai_act_category=AIActCategory.HIGH_RISK,
    )


class TestRendererTransparencySection:

    def test_15_section_present_with_tracker(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
        )
        result = renderer.render()
        assert "### Transparence du raisonnement" in result

    def test_16_agent_names_and_roles_in_plain_language(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher", "finance", "marketing", "sales"]),
            response="Test response",
        )
        result = renderer.render()
        assert "Researcher" in result
        assert "Recherche documentaire" in result
        assert "Finance" in result
        assert "Analyse financiere" in result
        assert "Marketing" in result
        assert "Sales" in result

    def test_17_validation_narrative_when_document_set(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
            document="Le document strategique consolide",
        )
        result = renderer.render()
        assert "document strategique consolide" in result

    def test_18_confidence_narrative_when_route_decision_set(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            route_decision=_make_route_decision(),
            response="Test response",
        )
        result = renderer.render()
        assert "elevee" in result
        assert "85%" in result
        assert "risque eleve" in result

    def test_19_reasoning_narrative_included(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
            reasoning_narrative="Le systeme a execute 5 etapes de raisonnement.",
        )
        result = renderer.render()
        assert "Raisonnement interne" in result
        assert "5 etapes de raisonnement" in result

    def test_20_meta_narrative_included(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
            meta_narrative="Evaluation metacognitive : confiance elevee.",
        )
        result = renderer.render()
        assert "Evaluation metacognitive" in result

    def test_21_section_absent_when_no_data(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            response="Test response",
        )
        result = renderer.render()
        assert "### Transparence du raisonnement" not in result

    def test_22_has_narrative_true_with_tracker(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            tracker=_make_tracker(),
        )
        assert renderer.has_narrative is True

    def test_23_has_narrative_true_with_route_decision_only(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            route_decision=_make_route_decision(),
        )
        assert renderer.has_narrative is True

    def test_24_has_narrative_false_when_empty(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer()
        assert renderer.has_narrative is False


# ============================================================================
# D. ComplianceGrid Art. 13 with has_narrative
# ============================================================================

class TestComplianceGridArt13Narrative:

    def test_25_art13_conforme_with_narrative(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_narrative=True,
        )
        art13 = grid.checks[0]
        assert art13.article == "Art. 13 AI Act (2024/1689)"
        assert art13.status == ComplianceStatus.CONFORME

    def test_26_art13_partiel_without_narrative(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_narrative=False,
        )
        art13 = grid.checks[0]
        assert art13.status == ComplianceStatus.PARTIEL

    def test_27_art13_evidence_mentions_narrative(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_narrative=True,
        )
        art13 = grid.checks[0]
        assert "Transparence du raisonnement" in art13.evidence

    def test_28_art13_no_gaps_when_narrative_present(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_narrative=True,
        )
        art13 = grid.checks[0]
        assert art13.gaps == ""


# ============================================================================
# E. _20_audit_metadata_append narrative resolution
# ============================================================================

def _make_hook():
    from python.extensions.monologue_start._20_audit_metadata_append import (
        AuditMetadataAppend,
    )
    agent = MagicMock()
    stored = {}
    agent.set_data = lambda k, v: stored.__setitem__(k, v)
    agent.get_data = lambda k: stored.get(k)
    hook = AuditMetadataAppend.__new__(AuditMetadataAppend)
    hook.agent = agent
    hook._stored = stored
    return hook


class TestResolveNarratives:

    def test_29_resolve_reasoning_narrative_from_data(self):
        hook = _make_hook()
        hook.agent.get_data = lambda k: (
            {"narrative": "Le systeme a execute 3 etapes."}
            if k == "_reasoning_outcome_safe" else None
        )
        result = hook._resolve_reasoning_narrative()
        assert result == "Le systeme a execute 3 etapes."

    def test_30_resolve_reasoning_narrative_none_when_absent(self):
        hook = _make_hook()
        result = hook._resolve_reasoning_narrative()
        assert result is None

    def test_31_resolve_meta_narrative_from_data(self):
        hook = _make_hook()
        hook.agent.get_data = lambda k: (
            {"narrative": "Confiance elevee."}
            if k == "_meta_decision_safe" else None
        )
        result = hook._resolve_meta_narrative()
        assert result == "Confiance elevee."

    def test_32_resolve_meta_narrative_none_when_absent(self):
        hook = _make_hook()
        result = hook._resolve_meta_narrative()
        assert result is None

    def test_33_resolve_reasoning_narrative_malformed_data(self):
        hook = _make_hook()
        hook.agent.get_data = lambda k: (
            "not-a-dict" if k == "_reasoning_outcome_safe" else None
        )
        result = hook._resolve_reasoning_narrative()
        assert result is None

    def test_33b_resolve_meta_narrative_malformed_data(self):
        hook = _make_hook()
        hook.agent.get_data = lambda k: (
            42 if k == "_meta_decision_safe" else None
        )
        result = hook._resolve_meta_narrative()
        assert result is None

    def test_33c_resolve_reasoning_narrative_dict_without_narrative_key(self):
        hook = _make_hook()
        hook.agent.get_data = lambda k: (
            {"debug_id": "x", "confidence": 0.5}
            if k == "_reasoning_outcome_safe" else None
        )
        result = hook._resolve_reasoning_narrative()
        assert result is None


# ============================================================================
# F. Integration tests
# ============================================================================

class TestIntegrationFullRender:

    def test_34_transparency_between_compliance_and_sources(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher", "finance", "marketing"]),
            route_decision=_make_route_decision(),
            query="Analyse strategique DICA France",
            response="Resultat de l'analyse",
            document="Le document strategique",
        )
        result = renderer.render()
        compliance_pos = result.find("### Grille de conformite")
        transparency_pos = result.find("### Transparence du raisonnement")
        metadata_pos = result.find("### Metadonnees techniques")
        assert compliance_pos < transparency_pos < metadata_pos

    def test_35_no_cot_no_prompt_in_narrative(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            route_decision=_make_route_decision(),
            response="Test",
        )
        result = renderer.render()
        transparency_start = result.find("### Transparence du raisonnement")
        next_section = result.find("###", transparency_start + 10)
        if next_section == -1:
            next_section = len(result)
        narrative_text = result[transparency_start:next_section]

        forbidden_terms = [
            "prompt", "system_message", "chain_of_thought",
            "CoT", "temperature", "top_p", "max_tokens",
            "openrouter", "anthropic", "claude",
            "gpt-4", "gpt-3", "llama",
        ]
        for term in forbidden_terms:
            assert term.lower() not in narrative_text.lower(), (
                f"Forbidden term '{term}' found in transparency narrative"
            )

    def test_36_duration_minutes_format(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.pipeline_tracker import PipelineTracker
        import time

        tracker = PipelineTracker()
        tracker.start_step("researcher")
        step = tracker._steps["researcher"]
        step._start_monotonic = time.monotonic() - 125
        tracker.complete_step("researcher")

        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=tracker,
            response="Test",
        )
        result = renderer.render()
        assert "2 min" in result

    def test_37_ai_act_category_labels_french(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.router.routing_contract import (
            RouteDecision, RouteVerdict, RouteIntent, IntentName, AIActCategory,
        )
        for cat, expected_label in [
            (AIActCategory.MINIMAL_RISK, "risque minimal"),
            (AIActCategory.LIMITED_RISK, "risque limite"),
            (AIActCategory.HIGH_RISK, "risque eleve"),
            (AIActCategory.UNACCEPTABLE, "risque inacceptable"),
        ]:
            rd = RouteDecision(
                verdict=RouteVerdict.PROCEED,
                intents=[RouteIntent(name=IntentName.FINANCE, score=0.9)],
                routing_strength=0.7,
                is_board_level=True,
                reasons=["test"],
                route_id="t",
                ai_act_category=cat,
            )
            renderer = AuditReportRenderer(
                envelope=_make_envelope(),
                tracker=_make_tracker(),
                route_decision=rd,
                response="Test",
            )
            result = renderer.render()
            assert expected_label in result, (
                f"Expected '{expected_label}' for {cat.name} in render output"
            )

    def test_38_confidence_label_all_ranges(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.router.routing_contract import (
            RouteDecision, RouteVerdict, RouteIntent, IntentName,
        )
        for strength, expected_label in [
            (0.15, "faible"),
            (0.45, "moderee"),
            (0.65, "bonne"),
            (0.92, "elevee"),
        ]:
            rd = RouteDecision(
                verdict=RouteVerdict.PROCEED,
                intents=[RouteIntent(name=IntentName.FINANCE, score=0.9)],
                routing_strength=strength,
                is_board_level=False,
                reasons=["test"],
                route_id="t",
            )
            renderer = AuditReportRenderer(
                envelope=_make_envelope(),
                tracker=_make_tracker(),
                route_decision=rd,
                response="Test",
            )
            result = renderer.render()
            assert expected_label in result, (
                f"Expected '{expected_label}' for strength={strength}"
            )

    def test_38b_human_review_narrative(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test",
            has_human_review=True,
        )
        result = renderer.render()
        assert "revue humaine" in result.lower()

    def test_38c_consensus_narrative(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test",
            has_consensus=True,
        )
        result = renderer.render()
        assert "consensus" in result.lower()

    def test_38d_art13_intro_mentions_ai_act(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test",
        )
        result = renderer.render()
        assert "Art. 13" in result
        assert "AI Act" in result
        assert "2024/1689" in result

    def test_38e_has_narrative_true_with_human_review(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(has_human_review=True)
        assert renderer.has_narrative is True

    def test_38f_has_narrative_true_with_consensus(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(has_consensus=True)
        assert renderer.has_narrative is True

    def test_38g_has_narrative_true_with_document(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(document="A document")
        assert renderer.has_narrative is True

    def test_38h_has_narrative_true_with_reasoning_narrative(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(reasoning_narrative="some narrative")
        assert renderer.has_narrative is True

    def test_38i_has_narrative_true_with_meta_narrative(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(meta_narrative="some meta")
        assert renderer.has_narrative is True

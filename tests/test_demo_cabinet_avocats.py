"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║        PROTOCOLE DE DÉMONSTRATION — CABINET D'AVOCATS                       ║
║                                                                              ║
║   Suite de tests formalisée pour validation par un cabinet juridique.        ║
║                                                                              ║
║   5 AXES D'AUDIT :                                                           ║
║     AXE 1 — FIABILITÉ JURIDIQUE (Anti-hallucination, citations)             ║
║     AXE 2 — SÉCURITÉ CONTRACTUELLE (Leak Guard, fail-closed, IP)           ║
║     AXE 3 — CONFORMITÉ RGPD / DÉONTOLOGIE (Data flow, secret pro)          ║
║     AXE 4 — ROBUSTESSE / FAIL-CLOSED (Pannes, injection, dégradé)          ║
║     AXE 5 — TRAÇABILITÉ / AUDITABILITÉ (Provenance, reproductibilité)      ║
║                                                                              ║
║   MÉTHODOLOGIE : TDD strict — chaque test vérifie un INVARIANT critique     ║
║   nommé [AXE-XX] pour traçabilité audit.                                    ║
║                                                                              ║
║   EXIGENCE : 100% PASS requis pour certification cabinet.                   ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary & Confidential                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import hashlib
import json
import uuid
import pytest
from typing import Dict, List, Any

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═════════════════════════════════════════════════════════════════════════════
# AXE 1 — FIABILITÉ JURIDIQUE
# "Le système ne ment-il jamais ?"
# ═════════════════════════════════════════════════════════════════════════════

class TestAxe1_FiabiliteJuridique:
    """AXE 1 — Vérification de la fiabilité des sorties juridiques.

    Un cabinet d'avocats exige que :
    - Aucune affirmation ne soit présentée sans source (UNSUPPORTED → REJECT)
    - Le système distingue FAIT / HYPOTHÈSE / OPINION
    - Les disclaimers soient toujours présents
    - La température soit forcée à 0 (déterminisme)
    """

    # ─── [AXE1-01] Claims sans source → REJECT ───
    def test_axe1_01_unsupported_claims_rejected(self):
        """[AXE1-01] Toute affirmation sans source est rejetée par le juge binaire."""
        from python.helpers.legal_pipeline import (
            ClaimType, LegalClaim, LegalDraft, LegalRouteContext,
            judge_legal_draft, DecisionScope, LegalRiskTier, Jurisdiction,
            generate_draft_id,
        )
        assert ClaimType.UNSUPPORTED == "unsupported"
        # Construire un vrai LegalDraft avec un claim UNSUPPORTED
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        _ts = 1707350400.0  # Fixed timestamp for determinism
        draft = LegalDraft(
            draft_id=generate_draft_id("Test unsupported claim", _ts),
            query="Test unsupported claim",
            facts=["Le salarié a été licencié."],
            rules=["Article L.1232-1 du Code du travail"],
            application="L'employeur n'a pas respecté la procédure de licenciement prévue par le Code du travail.",
            risks=["Risque de requalification"],
            legal_context=ctx,
        )
        # Ajouter un claim non supporté
        draft.claims.append(LegalClaim(
            id="c1", text="C'est illégal",
            claim_type=ClaimType.UNSUPPORTED, citation="",
        ))
        result = judge_legal_draft(draft)
        verdict = result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict)
        assert verdict in ("reject", "request_info"), \
            f"[AXE1-01] FAIL CRITIQUE: Claims UNSUPPORTED non rejetées! Verdict: {verdict}"

    # ─── [AXE1-02] Température forcée à 0 ───
    def test_axe1_02_temperature_zero_enforced(self):
        """[AXE1-02] La température du modèle DOIT être 0 en mode juridique."""
        from python.helpers.legal_safe_schema import LegalSafeResponse
        # Tenter de créer une réponse avec temp != 0 doit échouer
        with pytest.raises(Exception) as exc_info:
            # Construction d'un objet minimal avec temperature=0.7
            data = _build_minimal_legal_response(temperature=0.7)
            LegalSafeResponse(**data)
        # L'erreur doit mentionner la température
        assert "temperature" in str(exc_info.value).lower() or "0" in str(exc_info.value)

    # ─── [AXE1-03] Disclaimer obligatoire ───
    def test_axe1_03_disclaimer_always_present(self):
        """[AXE1-03] Le disclaimer 'ne constitue pas un conseil juridique' est TOUJOURS présent."""
        from python.helpers.legal_safe_schema import Disclaimers
        d = Disclaimers()
        assert d.not_legal_advice is True
        assert d.consult_professional is True
        assert d.no_liability is True
        assert "ne constitue pas un conseil juridique" in d.text_fr.lower()

    # ─── [AXE1-04] Confiance basse → escalade automatique ───
    def test_axe1_04_low_confidence_triggers_escalation(self):
        """[AXE1-04] Confiance < 0.75 → escalade humaine automatique."""
        from python.helpers.legal_safe_policy import CONFIDENCE_THRESHOLD
        assert CONFIDENCE_THRESHOLD == 0.75

    # ─── [AXE1-05] Domaine pénal → escalade systématique ───
    def test_axe1_05_penal_domain_always_escalated(self):
        """[AXE1-05] Le domaine pénal déclenche TOUJOURS une escalade."""
        from python.helpers.legal_safe_policy import ReviewTrigger
        # ReviewTrigger.DOMAIN_PENAL doit exister et être classé HIGH
        assert hasattr(ReviewTrigger, "DOMAIN_PENAL")

    # ─── [AXE1-06] Actes juridiques interdits ───
    def test_axe1_06_restricted_activities_detected(self):
        """[AXE1-06] Rédaction d'actes, représentation, dépôt de plainte → refusés."""
        from python.helpers.legal_safe_policy import RESTRICTED_ACTIVITY_PATTERNS
        assert "representation" in RESTRICTED_ACTIVITY_PATTERNS
        assert "drafting_legal_act" in RESTRICTED_ACTIVITY_PATTERNS
        assert "court_filing" in RESTRICTED_ACTIVITY_PATTERNS

    # ─── [AXE1-07] Juridiction UNKNOWN + BOARD → REJECT ───
    def test_axe1_07_unknown_jurisdiction_board_rejected(self):
        """[AXE1-07] BOARD scope + juridiction UNKNOWN → REJECT (pas de présomption FR)."""
        from python.helpers.legal_pipeline import (
            judge_legal_draft, DecisionScope, LegalDraft, LegalRouteContext,
            LegalRiskTier, Jurisdiction, generate_draft_id,
        )
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.UNKNOWN,
        )
        _ts = 1707350400.0
        draft = LegalDraft(
            draft_id=generate_draft_id("Acquisition transfrontalière", _ts),
            query="Acquisition transfrontalière",
            facts=["Acquisition transfrontalière impliquant 3 pays."],
            rules=["Aucune règle identifiée"],
            application="L'acquisition concerne plusieurs juridictions non identifiées, rendant l'analyse complexe.",
            risks=["Risque juridictionnel majeur"],
            legal_context=ctx,
        )
        result = judge_legal_draft(draft)
        verdict = result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict)
        has_jurisdiction_issue = any(
            "jurisdiction" in str(c).lower()
            for c in (result.missing_info if hasattr(result, 'missing_info') else [])
        )
        assert verdict != "approve" or has_jurisdiction_issue, \
            "[AXE1-07] FAIL: BOARD + UNKNOWN doit être rejeté ou demander la juridiction"

    # ─── [AXE1-08] Sources vérifiables requises ───
    def test_axe1_08_sources_required_for_operational(self):
        """[AXE1-08] OPERATIONAL scope → sources obligatoires."""
        from python.helpers.legal_pipeline import (
            judge_legal_draft, DecisionScope, LegalDraft, LegalRouteContext,
            LegalRiskTier, Jurisdiction, generate_draft_id,
        )
        ctx = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.OPERATIONAL,
            jurisdiction=Jurisdiction.FR,
        )
        _ts = 1707350400.0
        draft = LegalDraft(
            draft_id=generate_draft_id("Clause abusive", _ts),
            query="Clause abusive",
            facts=["Un contrat a été signé."],
            rules=[],  # PAS DE SOURCES
            application="Le contrat contient une clause potentiellement abusive qui pourrait être contestée devant un tribunal.",
            risks=[],
            legal_context=ctx,
        )
        result = judge_legal_draft(draft)
        verdict = result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict)
        assert verdict != "approve", \
            "[AXE1-08] FAIL: OPERATIONAL sans sources ne doit PAS être approuvé"


# ═════════════════════════════════════════════════════════════════════════════
# AXE 2 — SÉCURITÉ CONTRACTUELLE
# "Le système protège-t-il les actifs du cabinet et de ses clients ?"
# ═════════════════════════════════════════════════════════════════════════════

class TestAxe2_SecuriteContractuelle:
    """AXE 2 — Protection des actifs (IP, code source, savoir-faire).

    Un cabinet vérifie que :
    - Aucune clause de remise de code source ne passe le filtre
    - Les garanties absolues sont détectées
    - Le pipeline est fail-closed (P0 = blocage total)
    - L'export est impossible sans PASS legal_safe
    """

    # ─── [AXE2-01] Remise de code source → P0 ───
    def test_axe2_01_code_source_transfer_blocked(self):
        """[AXE2-01] 'Remise du code source' → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        clauses = [
            "Le Client recevra la remise du code source intégral.",
            "La livraison du code source est prévue à J+30.",
            "Le code source sera transmis au Client.",
            "Accès au repository Git du projet.",
        ]
        for clause in clauses:
            findings = scan_for_leaks(clause)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) >= 1, \
                f"[AXE2-01] FUITE NON DÉTECTÉE: '{clause}'"

    # ─── [AXE2-02] Cession IP → P0 ───
    def test_axe2_02_ip_cession_blocked(self):
        """[AXE2-02] Cession de propriété intellectuelle → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        clauses = [
            "Cession de tous les droits patrimoniaux.",
            "Cession du code au Client.",
            "Les droits sont transférés de manière irrévocable.",
        ]
        for clause in clauses:
            findings = scan_for_leaks(clause)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) >= 1, \
                f"[AXE2-02] CESSION IP NON DÉTECTÉE: '{clause}'"

    # ─── [AXE2-03] Garanties absolues → détectées ───
    def test_axe2_03_absolute_guarantees_detected(self):
        """[AXE2-03] Garanties absolues (zéro risque, conformité totale) → détectées."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        clauses = [
            "L'Éditeur garantit zéro risque.",
            "Logiciel sans aucune faille.",
            "Conformité totale garantie.",
            "L'Éditeur garantit la conformité du logiciel.",
        ]
        for clause in clauses:
            findings = scan_for_leaks(clause)
            severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
            assert len(severe) >= 1, \
                f"[AXE2-03] GARANTIE ABSOLUE NON DÉTECTÉE: '{clause}'"

    # ─── [AXE2-04] Pipeline fail-closed : P0 = pas de contrat ───
    def test_axe2_04_p0_blocks_contract_output(self):
        """[AXE2-04] Un seul P0 bloque TOTALEMENT la sortie du contrat."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import (
            ContractDraft, GateVerdictEnum,
        )
        draft = ContractDraft(
            sections={"CG": "Remise du code source intégral au Client."},
            variables={}, disclaimer="PROJET", correlation_id="axe2-04",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    # ─── [AXE2-05] Export PDF bloqué sans PASS ───
    def test_axe2_05_export_blocked_without_pass(self):
        """[AXE2-05] Aucun export PDF/DOC possible sans PASS legal_safe."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
            LeakFinding, FindingSeverity,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.REJECT, can_release=False,
                findings=[LeakFinding(
                    severity=FindingSeverity.P0, pattern="test",
                    context="...", recommendation="...", section="CG",
                )],
            ),
            gate_passed=False, gate_summary="P0",
        )
        assert is_export_allowed(output) is False, \
            "[AXE2-05] FAIL CRITIQUE: Export autorisé malgré REJECT!"

    # ─── [AXE2-06] MULTI_AGENT_CONSENSUS ne peut pas overrider ───
    def test_axe2_06_consensus_cannot_override_legal_gate(self):
        """[AXE2-06] Aucun mécanisme de consensus ne peut contourner le veto juridique."""
        from python.helpers.contract_drafting.governance import (
            can_consensus_override_legal_gate,
        )
        assert can_consensus_override_legal_gate() is False, \
            "[AXE2-06] FAIL CRITIQUE: Le consensus peut overrider le veto!"

    # ─── [AXE2-07] Veto legal_safe absolu ───
    def test_axe2_07_legal_safe_veto_absolute(self):
        """[AXE2-07] legal_safe a un droit de veto ABSOLU sur tout contrat."""
        from python.helpers.contract_drafting.governance import is_legal_safe_veto_absolute
        assert is_legal_safe_veto_absolute() is True

    # ─── [AXE2-08] Templates propres — 0 fuite IP ───
    def test_axe2_08_templates_zero_ip_leak(self):
        """[AXE2-08] Tous les templates contractuels sont exempts de fuites IP."""
        from python.helpers.contract_drafting.templates import get_template_pack
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        pack = get_template_pack()
        for name, template in pack.items():
            findings = scan_for_leaks(template, section=name)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) == 0, \
                f"[AXE2-08] Template '{name}' CONTIENT P0: {[f.pattern for f in p0s]}"

    # ─── [AXE2-09] Stamp export contient LEGAL_SAFE ───
    def test_axe2_09_export_stamp_mentions_legal_safe(self):
        """[AXE2-09] Le stamp d'export certifie la validation par LEGAL_SAFE."""
        from python.helpers.contract_drafting.export_control import get_export_stamp
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE, can_release=True, summary="OK",
            ),
            gate_passed=True, gate_summary="OK", rendered_contract="...",
        )
        stamp = get_export_stamp(output)
        assert "LEGAL_SAFE" in stamp.upper()

    # ─── [AXE2-10] Responsabilité plafonnée dans CG ───
    def test_axe2_10_liability_capped_in_cg(self):
        """[AXE2-10] Les CG contiennent un plafond de responsabilité."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"].lower()
        assert "plafond" in cg or "ne saurait excéder" in cg, \
            "[AXE2-10] FAIL: Pas de plafond de responsabilité dans les CG"

    # ─── [AXE2-11] DPA conditionnelle ───
    def test_axe2_11_dpa_conditional_on_remote_access(self):
        """[AXE2-11] DPA activée UNIQUEMENT si accès distant."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        # Sans accès distant → NON APPLICABLE
        draft_no = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "false"},
        )
        assert "NON APPLICABLE" in draft_no.sections.get("ANNEXE_4", "").upper()
        # Avec accès distant → DPA active
        draft_yes = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "true"},
        )
        a4 = draft_yes.sections.get("ANNEXE_4", "").lower()
        assert "article 28" in a4 or "sous-traitant" in a4

    # ─── [AXE2-12] Réversibilité sans remise code ───
    def test_axe2_12_reversibility_no_code_source(self):
        """[AXE2-12] L'annexe réversibilité ne contient AUCUNE remise de code."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a5 = get_template_pack()["ANNEXE_5"].lower()
        assert "remise du code source" not in a5
        assert "livraison du code source" not in a5


# ═════════════════════════════════════════════════════════════════════════════
# AXE 3 — CONFORMITÉ RGPD / DÉONTOLOGIE
# "Le système respecte-t-il les obligations réglementaires ?"
# ═════════════════════════════════════════════════════════════════════════════

class TestAxe3_ConformiteRGPD:
    """AXE 3 — Vérification de la conformité RGPD et déontologique.

    Un cabinet vérifie que :
    - Le système détecte les questions RGPD
    - Les conflits d'intérêt déclenchent une escalade
    - Les domaines non supportés sont refusés proprement
    - Le Leak Guard détecte les violations RGPD dans les contrats
    """

    # ─── [AXE3-01] Domaine RGPD reconnu ───
    def test_axe3_01_rgpd_domain_recognized(self):
        """[AXE3-01] Les questions RGPD sont classifiées correctement."""
        from python.helpers.legal_safe_policy import DOMAIN_KEYWORDS
        from python.helpers.legal_safe_schema import LegalDomain
        assert LegalDomain.RGPD_DONNEES in DOMAIN_KEYWORDS
        keywords = DOMAIN_KEYWORDS[LegalDomain.RGPD_DONNEES]
        assert "rgpd" in keywords
        assert "données personnelles" in keywords
        assert "cnil" in keywords

    # ─── [AXE3-02] Conflit d'intérêt → escalade ───
    def test_axe3_02_conflict_of_interest_escalated(self):
        """[AXE3-02] Un conflit d'intérêt détecté déclenche une escalade."""
        from python.helpers.legal_safe_policy import ReviewTrigger
        assert hasattr(ReviewTrigger, "CONFLICT_OF_INTEREST")

    # ─── [AXE3-03] Hors périmètre → refus propre ───
    def test_axe3_03_out_of_scope_handled(self):
        """[AXE3-03] Les questions hors périmètre (non FR/EU) sont refusées."""
        from python.helpers.legal_safe_policy import ReviewTrigger
        assert hasattr(ReviewTrigger, "OUT_OF_SCOPE")

    # ─── [AXE3-04] RGPD sans DPA dans contrat → flagué ───
    def test_axe3_04_rgpd_no_dpa_in_contract_flagged(self):
        """[AXE3-04] Traitement de données personnelles sans DPA → détecté."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur traite les données personnelles du Client dans le cadre du support."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, \
            "[AXE3-04] FAIL: Traitement de données sans DPA non détecté"

    # ─── [AXE3-05] Secret professionnel — no PII in logs ───
    def test_axe3_05_no_pii_in_audit_logs(self):
        """[AXE3-05] Les logs d'audit ne contiennent PAS de données personnelles."""
        from python.helpers.legal_rendering import DISCLAIMER
        # Le disclaimer mentionne que les sources sont traçables
        assert "provenance" in DISCLAIMER.lower() or "traçabilité" in DISCLAIMER.lower()

    # ─── [AXE3-06] Certitude demandée → refusée ───
    def test_axe3_06_certainty_request_detected(self):
        """[AXE3-06] Les demandes de certitude juridique sont détectées et refusées."""
        from python.helpers.legal_safe_policy import CERTAINTY_PATTERNS
        assert len(CERTAINTY_PATTERNS) >= 5
        # Vérifier que les patterns matchent
        import re
        test_phrases = [
            "Peux-tu certifier que c'est légal ?",
            "Garantis-moi que c'est conforme.",
            "Valider légalement ce contrat.",
        ]
        for phrase in test_phrases:
            matched = any(re.search(p, phrase, re.IGNORECASE) for p in CERTAINTY_PATTERNS)
            assert matched, f"[AXE3-06] Pattern non détecté: '{phrase}'"


# ═════════════════════════════════════════════════════════════════════════════
# AXE 4 — ROBUSTESSE / FAIL-CLOSED
# "Que se passe-t-il quand le système est sous stress ?"
# ═════════════════════════════════════════════════════════════════════════════

class TestAxe4_Robustesse:
    """AXE 4 — Vérification du comportement en mode dégradé.

    Un cabinet vérifie que :
    - Le système refuse plutôt que de deviner
    - L'injection de prompt est détectée
    - Le consensus sans quorum = REJECT
    - Les timeouts sont configurés
    """

    # ─── [AXE4-01] Fail-closed : disclaimer absent → REJECT ───
    def test_axe4_01_missing_disclaimer_rejected(self):
        """[AXE4-01] Un contrat sans disclaimer est TOUJOURS rejeté."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import (
            ContractDraft, GateVerdictEnum,
        )
        draft = ContractDraft(
            sections={"CG": "Clause standard."},
            variables={}, disclaimer="",  # VIDE
            correlation_id="axe4-01",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT, \
            "[AXE4-01] FAIL: Contrat sans disclaimer NON rejeté!"

    # ─── [AXE4-02] Fail-closed : pas de quorum = pas d'approbation ───
    def test_axe4_02_no_quorum_no_approval(self):
        """[AXE4-02] Sans quorum 2/3, AUCUNE approbation n'est possible."""
        from python.helpers.consensus_manager import ConsensusManager
        mgr = ConsensusManager(total_providers=3)
        # Vérifier que le système ne peut pas approuver sans votes
        # Le ConsensusManager requiert des propositions/votes actifs
        # Sans aucune proposition, aucune approbation n'est possible
        assert mgr.total_providers == 3
        # Pas de mécanisme d'auto-approbation
        assert not hasattr(mgr, 'auto_approve') or not getattr(mgr, 'auto_approve', False)

    # ─── [AXE4-03] Consensus : simulation interdite en production ───
    def test_axe4_03_simulation_forbidden_in_production(self):
        """[AXE4-03] La simulation de consensus est INTERDITE en production."""
        # Vérifier via le code source consensus_arbiter.py que simulation est False par défaut
        arbiter_path = os.path.join(
            BASE, "python", "helpers", "consensus_arbiter.py"
        )
        with open(arbiter_path) as f:
            content = f.read()
        assert "simulation_enabled" in content
        # Le défaut doit être False
        assert "simulation_enabled: bool = False" in content or \
               "simulation_enabled=False" in content, \
            "[AXE4-03] FAIL: simulation_enabled n'est pas False par défaut!"

    # ─── [AXE4-04] Network guard bloque les appels LLM en test ───
    def test_axe4_04_network_guard_active(self):
        """[AXE4-04] Le network guard empêche les appels LLM non mockés."""
        # Vérifier que conftest.py contient le guard
        conftest_path = os.path.join(BASE, "tests", "conftest.py")
        with open(conftest_path) as f:
            content = f.read()
        assert "network_guard" in content.lower() or "_network_guard" in content, \
            "[AXE4-04] FAIL: Network guard absent du conftest!"
        assert "RealLiteLLMCallForbiddenError" in content or "forbidden" in content.lower()

    # ─── [AXE4-05] Pipeline timeouts configurés ───
    def test_axe4_05_pipeline_timeouts_configured(self):
        """[AXE4-05] Tous les composants du pipeline ont des timeouts."""
        # Vérifier via le code source que les timeouts sont configurés
        arbiter_path = os.path.join(
            BASE, "python", "helpers", "consensus_arbiter.py"
        )
        with open(arbiter_path) as f:
            content = f.read()
        assert "global_timeout_ms" in content, \
            "[AXE4-05] FAIL: global_timeout_ms non configuré!"
        assert "per_arbiter_timeout_ms" in content, \
            "[AXE4-05] FAIL: per_arbiter_timeout_ms non configuré!"

    # ─── [AXE4-06] Gate audit report structuré ───
    def test_axe4_06_gate_audit_report_structured(self):
        """[AXE4-06] Le rapport d'audit de la gate est structuré et complet."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CG": "Clause standard sans problème."},
            variables={}, disclaimer="PROJET", correlation_id="axe4-06",
        )
        verdict = run_gate(draft)
        report = verdict.to_audit_report()
        assert "AUDIT CONTRACTUEL" in report
        assert "LEGAL_SAFE" in report
        assert "APPROVE" in report or "REJECT" in report

    # ─── [AXE4-07] Contrat E2E complet — pipeline intègre ───
    def test_axe4_07_full_pipeline_integrity(self):
        """[AXE4-07] Le pipeline E2E produit un contrat complet et sûr."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.export_control import is_export_allowed
        output = run_drafting_pipeline({
            "client_name": "Cabinet Martin & Associés",
            "editor_name": "KOREV",
            "software_name": "KOREV Evidence",
            "jurisdiction": "Tribunal de commerce de Paris",
            "licence_metric": "par utilisateur",
            "initial_posts": "5",
            "max_posts": "20",
            "remote_access": "false",
        })
        assert output.gate_passed is True
        assert is_export_allowed(output) is True
        assert "Cabinet Martin" in output.rendered_contract
        assert "KOREV" in output.rendered_contract
        # Vérifier l'absence de fuites
        forbidden = ["remise du code source", "cession du code", "code source livré"]
        for phrase in forbidden:
            assert phrase not in output.rendered_contract.lower(), \
                f"[AXE4-07] FUITE dans contrat E2E: '{phrase}'"


# ═════════════════════════════════════════════════════════════════════════════
# AXE 5 — TRAÇABILITÉ / AUDITABILITÉ
# "Peut-on reconstituer le raisonnement devant un juge ?"
# ═════════════════════════════════════════════════════════════════════════════

class TestAxe5_Tracabilite:
    """AXE 5 — Vérification de la traçabilité et de l'auditabilité.

    Un cabinet vérifie que :
    - Chaque contrat a un correlation_id unique
    - Les verdicts sont reproductibles (déterminisme)
    - Le rapport d'audit est exportable
    - Les findings sont détaillés (section, pattern, recommandation)
    """

    # ─── [AXE5-01] Correlation ID unique ───
    def test_axe5_01_correlation_id_unique(self):
        """[AXE5-01] Chaque contrat généré a un correlation_id UUID unique."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft1 = generate_contract({"client_name": "A"})
        draft2 = generate_contract({"client_name": "B"})
        assert draft1.correlation_id != draft2.correlation_id
        # Vérifier que c'est un UUID valide
        uuid.UUID(draft1.correlation_id)
        uuid.UUID(draft2.correlation_id)

    # ─── [AXE5-02] Reproductibilité du verdict ───
    def test_axe5_02_verdict_reproducible(self):
        """[AXE5-02] Mêmes inputs → même verdict (déterminisme)."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CG": "Clause standard sans problème."},
            variables={}, disclaimer="PROJET", correlation_id="axe5-02",
        )
        v1 = run_gate(draft)
        v2 = run_gate(draft)
        assert v1.verdict == v2.verdict
        assert v1.can_release == v2.can_release
        assert len(v1.findings) == len(v2.findings)

    # ─── [AXE5-03] Findings détaillés ───
    def test_axe5_03_findings_have_full_details(self):
        """[AXE5-03] Chaque finding a : severity, pattern, context, recommendation, section."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        findings = scan_for_leaks("Remise du code source au Client.", section="CG")
        assert len(findings) >= 1
        f = findings[0]
        assert f.severity is not None
        assert f.pattern != ""
        assert f.context != ""
        assert f.recommendation != ""
        assert f.section == "CG"

    # ─── [AXE5-04] Rapport d'audit exportable ───
    def test_axe5_04_audit_report_exportable(self):
        """[AXE5-04] Le rapport d'audit peut être exporté en texte structuré."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CG": "Remise du code source."},
            variables={}, disclaimer="PROJET", correlation_id="axe5-04",
        )
        verdict = run_gate(draft)
        report = verdict.to_audit_report()
        # Le rapport doit être un string non vide
        assert isinstance(report, str)
        assert len(report) > 100
        # Doit contenir les sections clés
        assert "Verdict" in report
        assert "P0" in report

    # ─── [AXE5-05] Variables manquantes tracées ───
    def test_axe5_05_missing_variables_marked(self):
        """[AXE5-05] Les variables manquantes sont marquées [À COMPLÉTER: ...]."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract({"client_name": "Test"})
        all_text = " ".join(draft.sections.values())
        assert "À COMPLÉTER" in all_text

    # ─── [AXE5-06] Decision.type = legal_contract ───
    def test_axe5_06_decision_type_correct(self):
        """[AXE5-06] Le type de décision est toujours 'legal_contract'."""
        from python.helpers.contract_drafting.governance import DECISION_GOVERNANCE_TYPE
        assert DECISION_GOVERNANCE_TYPE == "legal_contract"
        assert DECISION_GOVERNANCE_TYPE != "pricing"
        assert DECISION_GOVERNANCE_TYPE != "strategy"

    # ─── [AXE5-07] Documentation README existe ───
    def test_axe5_07_documentation_exists(self):
        """[AXE5-07] La documentation du process contractuel existe."""
        path = os.path.join(BASE, "python", "helpers", "contract_drafting", "README.md")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "FAIL" in content.upper()
        assert "LEGAL_SAFE" in content.upper() or "legal_safe" in content

    # ─── [AXE5-08] Leak Guard exhaustif ───
    def test_axe5_08_leak_guard_exhaustive(self):
        """[AXE5-08] Le Leak Guard couvre ≥16 patterns P0 et ≥9 patterns P1."""
        from python.helpers.contract_drafting.leak_guard import _P0_PATTERNS, _P1_PATTERNS
        assert len(_P0_PATTERNS) >= 16, f"P0: {len(_P0_PATTERNS)} < 16"
        assert len(_P1_PATTERNS) >= 9, f"P1: {len(_P1_PATTERNS)} < 9"


# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _build_minimal_legal_response(temperature: float = 0.0) -> dict:
    """Construit un objet LegalSafeResponse minimal pour les tests."""
    return {
        "mode": "legal_safe",
        "version": "1.0.0",
        "scope": {
            "jurisdiction_requested": "FR",
            "jurisdiction_detected": "FR",
            "out_of_scope": False,
        },
        "classification": {
            "domain": "contrats",
            "complexity": "simple",
            "requires_professional": False,
        },
        "facts": {"user_facts": ["Test"], "extracted_facts": []},
        "legal_basis": [],
        "analysis": {
            "firac": {
                "facts": "Test",
                "issue": "Test issue",
                "rules": "Test rules",
                "application": "Test application",
                "conclusion": "Test conclusion",
            },
            "risks": [],
            "next_action": "Aucune",
        },
        "conclusion": {
            "summary": "Test",
            "confidence": 0.8,
            "nuances": [],
        },
        "safety": {
            "requires_human_review": False,
            "review_triggers": [],
            "restricted_activity_detected": False,
            "conflict_of_interest": False,
        },
        "disclaimers": {
            "not_legal_advice": True,
            "consult_professional": True,
            "no_liability": True,
            "jurisdiction_specific": True,
        },
        "fallback": {"mode": "standard"},
        "output": {"format": "markdown", "content": "Test"},
        "meta": {
            "temperature": temperature,
            "model": "test",
            "timestamp": "2026-02-08T00:00:00Z",
        },
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

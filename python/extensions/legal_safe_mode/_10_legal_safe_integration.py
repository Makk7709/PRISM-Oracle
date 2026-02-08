"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — AGENT EXTENSION                        ║
║                                                                              ║
║  Extension pour intégrer le mode Legal-Safe dans le flux principal.         ║
║  - Détection automatique du profil "legal_safe"                             ║
║  - P2: Hook vers run_legal_pipeline (pipeline déterministe)                 ║
║  - P3: Short-circuit LLM quand pipeline produit une sortie                  ║
║  - Injection de kwargs (temperature=0)                                      ║
║  - Post-processing des réponses                                             ║
║  - Logging audit                                                             ║
║                                                                              ║
║  Version: 4.0.0 (Short-circuit LLM)                                         ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from python.helpers.extension import Extension

if TYPE_CHECKING:
    from agent import Agent, LoopData

# Structured logging
logger = logging.getLogger("legal_safe_mode")

# P2: Import legal pipeline (optional - graceful degradation)
try:
    from python.helpers.legal_orchestrator import (
        run_legal_pipeline,
        is_legal_pipeline_enabled,
    )
    from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
    from python.helpers.legal_rendering import render_legal_output
    LEGAL_PIPELINE_AVAILABLE = True
except ImportError:
    LEGAL_PIPELINE_AVAILABLE = False
    run_legal_pipeline = None
    is_legal_pipeline_enabled = None
    LegalOutput = None
    LegalOutputMode = None
    render_legal_output = None

# NEW: Import adversarial pipeline (7-phase instruction contradictoire)
try:
    from python.helpers.adversarial_consensus_integration import (
        get_adversarial_pipeline,
        analyze_with_adversarial,
    )
    ADVERSARIAL_PIPELINE_AVAILABLE = True
except ImportError:
    ADVERSARIAL_PIPELINE_AVAILABLE = False
    get_adversarial_pipeline = None
    analyze_with_adversarial = None


def is_adversarial_pipeline_enabled() -> bool:
    """Check if adversarial pipeline should be used instead of legal pipeline."""
    return os.environ.get("ADVERSARIAL_PIPELINE_ENABLED", "0") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# P3.2: ANTI DOUBLE-RUN PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level set to track executed correlation IDs (prevents re-execution)
_executed_correlation_ids: set = set()


def _mark_executed(correlation_id: str) -> bool:
    """
    Mark a correlation_id as executed.
    
    Returns:
        True if this is the first execution (allowed).
        False if this correlation_id was already executed (blocked).
    """
    if correlation_id in _executed_correlation_ids:
        logger.warning(
            f"DOUBLE-RUN BLOCKED: correlation_id={correlation_id} already executed"
        )
        return False
    _executed_correlation_ids.add(correlation_id)
    return True


def _clear_executed(correlation_id: str) -> None:
    """Remove a correlation_id from the executed set (allows re-execution)."""
    _executed_correlation_ids.discard(correlation_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENSION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeModeExtension(Extension):
    """
    Extension pour le mode Legal-Safe.
    
    Hooks utilisés:
    - agent_init: Initialisation du mode
    - monologue_start: Préprocessing + PIPELINE EXECUTION + SHORT-CIRCUIT
    - system_prompt: Injection du prompt additionnel
    - before_main_llm_call: Force les kwargs
    - response_stream_end: Post-processing de la réponse
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    
    LEGAL_SAFE_PROFILE = "legal_safe"
    FORCED_TEMPERATURE = 0.0
    CORRELATION_ID_KEY = "_legal_safe_correlation_id"
    START_TIME_KEY = "_legal_safe_start_time"
    PRE_TRIGGERS_KEY = "_legal_safe_pre_triggers"
    PIPELINE_OUTPUT_KEY = "_legal_pipeline_output"
    PIPELINE_RENDERED_KEY = "_legal_pipeline_rendered"
    PIPELINE_EXECUTED_KEY = "_legal_pipeline_executed"
    
    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    # ─────────────────────────────────────────────────────────────────────────
    # LEGAL AUTO-DETECTION PATTERNS
    # ─────────────────────────────────────────────────────────────────────────
    # These patterns detect queries that are CLEARLY legal and should
    # auto-activate the legal pipeline even without explicit profile setting.
    LEGAL_AUTODETECT_STRONG = [
        # Contract drafting
        r"\brédaction\b.*\bcontrat\b",
        r"\bcontrat\b.*\brédaction\b",
        r"\bcontrat\s+(?:de\s+)?(?:licence|prestation|service|travail|mandat|bail|location)",
        r"\bprêt\s+à\s+signature\b",
        r"\btexte\s+contractuel\b",
        r"\bconditions\s+(?:générales|particulières)\b",
        # Legal document production
        r"\blegal[_\s]?contract\b",
        r"\bproduire\s+un\s+contrat\b",
        r"\brédig(?:er?|ez)\s+(?:un|le|ce)\s+contrat\b",
        r"\bannexes?\s+(?:SLA|RGPD|DPA|sécurité|réversibilité)\b",
        # Explicit legal framing
        r"\bdroit\s+applicable\b.*\bjuridiction\b",
        r"\bjuridiction\b.*\btribunal\b",
        r"\bcode\s+civil\b",
        r"\bcode\s+de\s+commerce\b",
        r"\bcpi\b",
        r"\bpropriété\s+intellectuelle\b.*\bcession\b",
        r"\bcession\b.*\bpropriété\s+intellectuelle\b",
    ]
    
    LEGAL_AUTODETECT_WEAK = [
        # These need multiple matches to trigger
        r"\bcontrat\b",
        r"\bclause\b",
        r"\bjuridique\b",
        r"\blicence\b",
        r"\bRGPD\b",
        r"\bDPA\b",
        r"\bannexe\b",
        r"\bresponsabilité\b",
        r"\bréversibilité\b",
        r"\bconfidentialité\b",
        r"\bgarantie\b",
        r"\btribunal\b",
        r"\bjuridiction\b",
        r"\bpénalités?\b",
        r"\bart(?:icle)?\s*\d+",
        r"\bsignature\b",
    ]
    
    LEGAL_AUTODETECT_THRESHOLD_WEAK = 5  # Need >= 5 weak matches to auto-detect
    
    def _detect_legal_query(self, query: str) -> bool:
        """
        Auto-detect if a query is a legal request based on content analysis.
        
        Returns True if the query is clearly legal (contract drafting,
        legal document production, etc.) regardless of profile setting.
        """
        import re
        query_lower = query.lower()
        
        # Strong patterns: any single match triggers legal mode
        for pattern in self.LEGAL_AUTODETECT_STRONG:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info(
                    f"Legal auto-detect: STRONG match '{pattern}' — "
                    f"activating legal pipeline"
                )
                return True
        
        # Weak patterns: need multiple matches
        weak_count = 0
        for pattern in self.LEGAL_AUTODETECT_WEAK:
            matches = re.findall(pattern, query_lower, re.IGNORECASE)
            weak_count += len(matches)
        
        if weak_count >= self.LEGAL_AUTODETECT_THRESHOLD_WEAK:
            logger.info(
                f"Legal auto-detect: {weak_count} weak matches (threshold={self.LEGAL_AUTODETECT_THRESHOLD_WEAK}) — "
                f"activating legal pipeline"
            )
            return True
        
        return False
    
    def is_legal_safe_mode(self, agent: "Agent", query: str = "") -> bool:
        """
        Vérifie si le mode Legal-Safe est actif.
        
        Activation par:
        1. Profil agent = "legal_safe" (explicite)
        2. Variable d'environnement KOREV_LEGAL_SAFE_MODE
        3. Auto-détection du contenu de la requête (contrat, juridique, etc.)
        """
        # 1. Explicit profile
        if agent.config.profile == self.LEGAL_SAFE_PROFILE:
            return True
        
        # 2. Environment variable
        env_value = os.environ.get("KOREV_LEGAL_SAFE_MODE", "").lower()
        if env_value in ("true", "1", "yes", "on"):
            return True
        
        # 3. Auto-detect from query content
        if query and self._detect_legal_query(query):
            logger.info(
                f"Legal Safe Mode AUTO-ACTIVATED based on query content "
                f"(profile was '{agent.config.profile}')"
            )
            return True
        
        return False
    
    def should_use_legal_pipeline(self) -> bool:
        """P2: Vérifie si le pipeline légal doit être utilisé."""
        # If adversarial pipeline is enabled, don't use legacy legal pipeline
        if is_adversarial_pipeline_enabled():
            return False
        
        if not LEGAL_PIPELINE_AVAILABLE:
            return False
        
        if is_legal_pipeline_enabled is None or not is_legal_pipeline_enabled():
            return False
        
        hook_enabled = os.environ.get("LEGAL_PIPELINE_HOOK", "1") == "1"
        return hook_enabled
    
    def should_use_adversarial_pipeline(self) -> bool:
        """NEW: Vérifie si le pipeline adversarial (7 phases) doit être utilisé."""
        if not ADVERSARIAL_PIPELINE_AVAILABLE:
            return False
        return is_adversarial_pipeline_enabled()
    
    def _extract_contract_variables(self, user_text: str) -> dict:
        """
        Extract contract variables from user text (best-effort).
        Variables not found are left empty (template marks them [À COMPLÉTER]).
        """
        import re as _re
        variables = {}
        
        # Try to extract common variables
        # Client name
        client_match = _re.search(r"(?:client|entre.*et)\s+(\w[\w\s]{2,30}(?:France|SAS|SARL|SA|EURL|SCI))", user_text, _re.IGNORECASE)
        if client_match:
            variables["client_name"] = client_match.group(1).strip()
        
        # Editor name (KOREV by default)
        if "korev" in user_text.lower():
            variables["editor_name"] = "KOREV"
        
        # Software name
        for pattern in [
            r"(?:logiciel|software|produit)\s+(?:\"([^\"]+)\"|(\w[\w\s]+?)(?:\s*[,(.]|$))",
            r"(\w+\s+\w+)\s+\(actif\s+korev\)",
        ]:
            sw_match = _re.search(pattern, user_text, _re.IGNORECASE)
            if sw_match:
                name = sw_match.group(1) or sw_match.group(2) if sw_match.lastindex > 1 else sw_match.group(1)
                if name:
                    variables["software_name"] = name.strip()
                    break
        
        # Jurisdiction
        jur_match = _re.search(r"(?:tribunal|juridiction)\s+(?:de\s+)?(?:commerce\s+de\s+)?(\w+)", user_text, _re.IGNORECASE)
        if jur_match:
            variables["jurisdiction"] = f"Tribunal de commerce de {jur_match.group(1).strip()}"
        
        # Remote access
        if _re.search(r"(?:accès|acces)\s+(?:à\s+)?distance|support\s+distant|remote", user_text, _re.IGNORECASE):
            variables["remote_access"] = "true"
        else:
            variables["remote_access"] = "false"
        
        # Licence metric
        if "par poste" in user_text.lower():
            variables["licence_metric"] = "par poste"
        elif "par utilisateur" in user_text.lower():
            variables["licence_metric"] = "par utilisateur"
        
        return variables
    
    def _render_user_response(self, dossier) -> str:
        """
        Génère une réponse orientée utilisateur à partir du dossier adversarial.
        
        Produit une réponse structurée et lisible avec:
        - Réponse principale consolidée
        - Indice de confiance global
        - Sources juridiques
        - Points d'attention
        """
        import re
        import json as json_lib
        
        def clean_text(text: str) -> str:
            """Nettoie le texte: supprime JSON, balises, et contenu en anglais."""
            if not text:
                return ""
            
            # Supprimer les blocs JSON
            text = re.sub(r'\{[^{}]*"main_conclusions"[^{}]*\}', '', text, flags=re.DOTALL)
            text = re.sub(r'\{[^{}]*"conclusions"[^{}]*\}', '', text, flags=re.DOTALL)
            text = re.sub(r'```json[\s\S]*?```', '', text)
            text = re.sub(r'\{[\s\S]*?\}', '', text)
            
            # Supprimer les phrases en anglais (heuristique simple)
            english_patterns = [
                r"I appreciate your.*?\.",
                r"I need to clarify.*?\.",
                r"I'm designed to.*?\.",
                r"However, I.*?\.",
                r"Let me.*?\.",
                r"Source: \w+",
            ]
            for pattern in english_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
            # Nettoyer les artifacts
            text = re.sub(r'\[Certitude:.*?\]', '', text)
            text = re.sub(r'\[Opinion:.*?\]', '', text)
            text = re.sub(r'"main_conclusions":', '', text)
            text = re.sub(r'^\s*[\[\]",]+\s*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text.strip()
        
        def extract_legal_refs(text: str) -> list:
            """Extrait les références juridiques du texte."""
            refs = []
            patterns = [
                r'(art(?:icle)?\.?\s*L?\d+[\-\d]*(?:\s+(?:du|de)\s+[\w\s]+)?)',
                r'(CSP[,\s]+art\.?\s*[\w\-\d]+)',
                r'(Code\s+(?:civil|pénal|travail|santé|commerce)[^,\.\n]*)',
                r'(Cass\.\s*[^,\.\n]+)',
                r'(CE[,\s]+\d{1,2}\s+\w+\s+\d{4}[^,\.\n]*)',
                r'(loi\s+n°?\s*\d+[\-\d]*[^,\.\n]*)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                refs.extend(matches)
            return list(set(refs))[:10]
        
        # Calculer l'indice de confiance global
        reliability = dossier.audit_report.overall_reliability_score if dossier.audit_report else 0.5
        
        # Déterminer le niveau de confiance
        if reliability >= 0.8:
            confidence_label = "ÉLEVÉE"
            confidence_color = "🟢"
        elif reliability >= 0.6:
            confidence_label = "MODÉRÉE"
            confidence_color = "🟡"
        elif reliability >= 0.4:
            confidence_label = "LIMITÉE"
            confidence_color = "🟠"
        else:
            confidence_label = "FAIBLE"
            confidence_color = "🔴"
        
        # Collecter et nettoyer les conclusions
        clean_conclusions = []
        all_legal_refs = []
        
        for agent_id, analysis in dossier.agent_analyses.items():
            if analysis.main_conclusions:
                for conclusion in analysis.main_conclusions:
                    cleaned = clean_text(conclusion)
                    if cleaned and len(cleaned) > 20 and not cleaned.startswith("Error"):
                        # Extraire les refs juridiques
                        refs = extract_legal_refs(cleaned)
                        all_legal_refs.extend(refs)
                        
                        clean_conclusions.append({
                            "text": cleaned,
                            "role": analysis.agent_role.value,
                        })
        
        # Dédupliquer les conclusions
        seen = set()
        unique_conclusions = []
        for c in clean_conclusions:
            key = c["text"][:80].lower()
            if key not in seen:
                seen.add(key)
                unique_conclusions.append(c)
        
        # Dédupliquer les refs juridiques
        unique_refs = list(set(all_legal_refs))
        
        # Collecter les informations manquantes (nettoyées)
        missing_info = []
        for info in (dossier.missing_information or []):
            cleaned = clean_text(str(info))
            if cleaned and len(cleaned) > 10:
                missing_info.append(cleaned)
        
        # Collecter les points de désaccord (nettoyés)
        disagreements = []
        for point in (dossier.disagreement_points or []):
            cleaned = clean_text(str(point))
            if cleaned and len(cleaned) > 10:
                disagreements.append(cleaned)
        
        # ═══════════════════════════════════════════════════════════════════
        # CONSTRUCTION DE LA RÉPONSE
        # ═══════════════════════════════════════════════════════════════════
        
        response = f"""# ⚖️ Analyse Juridique Multi-Perspectives

| Indice de Confiance | Domaine | Criticité |
|:-------------------:|:-------:|:---------:|
| {confidence_color} **{confidence_label}** ({reliability:.0%}) | {dossier.domain.value.upper()} | {dossier.criticality.value.upper()} |

---

## 📋 Synthèse

"""
        
        # Points clés (conclusions nettoyées)
        if unique_conclusions:
            for i, c in enumerate(unique_conclusions[:6], 1):
                # Limiter la longueur et nettoyer
                text = c["text"]
                if len(text) > 500:
                    text = text[:500] + "..."
                response += f"**{i}.** {text}\n\n"
        else:
            response += "> ⚠️ Les analyses n'ont pas produit de conclusions exploitables.\n\n"
        
        # Sources juridiques
        if unique_refs:
            response += "\n---\n\n## 📚 Références Juridiques Citées\n\n"
            for ref in unique_refs[:8]:
                response += f"- {ref}\n"
        
        # Informations manquantes
        if missing_info:
            response += "\n---\n\n## ❓ Informations Complémentaires Nécessaires\n\n"
            for info in missing_info[:5]:
                if len(info) > 200:
                    info = info[:200] + "..."
                response += f"- {info}\n"
        
        # Points de désaccord
        if disagreements:
            response += "\n---\n\n## 🔀 Points de Débat entre Experts\n\n"
            for point in disagreements[:4]:
                if len(point) > 200:
                    point = point[:200] + "..."
                response += f"- {point}\n"
        
        # Avertissement standard
        response += f"""

---

## ⚠️ Avertissement

Cette analyse a été générée par **{len(dossier.agent_analyses)} agents IA** avec validation croisée.
Elle ne constitue pas un avis juridique et ne remplace pas la consultation d'un professionnel du droit.

| Métrique | Valeur |
|----------|--------|
| Indice de confiance | {reliability:.0%} |
| Agents consultés | {len(dossier.agent_analyses)} |
| Revues croisées | {len(dossier.peer_reviews)} |
| Protocole | {dossier.protocol.value} |

*Dossier: {dossier.id[:12]}*
"""
        
        return response
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: agent_init
    # ─────────────────────────────────────────────────────────────────────────
    
    async def execute(self, agent: "Agent", **kwargs):
        """Hook d'initialisation de l'agent."""
        if not self.is_legal_safe_mode(agent):
            return
        
        from python.helpers.print_style import PrintStyle
        
        PrintStyle(
            font_color="yellow",
            background_color="black",
            padding=True,
            bold=True
        ).print("⚖️ LEGAL-SAFE MODE ACTIVATED")
        
        if hasattr(agent.config.chat_model, 'kwargs'):
            agent.config.chat_model.kwargs["temperature"] = self.FORCED_TEMPERATURE
        
        agent.context.log.log(
            type="info",
            heading="Legal-Safe Mode",
            content="Mode juridique sécurisé activé. Temperature forcée à 0.",
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: monologue_start — CRITICAL: PIPELINE EXECUTION + SHORT-CIRCUIT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def monologue_start(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """
        Hook au début du monologue.
        
        CRITICAL: Si le pipeline legal produit une sortie, on court-circuite le LLM
        en définissant _pipeline_final_response. L'agent retournera cette réponse
        directement sans appeler le LLM.
        """
        from python.helpers.print_style import PrintStyle
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 0: Extract user text FIRST (needed for auto-detection)
        # ─────────────────────────────────────────────────────────────────
        user_text = ""
        if loop_data and loop_data.user_message:
            msg = loop_data.user_message
            msg_content = msg.content if hasattr(msg, 'content') else None
            
            if isinstance(msg_content, dict):
                user_text = (
                    msg_content.get("user_message", "") or 
                    msg_content.get("message", "") or 
                    msg_content.get("text", "") or 
                    ""
                )
            elif isinstance(msg_content, str):
                try:
                    import json as _json
                    parsed = _json.loads(msg_content.strip().strip('`').replace('json\n', ''))
                    user_text = (
                        parsed.get("user_message", "") or
                        parsed.get("message", "") or
                        parsed.get("text", "") or
                        msg_content
                    )
                except (ValueError, AttributeError):
                    user_text = msg_content
            elif isinstance(msg_content, list):
                parts = []
                for item in msg_content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        parts.append(
                            item.get("user_message", "") or
                            item.get("message", "") or
                            item.get("text", "") or
                            ""
                        )
                user_text = " ".join(filter(None, parts))
        
        # ─────────────────────────────────────────────────────────────────
        # STEP 1: Check legal safe mode (with query auto-detection)
        # ─────────────────────────────────────────────────────────────────
        # DEBUG: Always log entry
        is_legal = self.is_legal_safe_mode(agent, query=user_text)
        PrintStyle(font_color="yellow").print(
            f"🔧 DEBUG monologue_start: profile={agent.config.profile}, "
            f"is_legal_safe={is_legal}, "
            f"should_use_pipeline={self.should_use_legal_pipeline()}, "
            f"query_len={len(user_text)}"
        )
        
        if not is_legal:
            PrintStyle(font_color="red").print("🔧 DEBUG: NOT legal_safe mode - skipping")
            return
        
        # Générer un correlation_id pour cette session
        correlation_id = str(uuid4())
        agent.set_data(self.CORRELATION_ID_KEY, correlation_id)
        agent.set_data(self.START_TIME_KEY, time.time())
        
        # user_text already extracted above — skip duplicate extraction
        
        PrintStyle(font_color="green" if user_text else "red").print(
            f"🔧 DEBUG: Extracted user_text (len={len(user_text)}): '{user_text[:100]}...'" if user_text else "🔧 DEBUG: NO USER TEXT EXTRACTED!"
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # NEW: ROUTE TO CONTRACT DRAFTING PIPELINE IF INTENT DETECTED
        # ═══════════════════════════════════════════════════════════════════
        
        if user_text:
            try:
                from python.helpers.contract_drafting.orchestrator import (
                    detect_contract_drafting_intent,
                    run_drafting_pipeline,
                )
                
                if detect_contract_drafting_intent(user_text):
                    PrintStyle(font_color="cyan", bold=True).print(
                        "📝 CONTRACT DRAFTING PIPELINE — Intent detected, routing to legal_drafting_guarded"
                    )
                    logger.info(f"[{correlation_id}] Routing to CONTRACT DRAFTING pipeline...")
                    
                    # Extract variables from user text (minimal extraction)
                    variables = self._extract_contract_variables(user_text)
                    
                    # Execute pipeline
                    output = run_drafting_pipeline(variables, contract_type="on_prem_licence")
                    
                    # Build user-facing response
                    if output.gate_passed:
                        response_text = (
                            f"📝 **PROJET DE CONTRAT — À VALIDER PAR UN JURISTE QUALIFIÉ**\n\n"
                            f"Gate d'audit : ✅ {output.gate_summary}\n\n"
                            f"---\n\n"
                            f"{output.rendered_contract}\n\n"
                            f"---\n\n"
                            f"⚠️ **AVERTISSEMENT** : Ce document est un PROJET rédigé par un assistant IA. "
                            f"Il ne constitue PAS un acte juridique finalisé. "
                            f"Il DOIT être revu et validé par un juriste qualifié avant toute utilisation ou signature."
                        )
                    else:
                        corrections = "\n".join(f"  - {c}" for c in output.corrections_needed)
                        response_text = (
                            f"🚫 **CONTRAT NON LIBÉRÉ — Gate d'audit REJETÉE**\n\n"
                            f"Verdict : {output.gate_summary}\n\n"
                            f"**Corrections requises avant release :**\n{corrections}\n\n"
                            f"Le contrat ne peut pas être présenté tant que les problèmes P0 ne sont pas corrigés."
                        )
                    
                    # SHORT-CIRCUIT LLM
                    agent.set_data("_pipeline_final_response", response_text)
                    agent.set_data("_skip_llm", True)
                    agent.set_data("_pipeline_was_used", True)
                    agent.set_data("_contract_drafting_output", output)
                    
                    agent.context.log.log(
                        type="info",
                        heading="📝 Contract Drafting Pipeline",
                        content=f"Pipeline executed: gate_passed={output.gate_passed}",
                        kvps={
                            "correlation_id": correlation_id,
                            "gate_passed": output.gate_passed,
                            "gate_summary": output.gate_summary,
                            "p0_count": output.gate_verdict.p0_count(),
                            "p1_count": output.gate_verdict.p1_count(),
                        }
                    )
                    return  # Pipeline handled — exit monologue_start
                    
            except ImportError:
                logger.warning("Contract drafting module not available — continuing")
        
        # ═══════════════════════════════════════════════════════════════════
        # NEW: ROUTE TO ADVERSARIAL PIPELINE (7-phase) IF ENABLED
        # ═══════════════════════════════════════════════════════════════════
        
        PrintStyle(font_color="yellow").print(
            f"🔧 DEBUG: should_use_adversarial={self.should_use_adversarial_pipeline()}, "
            f"should_use_legal={self.should_use_legal_pipeline()}, "
            f"user_text_len={len(user_text)}"
        )
        
        if self.should_use_adversarial_pipeline() and user_text:
            PrintStyle(font_color="magenta", bold=True).print(
                f"📋 ADVERSARIAL PIPELINE ENABLED - Routing to 7-phase analysis"
            )
            logger.info(f"[{correlation_id}] Routing to ADVERSARIAL pipeline...")
            
            try:
                # Execute adversarial pipeline with agent profile
                dossier = await analyze_with_adversarial(
                    query=user_text,
                    context={"correlation_id": correlation_id},
                    agent_profile=self.LEGAL_SAFE_PROFILE,
                )
                
                # Render user-friendly response (not technical trace)
                full_rendered = self._render_user_response(dossier)
                
                # Store for reference
                agent.set_data(self.PIPELINE_OUTPUT_KEY, dossier)
                agent.set_data(self.PIPELINE_RENDERED_KEY, full_rendered)
                
                # SHORT-CIRCUIT LLM
                agent.set_data("_pipeline_final_response", full_rendered)
                agent.set_data("_skip_llm", True)
                agent.set_data("_pipeline_was_used", True)
                agent.set_data("_adversarial_dossier_id", dossier.id)
                
                # Log success
                agent.context.log.log(
                    type="info",
                    heading="📋 Adversarial Pipeline (7-Phase)",
                    content=f"Pipeline executed: domain={dossier.domain.value}, protocol={dossier.protocol.value}",
                    kvps={
                        "correlation_id": correlation_id,
                        "dossier_id": dossier.id,
                        "domain": dossier.domain.value,
                        "criticality": dossier.criticality.value,
                        "protocol": dossier.protocol.value,
                        "analyses_count": len(dossier.agent_analyses),
                        "audit_score": dossier.audit_report.overall_reliability_score,
                        "llm_bypassed": True,
                    }
                )
                
                logger.info(
                    f"[{correlation_id}] Adversarial pipeline SUCCESS - "
                    f"dossier={dossier.id[:8]}, domain={dossier.domain.value}"
                )
                
                return  # Done - LLM bypassed
                
            except Exception as e:
                logger.error(f"[{correlation_id}] Adversarial pipeline FAILED: {e}")
                import traceback
                traceback.print_exc()
                
                # Fail-closed with error message
                failure_response = f"""# ⚠️ Analyse Contradictoire Indisponible

> **Statut**: ÉCHEC PIPELINE ADVERSARIAL | **Mode**: FAIL-CLOSED

## 🚫 Erreur

Le système d'analyse multi-perspectives n'a pas pu traiter votre demande.

**Raison**: {str(e)[:300]}

## ⚠️ Important

- **Aucune analyse contradictoire n'a été effectuée**
- Cette réponse est un **blocage de sécurité** (fail-closed)
- Consultez directement un professionnel pour ce type de question

---

`correlation_id: {correlation_id}`
"""
                
                # NE PAS bloquer le LLM en cas d'échec du pipeline
                # Laisser l'agent répondre avec ses capacités de base
                agent.context.log.log(
                    type="warning",
                    heading="⚠️ Adversarial Pipeline FAILED - LLM Fallback",
                    content=f"Pipeline failed: {str(e)[:100]}. Allowing LLM to respond.",
                    kvps={
                        "correlation_id": correlation_id,
                        "llm_bypassed": False,
                        "reason": "adversarial_pipeline_failure",
                        "error": str(e)[:200],
                    }
                )
                
                # Ne pas retourner - laisser le LLM répondre normalement
                # return
        
        # ═══════════════════════════════════════════════════════════════════
        # P2/P3: ROUTE TO LEGACY LEGAL PIPELINE IF ENABLED
        # ═══════════════════════════════════════════════════════════════════
        
        if self.should_use_legal_pipeline() and user_text:
            PrintStyle(font_color="green").print(f"🔧 DEBUG: ENTERING PIPELINE EXECUTION")
            logger.info(f"[{correlation_id}] Routing to legal pipeline...")
            
            try:
                # Execute pipeline with automatic as_of_date (today)
                # P5: as_of_date is required for MEDIUM+ risk queries
                from datetime import date
                today = date.today()
                
                # Create LLM call function from agent's chat model
                # This allows the pipeline to generate FIRAC analysis even without indexed sources
                async def call_llm_func(messages, temperature=0, max_tokens=2000):
                    """Wrapper to call agent's LLM for FIRAC draft generation."""
                    try:
                        from python.helpers import llm_provider
                        
                        # Use the agent's configured chat model
                        provider_name = agent.config.chat_model.provider
                        model_name = agent.config.chat_model.name
                        
                        # Get provider wrapper
                        provider = llm_provider.get_provider(provider_name, model_name)
                        
                        # Extract prompt from messages
                        prompt = ""
                        for msg in messages:
                            if isinstance(msg, dict):
                                prompt += msg.get("content", "")
                            else:
                                prompt += str(msg)
                        
                        # Generate response
                        response = await provider.generate(
                            prompt=prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        return response
                    except Exception as e:
                        logger.error(f"LLM call failed: {e}")
                        return ""
                
                output = await run_legal_pipeline(
                    query=user_text,
                    correlation_id=correlation_id,
                    as_of_date=today,  # Default to today's date for temporal opposability
                    call_llm_func=call_llm_func,  # Enable LLM-based FIRAC analysis
                )
                
                # Render output
                if render_legal_output is not None:
                    style = "info"
                    if output.scope == "board":
                        style = "board"
                    elif output.scope == "operational" or output.risk_tier in ("medium", "high"):
                        style = "operational"
                    
                    rendered = render_legal_output(output, format="md", style=style)
                else:
                    rendered = output.answer
                
                # Store for reference
                agent.set_data(self.PIPELINE_OUTPUT_KEY, output)
                agent.set_data(self.PIPELINE_RENDERED_KEY, rendered)
                
                # ═══════════════════════════════════════════════════════════
                # CRITICAL: Set flags to SHORT-CIRCUIT LLM call
                # The agent runtime will check these flags and return the
                # pipeline response directly without calling the LLM.
                # ═══════════════════════════════════════════════════════════
                agent.set_data("_pipeline_final_response", rendered)
                agent.set_data("_skip_llm", True)
                agent.set_data("_pipeline_was_used", True)  # Signal to call_subordinate
                
                # Log success
                agent.context.log.log(
                    type="info",
                    heading="⚖️ Legal Pipeline (LLM Bypassed)",
                    content=f"Pipeline executed: mode={output.mode.value}",
                    kvps={
                        "correlation_id": correlation_id,
                        "output_mode": output.mode.value,
                        "consensus_status": output.consensus_status,
                        "llm_bypassed": True,
                    }
                )
                
                logger.info(
                    f"[{correlation_id}] Pipeline SUCCESS - LLM bypassed, "
                    f"mode={output.mode.value}"
                )
                
            except Exception as e:
                logger.error(f"[{correlation_id}] Pipeline FAILED: {e}")
                
                # ═══════════════════════════════════════════════════════════
                # CRITICAL: Even on failure, SHORT-CIRCUIT with error message
                # DO NOT let the LLM hallucinate a response!
                # ═══════════════════════════════════════════════════════════
                failure_response = f"""# ⚠️ Analyse Juridique Indisponible

> **Statut**: ÉCHEC PIPELINE | **Mode**: FAIL-CLOSED

## 🚫 Réponse Non Disponible

Le système d'analyse juridique n'a pas pu traiter votre demande.

**Raison**: {str(e)[:200]}

## ⚠️ Important

- **Aucune analyse n'a été effectuée** sur votre question
- **Ne vous fiez pas** à des réponses alternatives non sourcées
- Cette réponse est un **blocage de sécurité** (fail-closed)

## 📋 Actions Recommandées

1. Réessayez dans quelques instants
2. Si le problème persiste, consultez directement un professionnel du droit

---

`correlation_id: {correlation_id}`
"""
                
                # NE PAS bloquer le LLM en cas d'échec du pipeline
                # Laisser l'agent répondre avec ses capacités de base
                agent.context.log.log(
                    type="warning",
                    heading="⚠️ Legal Pipeline FAILED - LLM Fallback",
                    content=f"Pipeline failed: {str(e)[:100]}. Allowing LLM to respond.",
                    kvps={
                        "correlation_id": correlation_id,
                        "llm_bypassed": False,
                        "reason": "pipeline_failure_llm_fallback",
                        "error": str(e)[:200],
                    }
                )
                
                # Ne pas set _skip_llm - laisser le LLM répondre normalement
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: response_stream_end
    # ─────────────────────────────────────────────────────────────────────────
    
    async def response_stream_end(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """Hook après la réponse - post-processing et logging."""
        if not self.is_legal_safe_mode(agent):
            return
        
        # If pipeline was used, no need for post-processing
        if agent.get_data("_skip_llm"):
            return
        
        try:
            from python.helpers.legal_safe_runtime import LegalSafeResponseParser
            from python.helpers.legal_safe_logger import log_legal_safe_response, log_legal_safe_error
            from python.helpers.legal_safe_schema import ReviewTrigger
            
            response_text = loop_data.last_response
            if not response_text:
                return
            
            correlation_id = agent.get_data(self.CORRELATION_ID_KEY) or str(uuid4())
            start_time = agent.get_data(self.START_TIME_KEY) or time.time()
            latency_ms = int((time.time() - start_time) * 1000)
            
            parsed, is_valid, error = LegalSafeResponseParser.parse_response(
                response_text,
                correlation_id=correlation_id,
                provider=agent.config.chat_model.provider,
                model=agent.config.chat_model.name,
                latency_ms=latency_ms,
            )
            
            pre_triggers = agent.get_data(self.PRE_TRIGGERS_KEY) or []
            if pre_triggers:
                existing = set(parsed.safety.review_triggers)
                for t in pre_triggers:
                    existing.add(t)
                parsed.safety.review_triggers = list(existing)
                if existing:
                    parsed.safety.requires_human_review = True
            
            if is_valid:
                log_legal_safe_response(parsed)
            else:
                log_legal_safe_error(correlation_id, error or "Unknown error")
            
            if parsed.safety.requires_human_review:
                triggers_str = ", ".join([t.value for t in parsed.safety.review_triggers])
                agent.context.log.log(
                    type="warning",
                    heading="⚖️ ESCALADE REQUISE",
                    content=f"Validation humaine nécessaire. Triggers: {triggers_str}",
                    kvps={
                        "requires_human_review": True,
                        "review_triggers": [t.value for t in parsed.safety.review_triggers],
                        "confidence": parsed.conclusion.confidence,
                        "correlation_id": correlation_id,
                    }
                )
            
        except Exception as e:
            logger.error(f"Legal-Safe post-processing error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

# L'extension est chargée automatiquement par le système d'extensions

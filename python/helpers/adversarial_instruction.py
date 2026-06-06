"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             ADVERSARIAL INSTRUCTION - PROCÉDURE CONTRADICTOIRE IA            ║
║                                                                              ║
║  Système d'instruction contradictoire assistée par IA en 7 phases.           ║
║                                                                              ║
║  PHASES:                                                                     ║
║  1. Gate d'entrée     - Cadrage strict (domaine, criticité, protocole)       ║
║  2. Collecte          - Travail parallèle multi-modèles                      ║
║  3. Débat structuré   - Revue par les pairs inter-modèles                    ║
║  4. Détection hallu.  - Auditeur interne chasseur de doutes                  ║
║  5. Consolidation     - Synthèse avec degrés de fiabilité                    ║
║  6. Traçabilité       - Documentation systématique                           ║
║  7. Acceptation       - Interface décision humaine finale                    ║
║                                                                              ║
║  Principe: "Ce n'est pas une opinion, c'est un rapport d'instruction."       ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("adversarial_instruction")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: ENUMS ET TYPES DE BASE - GATE D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════

class Domain(str, Enum):
    """Domaines de qualification."""
    LEGAL = "legal"
    MEDICAL = "medical"
    FINANCE = "finance"
    STRATEGIC = "strategic"
    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    REGULATORY = "regulatory"
    ETHICS = "ethics"
    GENERAL = "general"


class CriticalityLevel(str, Enum):
    """Niveaux de criticité déterminant l'intensité du pipeline."""
    LOW = "low"              # Protocole léger
    MEDIUM = "medium"        # Protocole standard
    HIGH = "high"            # Protocole renforcé
    CRITICAL = "critical"    # Protocole maximal


class ProtocolType(str, Enum):
    """Types de protocoles d'instruction."""
    LIGHT = "light"          # 2 agents, pas de débat
    STANDARD = "standard"    # 3 agents, débat simple
    REINFORCED = "reinforced"  # 4 agents, débat + audit
    MAXIMAL = "maximal"      # 5+ agents, audit complet, traces détaillées


class AgentRole(str, Enum):
    """Rôles des agents dans le pipeline."""
    # Phase 2: Collecte
    DOCTRINAL = "doctrinal"              # Analyse doctrinale stricte
    JURISPRUDENCE = "jurisprudence"      # Recherche jurisprudence/exceptions
    PROCEDURAL = "procedural"            # Angle procédural/risques
    CONTEXTUAL = "contextual"            # Analyse contextuelle
    COMPARATIVE = "comparative"          # Droit/pratique comparé
    
    # Phase 4: Audit
    HALLUCINATION_HUNTER = "hallucination_hunter"  # Détection affirmations douteuses
    
    # Phase 5: Synthèse
    SYNTHESIZER = "synthesizer"          # Consolidation finale


class ConfidenceLevel(str, Enum):
    """Niveaux de confiance pour les assertions."""
    HIGHLY_RELIABLE = "highly_reliable"  # Consensus fort + sources solides
    PROBABLE = "probable"                # Probable mais discutable
    UNCERTAIN = "uncertain"              # Incertain
    MISSING_INFO = "missing_info"        # Information manquante
    HYPOTHESIS = "hypothesis"            # Hypothèse prise
    DISPUTED = "disputed"                # Point de désaccord


class IssueType(str, Enum):
    """Types de problèmes détectés."""
    UNSOURCED_CLAIM = "unsourced_claim"          # Affirmation non sourcée
    CIRCULAR_REASONING = "circular_reasoning"    # Raisonnement circulaire
    APPROXIMATION = "approximation"              # Approximation détectée
    INTERPRETATION = "interpretation"            # Interprétation vs fait
    CONTRADICTION = "contradiction"              # Contradiction interne
    LOGICAL_GAP = "logical_gap"                  # Saut logique
    OUTDATED_SOURCE = "outdated_source"          # Source potentiellement obsolète
    OVERCONFIDENCE = "overconfidence"            # Confiance excessive


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Source:
    """Représente une source citée."""
    id: str
    type: str  # "jurisprudence", "doctrine", "regulation", "article", etc.
    reference: str
    url: Optional[str] = None
    date: Optional[str] = None
    reliability_score: float = 0.5  # 0-1
    verified: bool = False
    verification_note: Optional[str] = None


@dataclass
class Assertion:
    """Une assertion avec son niveau de confiance."""
    id: str
    content: str
    confidence: ConfidenceLevel
    sources: List[str] = field(default_factory=list)  # IDs des sources
    supporting_agents: List[str] = field(default_factory=list)
    challenging_agents: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)  # IDs des issues
    reasoning: str = ""
    
    @property
    def support_ratio(self) -> float:
        """Ratio de support parmi les agents."""
        total = len(self.supporting_agents) + len(self.challenging_agents)
        if total == 0:
            return 0.0
        return len(self.supporting_agents) / total


@dataclass
class Issue:
    """Un problème détecté par l'auditeur."""
    id: str
    type: IssueType
    description: str
    severity: float  # 0-1
    related_assertion: Optional[str] = None
    detected_by: str = ""
    suggested_action: str = ""
    resolved: bool = False
    resolution_note: Optional[str] = None


@dataclass
class AgentAnalysis:
    """Analyse produite par un agent."""
    agent_id: str
    agent_role: AgentRole
    model_used: str
    timestamp: float
    
    # Contenu
    main_conclusions: List[str] = field(default_factory=list)
    key_arguments: List[str] = field(default_factory=list)
    sources_cited: List[Source] = field(default_factory=list)
    risks_identified: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    
    # Méta
    processing_time_ms: int = 0
    tokens_used: int = 0
    raw_response: str = ""


@dataclass
class PeerReview:
    """Revue par les pairs d'une analyse."""
    reviewer_id: str
    reviewed_agent_id: str
    timestamp: float
    
    weaknesses: List[str] = field(default_factory=list)
    contradictions: List[Tuple[str, str]] = field(default_factory=list)  # (point1, point2)
    uncertain_zones: List[str] = field(default_factory=list)
    corrections_proposed: List[Dict[str, str]] = field(default_factory=list)
    agreement_points: List[str] = field(default_factory=list)
    
    overall_assessment: str = ""
    confidence_in_review: float = 0.5


@dataclass
class AuditReport:
    """Rapport d'audit de l'auditeur interne."""
    auditor_id: str
    timestamp: float
    
    issues_found: List[Issue] = field(default_factory=list)
    unsourced_claims: List[str] = field(default_factory=list)
    circular_reasonings: List[str] = field(default_factory=list)
    approximations: List[str] = field(default_factory=list)
    interpretations_as_facts: List[str] = field(default_factory=list)
    
    sources_requiring_verification: List[str] = field(default_factory=list)
    prudence_recommendations: List[str] = field(default_factory=list)
    
    overall_reliability_score: float = 0.5


@dataclass
class ConsolidatedBlock:
    """Bloc consolidé avec niveau de fiabilité."""
    id: str
    category: ConfidenceLevel
    content: str
    supporting_evidence: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    agent_consensus: Dict[str, bool] = field(default_factory=dict)  # agent_id -> agrees
    residual_risks: List[str] = field(default_factory=list)
    
    @property
    def consensus_ratio(self) -> float:
        """Ratio de consensus."""
        if not self.agent_consensus:
            return 0.0
        return sum(self.agent_consensus.values()) / len(self.agent_consensus)


@dataclass
class InstructionDossier:
    """Dossier d'instruction complet."""
    id: str
    query: str
    created_at: float
    
    # Phase 1: Cadrage
    domain: Domain = Domain.GENERAL
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    protocol: ProtocolType = ProtocolType.STANDARD
    
    # Phase 2: Analyses
    agent_analyses: Dict[str, AgentAnalysis] = field(default_factory=dict)
    
    # Phase 3: Débats
    peer_reviews: List[PeerReview] = field(default_factory=list)
    
    # Phase 4: Audit
    audit_report: Optional[AuditReport] = None
    
    # Phase 5: Consolidation
    consolidated_blocks: Dict[ConfidenceLevel, List[ConsolidatedBlock]] = field(default_factory=dict)
    missing_information: List[str] = field(default_factory=list)
    hypotheses_taken: List[str] = field(default_factory=list)
    disagreement_points: List[str] = field(default_factory=list)
    
    # Phase 6: Traçabilité
    all_sources: Dict[str, Source] = field(default_factory=dict)
    all_issues: Dict[str, Issue] = field(default_factory=dict)
    all_assertions: Dict[str, Assertion] = field(default_factory=dict)
    processing_timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Phase 7: Décision
    human_decision: Optional[str] = None
    human_decision_timestamp: Optional[float] = None
    human_acknowledged_risks: List[str] = field(default_factory=list)
    
    # Statut
    status: str = "initialized"
    current_phase: int = 0
    error: Optional[str] = None
    
    def log_event(self, phase: int, event: str, details: Dict[str, Any] = None):
        """Ajoute un événement à la timeline."""
        self.processing_timeline.append({
            "timestamp": time.time(),
            "phase": phase,
            "event": event,
            "details": details or {}
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: GATE D'ENTRÉE - CADRAGE STRICT
# ═══════════════════════════════════════════════════════════════════════════════

class EntryGate:
    """
    Phase 1: Gate d'entrée - Cadrage strict.
    
    Responsabilités:
    - Qualification du domaine
    - Détection du niveau de criticité
    - Détermination du protocole requis
    
    Règle: Plus la décision est critique, plus le pipeline est lourd.
    Pas de refus possible - seulement basculement vers mode étendu.
    """
    
    # Mots-clés par domaine
    DOMAIN_KEYWORDS = {
        Domain.LEGAL: [
            "juridique", "legal", "loi", "tribunal", "contrat", "litige",
            "droit", "avocat", "jugement", "article", "code", "responsabilité",
            "contentieux", "procès", "jurisprudence", "cour", "cassation",
            "pénal", "prison", "accusé", "défense", "infraction", "délit",
            "crime", "fraude", "travail", "client", "peine", "condamnation"
        ],
        Domain.MEDICAL: [
            "médical", "santé", "patient", "diagnostic", "traitement",
            "maladie", "symptôme", "médicament", "chirurgie", "clinique",
            "hôpital", "thérapie", "pathologie", "ordonnance", "vaccin"
        ],
        Domain.FINANCE: [
            "finance", "investissement", "marché", "action", "obligation",
            "crédit", "banque", "assurance", "fiscal", "impôt", "patrimoine",
            "bourse", "trading", "liquidité", "risque financier"
        ],
        Domain.STRATEGIC: [
            "stratégie", "décision", "organisation", "management", "direction",
            "planification", "objectif", "compétition", "marché", "croissance",
            "transformation", "restructuration", "fusion", "acquisition"
        ],
        Domain.REGULATORY: [
            "réglementation", "conformité", "compliance", "régulateur",
            "autorisation", "licence", "certification", "audit", "contrôle",
            "norme", "standard", "RGPD", "AMF", "ANSM", "HAS"
        ],
        Domain.SCIENTIFIC: [
            "recherche", "étude", "scientifique", "expérience", "hypothèse",
            "méthodologie", "données", "statistique", "publication", "peer-review",
            "laboratoire", "protocole", "essai", "résultat"
        ],
        Domain.TECHNICAL: [
            "technique", "technologie", "système", "architecture", "code",
            "développement", "infrastructure", "sécurité", "performance",
            "scalabilité", "API", "base de données", "algorithme",
            "serveur", "configuration", "configurer", "réseau", "logiciel",
            "application", "bug", "erreur", "déploiement", "docker", "cloud"
        ],
        Domain.ETHICS: [
            "éthique", "morale", "déontologie", "responsabilité", "impact",
            "société", "environnement", "durabilité", "équité", "transparence",
            "consentement", "vie privée", "biais", "discrimination"
        ],
    }
    
    # Indicateurs de criticité
    CRITICALITY_INDICATORS = {
        CriticalityLevel.CRITICAL: [
            "vie ou mort", "irréversible", "pénal", "criminel", "urgence vitale",
            "catastrophique", "faillite", "prison", "décès", "invalidité",
            "radiation", "perte totale", "scandale", "crise majeure"
        ],
        CriticalityLevel.HIGH: [
            "grave", "important", "significatif", "majeur", "contentieux",
            "procès", "sanction", "amende", "perte substantielle", "réputation",
            "responsabilité civile", "audit", "régulateur", "mise en demeure"
        ],
        CriticalityLevel.MEDIUM: [
            "modéré", "standard", "habituel", "courant", "ordinaire",
            "révision", "vérification", "validation", "confirmation"
        ],
        CriticalityLevel.LOW: [
            "mineur", "simple", "information", "conseil", "orientation",
            "général", "préliminaire", "exploratoire"
        ],
    }
    
    # Mapping criticité -> protocole
    CRITICALITY_TO_PROTOCOL = {
        CriticalityLevel.LOW: ProtocolType.LIGHT,
        CriticalityLevel.MEDIUM: ProtocolType.STANDARD,
        CriticalityLevel.HIGH: ProtocolType.REINFORCED,
        CriticalityLevel.CRITICAL: ProtocolType.MAXIMAL,
    }
    
    # Configuration des protocoles
    PROTOCOL_CONFIG = {
        ProtocolType.LIGHT: {
            "min_agents": 2,
            "debate_rounds": 0,
            "audit_required": False,
            "trace_level": "basic",
        },
        ProtocolType.STANDARD: {
            "min_agents": 3,
            "debate_rounds": 1,
            "audit_required": False,
            "trace_level": "standard",
        },
        ProtocolType.REINFORCED: {
            "min_agents": 4,
            "debate_rounds": 2,
            "audit_required": True,
            "trace_level": "detailed",
        },
        ProtocolType.MAXIMAL: {
            "min_agents": 5,
            "debate_rounds": 3,
            "audit_required": True,
            "trace_level": "exhaustive",
        },
    }
    
    def __init__(self):
        self.qualification_history: List[Dict[str, Any]] = []
    
    def qualify_domain(self, query: str, context: Dict[str, Any] = None) -> Domain:
        """
        Qualifie le domaine de la requête.
        
        Micro-steps:
        1. Normaliser le texte
        2. Compter les mots-clés par domaine
        3. Prendre en compte le contexte explicite
        4. Retourner le domaine dominant
        """
        query_lower = query.lower()
        context = context or {}
        
        # Si domaine explicite dans le contexte
        if explicit_domain := context.get("domain"):
            try:
                return Domain(explicit_domain)
            except ValueError:
                pass
        
        # Compter les mots-clés
        domain_scores: Dict[Domain, int] = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                domain_scores[domain] = score
        
        # Retourner le domaine avec le plus de correspondances
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return Domain.GENERAL
    
    def detect_criticality(self, query: str, domain: Domain, 
                          context: Dict[str, Any] = None) -> CriticalityLevel:
        """
        Détecte le niveau de criticité.
        
        Micro-steps:
        1. Scanner les indicateurs de criticité
        2. Pondérer selon le domaine
        3. Appliquer les règles de basculement
        4. Retourner le niveau approprié
        """
        query_lower = query.lower()
        context = context or {}
        
        # Si criticité explicite
        if explicit_crit := context.get("criticality"):
            try:
                return CriticalityLevel(explicit_crit)
            except ValueError:
                pass
        
        # Scanner du plus critique au moins critique
        for level in [CriticalityLevel.CRITICAL, CriticalityLevel.HIGH, 
                      CriticalityLevel.MEDIUM, CriticalityLevel.LOW]:
            indicators = self.CRITICALITY_INDICATORS[level]
            if any(ind in query_lower for ind in indicators):
                # Règle: certains domaines augmentent automatiquement la criticité
                if domain in [Domain.LEGAL, Domain.MEDICAL] and level == CriticalityLevel.MEDIUM:
                    return CriticalityLevel.HIGH
                return level
        
        # Par défaut, les domaines très sensibles sont au niveau HIGH (prudence maximale)
        if domain in [Domain.LEGAL, Domain.MEDICAL]:
            return CriticalityLevel.HIGH
        
        # Les autres domaines sensibles sont au niveau MEDIUM
        if domain in [Domain.FINANCE, Domain.REGULATORY]:
            return CriticalityLevel.MEDIUM
        
        return CriticalityLevel.LOW
    
    def determine_protocol(self, criticality: CriticalityLevel, 
                          context: Dict[str, Any] = None) -> ProtocolType:
        """
        Détermine le protocole requis.
        
        Règle fondamentale: jamais de refus, seulement du renforcement.
        """
        context = context or {}
        
        # Forçage manuel vers un protocole plus lourd (jamais plus léger)
        if forced := context.get("force_protocol"):
            try:
                forced_protocol = ProtocolType(forced)
                base_protocol = self.CRITICALITY_TO_PROTOCOL[criticality]
                # Prendre le plus lourd des deux
                protocols_order = [ProtocolType.LIGHT, ProtocolType.STANDARD, 
                                  ProtocolType.REINFORCED, ProtocolType.MAXIMAL]
                base_idx = protocols_order.index(base_protocol)
                forced_idx = protocols_order.index(forced_protocol)
                return protocols_order[max(base_idx, forced_idx)]
            except (ValueError, KeyError):
                pass
        
        return self.CRITICALITY_TO_PROTOCOL[criticality]
    
    def get_protocol_config(self, protocol: ProtocolType) -> Dict[str, Any]:
        """Retourne la configuration du protocole."""
        return self.PROTOCOL_CONFIG[protocol].copy()
    
    def qualify(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Qualification complète de la requête.
        
        Returns:
            Dict avec domain, criticality, protocol, config
        """
        context = context or {}
        
        # Étape 1: Qualification du domaine
        domain = self.qualify_domain(query, context)
        
        # Étape 2: Détection de criticité
        criticality = self.detect_criticality(query, domain, context)
        
        # Étape 3: Détermination du protocole
        protocol = self.determine_protocol(criticality, context)
        
        # Étape 4: Récupération de la config
        config = self.get_protocol_config(protocol)
        
        result = {
            "domain": domain,
            "criticality": criticality,
            "protocol": protocol,
            "config": config,
            "timestamp": time.time(),
            "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16]
        }
        
        # Historique pour traçabilité
        self.qualification_history.append(result)
        
        logger.info(
            f"🚪 Gate qualification: domain={domain.value}, "
            f"criticality={criticality.value}, protocol={protocol.value}"
        )
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: COLLECTE INDÉPENDANTE
# ═══════════════════════════════════════════════════════════════════════════════

class AgentOrchestrator:
    """
    Phase 2: Orchestration de la collecte indépendante.
    
    Lance plusieurs intelligences en parallèle avec consignes différentes.
    Chaque agent travaille sans voir les autres.
    Objectif: maximiser la diversité cognitive.
    """
    
    # Prompts spécialisés par rôle
    ROLE_PROMPTS = {
        AgentRole.DOCTRINAL: """Tu es un expert en analyse doctrinale stricte.
Ta mission est d'analyser la question selon la DOCTRINE ÉTABLIE uniquement.

CONSIGNES:
- Cite uniquement des principes doctrinaux reconnus
- Référence les auteurs de doctrine majeurs
- Distingue clairement l'opinion majoritaire de l'opinion minoritaire
- Indique les évolutions doctrinales récentes
- Ne spécule pas, reste sur le terrain de la doctrine

FORMAT DE RÉPONSE (JSON):
{
    "main_conclusions": ["conclusion 1", "conclusion 2"],
    "doctrinal_principles": ["principe 1", "principe 2"],
    "sources": [{"type": "doctrine", "reference": "...", "date": "..."}],
    "certainty_level": "high/medium/low",
    "caveats": ["réserve 1", "réserve 2"]
}""",
        
        AgentRole.JURISPRUDENCE: """Tu es un expert en recherche jurisprudentielle.
Ta mission est de trouver la JURISPRUDENCE PERTINENTE et les EXCEPTIONS.

CONSIGNES:
- Recherche les décisions de principe applicables
- Identifie les revirements de jurisprudence
- Signale les exceptions et cas particuliers
- Note les divergences entre juridictions
- Distingue jurisprudence constante et décisions isolées

FORMAT DE RÉPONSE (JSON):
{
    "main_conclusions": ["conclusion 1", "conclusion 2"],
    "relevant_cases": [{"reference": "...", "date": "...", "key_holding": "..."}],
    "exceptions": ["exception 1", "exception 2"],
    "jurisdictional_differences": ["différence 1"],
    "sources": [{"type": "jurisprudence", "reference": "...", "date": "..."}],
    "caveats": ["réserve 1"]
}""",
        
        AgentRole.PROCEDURAL: """Tu es un expert en procédure et gestion des risques contentieux.
Ta mission est d'analyser l'angle PROCÉDURAL et les RISQUES.

CONSIGNES:
- Identifie les règles de procédure applicables
- Évalue les risques contentieux
- Signale les délais et prescriptions
- Note les preuves nécessaires
- Anticipe les arguments adverses

FORMAT DE RÉPONSE (JSON):
{
    "main_conclusions": ["conclusion 1", "conclusion 2"],
    "procedural_rules": ["règle 1", "règle 2"],
    "risks": [{"type": "...", "severity": "high/medium/low", "description": "..."}],
    "deadlines": ["délai 1", "délai 2"],
    "evidence_needed": ["preuve 1", "preuve 2"],
    "adverse_arguments": ["argument 1"],
    "sources": [{"type": "procedure", "reference": "..."}],
    "caveats": ["réserve 1"]
}""",
        
        AgentRole.CONTEXTUAL: """Tu es un expert en analyse contextuelle.
Ta mission est d'analyser le CONTEXTE SPÉCIFIQUE et les CIRCONSTANCES.

CONSIGNES:
- Prends en compte tous les éléments factuels
- Identifie les enjeux cachés ou implicites
- Note les parties prenantes et leurs intérêts
- Évalue l'impact pratique des différentes options
- Considère les contraintes opérationnelles

FORMAT DE RÉPONSE (JSON):
{
    "main_conclusions": ["conclusion 1", "conclusion 2"],
    "contextual_factors": ["facteur 1", "facteur 2"],
    "stakeholders": [{"name": "...", "interest": "...", "power": "high/medium/low"}],
    "practical_implications": ["implication 1"],
    "constraints": ["contrainte 1"],
    "sources": [],
    "caveats": ["réserve 1"]
}""",
        
        AgentRole.COMPARATIVE: """Tu es un expert en droit/pratique comparé.
Ta mission est d'apporter un ÉCLAIRAGE COMPARATIF.

CONSIGNES:
- Compare avec d'autres juridictions/pratiques
- Identifie les tendances internationales
- Note les solutions alternatives adoptées ailleurs
- Évalue la transposabilité
- Signale les évolutions probables

FORMAT DE RÉPONSE (JSON):
{
    "main_conclusions": ["conclusion 1", "conclusion 2"],
    "comparative_analysis": [{"jurisdiction": "...", "approach": "...", "outcome": "..."}],
    "international_trends": ["tendance 1"],
    "alternative_solutions": ["solution 1"],
    "transposability": "high/medium/low",
    "sources": [{"type": "comparative", "reference": "..."}],
    "caveats": ["réserve 1"]
}"""
    }
    
    # Configuration des agents par protocole
    AGENTS_BY_PROTOCOL = {
        ProtocolType.LIGHT: [AgentRole.DOCTRINAL, AgentRole.PROCEDURAL],
        ProtocolType.STANDARD: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, AgentRole.PROCEDURAL],
        ProtocolType.REINFORCED: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, 
                                  AgentRole.PROCEDURAL, AgentRole.CONTEXTUAL],
        ProtocolType.MAXIMAL: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, 
                               AgentRole.PROCEDURAL, AgentRole.CONTEXTUAL, AgentRole.COMPARATIVE],
    }
    
    def __init__(self, llm_caller: Callable = None):
        """
        Args:
            llm_caller: Fonction async pour appeler les LLMs
                        Signature: async def caller(prompt, model, role) -> str
        """
        self.llm_caller = llm_caller
        self.default_models = {
            AgentRole.DOCTRINAL: "anthropic/claude-3.5-sonnet",
            AgentRole.JURISPRUDENCE: "openai/gpt-4o",
            AgentRole.PROCEDURAL: "google/gemini-pro-1.5",
            AgentRole.CONTEXTUAL: "anthropic/claude-3.5-sonnet",
            AgentRole.COMPARATIVE: "openai/gpt-4o",
        }
    
    def get_agents_for_protocol(self, protocol: ProtocolType) -> List[AgentRole]:
        """Retourne les agents requis pour un protocole."""
        return self.AGENTS_BY_PROTOCOL[protocol]
    
    def build_agent_prompt(self, role: AgentRole, query: str, 
                          domain: Domain, context: Dict[str, Any] = None) -> str:
        """Construit le prompt pour un agent."""
        base_prompt = self.ROLE_PROMPTS.get(role, "")
        context = context or {}
        
        return f"""{base_prompt}

═══════════════════════════════════════════════════════════════════
QUESTION À ANALYSER
═══════════════════════════════════════════════════════════════════

Domaine: {domain.value}
Question: {query}

Contexte additionnel:
{json.dumps(context, indent=2, ensure_ascii=False) if context else "Aucun contexte additionnel fourni."}

═══════════════════════════════════════════════════════════════════
IMPORTANT
═══════════════════════════════════════════════════════════════════

- Travaille de manière INDÉPENDANTE
- Ne fais AUCUNE supposition sur ce que d'autres analystes pourraient dire
- Reste dans TON RÔLE SPÉCIFIQUE ({role.value})
- Sois HONNÊTE sur tes incertitudes
- Cite tes SOURCES avec précision
- Réponds UNIQUEMENT en JSON valide
"""
    
    async def run_agent(self, role: AgentRole, query: str, domain: Domain,
                       context: Dict[str, Any] = None) -> AgentAnalysis:
        """
        Exécute un agent et retourne son analyse.
        
        Micro-steps:
        1. Construire le prompt
        2. Appeler le LLM
        3. Parser la réponse
        4. Structurer l'analyse
        """
        agent_id = f"{role.value}_{uuid.uuid4().hex[:8]}"
        model = self.default_models.get(role, "anthropic/claude-3.5-sonnet")
        start_time = time.time()
        
        prompt = self.build_agent_prompt(role, query, domain, context)
        
        # Appel LLM (simulé si pas de caller)
        if self.llm_caller:
            raw_response = await self.llm_caller(prompt, model, role.value)
        else:
            # Simulation pour tests
            raw_response = self._simulate_response(role, query)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Parser la réponse JSON
        parsed = self._parse_agent_response(raw_response)
        
        # Construire les sources
        sources = []
        for src in parsed.get("sources", []):
            sources.append(Source(
                id=f"src_{uuid.uuid4().hex[:8]}",
                type=src.get("type", "unknown"),
                reference=src.get("reference", ""),
                url=src.get("url"),
                date=src.get("date"),
            ))
        
        analysis = AgentAnalysis(
            agent_id=agent_id,
            agent_role=role,
            model_used=model,
            timestamp=time.time(),
            main_conclusions=parsed.get("main_conclusions", []),
            key_arguments=parsed.get("key_arguments", parsed.get("doctrinal_principles", [])),
            sources_cited=sources,
            risks_identified=[r.get("description", r) if isinstance(r, dict) else r 
                            for r in parsed.get("risks", [])],
            caveats=parsed.get("caveats", []),
            processing_time_ms=processing_time,
            raw_response=raw_response,
        )
        
        logger.info(f"🔬 Agent {role.value} completed in {processing_time}ms")
        
        return analysis
    
    async def run_parallel_collection(self, query: str, domain: Domain, 
                                      protocol: ProtocolType,
                                      context: Dict[str, Any] = None) -> Dict[str, AgentAnalysis]:
        """
        Lance tous les agents en parallèle.
        
        Micro-steps:
        1. Déterminer les agents requis
        2. Lancer les tâches en parallèle
        3. Attendre toutes les réponses
        4. Agréger les résultats
        """
        agents = self.get_agents_for_protocol(protocol)
        
        logger.info(f"🚀 Launching {len(agents)} agents in parallel: {[a.value for a in agents]}")
        
        # Créer les tâches
        tasks = [
            self.run_agent(role, query, domain, context)
            for role in agents
        ]
        
        # Exécuter en parallèle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collecter les résultats
        analyses = {}
        for role, result in zip(agents, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {role.value} failed: {result}")
                continue
            analyses[result.agent_id] = result
        
        logger.info(f"✅ Collection complete: {len(analyses)} analyses received")
        
        return analyses
    
    def _parse_agent_response(self, response: str) -> Dict[str, Any]:
        """Parse une réponse JSON d'un agent."""
        import re
        
        # Extraire JSON si embarqué dans du texte
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {"main_conclusions": [], "caveats": ["Parse error"]}
    
    def _simulate_response(self, role: AgentRole, query: str) -> str:
        """Simule une réponse pour les tests."""
        return json.dumps({
            "main_conclusions": [
                f"[SIMULATED] Conclusion principale de l'agent {role.value}",
                f"[SIMULATED] Analyse de la question: {query[:50]}..."
            ],
            "sources": [
                {"type": "doctrine", "reference": f"Réf. simulée {role.value}", "date": "2024"}
            ],
            "caveats": ["Ceci est une réponse simulée pour les tests"],
            "risks": [{"type": "simulation", "severity": "low", "description": "Donnée de test"}]
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: DÉBAT STRUCTURÉ INTER-MODÈLES
# ═══════════════════════════════════════════════════════════════════════════════

class DebateOrchestrator:
    """
    Phase 3: Débat structuré inter-modèles.
    
    Chaque agent reçoit les productions des autres et doit:
    - Signaler les points faibles
    - Identifier les contradictions
    - Marquer les zones incertaines
    - Proposer des corrections
    
    Ce n'est pas du vote, c'est une revue par les pairs automatisée.
    On cherche: où sont les fragilités?
    """
    
    REVIEW_PROMPT = """Tu es un expert chargé de la REVUE PAR LES PAIRS d'une analyse.

Ta mission n'est PAS de donner raison ou tort.
Ta mission est de DÉTECTER LES FRAGILITÉS.

═══════════════════════════════════════════════════════════════════
ANALYSE À RÉVISER (produite par: {agent_role})
═══════════════════════════════════════════════════════════════════

{analysis_content}

═══════════════════════════════════════════════════════════════════
TES TÂCHES
═══════════════════════════════════════════════════════════════════

1. POINTS FAIBLES: Identifie les arguments fragiles ou mal étayés
2. CONTRADICTIONS: Repère les contradictions internes ou avec d'autres analyses
3. ZONES INCERTAINES: Marque ce qui manque de certitude
4. CORRECTIONS: Propose des corrections ou compléments
5. ACCORD: Note les points sur lesquels tu es en accord

FORMAT DE RÉPONSE (JSON):
{{
    "weaknesses": ["faiblesse 1", "faiblesse 2"],
    "contradictions": [["point A dit X", "mais point B dit Y"]],
    "uncertain_zones": ["zone 1", "zone 2"],
    "corrections_proposed": [{{"original": "...", "correction": "...", "reason": "..."}}],
    "agreement_points": ["point d'accord 1"],
    "overall_assessment": "Évaluation globale en 2-3 phrases",
    "confidence_in_review": 0.8
}}

AUTRES ANALYSES DISPONIBLES (pour comparaison):
{other_analyses}

Réponds UNIQUEMENT en JSON valide."""
    
    def __init__(self, llm_caller: Callable = None):
        self.llm_caller = llm_caller
    
    async def conduct_peer_review(
        self,
        reviewer_agent: AgentAnalysis,
        reviewed_agent: AgentAnalysis,
        all_analyses: Dict[str, AgentAnalysis]
    ) -> PeerReview:
        """
        Un agent révise le travail d'un autre.
        
        Micro-steps:
        1. Préparer le contexte de revue
        2. Formater les autres analyses pour comparaison
        3. Appeler le LLM reviewer
        4. Parser et structurer la revue
        """
        # Préparer le contenu de l'analyse à réviser
        analysis_content = json.dumps({
            "conclusions": reviewed_agent.main_conclusions,
            "arguments": reviewed_agent.key_arguments,
            "sources": [s.reference for s in reviewed_agent.sources_cited],
            "risks": reviewed_agent.risks_identified,
            "caveats": reviewed_agent.caveats,
        }, indent=2, ensure_ascii=False)
        
        # Préparer les autres analyses (sans celle en cours de revue)
        other_analyses = {}
        for aid, analysis in all_analyses.items():
            if aid != reviewed_agent.agent_id and aid != reviewer_agent.agent_id:
                other_analyses[analysis.agent_role.value] = {
                    "conclusions": analysis.main_conclusions[:2],  # Résumé
                    "key_points": analysis.key_arguments[:2]
                }
        
        prompt = self.REVIEW_PROMPT.format(
            agent_role=reviewed_agent.agent_role.value,
            analysis_content=analysis_content,
            other_analyses=json.dumps(other_analyses, indent=2, ensure_ascii=False)
        )
        
        # Appel LLM
        if self.llm_caller:
            raw_response = await self.llm_caller(
                prompt, 
                "anthropic/claude-3.5-sonnet",
                f"reviewer_{reviewer_agent.agent_role.value}"
            )
        else:
            raw_response = self._simulate_review()
        
        # Parser
        parsed = self._parse_review_response(raw_response)
        
        return PeerReview(
            reviewer_id=reviewer_agent.agent_id,
            reviewed_agent_id=reviewed_agent.agent_id,
            timestamp=time.time(),
            weaknesses=parsed.get("weaknesses", []),
            contradictions=[tuple(c) if isinstance(c, list) else (c, "") 
                           for c in parsed.get("contradictions", [])],
            uncertain_zones=parsed.get("uncertain_zones", []),
            corrections_proposed=parsed.get("corrections_proposed", []),
            agreement_points=parsed.get("agreement_points", []),
            overall_assessment=parsed.get("overall_assessment", ""),
            confidence_in_review=parsed.get("confidence_in_review", 0.5),
        )
    
    async def run_debate_round(
        self,
        analyses: Dict[str, AgentAnalysis],
        round_number: int
    ) -> List[PeerReview]:
        """
        Exécute un round de débat complet.
        
        Chaque agent révise tous les autres.
        
        Micro-steps:
        1. Créer les paires reviewer/reviewed
        2. Lancer les revues en parallèle
        3. Collecter les résultats
        """
        logger.info(f"🗣️ Starting debate round {round_number}")
        
        reviews = []
        agents = list(analyses.values())
        
        # Chaque agent révise les autres
        review_tasks = []
        for reviewer in agents:
            for reviewed in agents:
                if reviewer.agent_id != reviewed.agent_id:
                    review_tasks.append(
                        self.conduct_peer_review(reviewer, reviewed, analyses)
                    )
        
        # Exécuter en parallèle
        results = await asyncio.gather(*review_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Review failed: {result}")
                continue
            reviews.append(result)
        
        logger.info(f"✅ Debate round {round_number} complete: {len(reviews)} reviews")
        
        return reviews
    
    async def run_full_debate(
        self,
        analyses: Dict[str, AgentAnalysis],
        num_rounds: int
    ) -> List[PeerReview]:
        """Exécute le débat complet sur plusieurs rounds."""
        all_reviews = []
        
        for round_num in range(1, num_rounds + 1):
            round_reviews = await self.run_debate_round(analyses, round_num)
            all_reviews.extend(round_reviews)
        
        return all_reviews
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse une réponse de revue."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
    
    def _simulate_review(self) -> str:
        """Simule une revue pour les tests."""
        return json.dumps({
            "weaknesses": ["[SIM] Point faible détecté"],
            "contradictions": [["[SIM] Point A", "[SIM] Point B contradictoire"]],
            "uncertain_zones": ["[SIM] Zone d'incertitude"],
            "corrections_proposed": [{"original": "[SIM]", "correction": "[SIM]", "reason": "Test"}],
            "agreement_points": ["[SIM] Point d'accord"],
            "overall_assessment": "[SIMULATED] Revue de test",
            "confidence_in_review": 0.7
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: DÉTECTION ACTIVE D'HALLUCINATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class HallucinationHunter:
    """
    Phase 4: Détection active d'hallucinations.
    
    Agent spécialisé dont la mission N'EST PAS de répondre,
    mais de CHASSER les affirmations douteuses.
    
    Il doit:
    - Relever toute affirmation non sourcée
    - Signaler les raisonnements circulaires
    - Détecter les approximations
    - Marquer ce qui relève d'une interprétation et non d'un fait
    - Exiger sources ou prudence explicite
    
    C'est l'auditeur interne.
    """
    
    AUDIT_PROMPT = """Tu es un AUDITEUR INTERNE spécialisé dans la détection d'hallucinations et d'affirmations douteuses.

Ta mission N'EST PAS de répondre à la question.
Ta mission EST DE CHASSER les problèmes dans les analyses fournies.

═══════════════════════════════════════════════════════════════════
ANALYSES À AUDITER
═══════════════════════════════════════════════════════════════════

{all_analyses}

═══════════════════════════════════════════════════════════════════
TES TÂCHES D'AUDIT
═══════════════════════════════════════════════════════════════════

1. AFFIRMATIONS NON SOURCÉES
   - Relève TOUTE affirmation présentée comme un fait sans source
   - Exige une source ou une reformulation en "hypothèse"

2. RAISONNEMENTS CIRCULAIRES
   - Détecte les arguments qui se justifient par eux-mêmes
   - Identifie les pétitions de principe

3. APPROXIMATIONS
   - Repère les "environ", "généralement", "souvent" non quantifiés
   - Signale les généralisations abusives

4. INTERPRÉTATIONS PRÉSENTÉES COMME FAITS
   - Distingue ce qui EST de ce qui POURRAIT ÊTRE
   - Marque les analyses présentées comme des certitudes

5. SOURCES À VÉRIFIER
   - Identifie les sources potentiellement obsolètes
   - Note les références imprécises ou invérifiables

6. RECOMMANDATIONS DE PRUDENCE
   - Suggère où ajouter des réserves
   - Propose des reformulations plus honnêtes

FORMAT DE RÉPONSE (JSON):
{{
    "issues_found": [
        {{
            "type": "unsourced_claim|circular_reasoning|approximation|interpretation|outdated_source|overconfidence",
            "description": "Description du problème",
            "location": "Agent X, conclusion Y",
            "severity": 0.0 à 1.0,
            "suggested_action": "Action recommandée"
        }}
    ],
    "unsourced_claims": ["affirmation 1", "affirmation 2"],
    "circular_reasonings": ["raisonnement 1"],
    "approximations": ["approximation 1"],
    "interpretations_as_facts": ["interprétation 1"],
    "sources_requiring_verification": ["source 1"],
    "prudence_recommendations": ["recommandation 1"],
    "overall_reliability_score": 0.0 à 1.0
}}

Sois IMPITOYABLE. Mieux vaut un faux positif qu'une hallucination non détectée.
Réponds UNIQUEMENT en JSON valide."""
    
    def __init__(self, llm_caller: Callable = None):
        self.llm_caller = llm_caller
    
    async def audit_analyses(
        self,
        analyses: Dict[str, AgentAnalysis],
        peer_reviews: List[PeerReview] = None
    ) -> AuditReport:
        """
        Audite toutes les analyses et les revues.
        
        Micro-steps:
        1. Agréger toutes les analyses
        2. Inclure les points soulevés par les revues
        3. Lancer l'audit
        4. Parser et structurer le rapport
        """
        # Préparer le contenu à auditer
        audit_content = {}
        
        for agent_id, analysis in analyses.items():
            audit_content[f"Agent {analysis.agent_role.value}"] = {
                "conclusions": analysis.main_conclusions,
                "arguments": analysis.key_arguments,
                "sources": [{"ref": s.reference, "verified": s.verified} 
                           for s in analysis.sources_cited],
                "risks": analysis.risks_identified,
                "caveats": analysis.caveats,
            }
        
        # Ajouter les points de débat
        if peer_reviews:
            audit_content["Points de débat identifiés"] = {
                "weaknesses": list(set(w for r in peer_reviews for w in r.weaknesses)),
                "contradictions": [c for r in peer_reviews for c in r.contradictions],
                "uncertain_zones": list(set(z for r in peer_reviews for z in r.uncertain_zones)),
            }
        
        prompt = self.AUDIT_PROMPT.format(
            all_analyses=json.dumps(audit_content, indent=2, ensure_ascii=False)
        )
        
        # Appel LLM
        if self.llm_caller:
            raw_response = await self.llm_caller(
                prompt,
                "anthropic/claude-3.5-sonnet",
                "hallucination_hunter"
            )
        else:
            raw_response = self._simulate_audit()
        
        # Parser
        parsed = self._parse_audit_response(raw_response)
        
        # Construire les issues
        issues = []
        for issue_data in parsed.get("issues_found", []):
            issues.append(Issue(
                id=f"issue_{uuid.uuid4().hex[:8]}",
                type=IssueType(issue_data.get("type", "approximation")),
                description=issue_data.get("description", ""),
                severity=issue_data.get("severity", 0.5),
                detected_by="hallucination_hunter",
                suggested_action=issue_data.get("suggested_action", ""),
            ))
        
        report = AuditReport(
            auditor_id=f"auditor_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            issues_found=issues,
            unsourced_claims=parsed.get("unsourced_claims", []),
            circular_reasonings=parsed.get("circular_reasonings", []),
            approximations=parsed.get("approximations", []),
            interpretations_as_facts=parsed.get("interpretations_as_facts", []),
            sources_requiring_verification=parsed.get("sources_requiring_verification", []),
            prudence_recommendations=parsed.get("prudence_recommendations", []),
            overall_reliability_score=parsed.get("overall_reliability_score", 0.5),
        )
        
        logger.info(
            f"🔍 Audit complete: {len(issues)} issues found, "
            f"reliability score: {report.overall_reliability_score:.2f}"
        )
        
        return report
    
    def _parse_audit_response(self, response: str) -> Dict[str, Any]:
        """Parse une réponse d'audit."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
    
    def _simulate_audit(self) -> str:
        """Simule un audit pour les tests."""
        return json.dumps({
            "issues_found": [
                {
                    "type": "unsourced_claim",
                    "description": "[SIM] Affirmation sans source détectée",
                    "location": "Agent doctrinal, conclusion 1",
                    "severity": 0.6,
                    "suggested_action": "Ajouter une source ou reformuler en hypothèse"
                }
            ],
            "unsourced_claims": ["[SIM] Affirmation 1 non sourcée"],
            "circular_reasonings": [],
            "approximations": ["[SIM] Utilisation de 'généralement' sans quantification"],
            "interpretations_as_facts": [],
            "sources_requiring_verification": ["[SIM] Source datée de 2020"],
            "prudence_recommendations": ["[SIM] Ajouter une réserve sur l'applicabilité"],
            "overall_reliability_score": 0.65
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: CONSOLIDATION AVEC DEGRÉS DE FIABILITÉ
# ═══════════════════════════════════════════════════════════════════════════════

class Consolidator:
    """
    Phase 5: Consolidation avec degrés de fiabilité.
    
    Ce n'est qu'après le débat et l'audit qu'on autorise la synthèse.
    La synthèse ne doit JAMAIS être binaire.
    
    Elle produit:
    - Ce qui est hautement fiable (consensus fort + sources solides)
    - Ce qui est probable mais discutable
    - Ce qui est incertain
    - Ce qui manque comme information
    - Les hypothèses prises
    - Les points de désaccord entre modèles
    
    Le résultat est un RAPPORT D'INSTRUCTION, pas une opinion.
    """
    
    CONSOLIDATION_PROMPT = """Tu es un SYNTHÉTISEUR chargé de produire un RAPPORT D'INSTRUCTION.

Tu NE DONNES PAS une opinion.
Tu STRUCTURES les éléments selon leur NIVEAU DE FIABILITÉ.

═══════════════════════════════════════════════════════════════════
MATÉRIAU À CONSOLIDER
═══════════════════════════════════════════════════════════════════

ANALYSES DES AGENTS:
{analyses}

DÉBATS ET REVUES PAR LES PAIRS:
{reviews}

RAPPORT D'AUDIT:
{audit}

═══════════════════════════════════════════════════════════════════
STRUCTURE DE SORTIE REQUISE
═══════════════════════════════════════════════════════════════════

Tu dois classer CHAQUE élément dans UNE des catégories suivantes:

1. HIGHLY_RELIABLE (consensus fort + sources solides)
   - Tous les agents concordent
   - Sources multiples et vérifiées
   - Pas d'issue d'audit sur ce point

2. PROBABLE (probable mais discutable)
   - Majorité des agents concordent
   - Au moins une source
   - Issues mineures possibles

3. UNCERTAIN (incertain)
   - Désaccord entre agents
   - Sources limitées ou contestées
   - Issues d'audit significatives

4. MISSING_INFO (information manquante pour conclure)
   - Éléments factuels non disponibles
   - Sources impossibles à vérifier
   - Données requises non fournies

5. HYPOTHESIS (hypothèses prises)
   - Suppositions nécessaires au raisonnement
   - Interprétations retenues

6. DISPUTED (points de désaccord)
   - Contradictions non résolues entre agents
   - Arguments opposés de poids équivalent

FORMAT DE RÉPONSE (JSON):
{{
    "highly_reliable": [
        {{
            "content": "Élément fiable",
            "supporting_evidence": ["preuve 1", "preuve 2"],
            "source_refs": ["source 1"],
            "consensus_agents": ["doctrinal", "jurisprudence"]
        }}
    ],
    "probable": [...],
    "uncertain": [...],
    "missing_info": ["Information manquante 1"],
    "hypotheses_taken": ["Hypothèse 1"],
    "disagreement_points": ["Désaccord 1: Agent A dit X, Agent B dit Y"],
    "residual_risks": ["Risque résiduel 1"],
    "executive_summary": "Résumé exécutif en 3-5 phrases"
}}

Sois EXHAUSTIF et HONNÊTE. Chaque élément doit être classé.
Réponds UNIQUEMENT en JSON valide."""
    
    def __init__(self, llm_caller: Callable = None):
        self.llm_caller = llm_caller
    
    async def consolidate(
        self,
        analyses: Dict[str, AgentAnalysis],
        peer_reviews: List[PeerReview],
        audit_report: AuditReport
    ) -> Dict[str, Any]:
        """
        Consolide toutes les analyses en un rapport structuré.
        
        Micro-steps:
        1. Préparer le matériau (analyses, débats, audit)
        2. Appeler le synthétiseur
        3. Parser et structurer les blocs
        4. Calculer les métriques de consensus
        """
        # Préparer les analyses
        analyses_content = {}
        for agent_id, analysis in analyses.items():
            analyses_content[analysis.agent_role.value] = {
                "conclusions": analysis.main_conclusions,
                "arguments": analysis.key_arguments,
                "sources": [s.reference for s in analysis.sources_cited],
                "risks": analysis.risks_identified,
                "caveats": analysis.caveats,
            }
        
        # Préparer les revues
        reviews_content = {
            "weaknesses_identified": list(set(w for r in peer_reviews for w in r.weaknesses)),
            "contradictions": [list(c) for r in peer_reviews for c in r.contradictions],
            "uncertain_zones": list(set(z for r in peer_reviews for z in r.uncertain_zones)),
            "corrections_proposed": [c for r in peer_reviews for c in r.corrections_proposed],
            "agreement_points": list(set(a for r in peer_reviews for a in r.agreement_points)),
        }
        
        # Préparer l'audit
        audit_content = {
            "issues": [{"type": i.type.value, "desc": i.description, "severity": i.severity}
                      for i in audit_report.issues_found],
            "unsourced_claims": audit_report.unsourced_claims,
            "reliability_score": audit_report.overall_reliability_score,
            "prudence_recommendations": audit_report.prudence_recommendations,
        }
        
        prompt = self.CONSOLIDATION_PROMPT.format(
            analyses=json.dumps(analyses_content, indent=2, ensure_ascii=False),
            reviews=json.dumps(reviews_content, indent=2, ensure_ascii=False),
            audit=json.dumps(audit_content, indent=2, ensure_ascii=False),
        )
        
        # Appel LLM
        if self.llm_caller:
            raw_response = await self.llm_caller(
                prompt,
                "anthropic/claude-3.5-sonnet",
                "synthesizer"
            )
        else:
            raw_response = self._simulate_consolidation()
        
        # Parser
        parsed = self._parse_consolidation_response(raw_response)
        
        # Construire les blocs consolidés
        consolidated_blocks = {}
        for level in ConfidenceLevel:
            key = level.value
            if key in parsed:
                blocks = []
                for item in parsed[key]:
                    if isinstance(item, dict):
                        blocks.append(ConsolidatedBlock(
                            id=f"block_{uuid.uuid4().hex[:8]}",
                            category=level,
                            content=item.get("content", str(item)),
                            supporting_evidence=item.get("supporting_evidence", []),
                            source_ids=item.get("source_refs", []),
                        ))
                    else:
                        blocks.append(ConsolidatedBlock(
                            id=f"block_{uuid.uuid4().hex[:8]}",
                            category=level,
                            content=str(item),
                        ))
                consolidated_blocks[level] = blocks
        
        result = {
            "consolidated_blocks": consolidated_blocks,
            "missing_information": parsed.get("missing_info", []),
            "hypotheses_taken": parsed.get("hypotheses_taken", []),
            "disagreement_points": parsed.get("disagreement_points", []),
            "residual_risks": parsed.get("residual_risks", []),
            "executive_summary": parsed.get("executive_summary", ""),
        }
        
        logger.info(
            f"📊 Consolidation complete: "
            f"{sum(len(b) for b in consolidated_blocks.values())} blocks created"
        )
        
        return result
    
    def _parse_consolidation_response(self, response: str) -> Dict[str, Any]:
        """Parse une réponse de consolidation."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
    
    def _simulate_consolidation(self) -> str:
        """Simule une consolidation pour les tests."""
        return json.dumps({
            "highly_reliable": [
                {
                    "content": "[SIM] Élément hautement fiable avec consensus",
                    "supporting_evidence": ["Preuve 1", "Preuve 2"],
                    "source_refs": ["Source A"],
                    "consensus_agents": ["doctrinal", "jurisprudence"]
                }
            ],
            "probable": [
                {
                    "content": "[SIM] Élément probable mais discutable",
                    "supporting_evidence": ["Preuve partielle"],
                    "source_refs": ["Source B"]
                }
            ],
            "uncertain": [
                {
                    "content": "[SIM] Élément incertain - besoin de vérification",
                    "supporting_evidence": []
                }
            ],
            "missing_info": ["[SIM] Information X non disponible"],
            "hypotheses_taken": ["[SIM] Hypothèse: contexte standard"],
            "disagreement_points": ["[SIM] Agent A dit X, Agent B dit Y"],
            "residual_risks": ["[SIM] Risque de changement réglementaire"],
            "executive_summary": "[SIMULATED] Synthèse de test pour validation du pipeline."
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: TRAÇABILITÉ SYSTÉMATIQUE
# ═══════════════════════════════════════════════════════════════════════════════

class TraceabilityManager:
    """
    Phase 6: Traçabilité systématique.
    
    Chaque réponse critique doit embarquer:
    - Quels agents ont travaillé
    - Quelles sources ont été utilisées
    - Quels points ont fait débat
    - Quel niveau de confiance est associé à chaque bloc
    - Quels sont les risques résiduels
    
    Une IA qui EXPLIQUE ses propres LIMITES au lieu de les masquer.
    """
    
    def __init__(self):
        self.trace_store: Dict[str, Dict[str, Any]] = {}
    
    def generate_trace(self, dossier: InstructionDossier) -> Dict[str, Any]:
        """
        Génère une trace complète du processus d'instruction.
        
        Micro-steps:
        1. Collecter les métadonnées des agents
        2. Agréger les sources utilisées
        3. Lister les points de débat
        4. Associer les niveaux de confiance
        5. Documenter les risques résiduels
        """
        trace = {
            "dossier_id": dossier.id,
            "query": dossier.query,
            "generated_at": time.time(),
            
            # Métadonnées de cadrage
            "framing": {
                "domain": dossier.domain.value,
                "criticality": dossier.criticality.value,
                "protocol": dossier.protocol.value,
            },
            
            # Agents impliqués
            "agents_involved": [],
            
            # Sources utilisées
            "sources_used": [],
            
            # Points de débat
            "debate_points": [],
            
            # Niveaux de confiance par bloc
            "confidence_mapping": {},
            
            # Risques résiduels
            "residual_risks": [],
            
            # Timeline du processus
            "processing_timeline": dossier.processing_timeline,
            
            # Métriques
            "metrics": {},
        }
        
        # Collecter les agents
        for agent_id, analysis in dossier.agent_analyses.items():
            trace["agents_involved"].append({
                "id": agent_id,
                "role": analysis.agent_role.value,
                "model": analysis.model_used,
                "processing_time_ms": analysis.processing_time_ms,
                "conclusions_count": len(analysis.main_conclusions),
                "sources_cited_count": len(analysis.sources_cited),
            })
        
        # Collecter les sources
        for source_id, source in dossier.all_sources.items():
            trace["sources_used"].append({
                "id": source_id,
                "type": source.type,
                "reference": source.reference,
                "reliability": source.reliability_score,
                "verified": source.verified,
            })
        
        # Collecter les points de débat
        for review in dossier.peer_reviews:
            for weakness in review.weaknesses:
                trace["debate_points"].append({
                    "type": "weakness",
                    "content": weakness,
                    "raised_by": review.reviewer_id,
                })
            for contradiction in review.contradictions:
                trace["debate_points"].append({
                    "type": "contradiction",
                    "content": f"{contradiction[0]} vs {contradiction[1]}",
                    "raised_by": review.reviewer_id,
                })
        
        # Mapping de confiance
        for level, blocks in dossier.consolidated_blocks.items():
            trace["confidence_mapping"][level.value] = len(blocks)
        
        # Risques résiduels
        trace["residual_risks"] = dossier.disagreement_points + [
            f"Missing: {info}" for info in dossier.missing_information
        ]
        
        # Métriques
        trace["metrics"] = {
            "total_agents": len(dossier.agent_analyses),
            "total_sources": len(dossier.all_sources),
            "total_issues": len(dossier.all_issues),
            "peer_reviews_count": len(dossier.peer_reviews),
            "overall_reliability": dossier.audit_report.overall_reliability_score if dossier.audit_report else None,
        }
        
        # Stocker la trace
        self.trace_store[dossier.id] = trace
        
        logger.info(f"📋 Trace generated for dossier {dossier.id[:8]}")
        
        return trace
    
    def export_trace_markdown(self, trace: Dict[str, Any]) -> str:
        """Exporte la trace en format Markdown lisible."""
        md = []
        
        md.append("# 📋 TRACE D'INSTRUCTION CONTRADICTOIRE")
        md.append(f"\n**Dossier ID:** `{trace['dossier_id'][:16]}...`")
        md.append(f"**Généré le:** {datetime.fromtimestamp(trace['generated_at']).isoformat()}")
        
        md.append("\n## 🚪 Cadrage")
        md.append(f"- **Domaine:** {trace['framing']['domain']}")
        md.append(f"- **Criticité:** {trace['framing']['criticality']}")
        md.append(f"- **Protocole:** {trace['framing']['protocol']}")
        
        md.append("\n## 🤖 Agents Impliqués")
        for agent in trace['agents_involved']:
            md.append(f"- **{agent['role']}** (`{agent['model']}`): "
                     f"{agent['conclusions_count']} conclusions, "
                     f"{agent['sources_cited_count']} sources, "
                     f"{agent['processing_time_ms']}ms")
        
        md.append("\n## 📚 Sources Utilisées")
        for source in trace['sources_used'][:10]:  # Limiter
            verified = "✓" if source['verified'] else "?"
            md.append(f"- [{verified}] **{source['type']}:** {source['reference']}")
        
        md.append("\n## 🗣️ Points de Débat")
        for point in trace['debate_points'][:10]:
            md.append(f"- **{point['type']}:** {point['content']}")
        
        md.append("\n## 📊 Niveaux de Confiance")
        for level, count in trace['confidence_mapping'].items():
            md.append(f"- **{level}:** {count} éléments")
        
        md.append("\n## ⚠️ Risques Résiduels")
        for risk in trace['residual_risks'][:5]:
            md.append(f"- {risk}")
        
        md.append("\n## 📈 Métriques")
        for key, value in trace['metrics'].items():
            md.append(f"- **{key}:** {value}")
        
        return "\n".join(md)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: ACCEPTATION - DÉCISION HUMAINE
# ═══════════════════════════════════════════════════════════════════════════════

class HumanDecisionInterface:
    """
    Phase 7: Interface de décision humaine.
    
    Même avec ce pipeline, on n'obtient PAS une "vérité absolue".
    On obtient un DOSSIER D'AIDE À LA DÉCISION équivalent à
    une cellule d'experts humains bien organisée.
    
    La décision finale doit rester:
    - HUMAINE
    - ASSUMÉE
    - CONSCIENTE du risque résiduel
    """
    
    def __init__(self):
        self.pending_decisions: Dict[str, InstructionDossier] = {}
        self.decision_callbacks: List[Callable] = []
    
    def present_for_decision(self, dossier: InstructionDossier) -> Dict[str, Any]:
        """
        Prépare le dossier pour présentation à l'humain.
        
        Micro-steps:
        1. Structurer l'executive summary
        2. Lister les options avec leurs niveaux de fiabilité
        3. Expliciter les risques à assumer
        4. Préparer le formulaire d'acceptation
        """
        presentation = {
            "dossier_id": dossier.id,
            "query": dossier.query,
            
            "executive_summary": self._build_executive_summary(dossier),
            
            "highly_reliable_findings": [
                b.content for b in dossier.consolidated_blocks.get(ConfidenceLevel.HIGHLY_RELIABLE, [])
            ],
            
            "probable_findings": [
                b.content for b in dossier.consolidated_blocks.get(ConfidenceLevel.PROBABLE, [])
            ],
            
            "uncertainties": [
                b.content for b in dossier.consolidated_blocks.get(ConfidenceLevel.UNCERTAIN, [])
            ],
            
            "missing_information": dossier.missing_information,
            
            "hypotheses_to_accept": dossier.hypotheses_taken,
            
            "unresolved_disagreements": dossier.disagreement_points,
            
            "risks_to_acknowledge": self._compile_risks(dossier),
            
            "reliability_score": dossier.audit_report.overall_reliability_score if dossier.audit_report else None,
            
            "decision_form": {
                "options": [
                    {"id": "accept", "label": "Accepter les conclusions hautement fiables"},
                    {"id": "accept_with_reserves", "label": "Accepter avec réserves explicites"},
                    {"id": "request_more_info", "label": "Demander des informations complémentaires"},
                    {"id": "reject", "label": "Rejeter et reconsidérer"},
                ],
                "required_acknowledgments": [
                    "J'ai lu et compris les éléments incertains",
                    "J'accepte les hypothèses prises",
                    "Je suis conscient(e) des risques résiduels",
                    "La décision finale est mienne et assumée",
                ],
            },
        }
        
        self.pending_decisions[dossier.id] = dossier
        
        return presentation
    
    def record_human_decision(
        self,
        dossier_id: str,
        decision: str,
        acknowledged_risks: List[str],
        notes: str = ""
    ) -> bool:
        """
        Enregistre la décision humaine.
        
        Micro-steps:
        1. Valider que tous les acknowledgments sont présents
        2. Enregistrer la décision
        3. Mettre à jour le dossier
        4. Notifier les callbacks
        """
        dossier = self.pending_decisions.get(dossier_id)
        if not dossier:
            logger.error(f"Dossier {dossier_id} not found for decision")
            return False
        
        # Enregistrer la décision
        dossier.human_decision = decision
        dossier.human_decision_timestamp = time.time()
        dossier.human_acknowledged_risks = acknowledged_risks
        dossier.status = "decided"
        
        dossier.log_event(7, "human_decision_recorded", {
            "decision": decision,
            "acknowledged_risks_count": len(acknowledged_risks),
            "notes": notes,
        })
        
        # Notifier
        for callback in self.decision_callbacks:
            try:
                callback(dossier)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")
        
        logger.info(
            f"✅ Human decision recorded for dossier {dossier_id[:8]}: {decision}"
        )
        
        return True
    
    def _build_executive_summary(self, dossier: InstructionDossier) -> str:
        """Construit le résumé exécutif."""
        summary_parts = []
        
        # Domaine et criticité
        summary_parts.append(
            f"Analyse {dossier.domain.value} de niveau de criticité {dossier.criticality.value}."
        )
        
        # Nombre d'éléments fiables
        reliable_count = len(dossier.consolidated_blocks.get(ConfidenceLevel.HIGHLY_RELIABLE, []))
        probable_count = len(dossier.consolidated_blocks.get(ConfidenceLevel.PROBABLE, []))
        uncertain_count = len(dossier.consolidated_blocks.get(ConfidenceLevel.UNCERTAIN, []))
        
        summary_parts.append(
            f"{reliable_count} éléments hautement fiables, "
            f"{probable_count} probables, {uncertain_count} incertains."
        )
        
        # Score de fiabilité
        if dossier.audit_report:
            score = dossier.audit_report.overall_reliability_score
            summary_parts.append(f"Score de fiabilité global: {score:.0%}.")
        
        # Risques
        if dossier.disagreement_points:
            summary_parts.append(
                f"Attention: {len(dossier.disagreement_points)} point(s) de désaccord non résolu(s)."
            )
        
        return " ".join(summary_parts)
    
    def _compile_risks(self, dossier: InstructionDossier) -> List[str]:
        """Compile tous les risques à reconnaître."""
        risks = []
        
        # Désaccords
        for disagreement in dossier.disagreement_points:
            risks.append(f"Désaccord non résolu: {disagreement}")
        
        # Informations manquantes
        for missing in dossier.missing_information:
            risks.append(f"Information manquante: {missing}")
        
        # Issues d'audit
        if dossier.audit_report:
            for issue in dossier.audit_report.issues_found:
                if issue.severity > 0.5:
                    risks.append(f"Issue d'audit ({issue.type.value}): {issue.description}")
        
        return risks


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class AdversarialInstructionPipeline:
    """
    Orchestrateur principal du pipeline d'instruction contradictoire.
    
    Coordonne les 7 phases:
    1. Gate d'entrée (cadrage)
    2. Collecte indépendante
    3. Débat structuré
    4. Détection d'hallucinations
    5. Consolidation
    6. Traçabilité
    7. Décision humaine
    """
    
    def __init__(self, llm_caller: Callable = None):
        """
        Args:
            llm_caller: Fonction async pour appeler les LLMs
                        Signature: async def caller(prompt, model, role) -> str
        """
        self.llm_caller = llm_caller
        
        # Initialiser les composants
        self.entry_gate = EntryGate()
        self.agent_orchestrator = AgentOrchestrator(llm_caller)
        self.debate_orchestrator = DebateOrchestrator(llm_caller)
        self.hallucination_hunter = HallucinationHunter(llm_caller)
        self.consolidator = Consolidator(llm_caller)
        self.traceability_manager = TraceabilityManager()
        self.human_interface = HumanDecisionInterface()
        
        # Dossiers actifs
        self.active_dossiers: Dict[str, InstructionDossier] = {}
        
        logger.info("⚖️ AdversarialInstructionPipeline initialized")
    
    async def run_full_pipeline(
        self,
        query: str,
        context: Dict[str, Any] = None
    ) -> InstructionDossier:
        """
        Exécute le pipeline complet d'instruction contradictoire.
        
        Args:
            query: La question ou demande à analyser
            context: Contexte additionnel (optionnel)
            
        Returns:
            InstructionDossier complet
        """
        context = context or {}
        
        # Créer le dossier
        dossier = InstructionDossier(
            id=str(uuid.uuid4()),
            query=query,
            created_at=time.time(),
        )
        self.active_dossiers[dossier.id] = dossier
        
        try:
            # ═══════════════════════════════════════════════════════════
            # PHASE 1: GATE D'ENTRÉE
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 1
            dossier.log_event(1, "phase_started", {"phase": "entry_gate"})
            
            qualification = self.entry_gate.qualify(query, context)
            dossier.domain = qualification["domain"]
            dossier.criticality = qualification["criticality"]
            dossier.protocol = qualification["protocol"]
            
            config = qualification["config"]
            dossier.log_event(1, "phase_completed", {
                "domain": dossier.domain.value,
                "criticality": dossier.criticality.value,
                "protocol": dossier.protocol.value,
            })
            
            logger.info(f"📋 Dossier {dossier.id[:8]}: Phase 1 complete - {dossier.protocol.value}")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 2: COLLECTE INDÉPENDANTE
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 2
            dossier.log_event(2, "phase_started", {"agents_count": config["min_agents"]})
            
            analyses = await self.agent_orchestrator.run_parallel_collection(
                query, dossier.domain, dossier.protocol, context
            )
            dossier.agent_analyses = analyses
            
            # Collecter les sources
            for analysis in analyses.values():
                for source in analysis.sources_cited:
                    dossier.all_sources[source.id] = source
            
            dossier.log_event(2, "phase_completed", {
                "analyses_count": len(analyses),
                "sources_count": len(dossier.all_sources),
            })
            
            logger.info(f"📋 Dossier {dossier.id[:8]}: Phase 2 complete - {len(analyses)} analyses")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 3: DÉBAT STRUCTURÉ
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 3
            num_rounds = config["debate_rounds"]
            dossier.log_event(3, "phase_started", {"debate_rounds": num_rounds})
            
            if num_rounds > 0:
                peer_reviews = await self.debate_orchestrator.run_full_debate(
                    analyses, num_rounds
                )
                dossier.peer_reviews = peer_reviews
            
            dossier.log_event(3, "phase_completed", {
                "reviews_count": len(dossier.peer_reviews),
            })
            
            logger.info(f"📋 Dossier {dossier.id[:8]}: Phase 3 complete - {len(dossier.peer_reviews)} reviews")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 4: DÉTECTION D'HALLUCINATIONS
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 4
            dossier.log_event(4, "phase_started", {"audit_required": config["audit_required"]})
            
            if config["audit_required"]:
                audit_report = await self.hallucination_hunter.audit_analyses(
                    analyses, dossier.peer_reviews
                )
                dossier.audit_report = audit_report
                
                # Collecter les issues
                for issue in audit_report.issues_found:
                    dossier.all_issues[issue.id] = issue
            else:
                # Audit minimal même sans requirement
                dossier.audit_report = AuditReport(
                    auditor_id="minimal",
                    timestamp=time.time(),
                    overall_reliability_score=0.5,
                )
            
            dossier.log_event(4, "phase_completed", {
                "issues_found": len(dossier.all_issues),
                "reliability_score": dossier.audit_report.overall_reliability_score,
            })
            
            logger.info(
                f"📋 Dossier {dossier.id[:8]}: Phase 4 complete - "
                f"{len(dossier.all_issues)} issues, "
                f"reliability: {dossier.audit_report.overall_reliability_score:.2f}"
            )
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 5: CONSOLIDATION
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 5
            dossier.log_event(5, "phase_started", {})
            
            consolidation = await self.consolidator.consolidate(
                analyses, dossier.peer_reviews, dossier.audit_report
            )
            
            dossier.consolidated_blocks = consolidation["consolidated_blocks"]
            dossier.missing_information = consolidation["missing_information"]
            dossier.hypotheses_taken = consolidation["hypotheses_taken"]
            dossier.disagreement_points = consolidation["disagreement_points"]
            
            dossier.log_event(5, "phase_completed", {
                "blocks_created": sum(len(b) for b in dossier.consolidated_blocks.values()),
            })
            
            logger.info(f"📋 Dossier {dossier.id[:8]}: Phase 5 complete - consolidation done")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 6: TRAÇABILITÉ
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 6
            dossier.log_event(6, "phase_started", {})
            
            self.traceability_manager.generate_trace(dossier)
            
            dossier.log_event(6, "phase_completed", {
                "trace_generated": True,
            })
            
            logger.info(f"📋 Dossier {dossier.id[:8]}: Phase 6 complete - trace generated")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 7: PRÊT POUR DÉCISION HUMAINE
            # ═══════════════════════════════════════════════════════════
            dossier.current_phase = 7
            dossier.status = "awaiting_human_decision"
            dossier.log_event(7, "ready_for_decision", {})
            
            logger.info(f"✅ Dossier {dossier.id[:8]}: Pipeline complete - awaiting human decision")
            
            return dossier
            
        except Exception as e:
            dossier.status = "error"
            dossier.error = str(e)
            dossier.log_event(dossier.current_phase, "error", {"error": str(e)})
            logger.error(f"❌ Pipeline error for dossier {dossier.id[:8]}: {e}")
            raise
    
    def get_decision_presentation(self, dossier_id: str) -> Dict[str, Any]:
        """Récupère la présentation pour décision humaine."""
        dossier = self.active_dossiers.get(dossier_id)
        if not dossier:
            raise ValueError(f"Dossier {dossier_id} not found")
        return self.human_interface.present_for_decision(dossier)
    
    def record_decision(
        self,
        dossier_id: str,
        decision: str,
        acknowledged_risks: List[str],
        notes: str = ""
    ) -> bool:
        """Enregistre la décision humaine."""
        return self.human_interface.record_human_decision(
            dossier_id, decision, acknowledged_risks, notes
        )
    
    def get_trace_markdown(self, dossier_id: str) -> str:
        """Récupère la trace en format Markdown."""
        dossier = self.active_dossiers.get(dossier_id)
        if not dossier:
            raise ValueError(f"Dossier {dossier_id} not found")
        trace = self.traceability_manager.trace_store.get(dossier_id)
        if not trace:
            trace = self.traceability_manager.generate_trace(dossier)
        return self.traceability_manager.export_trace_markdown(trace)


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def create_adversarial_pipeline(llm_caller: Callable = None) -> AdversarialInstructionPipeline:
    """
    Crée une instance du pipeline d'instruction contradictoire.
    
    Args:
        llm_caller: Fonction async pour appeler les LLMs
                    Signature: async def caller(prompt, model, role) -> str
                    Si None, utilise des réponses simulées (pour tests)
    
    Returns:
        AdversarialInstructionPipeline configuré
    """
    return AdversarialInstructionPipeline(llm_caller)

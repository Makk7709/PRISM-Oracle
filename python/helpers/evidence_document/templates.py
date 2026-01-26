"""
Evidence Document Templates — Sans marques commerciales.

Templates disponibles:
- standard: Document professionnel polyvalent
- consulting_premium: Rapport stratégique haut de gamme
- legal_formal: Document juridique formel
- scientific_academic: Publication scientifique
- patent_ip: Rédaction de brevet
- financial_audit: Rapport financier/audit
- executive_brief: Note de synthèse direction
- medical_clinical: Rapport médical
- technical_doc: Documentation technique
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Template:
    """Configuration d'un template PDF."""
    
    # Identité
    name: str
    display_name: str
    description: str
    
    # Couleurs (hex)
    primary_color: str = "#1a365d"
    secondary_color: str = "#2c5282"
    accent_color: str = "#3182ce"
    text_color: str = "#2d3748"
    light_bg: str = "#f7fafc"
    header_bg: str = "#2c5282"
    
    # Typographie
    title_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    code_font: str = "Courier"
    
    # Tailles (pt)
    title_size: int = 24
    h1_size: int = 18
    h2_size: int = 14
    h3_size: int = 12
    h4_size: int = 11
    body_size: int = 10
    
    # Marges (cm)
    left_margin: float = 2.0
    right_margin: float = 2.0
    top_margin: float = 2.5
    bottom_margin: float = 2.5
    
    # Header/Footer
    show_header: bool = True
    show_footer: bool = True
    show_page_numbers: bool = True
    header_text: str = ""
    footer_text: str = ""
    
    # Confidentialité
    confidential_labels: Dict[str, str] = field(default_factory=lambda: {
        "public": "",
        "internal": "USAGE INTERNE",
        "confidential": "CONFIDENTIEL",
        "strictly_confidential": "STRICTEMENT CONFIDENTIEL",
        "secret": "SECRET"
    })
    
    # Structure suggérée
    suggested_sections: List[str] = field(default_factory=list)
    
    # Options avancées
    cover_page_style: str = "standard"  # standard, minimal, elaborate
    toc_depth: int = 2  # Niveaux dans la table des matières


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES DEFINITIONS (sans marques)
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, Template] = {
    
    # ─────────────────────────────────────────────────────────────────────────────
    # STANDARD — Document professionnel polyvalent
    # ─────────────────────────────────────────────────────────────────────────────
    "standard": Template(
        name="standard",
        display_name="Document Standard",
        description="Format professionnel polyvalent pour usage général",
        
        primary_color="#1a365d",
        secondary_color="#2c5282",
        accent_color="#3182ce",
        text_color="#2d3748",
        light_bg="#f7fafc",
        header_bg="#2c5282",
        
        suggested_sections=[]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # CONSULTING_PREMIUM — Rapport stratégique haut de gamme
    # ─────────────────────────────────────────────────────────────────────────────
    "consulting_premium": Template(
        name="consulting_premium",
        display_name="Rapport Stratégique Premium",
        description="Format cabinet de conseil stratégique haut de gamme",
        
        # Palette professionnelle
        primary_color="#003B5C",
        secondary_color="#00629B",
        accent_color="#0091DA",
        text_color="#1D1D1D",
        light_bg="#F5F7FA",
        header_bg="#003B5C",
        
        # Typographie soignée
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=28,
        h1_size=20,
        h2_size=16,
        h3_size=13,
        body_size=11,
        
        # Marges généreuses
        left_margin=2.5,
        right_margin=2.5,
        top_margin=3.0,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        
        cover_page_style="elaborate",
        toc_depth=3,
        
        suggested_sections=[
            "Executive Summary",
            "Situation Analysis",
            "Key Findings",
            "Strategic Options",
            "Recommendation",
            "Implementation Roadmap",
            "Risks & Mitigations",
            "Appendix"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # LEGAL_FORMAL — Document juridique
    # ─────────────────────────────────────────────────────────────────────────────
    "legal_formal": Template(
        name="legal_formal",
        display_name="Document Juridique Formel",
        description="Format juridique pour tribunaux, greffes, contrats",
        
        # Couleurs formelles
        primary_color="#1A1A2E",
        secondary_color="#2D2D44",
        accent_color="#4A4A6A",
        text_color="#000000",
        light_bg="#FAFAFA",
        header_bg="#1A1A2E",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=16,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=11,
        
        # Marges standards juridiques
        left_margin=2.5,
        right_margin=2.5,
        top_margin=3.5,
        bottom_margin=3.0,
        
        show_header=True,
        show_footer=True,
        footer_text="Page {page} sur {total}",
        
        cover_page_style="minimal",
        
        suggested_sections=[
            "INTITULÉ DE L'ACTE",
            "PARTIES",
            "EXPOSÉ DES FAITS",
            "DISCUSSION EN DROIT",
            "PAR CES MOTIFS",
            "DISPOSITIF",
            "PIÈCES ANNEXÉES"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # SCIENTIFIC_ACADEMIC — Publication scientifique
    # ─────────────────────────────────────────────────────────────────────────────
    "scientific_academic": Template(
        name="scientific_academic",
        display_name="Publication Scientifique",
        description="Format académique pour recherche et publications",
        
        primary_color="#2C3E50",
        secondary_color="#34495E",
        accent_color="#3498DB",
        text_color="#2C3E50",
        light_bg="#F8F9FA",
        header_bg="#2C3E50",
        
        title_size=20,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=10,
        
        # Marges académiques
        left_margin=2.0,
        right_margin=2.0,
        top_margin=2.5,
        bottom_margin=2.5,
        
        show_header=False,
        show_footer=True,
        
        cover_page_style="minimal",
        
        suggested_sections=[
            "Abstract",
            "Introduction",
            "Materials & Methods",
            "Results",
            "Discussion",
            "Conclusion",
            "Acknowledgments",
            "References",
            "Supplementary Data"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # PATENT_IP — Brevet / Propriété intellectuelle
    # ─────────────────────────────────────────────────────────────────────────────
    "patent_ip": Template(
        name="patent_ip",
        display_name="Brevet / Propriété Intellectuelle",
        description="Format conforme aux normes de dépôt de brevets",
        
        primary_color="#1B4332",
        secondary_color="#2D6A4F",
        accent_color="#40916C",
        text_color="#000000",
        light_bg="#F0F4F0",
        header_bg="#1B4332",
        
        title_size=14,
        h1_size=12,
        h2_size=11,
        h3_size=10,
        body_size=10,
        
        # Marge gauche large pour numérotation
        left_margin=3.0,
        right_margin=2.0,
        top_margin=3.0,
        bottom_margin=2.5,
        
        show_header=True,
        header_text="DEMANDE DE BREVET",
        
        cover_page_style="standard",
        
        suggested_sections=[
            "TITRE DE L'INVENTION",
            "DOMAINE TECHNIQUE",
            "ÉTAT DE LA TECHNIQUE ANTÉRIEURE",
            "EXPOSÉ DE L'INVENTION",
            "PROBLÈME TECHNIQUE",
            "SOLUTION TECHNIQUE",
            "AVANTAGES",
            "DESCRIPTION DÉTAILLÉE",
            "MODE DE RÉALISATION PRÉFÉRÉ",
            "REVENDICATIONS",
            "ABRÉGÉ",
            "FIGURES"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # FINANCIAL_AUDIT — Rapport financier
    # ─────────────────────────────────────────────────────────────────────────────
    "financial_audit": Template(
        name="financial_audit",
        display_name="Rapport Financier / Audit",
        description="Format pour rapports financiers et missions d'audit",
        
        primary_color="#1E3A5F",
        secondary_color="#2E5077",
        accent_color="#4A7C59",
        text_color="#1A1A1A",
        light_bg="#F5F5F5",
        header_bg="#1E3A5F",
        
        title_size=22,
        h1_size=16,
        h2_size=13,
        h3_size=11,
        body_size=10,
        
        show_header=True,
        
        cover_page_style="elaborate",
        toc_depth=2,
        
        suggested_sections=[
            "Synthèse Exécutive",
            "Points Clés",
            "Analyse des États Financiers",
            "Compte de Résultat",
            "Bilan",
            "Flux de Trésorerie",
            "Ratios Financiers",
            "Analyse des Écarts",
            "Recommandations",
            "Annexes"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # EXECUTIVE_BRIEF — Note de synthèse
    # ─────────────────────────────────────────────────────────────────────────────
    "executive_brief": Template(
        name="executive_brief",
        display_name="Note de Synthèse Executive",
        description="Format concis pour décideurs et direction",
        
        primary_color="#0D1B2A",
        secondary_color="#1B263B",
        accent_color="#415A77",
        text_color="#1D1D1D",
        light_bg="#F8F9FA",
        header_bg="#0D1B2A",
        
        title_size=24,
        h1_size=16,
        h2_size=13,
        h3_size=11,
        body_size=11,
        
        left_margin=2.5,
        right_margin=2.5,
        
        show_header=True,
        header_text="NOTE EXECUTIVE",
        
        cover_page_style="minimal",
        
        suggested_sections=[
            "Objet",
            "Recommandation",
            "Contexte",
            "Analyse",
            "Options",
            "Décision Requise",
            "Prochaines Étapes"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # MEDICAL_CLINICAL — Rapport médical
    # ─────────────────────────────────────────────────────────────────────────────
    "medical_clinical": Template(
        name="medical_clinical",
        display_name="Rapport Médical / Clinique",
        description="Format pour rapports médicaux et cliniques",
        
        primary_color="#0077B6",
        secondary_color="#0096C7",
        accent_color="#00B4D8",
        text_color="#023E8A",
        light_bg="#CAF0F8",
        header_bg="#0077B6",
        
        title_size=18,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=10,
        
        top_margin=3.0,
        
        show_header=True,
        header_text="DOCUMENT MÉDICAL",
        footer_text="Secret médical - Art. L.1110-4 CSP",
        
        confidential_labels={
            "public": "",
            "internal": "",
            "confidential": "CONFIDENTIEL - SECRET MÉDICAL",
            "strictly_confidential": "CONFIDENTIEL - SECRET MÉDICAL",
            "secret": "CONFIDENTIEL - SECRET MÉDICAL"
        },
        
        cover_page_style="standard",
        
        suggested_sections=[
            "Identification Patient",
            "Motif de Consultation",
            "Antécédents",
            "Examen Clinique",
            "Examens Complémentaires",
            "Diagnostic",
            "Traitement",
            "Évolution",
            "Conclusion"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # TECHNICAL_DOC — Documentation technique
    # ─────────────────────────────────────────────────────────────────────────────
    "technical_doc": Template(
        name="technical_doc",
        display_name="Documentation Technique",
        description="Format pour documentation technique et API",
        
        primary_color="#374151",
        secondary_color="#4B5563",
        accent_color="#6366F1",
        text_color="#1F2937",
        light_bg="#F3F4F6",
        header_bg="#374151",
        
        code_font="Courier",
        
        title_size=20,
        h1_size=16,
        h2_size=14,
        h3_size=12,
        body_size=10,
        
        show_header=True,
        header_text="DOCUMENTATION TECHNIQUE",
        
        cover_page_style="minimal",
        toc_depth=3,
        
        suggested_sections=[
            "Overview",
            "Architecture",
            "Requirements",
            "Installation",
            "Configuration",
            "API Reference",
            "Examples",
            "Troubleshooting",
            "Changelog"
        ]
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DETECTION WITH WORD BOUNDARIES AND WEIGHTING
# ═══════════════════════════════════════════════════════════════════════════════

import re
from dataclasses import dataclass


@dataclass
class Keyword:
    """Keyword with weight for template detection."""
    word: str
    weight: int = 1
    use_boundary: bool = True  # Use \b word boundaries


# Keywords avec pondération et word boundaries
TEMPLATE_KEYWORDS: Dict[str, List[Keyword]] = {
    "consulting_premium": [
        # High weight - very specific
        Keyword("rapport stratégique", weight=5),
        Keyword("cabinet conseil", weight=5),
        Keyword("recommandation stratégique", weight=5),
        Keyword("due diligence", weight=4),
        Keyword("m&a", weight=4, use_boundary=False),  # M&A is special
        Keyword("business case", weight=4),
        # Medium weight
        Keyword("stratégie", weight=3),
        Keyword("stratégique", weight=3),
        Keyword("strategic", weight=3),
        Keyword("consulting", weight=3),
        Keyword("acquisition", weight=2),
        Keyword("fusion", weight=2),
        Keyword("transformation", weight=2),
        Keyword("restructuration", weight=2),
        # Low weight
        Keyword("conseil", weight=1),
        Keyword("strategy", weight=1),
    ],
    "legal_formal": [
        # High weight - very specific legal terms
        Keyword("assignation", weight=5),
        Keyword("greffe", weight=5),
        Keyword("tribunal", weight=4),
        Keyword("plaidoirie", weight=4),
        Keyword("conclusions", weight=4),
        Keyword("jugement", weight=3),
        Keyword("contentieux", weight=3),
        # Medium weight
        Keyword("juridique", weight=3),
        Keyword("avocat", weight=3),
        Keyword("litige", weight=2),
        Keyword("contrat", weight=2),
        Keyword("cession", weight=2),
        Keyword("statuts", weight=2),
        # Low weight
        Keyword("droit", weight=1),
        Keyword("legal", weight=1),
        Keyword("loi", weight=1),
    ],
    "scientific_academic": [
        # High weight
        Keyword("publication scientifique", weight=5),
        Keyword("peer review", weight=5),
        Keyword("abstract", weight=4),
        Keyword("methodology", weight=4),
        Keyword("méthodologie", weight=4),
        # Medium weight
        Keyword("scientifique", weight=3),
        Keyword("académique", weight=3),
        Keyword("research", weight=3),
        Keyword("recherche", weight=3),
        Keyword("hypothesis", weight=2),
        Keyword("experiment", weight=2),
        # Low weight  
        Keyword("étude", weight=1),
        Keyword("paper", weight=1),
    ],
    "patent_ip": [
        # High weight - very specific
        Keyword("revendication", weight=5),
        Keyword("brevet", weight=5),
        Keyword("patent", weight=5),
        Keyword("art antérieur", weight=4),
        Keyword("prior art", weight=4),
        Keyword("propriété intellectuelle", weight=4),
        # Medium weight
        Keyword("invention", weight=3),
        Keyword("déposant", weight=3),
        Keyword("dépôt", weight=2),
        # Low weight - "ip" is too generic without boundary
        Keyword("intellectual property", weight=2),
    ],
    "financial_audit": [
        # High weight
        Keyword("commissaire aux comptes", weight=5),
        Keyword("expert comptable", weight=5),
        Keyword("audit", weight=4),
        Keyword("dcf", weight=4, use_boundary=False),  # DCF acronym
        Keyword("compte résultat", weight=4),
        # Medium weight
        Keyword("financier", weight=3),
        Keyword("financière", weight=3),
        Keyword("comptable", weight=3),
        Keyword("bilan", weight=3),
        Keyword("valorisation", weight=3),
        Keyword("cash flow", weight=2),
        Keyword("trésorerie", weight=2),
        # Low weight
        Keyword("ratio", weight=1),
        Keyword("p&l", weight=2, use_boundary=False),
    ],
    "executive_brief": [
        # High weight
        Keyword("note de synthèse", weight=5),
        Keyword("executive summary", weight=5),
        Keyword("note executive", weight=5),
        Keyword("executive brief", weight=4),
        # Medium weight
        Keyword("synthèse", weight=3),
        Keyword("direction", weight=3),
        Keyword("board", weight=2),
        Keyword("décision", weight=2),
        # Low weight
        Keyword("brief", weight=1),
        Keyword("note", weight=1),
    ],
    "medical_clinical": [
        # High weight
        Keyword("diagnostic", weight=4),
        Keyword("clinique", weight=4),
        Keyword("patient", weight=4),
        Keyword("ordonnance", weight=4),
        Keyword("prescription", weight=4),
        # Medium weight
        Keyword("médical", weight=3),
        Keyword("traitement", weight=3),
        Keyword("pathologie", weight=3),
        Keyword("consultation", weight=2),
        Keyword("examen", weight=2),
        # Low weight
        Keyword("hôpital", weight=1),
        Keyword("hospital", weight=1),
    ],
    "technical_doc": [
        # High weight
        Keyword("documentation technique", weight=5),
        Keyword("spécification technique", weight=5),
        Keyword("api", weight=4, use_boundary=False),  # API acronym
        Keyword("sdk", weight=4, use_boundary=False),  # SDK acronym
        # Medium weight
        Keyword("architecture", weight=3),
        Keyword("développement", weight=3),
        Keyword("readme", weight=3),
        Keyword("technique", weight=2),
        # Low weight
        Keyword("système", weight=1),
        Keyword("code", weight=1),
    ]
}


def detect_template(user_request: str) -> str:
    """
    Détecte le template approprié avec pondération et word boundaries.
    
    Args:
        user_request: Texte de la demande
        
    Returns:
        Nom du template (default: "standard")
    """
    request_lower = user_request.lower()
    
    scores: Dict[str, float] = {}
    
    for template_name, keywords in TEMPLATE_KEYWORDS.items():
        score = 0.0
        
        for kw in keywords:
            if kw.use_boundary:
                # Use word boundary regex
                pattern = r'\b' + re.escape(kw.word) + r'\b'
                if re.search(pattern, request_lower):
                    score += kw.weight
            else:
                # Simple substring match
                if kw.word in request_lower:
                    score += kw.weight
        
        if score > 0:
            scores[template_name] = score
    
    if scores:
        # Return highest scoring template
        return max(scores.keys(), key=lambda k: scores[k])
    
    return "standard"


def get_template(name: str) -> Template:
    """Récupère un template par nom."""
    return TEMPLATES.get(name, TEMPLATES["standard"])


def list_templates() -> List[Dict]:
    """Liste tous les templates disponibles."""
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "suggested_sections": t.suggested_sections
        }
        for t in TEMPLATES.values()
    ]

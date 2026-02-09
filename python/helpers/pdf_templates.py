"""
Professional PDF Templates System — KOREV Evidence

Templates disponibles:
- consulting_premium: Rapport stratégique premium KOREV Evidence
- legal_formal: Document juridique style greffe/tribunal
- scientific_academic: Rapport scientifique/académique
- patent_ip: Rédaction de brevet style INPI/EPO
- financial_audit: Rapport financier/audit
- executive_brief: Note de synthèse executive
- medical_clinical: Rapport médical/clinique
- technical_doc: Documentation technique

Chaque template définit:
- Styles (fonts, couleurs, espacements)
- Structure (sections attendues)
- Header/Footer spécifiques
- Logo/Branding
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, gray
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import cm, mm


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DATA CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PDFTemplate:
    """Configuration pour un template PDF."""
    name: str
    display_name: str
    description: str
    
    # Colors
    primary_color: str = "#1a365d"
    secondary_color: str = "#2c5282"
    accent_color: str = "#3182ce"
    text_color: str = "#2d3748"
    light_bg: str = "#f7fafc"
    header_bg: str = "#2c5282"
    
    # Typography
    title_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    code_font: str = "Courier"
    
    # Sizes
    title_size: int = 24
    h1_size: int = 18
    h2_size: int = 14
    h3_size: int = 12
    body_size: int = 10
    
    # Margins (cm)
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
    
    # Branding
    confidential_notice: str = ""
    watermark: str = ""
    
    # Structure hints (for agent guidance)
    suggested_sections: List[str] = field(default_factory=list)
    
    # Custom styles override
    custom_styles: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, PDFTemplate] = {
    
    # ─────────────────────────────────────────────────────────────────────────────
    # CONSULTING PREMIUM - KOREV Evidence Strategic Report
    # ─────────────────────────────────────────────────────────────────────────────
    "consulting_premium": PDFTemplate(
        name="consulting_premium",
        display_name="KOREV Evidence Premium",
        description="Rapport stratégique premium - KOREV Evidence",
        
        # PRISM Design System
        primary_color="#0D1117",      # PRISM dark
        secondary_color="#4A7CFF",    # PRISM accent
        accent_color="#4A7CFF",       # PRISM accent
        text_color="#1A1D23",         # PRISM text primary
        light_bg="#F0F4FF",           # PRISM accent bg
        header_bg="#0D1117",          # PRISM dark
        
        # Clean, professional typography
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=28,
        h1_size=20,
        h2_size=16,
        h3_size=13,
        body_size=11,
        
        # Generous margins
        left_margin=2.5,
        right_margin=2.5,
        top_margin=3.0,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="CONFIDENTIEL",
        footer_text="Document stratégique",
        confidential_notice="STRICTLY CONFIDENTIAL",
        
        suggested_sections=[
            "Executive Summary",
            "Situation Analysis",
            "Key Findings (MECE)",
            "Strategic Options",
            "Recommendation",
            "Implementation Roadmap",
            "Risks & Mitigations",
            "Appendix"
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────────
    # LEGAL - Tribunal/Greffe Style
    # ─────────────────────────────────────────────────────────────────────────────
    "legal": PDFTemplate(
        name="legal",
        display_name="Document Juridique - Greffe/Tribunal",
        description="Format juridique formel - style tribunal de commerce",
        
        # Formal, conservative colors
        primary_color="#1A1A2E",      # Dark navy
        secondary_color="#2D2D44",
        accent_color="#4A4A6A",
        text_color="#000000",         # Pure black for legal docs
        light_bg="#FAFAFA",
        header_bg="#1A1A2E",
        
        # Serif-like formal appearance (using available fonts)
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=16,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=11,
        
        # Standard legal margins
        left_margin=2.5,
        right_margin=2.5,
        top_margin=3.5,
        bottom_margin=3.0,
        
        show_header=True,
        show_footer=True,
        header_text="",
        footer_text="Page {page} sur {total}",
        
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
    # SCIENTIFIC - Academic/Research Paper
    # ─────────────────────────────────────────────────────────────────────────────
    "scientific": PDFTemplate(
        name="scientific",
        display_name="Rapport Scientifique/Académique",
        description="Format publication scientifique - style Nature/Science",
        
        # Clean, academic colors
        primary_color="#2C3E50",
        secondary_color="#34495E",
        accent_color="#3498DB",
        text_color="#2C3E50",
        light_bg="#F8F9FA",
        header_bg="#2C3E50",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=20,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=10,
        
        # Narrow margins for more content
        left_margin=2.0,
        right_margin=2.0,
        top_margin=2.5,
        bottom_margin=2.5,
        
        show_header=False,
        show_footer=True,
        footer_text="",
        
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
    # PATENT - INPI/EPO Style
    # ─────────────────────────────────────────────────────────────────────────────
    "patent": PDFTemplate(
        name="patent",
        display_name="Brevet - Style INPI/EPO",
        description="Rédaction de brevet conforme aux normes INPI/EPO",
        
        # Formal patent colors
        primary_color="#1B4332",       # Dark green (patent office)
        secondary_color="#2D6A4F",
        accent_color="#40916C",
        text_color="#000000",
        light_bg="#F0F4F0",
        header_bg="#1B4332",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=14,
        h1_size=12,
        h2_size=11,
        h3_size=10,
        body_size=10,
        
        # Standard patent margins with numbering space
        left_margin=3.0,
        right_margin=2.0,
        top_margin=3.0,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="DEMANDE DE BREVET",
        footer_text="",
        
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
    # FINANCIAL - Audit/Financial Report
    # ─────────────────────────────────────────────────────────────────────────────
    "financial": PDFTemplate(
        name="financial",
        display_name="Rapport Financier/Audit",
        description="Format rapport financier professionnel - KOREV Evidence",
        
        # Professional finance colors
        primary_color="#1E3A5F",       # Navy blue
        secondary_color="#2E5077",
        accent_color="#4A7C59",        # Green for positive
        text_color="#1A1A1A",
        light_bg="#F5F5F5",
        header_bg="#1E3A5F",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=22,
        h1_size=16,
        h2_size=13,
        h3_size=11,
        body_size=10,
        
        left_margin=2.0,
        right_margin=2.0,
        top_margin=2.5,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="CONFIDENTIEL - USAGE INTERNE",
        footer_text="",
        
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
    # EXECUTIVE - Executive Brief
    # ─────────────────────────────────────────────────────────────────────────────
    "executive": PDFTemplate(
        name="executive",
        display_name="Note de Synthèse Executive",
        description="Format note de synthèse concise pour dirigeants",
        
        # Clean executive colors
        primary_color="#0D1B2A",
        secondary_color="#1B263B",
        accent_color="#415A77",
        text_color="#1D1D1D",
        light_bg="#F8F9FA",
        header_bg="#0D1B2A",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=24,
        h1_size=16,
        h2_size=13,
        h3_size=11,
        body_size=11,
        
        left_margin=2.5,
        right_margin=2.5,
        top_margin=2.5,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="NOTE EXECUTIVE",
        footer_text="",
        
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
    # MEDICAL - Clinical/Medical Report
    # ─────────────────────────────────────────────────────────────────────────────
    "medical": PDFTemplate(
        name="medical",
        display_name="Rapport Médical/Clinique",
        description="Format rapport médical - style hospitalier",
        
        # Medical professional colors
        primary_color="#0077B6",        # Medical blue
        secondary_color="#0096C7",
        accent_color="#00B4D8",
        text_color="#023E8A",
        light_bg="#CAF0F8",
        header_bg="#0077B6",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        title_size=18,
        h1_size=14,
        h2_size=12,
        h3_size=11,
        body_size=10,
        
        left_margin=2.0,
        right_margin=2.0,
        top_margin=3.0,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="DOCUMENT MÉDICAL CONFIDENTIEL",
        footer_text="Secret médical - Art. L.1110-4 CSP",
        confidential_notice="CONFIDENTIEL - SECRET MÉDICAL",
        
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
    # TECHNICAL - Technical Documentation
    # ─────────────────────────────────────────────────────────────────────────────
    "technical": PDFTemplate(
        name="technical",
        display_name="Documentation Technique",
        description="Format documentation technique - style RFC/IEEE",
        
        # Technical neutral colors
        primary_color="#374151",
        secondary_color="#4B5563",
        accent_color="#6366F1",        # Indigo for tech
        text_color="#1F2937",
        light_bg="#F3F4F6",
        header_bg="#374151",
        
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        code_font="Courier",
        title_size=20,
        h1_size=16,
        h2_size=14,
        h3_size=12,
        body_size=10,
        
        left_margin=2.0,
        right_margin=2.0,
        top_margin=2.5,
        bottom_margin=2.5,
        
        show_header=True,
        show_footer=True,
        header_text="DOCUMENTATION TECHNIQUE",
        footer_text="",
        
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
    
    # ─────────────────────────────────────────────────────────────────────────────
    # DEFAULT - Standard Professional
    # ─────────────────────────────────────────────────────────────────────────────
    "default": PDFTemplate(
        name="default",
        display_name="Document KOREV Evidence",
        description="Format professionnel KOREV Evidence — Charte PRISM",
        
        # PRISM Design System colors
        primary_color="#1A1D23",      # Text primary
        secondary_color="#4A7CFF",    # PRISM accent
        accent_color="#4A7CFF",       # PRISM accent
        text_color="#4A5568",         # Text secondary
        light_bg="#F0F4FF",           # Accent background
        header_bg="#0D1117",          # PRISM dark
        
        suggested_sections=[]
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Keywords for automatic template detection
TEMPLATE_KEYWORDS = {
    "consulting_premium": [
        "consulting", "cabinet conseil", "stratégie", "stratégique",
        "strategic", "premium", "mece", "issue tree", "deck", "slide",
        "recommandation stratégique", "business case", "due diligence"
    ],
    "legal_formal": [
        "juridique", "legal", "tribunal", "greffe", "avocat", "lawyer",
        "assignation", "conclusions", "plaidoirie", "jugement", "arrêt",
        "contrat", "cession", "statuts", "procès", "litige", "contentieux",
        "droit", "loi", "code civil", "code commerce"
    ],
    "scientific_academic": [
        "scientifique", "scientific", "research", "recherche", "paper",
        "publication", "académique", "academic", "study", "étude",
        "methodology", "méthodologie", "peer review", "nature", "science",
        "experiment", "hypothesis", "abstract"
    ],
    "patent_ip": [
        "brevet", "patent", "inpi", "epo", "wipo", "invention",
        "revendication", "claim", "prior art", "art antérieur",
        "propriété intellectuelle", "intellectual property"
    ],
    "financial_audit": [
        "financier", "financial", "audit", "comptable", "accounting",
        "bilan", "balance", "compte résultat", "p&l", "income statement",
        "cash flow", "trésorerie", "ratio", "dcf", "valorisation",
        "commissaire aux comptes", "expert comptable"
    ],
    "executive_brief": [
        "executive", "synthèse", "summary", "brief", "note",
        "direction", "board", "comité", "decision", "décision",
        "ceo", "cfo", "dg", "directeur"
    ],
    "medical_clinical": [
        "médical", "medical", "clinique", "clinical", "patient",
        "diagnostic", "traitement", "treatment", "ordonnance",
        "prescription", "consultation", "examen", "pathologie",
        "syndrome", "hôpital", "hospital"
    ],
    "technical_doc": [
        "technique", "technical", "documentation technique", "api",
        "architecture", "system", "système", "développement",
        "development", "spec", "spécification", "rfc", "readme"
    ]
}


def detect_template(user_request: str) -> str:
    """
    Detect which template to use based on user's request.
    
    Args:
        user_request: The user's prompt/request text
        
    Returns:
        Template name (e.g., "consulting_premium", "legal_formal", etc.)
    """
    request_lower = user_request.lower()
    
    # Score each template based on keyword matches
    scores = {}
    for template_name, keywords in TEMPLATE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in request_lower)
        if score > 0:
            scores[template_name] = score
    
    # Return highest scoring template, or default
    if scores:
        return max(scores.keys(), key=lambda k: scores[k])
    return "default"


def get_template(name: str) -> PDFTemplate:
    """Get a template by name."""
    return TEMPLATES.get(name, TEMPLATES["default"])


def list_templates() -> List[Dict]:
    """List all available templates for display."""
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "sections": t.suggested_sections
        }
        for t in TEMPLATES.values()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE PROMPT FOR AGENT
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATE_SELECTION_PROMPT = """
## Templates de Documents Disponibles — KOREV Evidence

Tu peux créer des documents professionnels selon différents standards :

| Template | Utilisation | Mots-clés |
|----------|-------------|-----------|
| `consulting_premium` | Rapport stratégique premium | stratégie, consulting, MECE, recommandation |
| `legal_formal` | Document juridique formel | juridique, tribunal, greffe, contrat, avocat |
| `scientific_academic` | Publication scientifique | recherche, étude, méthodologie, abstract |
| `patent_ip` | Brevet INPI/EPO | brevet, invention, revendication, IP |
| `financial_audit` | Rapport financier/audit | financier, bilan, audit, DCF, valorisation |
| `executive_brief` | Note de synthèse | executive, synthèse, direction, décision |
| `medical_clinical` | Rapport médical | médical, clinique, diagnostic, patient |
| `technical_doc` | Documentation technique | technique, API, architecture, système |

### Usage

Ajoute le paramètre `template` à l'outil `file_writer` :

```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "rapport.pdf",
        "template": "consulting_premium",
        "title": "Analyse Stratégique",
        "content": "## Executive Summary\\n..."
    }
}
```

### Détection Automatique

Si l'utilisateur mentionne un style (ex: "dossier juridique", "rapport stratégique"),
détecte automatiquement le template approprié.
"""

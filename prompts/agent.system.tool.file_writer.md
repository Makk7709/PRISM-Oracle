## file_writer
Create professional files (PDF, CSV, Excel, text) with template support.

**USE THIS TOOL** when you need to:
- Generate a PDF report with professional formatting
- Create documents in specific styles (McKinsey, juridique, scientifique, brevet...)
- Create a CSV file with data
- Create an Excel spreadsheet
- Write any text file

---

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `filename` | ✅ | Output filename (without path) |
| `content` | ✅ | The Markdown content to write |
| `title` | ❌ | Document title (for PDF) |
| `template` | ❌ | PDF template name (see below) |
| `format` | ❌ | "pdf", "csv", "excel", "txt" (auto-detected) |

**Output:** Files are saved to `tmp/generated/` with timestamp.

---

## 🎨 TEMPLATES PDF DISPONIBLES

**IMPORTANT**: Choisis le template selon la demande utilisateur !

| Template | Utilisation | Mots-clés utilisateur |
|----------|-------------|----------------------|
| `mckinsey` | Rapport stratégique premium | "McKinsey", "consulting", "stratégie", "MECE", "deck" |
| `legal` | Document juridique formel | "juridique", "tribunal", "greffe", "avocat", "contrat" |
| `scientific` | Publication académique | "scientifique", "recherche", "étude", "paper" |
| `patent` | Brevet INPI/EPO | "brevet", "patent", "INPI", "invention" |
| `financial` | Rapport financier/audit | "financier", "audit", "bilan", "DCF" |
| `executive` | Note de synthèse | "executive", "synthèse", "direction", "brief" |
| `medical` | Rapport médical | "médical", "clinique", "diagnostic", "patient" |
| `technical` | Documentation technique | "technique", "API", "architecture", "doc" |

### Sections suggérées par template

**McKinsey**: Executive Summary → Situation Analysis → Key Findings (MECE) → Strategic Options → Recommendation → Implementation → Risks

**Legal**: INTITULÉ → PARTIES → EXPOSÉ DES FAITS → DISCUSSION EN DROIT → PAR CES MOTIFS → DISPOSITIF

**Scientific**: Abstract → Introduction → Methods → Results → Discussion → Conclusion → References

**Patent**: TITRE → DOMAINE TECHNIQUE → ART ANTÉRIEUR → PROBLÈME → SOLUTION → AVANTAGES → REVENDICATIONS

---

## Exemples

### Rapport McKinsey (stratégie)
```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "strategie_acquisition.pdf",
        "template": "mckinsey",
        "title": "Strategic Assessment — Acquisition Target Alpha",
        "content": "## Executive Summary\n\n> **Recommendation**: Proceed with acquisition at €50M valuation\n\n**Key insight**: Target presents 3x revenue synergy potential\n\n---\n\n## Situation Analysis\n\n### Market Position\n\n| Metric | Target | Industry Avg |\n|--------|--------|-------------|\n| Market Share | 12% | 8% |\n| Growth Rate | 25% | 15% |\n| EBITDA Margin | 18% | 12% |\n\n### MECE Decomposition\n\n**Branch 1: Synergies**\n- Cost synergies: **€5M/year**\n- Revenue synergies: **€3M/year**\n\n**Branch 2: Risks**\n- Integration complexity: Medium\n- Regulatory approval: Low risk\n\n---\n\n## Recommendation\n\n1. Proceed to due diligence phase\n2. Target closing: Q2 2026\n3. Integration PMO to be established\n\n---\n\n*Strictly Confidential*"
    }
}
```

### Document Juridique (greffe/tribunal)
```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "conclusions_appel.pdf",
        "template": "legal",
        "title": "CONCLUSIONS D'APPEL",
        "content": "## DEVANT LA COUR D'APPEL DE PARIS\n\n---\n\n## PARTIES\n\n**APPELANT:**\nSociété ALPHA SAS\nRCS Paris 123 456 789\nReprésentée par Me Dupont, avocat au barreau de Paris\n\n**INTIMÉ:**\nSociété BETA SARL\nRCS Lyon 987 654 321\n\n---\n\n## EXPOSÉ DES FAITS\n\nPar jugement du 15 janvier 2025, le Tribunal de Commerce de Paris a...\n\n---\n\n## DISCUSSION EN DROIT\n\n### Sur la recevabilité de l'appel\n\nConformément à l'article 538 du Code de procédure civile...\n\n### Sur le fond\n\nIl résulte des pièces versées aux débats que...\n\n---\n\n## PAR CES MOTIFS\n\nIl est demandé à la Cour de:\n\n1. Déclarer l'appel recevable et bien fondé\n2. Infirmer le jugement entrepris\n3. Condamner l'intimé aux dépens"
    }
}
```

### Brevet INPI
```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "demande_brevet.pdf",
        "template": "patent",
        "title": "DEMANDE DE BREVET D'INVENTION",
        "content": "## TITRE DE L'INVENTION\n\nDispositif et procédé d'analyse automatisée de documents juridiques\n\n---\n\n## DOMAINE TECHNIQUE\n\nLa présente invention concerne le domaine de l'intelligence artificielle appliquée à l'analyse documentaire, et plus particulièrement un système de traitement automatique de documents juridiques.\n\n---\n\n## ÉTAT DE LA TECHNIQUE ANTÉRIEURE\n\nLes systèmes existants présentent les limitations suivantes:\n- Temps de traitement élevé\n- Faible précision sur documents complexes\n- Absence de structuration sémantique\n\n---\n\n## PROBLÈME TECHNIQUE\n\nLe problème technique résolu par l'invention est de fournir un système capable de...\n\n---\n\n## SOLUTION TECHNIQUE\n\nL'invention propose un dispositif comprenant:\n\n1. Un module d'extraction OCR amélioré\n2. Un réseau de neurones spécialisé\n3. Un système de classification multi-niveaux\n\n---\n\n## REVENDICATIONS\n\n1. Dispositif d'analyse documentaire caractérisé en ce qu'il comprend...\n2. Procédé selon la revendication 1, caractérisé en ce que..."
    }
}
```

---

## Content format

**CSV/Excel:**
- First line = headers
- Following lines = data rows
- Use commas or semicolons as separators

**PDF (Full Markdown):**
- `# H1`, `## H2`, `### H3` — Headers
- `**bold**`, `*italic*` — Formatting
- `- item` — Bullet lists
- `1. item` — Numbered lists
- `| A | B |` — Tables
- ` ```code``` ` — Code blocks
- `> quote` — Blockquotes
- `---` — Horizontal rules

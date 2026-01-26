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
| `content` | ✅ | **LE CONTENU COMPLET** en Markdown |
| `title` | ❌ | Document title (for PDF) |
| `template` | ❌ | PDF template name (see below) |
| `format` | ❌ | "pdf", "csv", "excel", "txt" (auto-detected) |

**Output:** Files are saved to `tmp/generated/` with timestamp.

---

## ⚠️ RÈGLE CRITIQUE — CONTENU COMPLET

**OBLIGATOIRE:** Le paramètre `content` DOIT contenir **L'INTÉGRALITÉ** du document.

❌ **NE PAS FAIRE:**
- Résumer le contenu
- Mettre "voir ci-dessus"
- Tronquer l'analyse
- Référencer d'autres messages

✅ **FAIRE:**
- Inclure TOUTES les sections
- Inclure TOUS les détails de l'analyse
- Inclure TOUTES les données et tableaux
- Reproduire l'intégralité de ce qui doit apparaître dans le PDF

**Le PDF doit être un document autonome et complet.**

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

### Rapport McKinsey (stratégie) — EXEMPLE COMPLET

**IMPORTANT:** Remarquez que `content` contient TOUT le rapport, pas un résumé !

```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "strategie_acquisition.pdf",
        "template": "mckinsey",
        "title": "Strategic Assessment — Acquisition Target Alpha",
        "content": "## Executive Summary\n\n> **Recommendation**: Proceed with acquisition at €50M valuation\n\n**Key insight**: Target presents 3x revenue synergy potential with minimal integration risk.\n\n### Key Findings\n\n1. **Market position strong** — 12% share vs 8% industry average\n2. **Growth trajectory excellent** — 25% YoY vs 15% market\n3. **Margins superior** — 18% EBITDA vs 12% peers\n\n---\n\n## Situation Analysis\n\n### 1. Market Position\n\n| Metric | Target | Industry Avg | Delta |\n|--------|--------|-------------|-------|\n| Market Share | 12% | 8% | +4pp |\n| Growth Rate | 25% | 15% | +10pp |\n| EBITDA Margin | 18% | 12% | +6pp |\n| Customer NPS | 72 | 45 | +27 |\n\n### 2. MECE Decomposition\n\n#### Branch 1: Value Creation Levers\n\n**Cost Synergies (€5M/year)**\n- Procurement consolidation: €2M\n- IT systems integration: €1.5M\n- Back-office optimization: €1.5M\n\n**Revenue Synergies (€3M/year)**\n- Cross-selling to customer base: €2M\n- Geographic expansion: €1M\n\n#### Branch 2: Risk Assessment\n\n| Risk Category | Probability | Impact | Mitigation |\n|--------------|-------------|--------|------------|\n| Integration complexity | Medium | High | Dedicated PMO, 18-month timeline |\n| Key talent retention | Medium | Medium | Retention packages, clear career paths |\n| Regulatory approval | Low | High | Pre-filing engagement |\n| Customer churn | Low | Medium | Communication plan, SLA guarantees |\n\n---\n\n## Financial Analysis\n\n### Valuation\n\n- **Enterprise Value**: €50M\n- **EV/EBITDA**: 8.5x (vs peer median 10x)\n- **EV/Revenue**: 2.1x (vs peer median 2.5x)\n\n### Synergy-Adjusted Returns\n\n- **Base case IRR**: 22%\n- **Upside case IRR**: 28%\n- **Downside case IRR**: 15%\n\n---\n\n## Recommendation\n\n### Proceed with Acquisition\n\n**Rationale:**\n1. Strategic fit with core business\n2. Attractive valuation (15-20% discount to peers)\n3. Clear synergy roadmap\n4. Manageable integration risk\n\n### Next Steps\n\n1. **Week 1-2**: Launch confirmatory due diligence\n2. **Week 3-4**: Finalize purchase agreement\n3. **Week 5-6**: Regulatory filings\n4. **Q2 2026**: Target closing\n\n---\n\n## Appendix\n\n### A. Detailed Financial Projections\n\n[5-year P&L model details...]\n\n### B. Integration Timeline\n\n[Gantt chart details...]\n\n---\n\n*Strictly Confidential — For Internal Use Only*"
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

# KOREV Evidence - Medical Agent Demo

## Agent Profile: `medical`

### Description
Agent spécialisé MSL-level pour recherche biomédicale evidence-based avec:
- Multi-source cross-validation (PubMed, ClinicalTrials, OpenFDA)
- GRADE assessment automatique
- Signal detection pharmacovigilance (PRR, ROR, IC)
- Competitive intelligence pipeline

---

## Démonstration des Capacités

### 1. Signal Detection FAERS

**Query**: "Analyze cardiac safety signals for GLP-1 agonists"

```python
from faers_signal_detection import FAERSSignalDetector

detector = FAERSSignalDetector()
signal = detector.detect_signal('semaglutide', 'myocardial infarction')
```

**Output**:
```
## FAERS Signal Detection Report

### Signal Assessment
- **Signal Strength**: VERY_STRONG
- **Case Count**: 25

### Disproportionality Metrics
| Metric | Value | 95% CI | Threshold | Met? |
|--------|-------|--------|-----------|------|
| PRR | 24.41 | 15.17 - 39.30 | ≥2.0 (CI) | ✓ |
| ROR | 25.00 | 15.41 - 40.57 | ≥2.0 (CI) | ✓ |
| IC | 4.05 | IC025: 3.66 | IC025 ≥0 | ✓ |

### Recommendation
URGENT: Immediate case review and regulatory consultation required.
```

---

### 2. Clinical Trials Competitive Landscape

**Query**: "Competitive landscape for KRAS G12C inhibitors in NSCLC"

```bash
biomcp trial search -c "non-small cell lung cancer" -i "KRAS G12C" -s open --json
```

**Output** (Live from ClinicalTrials.gov):
- 15+ active trials
- Adagrasib (KRYSTAL-21), Sotorasib, IBI351, D-1553
- Phase 2-3 trials with enrollment 50-600 patients
- Key readouts expected 2026-2028

---

### 3. Evidence Synthesis

**Query**: "Efficacy of JAK inhibitors vs biologics in rheumatoid arthritis"

```python
from evidence_synthesis import MedicalEvidenceSynthesizer

synthesizer = MedicalEvidenceSynthesizer()
result = synthesizer.synthesize(
    query="JAK inhibitors vs biologics in RA",
    keywords=["JAK inhibitor", "tofacitinib", "baricitinib"],
    disease="rheumatoid arthritis"
)
```

**Output**:
```
## Evidence Synthesis Report

### GRADE Quality: MODERATE
Based on 40+ sources analyzed.

### Evidence Table
| Source | Type | Level | Finding |
|--------|------|-------|---------|
| PMID 12345 | pubmed | 1b | Head-to-head RCT... |
| NCT04134728 | clinicaltrials | 1b | Phase 3 GSK trial... |
...

### Limitations
- Search limited to English language sources
- Publication bias may affect results
```

---

### 4. Literature Search (via BioMCP)

**Query**: "Latest research on GLP-1 cardiovascular outcomes"

```bash
biomcp article search -k "GLP-1" -d "cardiovascular" --json
```

**Output** (Live from PubMed/Europe PMC):
- Recent meta-analyses and RCTs
- PMID/DOI citations
- Authors and publication dates

---

## Use Cases Industriels

### Medical Affairs
- Veille concurrentielle avec sources traçables
- Réponses aux questions médicales (MIRs)
- Support KOL/MSL avec evidence mapping

### Clinical Development
- Analyse endpoints Phase 3 par indication
- Benchmark design études vs concurrence
- Identification sites/investigateurs

### Drug Safety / Pharmacovigilance
- Signal detection FAERS automatisé
- Disproportionalité analysis (PRR/ROR/IC)
- Label comparison et gap analysis

### Regulatory Affairs
- Suivi FDA guidance drafts
- EMA EPAR summaries
- ICH compliance tracking

---

## Configuration

### Profil Agent
```bash
export EVIDENCE_AGENT_PROFILE=medical
```

### MCP Config
```bash
export EVIDENCE_MCP_CONFIG=mcp_config_medical.json
```

### Variables Environnement
```bash
NCBI_API_KEY=xxx          # PubMed rate limits
OPENFDA_API_KEY=xxx       # OpenFDA rate limits (optional)
TAVILY_API_KEY=xxx        # Web search
```

---

## Différenciateur vs ChatGPT/Claude Vanilla

| Feature | ChatGPT | Claude | **KOREV Evidence Medical** |
|---------|---------|--------|---------------------------|
| Sources traçables | ❌ | ❌ | ✅ PMID, NCT, FDA |
| GRADE assessment | ❌ | ❌ | ✅ Automatique |
| Signal detection PV | ❌ | ❌ | ✅ PRR/ROR/IC |
| ClinicalTrials live | ❌ | ❌ | ✅ API directe |
| **Consensus PRISM** | ❌ | ❌ | ✅ **Multi-LLM validation intégrée** |
| Fail-closed | ❌ | ❌ | ✅ Refuse si preuves insuffisantes |
| Audit-ready output | ❌ | ❌ | ✅ Structured reports |

---

## PRISM Consensus Integration

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDICAL AGENT OUTPUT                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PRISM INTEGRATION LAYER                        │
│  ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐  │
│  │ Evidence Check   │ │ Multi-LLM Vote   │ │ Quorum Check    │  │
│  │ (sources valid?) │ │ (2/3 approval)   │ │ (consensus?)    │  │
│  └──────────────────┘ └──────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌────────────────┐              ┌────────────────┐
     │   VALIDATED    │              │  FAIL-CLOSED   │
     │ (avec stamp)   │              │ (pas d'output) │
     └────────────────┘              └────────────────┘
```

### Statuts PRISM

| Status | Signification | Action |
|--------|---------------|--------|
| `VALIDATED` | Consensus atteint, output approuvé | Retourne output + stamp |
| `FAILED_CONSENSUS` | Quorum non atteint (2/3 requis) | Retourne message fail-closed |
| `INSUFFICIENT_EVIDENCE` | Pas assez de sources | Refuse d'émettre |
| `BLOCKED` | Policy violation | Bloqué |

### Exemple Output Validé

```markdown
## Evidence Synthesis Report
...contenu médical...

---
✅ **PRISM Validated** | ID: `a1b2c3d4` | Sources: 15
```

### Exemple Fail-Closed

```markdown
## ⚠️ Validation PRISM Non Atteinte

Cette analyse médicale n'a pas pu être validée par le consensus PRISM.

**Raison**: Consensus multi-LLM non atteint (quorum 2/3 requis)

**Actions recommandées**:
1. Reformuler la question avec plus de spécificité
2. Fournir des sources additionnelles
3. Consulter un professionnel de santé qualifié
```

---

## Compliance Notes

- Toute affirmation médicale requiert citation source
- Disclaimers automatiques dans les réponses
- **PRISM OBLIGATOIRE** sur domaine MEDICAL (intégré dans tous les outils)
- Fail-closed si consensus non atteint ou preuves insuffisantes
- Zéro conseil médical individuel (population-level only)

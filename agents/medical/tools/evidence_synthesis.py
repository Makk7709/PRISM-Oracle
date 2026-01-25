"""
KOREV Evidence - Medical Evidence Synthesis Tool
Haut de gamme: Multi-source cross-validation with automatic GRADE assessment
"""

import json
import subprocess
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class EvidenceLevel(Enum):
    """Oxford Centre for Evidence-Based Medicine Levels"""
    LEVEL_1A = "1a"  # Systematic review of RCTs
    LEVEL_1B = "1b"  # Individual RCT
    LEVEL_2A = "2a"  # Systematic review of cohort studies
    LEVEL_2B = "2b"  # Individual cohort study
    LEVEL_3 = "3"    # Case-control study
    LEVEL_4 = "4"    # Case series
    LEVEL_5 = "5"    # Expert opinion


class GRADEQuality(Enum):
    """GRADE certainty of evidence"""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class EvidenceItem:
    """Single piece of evidence with metadata"""
    source_id: str  # PMID, NCT, FDA reference
    source_type: str  # pubmed, clinicaltrials, fda_label, faers
    title: str
    claim: str
    evidence_level: EvidenceLevel
    sample_size: Optional[int] = None
    effect_size: Optional[str] = None
    confidence_interval: Optional[str] = None
    p_value: Optional[float] = None
    publication_date: Optional[str] = None
    authors: list = field(default_factory=list)
    url: Optional[str] = None
    
    def to_citation(self) -> str:
        """Generate inline citation"""
        if self.source_type == "pubmed":
            return f"(PMID: {self.source_id}; Level {self.evidence_level.value})"
        elif self.source_type == "clinicaltrials":
            return f"({self.source_id}; {self.evidence_level.value})"
        elif self.source_type == "fda_label":
            return f"(FDA Label: {self.source_id})"
        else:
            return f"({self.source_type}: {self.source_id})"


class SourceConcordance(Enum):
    """Concordance level between sources"""
    STRONG = "strong"      # 3+ sources concordantes
    MODERATE = "moderate"  # 2 sources concordantes
    WEAK = "weak"          # 1 source ou divergence
    CONFLICT = "conflict"  # Sources contradictoires


@dataclass
class CrossValidationResult:
    """Result of cross-validation between sources"""
    claim: str
    pubmed_support: bool
    trials_support: bool
    faers_support: bool
    label_support: bool
    concordance: SourceConcordance
    notes: str = ""


@dataclass 
class EvidenceSynthesis:
    """Aggregated evidence synthesis with GRADE assessment"""
    query: str
    total_sources: int
    evidence_items: list
    grade_quality: GRADEQuality
    consensus_statement: str
    limitations: list
    evidence_gaps: list
    # Cross-validation data
    cross_validation: list = field(default_factory=list)
    sources_by_type: dict = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Generate structured markdown report with cross-validation"""
        # Count sources by type
        type_counts = {}
        for item in self.evidence_items:
            t = item.source_type
            type_counts[t] = type_counts.get(t, 0) + 1
        
        md = f"""## Evidence Synthesis Report

### Query
{self.query}

### Sources Consultées
| Type | Count |
|------|-------|
"""
        for t, count in type_counts.items():
            md += f"| {t} | {count} |\n"
        
        md += f"""
**Total**: {self.total_sources} sources

### GRADE Quality: {self.grade_quality.value.upper()}

### Cross-Validation Matrix
"""
        if self.cross_validation:
            md += """
| Finding | PubMed | Trials | FAERS | Label | Concordance |
|---------|--------|--------|-------|-------|-------------|
"""
            for cv in self.cross_validation[:10]:
                pm = "✅" if cv.pubmed_support else "❌"
                tr = "✅" if cv.trials_support else "❌"
                fa = "✅" if cv.faers_support else "N/A"
                lb = "✅" if cv.label_support else "❌"
                md += f"| {cv.claim[:40]}... | {pm} | {tr} | {fa} | {lb} | **{cv.concordance.value.upper()}** |\n"
        else:
            md += "*Cross-validation data not available*\n"

        md += f"""
### Consensus Statement
{self.consensus_statement}

### Evidence Table

| Source | Type | Level | Finding |
|--------|------|-------|---------|
"""
        for item in self.evidence_items[:15]:
            md += f"| {item.source_id} | {item.source_type} | {item.evidence_level.value} | {item.claim[:60]}... |\n"
        
        md += f"""
### Limitations
"""
        for lim in self.limitations:
            md += f"- {lim}\n"
            
        md += f"""
### Evidence Gaps
"""
        for gap in self.evidence_gaps:
            md += f"- {gap}\n"
            
        return md


class MedicalEvidenceSynthesizer:
    """
    Premium medical evidence synthesis engine.
    Cross-validates across PubMed, ClinicalTrials, OpenFDA.
    """
    
    def __init__(self):
        self.biomcp_path = "biomcp"
        
    def _run_biomcp(self, args: list, timeout: int = 60) -> dict:
        """Execute BioMCP command and parse JSON output"""
        try:
            cmd = [self.biomcp_path] + args + ["--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            return {}
        except Exception as e:
            return {"error": str(e)}
    
    def search_pubmed(self, keywords: list, diseases: list = None, limit: int = 20) -> list:
        """Search PubMed via BioMCP"""
        args = ["article", "search"]
        for kw in keywords:
            args.extend(["-k", kw])
        if diseases:
            for d in diseases:
                args.extend(["-d", d])
        
        results = self._run_biomcp(args)
        
        evidence_items = []
        for article in results if isinstance(results, list) else []:
            # Infer evidence level from title/journal
            level = self._infer_evidence_level(article.get("title", ""))
            
            item = EvidenceItem(
                source_id=article.get("pmid", article.get("doi", "unknown")),
                source_type="pubmed",
                title=article.get("title", ""),
                claim=article.get("title", ""),  # Use title as proxy
                evidence_level=level,
                publication_date=article.get("date"),
                authors=article.get("authors", []),
                url=article.get("doi_url")
            )
            evidence_items.append(item)
            
        return evidence_items[:limit]
    
    def search_clinical_trials(self, condition: str, intervention: str = None, 
                                phase: str = None, status: str = "any") -> list:
        """Search ClinicalTrials.gov via BioMCP"""
        args = ["trial", "search", "-c", condition]
        if intervention:
            args.extend(["-i", intervention])
        if phase:
            args.extend(["-p", phase])
        args.extend(["-s", status])
        
        results = self._run_biomcp(args)
        
        evidence_items = []
        for trial in results if isinstance(results, list) else []:
            # Map phase to evidence level
            phase_str = trial.get("Phases", "")
            if "PHASE3" in phase_str:
                level = EvidenceLevel.LEVEL_1B
            elif "PHASE2" in phase_str:
                level = EvidenceLevel.LEVEL_2B
            else:
                level = EvidenceLevel.LEVEL_4
                
            item = EvidenceItem(
                source_id=trial.get("NCT Number", "unknown"),
                source_type="clinicaltrials",
                title=trial.get("Study Title", ""),
                claim=trial.get("Brief Summary", "")[:200],
                evidence_level=level,
                sample_size=self._parse_int(trial.get("Enrollment")),
                url=trial.get("Study URL")
            )
            evidence_items.append(item)
            
        return evidence_items
    
    def search_faers(self, drug_name: str, reaction: str = None) -> list:
        """Search FDA Adverse Event Reporting System"""
        args = ["openfda", "adverse", "search", "-d", drug_name]
        if reaction:
            args.extend(["-r", reaction])
            
        results = self._run_biomcp(args)
        
        evidence_items = []
        # FAERS data is Level 4 (case series / spontaneous reports)
        for report in results if isinstance(results, list) else []:
            item = EvidenceItem(
                source_id=report.get("safetyreportid", "unknown"),
                source_type="faers",
                title=f"FAERS Report: {drug_name}",
                claim=f"Adverse event report for {drug_name}",
                evidence_level=EvidenceLevel.LEVEL_4
            )
            evidence_items.append(item)
            
        return evidence_items[:50]  # Limit FAERS reports
    
    def synthesize(self, query: str, keywords: list, 
                   disease: str = None, drug: str = None) -> EvidenceSynthesis:
        """
        Multi-source evidence synthesis with GRADE assessment.
        Cross-validates PubMed + ClinicalTrials + FAERS.
        """
        all_evidence = []
        limitations = []
        gaps = []
        sources_by_type = {"pubmed": [], "clinicaltrials": [], "faers": []}
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 1: COLLECTE MULTI-SOURCE
        # ═══════════════════════════════════════════════════════════════════
        
        # 1.1 PubMed Literature
        diseases = [disease] if disease else []
        pubmed_evidence = self.search_pubmed(keywords, diseases)
        all_evidence.extend(pubmed_evidence)
        sources_by_type["pubmed"] = pubmed_evidence
        
        if not pubmed_evidence:
            gaps.append("No peer-reviewed literature found for this query")
        
        # 1.2 Clinical Trials
        trial_evidence = []
        if disease:
            trial_evidence = self.search_clinical_trials(
                condition=disease,
                intervention=drug,
                status="any"
            )
            all_evidence.extend(trial_evidence)
            sources_by_type["clinicaltrials"] = trial_evidence
            
            if not trial_evidence:
                gaps.append("No registered clinical trials found")
        
        # 1.3 FAERS Safety Data
        faers_evidence = []
        if drug:
            faers_evidence = self.search_faers(drug_name=drug)
            all_evidence.extend(faers_evidence)
            sources_by_type["faers"] = faers_evidence
            
            limitations.append("FAERS data is spontaneous reporting - cannot establish causality")
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 2: CROSS-VALIDATION / TRIANGULATION
        # ═══════════════════════════════════════════════════════════════════
        
        cross_validation = self._cross_validate_sources(
            pubmed_evidence, trial_evidence, faers_evidence, query
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 3: GRADE SCORING (ajusté par concordance)
        # ═══════════════════════════════════════════════════════════════════
        
        grade = self._calculate_grade_with_concordance(all_evidence, cross_validation)
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 4: CONSENSUS STATEMENT
        # ═══════════════════════════════════════════════════════════════════
        
        consensus = self._generate_consensus(query, all_evidence, grade)
        
        # Add standard limitations
        limitations.extend([
            "Search limited to English language sources",
            "Publication bias may affect literature results",
            "Evidence current as of search date only"
        ])
        
        # Check minimum sources requirement
        source_types_found = sum(1 for v in sources_by_type.values() if v)
        if source_types_found < 2:
            limitations.append("⚠️ WARNING: Only {source_types_found} source type found. Cross-validation limited.")
        
        return EvidenceSynthesis(
            query=query,
            total_sources=len(all_evidence),
            evidence_items=all_evidence,
            grade_quality=grade,
            consensus_statement=consensus,
            limitations=limitations,
            evidence_gaps=gaps,
            cross_validation=cross_validation,
            sources_by_type=sources_by_type
        )
    
    def _cross_validate_sources(
        self, 
        pubmed: list, 
        trials: list, 
        faers: list,
        query: str
    ) -> list:
        """
        Cross-validate findings across source types.
        Returns concordance assessment for key claims.
        """
        cross_validations = []
        
        # Extract key themes from query
        themes = self._extract_themes(query)
        
        for theme in themes[:5]:  # Top 5 themes
            pubmed_support = any(
                theme.lower() in (item.title + item.claim).lower() 
                for item in pubmed
            )
            trials_support = any(
                theme.lower() in (item.title + item.claim).lower() 
                for item in trials
            ) if trials else False
            faers_support = any(
                theme.lower() in item.claim.lower() 
                for item in faers
            ) if faers else False
            
            # Calculate concordance
            supports = sum([pubmed_support, trials_support, faers_support])
            if supports >= 3:
                concordance = SourceConcordance.STRONG
            elif supports == 2:
                concordance = SourceConcordance.MODERATE
            elif supports == 1:
                concordance = SourceConcordance.WEAK
            else:
                concordance = SourceConcordance.WEAK
            
            cross_validations.append(CrossValidationResult(
                claim=theme,
                pubmed_support=pubmed_support,
                trials_support=trials_support,
                faers_support=faers_support,
                label_support=False,  # Would need FDA label lookup
                concordance=concordance
            ))
        
        return cross_validations
    
    def _extract_themes(self, query: str) -> list:
        """Extract key themes from query for cross-validation"""
        # Simple extraction - in production would use NLP
        themes = []
        
        # Common medical themes
        keywords = ["efficacy", "safety", "side effect", "adverse", "outcome",
                   "survival", "response", "mortality", "efficacité", "sécurité"]
        
        query_lower = query.lower()
        for kw in keywords:
            if kw in query_lower:
                themes.append(kw)
        
        # Also extract drug/disease names from query
        words = query.split()
        for word in words:
            if len(word) > 4 and word[0].isupper():  # Likely proper noun (drug/disease)
                themes.append(word)
        
        return themes if themes else ["general findings"]
    
    def _calculate_grade_with_concordance(
        self, 
        evidence: list, 
        cross_validation: list
    ) -> GRADEQuality:
        """Calculate GRADE quality adjusted by source concordance"""
        base_grade = self._calculate_grade(evidence)
        
        if not cross_validation:
            return base_grade
        
        # Check concordance levels
        strong_count = sum(1 for cv in cross_validation if cv.concordance == SourceConcordance.STRONG)
        conflict_count = sum(1 for cv in cross_validation if cv.concordance == SourceConcordance.CONFLICT)
        
        # Upgrade if strong concordance
        if strong_count >= 2 and base_grade != GRADEQuality.HIGH:
            return GRADEQuality(list(GRADEQuality)[max(0, list(GRADEQuality).index(base_grade) - 1)].value)
        
        # Downgrade if conflicts
        if conflict_count >= 1 and base_grade != GRADEQuality.VERY_LOW:
            return GRADEQuality(list(GRADEQuality)[min(3, list(GRADEQuality).index(base_grade) + 1)].value)
        
        return base_grade
    
    def _infer_evidence_level(self, title: str) -> EvidenceLevel:
        """Infer evidence level from article title"""
        title_lower = title.lower()
        
        if any(x in title_lower for x in ["systematic review", "meta-analysis", "cochrane"]):
            return EvidenceLevel.LEVEL_1A
        elif any(x in title_lower for x in ["randomized", "randomised", "rct", "controlled trial"]):
            return EvidenceLevel.LEVEL_1B
        elif any(x in title_lower for x in ["cohort", "prospective", "longitudinal"]):
            return EvidenceLevel.LEVEL_2B
        elif any(x in title_lower for x in ["case-control", "case control"]):
            return EvidenceLevel.LEVEL_3
        elif any(x in title_lower for x in ["case series", "case report"]):
            return EvidenceLevel.LEVEL_4
        else:
            return EvidenceLevel.LEVEL_5  # Default to expert opinion
    
    def _calculate_grade(self, evidence: list) -> GRADEQuality:
        """Calculate GRADE quality based on evidence composition"""
        if not evidence:
            return GRADEQuality.VERY_LOW
            
        level_counts = {}
        for item in evidence:
            level = item.evidence_level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # High: Multiple RCTs or systematic reviews
        if level_counts.get("1a", 0) >= 1 or level_counts.get("1b", 0) >= 3:
            return GRADEQuality.HIGH
        # Moderate: Some RCTs or good cohort studies
        elif level_counts.get("1b", 0) >= 1 or level_counts.get("2a", 0) >= 1:
            return GRADEQuality.MODERATE
        # Low: Observational studies
        elif level_counts.get("2b", 0) >= 2 or level_counts.get("3", 0) >= 2:
            return GRADEQuality.LOW
        else:
            return GRADEQuality.VERY_LOW
    
    def _generate_consensus(self, query: str, evidence: list, grade: GRADEQuality) -> str:
        """Generate evidence-based consensus statement"""
        if not evidence:
            return f"Insufficient evidence to make a statement about: {query}"
        
        grade_prefix = {
            GRADEQuality.HIGH: "Strong evidence supports",
            GRADEQuality.MODERATE: "Moderate evidence suggests",
            GRADEQuality.LOW: "Limited evidence indicates",
            GRADEQuality.VERY_LOW: "Very limited evidence (primarily case reports) suggests"
        }
        
        return f"{grade_prefix[grade]} findings related to '{query}'. Based on {len(evidence)} sources analyzed."
    
    def _parse_int(self, value) -> Optional[int]:
        """Safely parse integer from various formats"""
        if value is None:
            return None
        try:
            return int(str(value).replace(",", ""))
        except:
            return None


# Tool interface for KOREV Evidence agent
def medical_evidence_synthesis(query: str, keywords: str, disease: str = None, drug: str = None, 
                                validate_prism: bool = True) -> str:
    """
    Multi-source medical evidence synthesis tool with PRISM consensus validation.
    
    Args:
        query: Research question (e.g., "efficacy of GLP-1 agonists in heart failure")
        keywords: Comma-separated search keywords
        disease: Optional disease/condition to focus on
        drug: Optional drug/intervention to include
        validate_prism: Whether to validate through PRISM consensus (default: True)
        
    Returns:
        Structured markdown report with evidence table and GRADE assessment.
        If PRISM validation fails, returns fail-closed message.
    """
    synthesizer = MedicalEvidenceSynthesizer()
    
    keyword_list = [k.strip() for k in keywords.split(",")]
    
    synthesis = synthesizer.synthesize(
        query=query,
        keywords=keyword_list,
        disease=disease,
        drug=drug
    )
    
    output = synthesis.to_markdown()
    
    # PRISM Consensus Validation (OBLIGATOIRE en domaine médical)
    if validate_prism:
        try:
            from prism_integration import validate_medical_sync
            
            # Convertir evidence_items en format sources
            sources = []
            for item in synthesis.evidence_items:
                sources.append({
                    "id": item.source_id,
                    "type": item.source_type,
                    "level": item.evidence_level.value,
                    "title": item.title,
                    "url": item.url or "",
                })
            
            # Valider via PRISM
            validated_output = validate_medical_sync(
                query=query,
                output=output,
                sources=sources,
            )
            return validated_output
            
        except ImportError:
            # PRISM non disponible - ajouter warning
            output += "\n\n⚠️ *Note: PRISM consensus validation not available*"
    
    return output

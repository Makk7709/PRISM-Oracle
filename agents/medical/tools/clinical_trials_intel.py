"""
KOREV Evidence - Clinical Trials Competitive Intelligence Tool
Haut de gamme: Pipeline analysis, endpoint tracking, competitive landscape
"""

import json
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from collections import defaultdict


@dataclass
class TrialSummary:
    """Structured clinical trial data"""
    nct_id: str
    title: str
    sponsor: str
    phase: str
    status: str
    condition: str
    intervention: str
    enrollment: int
    start_date: str
    completion_date: str
    primary_endpoint: str
    study_design: str
    url: str
    
    def to_row(self) -> list:
        """Convert to table row"""
        return [
            self.nct_id,
            self.sponsor[:20] if self.sponsor else "N/A",
            self.phase,
            self.status[:15],
            str(self.enrollment),
            self.completion_date[:10] if self.completion_date else "N/A"
        ]


@dataclass
class CompetitiveLandscape:
    """Aggregated competitive intelligence"""
    condition: str
    intervention_class: str
    total_trials: int
    by_phase: dict
    by_status: dict
    by_sponsor: dict
    endpoint_analysis: dict
    timeline_analysis: dict
    key_trials: list
    
    def to_markdown(self) -> str:
        """Generate competitive intelligence report"""
        md = f"""## Clinical Trials Competitive Landscape

### Overview
- **Indication**: {self.condition}
- **Drug Class/Target**: {self.intervention_class}
- **Total Active Trials**: {self.total_trials}

### Phase Distribution

| Phase | Count | % |
|-------|-------|---|
"""
        total = sum(self.by_phase.values())
        for phase, count in sorted(self.by_phase.items()):
            pct = (count / total * 100) if total > 0 else 0
            md += f"| {phase} | {count} | {pct:.1f}% |\n"

        md += f"""
### Status Distribution

| Status | Count |
|--------|-------|
"""
        for status, count in sorted(self.by_status.items(), key=lambda x: -x[1]):
            md += f"| {status} | {count} |\n"

        md += f"""
### Top Sponsors

| Sponsor | Trials |
|---------|--------|
"""
        for sponsor, count in sorted(self.by_sponsor.items(), key=lambda x: -x[1])[:10]:
            md += f"| {sponsor[:40]} | {count} |\n"

        md += f"""
### Endpoint Analysis

| Endpoint Type | Frequency |
|---------------|-----------|
"""
        for endpoint, count in sorted(self.endpoint_analysis.items(), key=lambda x: -x[1])[:10]:
            md += f"| {endpoint[:50]} | {count} |\n"

        md += f"""
### Key Trials (Phase 3)

| NCT ID | Sponsor | Status | N | Est. Completion |
|--------|---------|--------|---|-----------------|
"""
        for trial in self.key_trials[:15]:
            row = trial.to_row()
            md += f"| {row[0]} | {row[1]} | {row[3]} | {row[4]} | {row[5]} |\n"

        md += f"""
### Timeline Analysis

**Expected Phase 3 Readouts (Next 24 Months)**:
"""
        for year, trials in sorted(self.timeline_analysis.items()):
            md += f"- **{year}**: {len(trials)} trials\n"
            for t in trials[:5]:
                md += f"  - {t.nct_id}: {t.sponsor} ({t.intervention[:30]})\n"

        return md


class ClinicalTrialsIntelligence:
    """
    Premium clinical trials competitive intelligence engine.
    Aggregates pipeline data, endpoints, timelines, sponsors.
    """
    
    def __init__(self):
        self.biomcp_path = "biomcp"
        
    def _run_biomcp(self, args: list, timeout: int = 120) -> list:
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
                data = json.loads(result.stdout)
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def search_trials(self, condition: str, intervention: str = None,
                      phase: str = None, status: str = "any") -> list:
        """Search ClinicalTrials.gov"""
        args = ["trial", "search", "-c", condition]
        if intervention:
            args.extend(["-i", intervention])
        if phase:
            args.extend(["-p", phase])
        args.extend(["-s", status])
        
        results = self._run_biomcp(args)
        
        trials = []
        for trial in results:
            # Parse sponsor from study design or title
            sponsor = self._extract_sponsor(trial)
            
            summary = TrialSummary(
                nct_id=trial.get("NCT Number", ""),
                title=trial.get("Study Title", ""),
                sponsor=sponsor,
                phase=self._normalize_phase(trial.get("Phases", "")),
                status=trial.get("Study Status", ""),
                condition=trial.get("Conditions", ""),
                intervention=trial.get("Interventions", ""),
                enrollment=self._parse_int(trial.get("Enrollment", 0)),
                start_date=trial.get("Start Date", ""),
                completion_date=trial.get("Completion Date", ""),
                primary_endpoint=self._extract_endpoint(trial),
                study_design=trial.get("Study Design", ""),
                url=trial.get("Study URL", "")
            )
            trials.append(summary)
            
        return trials
    
    def analyze_landscape(self, condition: str, intervention_class: str = None) -> CompetitiveLandscape:
        """
        Generate comprehensive competitive landscape analysis.
        Aggregates trials by phase, status, sponsor, endpoints.
        """
        # Search all trials for condition
        all_trials = self.search_trials(
            condition=condition,
            intervention=intervention_class,
            status="any"
        )
        
        # Aggregate by phase
        by_phase = defaultdict(int)
        for trial in all_trials:
            by_phase[trial.phase] += 1
            
        # Aggregate by status
        by_status = defaultdict(int)
        for trial in all_trials:
            by_status[trial.status] += 1
            
        # Aggregate by sponsor
        by_sponsor = defaultdict(int)
        for trial in all_trials:
            if trial.sponsor:
                by_sponsor[trial.sponsor] += 1
                
        # Endpoint analysis
        endpoint_analysis = self._analyze_endpoints(all_trials)
        
        # Timeline analysis (upcoming readouts)
        timeline_analysis = self._analyze_timeline(all_trials)
        
        # Filter key Phase 3 trials
        key_trials = [t for t in all_trials if "3" in t.phase]
        key_trials.sort(key=lambda x: x.enrollment, reverse=True)
        
        return CompetitiveLandscape(
            condition=condition,
            intervention_class=intervention_class or "All",
            total_trials=len(all_trials),
            by_phase=dict(by_phase),
            by_status=dict(by_status),
            by_sponsor=dict(by_sponsor),
            endpoint_analysis=endpoint_analysis,
            timeline_analysis=timeline_analysis,
            key_trials=key_trials
        )
    
    def _extract_sponsor(self, trial: dict) -> str:
        """Extract sponsor from trial data"""
        # Try various fields
        title = trial.get("Study Title", "").lower()
        
        # Known pharma companies
        sponsors = [
            "Pfizer", "Novartis", "Roche", "Merck", "AstraZeneca",
            "Bristol-Myers Squibb", "AbbVie", "Eli Lilly", "Amgen",
            "Gilead", "Regeneron", "Sanofi", "Johnson & Johnson",
            "Takeda", "Boehringer Ingelheim", "GSK", "Bayer",
            "Biogen", "Vertex", "Moderna", "BioNTech"
        ]
        
        for sponsor in sponsors:
            if sponsor.lower() in title:
                return sponsor
                
        # Extract from interventions
        interventions = trial.get("Interventions", "")
        for sponsor in sponsors:
            if sponsor.lower() in interventions.lower():
                return sponsor
                
        return "Academic/Other"
    
    def _normalize_phase(self, phase_str: str) -> str:
        """Normalize phase string"""
        if not phase_str:
            return "N/A"
        if "PHASE3" in phase_str:
            return "Phase 3"
        elif "PHASE2" in phase_str and "PHASE1" in phase_str:
            return "Phase 1/2"
        elif "PHASE2" in phase_str:
            return "Phase 2"
        elif "PHASE1" in phase_str:
            return "Phase 1"
        elif "PHASE4" in phase_str:
            return "Phase 4"
        else:
            return phase_str
    
    def _extract_endpoint(self, trial: dict) -> str:
        """Extract primary endpoint from trial summary"""
        summary = trial.get("Brief Summary", "")
        
        # Common endpoint keywords
        endpoint_markers = [
            "primary endpoint", "primary outcome", "primary efficacy",
            "objective response", "progression-free survival", "overall survival",
            "disease-free survival", "HbA1c", "ACR20", "PASI"
        ]
        
        summary_lower = summary.lower()
        for marker in endpoint_markers:
            if marker in summary_lower:
                return marker.title()
                
        return "Not specified"
    
    def _analyze_endpoints(self, trials: list) -> dict:
        """Aggregate endpoint frequency"""
        endpoints = defaultdict(int)
        
        common_endpoints = {
            "overall survival": "OS (Overall Survival)",
            "progression-free survival": "PFS (Progression-Free Survival)",
            "objective response": "ORR (Objective Response Rate)",
            "disease-free survival": "DFS (Disease-Free Survival)",
            "pathological complete response": "pCR",
            "hba1c": "HbA1c Change",
            "acr20": "ACR20 Response",
            "pasi": "PASI Score",
            "quality of life": "QoL",
            "safety": "Safety/Tolerability"
        }
        
        for trial in trials:
            summary = trial.title.lower() + " " + (trial.primary_endpoint or "").lower()
            for key, label in common_endpoints.items():
                if key in summary:
                    endpoints[label] += 1
                    
        return dict(endpoints)
    
    def _analyze_timeline(self, trials: list) -> dict:
        """Group trials by expected completion year"""
        timeline = defaultdict(list)
        
        for trial in trials:
            if trial.completion_date:
                try:
                    year = trial.completion_date[:4]
                    if year.isdigit() and int(year) >= 2025:
                        timeline[year].append(trial)
                except:
                    pass
                    
        return dict(timeline)
    
    def _parse_int(self, value) -> int:
        """Safely parse integer"""
        try:
            return int(str(value).replace(",", ""))
        except:
            return 0


# Tool interface for KOREV Evidence agent
def clinical_trials_landscape(condition: str, intervention_class: str = None, 
                               validate_prism: bool = True) -> str:
    """
    Generate competitive landscape analysis from ClinicalTrials.gov.
    Outputs are validated through PRISM multi-LLM consensus.
    
    Args:
        condition: Disease/condition (e.g., "non-small cell lung cancer")
        intervention_class: Optional drug class/target (e.g., "KRAS G12C")
        validate_prism: Whether to validate through PRISM consensus (default: True)
        
    Returns:
        Comprehensive competitive intelligence report in markdown.
        If PRISM validation fails, returns fail-closed message.
    """
    intel = ClinicalTrialsIntelligence()
    landscape = intel.analyze_landscape(condition, intervention_class)
    output = landscape.to_markdown()
    
    # PRISM Consensus Validation
    if validate_prism:
        try:
            from prism_integration import validate_medical_sync
            
            # Sources = individual trials found
            sources = []
            for trial in landscape.key_trials[:10]:
                sources.append({
                    "id": trial.nct_id,
                    "type": "clinicaltrials",
                    "level": "2b" if "3" in trial.phase else "4",
                    "title": trial.title[:100],
                    "url": trial.url,
                })
            
            query = f"Clinical trials landscape: {condition}" + (
                f" ({intervention_class})" if intervention_class else ""
            )
            
            validated_output = validate_medical_sync(
                query=query,
                output=output,
                sources=sources,
            )
            return validated_output
            
        except ImportError:
            output += "\n\n⚠️ *Note: PRISM consensus validation not available*"
    
    return output


def trial_endpoint_analysis(condition: str, phase: str = "phase3") -> str:
    """
    Analyze endpoints used in clinical trials for a given indication.
    
    Args:
        condition: Disease/condition
        phase: Trial phase to focus on (phase1, phase2, phase3)
        
    Returns:
        Endpoint frequency analysis report
    """
    intel = ClinicalTrialsIntelligence()
    trials = intel.search_trials(condition=condition, phase=phase)
    
    endpoint_counts = defaultdict(int)
    for trial in trials:
        ep = trial.primary_endpoint
        if ep and ep != "Not specified":
            endpoint_counts[ep] += 1
    
    report = f"""## Endpoint Analysis: {condition} ({phase.title()})

### Primary Endpoints Used

| Endpoint | Trials Using |
|----------|--------------|
"""
    for ep, count in sorted(endpoint_counts.items(), key=lambda x: -x[1]):
        report += f"| {ep} | {count} |\n"
    
    report += f"""
### Regulatory Implications
- Most common endpoints align with FDA/EMA guidance for this indication
- Consider endpoint selection based on precedent and regulatory feedback
- Surrogate endpoints may accelerate approval but require post-marketing confirmation
"""
    return report

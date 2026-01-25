"""
KOREV Evidence - Medical Agent Response Tool
Haut de gamme: Structured responses with evidence grading and citations
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class MedicalResponse:
    """Structured medical response with evidence grading"""
    question: str
    answer: str
    evidence_grade: str  # HIGH, MODERATE, LOW, VERY_LOW, INSUFFICIENT
    sources: list
    confidence: float  # 0.0 - 1.0
    limitations: list
    search_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    # Mandatory medical disclaimers
    DISCLAIMER = """
---
**Disclaimer**: This analysis is for informational purposes only and does not constitute medical advice. 
Clinical decisions should be made by qualified healthcare professionals. Evidence current as of {date}.
"""
    
    def to_markdown(self) -> str:
        """Generate formatted medical response"""
        # Evidence grade badge
        grade_badges = {
            "HIGH": "🟢 HIGH",
            "MODERATE": "🟡 MODERATE", 
            "LOW": "🟠 LOW",
            "VERY_LOW": "🔴 VERY LOW",
            "INSUFFICIENT": "⚫ INSUFFICIENT"
        }
        badge = grade_badges.get(self.evidence_grade, "⚫ UNKNOWN")
        
        md = f"""## Medical Intelligence Response

### Question
{self.question}

### Evidence Grade: {badge}
Confidence: {self.confidence:.0%}

### Answer
{self.answer}

### Sources ({len(self.sources)})

| # | Source | Type | Level |
|---|--------|------|-------|
"""
        for i, src in enumerate(self.sources[:20], 1):
            source_id = src.get("id", "N/A")
            source_type = src.get("type", "unknown")
            level = src.get("level", "N/A")
            md += f"| {i} | {source_id} | {source_type} | {level} |\n"

        if self.limitations:
            md += f"""
### Limitations
"""
            for lim in self.limitations:
                md += f"- {lim}\n"

        md += self.DISCLAIMER.format(date=self.search_date)
        
        return md


def medical_response(question: str, answer: str, evidence_grade: str,
                     sources: list = None, confidence: float = 0.5,
                     limitations: list = None, validate_prism: bool = True) -> str:
    """
    Generate a structured medical response with evidence grading.
    All outputs are validated through PRISM multi-LLM consensus.
    
    This tool should be called as the final step when answering medical questions.
    It ensures proper disclaimers, evidence attribution, and PRISM validation.
    
    Args:
        question: The original medical question
        answer: The evidence-based answer
        evidence_grade: One of HIGH, MODERATE, LOW, VERY_LOW, INSUFFICIENT
        sources: List of source dicts with id, type, level keys
        confidence: Confidence score (0.0 - 1.0)
        limitations: List of study/analysis limitations
        validate_prism: Whether to validate through PRISM consensus (default: True)
        
    Returns:
        Formatted markdown response with evidence grading and disclaimers.
        If PRISM validation fails, returns fail-closed message.
    """
    response = MedicalResponse(
        question=question,
        answer=answer,
        evidence_grade=evidence_grade.upper(),
        sources=sources or [],
        confidence=confidence,
        limitations=limitations or []
    )
    output = response.to_markdown()
    
    # PRISM Consensus Validation (OBLIGATOIRE pour réponses médicales)
    if validate_prism and sources:
        try:
            from prism_integration import validate_medical_sync
            
            validated_output = validate_medical_sync(
                query=question,
                output=output,
                sources=sources,
            )
            return validated_output
            
        except ImportError:
            output += "\n\n⚠️ *Note: PRISM consensus validation not available*"
    elif validate_prism and not sources:
        # Pas de sources = warning obligatoire
        output += "\n\n⚠️ **Warning**: No sources provided. PRISM validation skipped."
    
    return output


# Specialized response types

def literature_review_response(topic: str, findings: str, studies_analyzed: int,
                                meta_analyses: int, rcts: int, 
                                sources: list, gaps: list = None) -> str:
    """
    Generate structured literature review response.
    
    Args:
        topic: Review topic
        findings: Key findings narrative
        studies_analyzed: Total studies reviewed
        meta_analyses: Number of meta-analyses/systematic reviews
        rcts: Number of RCTs
        sources: List of source dicts
        gaps: Knowledge gaps identified
        
    Returns:
        Formatted literature review report
    """
    # Calculate evidence grade based on study types
    if meta_analyses >= 2 or rcts >= 5:
        grade = "HIGH"
        confidence = 0.85
    elif meta_analyses >= 1 or rcts >= 2:
        grade = "MODERATE"
        confidence = 0.70
    elif rcts >= 1 or studies_analyzed >= 5:
        grade = "LOW"
        confidence = 0.55
    else:
        grade = "VERY_LOW"
        confidence = 0.40
    
    answer = f"""**Literature Analysis Summary**

{findings}

**Study Composition:**
- Total studies analyzed: {studies_analyzed}
- Systematic reviews/meta-analyses: {meta_analyses}
- Randomized controlled trials: {rcts}
- Observational/other: {studies_analyzed - meta_analyses - rcts}
"""

    if gaps:
        answer += "\n**Knowledge Gaps:**\n"
        for gap in gaps:
            answer += f"- {gap}\n"
    
    limitations = [
        "Search limited to indexed databases (PubMed, Semantic Scholar)",
        "Publication bias may affect findings",
        "Non-English publications not included",
        "Grey literature not systematically searched"
    ]
    
    return medical_response(
        question=f"Literature review: {topic}",
        answer=answer,
        evidence_grade=grade,
        sources=sources,
        confidence=confidence,
        limitations=limitations
    )


def safety_analysis_response(drug: str, event: str, signal_detected: bool,
                              prr: float, cases: int, sources: list) -> str:
    """
    Generate structured drug safety analysis response.
    
    Args:
        drug: Drug name
        event: Adverse event
        signal_detected: Whether signal was detected
        prr: Proportional Reporting Ratio
        cases: Number of cases
        sources: List of source dicts
        
    Returns:
        Formatted safety analysis report
    """
    if signal_detected:
        if prr >= 4.0:
            grade = "HIGH"
            confidence = 0.80
            finding = f"**SIGNAL DETECTED**: Strong disproportionality observed (PRR={prr:.2f})"
        else:
            grade = "MODERATE"
            confidence = 0.65
            finding = f"**SIGNAL DETECTED**: Moderate disproportionality observed (PRR={prr:.2f})"
    else:
        grade = "LOW"
        confidence = 0.50
        finding = f"**NO SIGNAL**: No disproportionality detected (PRR={prr:.2f})"
    
    answer = f"""{finding}

**Drug-Event Analysis:**
- Drug: {drug}
- Adverse Event: {event}
- Cases in FAERS: {cases}
- PRR: {prr:.2f}

**Interpretation:**
{"This signal warrants further investigation including case review and potential label evaluation." if signal_detected else "Routine monitoring continues. No immediate action required."}
"""
    
    limitations = [
        "FAERS is spontaneous reporting - cannot establish causality",
        "Reporting rates vary by drug age and publicity",
        "Confounding by indication not controlled",
        "Incomplete data on concomitant medications"
    ]
    
    return medical_response(
        question=f"Safety analysis: {drug} and {event}",
        answer=answer,
        evidence_grade=grade,
        sources=sources,
        confidence=confidence,
        limitations=limitations
    )

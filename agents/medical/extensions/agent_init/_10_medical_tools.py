"""
KOREV Evidence - Medical Agent Initialization Extension
Registers premium medical tools with the agent runtime.
"""

import os
import sys

# Ensure agent tools directory is in path
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(AGENT_DIR, "tools")

if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def init_extension(agent):
    """
    Initialize medical agent extension.
    Called automatically when medical profile is loaded.
    """
    # Import medical tools
    try:
        from evidence_synthesis import medical_evidence_synthesis
        from faers_signal_detection import faers_signal_detection
        from clinical_trials_intel import clinical_trials_landscape, trial_endpoint_analysis
        from response import medical_response, literature_review_response, safety_analysis_response
        
        # Register tools with agent
        medical_tools = {
            "medical_evidence_synthesis": {
                "function": medical_evidence_synthesis,
                "description": "Multi-source medical evidence synthesis with GRADE assessment. Cross-validates PubMed, ClinicalTrials, OpenFDA.",
                "parameters": {
                    "query": "Research question (e.g., 'efficacy of GLP-1 agonists in heart failure')",
                    "keywords": "Comma-separated search keywords",
                    "disease": "Optional: Disease/condition to focus on",
                    "drug": "Optional: Drug/intervention to include"
                }
            },
            "faers_signal_detection": {
                "function": faers_signal_detection,
                "description": "Detect safety signals from FAERS using disproportionality analysis (PRR, ROR, IC).",
                "parameters": {
                    "drug_name": "Generic or brand name of drug",
                    "adverse_event": "MedDRA Preferred Term (e.g., 'myocardial infarction')"
                }
            },
            "clinical_trials_landscape": {
                "function": clinical_trials_landscape,
                "description": "Generate competitive landscape analysis from ClinicalTrials.gov.",
                "parameters": {
                    "condition": "Disease/condition (e.g., 'non-small cell lung cancer')",
                    "intervention_class": "Optional: Drug class/target (e.g., 'KRAS G12C')"
                }
            },
            "trial_endpoint_analysis": {
                "function": trial_endpoint_analysis,
                "description": "Analyze endpoints used in clinical trials for indication.",
                "parameters": {
                    "condition": "Disease/condition",
                    "phase": "Trial phase (phase1, phase2, phase3)"
                }
            },
            "medical_response": {
                "function": medical_response,
                "description": "Generate structured medical response with evidence grading and disclaimers.",
                "parameters": {
                    "question": "The original medical question",
                    "answer": "Evidence-based answer",
                    "evidence_grade": "HIGH, MODERATE, LOW, VERY_LOW, or INSUFFICIENT",
                    "sources": "List of source dicts with id, type, level",
                    "confidence": "Confidence score (0.0-1.0)",
                    "limitations": "List of limitations"
                }
            },
            "literature_review_response": {
                "function": literature_review_response,
                "description": "Generate structured literature review report.",
                "parameters": {
                    "topic": "Review topic",
                    "findings": "Key findings narrative",
                    "studies_analyzed": "Total studies",
                    "meta_analyses": "Number of meta-analyses",
                    "rcts": "Number of RCTs",
                    "sources": "Source list",
                    "gaps": "Knowledge gaps"
                }
            },
            "safety_analysis_response": {
                "function": safety_analysis_response,
                "description": "Generate drug safety analysis report.",
                "parameters": {
                    "drug": "Drug name",
                    "event": "Adverse event",
                    "signal_detected": "Boolean",
                    "prr": "PRR value",
                    "cases": "Case count",
                    "sources": "Source list"
                }
            }
        }
        
        # Register with agent if available
        if hasattr(agent, "register_tools"):
            agent.register_tools(medical_tools)
            print("[Medical Agent] Registered 7 premium medical tools")
        else:
            # Store for later access
            agent.medical_tools = medical_tools
            print("[Medical Agent] Medical tools stored (register_tools not available)")
            
    except ImportError as e:
        print(f"[Medical Agent] Warning: Could not import medical tools: {e}")
        

def get_medical_system_prompt_additions() -> str:
    """
    Additional system prompt content for medical agent.
    """
    return """
## Medical Agent Premium Tools

You have access to the following specialized medical tools:

### 1. medical_evidence_synthesis
Multi-source evidence synthesis with automatic GRADE assessment.
- Cross-validates PubMed, ClinicalTrials.gov, and OpenFDA
- Generates evidence tables with Oxford levels (1a-5)
- Calculates GRADE quality (HIGH/MODERATE/LOW/VERY_LOW)

### 2. faers_signal_detection
Pharmacovigilance signal detection using disproportionality analysis.
- Calculates PRR, ROR, IC (Information Component)
- Classifies signal strength (NO_SIGNAL to VERY_STRONG)
- Generates regulatory-ready safety reports

### 3. clinical_trials_landscape
Competitive intelligence from ClinicalTrials.gov.
- Aggregates by phase, status, sponsor
- Analyzes endpoints and timelines
- Identifies key competitor trials

### 4. trial_endpoint_analysis
Endpoint frequency analysis for indication.
- Maps endpoint usage across phases
- Identifies regulatory precedent
- Supports trial design decisions

### 5. medical_response / literature_review_response / safety_analysis_response
Structured response generators with:
- Automatic evidence grading
- Mandatory disclaimers
- Source citation formatting

## Usage Protocol

1. **Always cite sources** - Every medical claim needs PMID, NCT, or FDA reference
2. **State evidence level** - Use Oxford levels or GRADE quality
3. **Include disclaimers** - Use response tools to ensure compliance
4. **Flag uncertainties** - Explicitly state when evidence is lacking
5. **Never give medical advice** - Population-level analysis only
"""

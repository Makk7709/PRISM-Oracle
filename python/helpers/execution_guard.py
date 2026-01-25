"""
Execution Guard — Forces tool execution for actionable requests.

This module enforces the "operator, not commentator" principle by:
1. Detecting executable requests (action verbs)
2. Rejecting text-only responses when execution is required
3. Providing EXECUTION_REQUIRED feedback to force tool calls
"""

import re
from typing import Optional
from dataclasses import dataclass
from python.helpers.print_style import PrintStyle


@dataclass
class ExecutionGuardResult:
    """Result of execution guard check."""
    is_executable_request: bool
    has_tool_call: bool
    is_valid: bool
    rejection_message: Optional[str] = None
    detected_actions: list[str] = None
    
    def __post_init__(self):
        if self.detected_actions is None:
            self.detected_actions = []


# Action verb patterns that trigger TOOL_REQUIRED
# Organized by language (French + English)
ACTION_PATTERNS = {
    # French action verbs
    "fr": [
        r"\b(génère|genere|générer|generer)\b",
        r"\b(produis|produire|produit)\b",
        r"\b(classe|classer|classement)\b",
        r"\b(regroupe|regrouper|regroupement)\b",
        r"\b(crée|créer|cree|creer|création)\b",
        r"\b(exporte|exporter|exportation)\b",
        r"\b(transforme|transformer|transformation)\b",
        r"\b(analyse|analyser|analysis)\b",
        r"\b(structure|structurer|structuration)\b",
        r"\b(organise|organiser|organisation)\b",
        r"\b(traite|traiter|traitement)\b",
        r"\b(fusionne|fusionner|fusion)\b",
        r"\b(extrais|extraire|extraction)\b",
        r"\b(convertis|convertir|conversion)\b",
        r"\b(trie|trier|tri)\b",
        r"\b(renomme|renommer)\b",
        r"\b(copie|copier)\b",
        r"\b(déplace|déplacer|deplace|deplacer)\b",
        r"\b(supprime|supprimer)\b",
        r"\b(télécharge|télécharger|telecharge|telecharger)\b",
        r"\b(enregistre|enregistrer|sauvegarde|sauvegarder)\b",
        r"\b(compile|compiler)\b",
        r"\b(calcule|calculer|calcul)\b",
        r"\b(résume|résumer|resume|resumer)\b",
        r"\b(traduis|traduire|traduction)\b",
        r"\b(recherche|rechercher)\b",
        r"\b(liste|lister)\b",
        r"\b(affiche|afficher)\b",
        r"\b(ouvre|ouvrir)\b",
        r"\b(ferme|fermer)\b",
        r"\b(exécute|exécuter|execute|executer)\b",
        r"\b(lance|lancer)\b",
        r"\b(installe|installer)\b",
        r"\b(configure|configurer)\b",
        r"\b(mets à jour|mettre à jour|maj)\b",
        r"\bfais (un|une|le|la|les|du|des)\b",
    ],
    # English action verbs
    "en": [
        r"\b(generate|generates|generating)\b",
        r"\b(produce|produces|producing)\b",
        r"\b(classify|classifies|classifying|classification)\b",
        r"\b(group|groups|grouping)\b",
        r"\b(create|creates|creating|creation)\b",
        r"\b(export|exports|exporting)\b",
        r"\b(transform|transforms|transforming)\b",
        r"\b(analyze|analyzes|analyzing|analyse|analyses|analysing)\b",
        r"\b(structure|structures|structuring)\b",
        r"\b(organize|organizes|organizing|organise|organises|organising)\b",
        r"\b(process|processes|processing)\b",
        r"\b(merge|merges|merging)\b",
        r"\b(extract|extracts|extracting)\b",
        r"\b(convert|converts|converting)\b",
        r"\b(sort|sorts|sorting)\b",
        r"\b(rename|renames|renaming)\b",
        r"\b(copy|copies|copying)\b",
        r"\b(move|moves|moving)\b",
        r"\b(delete|deletes|deleting)\b",
        r"\b(download|downloads|downloading)\b",
        r"\b(save|saves|saving)\b",
        r"\b(compile|compiles|compiling)\b",
        r"\b(calculate|calculates|calculating)\b",
        r"\b(summarize|summarizes|summarizing|summarise)\b",
        r"\b(translate|translates|translating)\b",
        r"\b(search|searches|searching)\b",
        r"\b(list|lists|listing)\b",
        r"\b(show|shows|showing|display|displays)\b",
        r"\b(open|opens|opening)\b",
        r"\b(close|closes|closing)\b",
        r"\b(execute|executes|executing|run|runs|running)\b",
        r"\b(launch|launches|launching)\b",
        r"\b(install|installs|installing)\b",
        r"\b(configure|configures|configuring)\b",
        r"\b(update|updates|updating)\b",
        r"\bmake (a|an|the|me|this)\b",
        r"\bdo (a|an|the|this)\b",
    ],
    # File/document specific patterns
    "files": [
        r"\b(pdf|xlsx?|csv|json|xml|txt|docx?|image|photo|fichier|file|document)\b",
        r"\b(dossier|folder|directory|répertoire|repertoire)\b",
    ]
}

# Compile all patterns
COMPILED_PATTERNS = {}
for lang, patterns in ACTION_PATTERNS.items():
    COMPILED_PATTERNS[lang] = [re.compile(p, re.IGNORECASE) for p in patterns]


def detect_action_request(user_message: str) -> tuple[bool, list[str]]:
    """
    Detect if a user message contains action verbs requiring tool execution.
    
    Returns:
        tuple: (is_action_request: bool, detected_actions: list[str])
    """
    if not user_message:
        return False, []
    
    # Ensure user_message is a string
    if not isinstance(user_message, str):
        try:
            user_message = str(user_message)
        except Exception:
            return False, []
    
    detected_actions = []
    message_lower = user_message.lower()
    
    # Check all language patterns
    for lang, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            matches = pattern.findall(message_lower)
            if matches:
                detected_actions.extend(matches)
    
    # Deduplicate
    detected_actions = list(set(detected_actions))
    
    # Consider it an action request if we found action verbs
    # AND the message contains file-related terms OR is clearly imperative
    has_action_verbs = len(detected_actions) > 0
    has_file_context = any(p.search(message_lower) for p in COMPILED_PATTERNS.get("files", []))
    is_imperative = message_lower.strip().split()[0] if message_lower.strip() else ""
    
    # Action request if: action verbs + (file context OR starts with action verb)
    is_action_request = has_action_verbs and (has_file_context or len(detected_actions) >= 1)
    
    return is_action_request, detected_actions


def has_tool_call(agent_response: str) -> bool:
    """
    Check if agent response contains a valid tool call.
    
    Args:
        agent_response: The raw response from the agent
        
    Returns:
        bool: True if response contains a tool_name that isn't just 'response' with explanation
    """
    if not agent_response:
        return False
    
    # Look for tool_name in the response
    tool_name_match = re.search(r'"tool_name"\s*:\s*"([^"]+)"', agent_response)
    
    if not tool_name_match:
        return False
    
    tool_name = tool_name_match.group(1).lower()
    
    # 'response' tool requires validation
    if tool_name == "response":
        # REJECT MISSING_TOOL responses - agent should use code_execution instead!
        if "MISSING_TOOL:" in agent_response or "MISSING_TOOL" in agent_response:
            PrintStyle(font_color="yellow", bold=True).print(
                "[Execution Guard] REJECTED: MISSING_TOOL is not allowed. Use code_execution!"
            )
            return False  # Force agent to use code_execution
        
        # REJECT "Tool not found" leaks - NEVER expose internal tool errors to user
        if "Tool not found" in agent_response or "Available tools:" in agent_response:
            PrintStyle(font_color="yellow", bold=True).print(
                "[Execution Guard] REJECTED: Tool list leak detected. Use code_execution!"
            )
            return False  # Force agent to use code_execution
        
        # REJECT ANY tool-related leak messages
        leak_patterns = [
            "TOOL_UNAVAILABLE",
            "GRAPH_POLICY_REDIRECT",
            "graph tool",
            "chart tool",
            "plot tool",
            "[SYSTEM] Use code_execution",
            "tool is not available",
            "outil non disponible",
            "outil n'est pas disponible",
            "not available",
            "n'existe pas",
            "doesn't exist",
            "does not exist",
        ]
        response_lower = agent_response.lower()
        for pattern in leak_patterns:
            if pattern.lower() in response_lower:
                PrintStyle(font_color="yellow", bold=True).print(
                    f"[Execution Guard] REJECTED: Tool leak detected ({pattern}). Execute with code_execution!"
                )
                return False
        
        # Check if the response text is short (< 200 chars = acceptable brief response)
        text_match = re.search(r'"text"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', agent_response, re.DOTALL)
        if text_match:
            text_content = text_match.group(1)
            # Allow short responses after execution
            if len(text_content) < 200:
                return True
            # Long text response without execution = violation
            return False
        
        return False
    
    # Any other tool = valid execution
    return True


def check_execution_guard(
    user_message: str,
    agent_response: str,
    force_execution: bool = False
) -> ExecutionGuardResult:
    """
    Main guard function: checks if agent response complies with execution policy.
    
    Args:
        user_message: The original user request
        agent_response: The agent's response (raw JSON string)
        force_execution: If True, always require tool execution
        
    Returns:
        ExecutionGuardResult with validation status
    """
    is_executable, detected_actions = detect_action_request(user_message)
    has_tool = has_tool_call(agent_response)
    
    # If not an executable request, any response is valid
    if not is_executable and not force_execution:
        return ExecutionGuardResult(
            is_executable_request=False,
            has_tool_call=has_tool,
            is_valid=True,
            detected_actions=detected_actions
        )
    
    # If executable request but no tool call → VIOLATION
    if (is_executable or force_execution) and not has_tool:
        rejection_msg = _build_rejection_message(detected_actions)
        
        PrintStyle(font_color="yellow", bold=True).print(
            f"[Execution Guard] VIOLATION: Executable request without tool call"
        )
        PrintStyle(font_color="yellow").print(
            f"  Detected actions: {detected_actions}"
        )
        
        return ExecutionGuardResult(
            is_executable_request=True,
            has_tool_call=False,
            is_valid=False,
            rejection_message=rejection_msg,
            detected_actions=detected_actions
        )
    
    # Valid: has tool call
    return ExecutionGuardResult(
        is_executable_request=is_executable,
        has_tool_call=True,
        is_valid=True,
        detected_actions=detected_actions
    )


def _build_rejection_message(detected_actions: list[str]) -> str:
    """Build the EXECUTION_REQUIRED rejection message."""
    actions_str = ", ".join(detected_actions[:5]) if detected_actions else "action requested"
    
    return f"""{{
    "error": "EXECUTION_REQUIRED",
    "message": "You must call a tool to execute this task. Detected action intent: {actions_str}",
    "instructions": [
        "NEVER say MISSING_TOOL. Use code_execution instead.",
        "Write Python code to accomplish the task.",
        "Available: pandas, openpyxl, fitz (PyMuPDF), reportlab, pytesseract, PIL",
        "Files are in: tmp/uploads/",
        "Execute immediately with code_execution tool."
    ],
    "example": {{
        "tool_name": "code_execution",
        "tool_args": {{
            "runtime": "python",
            "code": "import pandas as pd\\ndf = pd.read_excel('tmp/uploads/yourfile.xlsx')\\nprint(df)"
        }}
    }}
}}"""


def get_execution_policy_prompt() -> str:
    """
    Returns the execution policy reminder to inject into system prompt.
    """
    return """
## EXECUTION POLICY ACTIVE
- You MUST call tools when action is requested
- Text-only responses to action requests are REJECTED
- If you cannot execute: respond with MISSING_TOOL: <name>
- Be an operator, not a commentator
"""


# Convenience function for integration
def enforce_execution(user_message: str, agent_response: str) -> tuple[bool, Optional[str]]:
    """
    Simple interface for execution enforcement.
    
    Returns:
        tuple: (is_valid: bool, rejection_message: Optional[str])
    """
    result = check_execution_guard(user_message, agent_response)
    return result.is_valid, result.rejection_message

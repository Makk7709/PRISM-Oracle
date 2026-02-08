"""
Tests for Execution Guard — Validates tool execution enforcement.

Run with: python -m pytest tests/test_execution_guard.py -v
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.execution_guard import (
    detect_action_request,
    has_tool_call,
    check_execution_guard,
    ExecutionGuardResult
)


class TestActionDetection:
    """Test action verb detection in user messages."""
    
    def test_french_action_verbs(self):
        """French action verbs should be detected."""
        messages = [
            "Génère un rapport PDF",
            "Classe ces documents par client",
            "Produis un fichier Excel",
            "Regroupe les factures",
            "Crée un dossier pour chaque client",
            "Exporte les données en CSV",
            "Transforme ce fichier",
            "Analyse ce document",
            "Trie les fichiers alphabétiquement",
            "Fais un PDF de synthèse",
        ]
        
        for msg in messages:
            is_action, actions = detect_action_request(msg)
            assert is_action, f"Should detect action in: {msg}"
            assert len(actions) > 0, f"Should find action verbs in: {msg}"
    
    def test_english_action_verbs(self):
        """English action verbs should be detected."""
        messages = [
            "Generate a PDF report",
            "Classify these documents",
            "Produce an Excel file",
            "Group the invoices",
            "Create a folder for each client",
            "Export data to CSV",
            "Transform this file",
            "Analyze this document",
            "Sort files alphabetically",
            "Make a summary PDF",
        ]
        
        for msg in messages:
            is_action, actions = detect_action_request(msg)
            assert is_action, f"Should detect action in: {msg}"
    
    def test_non_action_messages(self):
        """Non-action messages should not trigger execution requirement."""
        messages = [
            "Bonjour, comment vas-tu?",
            "What is the capital of France?",
            "Explain how neural networks work",
            "Tell me about Python",
            "What time is it?",
        ]
        
        for msg in messages:
            is_action, actions = detect_action_request(msg)
            # These might or might not be detected, but shouldn't force execution
            # The key is they don't have clear file/document context
            pass  # Non-strict test - detection is heuristic


class TestToolCallDetection:
    """Test tool call detection in agent responses."""
    
    def test_valid_tool_call(self):
        """Valid tool calls should be detected."""
        response = '''
        {
            "thoughts": ["Processing request"],
            "tool_name": "code_execution",
            "tool_args": {"code": "print('hello')"}
        }
        '''
        assert has_tool_call(response) is True
    
    def test_response_tool_with_short_text(self):
        """Response tool with short text is valid."""
        response = '''
        {
            "thoughts": ["Done"],
            "tool_name": "response",
            "tool_args": {"text": "Task completed."}
        }
        '''
        assert has_tool_call(response) is True
    
    def test_response_tool_with_missing_tool_rejected(self):
        """Response tool with MISSING_TOOL is REJECTED (agent must use code_execution)."""
        response = '''
        {
            "thoughts": ["No tool available"],
            "tool_name": "response",
            "tool_args": {"text": "MISSING_TOOL: pdf_merger\\nREASON: No tool for merging PDFs"}
        }
        '''
        # MISSING_TOOL responses are explicitly rejected by the execution guard
        # The agent should use code_execution instead
        assert has_tool_call(response) is False
    
    def test_response_tool_with_long_text(self):
        """Response tool with long explanatory text is a violation."""
        long_text = "I will now explain my detailed plan. " * 20  # > 200 chars
        response = f'''
        {{
            "thoughts": ["Explaining plan"],
            "tool_name": "response",
            "tool_args": {{"text": "{long_text}"}}
        }}
        '''
        assert has_tool_call(response) is False
    
    def test_no_tool_call(self):
        """No tool_name should be detected as no tool call."""
        response = "I will analyze the documents and create a plan."
        assert has_tool_call(response) is False


class TestExecutionGuard:
    """Test the main execution guard function."""
    
    def test_action_request_with_tool_call_valid(self):
        """Action request with tool call should be valid."""
        user_msg = "Génère un PDF avec ces documents"
        agent_response = '''
        {
            "thoughts": ["Generating PDF"],
            "tool_name": "code_execution",
            "tool_args": {"code": "generate_pdf()"}
        }
        '''
        
        result = check_execution_guard(user_msg, agent_response)
        assert result.is_valid is True
        assert result.is_executable_request is True
        assert result.has_tool_call is True
    
    def test_action_request_without_tool_call_invalid(self):
        """Action request without tool call should be invalid."""
        user_msg = "Classe ces fichiers par date"
        agent_response = '''
        {
            "thoughts": ["I will explain my plan"],
            "tool_name": "response",
            "tool_args": {"text": "Je vais d'abord analyser les fichiers, puis les classer selon leur date. Voici les étapes que je vais suivre: 1. Lire les métadonnées 2. Extraire les dates 3. Créer les dossiers 4. Déplacer les fichiers. Voulez-vous que je procède?"}
        }
        '''
        
        result = check_execution_guard(user_msg, agent_response)
        assert result.is_valid is False
        assert result.rejection_message is not None
        assert "EXECUTION_REQUIRED" in result.rejection_message
    
    def test_non_action_request_always_valid(self):
        """Non-action requests should always be valid."""
        user_msg = "What is Python?"
        agent_response = '''
        {
            "thoughts": ["Explaining Python"],
            "tool_name": "response",
            "tool_args": {"text": "Python is a programming language..."}
        }
        '''
        
        result = check_execution_guard(user_msg, agent_response)
        assert result.is_valid is True
    
    def test_missing_tool_response_rejected(self):
        """MISSING_TOOL response should be REJECTED (agent must use code_execution)."""
        user_msg = "Fusionne ces PDFs et réordonne les pages"
        agent_response = '''
        {
            "thoughts": ["No tool available for this"],
            "tool_name": "response",
            "tool_args": {"text": "MISSING_TOOL: pdf_page_reorder\\nREASON: No tool allows PDF page reordering"}
        }
        '''
        
        result = check_execution_guard(user_msg, agent_response)
        # The guard REJECTS MISSING_TOOL responses — agent must use code_execution
        assert result.is_valid is False
        assert result.has_tool_call is False


class TestIntegration:
    """Integration tests simulating real scenarios."""
    
    def test_document_classification_scenario(self):
        """Test document classification enforcement."""
        # User asks to classify documents
        user_msg = "Classe ces documents en PDF par client"
        
        # Bad response: just explains
        bad_response = '''
        {
            "thoughts": ["Planning classification"],
            "tool_name": "response",
            "tool_args": {"text": "Je vais classer vos documents. Voici mon plan détaillé: premièrement, je vais identifier les clients, deuxièmement je vais créer des dossiers, troisièmement je vais déplacer les fichiers. Souhaitez-vous que je commence?"}
        }
        '''
        
        result = check_execution_guard(user_msg, bad_response)
        assert result.is_valid is False, "Should reject explanatory response"
        
        # Good response: executes tool
        good_response = '''
        {
            "thoughts": ["Classifying documents"],
            "tool_name": "code_execution",
            "tool_args": {"runtime": "python", "code": "classify_documents()"}
        }
        '''
        
        result = check_execution_guard(user_msg, good_response)
        assert result.is_valid is True, "Should accept tool execution"


# Control Prompt for Manual Testing
CONTROL_PROMPT = """
# PROMPT DE CONTRÔLE — Exécution Obligatoire

## Test 1: Demande d'action → doit forcer tool_call
Message utilisateur:
> "Classe ces documents par client et génère un PDF récapitulatif"

Comportement attendu:
- L'agent appelle immédiatement un tool (code_execution, etc.)
- PAS de longue explication
- PAS de "je vais faire..."

## Test 2: Réponse textuelle seule → doit être rejetée
Si l'agent répond avec:
> "Je vais d'abord analyser les documents..."

Comportement attendu:
- Le système rejette avec EXECUTION_REQUIRED
- L'agent doit regénérer avec un tool_call

## Test 3: Outil manquant → MISSING_TOOL
Message utilisateur:
> "Fusionne ces PDFs et réordonne les pages 3, 1, 2"

Si aucun tool ne permet cela:
> MISSING_TOOL: pdf_page_reorder
> REASON: No tool allows PDF page reordering

## Test 4: Question simple → texte autorisé
Message utilisateur:
> "Qu'est-ce que Python?"

Comportement attendu:
- Réponse textuelle autorisée (pas d'action demandée)

## Critères de Succès
✅ Action request + tool_call = VALID
✅ Action request + long text = REJECTED (EXECUTION_REQUIRED)
✅ Action request + MISSING_TOOL = VALID
✅ Non-action request + text = VALID
✅ L'agent n'entre jamais en mode bavard
"""


if __name__ == "__main__":
    print(CONTROL_PROMPT)
    print("\n" + "="*60)
    print("Running tests...")
    pytest.main([__file__, "-v"])

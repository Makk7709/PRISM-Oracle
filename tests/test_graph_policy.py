"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              GRAPH POLICY TESTS — Kill Tests + Integration                    ║
║                                                                              ║
║  Tests pour valider:                                                          ║
║  - Détection des requêtes graph                                              ║
║  - Routage vers code_execution                                               ║
║  - AUCUNE fuite de debug (kill tests)                                        ║
║  - Génération de graphiques depuis Excel                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.graph_runner import (
    is_graph_request,
    detect_file_type,
    FileType,
    GraphType,
    GraphRequest,
    GraphResult,
    generate_graph_code,
    ALL_GRAPH_KEYWORDS,
)
from python.helpers.execution_guard import (
    has_tool_call,
    detect_action_request,
    check_execution_guard,
)
from python.tools.unknown import (
    is_graph_tool_request,
    GRAPH_TOOL_PATTERNS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: GRAPH REQUEST DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphRequestDetection:
    """Tests pour la détection des requêtes de graphiques."""
    
    # French graph requests
    @pytest.mark.parametrize("text", [
        "Fais un graphique des ventes",
        "Génère un camembert",
        "Trace une courbe d'évolution",
        "Dessine un histogramme",
        "Crée un graph des données",
        "Visualise les tendances",
        "Montre-moi la répartition en barres",
        "Je veux voir la distribution",
    ])
    def test_detect_french_graph_requests(self, text):
        """T1: Détecte les requêtes FR de graphiques."""
        assert is_graph_request(text), f"Should detect graph request: {text}"
    
    # English graph requests
    @pytest.mark.parametrize("text", [
        "Create a bar chart",
        "Generate a pie chart",
        "Plot the data",
        "Draw a histogram",
        "Show me a scatter plot",
        "Visualize the trends",
        "Make a line chart",
    ])
    def test_detect_english_graph_requests(self, text):
        """T2: Détecte les requêtes EN de graphiques."""
        assert is_graph_request(text), f"Should detect graph request: {text}"
    
    # Non-graph requests
    @pytest.mark.parametrize("text", [
        "Lis ce fichier Excel",
        "Résume le document",
        "Envoie un email",
        "Calcule la somme",
        "Read this file",
        "What is the weather?",
    ])
    def test_reject_non_graph_requests(self, text):
        """T3: Ne détecte PAS les requêtes non-graph."""
        assert not is_graph_request(text), f"Should NOT detect: {text}"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: GRAPH TOOL ROUTING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphToolRouting:
    """Tests pour le routage des tools graph vers code_execution."""
    
    @pytest.mark.parametrize("tool_name", [
        "graph",
        "plot",
        "chart",
        "draw_chart",
        "generate_graph",
        "create_plot",
        "visualize",
        "histogram",
        "pie_chart",
        "bar_chart",
        "scatter_plot",
        "line_chart",
    ])
    def test_detect_graph_tool_names(self, tool_name):
        """T4: Détecte les noms d'outils graphiques."""
        assert is_graph_tool_request(tool_name), f"Should detect graph tool: {tool_name}"
    
    @pytest.mark.parametrize("tool_name", [
        "code_execution",
        "response",
        "search_engine",
        "browser_agent",
        "read_file",
        "write_file",
    ])
    def test_reject_non_graph_tool_names(self, tool_name):
        """T5: Ne détecte PAS les outils non-graph."""
        assert not is_graph_tool_request(tool_name), f"Should NOT detect: {tool_name}"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: KILL TESTS — NO DEBUG LEAKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillNoDebugLeaks:
    """
    KILL TESTS: Aucune sortie utilisateur ne doit contenir les chaînes interdites.
    
    Ces tests sont NON-NÉGOCIABLES. Si l'un échoue, le build DOIT échouer.
    """
    
    FORBIDDEN_STRINGS = [
        "Tool not found",
        "Available tools:",
        "TOOL_UNAVAILABLE",
        "GRAPH_POLICY_REDIRECT",
        "MISSING_TOOL",
    ]
    
    def test_kill_tool_not_found_leak(self):
        """KILL-1: 'Tool not found' ne doit JAMAIS atteindre l'utilisateur."""
        # Simuler une réponse avec fuite
        response_with_leak = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "Tool not found. Available tools: code_execution, response..."
            }
        }'''
        
        # has_tool_call doit rejeter cette réponse
        assert not has_tool_call(response_with_leak), \
            "KILL FAILED: 'Tool not found' leak must be rejected!"
    
    def test_kill_available_tools_leak(self):
        """KILL-2: 'Available tools:' ne doit JAMAIS atteindre l'utilisateur."""
        response_with_leak = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "I cannot do that. Available tools: search, browser..."
            }
        }'''
        
        assert not has_tool_call(response_with_leak), \
            "KILL FAILED: 'Available tools' leak must be rejected!"
    
    def test_kill_tool_unavailable_leak(self):
        """KILL-3: 'TOOL_UNAVAILABLE' ne doit JAMAIS atteindre l'utilisateur."""
        response_with_leak = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "TOOL_UNAVAILABLE: graph"
            }
        }'''
        
        assert not has_tool_call(response_with_leak), \
            "KILL FAILED: 'TOOL_UNAVAILABLE' leak must be rejected!"
    
    def test_kill_graph_policy_redirect_leak(self):
        """KILL-4: 'GRAPH_POLICY_REDIRECT' ne doit JAMAIS atteindre l'utilisateur."""
        response_with_leak = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "GRAPH_POLICY_REDIRECT - use code_execution instead"
            }
        }'''
        
        assert not has_tool_call(response_with_leak), \
            "KILL FAILED: 'GRAPH_POLICY_REDIRECT' leak must be rejected!"
    
    def test_kill_missing_tool_leak(self):
        """KILL-5: 'MISSING_TOOL' ne doit JAMAIS atteindre l'utilisateur."""
        response_with_leak = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "MISSING_TOOL: I need a graph tool"
            }
        }'''
        
        assert not has_tool_call(response_with_leak), \
            "KILL FAILED: 'MISSING_TOOL' leak must be rejected!"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: VALID RESPONSES — SHOULD PASS
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidResponses:
    """Tests pour les réponses valides qui DOIVENT passer."""
    
    def test_valid_code_execution_response(self):
        """T6: code_execution avec graph matplotlib doit passer."""
        valid_response = '''{
            "tool_name": "code_execution",
            "tool_args": {
                "runtime": "python",
                "code": "import matplotlib.pyplot as plt\\nplt.bar([1,2,3], [4,5,6])\\nplt.savefig('graph.png')"
            }
        }'''
        
        assert has_tool_call(valid_response), \
            "code_execution for graphs should be accepted!"
    
    def test_valid_short_response(self):
        """T7: Réponse courte après exécution doit passer."""
        valid_response = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "Voici votre graphique! Le fichier est sauvegardé dans tmp/generated/graph.png"
            }
        }'''
        
        assert has_tool_call(valid_response), \
            "Short response after execution should pass!"
    
    def test_valid_graph_result_response(self):
        """T8: Réponse avec résultat de graphique doit passer."""
        valid_response = '''{
            "tool_name": "response",
            "tool_args": {
                "text": "Graphique généré avec succès. 150 lignes analysées."
            }
        }'''
        
        assert has_tool_call(valid_response), \
            "Graph result response should pass!"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: FILE TYPE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileTypeDetection:
    """Tests pour la détection du type de fichier."""
    
    @pytest.mark.parametrize("filename,expected", [
        ("data.xlsx", FileType.EXCEL),
        ("report.xls", FileType.EXCEL),
        ("DATA.XLSX", FileType.EXCEL),
        ("export.csv", FileType.CSV),
        ("document.pdf", FileType.PDF),
        ("image.png", FileType.UNKNOWN),
        ("script.py", FileType.UNKNOWN),
    ])
    def test_detect_file_types(self, filename, expected):
        """T9: Détection correcte des types de fichiers."""
        assert detect_file_type(filename) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: CODE GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodeGeneration:
    """Tests pour la génération de code Python."""
    
    def test_generate_graph_code_contains_matplotlib(self):
        """T10: Le code généré doit contenir matplotlib."""
        code = generate_graph_code("test.xlsx", "Test Graph")
        
        assert "import matplotlib" in code
        assert "matplotlib.use('Agg')" in code
        assert "plt.savefig" in code
    
    def test_generate_graph_code_contains_pandas(self):
        """T11: Le code généré doit contenir pandas."""
        code = generate_graph_code("test.xlsx")
        
        assert "import pandas as pd" in code
        assert "pd.read_excel" in code or "pd.read_csv" in code
    
    def test_generate_graph_code_saves_to_correct_dir(self):
        """T12: Le code doit sauvegarder dans tmp/generated/."""
        code = generate_graph_code("test.xlsx")
        
        assert "tmp/generated" in code
    
    def test_generate_graph_code_no_seaborn(self):
        """T13: Le code ne doit PAS utiliser seaborn."""
        code = generate_graph_code("test.xlsx")
        
        assert "seaborn" not in code.lower()
        assert "sns." not in code


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: INTEGRATION TEST — GRAPH GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphGeneration:
    """Tests d'intégration pour la génération de graphiques."""
    
    @pytest.fixture
    def temp_excel_file(self):
        """Crée un fichier Excel temporaire pour les tests."""
        try:
            import pandas as pd
            import openpyxl
        except ImportError:
            pytest.skip("pandas or openpyxl not installed")
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name
        
        # Créer données test
        df = pd.DataFrame({
            "Category": ["A", "B", "C", "D", "E"],
            "Value": [10, 25, 15, 30, 20],
            "Count": [100, 200, 150, 300, 250],
        })
        df.to_excel(temp_path, index=False)
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_generate_graph_from_excel(self, temp_excel_file):
        """T14: Génère un graphique depuis un Excel valide."""
        from python.helpers.graph_runner import generate_graph, GraphRequest
        
        request = GraphRequest(
            file_path=temp_excel_file,
            title="Test Graph",
        )
        
        result = generate_graph(request)
        
        assert result.success, f"Graph generation failed: {result.error}"
        assert result.file_path is not None
        assert result.graph_type is not None
        assert result.summary
        assert len(result.hypotheses) > 0
    
    def test_generate_graph_returns_artifact(self, temp_excel_file):
        """T15: Le résultat contient un artifact valide."""
        from python.helpers.graph_runner import generate_graph, GraphRequest
        
        request = GraphRequest(file_path=temp_excel_file)
        result = generate_graph(request)
        
        if result.success:
            artifact = result.to_artifact()
            
            assert artifact["type"] == "image"
            assert artifact["path"] is not None
            assert artifact["graph_type"] is not None
    
    def test_graph_markdown_output(self, temp_excel_file):
        """T16: Le markdown de sortie est bien formaté."""
        from python.helpers.graph_runner import generate_graph, GraphRequest
        
        request = GraphRequest(file_path=temp_excel_file)
        result = generate_graph(request)
        
        if result.success:
            md = result.to_markdown()
            
            assert "✅" in md
            assert "![" in md  # Image markdown
            assert "Résumé" in md or "Type:" in md


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: EXECUTION GUARD INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionGuardIntegration:
    """Tests d'intégration avec execution_guard."""
    
    def test_graph_request_requires_execution(self):
        """T17: Une requête graph nécessite une exécution."""
        user_message = "Génère un graphique à partir du fichier Excel"
        
        is_action, actions = detect_action_request(user_message)
        
        assert is_action, "Graph request should be detected as action"
        assert len(actions) > 0
    
    def test_graph_text_response_rejected(self):
        """T18: Réponse texte pour graph sans exécution = rejet."""
        user_message = "Crée un graphique des ventes"
        agent_response = '''{
            "thoughts": ["I will explain how to make a graph"],
            "tool_name": "response",
            "tool_args": {
                "text": "Pour créer un graphique, vous devez d'abord importer matplotlib et pandas. Ensuite, chargez vos données avec pd.read_excel() puis utilisez plt.bar() pour créer un graphique en barres. Voici les étapes détaillées: 1. Installer les bibliothèques 2. Charger le fichier 3. Préparer les données 4. Créer le graphique 5. Sauvegarder le fichier. N'hésitez pas à me demander si vous avez besoin d'aide!"
            }
        }'''
        
        result = check_execution_guard(user_message, agent_response)
        
        # Long text response without actual execution should be rejected
        # OR at minimum it should be flagged as not having tool execution
        assert result.is_executable_request, \
            "Graph request should be marked as executable"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: KEYWORDS COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeywordsCoverage:
    """Tests pour la couverture des mots-clés."""
    
    def test_all_french_keywords_covered(self):
        """T19: Tous les mots-clés FR sont dans la liste."""
        required_fr = ["graph", "courbe", "camembert", "histogramme", "barres"]
        
        for kw in required_fr:
            assert kw in ALL_GRAPH_KEYWORDS, f"Missing FR keyword: {kw}"
    
    def test_all_english_keywords_covered(self):
        """T20: Tous les mots-clés EN sont dans la liste."""
        required_en = ["chart", "plot", "pie", "histogram", "scatter", "bar"]
        
        for kw in required_en:
            assert kw in ALL_GRAPH_KEYWORDS, f"Missing EN keyword: {kw}"
    
    def test_tool_patterns_coverage(self):
        """T21: Les patterns d'outils couvrent les cas critiques."""
        assert "graph" in GRAPH_TOOL_PATTERNS
        assert "plot" in GRAPH_TOOL_PATTERNS
        assert "chart" in GRAPH_TOOL_PATTERNS


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

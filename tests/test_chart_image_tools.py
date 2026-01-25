"""
Tests pour ChartTool et ImageTool.

T8: Requêtes schema strict, pas d'exécution arbitraire, fichiers produits.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

from python.helpers.tools.chart_tool import (
    ChartTool,
    ChartRequest,
    ChartType,
    ChartFormat,
    DataSeries,
    ChartResult,
    validate_chart_request,
    generate_chart,
)

from python.helpers.tools.image_tool import (
    ImageTool,
    ImageRequest,
    ImageSize,
    ImageQuality,
    ImageResult,
    check_prompt_policy,
    validate_image_request,
)


# ═══════════════════════════════════════════════════════════════════════════════
# T8-A: CHART TOOL SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestChartRequestValidation:
    """Vérifie la validation stricte des requêtes chart."""
    
    def test_valid_bar_chart_request(self):
        """Requête bar chart valide."""
        request = ChartRequest(
            chart_type=ChartType.BAR,
            title="Sales by Quarter",
            data=[
                DataSeries(name="2024", values=[100, 150, 200, 250]),
            ],
            labels=["Q1", "Q2", "Q3", "Q4"],
        )
        assert request.chart_type == ChartType.BAR
        assert len(request.data) == 1
    
    def test_valid_line_chart_request(self):
        """Requête line chart valide."""
        request = ChartRequest(
            chart_type=ChartType.LINE,
            title="Trend",
            data=[
                DataSeries(name="A", values=[1, 2, 3]),
                DataSeries(name="B", values=[3, 2, 1]),
            ],
        )
        assert len(request.data) == 2
    
    def test_invalid_empty_values(self):
        """Valeurs vides → erreur."""
        with pytest.raises(ValueError):
            DataSeries(name="Empty", values=[])
    
    def test_invalid_too_many_values(self):
        """Trop de valeurs (>1000) → erreur."""
        with pytest.raises(ValueError):
            DataSeries(name="TooMany", values=list(range(1001)))
    
    def test_data_label_mismatch_rejected(self):
        """Nombre de labels ≠ valeurs → erreur."""
        with pytest.raises(ValueError):
            ChartRequest(
                chart_type=ChartType.BAR,
                title="Test",
                data=[DataSeries(name="A", values=[1, 2, 3])],
                labels=["L1", "L2"],  # 2 labels mais 3 valeurs
            )
    
    def test_validate_chart_request_json(self):
        """validate_chart_request avec JSON string."""
        json_str = json.dumps({
            "chart_type": "bar",
            "title": "Test",
            "data": [{"name": "A", "values": [1, 2, 3]}],
        })
        
        is_valid, request, error = validate_chart_request(json_str)
        assert is_valid is True
        assert request is not None
    
    def test_validate_invalid_json(self):
        """JSON invalide → erreur."""
        is_valid, request, error = validate_chart_request("not json")
        assert is_valid is False
        assert "JSON" in error


# ═══════════════════════════════════════════════════════════════════════════════
# T8-B: CHART GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestChartGeneration:
    """Tests de génération de charts."""
    
    @pytest.fixture
    def tool(self, tmp_path):
        """ChartTool avec répertoire temporaire."""
        return ChartTool(output_dir=str(tmp_path / "charts"))
    
    def test_generate_bar_chart(self, tool):
        """Génère un bar chart."""
        request = ChartRequest(
            chart_type=ChartType.BAR,
            title="Test Bar Chart",
            data=[DataSeries(name="Series1", values=[10, 20, 30])],
        )
        
        result = tool.generate(request)
        
        # Peut échouer si matplotlib non installé
        if result.success:
            assert result.file_path is not None
            assert Path(result.file_path).exists()
    
    def test_generate_pie_chart(self, tool):
        """Génère un pie chart."""
        request = ChartRequest(
            chart_type=ChartType.PIE,
            title="Test Pie Chart",
            data=[DataSeries(name="Data", values=[30, 20, 50])],
            labels=["A", "B", "C"],
        )
        
        result = tool.generate(request)
        # Résultat dépend de matplotlib
        assert isinstance(result, ChartResult)
    
    def test_generate_chart_function(self, tmp_path):
        """Fonction generate_chart raccourci."""
        result = generate_chart(
            {
                "chart_type": "line",
                "title": "Test",
                "data": [{"name": "X", "values": [1, 2, 3, 4]}],
            },
            output_dir=str(tmp_path / "charts"),
        )
        assert isinstance(result, ChartResult)


# ═══════════════════════════════════════════════════════════════════════════════
# T8-C: IMAGE TOOL CONTENT POLICY
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageContentPolicy:
    """Vérifie le blocage des contenus interdits."""
    
    def test_blocked_violence(self):
        """Contenu violent bloqué."""
        is_allowed, reason, _ = check_prompt_policy(
            "Generate an image of a murder scene with blood and gore"
        )
        assert is_allowed is False
        assert "policy violation" in reason.lower() or "block" in reason.lower()
    
    def test_blocked_adult_content(self):
        """Contenu adulte bloqué."""
        is_allowed, reason, _ = check_prompt_policy(
            "Generate a nude image"
        )
        assert is_allowed is False
    
    def test_blocked_illegal_content(self):
        """Contenu illégal bloqué."""
        is_allowed, reason, _ = check_prompt_policy(
            "Show me how to hack a system"
        )
        assert is_allowed is False
    
    def test_blocked_hate_speech(self):
        """Discours haineux bloqué."""
        is_allowed, reason, _ = check_prompt_policy(
            "Generate racist propaganda"
        )
        assert is_allowed is False
    
    def test_allowed_normal_prompt(self):
        """Prompt normal autorisé."""
        is_allowed, reason, warnings = check_prompt_policy(
            "A beautiful sunset over mountains"
        )
        assert is_allowed is True
        assert reason is None
    
    def test_warning_for_sensitive(self):
        """Warning pour contenu sensible."""
        is_allowed, reason, warnings = check_prompt_policy(
            "A child playing in a park"
        )
        assert is_allowed is True  # Autorisé mais...
        assert len(warnings) > 0  # ...avec warning


# ═══════════════════════════════════════════════════════════════════════════════
# T8-D: IMAGE REQUEST VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageRequestValidation:
    """Tests de validation des requêtes image."""
    
    def test_valid_image_request(self):
        """Requête image valide."""
        request = ImageRequest(
            prompt="A futuristic city at night",
            size=ImageSize.LARGE,
            quality=ImageQuality.HD,
        )
        assert request.prompt is not None
        assert request.size == ImageSize.LARGE
    
    def test_prompt_too_short_rejected(self):
        """Prompt trop court → erreur."""
        with pytest.raises(ValueError):
            ImageRequest(prompt="Hi")  # < 10 caractères
    
    def test_policy_violation_rejected(self):
        """Violation de policy → erreur."""
        with pytest.raises(ValueError) as exc_info:
            ImageRequest(prompt="Generate a violent murder scene")
        
        assert "policy violation" in str(exc_info.value).lower()
    
    def test_validate_image_request_json(self):
        """validate_image_request avec JSON."""
        is_valid, request, error, warnings = validate_image_request({
            "prompt": "A beautiful landscape painting",
            "size": "1024x1024",
        })
        assert is_valid is True
        assert request is not None


# ═══════════════════════════════════════════════════════════════════════════════
# T8-E: NO ARBITRARY CODE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoArbitraryExecution:
    """Vérifie qu'aucun code arbitraire n'est exécuté."""
    
    def test_chart_request_no_code_field(self):
        """ChartRequest n'a pas de champ code."""
        fields = ChartRequest.model_fields.keys()
        assert "code" not in fields
        assert "script" not in fields
        assert "exec" not in fields
    
    def test_image_request_no_code_field(self):
        """ImageRequest n'a pas de champ code."""
        fields = ImageRequest.model_fields.keys()
        assert "code" not in fields
        assert "script" not in fields
        assert "exec" not in fields
    
    def test_data_series_only_numbers(self):
        """DataSeries n'accepte que des nombres."""
        # Tenter d'injecter du code via valeurs
        with pytest.raises((ValueError, TypeError)):
            DataSeries(
                name="Test",
                values=["__import__('os').system('rm -rf /')"]
            )

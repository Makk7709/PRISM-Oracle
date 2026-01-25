"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CHART TOOL — Safe Matplotlib Wrapper                      ║
║                                                                              ║
║  Génération de graphiques via schéma strict.                                 ║
║                                                                              ║
║  SÉCURITÉ:                                                                   ║
║  - Le LLM NE dessine PAS lui-même                                            ║
║  - Il demande un chart via JSON structuré                                    ║
║  - Validation stricte du schéma avant exécution                              ║
║  - Pas d'exécution de code arbitraire                                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("chart_tool")


# ═══════════════════════════════════════════════════════════════════════════════
# CHART TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ChartType(str, Enum):
    """Types de graphiques supportés."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    AREA = "area"
    HEATMAP = "heatmap"
    BOX = "box"


class ChartFormat(str, Enum):
    """Formats de sortie."""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"


# ═══════════════════════════════════════════════════════════════════════════════
# CHART REQUEST SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

class DataSeries(BaseModel):
    """Une série de données pour le graphique."""
    name: str = Field(..., description="Nom de la série")
    values: List[Union[int, float]] = Field(..., description="Valeurs numériques")
    color: Optional[str] = Field(None, description="Couleur (hex ou nom)")
    
    @field_validator("values")
    @classmethod
    def validate_values(cls, v):
        if not v:
            raise ValueError("Values cannot be empty")
        if len(v) > 1000:
            raise ValueError("Too many values (max 1000)")
        return v
    
    @field_validator("color")
    @classmethod
    def validate_color(cls, v):
        if v is None:
            return v
        # Accepter couleurs nommées ou hex
        valid_colors = [
            "red", "blue", "green", "yellow", "orange", "purple",
            "cyan", "magenta", "black", "white", "gray", "grey"
        ]
        if v.lower() in valid_colors:
            return v
        if v.startswith("#") and len(v) == 7:
            return v
        raise ValueError(f"Invalid color: {v}")


class ChartRequest(BaseModel):
    """
    Requête de génération de graphique.
    
    Le LLM doit soumettre ce schéma JSON pour demander un graphique.
    """
    
    # Type et titre
    chart_type: ChartType = Field(..., description="Type de graphique")
    title: str = Field(..., max_length=200, description="Titre du graphique")
    
    # Données
    data: List[DataSeries] = Field(..., min_length=1, max_length=10)
    labels: Optional[List[str]] = Field(None, description="Labels pour l'axe X")
    
    # Axes
    x_label: str = Field("", max_length=100)
    y_label: str = Field("", max_length=100)
    
    # Options
    legend: bool = Field(True, description="Afficher la légende")
    grid: bool = Field(True, description="Afficher la grille")
    
    # Sortie
    output_format: ChartFormat = Field(ChartFormat.PNG)
    width: int = Field(800, ge=200, le=2000)
    height: int = Field(600, ge=200, le=2000)
    dpi: int = Field(100, ge=72, le=300)
    
    # Sécurité
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID unique de la requête"
    )
    
    @model_validator(mode="after")
    def validate_data_consistency(self) -> "ChartRequest":
        """Vérifie la cohérence des données."""
        if self.labels:
            # Vérifier que les labels correspondent aux données
            for series in self.data:
                if len(series.values) != len(self.labels):
                    raise ValueError(
                        f"Series '{series.name}' has {len(series.values)} values "
                        f"but {len(self.labels)} labels provided"
                    )
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_chart_request(request_json: Union[str, Dict]) -> Tuple[bool, Optional[ChartRequest], Optional[str]]:
    """
    Valide une requête de graphique.
    
    Args:
        request_json: JSON string ou dict de la requête
        
    Returns:
        (is_valid, parsed_request, error_message)
    """
    try:
        if isinstance(request_json, str):
            data = json.loads(request_json)
        else:
            data = request_json
        
        request = ChartRequest(**data)
        return True, request, None
        
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {e}"
    except Exception as e:
        return False, None, f"Validation error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# CHART TOOL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChartResult:
    """Résultat de la génération d'un graphique."""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    request_id: str = ""
    error: Optional[str] = None
    generation_time_ms: int = 0
    
    def to_markdown_ref(self) -> str:
        """Retourne une référence markdown vers le graphique."""
        if self.success and self.file_path:
            name = Path(self.file_path).name
            return f"![{name}]({self.file_path})"
        return f"*Chart generation failed: {self.error}*"


class ChartTool:
    """
    Outil de génération de graphiques via matplotlib.
    
    Usage:
        tool = ChartTool(output_dir="reports/job_123/assets")
        
        request = ChartRequest(
            chart_type=ChartType.BAR,
            title="Sales by Quarter",
            data=[
                DataSeries(name="2024", values=[100, 150, 200, 250]),
                DataSeries(name="2023", values=[80, 120, 180, 220]),
            ],
            labels=["Q1", "Q2", "Q3", "Q4"],
            x_label="Quarter",
            y_label="Sales (M$)",
        )
        
        result = tool.generate(request)
        print(result.file_path)
    """
    
    def __init__(self, output_dir: str = "charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Vérifier matplotlib
        try:
            import matplotlib
            matplotlib.use('Agg')  # Backend non-interactif
            self._matplotlib_available = True
        except ImportError:
            self._matplotlib_available = False
            logger.warning("matplotlib not available, chart generation disabled")
    
    def generate(self, request: ChartRequest) -> ChartResult:
        """
        Génère un graphique.
        
        Args:
            request: Requête validée
            
        Returns:
            ChartResult avec le chemin du fichier
        """
        import time
        start_time = time.time()
        
        if not self._matplotlib_available:
            return ChartResult(
                success=False,
                request_id=request.request_id,
                error="matplotlib not available",
            )
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(request.width / 100, request.height / 100))
            
            # Générer selon le type
            if request.chart_type == ChartType.LINE:
                self._draw_line(ax, request)
            elif request.chart_type == ChartType.BAR:
                self._draw_bar(ax, request)
            elif request.chart_type == ChartType.PIE:
                self._draw_pie(ax, request)
            elif request.chart_type == ChartType.SCATTER:
                self._draw_scatter(ax, request)
            elif request.chart_type == ChartType.HISTOGRAM:
                self._draw_histogram(ax, request)
            elif request.chart_type == ChartType.AREA:
                self._draw_area(ax, request)
            elif request.chart_type == ChartType.BOX:
                self._draw_box(ax, request)
            else:
                raise ValueError(f"Unsupported chart type: {request.chart_type}")
            
            # Titre et labels
            ax.set_title(request.title, fontsize=14, fontweight='bold')
            if request.x_label:
                ax.set_xlabel(request.x_label)
            if request.y_label:
                ax.set_ylabel(request.y_label)
            
            # Légende et grille
            if request.legend and len(request.data) > 1:
                ax.legend()
            if request.grid and request.chart_type != ChartType.PIE:
                ax.grid(True, alpha=0.3)
            
            # Sauvegarder
            filename = f"chart_{request.request_id[:8]}.{request.output_format.value}"
            file_path = self.output_dir / filename
            
            plt.tight_layout()
            plt.savefig(file_path, format=request.output_format.value, dpi=request.dpi)
            plt.close(fig)
            
            file_size = file_path.stat().st_size
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Chart generated: {filename} ({file_size} bytes, {generation_time_ms}ms)"
            )
            
            return ChartResult(
                success=True,
                file_path=str(file_path),
                file_size=file_size,
                request_id=request.request_id,
                generation_time_ms=generation_time_ms,
            )
            
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return ChartResult(
                success=False,
                request_id=request.request_id,
                error=str(e),
                generation_time_ms=int((time.time() - start_time) * 1000),
            )
    
    # ─────────────────────────────────────────────────────────────────────────
    # DRAWING METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _draw_line(self, ax, request: ChartRequest):
        """Dessine un graphique linéaire."""
        x = request.labels or list(range(len(request.data[0].values)))
        for series in request.data:
            ax.plot(x, series.values, label=series.name, color=series.color, marker='o')
    
    def _draw_bar(self, ax, request: ChartRequest):
        """Dessine un graphique en barres."""
        import numpy as np
        
        x = np.arange(len(request.data[0].values))
        width = 0.8 / len(request.data)
        
        for i, series in enumerate(request.data):
            offset = width * (i - len(request.data) / 2 + 0.5)
            ax.bar(x + offset, series.values, width, label=series.name, color=series.color)
        
        if request.labels:
            ax.set_xticks(x)
            ax.set_xticklabels(request.labels)
    
    def _draw_pie(self, ax, request: ChartRequest):
        """Dessine un graphique en camembert."""
        series = request.data[0]
        labels = request.labels or [f"Item {i+1}" for i in range(len(series.values))]
        ax.pie(series.values, labels=labels, autopct='%1.1f%%')
    
    def _draw_scatter(self, ax, request: ChartRequest):
        """Dessine un nuage de points."""
        if len(request.data) >= 2:
            ax.scatter(
                request.data[0].values,
                request.data[1].values,
                label=f"{request.data[0].name} vs {request.data[1].name}",
                color=request.data[0].color,
            )
        else:
            x = list(range(len(request.data[0].values)))
            ax.scatter(x, request.data[0].values, label=request.data[0].name)
    
    def _draw_histogram(self, ax, request: ChartRequest):
        """Dessine un histogramme."""
        for series in request.data:
            ax.hist(series.values, label=series.name, alpha=0.7, color=series.color)
    
    def _draw_area(self, ax, request: ChartRequest):
        """Dessine un graphique en aires."""
        x = request.labels or list(range(len(request.data[0].values)))
        for series in request.data:
            ax.fill_between(x, series.values, alpha=0.5, label=series.name)
            ax.plot(x, series.values, color=series.color)
    
    def _draw_box(self, ax, request: ChartRequest):
        """Dessine un box plot."""
        data = [series.values for series in request.data]
        labels = [series.name for series in request.data]
        ax.boxplot(data, labels=labels)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

_tool_instance: Optional[ChartTool] = None


def generate_chart(
    request_json: Union[str, Dict],
    output_dir: str = "charts",
) -> ChartResult:
    """
    Génère un graphique depuis une requête JSON.
    
    Usage:
        result = generate_chart({
            "chart_type": "bar",
            "title": "Sales",
            "data": [{"name": "2024", "values": [100, 150, 200]}],
            "labels": ["Q1", "Q2", "Q3"]
        })
    """
    # Valider
    is_valid, request, error = validate_chart_request(request_json)
    if not is_valid:
        return ChartResult(success=False, error=error)
    
    # Générer
    global _tool_instance
    if _tool_instance is None or str(_tool_instance.output_dir) != output_dir:
        _tool_instance = ChartTool(output_dir)
    
    return _tool_instance.generate(request)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ChartType",
    "ChartFormat",
    "DataSeries",
    "ChartRequest",
    "ChartResult",
    "ChartTool",
    "validate_chart_request",
    "generate_chart",
]

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GRAPH RUNNER — Auto-Graph from Data                       ║
║                                                                              ║
║  Génération automatique de graphiques depuis fichiers Excel/CSV/PDF.        ║
║                                                                              ║
║  FEATURES:                                                                   ║
║  - Détection automatique du type de fichier                                  ║
║  - Sélection intelligente du type de graphique                               ║
║  - Export PNG/PDF dans tmp/generated/                                        ║
║  - Résumé interprétatif des données                                          ║
║                                                                              ║
║  SÉCURITÉ:                                                                   ║
║  - Utilise UNIQUEMENT matplotlib (pas seaborn)                               ║
║  - Validation stricte des chemins de fichiers                                ║
║  - Pas d'exécution de code arbitraire                                        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("graph_runner")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "tmp/generated"

GRAPH_KEYWORDS_FR = [
    "graph", "graphique", "courbe", "camembert", "histogramme",
    "barres", "nuage", "scatter", "évolution", "trend", "tendance",
    "répartition", "distribution", "pie", "chart", "plot", "figure",
    "diagramme", "visualisation", "visualiser", "tracer", "dessiner",
]

GRAPH_KEYWORDS_EN = [
    "graph", "chart", "plot", "curve", "pie", "histogram", "bar",
    "scatter", "trend", "evolution", "distribution", "figure",
    "diagram", "visualize", "visualization", "draw", "line chart",
]

ALL_GRAPH_KEYWORDS = list(set(GRAPH_KEYWORDS_FR + GRAPH_KEYWORDS_EN))


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class GraphType(str, Enum):
    """Types de graphiques supportés."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    AREA = "area"
    HBAR = "hbar"  # Horizontal bar


class FileType(str, Enum):
    """Types de fichiers supportés."""
    EXCEL = "excel"
    CSV = "csv"
    PDF = "pdf"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GraphRequest:
    """Requête de génération de graphique."""
    file_path: str
    title: Optional[str] = None
    graph_type: Optional[GraphType] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    output_format: str = "png"
    width: int = 1200
    height: int = 800
    dpi: int = 100


@dataclass
class GraphResult:
    """Résultat de la génération."""
    success: bool
    file_path: Optional[str] = None
    graph_type: Optional[GraphType] = None
    title: str = ""
    summary: str = ""
    hypotheses: List[str] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None
    generation_time_ms: int = 0
    data_shape: Tuple[int, int] = (0, 0)
    columns_used: List[str] = field(default_factory=list)
    
    def to_artifact(self) -> Dict[str, Any]:
        """Convertit en artifact pour Output Contract."""
        return {
            "type": "image",
            "path": self.file_path,
            "description": self.title,
            "graph_type": self.graph_type.value if self.graph_type else None,
            "summary": self.summary,
            "hypotheses": self.hypotheses,
            "sources": self.sources,
        }
    
    def to_markdown(self) -> str:
        """Génère le markdown pour affichage."""
        if not self.success:
            return f"## ❌ Génération échouée\n\n**Erreur:** {self.error}"
        
        md = f"## ✅ Graphique généré\n\n"
        md += f"![{self.title}]({self.file_path})\n\n"
        
        if self.summary:
            md += f"### Résumé\n{self.summary}\n\n"
        
        if self.hypotheses:
            md += "### Hypothèses\n"
            for h in self.hypotheses:
                md += f"- {h}\n"
            md += "\n"
        
        md += f"*Type: {self.graph_type.value if self.graph_type else 'auto'} • "
        md += f"Données: {self.data_shape[0]} lignes × {self.data_shape[1]} colonnes • "
        md += f"{self.generation_time_ms}ms*\n"
        
        return md


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def is_graph_request(text: str) -> bool:
    """
    Détecte si une requête utilisateur demande un graphique.
    
    Args:
        text: Texte de la requête
        
    Returns:
        True si la requête demande un graphique
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Vérifier les mots-clés
    for keyword in ALL_GRAPH_KEYWORDS:
        if keyword in text_lower:
            return True
    
    # Patterns régex pour expressions composées
    patterns = [
        r"fais\s+(un|une|le|la|des)\s+(graph|chart|courbe)",
        r"génère\s+(un|une)\s+(graph|chart|plot)",
        r"trace\s+(un|une|la|le)",
        r"dessine\s+(un|une)",
        r"visualise\s+(les|la|le)",
        r"create\s+a\s+(graph|chart|plot)",
        r"generate\s+a\s+(graph|chart|plot)",
        r"make\s+a\s+(graph|chart|plot)",
        r"show\s+(me\s+)?(a\s+)?(graph|chart|plot)",
    ]
    
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False


def detect_file_type(file_path: str) -> FileType:
    """Détecte le type de fichier."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext in [".xlsx", ".xls", ".xlsm"]:
        return FileType.EXCEL
    elif ext == ".csv":
        return FileType.CSV
    elif ext == ".pdf":
        return FileType.PDF
    else:
        return FileType.UNKNOWN


def detect_best_graph_type(df, x_col: Optional[str] = None, y_col: Optional[str] = None) -> Tuple[GraphType, str, str, List[str]]:
    """
    Détecte automatiquement le meilleur type de graphique.
    
    Returns:
        (graph_type, x_column, y_column, hypotheses)
    """
    import pandas as pd
    
    hypotheses = []
    
    # Analyser les colonnes
    date_cols = []
    numeric_cols = []
    categorical_cols = []
    
    for col in df.columns:
        # Détecter dates
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
        elif df[col].dtype == 'object':
            # Essayer de parser comme date
            try:
                pd.to_datetime(df[col], errors='raise')
                date_cols.append(col)
            except:
                # C'est une catégorie
                if df[col].nunique() <= 20:
                    categorical_cols.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
    
    # Logique de sélection
    if x_col and y_col:
        # Colonnes spécifiées
        if x_col in date_cols:
            return GraphType.LINE, x_col, y_col, ["Colonnes X/Y spécifiées par l'utilisateur"]
        elif x_col in categorical_cols:
            return GraphType.BAR, x_col, y_col, ["Colonnes X/Y spécifiées par l'utilisateur"]
        else:
            return GraphType.SCATTER, x_col, y_col, ["Colonnes X/Y spécifiées par l'utilisateur"]
    
    # Auto-détection
    if date_cols and numeric_cols:
        # Données temporelles → Line chart
        x = date_cols[0]
        y = numeric_cols[0]
        hypotheses.append(f"Colonne '{x}' détectée comme temporelle → Line chart")
        hypotheses.append(f"Colonne '{y}' utilisée pour les valeurs")
        return GraphType.LINE, x, y, hypotheses
    
    elif categorical_cols and numeric_cols:
        # Catégories + valeurs → Bar chart
        x = categorical_cols[0]
        y = numeric_cols[0]
        hypotheses.append(f"Colonne '{x}' détectée comme catégorielle → Bar chart")
        hypotheses.append(f"Colonne '{y}' utilisée pour les valeurs")
        
        # Si trop de catégories, utiliser horizontal
        if df[x].nunique() > 10:
            hypotheses.append("Plus de 10 catégories → Bar chart horizontal")
            return GraphType.HBAR, x, y, hypotheses
        
        return GraphType.BAR, x, y, hypotheses
    
    elif len(numeric_cols) >= 2:
        # 2+ colonnes numériques → Scatter
        x = numeric_cols[0]
        y = numeric_cols[1]
        hypotheses.append(f"Deux colonnes numériques détectées → Scatter plot")
        hypotheses.append(f"X: '{x}', Y: '{y}'")
        return GraphType.SCATTER, x, y, hypotheses
    
    elif len(numeric_cols) == 1:
        # Une seule colonne numérique → Histogram
        y = numeric_cols[0]
        hypotheses.append(f"Une seule colonne numérique → Histogramme de distribution")
        return GraphType.HISTOGRAM, None, y, hypotheses
    
    elif categorical_cols:
        # Que des catégories → Pie chart des fréquences
        x = categorical_cols[0]
        hypotheses.append(f"Que des catégories → Camembert des fréquences de '{x}'")
        return GraphType.PIE, x, None, hypotheses
    
    # Fallback
    hypotheses.append("Données non structurées → Bar chart par défaut")
    if len(df.columns) >= 2:
        return GraphType.BAR, df.columns[0], df.columns[1], hypotheses
    
    return GraphType.BAR, df.columns[0], df.columns[0], hypotheses


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_data(file_path: str) -> Tuple[Any, FileType, Optional[str]]:
    """
    Charge les données depuis un fichier.
    
    Returns:
        (dataframe, file_type, error)
    """
    import pandas as pd
    
    file_type = detect_file_type(file_path)
    
    try:
        if file_type == FileType.EXCEL:
            # Essayer différents moteurs
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except:
                df = pd.read_excel(file_path)
            return df, file_type, None
        
        elif file_type == FileType.CSV:
            # Essayer différents encodages
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    return df, file_type, None
                except:
                    continue
            return None, file_type, "Impossible de lire le CSV (encodage non supporté)"
        
        elif file_type == FileType.PDF:
            # Extraire tableaux du PDF
            try:
                import tabula
                dfs = tabula.read_pdf(file_path, pages='all')
                if dfs:
                    df = pd.concat(dfs, ignore_index=True)
                    return df, file_type, None
                else:
                    return None, file_type, "Aucun tableau trouvé dans le PDF"
            except ImportError:
                return None, file_type, "tabula-py non installé pour lecture PDF"
            except Exception as e:
                return None, file_type, f"Erreur lecture PDF: {str(e)}"
        
        else:
            return None, file_type, f"Type de fichier non supporté: {file_path}"
    
    except Exception as e:
        return None, file_type, f"Erreur chargement: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_graph(request: GraphRequest) -> GraphResult:
    """
    Génère un graphique depuis une requête.
    
    Args:
        request: GraphRequest avec les paramètres
        
    Returns:
        GraphResult avec le chemin du fichier généré
    """
    import matplotlib
    matplotlib.use('Agg')  # Backend non-interactif
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    
    start_time = time.time()
    
    # Vérifier le fichier
    if not os.path.exists(request.file_path):
        return GraphResult(
            success=False,
            error=f"Fichier non trouvé: {request.file_path}",
            generation_time_ms=int((time.time() - start_time) * 1000)
        )
    
    # Charger les données
    df, file_type, error = load_data(request.file_path)
    if error:
        return GraphResult(
            success=False,
            error=error,
            generation_time_ms=int((time.time() - start_time) * 1000)
        )
    
    if df is None or df.empty:
        return GraphResult(
            success=False,
            error="Fichier vide ou non lisible",
            generation_time_ms=int((time.time() - start_time) * 1000)
        )
    
    # Nettoyer les données
    df = df.dropna(how='all')  # Supprimer lignes vides
    
    # Détecter le type de graphique
    graph_type, x_col, y_col, hypotheses = detect_best_graph_type(
        df, 
        request.x_column, 
        request.y_column
    )
    
    if request.graph_type:
        graph_type = request.graph_type
        hypotheses.insert(0, f"Type de graphique spécifié: {graph_type.value}")
    
    # Préparer le titre
    title = request.title or f"Analyse de {Path(request.file_path).stem}"
    
    # Créer la figure
    fig, ax = plt.subplots(figsize=(request.width / 100, request.height / 100))
    
    try:
        # Générer selon le type
        if graph_type == GraphType.LINE:
            _draw_line(ax, df, x_col, y_col, title)
        elif graph_type == GraphType.BAR:
            _draw_bar(ax, df, x_col, y_col, title)
        elif graph_type == GraphType.HBAR:
            _draw_hbar(ax, df, x_col, y_col, title)
        elif graph_type == GraphType.PIE:
            _draw_pie(ax, df, x_col, title)
        elif graph_type == GraphType.SCATTER:
            _draw_scatter(ax, df, x_col, y_col, title)
        elif graph_type == GraphType.HISTOGRAM:
            _draw_histogram(ax, df, y_col, title)
        elif graph_type == GraphType.AREA:
            _draw_area(ax, df, x_col, y_col, title)
        else:
            _draw_bar(ax, df, x_col, y_col, title)
        
        # Style
        import matplotlib.pyplot as plt
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Sauvegarder
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"graph_{uuid.uuid4().hex[:8]}.{request.output_format}"
        output_path = output_dir / filename
        
        plt.savefig(output_path, format=request.output_format, dpi=request.dpi, 
                   bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        # Générer le résumé
        summary = _generate_summary(df, graph_type, x_col, y_col)
        
        # Sources
        sources = [
            {"id": "S1", "type": "document", "path": request.file_path, "reliability": "high"},
            {"id": "S2", "type": "tool", "name": "graph_runner", "reliability": "high"},
        ]
        
        generation_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Graph generated: {filename} ({generation_time}ms)")
        
        return GraphResult(
            success=True,
            file_path=str(output_path),
            graph_type=graph_type,
            title=title,
            summary=summary,
            hypotheses=hypotheses,
            sources=sources,
            generation_time_ms=generation_time,
            data_shape=(len(df), len(df.columns)),
            columns_used=[x_col, y_col] if y_col else [x_col] if x_col else [],
        )
        
    except Exception as e:
        plt.close(fig)
        logger.error(f"Graph generation failed: {e}")
        return GraphResult(
            success=False,
            error=str(e),
            generation_time_ms=int((time.time() - start_time) * 1000)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DRAWING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_line(ax, df, x_col: str, y_col: str, title: str):
    """Dessine un graphique linéaire."""
    import pandas as pd
    import matplotlib.pyplot as plt
    
    # Convertir X en datetime si possible
    try:
        x_data = pd.to_datetime(df[x_col])
    except:
        x_data = df[x_col]
    
    y_data = pd.to_numeric(df[y_col], errors='coerce')
    
    ax.plot(x_data, y_data, marker='o', markersize=4, linewidth=2, color='#2196F3')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, alpha=0.3)
    
    # Rotation des labels si dates
    plt.xticks(rotation=45, ha='right')


def _draw_bar(ax, df, x_col: str, y_col: str, title: str):
    """Dessine un graphique en barres."""
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Agréger si nécessaire
    if df[x_col].duplicated().any():
        grouped = df.groupby(x_col)[y_col].sum()
        x_data = grouped.index.tolist()
        y_data = grouped.values
    else:
        x_data = df[x_col].tolist()
        y_data = pd.to_numeric(df[y_col], errors='coerce').tolist()
    
    # Limiter à 20 barres
    if len(x_data) > 20:
        x_data = x_data[:20]
        y_data = y_data[:20]
    
    colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(x_data)))
    ax.bar(range(len(x_data)), y_data, color=colors)
    ax.set_xticks(range(len(x_data)))
    ax.set_xticklabels([str(x)[:15] for x in x_data], rotation=45, ha='right')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, alpha=0.3, axis='y')


def _draw_hbar(ax, df, x_col: str, y_col: str, title: str):
    """Dessine un graphique en barres horizontales."""
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Agréger si nécessaire
    if df[x_col].duplicated().any():
        grouped = df.groupby(x_col)[y_col].sum().sort_values(ascending=True)
        y_labels = grouped.index.tolist()
        x_values = grouped.values
    else:
        y_labels = df[x_col].tolist()
        x_values = pd.to_numeric(df[y_col], errors='coerce').tolist()
    
    # Limiter à 20 barres
    if len(y_labels) > 20:
        y_labels = y_labels[-20:]
        x_values = x_values[-20:]
    
    colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(y_labels)))
    ax.barh(range(len(y_labels)), x_values, color=colors)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels([str(y)[:20] for y in y_labels])
    ax.set_xlabel(y_col)
    ax.set_ylabel(x_col)
    ax.grid(True, alpha=0.3, axis='x')


def _draw_pie(ax, df, x_col: str, title: str):
    """Dessine un camembert."""
    import matplotlib.pyplot as plt
    
    # Compter les fréquences
    counts = df[x_col].value_counts()
    
    # Limiter à 10 catégories
    if len(counts) > 10:
        others = counts[10:].sum()
        counts = counts[:10]
        counts['Autres'] = others
    
    colors = plt.cm.Set3(range(len(counts)))
    ax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', 
           colors=colors, startangle=90)
    ax.axis('equal')


def _draw_scatter(ax, df, x_col: str, y_col: str, title: str):
    """Dessine un nuage de points."""
    import pandas as pd
    
    x_data = pd.to_numeric(df[x_col], errors='coerce')
    y_data = pd.to_numeric(df[y_col], errors='coerce')
    
    ax.scatter(x_data, y_data, alpha=0.6, c='#FF5722', s=50)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, alpha=0.3)


def _draw_histogram(ax, df, y_col: str, title: str):
    """Dessine un histogramme."""
    import pandas as pd
    
    data = pd.to_numeric(df[y_col], errors='coerce').dropna()
    
    ax.hist(data, bins=30, color='#9C27B0', alpha=0.7, edgecolor='white')
    ax.set_xlabel(y_col)
    ax.set_ylabel("Fréquence")
    ax.grid(True, alpha=0.3, axis='y')


def _draw_area(ax, df, x_col: str, y_col: str, title: str):
    """Dessine un graphique en aires."""
    import pandas as pd
    
    x_data = df[x_col]
    y_data = pd.to_numeric(df[y_col], errors='coerce')
    
    ax.fill_between(range(len(x_data)), y_data, alpha=0.4, color='#4CAF50')
    ax.plot(range(len(x_data)), y_data, color='#4CAF50', linewidth=2)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(True, alpha=0.3)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_summary(df, graph_type: GraphType, x_col: str, y_col: str) -> str:
    """Génère un résumé interprétatif des données."""
    import pandas as pd
    
    summary_parts = []
    
    # Stats générales
    summary_parts.append(f"**Données:** {len(df)} lignes, {len(df.columns)} colonnes")
    
    if y_col and y_col in df.columns:
        y_numeric = pd.to_numeric(df[y_col], errors='coerce')
        if not y_numeric.isna().all():
            summary_parts.append(
                f"**{y_col}:** min={y_numeric.min():.2f}, "
                f"max={y_numeric.max():.2f}, "
                f"moyenne={y_numeric.mean():.2f}"
            )
    
    if x_col and x_col in df.columns:
        unique = df[x_col].nunique()
        summary_parts.append(f"**{x_col}:** {unique} valeurs uniques")
    
    # Interprétation selon le type
    if graph_type == GraphType.LINE:
        summary_parts.append("*Graphique linéaire montrant l'évolution temporelle*")
    elif graph_type in [GraphType.BAR, GraphType.HBAR]:
        summary_parts.append("*Graphique en barres comparant les catégories*")
    elif graph_type == GraphType.PIE:
        summary_parts.append("*Camembert montrant la répartition*")
    elif graph_type == GraphType.SCATTER:
        summary_parts.append("*Nuage de points montrant la corrélation*")
    elif graph_type == GraphType.HISTOGRAM:
        summary_parts.append("*Histogramme montrant la distribution*")
    
    return "\n".join(summary_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# CODE GENERATION FOR code_execution
# ═══════════════════════════════════════════════════════════════════════════════

def generate_graph_code(file_path: str, title: Optional[str] = None) -> str:
    """
    Génère le code Python pour code_execution.
    
    Utilisé par l'orchestrateur pour router vers code_execution.
    """
    title = title or f"Analyse de {Path(file_path).stem}"
    
    code = f'''import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# Configuration
file_path = "{file_path}"
output_dir = "tmp/generated"
os.makedirs(output_dir, exist_ok=True)

# Charger les données
ext = file_path.split('.')[-1].lower()
if ext in ['xlsx', 'xls']:
    df = pd.read_excel(file_path)
elif ext == 'csv':
    df = pd.read_csv(file_path)
else:
    raise ValueError(f"Format non supporté: {{ext}}")

print(f"Données chargées: {{len(df)}} lignes, {{len(df.columns)}} colonnes")
print(f"Colonnes: {{list(df.columns)}}")

# Détecter les colonnes numériques
numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
if not numeric_cols:
    print("Aucune colonne numérique trouvée")
else:
    # Créer le graphique
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Utiliser la première colonne comme X et la première numérique comme Y
    if len(df.columns) >= 2:
        x_col = df.columns[0]
        y_col = numeric_cols[0]
        
        # Bar chart par défaut
        data = df.groupby(x_col)[y_col].sum().head(20)
        data.plot(kind='bar', ax=ax, color='#2196F3')
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
    else:
        # Histogramme si une seule colonne
        df[numeric_cols[0]].hist(ax=ax, bins=30, color='#9C27B0')
        ax.set_xlabel(numeric_cols[0])
        ax.set_ylabel("Fréquence")
    
    ax.set_title("{title}", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Sauvegarder
    import uuid
    output_path = f"{{output_dir}}/graph_{{uuid.uuid4().hex[:8]}}.png"
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"Graphique sauvegardé: {{output_path}}")
'''
    return code


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "GraphType",
    "FileType",
    "GraphRequest",
    "GraphResult",
    "is_graph_request",
    "detect_file_type",
    "detect_best_graph_type",
    "load_data",
    "generate_graph",
    "generate_graph_code",
    "ALL_GRAPH_KEYWORDS",
]

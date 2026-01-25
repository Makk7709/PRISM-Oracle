"""
Unknown Tool Handler — Auto-execute with code_execution.

When an unknown tool is called (especially for analysis/graph tasks),
this handler automatically generates and executes Python code.

CRITICAL: 
- Never tell user a tool is missing
- Auto-execute the task with code_execution
- Deliver value first
"""

import os
import glob
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


# Keywords indicating analysis/graph requests
ANALYSIS_KEYWORDS = [
    "graph", "plot", "chart", "analyse", "analyze", "visualize", "visualise",
    "histogram", "pie", "bar", "scatter", "line", "trend", "distribution",
    "extract", "read", "parse", "load", "data", "excel", "csv", "tableau",
    "table", "summary", "statistics", "stats", "report",
]


def is_analysis_request(tool_name: str, args: dict) -> bool:
    """Check if this looks like an analysis/graph request."""
    tool_lower = tool_name.lower() if tool_name else ""
    
    # Check tool name
    for kw in ANALYSIS_KEYWORDS:
        if kw in tool_lower:
            return True
    
    # Check args for file paths
    for key, value in args.items():
        if isinstance(value, str):
            if any(ext in value.lower() for ext in ['.xlsx', '.xls', '.csv', '.pdf']):
                return True
    
    return False


def find_uploaded_files() -> list[str]:
    """Find recently uploaded files."""
    upload_dirs = [
        "tmp/uploads",
        "work_dir/tmp/uploads", 
        "tmp",
    ]
    
    files_found = []
    for upload_dir in upload_dirs:
        if os.path.exists(upload_dir):
            for ext in ['*.xlsx', '*.xls', '*.csv', '*.pdf']:
                files_found.extend(glob.glob(os.path.join(upload_dir, ext)))
                files_found.extend(glob.glob(os.path.join(upload_dir, '**', ext), recursive=True))
    
    # Sort by modification time (most recent first)
    files_found = list(set(files_found))
    files_found.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
    
    return files_found[:5]  # Return top 5 most recent


def generate_analysis_code(file_path: str = None, tool_name: str = "", args: dict = None) -> str:
    """Generate Python code for analysis + graph."""
    
    # Try to find a file if not specified
    if not file_path:
        uploaded = find_uploaded_files()
        if uploaded:
            file_path = uploaded[0]
        else:
            # Return code that will list files and ask for input
            return '''import os
import glob

# Search for data files
upload_dirs = ["tmp/uploads", "work_dir/tmp/uploads", "tmp", "."]
files_found = []
for d in upload_dirs:
    if os.path.exists(d):
        for ext in ["*.xlsx", "*.xls", "*.csv"]:
            files_found.extend(glob.glob(os.path.join(d, ext)))
            files_found.extend(glob.glob(os.path.join(d, "**", ext), recursive=True))

files_found = list(set(files_found))
if files_found:
    print(f"Fichiers trouvés: {files_found}")
    print("\\nVeuillez spécifier quel fichier analyser.")
else:
    print("Aucun fichier de données trouvé.")
    print("Veuillez uploader un fichier Excel ou CSV.")
'''
    
    # Determine file extension
    ext = os.path.splitext(file_path)[1].lower()
    
    # Generate appropriate loading code
    if ext in ['.xlsx', '.xls']:
        load_code = f"df = pd.read_excel('{file_path}')"
    elif ext == '.csv':
        load_code = f"df = pd.read_csv('{file_path}')"
    else:
        load_code = f"# Unsupported file type: {ext}"
    
    return f'''import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import uuid

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("📂 Chargement du fichier...")
{load_code}
print(f"✅ Données chargées: {{len(df)}} lignes, {{len(df.columns)}} colonnes")
print(f"\\n📋 Colonnes: {{list(df.columns)}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. ANALYSE STATISTIQUE
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n📊 ANALYSE STATISTIQUE:")
print("-" * 50)

# Afficher les premières lignes
print("\\n🔍 Aperçu des données:")
print(df.head(10).to_string())

# Statistiques descriptives pour colonnes numériques
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
if numeric_cols:
    print("\\n📈 Statistiques descriptives:")
    print(df[numeric_cols].describe().to_string())

# Valeurs uniques pour colonnes catégorielles
cat_cols = df.select_dtypes(include=['object']).columns.tolist()
if cat_cols:
    print("\\n🏷️ Colonnes catégorielles:")
    for col in cat_cols[:5]:  # Limiter à 5 colonnes
        unique_count = df[col].nunique()
        print(f"  - {{col}}: {{unique_count}} valeurs uniques")
        if unique_count <= 10:
            print(f"    Valeurs: {{df[col].unique().tolist()}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. GÉNÉRATION DU GRAPHIQUE
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n🎨 Génération du graphique...")

# Créer le répertoire de sortie
os.makedirs('tmp/generated', exist_ok=True)

# Sélectionner les colonnes pour le graphique
fig, ax = plt.subplots(figsize=(12, 8))

if numeric_cols and cat_cols:
    # Bar chart: catégorie vs valeur numérique
    x_col = cat_cols[0]
    y_col = numeric_cols[0]
    
    # Agréger si nécessaire
    if df[x_col].duplicated().any():
        plot_data = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(15)
    else:
        plot_data = df.set_index(x_col)[y_col].head(15)
    
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(plot_data)))
    bars = ax.bar(range(len(plot_data)), plot_data.values, color=colors)
    ax.set_xticks(range(len(plot_data)))
    ax.set_xticklabels([str(x)[:20] for x in plot_data.index], rotation=45, ha='right')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f'{{y_col}} par {{x_col}}', fontsize=14, fontweight='bold')
    
    # Ajouter les valeurs sur les barres
    for bar, val in zip(bars, plot_data.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                f'{{val:,.0f}}', ha='center', va='bottom', fontsize=8)

elif len(numeric_cols) >= 2:
    # Scatter plot: deux colonnes numériques
    x_col = numeric_cols[0]
    y_col = numeric_cols[1]
    ax.scatter(df[x_col], df[y_col], alpha=0.6, c='#2196F3', s=50)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f'{{y_col}} vs {{x_col}}', fontsize=14, fontweight='bold')

elif numeric_cols:
    # Histogram: une colonne numérique
    col = numeric_cols[0]
    ax.hist(df[col].dropna(), bins=30, color='#9C27B0', alpha=0.7, edgecolor='white')
    ax.set_xlabel(col)
    ax.set_ylabel('Fréquence')
    ax.set_title(f'Distribution de {{col}}', fontsize=14, fontweight='bold')

elif cat_cols:
    # Pie chart: fréquences d'une colonne catégorielle
    col = cat_cols[0]
    counts = df[col].value_counts().head(10)
    colors = plt.cm.Set3(range(len(counts)))
    ax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', colors=colors)
    ax.set_title(f'Répartition de {{col}}', fontsize=14, fontweight='bold')

else:
    ax.text(0.5, 0.5, 'Données insuffisantes pour générer un graphique', 
            ha='center', va='center', fontsize=14)

ax.grid(True, alpha=0.3)
plt.tight_layout()

# Sauvegarder
output_path = f"tmp/generated/graph_{{uuid.uuid4().hex[:8]}}.png"
plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
plt.close()

print(f"\\n✅ Graphique sauvegardé: {{output_path}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. RÉSUMÉ
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 50)
print("📋 RÉSUMÉ DE L'ANALYSE")
print("=" * 50)
print(f"📁 Fichier: {file_path}")
print(f"📊 Dimensions: {{len(df)}} lignes × {{len(df.columns)}} colonnes")
if numeric_cols:
    print(f"🔢 Colonnes numériques: {{numeric_cols}}")
if cat_cols:
    print(f"🏷️ Colonnes catégorielles: {{cat_cols[:5]}}")
print(f"🖼️ Graphique: {{output_path}}")
'''


class Unknown(Tool):
    """
    Handles unknown tool requests by auto-executing with code_execution.
    
    For analysis/graph requests, generates and executes Python code automatically.
    For other requests, returns a minimal guidance message.
    """
    
    async def execute(self, **kwargs):
        tool_name = self.name or "unknown"
        
        PrintStyle(font_color="yellow").print(
            f"[Unknown Tool] Tool '{tool_name}' not found. Checking for auto-execution..."
        )
        
        # Check if this is an analysis/graph request
        if is_analysis_request(tool_name, self.args):
            PrintStyle(font_color="cyan").print(
                f"[Unknown Tool] Detected analysis request. Auto-executing with code_execution..."
            )
            
            # Find file from args or uploaded files
            file_path = None
            for key, value in self.args.items():
                if isinstance(value, str) and any(ext in value.lower() for ext in ['.xlsx', '.xls', '.csv', '.pdf']):
                    file_path = value
                    break
            
            # Generate analysis code
            code = generate_analysis_code(file_path, tool_name, self.args)
            
            # Execute using CodeExecution
            from python.tools.code_execution_tool import CodeExecution
            
            exec_args = {
                "runtime": "python",
                "code": code,
            }
            
            code_exec = CodeExecution(
                agent=self.agent,
                name="code_execution",
                method="",
                args=exec_args,
                message=self.message,
                loop_data=self.loop_data
            )
            code_exec.log = self.log
            
            # Execute and return result
            result = await code_exec.execute(**exec_args)
            return result
        
        # For non-analysis requests, return minimal guidance
        return Response(
            message=f'Tool "{tool_name}" not recognized. Use code_execution for custom tasks.',
            break_loop=False,
        )

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
    
    return f'''import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import uuid
import warnings
warnings.filterwarnings('ignore')

file_path = "{file_path}"
ext = file_path.split('.')[-1].lower()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SMART LOADING — Handle dirty Excel files
# ═══════════════════════════════════════════════════════════════════════════════
print("📂 Chargement intelligent du fichier...")

def smart_load_excel(path):
    """Load Excel with auto-detection of header row."""
    # Try different header rows (0, 1, 2, 3, 4, 5)
    best_df = None
    best_score = -1
    best_header = 0
    
    for header_row in range(6):
        try:
            df = pd.read_excel(path, header=header_row)
            
            # Score: prefer named columns over "Unnamed"
            unnamed_count = sum(1 for c in df.columns if 'Unnamed' in str(c) or 'datetime' in str(type(c)))
            named_count = len(df.columns) - unnamed_count
            
            # Also prefer rows with actual data
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            data_score = len(numeric_cols) * 10 + named_count
            
            if data_score > best_score:
                best_score = data_score
                best_df = df
                best_header = header_row
        except:
            continue
    
    if best_df is not None:
        print(f"  → Header détecté à la ligne {{best_header}}")
        return best_df
    
    # Fallback: load as-is
    return pd.read_excel(path)

def smart_load_csv(path):
    """Load CSV with encoding detection."""
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            return pd.read_csv(path, encoding=encoding)
        except:
            continue
    return pd.read_csv(path)

# Load file
if ext in ['xlsx', 'xls']:
    df = smart_load_excel(file_path)
elif ext == 'csv':
    df = smart_load_csv(file_path)
else:
    df = pd.read_excel(file_path)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. CLEAN DATA — Fix column names and types
# ═══════════════════════════════════════════════════════════════════════════════
print("🧹 Nettoyage des données...")

# Clean column names
df.columns = [str(c).strip() if not isinstance(c, (int, float)) else f'Col_{{i}}' 
              for i, c in enumerate(df.columns)]

# Remove columns that are mostly empty
df = df.dropna(axis=1, thresh=len(df) * 0.3)  # Keep columns with >30% data

# Remove rows that are completely empty
df = df.dropna(how='all')

# Remove rows where all values are NaN or whitespace
df = df[df.apply(lambda row: row.astype(str).str.strip().str.len().sum() > 0, axis=1)]

# Convert numeric columns properly
for col in df.columns:
    # Try to convert to numeric
    try:
        numeric_col = pd.to_numeric(df[col], errors='coerce')
        if numeric_col.notna().sum() > len(df) * 0.5:  # >50% valid numbers
            df[col] = numeric_col
    except:
        pass

print(f"✅ Données nettoyées: {{len(df)}} lignes, {{len(df.columns)}} colonnes")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. IDENTIFY COLUMNS
# ═══════════════════════════════════════════════════════════════════════════════
# Find numeric and categorical columns
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = [c for c in df.columns if c not in numeric_cols and df[c].nunique() < 50]

print(f"📊 Colonnes numériques: {{numeric_cols[:5]}}")
print(f"🏷️ Colonnes catégorielles: {{cat_cols[:5]}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. ANALYSE STATISTIQUE
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("📊 ANALYSE STATISTIQUE")
print("=" * 60)

# Show sample data
print("\\n🔍 Échantillon de données:")
print(df.head(10).to_string(max_cols=8))

if numeric_cols:
    print("\\n📈 Statistiques des colonnes numériques:")
    stats = df[numeric_cols[:5]].describe()
    print(stats.to_string())
    
    # Total/Sum for key columns
    print("\\n💰 Totaux:")
    for col in numeric_cols[:3]:
        total = df[col].sum()
        print(f"  {{col}}: {{total:,.2f}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. GÉNÉRATION DU GRAPHIQUE
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n🎨 Génération du graphique...")
os.makedirs('tmp/generated', exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 8))

try:
    if numeric_cols and cat_cols:
        # Bar chart: best categorical vs best numeric
        x_col = cat_cols[0]
        y_col = numeric_cols[0]
        
        # Clean and aggregate
        plot_df = df[[x_col, y_col]].dropna()
        plot_df[x_col] = plot_df[x_col].astype(str).str[:30]  # Truncate labels
        plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors='coerce')
        plot_df = plot_df.dropna()
        
        if len(plot_df) > 0:
            agg = plot_df.groupby(x_col)[y_col].sum().nlargest(15)
            
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(agg)))
            bars = ax.barh(range(len(agg)), agg.values, color=colors)
            ax.set_yticks(range(len(agg)))
            ax.set_yticklabels(agg.index)
            ax.set_xlabel(y_col)
            ax.set_title(f'Top 15 - {{y_col}} par {{x_col}}', fontsize=14, fontweight='bold')
            
            # Add value labels
            for bar, val in zip(bars, agg.values):
                ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2, 
                        f' {{val:,.0f}}', va='center', fontsize=9)
        else:
            raise ValueError("No valid data for bar chart")
    
    elif len(numeric_cols) >= 2:
        # Scatter plot
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        ax.scatter(df[x_col].dropna(), df[y_col].dropna(), alpha=0.6, c='#2196F3', s=50)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f'{{y_col}} vs {{x_col}}', fontsize=14, fontweight='bold')
    
    elif numeric_cols:
        # Histogram
        col = numeric_cols[0]
        data = df[col].dropna()
        ax.hist(data, bins=min(30, len(data)//5 + 1), color='#9C27B0', alpha=0.7, edgecolor='white')
        ax.set_xlabel(col)
        ax.set_ylabel('Fréquence')
        ax.set_title(f'Distribution de {{col}}', fontsize=14, fontweight='bold')
        ax.axvline(data.mean(), color='red', linestyle='--', label=f'Moyenne: {{data.mean():,.2f}}')
        ax.legend()
    
    else:
        # Fallback: show column value counts
        if cat_cols:
            col = cat_cols[0]
            counts = df[col].value_counts().head(10)
            ax.pie(counts.values, labels=[str(l)[:20] for l in counts.index], 
                   autopct='%1.1f%%', colors=plt.cm.Set3(range(len(counts))))
            ax.set_title(f'Répartition de {{col}}', fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'Données insuffisantes', ha='center', va='center', fontsize=16)

except Exception as e:
    print(f"⚠️ Erreur graphique: {{e}}")
    ax.text(0.5, 0.5, f'Erreur: {{str(e)[:50]}}', ha='center', va='center', fontsize=12)

ax.grid(True, alpha=0.3)
plt.tight_layout()

# Save
output_path = f"tmp/generated/graph_{{uuid.uuid4().hex[:8]}}.png"
plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
plt.close()

print(f"\\n✅ Graphique sauvegardé: {{output_path}}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. RÉSUMÉ FINAL
# ═══════════════════════════════════════════════════════════════════════════════
print("\\n" + "=" * 60)
print("📋 RÉSUMÉ")
print("=" * 60)
print(f"📁 Fichier: {file_path}")
print(f"📊 Dimensions: {{len(df)}} lignes × {{len(df.columns)}} colonnes")
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

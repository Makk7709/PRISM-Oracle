## GRAPH POLICY (MANDATORY)

When user requests a graph, chart, plot, visualization, or any visual data representation:

### REQUIRED: Use code_execution

```json
{
    "tool_name": "code_execution",
    "tool_args": {
        "runtime": "python",
        "code": "..."
    }
}
```

### Standard Template

```python
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# 1. Load data
file_path = "tmp/uploads/YOUR_FILE.xlsx"  # or .csv
ext = file_path.split('.')[-1].lower()
if ext in ['xlsx', 'xls']:
    df = pd.read_excel(file_path)
else:
    df = pd.read_csv(file_path)

print(f"Data loaded: {len(df)} rows, {len(df.columns)} columns")
print(f"Columns: {list(df.columns)}")

# 2. Prepare data
numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
x_col = df.columns[0]
y_col = numeric_cols[0] if numeric_cols else df.columns[1]

# 3. Create figure
fig, ax = plt.subplots(figsize=(12, 8))

# 4. Plot (choose appropriate type)
# Bar chart:
df.groupby(x_col)[y_col].sum().head(20).plot(kind='bar', ax=ax, color='#2196F3')
# OR Line chart:
# ax.plot(df[x_col], df[y_col], marker='o', linewidth=2)
# OR Pie chart:
# df[x_col].value_counts().head(10).plot(kind='pie', ax=ax, autopct='%1.1f%%')

ax.set_title("Your Title", fontsize=14, fontweight='bold')
ax.set_xlabel(x_col)
ax.set_ylabel(y_col)
ax.grid(True, alpha=0.3)
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# 5. Save
os.makedirs('tmp/generated', exist_ok=True)
import uuid
output_path = f"tmp/generated/graph_{uuid.uuid4().hex[:8]}.png"
plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
plt.close()

print(f"✅ Graph saved: {output_path}")
```

### RULES

1. **NEVER** call a "graph" or "chart" tool - they don't exist
2. **ALWAYS** use code_execution with matplotlib
3. **NEVER** tell user "tool not found" - just generate the graph
4. **ALWAYS** save to tmp/generated/
5. **ALWAYS** print the output path

### Auto-select Chart Type

| Data Pattern | Chart Type |
|-------------|------------|
| Date/time + values | Line chart |
| Categories + values | Bar chart |
| Categories only | Pie chart |
| 2 numeric columns | Scatter plot |
| 1 numeric column | Histogram |
| Many categories (>10) | Horizontal bar |

### Keywords that trigger Graph Policy

FR: graph, graphique, courbe, camembert, histogramme, barres, nuage, scatter, évolution, tendance, répartition, distribution, visualisation
EN: graph, chart, plot, curve, pie, histogram, bar, scatter, trend, distribution, figure, diagram, visualize

"""
KOREV Evidence — Generateur automatique de graphiques PRISM pour dossiers strategiques.

Parse les tables markdown des dossiers consolides et genere des graphiques
matplotlib avec la charte graphique PRISM (couleurs Evidence, typographie, branding).

Types de graphiques auto-detectes :
- Projections financieres (colonnes annees) → line chart
- TAM/SAM/SOM → waterfall bar
- Benchmark concurrentiel → horizontal bar
- Scenarios (Base/Pessimiste/Optimiste) → grouped bar
- Repartition / parts de marche → donut chart
- Evolution temporelle → area chart

Usage:
    from python.helpers.strategic_charts import generate_charts_from_markdown

    charts = generate_charts_from_markdown(markdown_content, output_dir="/tmp/charts")
    # Returns list of ChartOutput with image paths + insertion points
"""

import base64
import hashlib
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("strategic_charts")

# ═══════════════════════════════════════════════════════════════════════════════
# PRISM DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════════════

PRISM_COLORS = [
    "#4A7CFF",  # accent
    "#38A169",  # green
    "#E53E3E",  # red
    "#D69E2E",  # amber
    "#805AD5",  # purple
    "#DD6B20",  # orange
    "#319795",  # teal
    "#D53F8C",  # pink
]

PRISM_DARK = "#0D1117"
PRISM_TEXT = "#1A1D23"
PRISM_TEXT_SECONDARY = "#4A5568"
PRISM_BORDER = "#E2E8F0"
PRISM_BG = "#FAFBFC"
PRISM_ACCENT = "#4A7CFF"


class ChartKind(str, Enum):
    LINE = "line"
    BAR = "bar"
    HORIZONTAL_BAR = "hbar"
    STACKED_BAR = "stacked_bar"
    DONUT = "donut"
    AREA = "area"
    WATERFALL = "waterfall"


@dataclass
class ParsedTable:
    """A markdown table parsed into structured data."""
    headers: List[str]
    rows: List[List[str]]
    raw_markdown: str
    section_title: str = ""
    line_index: int = 0


@dataclass
class ChartOutput:
    """Result of chart generation."""
    image_path: str
    image_bytes: bytes
    chart_kind: ChartKind
    title: str
    table_line_index: int
    width_px: int = 800
    height_px: int = 400

    @property
    def base64_png(self) -> str:
        return base64.b64encode(self.image_bytes).decode("ascii")

    @property
    def html_img_tag(self) -> str:
        return (
            f'<div style="text-align:center;margin:16px 0;">'
            f'<img src="data:image/png;base64,{self.base64_png}" '
            f'style="max-width:100%;height:auto;" alt="{self.title}"/>'
            f'</div>'
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MATPLOTLIB PRISM STYLE
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_prism_style():
    """Configure matplotlib with PRISM design tokens."""
    import matplotlib.pyplot as plt
    import matplotlib

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": PRISM_BORDER,
        "axes.labelcolor": PRISM_TEXT,
        "axes.titlecolor": PRISM_TEXT,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": PRISM_BORDER,
        "grid.alpha": 0.5,
        "grid.linewidth": 0.5,
        "xtick.color": PRISM_TEXT_SECONDARY,
        "ytick.color": PRISM_TEXT_SECONDARY,
        "text.color": PRISM_TEXT,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.15,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN TABLE PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_markdown_tables(markdown: str) -> List[ParsedTable]:
    """Extract all markdown tables with their context."""
    lines = markdown.split("\n")
    tables = []
    i = 0
    current_section = ""

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("## ") or line.startswith("### "):
            current_section = line.lstrip("#").strip()

        if line.startswith("|") and "|" in line[1:]:
            table_start = i
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 3:
                headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                rows = []
                for tl in table_lines[2:]:
                    cells = [c.strip() for c in tl.strip("|").split("|")]
                    if cells and not all(set(c) <= {"-", ":", " "} for c in cells):
                        rows.append(cells)

                if headers and rows:
                    tables.append(ParsedTable(
                        headers=headers,
                        rows=rows,
                        raw_markdown="\n".join(table_lines),
                        section_title=current_section,
                        line_index=table_start,
                    ))
            continue

        i += 1

    return tables


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE CLASSIFICATION & NUMERIC EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

_YEAR_RE = re.compile(r"20[2-3]\d")
_NUM_RE = re.compile(r"[\d,.]+")
_CURRENCY_RE = re.compile(r"[\d,.]+\s*(?:M|Mds?|K|B)?\s*(?:EUR|€|\$|USD)", re.IGNORECASE)
_PERCENT_RE = re.compile(r"[\d,.]+\s*%")
_TAM_RE = re.compile(r"\bTAM\b|\bSAM\b|\bSOM\b", re.IGNORECASE)
_SCENARIO_RE = re.compile(r"\b(?:base|pessimiste|optimiste|conserv|agressif)\b", re.IGNORECASE)
_SWOT_RE = re.compile(r"\b(?:forces?|faiblesses?|opportunit|menaces?|strengths?|weakness|threats?)\b", re.IGNORECASE)
_SKIP_RE = re.compile(
    r"\b(?:correlation.id|parametre|valeur|type|mode|statut|claim|criticite)\b",
    re.IGNORECASE,
)


def _extract_number(cell: str) -> Optional[float]:
    """Extract a numeric value from a cell (handles M, Mds, K, %, etc.)."""
    cell = cell.strip().replace("\u202f", "").replace("\xa0", "")
    cell = cell.replace(",", ".")

    multiplier = 1.0
    if re.search(r"\bMds\b", cell, re.IGNORECASE):
        multiplier = 1_000_000_000
    elif re.search(r"\bM\b", cell):
        multiplier = 1_000_000
    elif re.search(r"\bK\b", cell, re.IGNORECASE):
        multiplier = 1_000
    elif re.search(r"\bB\b", cell, re.IGNORECASE):
        multiplier = 1_000_000_000

    if "%" in cell:
        match = re.search(r"(-?[\d.]+)\s*%", cell)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    match = re.search(r"(-?[\d.]+)", cell)
    if match:
        try:
            val = float(match.group(1))
            return val * multiplier if multiplier != 1.0 else val
        except ValueError:
            return None
    return None


def _classify_table(table: ParsedTable) -> Optional[Tuple[ChartKind, str]]:
    """Classify a table and decide what chart to generate.

    Returns (ChartKind, chart_title) or None if not chart-worthy.
    """
    header_text = " ".join(table.headers).lower()
    all_text = header_text + " " + " ".join(
        " ".join(r) for r in table.rows
    ).lower()

    if _SKIP_RE.search(header_text):
        return None

    year_cols = [h for h in table.headers if _YEAR_RE.search(h)]

    if len(year_cols) >= 2:
        numeric_rows = 0
        for row in table.rows:
            nums = [_extract_number(c) for c in row[1:] if _extract_number(c) is not None]
            if nums:
                numeric_rows += 1
        if numeric_rows >= 1:
            label = "TAM / SAM / SOM" if _TAM_RE.search(all_text) else "Projections"
            return (ChartKind.LINE, f"{label} — {table.section_title}")

    if _TAM_RE.search(all_text) and len(table.rows) >= 2:
        return (ChartKind.BAR, f"TAM / SAM / SOM — {table.section_title}")

    if _SCENARIO_RE.search(all_text):
        return (ChartKind.BAR, f"Analyse par scenarios — {table.section_title}")

    if _SWOT_RE.search(header_text):
        return None

    row_labels = [r[0] for r in table.rows if r]
    numeric_cols = 0
    for row in table.rows:
        for cell in row[1:]:
            if _extract_number(cell) is not None:
                numeric_cols += 1
                break

    if numeric_cols >= 2 and len(table.rows) >= 3:
        return (ChartKind.HORIZONTAL_BAR, f"Comparatif — {table.section_title}")

    if len(table.rows) >= 3 and numeric_cols >= 1:
        return (ChartKind.BAR, table.section_title or "Donnees")

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# CHART GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_line_chart(table: ParsedTable, title: str, output_path: str) -> Optional[bytes]:
    """Generate a line chart from a table with year columns."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _apply_prism_style()

    year_indices = []
    year_labels = []
    for idx, h in enumerate(table.headers):
        if _YEAR_RE.search(h):
            year_indices.append(idx)
            year_labels.append(h.strip())

    if len(year_indices) < 2:
        return None

    fig, ax = plt.subplots(figsize=(8, 4.5))

    plotted = 0
    for row in table.rows:
        label = row[0].strip() if row else "?"
        values = []
        valid = True
        for yi in year_indices:
            if yi < len(row):
                val = _extract_number(row[yi])
                if val is not None:
                    values.append(val)
                else:
                    valid = False
                    break
            else:
                valid = False
                break

        if valid and values and plotted < 6:
            color = PRISM_COLORS[plotted % len(PRISM_COLORS)]
            ax.plot(year_labels, values, marker="o", linewidth=2.5,
                    markersize=7, label=label, color=color)

            for xi, v in enumerate(values):
                fmt = f"{v:,.0f}" if v >= 100 else f"{v:.1f}"
                ax.annotate(fmt, (year_labels[xi], v),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=8, color=color)
            plotted += 1

    if plotted == 0:
        plt.close(fig)
        return None

    ax.set_title(title, pad=12)
    if plotted > 1:
        ax.legend(loc="upper left", framealpha=0.9)

    fig.savefig(output_path, format="png")
    with open(output_path, "rb") as f:
        data = f.read()
    plt.close(fig)
    return data


def _generate_bar_chart(table: ParsedTable, title: str, output_path: str) -> Optional[bytes]:
    """Generate a vertical bar chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _apply_prism_style()

    labels = [r[0].strip() for r in table.rows if r]

    num_col_idx = None
    for ci in range(1, len(table.headers)):
        has_nums = sum(
            1 for r in table.rows
            if ci < len(r) and _extract_number(r[ci]) is not None
        )
        if has_nums >= len(table.rows) * 0.5:
            num_col_idx = ci
            break

    if num_col_idx is None:
        return None

    values = []
    valid_labels = []
    for row in table.rows:
        if num_col_idx < len(row):
            val = _extract_number(row[num_col_idx])
            if val is not None:
                values.append(val)
                valid_labels.append(row[0].strip())

    if len(values) < 2:
        return None

    fig, ax = plt.subplots(figsize=(max(6, len(values) * 1.2), 4.5))

    colors = [PRISM_COLORS[i % len(PRISM_COLORS)] for i in range(len(values))]
    bars = ax.bar(valid_labels, values, color=colors, width=0.6, edgecolor="white", linewidth=0.5)

    for bar, val in zip(bars, values):
        fmt = f"{val:,.0f}" if abs(val) >= 100 else f"{val:.1f}"
        ax.annotate(fmt, (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=9, fontweight="bold",
                    xytext=(0, 4), textcoords="offset points")

    ax.set_title(title, pad=12)
    if table.headers and num_col_idx < len(table.headers):
        ax.set_ylabel(table.headers[num_col_idx])

    plt.xticks(rotation=30 if max(len(l) for l in valid_labels) > 12 else 0, ha="right")

    fig.savefig(output_path, format="png")
    with open(output_path, "rb") as f:
        data = f.read()
    plt.close(fig)
    return data


def _generate_hbar_chart(table: ParsedTable, title: str, output_path: str) -> Optional[bytes]:
    """Generate a horizontal bar chart for comparisons."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _apply_prism_style()

    labels = [r[0].strip() for r in table.rows if r]

    all_series = []
    for ci in range(1, len(table.headers)):
        values = []
        valid = True
        for row in table.rows:
            if ci < len(row):
                val = _extract_number(row[ci])
                if val is not None:
                    values.append(val)
                else:
                    valid = False
                    break
            else:
                valid = False
                break
        if valid and values:
            all_series.append((table.headers[ci].strip(), values))

    if not all_series:
        return None

    fig, ax = plt.subplots(figsize=(8, max(3, len(labels) * 0.6 + 1)))

    if len(all_series) == 1:
        name, values = all_series[0]
        y_pos = np.arange(len(labels))
        colors = [PRISM_COLORS[i % len(PRISM_COLORS)] for i in range(len(values))]
        bars = ax.barh(y_pos, values, color=colors, height=0.5, edgecolor="white")

        for bar, val in zip(bars, values):
            fmt = f"{val:,.0f}" if abs(val) >= 100 else f"{val:.1f}"
            ax.annotate(fmt, (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                        ha="left", va="center", fontsize=9, fontweight="bold",
                        xytext=(4, 0), textcoords="offset points")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel(name)
    else:
        y_pos = np.arange(len(labels))
        bar_h = 0.8 / len(all_series)
        for si, (name, values) in enumerate(all_series):
            offset = bar_h * (si - len(all_series) / 2 + 0.5)
            color = PRISM_COLORS[si % len(PRISM_COLORS)]
            ax.barh(y_pos + offset, values, bar_h, label=name, color=color)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.legend(loc="lower right")

    ax.set_title(title, pad=12)
    ax.invert_yaxis()

    fig.savefig(output_path, format="png")
    with open(output_path, "rb") as f:
        data = f.read()
    plt.close(fig)
    return data


def _generate_donut_chart(table: ParsedTable, title: str, output_path: str) -> Optional[bytes]:
    """Generate a donut chart for proportional data."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _apply_prism_style()

    labels = []
    values = []
    for row in table.rows:
        if len(row) >= 2:
            val = _extract_number(row[1])
            if val is not None and val > 0:
                labels.append(row[0].strip())
                values.append(val)

    if len(values) < 2:
        return None

    fig, ax = plt.subplots(figsize=(6, 5))
    colors = [PRISM_COLORS[i % len(PRISM_COLORS)] for i in range(len(values))]

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=colors, pctdistance=0.78,
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )

    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")

    ax.set_title(title, pad=16)

    fig.savefig(output_path, format="png")
    with open(output_path, "rb") as f:
        data = f.read()
    plt.close(fig)
    return data


_GENERATORS = {
    ChartKind.LINE: _generate_line_chart,
    ChartKind.BAR: _generate_bar_chart,
    ChartKind.HORIZONTAL_BAR: _generate_hbar_chart,
    ChartKind.STACKED_BAR: _generate_bar_chart,
    ChartKind.DONUT: _generate_donut_chart,
    ChartKind.AREA: _generate_line_chart,
    ChartKind.WATERFALL: _generate_bar_chart,
}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_charts_from_markdown(
    markdown: str,
    output_dir: Optional[str] = None,
) -> List[ChartOutput]:
    """Parse markdown content and generate PRISM-styled charts for chart-worthy tables.

    Args:
        markdown: Full markdown content of the strategic dossier
        output_dir: Directory for temp chart images (auto-created if None)

    Returns:
        List of ChartOutput with image bytes and insertion metadata
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        logger.warning("matplotlib not available — skipping chart generation")
        return []

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="evidence_charts_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    tables = _parse_markdown_tables(markdown)
    charts: List[ChartOutput] = []

    for table in tables:
        classification = _classify_table(table)
        if classification is None:
            continue

        kind, title = classification
        generator = _GENERATORS.get(kind)
        if generator is None:
            continue

        table_hash = hashlib.md5(table.raw_markdown.encode()).hexdigest()[:8]
        filename = f"chart_{kind.value}_{table_hash}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            image_bytes = generator(table, title, filepath)
            if image_bytes:
                charts.append(ChartOutput(
                    image_path=filepath,
                    image_bytes=image_bytes,
                    chart_kind=kind,
                    title=title,
                    table_line_index=table.line_index,
                ))
                logger.info(
                    f"Chart generated: {kind.value} — {title} ({len(image_bytes)} bytes)"
                )
        except Exception as exc:
            logger.warning(f"Chart generation failed for {kind.value}: {exc}")

    logger.info(f"Generated {len(charts)} charts from {len(tables)} tables")
    return charts


def inject_charts_into_html(html: str, charts: List[ChartOutput]) -> str:
    """Inject base64 chart images into HTML content after their source tables.

    Used by the WeasyPrint rendering path.
    """
    if not charts:
        return html

    for chart in reversed(charts):
        table_end_pattern = re.compile(r"(</table>)", re.IGNORECASE)
        matches = list(table_end_pattern.finditer(html))

        if matches:
            best_match = None
            for m in matches:
                preceding = html[:m.start()]
                if chart.title.split("—")[0].strip().lower() in preceding[-500:].lower():
                    best_match = m
                    break

            if best_match is None and matches:
                table_count = len(matches)
                chart_table_approx = min(
                    chart.table_line_index,
                    table_count - 1,
                )
                if chart_table_approx < len(matches):
                    best_match = matches[chart_table_approx]

            if best_match:
                insert_pos = best_match.end()
                html = html[:insert_pos] + "\n" + chart.html_img_tag + "\n" + html[insert_pos:]

    return html


def inject_charts_into_markdown(markdown: str, charts: List[ChartOutput]) -> str:
    """Inject chart image references into markdown after their source tables.

    Used by the ReportLab rendering path — inserts <!--CHART:path--> markers.
    """
    if not charts:
        return markdown

    lines = markdown.split("\n")

    sorted_charts = sorted(charts, key=lambda c: c.table_line_index, reverse=True)

    for chart in sorted_charts:
        insert_line = chart.table_line_index
        while insert_line < len(lines) and lines[insert_line].strip().startswith("|"):
            insert_line += 1

        marker = f"<!--CHART:{chart.image_path}-->"
        lines.insert(insert_line, marker)

    return "\n".join(lines)

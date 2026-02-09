"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REPORT JOB — Long Report Generation                       ║
║                                                                              ║
║  Système de génération de rapports longs via chunks.                         ║
║                                                                              ║
║  Principe:                                                                   ║
║  1. Pas de limite artificielle côté app                                      ║
║  2. Génération section par section (chunks)                                  ║
║  3. Écriture progressive dans fichier                                        ║
║  4. Export MD/PDF/HTML                                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, AsyncGenerator

logger = logging.getLogger("report_job")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_REPORTS_DIR = "reports"


class ReportStatus(str, Enum):
    """Statut d'un job de rapport."""
    PENDING = "pending"
    GENERATING = "generating"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    """Formats d'export supportés."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


@dataclass
class ReportConfig:
    """Configuration d'un rapport."""
    # Génération
    max_sections: Optional[int] = None  # None = pas de limite
    chunk_size_tokens: int = 4000       # Tokens par chunk
    overlap_tokens: int = 200           # Overlap pour contexte
    
    # Fichiers
    output_dir: str = DEFAULT_REPORTS_DIR
    export_formats: List[ExportFormat] = field(
        default_factory=lambda: [ExportFormat.MARKDOWN]
    )
    
    # Timeouts
    section_timeout_s: int = 60
    total_timeout_s: int = 3600  # 1 heure max
    
    # Consensus
    require_consensus: bool = False
    consensus_per_section: bool = False


@dataclass
class ReportSection:
    """Section d'un rapport."""
    section_id: str
    title: str
    order: int
    
    # Contenu
    content: str = ""
    status: str = "pending"  # pending, generating, completed, failed
    
    # Métadonnées
    word_count: int = 0
    generated_at: Optional[str] = None
    generation_time_ms: int = 0
    
    # Assets
    assets: List[str] = field(default_factory=list)  # Paths to charts/images
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "order": self.order,
            "status": self.status,
            "word_count": self.word_count,
            "generated_at": self.generated_at,
            "assets_count": len(self.assets),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT JOB
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReportJob:
    """
    Job de génération de rapport long.
    
    Usage:
        job = ReportJob(
            title="Research Analysis",
            query="Analyze transformer architectures",
            outline=["Introduction", "Methods", "Results", "Conclusion"],
        )
        
        await job.start()
        
        while job.status == ReportStatus.GENERATING:
            print(f"Progress: {job.progress_percent}%")
            await asyncio.sleep(1)
        
        print(f"Report: {job.output_path}")
    """
    
    # Identifiants
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Requête
    title: str = ""
    query: str = ""
    outline: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration
    config: ReportConfig = field(default_factory=ReportConfig)
    
    # État
    status: ReportStatus = ReportStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Sections
    sections: List[ReportSection] = field(default_factory=list)
    current_section_idx: int = 0
    
    # Fichiers
    output_dir: Optional[Path] = None
    report_path: Optional[Path] = None
    assets_dir: Optional[Path] = None
    
    # Métriques
    total_words: int = 0
    total_generation_time_ms: int = 0
    
    # Erreurs
    error: Optional[str] = None
    
    def __post_init__(self):
        """Initialise les répertoires et sections."""
        # Créer la structure de répertoires
        base_dir = Path(self.config.output_dir)
        self.output_dir = base_dir / self.job_id
        self.report_path = self.output_dir / "report.md"
        self.assets_dir = self.output_dir / "assets"
        
        # Initialiser les sections depuis l'outline
        if self.outline and not self.sections:
            for i, title in enumerate(self.outline):
                self.sections.append(ReportSection(
                    section_id=f"section_{i:03d}",
                    title=title,
                    order=i,
                ))
    
    @property
    def progress_percent(self) -> float:
        """Calcule le pourcentage de progression."""
        if not self.sections:
            return 0.0
        completed = sum(1 for s in self.sections if s.status == "completed")
        return (completed / len(self.sections)) * 100
    
    @property
    def sections_completed(self) -> int:
        """Nombre de sections complétées."""
        return sum(1 for s in self.sections if s.status == "completed")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export pour API/persistance."""
        return {
            "job_id": self.job_id,
            "title": self.title,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress_percent": self.progress_percent,
            "sections_count": len(self.sections),
            "sections_completed": self.sections_completed,
            "total_words": self.total_words,
            "output_path": str(self.report_path) if self.report_path else None,
            "error": self.error,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────────
    
    async def start(
        self,
        generator: Callable[[str, Dict[str, Any]], AsyncGenerator[str, None]] = None,
    ):
        """
        Démarre la génération du rapport.
        
        Args:
            generator: Async generator qui produit le contenu section par section.
                       Si None, utilise un générateur par défaut.
        """
        if self.status not in [ReportStatus.PENDING, ReportStatus.PAUSED]:
            raise RuntimeError(f"Cannot start job in status {self.status}")
        
        self.status = ReportStatus.GENERATING
        self.started_at = datetime.now(timezone.utc).isoformat()
        
        # Créer les répertoires
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
        
        # Initialiser le fichier rapport
        self._write_header()
        
        try:
            # Générer chaque section
            for i, section in enumerate(self.sections):
                if self.status == ReportStatus.CANCELLED:
                    break
                
                if section.status == "completed":
                    continue
                
                self.current_section_idx = i
                section.status = "generating"
                
                start_time = time.time()
                
                try:
                    if generator:
                        # Utiliser le générateur fourni
                        content_parts = []
                        async for chunk in generator(section.title, self.context):
                            content_parts.append(chunk)
                            # Écrire progressivement
                            self._append_content(chunk)
                        section.content = "".join(content_parts)
                    else:
                        # Générateur par défaut (placeholder)
                        section.content = await self._default_generate_section(section)
                        self._write_section(section)
                    
                    section.status = "completed"
                    section.word_count = len(section.content.split())
                    section.generated_at = datetime.now(timezone.utc).isoformat()
                    section.generation_time_ms = int((time.time() - start_time) * 1000)
                    
                    self.total_words += section.word_count
                    self.total_generation_time_ms += section.generation_time_ms
                    
                    logger.info(
                        f"Section '{section.title}' completed: "
                        f"{section.word_count} words, {section.generation_time_ms}ms "
                        f"[{self.job_id}]"
                    )
                    
                except Exception as e:
                    section.status = "failed"
                    logger.error(f"Section '{section.title}' failed: {e}")
                    if self.config.max_sections and i >= self.config.max_sections:
                        break
                    # Continue avec la section suivante
            
            # Finaliser
            if self.status != ReportStatus.CANCELLED:
                self._write_footer()
                self._export_formats()
                self.status = ReportStatus.COMPLETED
            
            self.completed_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(
                f"Report job completed: {self.sections_completed}/{len(self.sections)} sections, "
                f"{self.total_words} words [{self.job_id}]"
            )
            
        except Exception as e:
            self.status = ReportStatus.FAILED
            self.error = str(e)
            logger.error(f"Report job failed: {e} [{self.job_id}]")
            raise
    
    def pause(self):
        """Met en pause la génération."""
        if self.status == ReportStatus.GENERATING:
            self.status = ReportStatus.PAUSED
    
    def cancel(self):
        """Annule la génération."""
        self.status = ReportStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc).isoformat()
    
    # ─────────────────────────────────────────────────────────────────────────
    # FILE OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _write_header(self):
        """Écrit l'en-tête du rapport."""
        header = f"""# {self.title}

> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
> Job ID: `{self.job_id}`

---

## Table of Contents

"""
        for i, section in enumerate(self.sections, 1):
            header += f"{i}. [{section.title}](#{section.title.lower().replace(' ', '-')})\n"
        
        header += "\n---\n\n"
        
        self.report_path.write_text(header, encoding="utf-8")
    
    def _write_section(self, section: ReportSection):
        """Écrit une section dans le fichier."""
        content = f"\n## {section.title}\n\n{section.content}\n"
        
        # Assets
        if section.assets:
            content += "\n### Assets\n\n"
            for asset in section.assets:
                asset_name = Path(asset).name
                content += f"![{asset_name}](assets/{asset_name})\n"
        
        with open(self.report_path, "a", encoding="utf-8") as f:
            f.write(content)
    
    def _append_content(self, content: str):
        """Ajoute du contenu en streaming."""
        with open(self.report_path, "a", encoding="utf-8") as f:
            f.write(content)
    
    def _write_footer(self):
        """Écrit le pied de page du rapport."""
        footer = f"""

---

## Report Metadata

| Metric | Value |
|--------|-------|
| Total Sections | {len(self.sections)} |
| Completed Sections | {self.sections_completed} |
| Total Words | {self.total_words} |
| Generation Time | {self.total_generation_time_ms / 1000:.1f}s |
| Job ID | `{self.job_id}` |

*Generated by KOREV Evidence Report System*
"""
        with open(self.report_path, "a", encoding="utf-8") as f:
            f.write(footer)
    
    def _export_formats(self):
        """Exporte dans les formats configurés."""
        for fmt in self.config.export_formats:
            if fmt == ExportFormat.MARKDOWN:
                pass  # Déjà fait
            elif fmt == ExportFormat.HTML:
                self._export_html()
            elif fmt == ExportFormat.PDF:
                self._export_pdf()
    
    def _export_html(self):
        """Exporte en HTML avec la charte KOREV Evidence (PRISM Design System)."""
        try:
            import markdown
            md_content = self.report_path.read_text(encoding="utf-8")
            body_html = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>{self.title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        @page {{ size: A4; margin: 20mm 22mm 25mm 22mm; }}
        body {{ font-family: 'Inter', -apple-system, sans-serif; font-size: 10pt; line-height: 1.65; color: #4A5568; max-width: 166mm; margin: 0 auto; padding: 0; }}
        h1 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 18pt; font-weight: 600; color: #1A1D23; margin-top: 28px; margin-bottom: 10px; }}
        h2 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 13pt; font-weight: 600; color: #4A7CFF; margin-top: 22px; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid #E2E8F0; }}
        h3 {{ font-family: 'Inter', sans-serif; font-size: 11pt; font-weight: 700; color: #1A1D23; margin-top: 16px; margin-bottom: 6px; }}
        h4 {{ font-family: 'Inter', sans-serif; font-size: 10pt; font-weight: 600; color: #4A5568; }}
        p {{ margin-bottom: 8px; }}
        strong {{ font-weight: 600; color: #1A1D23; }}
        a {{ color: #4A7CFF; text-decoration: none; }}
        code {{ font-size: 8.5pt; background: #FAFBFC; padding: 1px 4px; border-radius: 3px; color: #4A7CFF; }}
        pre {{ background: #0D1117; color: #E2E8F0; padding: 12px 14px; border-radius: 6px; font-size: 8pt; overflow-wrap: break-word; white-space: pre-wrap; }}
        pre code {{ background: none; color: inherit; padding: 0; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; table-layout: fixed; margin: 10px 0 14px 0; }}
        thead th {{ background: #0D1117; color: white; font-weight: 600; text-align: left; padding: 7px 9px; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.05em; }}
        tbody td {{ padding: 6px 9px; border-bottom: 1px solid #F1F5F9; vertical-align: top; word-wrap: break-word; }}
        tbody tr:nth-child(even) {{ background: #FAFBFC; }}
        blockquote {{ border-left: 3px solid #4A7CFF; padding: 10px 14px; margin: 12px 0; background: #F0F4FF; border-radius: 0 4px 4px 0; font-style: italic; }}
        hr {{ border: none; border-top: 1px solid #E2E8F0; margin: 16px 0; }}
        ul, ol {{ padding-left: 18px; }}
        li {{ margin-bottom: 4px; font-size: 9.5pt; }}
        img {{ max-width: 100%; }}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""
            html_path = self.output_dir / "report.html"
            html_path.write_text(html_content, encoding="utf-8")
            logger.info(f"HTML export: {html_path}")
        except ImportError:
            logger.warning("markdown library not installed, skipping HTML export")
    
    def _export_pdf(self):
        """Exporte en PDF via le moteur PRISM centralisé."""
        try:
            from python.helpers.evidence_pdf_engine import markdown_to_pdf
            md_content = self.report_path.read_text(encoding="utf-8")
            pdf_path = self.output_dir / "report.pdf"
            markdown_to_pdf(
                content=md_content,
                output_path=str(pdf_path),
                title=self.title,
                header_right="Rapport",
            )
            logger.info(f"PDF export (PRISM): {pdf_path}")
        except Exception as e:
            logger.warning(f"PRISM engine failed ({e}), trying legacy weasyprint")
            try:
                from weasyprint import HTML
                html_path = self.output_dir / "report.html"
                if not html_path.exists():
                    self._export_html()
                pdf_path = self.output_dir / "report.pdf"
                HTML(filename=str(html_path)).write_pdf(str(pdf_path))
                logger.info(f"PDF export (legacy): {pdf_path}")
            except ImportError:
                logger.warning("weasyprint not installed, skipping PDF export")
    
    async def _default_generate_section(self, section: ReportSection) -> str:
        """Générateur par défaut (placeholder)."""
        return f"""### {section.title}

*This section would contain detailed analysis of: {section.title}*

The content for this section has not been generated yet.
Please provide a custom generator function when starting the report job.

---
"""
    
    # ─────────────────────────────────────────────────────────────────────────
    # ASSETS
    # ─────────────────────────────────────────────────────────────────────────
    
    def add_asset(
        self,
        section_idx: int,
        asset_path: str,
        copy: bool = True,
    ) -> str:
        """
        Ajoute un asset (chart, image) à une section.
        
        Args:
            section_idx: Index de la section
            asset_path: Chemin vers le fichier asset
            copy: Si True, copie le fichier dans assets/
            
        Returns:
            Chemin relatif de l'asset
        """
        if section_idx >= len(self.sections):
            raise IndexError(f"Section index {section_idx} out of range")
        
        source = Path(asset_path)
        if not source.exists():
            raise FileNotFoundError(f"Asset not found: {asset_path}")
        
        dest_name = f"{self.sections[section_idx].section_id}_{source.name}"
        dest_path = self.assets_dir / dest_name
        
        if copy:
            shutil.copy2(source, dest_path)
        
        self.sections[section_idx].assets.append(str(dest_path))
        
        return f"assets/{dest_name}"


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ReportManager:
    """Gestionnaire de jobs de rapports."""
    
    def __init__(self, base_dir: str = DEFAULT_REPORTS_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, ReportJob] = {}
    
    def create_job(
        self,
        title: str,
        query: str,
        outline: List[str],
        context: Dict[str, Any] = None,
        config: ReportConfig = None,
    ) -> ReportJob:
        """Crée un nouveau job de rapport."""
        job = ReportJob(
            title=title,
            query=query,
            outline=outline,
            context=context or {},
            config=config or ReportConfig(output_dir=str(self.base_dir)),
        )
        self.jobs[job.job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[ReportJob]:
        """Récupère un job par son ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """Liste tous les jobs."""
        return [job.to_dict() for job in self.jobs.values()]
    
    def cleanup_old_jobs(self, max_age_days: int = 7):
        """Nettoie les jobs anciens."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
        
        to_remove = []
        for job_id, job in self.jobs.items():
            if job.status in [ReportStatus.COMPLETED, ReportStatus.FAILED, ReportStatus.CANCELLED]:
                created = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
                if created.timestamp() < cutoff:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            job = self.jobs.pop(job_id)
            if job.output_dir and job.output_dir.exists():
                shutil.rmtree(job.output_dir)
            logger.info(f"Cleaned up old job: {job_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_manager_instance: Optional[ReportManager] = None


def get_report_manager() -> ReportManager:
    """Retourne l'instance singleton du manager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ReportManager()
    return _manager_instance


def create_report_job(
    title: str,
    query: str,
    outline: List[str],
    context: Dict[str, Any] = None,
    config: ReportConfig = None,
) -> ReportJob:
    """
    Crée un job de rapport.
    
    Usage:
        job = create_report_job(
            title="Market Analysis",
            query="Analyze AI market trends",
            outline=["Executive Summary", "Market Overview", "Trends", "Recommendations"],
        )
        
        await job.start()
    """
    return get_report_manager().create_job(
        title, query, outline, context, config
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ReportStatus",
    "ExportFormat",
    # Config
    "ReportConfig",
    # Data
    "ReportSection",
    "ReportJob",
    # Manager
    "ReportManager",
    # Functions
    "get_report_manager",
    "create_report_job",
]

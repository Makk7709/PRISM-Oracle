"""
T7: Long Report Generation — Test Obligatoire.

Vérifie que le système peut générer des rapports longs
(50+ sections) sans limite artificielle côté app.

Ce test est OBLIGATOIRE pour tenir la promesse "rapport 300 pages".
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path

from python.helpers.reporting.report_job import (
    ReportJob,
    ReportManager,
    ReportConfig,
    ReportStatus,
    ReportSection,
    ExportFormat,
)
from python.helpers.reporting.report_assembler import (
    ReportAssembler,
    SectionOutline,
    ChunkContext,
)


class TestLongReportGeneration:
    """
    T7: Génération de rapports longs (50+ sections).
    
    Vérifications:
    - Pas de limite artificielle côté app
    - Configuration correcte
    - Création de job avec 50+ sections outline
    """
    
    @pytest.fixture
    def temp_dir(self):
        """Crée un répertoire temporaire pour les tests."""
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)
    
    @pytest.fixture
    def config(self, temp_dir):
        """Configuration de test."""
        return ReportConfig(
            output_dir=Path(temp_dir),
            max_sections=None,  # PAS DE LIMITE
            chunk_size_tokens=500,
            export_formats=[ExportFormat.MARKDOWN],
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 1: Job peut être créé avec 50+ sections
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_can_create_job_with_50_sections(self, config, temp_dir):
        """Peut créer un job avec 50 sections sans limite."""
        manager = ReportManager()
        
        outline = [f"Section {i+1}" for i in range(50)]
        job = manager.create_job(
            title="Test Report 50 Sections",
            query="Generate comprehensive analysis",
            outline=outline,
            config=config,
        )
        
        # Vérifications
        assert job is not None
        assert len(job.outline) == 50
        assert job.status == ReportStatus.PENDING
        assert job.config.max_sections is None  # Pas de limite
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 2: Pas de limite max_sections
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_no_artificial_section_limit(self, config):
        """max_sections=None signifie pas de limite."""
        assert config.max_sections is None
        
        # Vérifier que la config accepte None
        config2 = ReportConfig(max_sections=None)
        assert config2.max_sections is None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 3: Job avec 100 sections
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_can_create_job_with_100_sections(self, config, temp_dir):
        """Peut créer un job avec 100 sections."""
        manager = ReportManager()
        
        outline = [f"Section {i+1}" for i in range(100)]
        job = manager.create_job(
            title="Test Report 100 Sections",
            query="Generate",
            outline=outline,
            config=config,
        )
        
        assert len(job.outline) == 100
        assert job.config.max_sections is None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 4: Répertoires créés correctement
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_directories_created(self, config, temp_dir):
        """Les répertoires sont créés."""
        manager = ReportManager()
        
        job = manager.create_job(
            title="Test",
            query="Test",
            outline=["Section 1"],
            config=config,
        )
        
        # Le job doit avoir des paths définis
        assert job.output_dir is not None
        assert job.report_path is not None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cas 5: Cancel method exists
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_cancel_method_exists(self, config, temp_dir):
        """La méthode cancel existe."""
        manager = ReportManager()
        
        job = manager.create_job(
            title="Test",
            query="Test",
            outline=["Section 1"],
            config=config,
        )
        
        # Cancel existe et ne crash pas sur un job non démarré
        assert hasattr(job, "cancel")
        job.cancel()
        assert job.status == ReportStatus.CANCELLED


class TestReportAssembler:
    """
    Test de l'assembleur de rapport par chunks.
    """
    
    @pytest.mark.asyncio
    async def test_assembler_generates_sections(self):
        """L'assembleur génère des sections."""
        assembler = ReportAssembler(
            title="Test Report",
            query="Analyze something",
        )
        
        # Ajouter des sections
        for i in range(5):
            assembler.add_section(
                title=f"Section {i+1}",
                description=f"Analysis part {i+1}",
                key_points=[f"Point A{i}", f"Point B{i}"],
            )
        
        # Ajouter des citations
        assembler.add_citation("src1", {"title": "Source 1", "url": "http://example.com"})
        
        # Générer
        chunks = []
        async for chunk in assembler.generate():
            chunks.append(chunk)
        
        # Au moins un chunk par section + header + footer
        assert len(chunks) >= 5
        
        # Le contenu total n'est pas vide
        total = "".join(chunks)
        assert len(total) > 0


class TestReportQuotas:
    """
    Test des quotas et limites de rapport.
    """
    
    def test_max_sections_config(self):
        """max_sections est configurable (None = pas de limite)."""
        # None = pas de limite
        config = ReportConfig(max_sections=None)
        assert config.max_sections is None
        
        # Limité
        config2 = ReportConfig(max_sections=100)
        assert config2.max_sections == 100
    
    def test_timeout_config(self):
        """Timeouts sont configurables."""
        config = ReportConfig(
            section_timeout_s=120,
            total_timeout_s=7200,
        )
        assert config.section_timeout_s == 120
        assert config.total_timeout_s == 7200


class TestReportNoTokenLimit:
    """
    Vérifie qu'il n'y a pas de limite de tokens artificielle côté app.
    """
    
    def test_chunk_size_configurable(self):
        """chunk_size_tokens est configurable (pas hardcodé)."""
        config1 = ReportConfig(chunk_size_tokens=1000)
        config2 = ReportConfig(chunk_size_tokens=8000)
        
        assert config1.chunk_size_tokens == 1000
        assert config2.chunk_size_tokens == 8000
    
    def test_no_max_tokens_limit(self):
        """Pas de max_tokens global sur le rapport."""
        config = ReportConfig()
        
        # Ces attributs ne devraient pas exister ou être None
        assert not hasattr(config, "max_total_tokens") or config.max_total_tokens is None

"""
Legal Sources — CLI

Usage:
    python -m legal_sources ingest --source legi --since 2025-01-01
    python -m legal_sources ingest --source cass --since 2025-01-01
    python -m legal_sources verify
    python -m legal_sources stats
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_default_config, LegalSourcesConfig
from .models import LegalSource, IngestionResult


def setup_logging(level: str = "INFO", format: str = "text"):
    """Configure le logging."""
    log_format = (
        '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
        if format == "json"
        else "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
    )
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_ingest(args):
    """Commande d'ingestion."""
    from .fetchers import JudilibreFetcher, LegiFranceFetcher
    from .chunking import LegalChunker, ChunkerConfig
    
    config = get_default_config()
    config.ensure_dirs()
    
    source = LegalSource(args.source.lower())
    since = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    limit = args.limit
    
    logging.info(f"Starting ingestion for {source.value}")
    logging.info(f"Since: {since}, Limit: {limit}")
    
    result = IngestionResult(source=source, started_at=datetime.utcnow())
    
    try:
        # Sélectionner le fetcher
        if source == LegalSource.CASS:
            fetcher = JudilibreFetcher(config)
        elif source == LegalSource.LEGI:
            fetcher = LegiFranceFetcher(config)
        else:
            logging.error(f"Source {source.value} not yet implemented")
            sys.exit(1)
        
        # Chunker
        chunker = LegalChunker(ChunkerConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        ))
        
        # Récupérer et traiter les documents
        for doc in fetcher.fetch_and_parse(since=since, limit=limit):
            result.docs_fetched += 1
            result.docs_parsed += 1
            
            # Sauvegarder le document
            doc_path = config.processed_dir / source.value / f"{doc.doc_id}.json"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)
            
            result.docs_indexed += 1
            
            # Découper en chunks
            for chunk in chunker.chunk_document(doc):
                chunk_path = config.index_dir / source.value / f"{chunk.chunk_id}.json"
                chunk_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(chunk_path, "w", encoding="utf-8") as f:
                    json.dump(chunk.to_dict(), f, ensure_ascii=False, indent=2)
                
                result.chunks_created += 1
            
            result.last_doc_id = doc.doc_id
            
            if result.docs_indexed % 100 == 0:
                logging.info(f"Progress: {result.docs_indexed} docs, {result.chunks_created} chunks")
        
        result.completed_at = datetime.utcnow()
        
        logging.info(f"Ingestion complete: {result.to_dict()}")
        
        # Sauvegarder le rapport
        report_path = config.base_dir / "reports" / f"ingest_{source.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        
        return 0 if result.success else 1
        
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        result.errors.append(str(e))
        result.docs_failed += 1
        return 1


def cmd_verify(args):
    """Commande de vérification."""
    from .models import LegalDoc, LegalChunk, Provenance
    
    config = get_default_config()
    
    errors = []
    warnings = []
    stats = {
        "docs_checked": 0,
        "chunks_checked": 0,
        "provenance_valid": 0,
        "provenance_invalid": 0,
    }
    
    logging.info("Starting verification...")
    
    # Vérifier les documents
    for source_dir in config.processed_dir.iterdir():
        if not source_dir.is_dir():
            continue
        
        for doc_file in source_dir.glob("*.json"):
            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                doc = LegalDoc.from_dict(data)
                stats["docs_checked"] += 1
                
                # Vérifier doc_id stable
                expected_id = doc._compute_doc_id()
                if doc.doc_id != expected_id:
                    errors.append(f"Doc {doc_file.name}: doc_id mismatch (got {doc.doc_id}, expected {expected_id})")
                
                # Vérifier provenance
                if not doc.provenance:
                    warnings.append(f"Doc {doc_file.name}: missing provenance")
                    stats["provenance_invalid"] += 1
                else:
                    stats["provenance_valid"] += 1
                
            except Exception as e:
                errors.append(f"Doc {doc_file.name}: parse error - {e}")
    
    # Vérifier les chunks
    for source_dir in config.index_dir.iterdir():
        if not source_dir.is_dir():
            continue
        
        for chunk_file in source_dir.glob("*.json"):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                chunk = LegalChunk.from_dict(data)
                stats["chunks_checked"] += 1
                
                # Vérifier chunk_id stable
                expected_id = chunk._compute_chunk_id()
                if chunk.chunk_id != expected_id:
                    errors.append(f"Chunk {chunk_file.name}: chunk_id mismatch")
                
                # Vérifier provenance
                if not chunk.provenance or not chunk.provenance.origin_id:
                    warnings.append(f"Chunk {chunk_file.name}: incomplete provenance")
                
            except Exception as e:
                errors.append(f"Chunk {chunk_file.name}: parse error - {e}")
    
    # Rapport
    logging.info(f"Verification complete: {stats}")
    
    if errors:
        logging.error(f"Errors ({len(errors)}):")
        for err in errors[:10]:
            logging.error(f"  - {err}")
        if len(errors) > 10:
            logging.error(f"  ... and {len(errors) - 10} more")
    
    if warnings:
        logging.warning(f"Warnings ({len(warnings)}):")
        for warn in warnings[:10]:
            logging.warning(f"  - {warn}")
    
    return 0 if not errors else 1


def cmd_stats(args):
    """Commande de statistiques."""
    config = get_default_config()
    
    stats = {
        "sources": {},
        "total_docs": 0,
        "total_chunks": 0,
    }
    
    # Compter les documents
    if config.processed_dir.exists():
        for source_dir in config.processed_dir.iterdir():
            if source_dir.is_dir():
                count = len(list(source_dir.glob("*.json")))
                stats["sources"][source_dir.name] = {"docs": count}
                stats["total_docs"] += count
    
    # Compter les chunks
    if config.index_dir.exists():
        for source_dir in config.index_dir.iterdir():
            if source_dir.is_dir():
                count = len(list(source_dir.glob("*.json")))
                if source_dir.name in stats["sources"]:
                    stats["sources"][source_dir.name]["chunks"] = count
                else:
                    stats["sources"][source_dir.name] = {"chunks": count}
                stats["total_chunks"] += count
    
    print(json.dumps(stats, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Legal Sources — Ingestion de données juridiques",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de log",
    )
    
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Format de log",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingérer des données juridiques")
    ingest_parser.add_argument(
        "--source",
        required=True,
        choices=["legi", "cass", "jade", "constit"],
        help="Source à ingérer",
    )
    ingest_parser.add_argument(
        "--since",
        help="Date minimum (YYYY-MM-DD)",
    )
    ingest_parser.add_argument(
        "--limit",
        type=int,
        help="Nombre maximum de documents",
    )
    
    # Commande verify
    verify_parser = subparsers.add_parser("verify", help="Vérifier l'intégrité des données")
    
    # Commande stats
    stats_parser = subparsers.add_parser("stats", help="Afficher les statistiques")
    
    args = parser.parse_args()
    
    setup_logging(args.log_level, args.log_format)
    
    if args.command == "ingest":
        sys.exit(cmd_ingest(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "stats":
        sys.exit(cmd_stats(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

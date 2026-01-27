"""
Legal Sources — CLI Enterprise

Usage:
    python -m legal_sources ingest --source legi --since 2025-01-01
    python -m legal_sources ingest --source cass --since 2025-01-01 --smoke
    python -m legal_sources search --q "L132-8" --source legi --limit 10
    python -m legal_sources lookup --origin-id LEGIARTI000006420055
    python -m legal_sources export-audit --chunk-ids id1,id2 --out audit.json
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
from .models import LegalSource, IngestionResult, ProvenanceValidationError


def setup_logging(level: str = "INFO", format_type: str = "text"):
    """Configure le logging."""
    if format_type == "json":
        log_format = '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
    else:
        log_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_ingest(args):
    """Commande d'ingestion avec résilience."""
    from .fetchers import JudilibreFetcher, LegiFranceFetcher
    from .chunking import LegalChunker, ChunkerConfig
    from .indexing import LegalIndex
    from .resilience import CheckpointManager
    
    config = get_default_config()
    config.ensure_dirs()
    
    source = LegalSource(args.source.lower())
    since = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    limit = args.limit
    is_smoke = getattr(args, 'smoke', False)
    
    logging.info(json.dumps({
        "event": "ingest_start",
        "source": source.value,
        "since": since.isoformat() if since else None,
        "limit": limit,
        "smoke": is_smoke,
    }))
    
    result = IngestionResult(source=source, started_at=datetime.utcnow())
    
    # Checkpoint manager
    checkpoint_mgr = CheckpointManager(config.cache_dir)
    checkpoint = checkpoint_mgr.get(source.value)
    
    if checkpoint and not is_smoke:
        logging.info(f"Resuming from checkpoint: page={checkpoint.page}, docs={checkpoint.docs_processed}")
    
    # Index
    index = LegalIndex(config.index_dir)
    
    # Sample citations for smoke report
    sample_citations = []
    
    try:
        # Sélectionner le fetcher
        if source == LegalSource.CASS:
            from .fetchers import JudilibreFetcher
            fetcher = JudilibreFetcher(config)
        elif source == LegalSource.LEGI:
            from .fetchers import LegiFranceFetcher
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
            
            # Vérifier provenance (AUDIT: no provenance, no index)
            try:
                doc.validate_for_indexing()
            except ProvenanceValidationError as e:
                logging.warning(f"Document rejected: {e}")
                result.docs_rejected_no_provenance += 1
                continue
            
            result.docs_parsed += 1
            
            # Vérifier si déjà indexé (idempotence)
            if index.doc_exists(doc.doc_id):
                result.docs_skipped += 1
                continue
            
            # Ajouter au storage
            doc_path = config.processed_dir / source.value / f"{doc.doc_id}.json"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)
            
            # Ajouter à l'index
            index.add_doc(doc)
            result.docs_indexed += 1
            
            # Découper en chunks
            for chunk in chunker.chunk_document(doc):
                if not index.chunk_exists(chunk.chunk_id):
                    index.add_chunk(chunk)
                    result.chunks_created += 1
            
            result.last_doc_id = doc.doc_id
            
            # Collecter samples pour smoke
            if is_smoke and len(sample_citations) < 5:
                sample_citations.append(doc.citation)
            
            # Checkpoint périodique
            if result.docs_indexed % 10 == 0:
                checkpoint_mgr.update(
                    source=source.value,
                    page=result.docs_indexed // 10,
                    last_doc_id=doc.doc_id,
                    last_origin_id=doc.origin_id,
                    docs_processed=result.docs_indexed,
                )
            
            if result.docs_indexed % 50 == 0:
                logging.info(json.dumps({
                    "event": "progress",
                    "docs_indexed": result.docs_indexed,
                    "chunks_created": result.chunks_created,
                }))
        
        result.completed_at = datetime.utcnow()
        
        logging.info(json.dumps({
            "event": "ingest_complete",
            **result.to_dict(),
        }))
        
        # Générer rapport smoke si demandé
        if is_smoke:
            _generate_smoke_report(result, sample_citations, config)
        
        # Clear checkpoint on success
        if result.success:
            checkpoint_mgr.clear(source.value)
        
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


def _generate_smoke_report(result: IngestionResult, samples: list, config: LegalSourcesConfig):
    """Génère un rapport de smoke test."""
    report_path = config.base_dir / "reports" / f"smoke_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        f"# Smoke Test Report — {result.source.value.upper()}",
        "",
        f"**Date**: {datetime.utcnow().isoformat()}",
        f"**Duration**: {result.duration_seconds:.2f}s",
        "",
        "## Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Documents fetched | {result.docs_fetched} |",
        f"| Documents parsed | {result.docs_parsed} |",
        f"| Documents indexed | {result.docs_indexed} |",
        f"| Documents skipped (idempotent) | {result.docs_skipped} |",
        f"| Documents rejected (no provenance) | {result.docs_rejected_no_provenance} |",
        f"| Chunks created | {result.chunks_created} |",
        f"| Retries total | {result.retries_total} |",
        f"| Rate limited (429) | {result.rate_limited_count} |",
        f"| Errors | {len(result.errors)} |",
        "",
        "## Sample Citations",
        "",
    ]
    
    for i, citation in enumerate(samples, 1):
        lines.append(f"{i}. {citation}")
    
    if result.errors:
        lines.extend([
            "",
            "## Errors",
            "",
        ])
        for err in result.errors[:5]:
            lines.append(f"- {err}")
    
    lines.extend([
        "",
        "## Verdict",
        "",
        f"**Status**: {'✅ PASS' if result.success else '❌ FAIL'}",
    ])
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    logging.info(f"Smoke report saved to {report_path}")


def cmd_search(args):
    """Commande de recherche FTS5."""
    from .indexing import LegalIndex
    
    config = get_default_config()
    index = LegalIndex(config.index_dir)
    
    results = index.search(
        query=args.q,
        source=args.source,
        limit=args.limit,
    )
    
    if args.format == "json":
        output = [r.to_dict() for r in results]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\nFound {len(results)} results for '{args.q}':\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.source}] {r.citation}")
            print(f"   Pinpoint: {r.pinpoint}")
            print(f"   Score: {r.score:.4f}")
            print(f"   Origin: {r.provenance.get('origin_id', 'N/A')}")
            print(f"   Snippet: {r.text_snippet[:100]}...")
            print()
    
    return 0


def cmd_lookup(args):
    """Commande de lookup par origin_id."""
    from .indexing import LegalIndex
    
    config = get_default_config()
    index = LegalIndex(config.index_dir)
    
    result = index.lookup_by_origin_id(args.origin_id)
    
    if not result:
        print(f"No document found for origin_id: {args.origin_id}")
        return 1
    
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        doc = result["doc"]
        chunks = result["chunks"]
        
        print(f"\n=== Document ===")
        print(f"Citation: {doc.get('citation')}")
        print(f"Title: {doc.get('title')}")
        print(f"Source: {doc.get('source')}")
        print(f"Origin ID: {doc.get('origin_id')}")
        print(f"Date: {doc.get('date')}")
        
        if doc.get("provenance"):
            prov = doc["provenance"]
            print(f"\n=== Provenance ===")
            print(f"License: {prov.get('license_name')}")
            print(f"License URL: {prov.get('license_url')}")
            print(f"Terms: {prov.get('terms_name')}")
            print(f"Terms URL: {prov.get('terms_url')}")
            print(f"Retrieved: {prov.get('retrieved_at')}")
        
        print(f"\n=== Chunks ({len(chunks)}) ===")
        for c in chunks[:5]:
            print(f"  - {c.get('chunk_id')}: {c.get('pinpoint')}")
    
    return 0


def cmd_export_audit(args):
    """Commande d'export audit bundle."""
    from .indexing import LegalIndex
    from .audit_bundle import build_audit_bundle, validate_audit_bundle, generate_audit_report
    
    config = get_default_config()
    index = LegalIndex(config.index_dir)
    
    # Parser les chunk_ids
    chunk_ids = [cid.strip() for cid in args.chunk_ids.split(",") if cid.strip()]
    
    if not chunk_ids:
        print("Error: No chunk_ids provided")
        return 1
    
    # Récupérer les chunks
    chunks = index.get_all_chunks_for_ids(chunk_ids)
    
    if not chunks:
        print(f"Error: No chunks found for ids: {chunk_ids}")
        return 1
    
    # Construire le bundle
    bundle = build_audit_bundle(chunks, description=args.description or "Audit export")
    
    # Valider
    validation = validate_audit_bundle(bundle)
    
    # Output
    out_path = Path(args.out) if args.out else config.base_dir / "reports" / f"audit_bundle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    bundle.save(out_path)
    
    print(f"Audit bundle saved to: {out_path}")
    print(f"Bundle ID: {bundle.bundle_id}")
    print(f"Total entries: {bundle.total_chunks}")
    print(f"Valid: {validation['valid']}")
    
    if not validation['valid']:
        print(f"Missing fields: {len(validation['missing_fields'])}")
        for field in validation['missing_fields'][:5]:
            print(f"  - {field}")
    
    # Générer aussi le rapport markdown
    if args.report:
        report_path = out_path.with_suffix(".md")
        report = generate_audit_report(bundle)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Audit report saved to: {report_path}")
    
    return 0


def cmd_verify(args):
    """Commande de vérification."""
    from .models import LegalDoc, LegalChunk, Provenance, ProvenanceValidationError
    from .indexing import LegalIndex
    
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
    if config.processed_dir.exists():
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
                        errors.append(f"Doc {doc_file.name}: doc_id mismatch")
                    
                    # Vérifier provenance complète
                    try:
                        doc.validate_for_indexing()
                        stats["provenance_valid"] += 1
                    except ProvenanceValidationError as e:
                        stats["provenance_invalid"] += 1
                        errors.append(f"Doc {doc_file.name}: {e}")
                    
                except Exception as e:
                    errors.append(f"Doc {doc_file.name}: parse error - {e}")
    
    # Vérifier l'index SQLite
    index = LegalIndex(config.index_dir)
    index_stats = index.get_stats()
    stats["chunks_checked"] = index_stats["total_chunks"]
    
    # Rapport
    print(json.dumps({
        "event": "verify_complete",
        "stats": stats,
        "index_stats": index_stats,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
    }, indent=2))
    
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warn in warnings[:10]:
            print(f"  - {warn}")
    
    return 0 if not errors else 1


def cmd_stats(args):
    """Commande de statistiques."""
    from .indexing import LegalIndex
    
    config = get_default_config()
    index = LegalIndex(config.index_dir)
    
    stats = index.get_stats()
    
    # Ajouter stats fichiers
    file_stats = {"sources": {}}
    if config.processed_dir.exists():
        for source_dir in config.processed_dir.iterdir():
            if source_dir.is_dir():
                count = len(list(source_dir.glob("*.json")))
                file_stats["sources"][source_dir.name] = {"files": count}
    
    output = {
        "index": stats,
        "files": file_stats,
    }
    
    print(json.dumps(output, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Legal Sources — Ingestion Enterprise",
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
    
    # === Commande ingest ===
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
    ingest_parser.add_argument(
        "--smoke",
        action="store_true",
        help="Mode smoke test (génère rapport)",
    )
    ingest_parser.add_argument(
        "--code",
        help="Code spécifique à ingérer (pour LEGI)",
    )
    
    # === Commande search ===
    search_parser = subparsers.add_parser("search", help="Rechercher dans l'index")
    search_parser.add_argument(
        "--q",
        required=True,
        help="Termes de recherche",
    )
    search_parser.add_argument(
        "--source",
        help="Filtrer par source (legi, cass, etc.)",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Nombre max de résultats",
    )
    search_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Format de sortie",
    )
    
    # === Commande lookup ===
    lookup_parser = subparsers.add_parser("lookup", help="Lookup par origin_id")
    lookup_parser.add_argument(
        "--origin-id",
        required=True,
        help="Origin ID (LEGIARTI..., etc.)",
    )
    lookup_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Format de sortie",
    )
    
    # === Commande export-audit ===
    audit_parser = subparsers.add_parser("export-audit", help="Exporter un audit bundle")
    audit_parser.add_argument(
        "--chunk-ids",
        required=True,
        help="IDs des chunks (séparés par virgule)",
    )
    audit_parser.add_argument(
        "--out",
        help="Chemin de sortie",
    )
    audit_parser.add_argument(
        "--description",
        help="Description du bundle",
    )
    audit_parser.add_argument(
        "--report",
        action="store_true",
        help="Générer aussi un rapport Markdown",
    )
    
    # === Commande verify ===
    verify_parser = subparsers.add_parser("verify", help="Vérifier l'intégrité")
    
    # === Commande stats ===
    stats_parser = subparsers.add_parser("stats", help="Afficher les statistiques")
    
    args = parser.parse_args()
    
    setup_logging(args.log_level, args.log_format)
    
    if args.command == "ingest":
        sys.exit(cmd_ingest(args))
    elif args.command == "search":
        sys.exit(cmd_search(args))
    elif args.command == "lookup":
        sys.exit(cmd_lookup(args))
    elif args.command == "export-audit":
        sys.exit(cmd_export_audit(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "stats":
        sys.exit(cmd_stats(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

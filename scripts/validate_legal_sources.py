#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P4.4: VALIDATE LEGAL SOURCES                              ║
║                                                                              ║
║  Validates legal source documents for:                                      ║
║  - Content hashes (integrity)                                               ║
║  - Required provenance fields                                               ║
║  - Publisher whitelist compliance                                           ║
║  - Duplicate detection                                                       ║
║                                                                              ║
║  Usage:                                                                      ║
║    python scripts/validate_legal_sources.py --corpus                        ║
║    python scripts/validate_legal_sources.py --input sources.json            ║
║    python scripts/validate_legal_sources.py --index data/legal_index        ║
║                                                                              ║
║  Version: 1.0.0 (P4)                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ValidationReport:
    """Accumulates validation results."""
    
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.duplicates: List[Dict[str, Any]] = []
        self.publishers: Dict[str, int] = defaultdict(int)
        self.jurisdictions: Dict[str, int] = defaultdict(int)
        self.content_hashes: Dict[str, List[str]] = defaultdict(list)  # hash -> [origin_ids]
    
    def add_error(self, origin_id: str, field: str, message: str):
        self.errors.append({
            "origin_id": origin_id,
            "field": field,
            "message": message,
        })
    
    def add_warning(self, origin_id: str, field: str, message: str):
        self.warnings.append({
            "origin_id": origin_id,
            "field": field,
            "message": message,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total": self.total,
            "valid": self.valid,
            "invalid": self.total - self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "duplicate_count": len(self.duplicates),
            "errors": self.errors,
            "warnings": self.warnings,
            "duplicates": self.duplicates,
            "publishers": dict(self.publishers),
            "jurisdictions": dict(self.jurisdictions),
        }
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total documents:  {self.total}")
        print(f"Valid:            {self.valid}")
        print(f"Invalid:          {self.total - self.valid}")
        print(f"Errors:           {len(self.errors)}")
        print(f"Warnings:         {len(self.warnings)}")
        print(f"Duplicates:       {len(self.duplicates)}")
        
        if self.publishers:
            print(f"\nPublishers:")
            for pub, count in sorted(self.publishers.items()):
                print(f"  - {pub}: {count}")
        
        if self.jurisdictions:
            print(f"\nJurisdictions:")
            for jur, count in sorted(self.jurisdictions.items()):
                print(f"  - {jur}: {count}")


def validate_document(doc: Dict[str, Any], report: ValidationReport, check_whitelist: bool = True):
    """
    Validate a single document.
    
    Checks:
    - Required fields (origin_id, text, provenance)
    - Provenance completeness
    - Publisher whitelist
    - Content hash
    """
    origin_id = doc.get("origin_id", "unknown")
    report.total += 1
    is_valid = True
    
    # 1. Required fields
    if not doc.get("origin_id"):
        report.add_error(origin_id, "origin_id", "Missing origin_id")
        is_valid = False
    
    if not doc.get("text"):
        report.add_error(origin_id, "text", "Missing or empty text")
        is_valid = False
    
    if not doc.get("provenance"):
        report.add_error(origin_id, "provenance", "Missing provenance")
        is_valid = False
        return is_valid
    
    prov = doc["provenance"]
    
    # 2. Provenance required fields
    required_prov = ["source", "source_name", "origin_url", "license_name"]
    for field in required_prov:
        if not prov.get(field):
            report.add_error(origin_id, f"provenance.{field}", f"Missing {field}")
            is_valid = False
    
    # 3. Publisher whitelist
    if check_whitelist:
        from python.helpers.legal_agent_contracts import Publisher
        
        publisher = prov.get("source") or prov.get("publisher")
        if publisher and not Publisher.is_whitelisted(publisher):
            report.add_error(
                origin_id, 
                "provenance.source",
                f"Publisher '{publisher}' not in whitelist"
            )
            is_valid = False
    
    # 4. Track statistics
    publisher = prov.get("source", "unknown")
    report.publishers[publisher] += 1
    
    jurisdiction = prov.get("jurisdiction", "unknown")
    report.jurisdictions[jurisdiction] += 1
    
    # 5. Content hash for duplicate detection
    if doc.get("text"):
        content_hash = compute_content_hash(doc["text"])
        report.content_hashes[content_hash].append(origin_id)
    
    # 6. Optional field warnings
    optional_prov = ["retrieved_at", "version_date", "content_hash"]
    for field in optional_prov:
        if not prov.get(field):
            report.add_warning(origin_id, f"provenance.{field}", f"Missing optional {field}")
    
    if is_valid:
        report.valid += 1
    
    return is_valid


def detect_duplicates(report: ValidationReport):
    """Detect duplicate documents by content hash."""
    for content_hash, origin_ids in report.content_hashes.items():
        if len(origin_ids) > 1:
            report.duplicates.append({
                "content_hash": content_hash[:16],
                "origin_ids": origin_ids,
            })


def validate_corpus():
    """Validate the test corpus fixture."""
    from tests.fixtures.legal_corpus import CORPUS
    
    report = ValidationReport()
    
    for doc in CORPUS:
        validate_document(doc, report)
    
    detect_duplicates(report)
    
    return report


def validate_file(input_path: str):
    """Validate documents from a JSON file."""
    with open(input_path, "r") as f:
        docs = json.load(f)
    
    if not isinstance(docs, list):
        docs = [docs]
    
    report = ValidationReport()
    
    for doc in docs:
        validate_document(doc, report)
    
    detect_duplicates(report)
    
    return report


def validate_index(index_path: str):
    """Validate an existing FTS5 index."""
    report = ValidationReport()
    
    try:
        from python.legal_sources.indexing import LegalIndex
        
        index = LegalIndex(index_path)
        
        # Get all documents from index
        # This is a simplified check - full validation would need raw data
        results = index.search("*", limit=1000)  # Get all
        
        for result in results:
            doc = {
                "origin_id": result.chunk_id,
                "text": result.text,
                "provenance": result.provenance if hasattr(result, 'provenance') else {},
            }
            validate_document(doc, report, check_whitelist=False)
        
        detect_duplicates(report)
        
    except ImportError as e:
        print(f"ERROR: LegalIndex not available: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to validate index: {e}")
        sys.exit(1)
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate legal source documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_legal_sources.py --corpus
  python scripts/validate_legal_sources.py --input sources.json
  python scripts/validate_legal_sources.py --index data/legal_index
  python scripts/validate_legal_sources.py --corpus --output report.json
        """,
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--corpus",
        action="store_true",
        help="Validate the test corpus fixture",
    )
    group.add_argument(
        "--input",
        "-i",
        type=str,
        help="Input JSON file with source documents",
    )
    group.add_argument(
        "--index",
        type=str,
        help="Path to existing FTS5 index to validate",
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output JSON file for validation report",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed validation results",
    )
    
    args = parser.parse_args()
    
    # Run validation
    if args.corpus:
        print("Validating test corpus fixture...")
        report = validate_corpus()
    elif args.input:
        print(f"Validating {args.input}...")
        report = validate_file(args.input)
    elif args.index:
        print(f"Validating index at {args.index}...")
        report = validate_index(args.index)
    
    # Print summary
    report.print_summary()
    
    # Print errors if verbose
    if args.verbose and report.errors:
        print(f"\n{'='*60}")
        print("ERRORS")
        print(f"{'='*60}")
        for error in report.errors[:20]:  # Limit output
            print(f"  [{error['origin_id']}] {error['field']}: {error['message']}")
        if len(report.errors) > 20:
            print(f"  ... and {len(report.errors) - 20} more errors")
    
    # Print duplicates if found
    if report.duplicates:
        print(f"\n{'='*60}")
        print("DUPLICATES DETECTED")
        print(f"{'='*60}")
        for dup in report.duplicates[:10]:
            print(f"  Hash {dup['content_hash']}: {', '.join(dup['origin_ids'])}")
    
    # Save report
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\nReport saved to {args.output}")
    
    # Exit code
    if report.errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

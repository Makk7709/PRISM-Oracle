#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P3.5: LEGAL INDEX BUILD SCRIPT                            ║
║                                                                              ║
║  Build a test FTS5 index from the corpus fixture.                           ║
║  Used in CI nightly and for local E2E testing.                              ║
║                                                                              ║
║  Usage:                                                                      ║
║    python scripts/build_legal_index_test.py --output data/legal_index       ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def validate_provenance(doc: dict) -> bool:
    """
    P3.5: Validate that provenance has all required fields.
    
    Required:
    - source (str)
    - source_name (str)
    - origin_url (str)
    - license_name (str)
    """
    prov = doc.get("provenance", {})
    
    required = ["source", "source_name", "origin_url", "license_name"]
    
    for field in required:
        if not prov.get(field):
            print(f"ERROR: Missing/empty provenance field '{field}' in doc {doc.get('origin_id')}")
            return False
    
    return True


def build_index(output_path: str, verbose: bool = False) -> dict:
    """
    Build the legal FTS5 index from corpus fixture.
    
    Args:
        output_path: Directory to create the index in
        verbose: Print progress
        
    Returns:
        Build report dict
    """
    from tests.fixtures.legal_corpus import CORPUS, create_test_index
    
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "corpus_size": len(CORPUS),
        "indexed": 0,
        "skipped": 0,
        "provenance_valid": 0,
        "provenance_invalid": 0,
        "content_hashes": {},
    }
    
    # Validate provenance for all documents
    for doc in CORPUS:
        if validate_provenance(doc):
            report["provenance_valid"] += 1
            
            # Compute content hash
            content_hash = compute_content_hash(doc.get("text", ""))
            report["content_hashes"][doc["origin_id"]] = content_hash
        else:
            report["provenance_invalid"] += 1
            report["skipped"] += 1
    
    if report["provenance_invalid"] > 0:
        print(f"WARNING: {report['provenance_invalid']} documents have invalid provenance")
    
    # Build index
    if verbose:
        print(f"Building index at {output_path}...")
        print(f"  Corpus size: {report['corpus_size']}")
    
    try:
        index = create_test_index(output_dir)
        report["indexed"] = report["corpus_size"] - report["skipped"]
        
        # Verify index
        results = index.search("contrat", limit=5)
        report["verification_results"] = len(results)
        
        if verbose:
            print(f"  Indexed: {report['indexed']}")
            print(f"  Verification search returned {len(results)} results")
        
    except ImportError as e:
        print(f"ERROR: LegalIndex not available: {e}")
        report["error"] = str(e)
        return report
    except Exception as e:
        print(f"ERROR: Index build failed: {e}")
        report["error"] = str(e)
        return report
    
    # Write build report
    report_path = output_dir / "build_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    if verbose:
        print(f"  Report written to {report_path}")
    
    # Compute index hash for reproducibility
    index_files = list(output_dir.glob("*.db")) + list(output_dir.glob("*.sqlite"))
    if index_files:
        index_hash = compute_content_hash("".join(str(f.stat().st_size) for f in index_files))
        report["index_hash"] = index_hash
        if verbose:
            print(f"  Index hash: {index_hash}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Build legal FTS5 index from corpus fixture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_legal_index_test.py --output data/legal_index
  python scripts/build_legal_index_test.py --output /tmp/test_index --verbose
  python scripts/build_legal_index_test.py --validate-only
        """,
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/legal_index",
        help="Output directory for the index (default: data/legal_index)",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print progress information",
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate corpus provenance, don't build index",
    )
    
    args = parser.parse_args()
    
    if args.validate_only:
        from tests.fixtures.legal_corpus import CORPUS
        
        print("Validating corpus provenance...")
        valid = 0
        invalid = 0
        
        for doc in CORPUS:
            if validate_provenance(doc):
                valid += 1
            else:
                invalid += 1
        
        print(f"Valid: {valid}, Invalid: {invalid}")
        sys.exit(0 if invalid == 0 else 1)
    
    report = build_index(args.output, verbose=args.verbose)
    
    if "error" in report:
        print(f"Build failed: {report['error']}")
        sys.exit(1)
    
    print(f"Index built successfully: {report['indexed']} documents indexed")
    
    # Check for nightly requirement
    if os.environ.get("CI_NIGHTLY") == "1":
        if report["indexed"] < 20:
            print(f"ERROR: Nightly requires at least 20 documents, got {report['indexed']}")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

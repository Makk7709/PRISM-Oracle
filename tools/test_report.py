#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TEST REPORT — Autonomous Test Runner                       ║
║                                                                              ║
║  Exécute les tests critiques avec options:                                   ║
║  - --fast: Tests rapides (T0-T9 core)                                        ║
║  - --full: Tous les tests                                                    ║
║  - --repeat N: Stress run (N itérations, boucle Python autonome)             ║
║                                                                              ║
║  IMPORTANT: Ce script n'utilise PAS pytest-repeat.                           ║
║  Le stress run est une boucle Python native → zéro dépendance externe.       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python tools/test_report.py --fast
    python tools/test_report.py --full
    python tools/test_report.py --full --repeat 30
    python tools/test_report.py --kill-tests
"""

import argparse
import subprocess
import sys
import os
import time
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@dataclass
class TestResult:
    """Résultat d'une exécution de tests."""
    iteration: int
    passed: bool
    exit_code: int
    duration_ms: int
    tests_run: int
    tests_failed: int
    output: str


# ═══════════════════════════════════════════════════════════════════════════════
# TEST SETS
# ═══════════════════════════════════════════════════════════════════════════════

FAST_TESTS = [
    "tests/test_user_entry_gate.py",           # T0
    "tests/test_research_bypass.py",           # T2bis
    "tests/test_criticality_router.py",        # T3
    "tests/test_consensus_no_simulation_prod.py",  # T4
    "tests/test_strict_evidence_fail_closed.py",   # T5
    "tests/test_final_output_claim_integrity.py",  # T9
]

FULL_TESTS = FAST_TESTS + [
    "tests/test_multitask_consensus_routing.py",  # T1/T2
    "tests/test_long_report_job.py",              # T7
    "tests/test_chart_image_tools.py",            # T8
    "tests/test_anti_bypass.py",
]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_pytest(test_files: List[str], verbose: bool = True) -> TestResult:
    """
    Exécute pytest sur les fichiers spécifiés.
    
    Returns:
        TestResult avec les détails de l'exécution
    """
    cmd = ["python", "-m", "pytest"] + test_files
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    else:
        cmd.append("-q")
    
    start = time.time()
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    duration_ms = int((time.time() - start) * 1000)
    
    # Parse output for test counts
    tests_run = 0
    tests_failed = 0
    
    # Look for pytest summary line: "X passed, Y failed"
    for line in result.stdout.split('\n'):
        if 'passed' in line or 'failed' in line:
            import re
            passed_match = re.search(r'(\d+) passed', line)
            failed_match = re.search(r'(\d+) failed', line)
            if passed_match:
                tests_run += int(passed_match.group(1))
            if failed_match:
                tests_failed += int(failed_match.group(1))
                tests_run += tests_failed
    
    return TestResult(
        iteration=0,
        passed=result.returncode == 0,
        exit_code=result.returncode,
        duration_ms=duration_ms,
        tests_run=tests_run,
        tests_failed=tests_failed,
        output=result.stdout + result.stderr,
    )


def run_stress_test(
    test_files: List[str],
    iterations: int,
    verbose: bool = False,
    stop_on_failure: bool = True,
) -> List[TestResult]:
    """
    Stress run: exécute les tests N fois en boucle Python native.
    
    IMPORTANT: N'utilise PAS pytest-repeat. Boucle Python autonome.
    
    Args:
        test_files: Liste des fichiers de test
        iterations: Nombre d'itérations
        verbose: Afficher output détaillé
        stop_on_failure: Arrêter au premier échec (-x behavior)
        
    Returns:
        Liste des résultats pour chaque itération
    """
    results: List[TestResult] = []
    flakes = 0
    
    print(f"\n{'='*70}")
    print(f"🔥 STRESS RUN — {iterations} iterations")
    print(f"{'='*70}")
    print(f"Tests: {len(test_files)} files")
    print(f"Stop on failure: {stop_on_failure}")
    print()
    
    for i in range(1, iterations + 1):
        print(f"[{i}/{iterations}] Running...", end=" ", flush=True)
        
        result = run_pytest(test_files, verbose=False)
        result.iteration = i
        results.append(result)
        
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} ({result.duration_ms}ms, {result.tests_run} tests)")
        
        if not result.passed:
            flakes += 1
            if stop_on_failure:
                print(f"\n🛑 Stopping on first failure (iteration {i})")
                if verbose:
                    print("\n--- Output ---")
                    print(result.output[-2000:])  # Last 2000 chars
                break
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 STRESS RUN SUMMARY")
    print(f"{'='*70}")
    print(f"Iterations completed: {len(results)}/{iterations}")
    print(f"Flakes: {flakes}")
    print(f"Total duration: {sum(r.duration_ms for r in results)}ms")
    
    if flakes == 0:
        print(f"\n✅ STRESS RUN PASSED — 0 flakes in {len(results)} iterations")
    else:
        print(f"\n❌ STRESS RUN FAILED — {flakes} flake(s) detected")
    
    return results


def run_kill_tests(verbose: bool = False) -> bool:
    """
    Exécute les kill tests.
    
    IMPORTANT: Vérifie que git status est propre après exécution.
    """
    print(f"\n{'='*70}")
    print(f"🔪 KILL TESTS")
    print(f"{'='*70}")
    
    # Check git status BEFORE
    git_before = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    # Run kill tests
    cmd = ["python", "tools/kill_tests.py"]
    if verbose:
        cmd.append("--verbose")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Check git status AFTER
    git_after = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    # Verify no files changed
    if git_before.stdout != git_after.stdout:
        print("\n❌ CRITICAL: Kill tests left dirty files!")
        print("Diff in git status:")
        print(git_after.stdout)
        return False
    
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(
    fast_result: Optional[TestResult],
    full_result: Optional[TestResult],
    stress_results: Optional[List[TestResult]],
    kill_passed: Optional[bool],
) -> str:
    """Génère un rapport de test formaté."""
    
    lines = [
        "# Test Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
    ]
    
    if fast_result:
        status = "✅ PASS" if fast_result.passed else "❌ FAIL"
        lines.extend([
            "## FAST Tests",
            f"Status: {status}",
            f"Tests: {fast_result.tests_run}",
            f"Failed: {fast_result.tests_failed}",
            f"Duration: {fast_result.duration_ms}ms",
            "",
        ])
    
    if full_result:
        status = "✅ PASS" if full_result.passed else "❌ FAIL"
        lines.extend([
            "## FULL Tests",
            f"Status: {status}",
            f"Tests: {full_result.tests_run}",
            f"Failed: {full_result.tests_failed}",
            f"Duration: {full_result.duration_ms}ms",
            "",
        ])
    
    if stress_results:
        flakes = sum(1 for r in stress_results if not r.passed)
        status = "✅ PASS" if flakes == 0 else "❌ FAIL"
        lines.extend([
            "## Stress Run",
            f"Status: {status}",
            f"Iterations: {len(stress_results)}",
            f"Flakes: {flakes}",
            f"Total Duration: {sum(r.duration_ms for r in stress_results)}ms",
            "",
        ])
    
    if kill_passed is not None:
        status = "✅ PASS" if kill_passed else "❌ FAIL"
        lines.extend([
            "## Kill Tests",
            f"Status: {status}",
            "",
        ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Test Report — Autonomous Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run fast tests only (T0-T9 core)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all tests",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help="Stress run: repeat tests N times (autonomous Python loop, no pytest-repeat)",
    )
    parser.add_argument(
        "--kill-tests",
        action="store_true",
        help="Run kill tests",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--report",
        type=str,
        metavar="FILE",
        help="Write report to file",
    )
    
    args = parser.parse_args()
    
    # Default to --fast if nothing specified
    if not args.fast and not args.full and not args.kill_tests:
        args.fast = True
    
    fast_result = None
    full_result = None
    stress_results = None
    kill_passed = None
    
    success = True
    
    # Run tests
    if args.fast:
        print(f"\n{'='*70}")
        print("⚡ FAST TESTS")
        print(f"{'='*70}")
        
        if args.repeat > 1:
            stress_results = run_stress_test(
                FAST_TESTS, args.repeat, args.verbose
            )
            success = all(r.passed for r in stress_results)
        else:
            fast_result = run_pytest(FAST_TESTS, args.verbose)
            success = fast_result.passed
    
    if args.full:
        print(f"\n{'='*70}")
        print("🔬 FULL TESTS")
        print(f"{'='*70}")
        
        if args.repeat > 1:
            stress_results = run_stress_test(
                FULL_TESTS, args.repeat, args.verbose
            )
            success = success and all(r.passed for r in stress_results)
        else:
            full_result = run_pytest(FULL_TESTS, args.verbose)
            success = success and full_result.passed
    
    if args.kill_tests:
        kill_passed = run_kill_tests(args.verbose)
        success = success and kill_passed
    
    # Generate report
    if args.report:
        report = generate_report(
            fast_result, full_result, stress_results, kill_passed
        )
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"\nReport written to: {args.report}")
    
    # Final verdict
    print(f"\n{'='*70}")
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ TESTS FAILED")
    print(f"{'='*70}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

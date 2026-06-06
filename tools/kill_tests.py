#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    KILL TESTS — Proof of Test Sensitivity                    ║
║                                                                              ║
║  Ces tests PROUVENT que la suite de tests détecte les régressions.           ║
║                                                                              ║
║  Principe:                                                                   ║
║  1. Patch temporairement une règle critique (RUNTIME ONLY)                   ║
║  2. Vérifie que les tests ÉCHOUENT                                           ║
║  3. Restaure et vérifie que les tests PASSENT                                ║
║                                                                              ║
║  Si les tests NE CASSENT PAS après le patch, c'est un gap de coverage.       ║
║                                                                              ║
║  IMPORTANT: Tous les patches sont en MÉMOIRE uniquement.                     ║
║  AUCUNE modification de fichier. `git status` doit rester propre.            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python tools/kill_tests.py           # Run all kill tests
    python tools/kill_tests.py --verbose # With detailed output
    python tools/kill_tests.py --dry-run # Show what would be patched
"""

import argparse
import subprocess
import sys
import os
from dataclasses import dataclass
from typing import Callable, List, Optional
from unittest.mock import patch
import importlib

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@dataclass
class KillTestResult:
    """Résultat d'un kill test."""
    name: str
    patch_description: str
    tests_failed_as_expected: bool
    tests_passed_after_restore: bool
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.tests_failed_as_expected and self.tests_passed_after_restore


class KillTest:
    """
    Un kill test individuel.
    
    IMPORTANT: Tous les patches utilisent unittest.mock.patch (monkeypatch).
    AUCUNE modification de fichier n'est autorisée.
    
    Le patch_func DOIT retourner un context manager qui:
    1. Applique le patch en mémoire à l'entrée
    2. Restaure automatiquement à la sortie
    """
    
    def __init__(
        self,
        name: str,
        patch_description: str,
        patch_func: Callable,
        target_test: str,
    ):
        self.name = name
        self.patch_description = patch_description
        self.patch_func = patch_func  # DOIT être un context manager (with statement)
        self.target_test = target_test
    
    def run(self, verbose: bool = False) -> KillTestResult:
        """Exécute le kill test."""
        print(f"\n{'='*60}")
        print(f"🔪 KILL TEST: {self.name}")
        print(f"   Patch: {self.patch_description}")
        print(f"   Target: {self.target_test}")
        print(f"{'='*60}")
        
        try:
            # Phase 1: Appliquer le patch et vérifier que les tests échouent
            # (in-process car patches doivent être actifs)
            print("\n📍 Phase 1: Applying patch, expecting test FAILURE...")
            
            with self.patch_func():
                failed = self._run_test(expect_failure=True, verbose=verbose, in_process=True)
            
            if not failed:
                return KillTestResult(
                    name=self.name,
                    patch_description=self.patch_description,
                    tests_failed_as_expected=False,
                    tests_passed_after_restore=False,
                    error="Tests did NOT fail with patch applied - GAP IN COVERAGE!"
                )
            
            print("   ✅ Tests failed as expected")
            
            # Phase 2: Sans patch, vérifier que les tests passent
            # (subprocess pour clean state - pas de leakage de patches)
            print("\n📍 Phase 2: Without patch, expecting test SUCCESS...")
            
            passed = self._run_test(expect_failure=False, verbose=verbose, in_process=False)
            
            if not passed:
                return KillTestResult(
                    name=self.name,
                    patch_description=self.patch_description,
                    tests_failed_as_expected=True,
                    tests_passed_after_restore=False,
                    error="Tests failed WITHOUT patch - tests are broken!"
                )
            
            print("   ✅ Tests passed after restore")
            
            return KillTestResult(
                name=self.name,
                patch_description=self.patch_description,
                tests_failed_as_expected=True,
                tests_passed_after_restore=True,
            )
            
        except Exception as e:
            return KillTestResult(
                name=self.name,
                patch_description=self.patch_description,
                tests_failed_as_expected=False,
                tests_passed_after_restore=False,
                error=str(e)
            )
    
    def _run_test(self, expect_failure: bool, verbose: bool, in_process: bool = True) -> bool:
        """
        Exécute le test cible et retourne True si comportement attendu.
        
        Si in_process=True, utilise pytest.main() (patches actifs).
        Si in_process=False, utilise subprocess (clean state).
        """
        if in_process:
            return self._run_test_in_process(verbose, expect_failure)
        else:
            return self._run_test_subprocess(verbose, expect_failure)
    
    def _run_test_in_process(self, verbose: bool, expect_failure: bool) -> bool:
        """Run with pytest.main() - patches are active."""
        import pytest
        import io
        import sys
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        if not verbose:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        
        try:
            args = [self.target_test, "-x", "-q", "--tb=no", "-p", "no:cacheprovider"]
            if verbose:
                args.append("-v")
            
            exit_code = pytest.main(args)
            test_passed = exit_code == 0
            
        finally:
            if not verbose:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        if verbose:
            print(f"   Exit code: {exit_code}")
        
        if expect_failure:
            return not test_passed
        else:
            return test_passed
    
    def _run_test_subprocess(self, verbose: bool, expect_failure: bool) -> bool:
        """Run with subprocess - clean state, no patches."""
        cmd = ["python", "-m", "pytest", self.target_test, "-x", "-q", "--tb=no"]
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        
        if verbose:
            print(f"   stdout: {result.stdout[:500] if result.stdout else ''}")
            print(f"   Exit code: {result.returncode}")
        
        test_passed = result.returncode == 0
        
        if expect_failure:
            return not test_passed
        else:
            return test_passed


# ═══════════════════════════════════════════════════════════════════════════════
# KILL TEST DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_kill_tests() -> List[KillTest]:
    """Crée la liste des kill tests."""
    tests = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL TEST 1: Quorum 2/3 → 1/3 (bypass quorum)
    # ─────────────────────────────────────────────────────────────────────────
    
    def patch_quorum():
        """Patch le quorum de 2/3 à 1/3."""
        from python.helpers import consensus_manager
        
        
        def broken_check(self):
            """Quorum cassé: 1 vote suffit."""
            count = self.get_vote_count()
            # BROKEN: 1 vote suffit au lieu de 2/3
            if count.approvals >= 1:
                self.status = consensus_manager.ConsensusStatus.APPROVED
                return True
            if count.rejections >= 1:
                self.status = consensus_manager.ConsensusStatus.REJECTED
                return True
            return False
        
        return patch.object(
            consensus_manager.DecisionProposal,
            'check_consensus',
            broken_check
        )
    
    tests.append(KillTest(
        name="QUORUM_BYPASS",
        patch_description="Change quorum from 2/3 to 1/3 (single vote approval)",
        patch_func=patch_quorum,
        target_test="tests/test_prism_tally_quorum.py",
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL TEST 2: Abstain = Approve (traitement abstention)
    # ─────────────────────────────────────────────────────────────────────────
    
    def patch_abstain():
        """Patch abstain pour compter comme approve."""
        from python.helpers import consensus_manager
        
        
        def broken_get_count(self):
            """BROKEN: Abstain compte comme approve."""
            count = consensus_manager.VoteCount()
            for vote in self.votes.values():
                if vote.vote == consensus_manager.VoteType.APPROVE:
                    count.approvals += 1
                elif vote.vote == consensus_manager.VoteType.ABSTAIN:
                    count.approvals += 1  # BROKEN: Abstain = Approve
                elif vote.vote == consensus_manager.VoteType.REJECT:
                    count.rejections += 1
                else:
                    count.unavailable += 1
                count.total += 1
            return count
        
        return patch.object(
            consensus_manager.DecisionProposal,
            'get_vote_count',
            broken_get_count
        )
    
    tests.append(KillTest(
        name="ABSTAIN_AS_APPROVE",
        patch_description="Count ABSTAIN votes as APPROVE (breaks fail-closed)",
        patch_func=patch_abstain,
        target_test="tests/test_prism_tally_quorum.py",
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL TEST 3: Evidence validation always passes (zéro hallucination bypass)
    # ─────────────────────────────────────────────────────────────────────────
    
    def patch_evidence_validation():
        """Patch pour que la validation d'evidence passe toujours."""
        from python.helpers import evidence
        
        def broken_validate(self):
            """BROKEN: Toujours retourner SUFFICIENT."""
            return evidence.EvidenceValidationResult.SUFFICIENT
        
        return patch.object(
            evidence.EvidencePack,
            'validate',
            broken_validate
        )
    
    tests.append(KillTest(
        name="EVIDENCE_ALWAYS_VALID",
        patch_description="Make evidence validation always pass (breaks strict mode)",
        patch_func=patch_evidence_validation,
        target_test="tests/test_strict_evidence_fail_closed.py",
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL TEST 4: Consensus bypass pour legal_safe
    # ─────────────────────────────────────────────────────────────────────────
    
    def patch_legal_safe_consensus():
        """Patch pour bypasser consensus sur legal_safe."""
        from python.helpers import criticality_router
        
        # Remove legal_safe from required profiles
        criticality_router.CONSENSUS_REQUIRED_PROFILES.copy()
        
        def broken_context():
            criticality_router.CONSENSUS_REQUIRED_PROFILES.discard("legal_safe")
            return patch.object(
                criticality_router,
                'CONSENSUS_REQUIRED_PROFILES',
                criticality_router.CONSENSUS_REQUIRED_PROFILES
            )
        
        # Restore after
        class BrokenContext:
            def __enter__(self):
                criticality_router.CONSENSUS_REQUIRED_PROFILES.discard("legal_safe")
                return self
            
            def __exit__(self, *args):
                criticality_router.CONSENSUS_REQUIRED_PROFILES.add("legal_safe")
        
        return BrokenContext
    
    tests.append(KillTest(
        name="LEGAL_SAFE_BYPASS",
        patch_description="Remove legal_safe from mandatory consensus profiles",
        patch_func=lambda: patch_legal_safe_consensus()(),
        target_test="tests/test_multitask_consensus_routing.py::TestMultitaskLegalSafeConsensus",
    ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL TEST 5: Simulation check bypassed
    # ─────────────────────────────────────────────────────────────────────────
    
    def patch_simulation_check():
        """Patch pour que verify_no_simulation_in_production() ne fasse rien."""
        from python.helpers import consensus_arbiter
        
        def broken_verify():
            """BROKEN: Ne vérifie rien, pas d'erreur."""
            pass
        
        return patch.object(
            consensus_arbiter,
            'verify_no_simulation_in_production',
            broken_verify
        )
    
    tests.append(KillTest(
        name="SIMULATION_CHECK_BYPASS",
        patch_description="Make verify_no_simulation_in_production() a no-op (breaks prod safety)",
        patch_func=patch_simulation_check,
        target_test="tests/test_consensus_no_simulation_prod.py::TestNoSimulationInProduction::test_verify_function_raises_in_production",
    ))
    
    return tests


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def get_git_status() -> set:
    """
    Retourne l'ensemble des fichiers modifiés/non-suivis dans git.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        return set()
    return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()


def check_git_status_unchanged(before: set, after: set) -> bool:
    """
    Vérifie que le git status n'a PAS changé pendant les kill tests.
    
    CRITIQUE: Les kill tests ne doivent JAMAIS modifier ou créer des fichiers.
    On compare l'état avant/après, pas l'état absolu (car il peut y avoir
    des modifications non-liées dans le working tree).
    """
    new_files = after - before
    if new_files:
        print(f"\n⚠️  New/modified files detected during kill tests:")
        for f in new_files:
            print(f"   {f}")
        return False
    return True


def run_all_kill_tests(verbose: bool = False, dry_run: bool = False) -> bool:
    """Exécute tous les kill tests."""
    print("\n" + "="*70)
    print("🔪 KILL TESTS — Proof of Test Sensitivity")
    print("="*70)
    print("⚠️  All patches are RUNTIME ONLY — no file modifications")
    
    # Capture git status BEFORE
    git_status_before = get_git_status()
    
    tests = create_kill_tests()
    
    if dry_run:
        print("\n📋 DRY RUN — Would execute these kill tests:\n")
        for test in tests:
            print(f"  • {test.name}")
            print(f"    Patch: {test.patch_description}")
            print(f"    Target: {test.target_test}\n")
        return True
    
    results: List[KillTestResult] = []
    
    for test in tests:
        result = test.run(verbose=verbose)
        results.append(result)
    
    # Capture git status AFTER
    git_status_after = get_git_status()
    
    # Summary
    print("\n" + "="*70)
    print("📊 KILL TESTS SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for result in results:
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"\n{status} {result.name}")
        print(f"   Patch: {result.patch_description}")
        
        if result.success:
            passed += 1
            print(f"   → Tests broke with patch: YES")
            print(f"   → Tests passed after restore: YES")
        else:
            failed += 1
            if result.error:
                print(f"   → ERROR: {result.error}")
            if not result.tests_failed_as_expected:
                print(f"   → ⚠️  GAP: Tests did NOT detect the regression!")
            if not result.tests_passed_after_restore:
                print(f"   → ⚠️  Tests are broken even without patch!")
    
    print("\n" + "-"*70)
    print(f"TOTAL: {passed}/{len(results)} passed")
    
    # CRITICAL: Verify no NEW dirty files (compare before/after)
    if not check_git_status_unchanged(git_status_before, git_status_after):
        print("\n❌ CRITICAL: Kill tests created/modified files!")
        print("   This violates the runtime-only patch requirement.")
        return False
    else:
        print("\n✅ Git status unchanged — no files modified by kill tests")
    
    if failed > 0:
        print(f"\n❌ {failed} kill test(s) FAILED — Test coverage gaps detected!")
        return False
    
    print("\n✅ All kill tests passed — Tests properly detect regressions!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Kill Tests — Proof of test sensitivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be patched without running",
    )
    
    args = parser.parse_args()
    
    success = run_all_kill_tests(
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

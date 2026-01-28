# PRISM + Evidence Deep Verification Test Suite

## Vue d'ensemble

Suite de tests complète pour valider le système de consensus PRISM et l'orchestration Evidence.

```
tests/
├── harness/                    # Harness de test déterministe
│   ├── __init__.py
│   ├── fakes.py               # FakeLLM, FakeTools, FakeMCP
│   ├── fixtures.py            # 6 scénarios E2E
│   └── assertions.py          # Assertions spécialisées
├── e2e/
│   └── test_e2e_scenarios.py  # Tests E2E complets
├── property/
│   └── test_invariants.py     # Tests de propriétés
├── test_prism_contract.py     # Contrat de vote strict
├── test_prism_timeouts.py     # Timeouts déterministes
├── test_prism_tally_quorum.py # Calcul tally & quorum 2/3
├── test_evidence_prism_integration.py  # Intégration pipeline
└── README_tests.md            # Cette documentation
```

## Commandes rapides

### FAST GATE (~2-10 secondes)
```bash
# Tests unitaires core uniquement
python tests/test_prism_contract.py
python tests/test_prism_tally_quorum.py

# Ou avec pytest
pytest tests/test_prism_contract.py tests/test_prism_tally_quorum.py -q
```

### FULL GATE (tous les tests)
```bash
# Exécuter toute la suite
python -m pytest -q

# Ou fichier par fichier
python tests/test_prism_contract.py
python tests/test_prism_timeouts.py
python tests/test_prism_tally_quorum.py
python tests/test_evidence_prism_integration.py
python tests/e2e/test_e2e_scenarios.py
python tests/property/test_invariants.py
```

### Rapport complet
```bash
python tools/test_report.py
```

## Invariants testés

### 1. Contrat de vote strict
- Schéma JSON obligatoire : `approve` (bool), `confidence` (0-1), `provider`, `reasoning`
- Types validés strictement
- Champs extra rejetés en mode strict

### 2. Timeouts déterministes
- Per-agent timeout : 250-300ms
- Global budget : ~900ms
- Timeout = REJECTED (jamais APPROVED)
- Cancellation propre (pas de tâches orphelines)

### 3. Quorum 2/3
- Minimum 2/3 des votes valides pour décision
- Abstain/UNAVAILABLE exclus du quorum
- NO_CONSENSUS si pas de majorité

### 4. Fail-closed
- Toute erreur/timeout → REJECT
- Jamais d'approbation par défaut
- Incertitude → Rejet

### 5. Anti-bypass
- Outils interdits non appelés
- Sanitization du contenu
- Pas d'injection de prompt

### 6. Déterminisme
- temp=0 forcé
- Mêmes inputs → mêmes outputs
- Seeds fixes pour reproductibilité

## Scénarios E2E

| Scénario | Description | Résultat attendu |
|----------|-------------|------------------|
| investor_dossier | Multi-sources avec contradictions | REJECTED (prudence) |
| legal_contract | Citations juridiques | APPROVED |
| finance_incoherent | Données incohérentes | REJECTED (alerte) |
| prompt_injection | Document contaminé | REJECTED + neutralisation |
| degraded_mode | 2 providers down | Fail-safe |
| idempotence | Même input x2 | Même output |

## Harness de test

### FakeLLMProvider
```python
from tests.harness.fakes import FakeLLMProvider

provider = FakeLLMProvider("arbiter_1", scenario="approve_safe")
vote = await provider.vote("action", {"context": "test"})
```

Scénarios disponibles:
- `approve_safe` : Approbation confiante
- `approve_cautious` : Approbation avec réserves
- `reject_risky` : Rejet pour risques
- `reject_uncertain` : Rejet par incertitude
- `abstain` : Abstention

### FaultInjector
```python
from tests.harness.fakes import FaultInjector, FaultType, FaultConfig

injector = FaultInjector()
injector.configure("provider_name", FaultConfig(
    fault_type=FaultType.TIMEOUT,
    delay_ms=500
))
```

Types de fautes:
- `INFRA_FAILURE` : Délai dépassé ou infra indisponible
- `SCHEMA_FAIL` : Réponse invalide
- `NETWORK_ERROR` : Erreur réseau
- `RATE_LIMIT` : Limite atteinte
- `PROMPT_INJECTION` : Injection simulée

### Assertions spécialisées
```python
from tests.harness.assertions import (
    assert_vote_schema,      # Valide schéma de vote
    assert_consensus_result, # Valide résultat consensus
    assert_audit_entry,      # Vérifie log d'audit
    assert_no_bypass,        # Vérifie anti-bypass
    assert_sanitized,        # Vérifie sanitization
    assert_idempotent,       # Vérifie idempotence
)
```

## Contraintes qualité

- ✅ **100% offline** : Aucun appel réseau
- ✅ **Zéro flaky** : Pas de sleep réel, seeds fixes
- ✅ **Messages explicites** : Assertions parlantes
- ✅ **Pas de données sensibles** dans les fixtures
- ✅ **Typage strict** (si mypy disponible)

## Ajout de tests

### Nouveau test unitaire
```python
class TestNewFeature:
    def test_feature_works(self):
        # Arrange
        manager = ConsensusManager(...)
        
        # Act
        result = await manager.propose(...)
        
        # Assert
        assert result is not None
```

### Nouveau scénario E2E
1. Ajouter la fixture dans `tests/harness/fixtures.py`
2. Créer le test dans `tests/e2e/test_e2e_scenarios.py`
3. Vérifier les assertions d'audit

## Métriques

La suite génère des métriques :
- `total_proposals` : Nombre de propositions
- `approved_proposals` : Approbations
- `rejected_proposals` : Rejets
- `timeout_proposals` : Timeouts
- `average_decision_time` : Temps moyen de décision

## Troubleshooting

### Test flaky
- Vérifier qu'il n'y a pas de `time.sleep()` réel
- Utiliser `TestClock` pour le temps virtuel
- Vérifier les seeds de random

### Timeout inattendu
- Augmenter `timeout_ms` dans le test
- Vérifier les fautes injectées
- Vérifier que les votes sont soumis

### Échec de schéma
- Vérifier les champs requis
- Utiliser `assert_vote_schema(vote, strict=False)` pour debug
- Vérifier les types (bool vs string)

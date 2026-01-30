# Checklist CTO 30 min — KOREV Evidence

**Objectif** : Vérifier en 30 minutes maximum l'état de santé du système KOREV Evidence.  
**Prérequis** : Terminal, accès au repo, Python 3.10+, clés API optionnelles pour tests live.  
**Temps estimé** : 25-30 minutes.

---

## Légende

| Symbole | Signification |
|---------|---------------|
| ✅ | PASS — Contrôle réussi |
| ❌ | FAIL — Contrôle échoué, action requise |
| ⚠️ | WARN — Non bloquant, à surveiller |

---

## Section A — Intégrité documentaire (5 min)

### A-01. Lint audit documentaire
**But** : Vérifier que l'audit respecte les règles de structure.  
**Commande** :
```bash
make audit-lint
```
**Preuve attendue** : `[PASS] Lint documentaire`  
**Critère** : PASS si 0 erreur.  
**Action corrective** : Corriger les erreurs listées par le lint.

---

### A-02. Vérification complète audit
**But** : Vérifier structure + fichiers référencés.  
**Commande** :
```bash
make audit-verify
```
**Preuve attendue** : `[PASS] Audit verification complète`  
**Critère** : PASS si exit code 0.  
**Action corrective** : Corriger l'audit ou ajouter les fichiers manquants.

---

### A-03. Pas de collision ClaimID
**But** : Vérifier qu'aucun ClaimID n'est utilisé par plusieurs briques.  
**Commande** :
```bash
grep -E "^- ClaimID:" docs/KOREV_Evidence_Audit.md | sort | uniq -d
```
**Preuve attendue** : Aucune sortie (liste vide).  
**Critère** : PASS si aucune collision détectée.  
**Action corrective** : Séparer les ClaimID en collision.

---

## Section B — Tests consensus (8 min)

### B-01. Quorum PRISM 2/3
**But** : Vérifier que le quorum 2/3 est correctement calculé.  
**Commande** :
```bash
python -m pytest tests/test_prism_tally_quorum.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/consensus_manager.py`.

---

### B-02. Consensus engine
**But** : Vérifier le moteur de consensus.  
**Commande** :
```bash
python -m pytest tests/test_prism_consensus.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/consensus/engine.py`.

---

### B-03. Fail-closed sur evidence
**But** : Vérifier le comportement fail-closed.  
**Commande** :
```bash
python -m pytest tests/test_strict_evidence_fail_closed.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/critical_decision_gate.py`.

---

## Section C — Tests routeur (5 min)

### C-01. Déterminisme routeur
**But** : Vérifier que le routeur est déterministe.  
**Commande** :
```bash
python -m pytest tests/test_router_determinism.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/router/router.py`.

---

### C-02. Détection injection
**But** : Vérifier la détection d'injection prompt.  
**Commande** :
```bash
python -m pytest tests/test_injection_handling.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/router/router.py`.

---

### C-03. Routeur criticité
**But** : Vérifier l'évaluation de criticité.  
**Commande** :
```bash
python -m pytest tests/test_criticality_router.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/criticality_router.py`.

---

## Section D — Tests pipeline legal/medical (5 min)

### D-01. Pipeline légal
**But** : Vérifier l'orchestrateur légal.  
**Commande** :
```bash
python -m pytest tests/test_legal_orchestrator.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/legal_orchestrator.py`.

---

### D-02. Contrat médical
**But** : Vérifier le contrat de sortie médical.  
**Commande** :
```bash
python -m pytest tests/test_medical_agent_hardening.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/medical_contract.py`.

---

### D-03. Intégrité claims sortie
**But** : Vérifier que les claims non sourcés sont refusés.  
**Commande** :
```bash
python -m pytest tests/test_final_output_claim_integrity.py -v --tb=short
```
**Preuve attendue** : Tous les tests PASS.  
**Critère** : PASS si 0 échec.  
**Action corrective** : Corriger `python/helpers/evidence.py`.

---

## Section E — Wiring runtime (4 min)

### E-01. Existence consensus_manager
**But** : Vérifier que le module consensus existe et est importable.  
**Commande** :
```bash
python -c "from python.helpers.consensus_manager import DecisionProposal, ConsensusStatus; print('OK')"
```
**Preuve attendue** : `OK`  
**Critère** : PASS si pas d'erreur d'import.  
**Action corrective** : Vérifier le module et ses dépendances.

---

### E-02. Existence criticality_router
**But** : Vérifier que le routeur de criticité est importable.  
**Commande** :
```bash
python -c "from python.helpers.criticality_router import CriticalityRouter; print('OK')"
```
**Preuve attendue** : `OK`  
**Critère** : PASS si pas d'erreur d'import.  
**Action corrective** : Vérifier le module et ses dépendances.

---

### E-03. Existence collaborative_consensus
**But** : Vérifier que le débat collaboratif est importable.  
**Commande** :
```bash
python -c "from python.helpers.collaborative_consensus import run_collaborative_consensus; print('OK')"
```
**Preuve attendue** : `OK`  
**Critère** : PASS si pas d'erreur d'import.  
**Action corrective** : Vérifier le module et ses dépendances.

---

### E-04. Wiring call_subordinate
**But** : Vérifier que l'outil de délégation est connecté.  
**Commande** :
```bash
grep -l "_validate_with_consensus" python/tools/call_subordinate.py && echo "WIRED"
```
**Preuve attendue** : Chemin du fichier + `WIRED`  
**Critère** : PASS si wiring détecté.  
**Action corrective** : Reconnecter le wiring consensus dans call_subordinate.

---

## Section F — Configuration & déploiement (3 min)

### F-01. Validité docker-compose
**But** : Vérifier la syntaxe du docker-compose.  
**Commande** :
```bash
docker compose -f deploy/docker-compose.yml config --quiet && echo "OK"
```
**Preuve attendue** : `OK` (pas d'erreur).  
**Critère** : PASS si syntaxe valide.  
**Action corrective** : Corriger le fichier docker-compose.yml.

---

### F-02. Variables d'environnement documentées
**But** : Vérifier que les variables clés sont documentées.  
**Commande** :
```bash
grep -E "^(OPENAI_API_KEY|ANTHROPIC_API_KEY|EVIDENCE_ENV)=" .env.example && echo "DOCUMENTED"
```
**Preuve attendue** : Variables listées + `DOCUMENTED`  
**Critère** : PASS si variables documentées.  
**Action corrective** : Mettre à jour .env.example.

---

### F-03. Volume audit logs
**But** : Vérifier que le volume d'audit est configuré.  
**Commande** :
```bash
grep -q "evidence-audit" deploy/docker-compose.yml && echo "VOLUME_OK"
```
**Preuve attendue** : `VOLUME_OK`  
**Critère** : PASS si volume configuré.  
**Action corrective** : Ajouter le volume dans docker-compose.yml.

---

## Section G — Sécurité (3 min)

### G-01. Pas de secrets dans le repo
**But** : Vérifier qu'aucun secret n'est commité.  
**Commande** :
```bash
git grep -l "sk-" --cached 2>/dev/null | grep -v ".example" | head -5 || echo "NO_SECRETS"
```
**Preuve attendue** : `NO_SECRETS`  
**Critère** : PASS si aucun secret trouvé.  
**Action corrective** : Supprimer les secrets, révoquer les clés.

---

### G-02. Protection API key handler
**But** : Vérifier que l'API requiert une clé.  
**Commande** :
```bash
grep -q "requires_api_key" python/api/api_message.py && echo "PROTECTED"
```
**Preuve attendue** : `PROTECTED`  
**Critère** : PASS si protection présente.  
**Action corrective** : Ajouter le décorateur requires_api_key.

---

### G-03. Guardrail simulation prod
**But** : Vérifier que la simulation est interdite en prod.  
**Commande** :
```bash
grep -q "EVIDENCE_ENV" python/helpers/consensus_arbiter.py && echo "GUARDRAIL_OK"
```
**Preuve attendue** : `GUARDRAIL_OK`  
**Critère** : PASS si guardrail présent.  
**Action corrective** : Ajouter la vérification d'environnement.

---

## Section H — Observabilité (2 min)

### H-01. Logs structurés consensus
**But** : Vérifier la présence de logs structurés.  
**Commande** :
```bash
grep -E "(log_event|correlation_id)" python/helpers/consensus_manager.py | head -3 && echo "LOGGING_OK"
```
**Preuve attendue** : Lignes de log + `LOGGING_OK`  
**Critère** : PASS si logging structuré.  
**Action corrective** : Ajouter le logging structuré.

---

### H-02. Métriques routeur
**But** : Vérifier la présence du module de métriques.  
**Commande** :
```bash
test -f python/helpers/router/metrics.py && echo "METRICS_OK"
```
**Preuve attendue** : `METRICS_OK`  
**Critère** : PASS si fichier existe.  
**Action corrective** : Créer le module de métriques.

---

## Récapitulatif final

| Section | Contrôles | Temps estimé |
|---------|-----------|--------------|
| A — Intégrité doc | 3 | 5 min |
| B — Consensus | 3 | 8 min |
| C — Routeur | 3 | 5 min |
| D — Legal/Medical | 3 | 5 min |
| E — Wiring | 4 | 4 min |
| F — Config/Deploy | 3 | 3 min |
| G — Sécurité | 3 | 3 min |
| H — Observabilité | 2 | 2 min |
| **TOTAL** | **24** | **~30 min** |

---

## Commande rapide (tous les tests automatisables)

```bash
# Exécuter tous les contrôles automatisables
make audit-smoke
```

---

## Post-checklist

1. Si tout est PASS : documenter la date de vérification.
2. Si FAIL : corriger avant de merger/déployer.
3. Relancer `make audit-verify` après corrections.

---

## Prompt de contrôle — Itération suivante

```
Mission: Exécuter la checklist CTO 30 min KOREV Evidence.
1. Exécuter `make audit-verify`
2. Si FAIL: corriger selon les actions correctives listées
3. Recommencer jusqu'à PASS
4. Documenter les corrections dans CHANGELOG_AUDIT.md
5. Confirmer: `[PASS] Audit verification complète`
```

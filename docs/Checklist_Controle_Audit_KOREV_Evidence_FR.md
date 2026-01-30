## Checklist CTO 30 minutes - Audit KOREV Evidence (FR)

### 0-5 min - Sanity checks
**Controle 01 - Lint documentaire (briques + claims)**
- But: verifier que l'audit respecte le modele "brique".
- Commande(s): `make audit-verify`
- Preuve attendue: sortie "PASS" du lint documentaire.
- Critere PASS/FAIL: PASS si 0 erreur.
- Action corrective si FAIL: corriger `docs/KOREV_Evidence_Audit.md` (BrickID, Statut, Preuves, Validation, Limites, ClaimID).

**Controle 02 - Structure repo minimale**
- But: verifier presence des dossiers cles.
- Commande(s): `ls docs python agents tests deploy docker`
- Preuve attendue: dossiers existants.
- Critere PASS/FAIL: PASS si dossiers listes sans erreur.
- Action corrective si FAIL: corriger l'arborescence ou la documentation.

**Controle 03 - Lancement UI (smoke)**
- But: verifier que l'UI demarre.
- Commande(s): `python run_ui.py`
- Preuve attendue: log "Starting server...".
- Critere PASS/FAIL: PASS si serveur demarre sans exception.
- Action corrective si FAIL: verifier `.env`, dependances, ports.

### 5-15 min - Briques critiques
**Controle 04 - Routage deterministe (tests)**
- But: valider le routeur deterministe.
- Commande(s): `python -m pytest tests/test_router_determinism.py -v`
- Preuve attendue: tests PASS.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: corriger `python/helpers/router/router.py`.

**Controle 05 - Detection d'injection**
- But: valider les patterns d'injection.
- Commande(s): `python -m pytest tests/test_injection_handling.py -v`
- Preuve attendue: tests PASS.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: ajuster `python/helpers/router/policy.py`.

**Controle 06 - Quorum consensus 2/3**
- But: valider le quorum et la logique NO_CONSENSUS.
- Commande(s): `python -m pytest tests/test_prism_tally_quorum.py -v`
- Preuve attendue: tests PASS.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: corriger `python/helpers/consensus_manager.py`.

**Controle 07 - Consensus PRISM (smoke)**
- But: valider le pipeline consensus minimal.
- Commande(s): `python test_consensus_simple.py`
- Preuve attendue: tests PASS en console.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: corriger consensus manager/engine.

**Controle 08 - Pipeline legal (E2E)**
- But: valider les invariants legaux.
- Commande(s): `python -m pytest tests/test_legal_orchestrator.py -v`
- Preuve attendue: tests PASS.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: corriger `python/helpers/legal_orchestrator.py`.

**Controle 09 - Contrat medical**
- But: valider le contrat medical strict.
- Commande(s): `python -m pytest tests/test_medical_agent_hardening.py -v`
- Preuve attendue: tests PASS.
- Critere PASS/FAIL: PASS si 0 echec.
- Action corrective si FAIL: corriger `python/helpers/medical_contract.py`.

### 15-25 min - Securite & observabilite
**Controle 10 - Securite API (cle)**
- But: verifier l'exigence de cle API sur handler.
- Commande(s): appeler `/api_message` sans cle (curl).
- Preuve attendue: HTTP 401.
- Critere PASS/FAIL: PASS si 401.
- Action corrective si FAIL: verifier `python/api/api_message.py`.

**Controle 11 - Logs consensus**
- But: verifier les logs structures.
- Commande(s): executer un test consensus.
- Preuve attendue: logs `consensus_tally`/`arbiter_call`.
- Critere PASS/FAIL: PASS si evenements logges.
- Action corrective si FAIL: verifier config logging.

**Controle 12 - Router metrics**
- But: verifier l'emission des metriques routeur.
- Commande(s): activer `DETERMINISTIC_ROUTER_V2=1` et executer une delegation.
- Preuve attendue: logs `[ROUTER_METRICS]`.
- Critere PASS/FAIL: PASS si logs presents.
- Action corrective si FAIL: verifier `python/helpers/router/metrics.py`.

### 25-30 min - Deploiement & conclusion
**Controle 13 - Validation docker-compose**
- But: valider la configuration docker.
- Commande(s): `docker compose -f deploy/docker-compose.yml config`
- Preuve attendue: config valide.
- Critere PASS/FAIL: PASS si sortie sans erreur.
- Action corrective si FAIL: corriger `deploy/docker-compose.yml`.

**Controle 14 - Audit final (go/no-go)**
- But: statuer sur la conformite documentaire.
- Commande(s): `make audit-verify`
- Preuve attendue: PASS.
- Critere PASS/FAIL: PASS si 0 erreur.
- Action corrective si FAIL: corriger l'audit jusqu'a PASS.

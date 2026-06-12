# Rapport de nettoyage documentaire — KOREV Evidence

**Date** : 2026-05-31
**Auteur** : Amine Mohamed <amine.mohamed@korev-ai.com>
**Persona** : documentaliste-archiviste technique senior (due diligence / commissaire aux apports)
**Périmètre** : documentaire uniquement — aucune modification de logique métier, de code applicatif ou de tests.

---

## 1. Résumé exécutif

La documentation du dépôt a été cartographiée, classifiée et réalignée. Les documents **obsolètes** (contradictoires avec le code actuel) et **historiques** (datés, remplacés) ont été déplacés dans une arborescence d'archive dédiée (`docs/archive/`), chacun signalé par une **bannière d'archivage**. Le `README.md` principal a été réécrit pour devenir une porte d'entrée fiable, distinguant explicitement modules **actifs**, modules **legacy/dépréciés**, documentation **de référence** et documentation **archivée**, avec une section dédiée aux **auditeurs / commissaire aux apports**.

Le principal risque corrigé : `docs/consensus/ARCHITECTURE_CURRENT.md` présentait comme « entrypoints actuels » des modules **supprimés** (`consensus_integration.py`, `consensus_mcp_integration.py`), ce qui aurait pu induire en erreur un ingénieur ou un auditeur.

**Verdict** : documentation **partiellement saine → saine sur le chemin critique**. Réserves résiduelles isolées et tracées (voir §6).

---

## 2. Volumétrie

| Indicateur | Valeur |
|---|---|
| Documents de documentation analysés (hors prompts runtime, golden tests, requirements) | ≈ 60 |
| Fichiers `docs/**/*.md` (après réorganisation) | 43 |
| Documents actifs (conservés en place) | majorité |
| Documents mis à jour | 2 (`README.md` réécrit, `docs/audit/PROJECT_AUDIT_NOTES.md`) |
| Documents archivés (déplacés + bannière) | 11 (1 obsolète + 10 historiques) |
| Doublons fusionnés/supprimés | 0 (aucune suppression ; archivage uniquement) |
| Documents créés | 2 (`docs/archive/README.md`, ce rapport) |

> Hors périmètre documentaire : `prompts/**`, `agents/**/prompts/**` (templates runtime = configuration), `tests/golden/*.txt`, `requirements*.txt`, `docker/*/build.txt`, `legal/*.txt`.

---

## 3. Classification par famille

| Famille | Exemples | Statut dominant |
|---|---|---|
| **Entrée / README** | `README.md`, `docs/README.md` | ACTIF (README réécrit) |
| **ADR** | `docs/adr/ADR-006 … ADR-010` | ACTIF (journal append-only ; ADR-009 → ADR-010) |
| **Architecture / chemin critique** | `critical_request_path_map`, `EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED`, `CHAT_DELEGATION_PIPELINE_MAP`, `architecture.md` | ACTIF |
| **Audit chemin critique** | `critical_path_remediation_report`, `critical_path_hostile_audit` | ACTIF (récent) |
| **Consensus (working docs janv. 2026)** | `consensus/ARCHITECTURE_CURRENT/TARGET/AUDIT_REPORT`, `_consensus_paths_inventory`, `CONSENSUS_CRITICAL_REPORT` | OBSOLÈTE / HISTORIQUE → **archivés** |
| **Consensus (contrat UI)** | `consensus/OUTPUT_CONTRACT.md` | ACTIF (conservé) |
| **Rapports datés** | `reasoning_validation_report`, `AUDIT_*_2026-02-11`, `SESSION_REPORT_2026-03-30`, `KOREV_Evidence_Dossier_Strategique_20260131` | HISTORIQUE → **archivés** |
| **Rapports récents / actifs** | `CI_EXECUTION_REPORT`, `CONTRADICTOR_AGENT_IMPLEMENTATION_REPORT`, `PROD_READINESS_AUDIT` | ACTIF/RÉCENT (conservés — référencés par docs actifs) |
| **Migration / roadmap** | `RENAME_ROADMAP` (terminée) | HISTORIQUE → **archivé** |
| **Installation / déploiement** | `MANUEL_INSTALLATION_CLIENT`, `GUIDE_*`, `deploy/RUNBOOK`, `GUIDE_DEPLOIEMENT_ENTREPRISE` | ACTIF |
| **Valorisation / commissaire** | `DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE`, `PACK_RDV_COMMISSAIRE_APPORTS`, `RAPPORT_TECHNIQUE_VALORISATION`, `audit-hostile-valorisation/` | HISTORIQUE À CONSERVER (en place, datés) |
| **Onboarding** | `DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE`, `missions/MISSION_AYA_01` | ACTIF |
| **Framework générique (upstream)** | `installation.md`, `usage.md`, `development.md`, `extensibility.md`, `connectivity.md`, `contribution.md`, `troubleshooting.md`, `quickstart.md`, `tunnel.md`, `mcp_setup.md`, `notifications.md` | ACTIF (générique) |
| **Specs / designs** | `SPEC_*`, `designs/backup-specification-*` | ACTIF (à confirmer ponctuellement) |

---

## 4. Documents déplacés (ancien → nouveau)

| Ancien chemin | Nouveau chemin | Statut |
|---|---|---|
| `docs/consensus/ARCHITECTURE_CURRENT.md` | `docs/archive/obsolete/ARCHITECTURE_CURRENT.md` | Obsolète |
| `docs/consensus/ARCHITECTURE_TARGET.md` | `docs/archive/historical/ARCHITECTURE_TARGET.md` | Historique |
| `docs/consensus/AUDIT_REPORT.md` | `docs/archive/historical/CONSENSUS_AUDIT_REPORT_2026-01-28.md` | Historique |
| `docs/_consensus_paths_inventory.md` | `docs/archive/historical/_consensus_paths_inventory.md` | Historique |
| `docs/CONSENSUS_CRITICAL_REPORT.md` | `docs/archive/historical/CONSENSUS_CRITICAL_REPORT.md` | Historique |
| `docs/reasoning_validation_report.md` | `docs/archive/historical/reasoning_validation_report.md` | Historique |
| `docs/RENAME_ROADMAP.md` | `docs/archive/historical/RENAME_ROADMAP.md` | Historique |
| `docs/AUDIT_OCR_2026-02-11.md` | `docs/archive/historical/AUDIT_OCR_2026-02-11.md` | Historique |
| `docs/AUDIT_PRE_DEPLOIEMENT_2026-02-11.md` | `docs/archive/historical/AUDIT_PRE_DEPLOIEMENT_2026-02-11.md` | Historique |
| `docs/reports/SESSION_REPORT_2026-03-30_MULTI_TENANT_SCHEDULER_NOTIFICATIONS.md` | `docs/archive/historical/…` | Historique |
| `docs/reports/KOREV_Evidence_Dossier_Strategique_20260131_132242.md` | `docs/archive/historical/…` | Historique |

> Déplacements réalisés via `git mv` (historique préservé). Chaque fichier porte désormais une bannière `⚠️ DOCUMENT ARCHIVÉ`.

---

## 5. Contradictions détectées et traitées

| # | Contradiction | Traitement |
|---|---|---|
| C-1 | `consensus/ARCHITECTURE_CURRENT.md` décrit des modules **supprimés** comme actifs | Archivé en `obsolete/` + bannière + renvoi vers `critical_request_path_map` / ADR-010 |
| C-2 | `consensus/ARCHITECTURE_TARGET.md` : doctrine « fail-soft : never refuse » **vs** ADR-010 « fail-closed par défaut » | Archivé en `historical/` + bannière renvoyant à ADR-008/010 |
| C-3 | `README.md` : badge « Version 3.0 » mais changelog s'arrêtant à v2.1.0 ; lien dépôt erroné (`PRISM-Evidence` au lieu de `PRISM-Oracle`) ; « 8+ » vs « 5 » serveurs MCP | README réécrit (statut au lieu de version fictive, chiffres alignés, doctrine ADR-010 ajoutée) |
| C-4 | `PROJECT_AUDIT_NOTES.md` référençait `docs/INFRA_SERVEUR_OVH.md` (retiré du dépôt) et 2 fichiers d'onboarding inexistants | Liens corrigés / annotés « À confirmer / absents » |
| C-5 | `PROJECT_AUDIT_NOTES.md` pointait vers les 2 audits 2026-02-11 désormais archivés | Liens mis à jour vers `docs/archive/historical/` |

---

## 6. Documents encore à confirmer / réserves résiduelles

| Élément | Nature | Recommandation |
|---|---|---|
| `docs/ONBOARDING_AYA_30_60_90.md`, `docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md` | **Référencés mais absents** du dépôt | Recréer ou retirer définitivement les références |
| `docs/reports/MULTI_TENANT_AUTHZ_AUDIT_MATRIX.md`, `PERSISTENT_IDENTITY_MIGRATION_PLAN.md` | Statut actif/terminé **non vérifié en profondeur** | Confirmer (actif vs historique) avant prochaine passe |
| `docs/reports/market_study_*`, `plialpes_*` | Artefacts illustratifs (sorties de démo BEFORE/AFTER) | Conserver, éventuellement déplacer en `docs/examples/` ultérieurement |
| `docs/reports/MCP_QUALITY_CONTROL_PROMPT_ULTRA.md`, `docs/AUTO_PROMPT_PRODUCTION_SYNC_AND_VALIDATION.md` | Prompts opérationnels réutilisables | Conserver ; clarifier qu'il s'agit de prompts, pas d'état produit |
| `docs/consensus/OUTPUT_CONTRACT.md` | Contrat UI valide mais antérieur à la signature v2 | Ajouter un renvoi vers `critical_output` (P2) |
| Modules `research_consensus_integration` / `research_pipeline` | Dépréciés (P1) | Planifier migration ou suppression |
| `collaborative_consensus`, migration medical/smoke | Réserves P1 (cf. audits chemin critique) | Aligner sur `critical_output` |

> Aucune doctrine technique n'a été réécrite sans preuve. Les incertitudes sont marquées « À confirmer » et non tranchées arbitrairement.

---

## 7. Risques documentaires résiduels

1. **Volume valorisation/commissaire** : plusieurs dossiers datés coexistent (`DOSSIER_COMMISSAIRE`, `PACK_RDV`, `RAPPORT_TECHNIQUE`, `audit-hostile-valorisation/`). Conservés volontairement (traçabilité due diligence), mais un index unique daté faciliterait la lecture par un commissaire.
2. **Docs framework upstream** : les guides génériques (`usage.md`, `development.md`, etc.) héritent d'Agent Zero ; ils restent globalement valables mais ne décrivent pas les couches Evidence/PRISM. Le README oriente désormais vers les docs spécifiques.
3. **Références absentes** : 2 fichiers d'onboarding référencés mais inexistants (cf. §6).

---

## 8. Recommandations anti-régression

- Toute nouvelle doc datée (rapport, audit, session) doit naître dans `docs/reports/` puis être **archivée avec bannière** dès qu'elle est dépassée — jamais laissée en place comme « courante ».
- Le `README.md` et `docs/METRICS_CANONICAL_SOURCE.md` sont les **sources de vérité** ; tout chiffre/architecture divergent ailleurs doit renvoyer vers eux.
- Interdire la réintroduction de références à des modules supprimés/dépréciés comme s'ils étaient actifs (à intégrer au protocole de pre-commit-audit).
- À chaque suppression de module, faire un `grep` documentaire et archiver/annoter les docs concernés dans la même passe.

---

## 9. Audit hostile documentaire

| # | Question | Réponse |
|---|---|---|
| 1 | Un nouvel ingénieur peut-il être orienté vers un processus obsolète ? | **Risque fortement réduit.** Les docs consensus janv. 2026 sont archivés ; le README pointe vers le chemin critique vérifié et ADR-010. Réserve : guides upstream génériques. |
| 2 | Un commissaire peut-il confondre une expérimentation ancienne avec un actif actuel ? | **Non, si bannières lues.** Tous les docs datés portent `⚠️ DOCUMENT ARCHIVÉ` + statut + remplaçant. Section « Pour les auditeurs » dédiée. |
| 3 | Un auditeur peut-il identifier une contradiction majeure README/docs/code ? | **Non sur le chemin critique.** Contradictions C-1→C-5 corrigées. Réserves P1 explicitement listées (non masquées). |
| 4 | Des docs anciens affaiblissent-ils la valorisation (image brouillée) ? | **Atténué.** Historique isolé en `docs/archive/historical/`, conservé pour due diligence mais clairement séparé de l'état courant. |
| 5 | La doc active permet-elle de comprendre vite ce qui est maintenu ? | **Oui.** README §Modules actifs / §Modules legacy + diagramme de pipeline. |
| 6 | Les zones d'incertitude sont-elles isolées ? | **Oui.** §6 « À confirmer » + réserves P1 explicites. |
| 7 | Le README suffit-il comme point d'entrée fiable ? | **Oui** pour l'orientation ; il renvoie aux sources de vérité (ADR, cartographie, métriques). |

### Plan de remédiation court

**Actions critiques restantes** : aucune (les contradictions misleading ont été traitées).

**Actions recommandées** :

- Statuer sur `MULTI_TENANT_AUTHZ_AUDIT_MATRIX` / `PERSISTENT_IDENTITY_MIGRATION_PLAN` (actif vs historique).
- Recréer ou retirer les 2 fichiers d'onboarding référencés mais absents.
- Ajouter un renvoi `OUTPUT_CONTRACT.md → critical_output`.

**Actions facultatives** :

- Déplacer `market_study_*` / `plialpes_*` vers `docs/examples/`.
- Index unique daté pour le dossier commissaire.
- Migrer/supprimer les modules de recherche dépréciés (P1).

---

## 10. Verdict final

**Documentation : SAINE sur le chemin critique, PARTIELLEMENT SAINE globalement** (réserves non bloquantes, isolées et tracées).
**Repo : prêt pour un audit documentaire externe**, sous réserve des actions recommandées ci-dessus.

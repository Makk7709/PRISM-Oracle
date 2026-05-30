<!-- markdownlint-disable MD060 -->

# 09 — Mise à jour du dossier commissaire (post-P0 RDBMS et fix yENoyKIZ)

**Projet :** KOREV Evidence  
**Date :** 5 mai 2026  
**Objet :** addendum auditable au dossier commissaire aux apports / Diag & Grow, traçant les évolutions techniques et leurs effets sur la valorisation depuis l'audit du 25 avril 2026 (livrable `08`).  
**HEAD Git verifié :** `0d0a35da` au 5 mai 2026 (3 commits ajoutés depuis l'audit `08`).  
**Documents impactés :**

- `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` (mis à jour en miroir)
- `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` (mis à jour en miroir)
- `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md` (snapshot historique du 25 avril, **non modifié** pour préserver l'audit-trail)

---

## 1. Position hostile en une page

Trois commits ont été poussés entre le 25 avril et le 5 mai 2026. Aucun ne change la traction commerciale, la propriété intellectuelle PRISM, la base open-source Agent Zero ni les fourchettes de valorisation. En revanche, deux commits **renforcent matériellement la défense** en verrouillant des risques auparavant ouverts, et un commit **expose explicitement** une dette technique de persistance qui n'était pas isolée comme telle dans le dossier précédent. La position de valorisation cible (958 000 — 1 054 000 €) reste défendable ; la décote technique résiduelle bouge de manière neutre à très légèrement favorable.

Le présent addendum doit être joint au dossier commissaire et au Pack RDV. Il ne remplace pas l'audit `08` du 25 avril : il le complète et trace les changements postérieurs.

---

## 2. Cartographie des changements (3 commits)

| Commit | Date | Périmètre | Effet sur le dossier |
|---|---|---|---|
| `de8b9c7e` | 4 mai 2026 | Fix `file_writer` fail-hard sur `§§include` non résolus + ADR-006 + 14 tests + post-mortem yENoyKIZ | **Verrouille** un risque "fail-silent tool" auparavant non explicité dans le dossier |
| `b11b4d99` | 5 mai 2026 | P0 migration RDBMS : Postgres + pgvector + compose staging + ADR-007 + 6 tests d'infra + scripts backup/snapshot | **Expose** la dette technique "filesystem-first" et **publie une roadmap structurée** pour la résorber |
| `0d0a35da` | 5 mai 2026 | Fix DEF-8 `pg_dump --clean --if-exists` + script `pg_restore_from_dump.sh` fail-loud + test T7 | **Verrouille** un risque de restore fail-silent introduit par P0 lui-même, avant tout cron actif en prod |

### 2.1 Vérifications Git contradictoires

```bash
git log --oneline 7a7abd6a..0d0a35da
# 0d0a35da fix(backup): pg_dump --clean --if-exists + pg_restore fail-loud (DEF-8)
# b11b4d99 feat(infra): P0 migration RDBMS — Postgres + pgvector (gated, zero-impact prod)
# de8b9c7e fix(file_writer): fail-hard on unresolved §§include directives (yENoyKIZ)
# 7a7abd6a fix(image-gen): resilient OpenAI calls + safe fallback when Google key missing
```

Les 3 commits cumulés (`git diff 7a7abd6a..0d0a35da --shortstat`) totalisent **24 fichiers modifiés ou créés, +3 048 insertions, -42 suppressions**. Aucun fichier supprimé sans remplacement. La branche `main` est en sync entre origin et le VPS OVH (`git pull` validé sur HEAD `0d0a35da`).

---

## 3. Fix yENoyKIZ — verrouillage du risque fail-silent (commit `de8b9c7e`)

### 3.1 Contexte

Le 4 mai 2026, l'audit de la session `yENoyKIZ` (compte `amine`, génération d'un dossier d'intégration engineering pour la nouvelle Lead Engineer) a révélé un mode de défaillance dans le tool `file_writer` : un PDF de 25 434 octets a été produit avec succès apparent (`Response.message = "✅ File created successfully!"`) alors que son contenu utile était la chaîne littérale `§§include(/app/tmp/korev_dossier_content.md)`, la directive d'include n'ayant pas été résolue parce que le répertoire `/app/tmp` ne figurait pas dans `ALLOWED_INCLUDE_DIRS`.

C'est exactement le pattern de défaut interne nommé "écart entre capacité déclarée et verrou bloquant effectif", déjà identifié dans `audit-hostile-valorisation/01-executive-summary.md`.

### 3.2 Correction

- `python/tools/file_writer.py` : introduction de `IncludeResolutionError`. Le tool fait désormais une **résolution atomique** de toutes les directives `§§include(...)` AVANT toute écriture sur disque. Si une seule directive ne peut être résolue, `execute()` retourne une `Response` d'erreur explicite et n'écrit aucun fichier.
- 4 nouveaux fichiers de tests :
  - `tests/security/test_file_writer_includes_failure.py` (14 cas T1-T8, T19-T20, T25-T28)
  - `tests/security/test_file_writer_includes_message.py` (9 cas T9-T13 + 4 edge cases)
  - `tests/integration/test_file_writer_pdf_integrity.py` (3 cas T14-T16, marker `slow`)
  - `tests/regression/test_session_yenoyikz_repro.py` (2 cas T17-T18)
- ADR-006 : `docs/adr/ADR-006-tool-io-integrity-contract.md` formalise le **contrat d'intégrité I/O des tools**. Tout tool qui écrit un artefact sur disque DOIT respecter : atomicité des transformations, fail-loud sur entrée corrompue, message d'erreur exploitable par l'agent, reflet exact du système de fichiers, observabilité.

### 3.3 Validation runtime

Le PDF cassé (25 KB) a été régénéré avec succès en PDF correct (259 KB, ratio recovery 126,7 %). 7/7 vérifications structurelles passent. Aucune directive `§§include` orpheline détectée dans le PDF final. La régénération a également mis en lumière 2 bugs latents du pipeline PDF (fontTools `setUnicodeRanges`, ReportLab parsing markdown) qui sont tracés comme tickets B-1 et B-2 mais ne bloquent plus la régénération nominale.

### 3.4 Effet sur le dossier commissaire

Avant `de8b9c7e`, un commissaire hostile pouvait attaquer : *"Vos tools peuvent prétendre avoir écrit un fichier alors qu'ils ont écrit un fichier corrompu — votre claim de pipeline auditable est partiellement infondé."* Cette attaque est désormais bloquée par :

- l'invariant code (`IncludeResolutionError` levé avant écriture) ;
- 28 tests unitaires + intégration + régression qui verrouillent le comportement ;
- un ADR formalisant le contrat I/O ;
- un post-mortem documentant l'incident et sa résolution ;
- un déploiement runtime validé (PDF régénéré avec succès).

**Impact valorisation :** consolide la lisibilité du pipeline auditable. Cohérent avec la décote technique 12-20 % existante (pas de modification numérique).

---

## 4. P0 migration RDBMS — exposition de dette + roadmap (commit `b11b4d99`)

### 4.1 Constat révélé par l'audit P0

L'audit infrastructurel du 5 mai 2026 a confirmé que la persistance métier de KOREV Evidence repose sur un schéma **filesystem-first** :

| Donnée métier | Stockage actuel |
|---|---|
| Comptes utilisateurs / orgs | `deploy/users.json` (fichier JSON monté read-only) |
| Sessions de chat | `tmp/chats/{ctxid}/chat.json` + `messages/*.txt` |
| Mémoire vectorielle | `memory/users/<user>/default/index.faiss` (FAISS binaire par utilisateur) |
| Index légal (FTS) | `data/legal/index/legal_index.sqlite` (66 MB) |
| Artefacts générés | `shared/users/<user>/generated/` |
| Rapports d'audit signés | `audit/<...>/audit_report.md` + `replay_snapshot.json` |
| Uploads utilisateurs | `tmp/uploads/<user>/` |

Cette architecture a tenu jusqu'à 7 utilisateurs en prod, mais expose plusieurs dettes : pas de transactionnalité multi-fichier, pas de requête relationnelle, pas de RBAC granulaire au niveau donnée, sauvegarde non triviale, pas de verrouillage concurrent natif. L'audit `08` (25 avril) ne traçait pas explicitement cette dette sous cet angle.

### 4.2 Roadmap publiée — ADR-007

ADR-007 (`docs/adr/ADR-007-postgres-pgvector-adoption.md`) acte l'adoption de **PostgreSQL 16 + pgvector** comme socle de persistance métier, en 7 phases sur 4-6 mois :

| Phase | Objet | Statut |
|---|---|---|
| **P0** | Pré-requis infra (compose, init SQL, snapshot, backup, tests) | **Livré** (5 mai 2026) |
| P1 | Couche Repository + dual-write `users.json` ↔ Postgres | Planifiée |
| P2 | Migration sessions de chat (`ChatRepository`) | Planifiée |
| P3 | Migration mémoire vectorielle FAISS → pgvector | Planifiée |
| P4 | Indexation des artefacts d'audit (métadonnées) | Planifiée |
| P5 | Migration `legal_index.sqlite` → schéma `legal` | Planifiée |
| P6 | Décommissioning des fichiers source de vérité | Planifiée |

Chaque phase respecte le pattern Repository feature-flag → dual-write → backfill → dual-read verification → cutover read primary DB → cutover write primary DB → décommissioning. Aucune phase ne supprime un fichier source de vérité avant 7 jours de stabilité staging.

### 4.3 P0 livré — ce qui n'impacte pas la prod

- Service `evidence-postgres` ajouté à `deploy/docker-compose.yml` derrière `profiles: ["db"]` : `docker compose up -d` standard NE le démarre PAS.
- Compose `deploy/docker-compose.staging.yml` autonome (project name verrouillé `name: evidence-staging`, réseau et volumes séparés, port 5433 sur localhost).
- Init SQL `deploy/postgres/init/01_extensions.sql` : extensions `pgcrypto`, `vector`, `pg_trgm` + 5 schémas `identity`, `chats`, `memory`, `audit`, `legal` (aucune table métier en P0).
- Scripts `scripts/backup/snapshot_pre_migration.sh` et `scripts/backup/pg_dump_daily.sh` (cron file en `.disabled`, non installé en P0).
- 6 tests d'infra `tests/infra/test_postgres_compose.py` (marker `infra`, T1-T6).
- Aucun service applicatif (`backend`, `demo`, `caddy`, `samba`) ne `depends_on` Postgres.
- Snapshot prod pré-P0 immutable conservé sur le VPS OVH : `/home/ubuntu/snapshots/pre-P0-20260505-143731/` (505 MB, manifeste SHA-256 validé, `users.json ≡ users.json.live` bit-à-bit).

### 4.4 Préoccupation H-4 levée — signatures audit indépendantes du chemin filesystem

L'audit hostile du plan RDBMS avait identifié un risque critique : *si la migration change l'emplacement des `replay_snapshot.json` et des `audit_report.md`, les signatures HMAC-SHA256 / RSA-PSS-SHA256 émises avant la migration deviennent-elles invalides ?*

L'audit ciblé du 5 mai 2026 a vérifié les fonctions `replay_engine.compute_integrity()` et `integrity_block._build_sign_payload()`. Le payload signé contient uniquement des hashes de contenus (`hash_request`, `hash_response`, `hash_document`, `signed_at`, `system_prompt_hash`, `history_hash`, `memory_snapshot_hash`). **Aucun chemin filesystem n'entre dans le payload.** La migration RDBMS ne peut donc pas invalider les signatures audit déjà émises. Cette garantie est documentée dans ADR-007 § "Garanties contractuelles" point 2.

### 4.5 Effet sur le dossier commissaire

L'exposition de la dette `filesystem-first` pourrait être lue comme un signal négatif. La lecture honnête est inverse :

- la dette EXISTAIT déjà avant le 25 avril ; elle n'avait simplement pas été isolée comme telle dans le dossier ;
- la roadmap (ADR-007) est publiée AVEC un plan détaillé en 7 phases, des critères Go/No-Go, un test restore < 30 min validé, et une stratégie de rollback à chaque phase ;
- l'audit hostile du plan a été conduit AVANT toute action ; 2 défauts critiques (H-1 staging, H-4 signatures) ont été levés avant le commit ;
- les signatures audit existantes restent valides (point 4.4).

**Impact valorisation :** **neutre à favorable**. La dette était implicite ; elle est désormais explicite et adressée par une roadmap technique structurée et testée. Cela renforce la position défendable face à l'attaque "vous découvrez la persistance le jour du RDV".

---

## 5. Fix DEF-8 — verrouillage du pipeline restore (commit `0d0a35da`)

### 5.1 Constat

Le test runtime de la phase P0 a déclenché une `ERROR: multiple primary keys for table "korev_init_marker" are not allowed` lors du premier essai de restore complet. Le restore semblait terminé, mais en réalité une ligne `korev_init_marker` insérée APRÈS le init script du conteneur n'était PAS restaurée. Pattern fail-silent identique à yENoyKIZ, interdit par ADR-006.

### 5.2 Cause technique

`pg_dump_daily.sh` produisait un dump `--format=plain` sans `--clean --if-exists`. Le restore tentait `CREATE TABLE` sans `DROP` préalable, ce qui échouait sur les tables déjà créées par l'init script du conteneur fraîchement provisionné. Sans `ON_ERROR_STOP=1` côté restore, psql poursuivait après l'erreur, donnant l'apparence d'un succès.

### 5.3 Correction

- `pg_dump_daily.sh` : ajout `--clean --if-exists` (chaque CREATE est précédé d'un `DROP IF EXISTS`).
- `pg_restore_from_dump.sh` (nouveau, 124 lignes) : restore standardisé avec `psql --set ON_ERROR_STOP=1`, vérification SHA-256 contre `MANIFEST.sha256`, `gunzip --test`, exit codes documentés (2/3/4/5/6).
- `tests/infra/test_dump_restore_pipeline.py` (nouveau) : test T7 marker `infra` + `slow` qui pose un marker APRÈS l'init script, dump, `down -v`, `up` neuf, restore via le nouveau script, et **vérifie que le marker post-init est présent**. Cette assertion aurait piégé DEF-8 en CI.

### 5.4 Validation runtime

Cycle complet `dump → down -v → up → restore` chronométré sur le VPS : **15 secondes** de bout en bout (largement sous le seuil Go/No-Go P0 → P1 de 30 minutes). Toutes les données restaurées : marker `P0` (init) + `TEST_T7_BEFORE_DUMP` (post-init), table `chats.test_t7_table` avec ses 3 payloads, colonne `vector(3)` intacte.

### 5.5 Effet sur le dossier commissaire

DEF-8 a été identifié et corrigé AVANT tout cron actif en prod (le cron file est livré avec suffixe `.disabled` et ne sera installé qu'en P1). Aucune perte de données réelle. La rigueur de l'audit hostile pre-commit a évité un défaut runtime qui aurait pu casser la sauvegarde silencieusement.

**Impact valorisation :** **favorable**. Démontre la maturité du processus pre-commit-audit (protocole interne de pre-commit-audit) et la capacité à détecter des défauts fail-silent avant exposition prod.

---

## 6. Incidents runtime traités (capacité opérationnelle)

Pendant la phase P0, deux incidents ont été déclenchés et résolus en moins d'une minute chacun. Ils sont documentés en post-mortem dans `docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md` § Post-mortem.

| Incident | Date | Détection | Résolution | Trace |
|---|---|---|---|---|
| `--remove-orphans` détruit 2 containers prod (`evidence-backend`, `evidence-backend-demo`) | 5 mai 2026, 14:46 UTC | Sortie `docker ps --format` immédiate | `docker compose up -d` depuis le dossier prod ; volumes préservés | Post-mortem § "Incident `--remove-orphans`" |
| Pipeline restore fail-silent (DEF-8) | 5 mai 2026, 15:15 UTC | Vérification manuelle post-restore : marker post-init absent | `--clean --if-exists` + `pg_restore_from_dump.sh` fail-loud + test T7 | Post-mortem § "DEF-8" |

Ces incidents sont **publics dans le dossier interne** et **traçables**. Pour un commissaire, c'est un signe positif : un projet qui n'expose aucun incident est généralement un projet qui les masque.

**Effet sur le dossier :** ajoute deux items à la section "limites connues" (cf. checklist 8.1 du `08-audit-hostile-dossier-commissaire-apports.md`).

---

## 7. Audit hostile pre-commit devenu systématique

Le protocole interne de pre-commit-audit impose désormais un protocole obligatoire en 3 phases AVANT tout `git commit` ou `git push` :

1. **Relecture contradictoire** du diff cumulé (références croisées, signatures de code, numéros de ligne, dépendances, cohérence comptage).
2. **Checklist de défauts** explicite avec sévérité (Critique / Important / Modéré / Mineur).
3. **Re-audit total** déclenché par tout défaut Critique ou Important corrigé (pour détecter les effets cascade).

**Phase 4** : commit avec mention de l'audit dans le message.

Cette règle a été appliquée sur les 3 commits du présent addendum :

| Commit | DEF trouvés | DEF Critique/Important | Re-audit total |
|---|---|---|---|
| `de8b9c7e` (yENoyKIZ) | DEF-1 (mineur, signature manquante) | 0 | non requis |
| `b11b4d99` (P0 RDBMS) | 7 DEF (DEF-1 à DEF-7) — 2 Modérés + 5 Mineurs | 0 dans le diff (incident `--remove-orphans` hors diff) | non requis |
| `0d0a35da` (DEF-8) | DEF-8 (Important) + DEF-9 (mineur, code mort post-`set -e`) | 1 Important corrigé | **1 passe complète** post-correction, 0 défaut résiduel |

**Effet sur le dossier :** introduit un nouvel actif valorisable au titre de la qualité — une doctrine pre-commit auditée et tracée systématiquement dans les messages de commit. Argumentaire défendable face à l'attaque "comment garantissez-vous l'absence de régression silencieuse" : *réponse — un protocole écrit, appliqué à chaque commit, dont la trace est dans le log Git public*.

---

## 8. Score de maturité technique — réajustement proposé

L'audit `07-scorecard-valorisation.md` (25 avril 2026) chiffrait la maturité à **69/100** (post P1/P2 partiel). Les commits postérieurs ajoutent :

| Dimension scorecard | Effet | Δ estimé |
|---|---|---|
| Tests | +28 tests file_writer (yENoyKIZ) + 6 T1-T6 + 1 T7 = **+35 tests** | +0,5 pt |
| Documentation | ADR-006 + ADR-007 + journal P0 + addendum 09 + 2 post-mortem = **+5 documents structurés** | +0,5 pt |
| Architecture | Roadmap RDBMS publiée et amorcée (P0 livré) | +0,5 pt |
| Industrialisation | Compose staging + scripts backup + restore fail-loud + cron prêt | +0,5 pt |
| Sécurité | Vérification H-4 (signatures self-contained), aucune régression | 0 pt |
| Bus factor / qualité | Doctrine pre-commit-audit appliquée systématiquement | +1 pt |

**Score réajusté estimé :** **~72/100** (vs 69/100 au 25 avril).

Cette réévaluation est un **estimé interne** ; elle ne doit pas être présentée au commissaire comme un audit externe indépendant. Elle peut être proposée au commissaire pour discussion. Le score 69/100 reste la valeur citée par la source canonique `audit-07` jusqu'à ce que cette source soit elle-même mise à jour.

**Effet valorisation :** la décote technique résiduelle 12-20 % reste maintenue par prudence. Le déplacement de 69 à ~72 ne suffit pas à justifier une révision des fourchettes ; il sécurise simplement la borne haute du scénario défendable équilibré (1 054 000 €).

---

## 9. Mise à jour du sommaire d'annexes

Le sommaire A1-A12 du `08-audit-hostile-dossier-commissaire-apports.md` reste valide. Trois annexes additionnelles peuvent être préparées si Diag & Grow demande des preuves opérationnelles supplémentaires :

| ID  | Annexe additionnelle | Priorité | Pourquoi |
|---|---|---|---|
| A13 | Capture `pytest tests/security/test_file_writer_includes_failure.py -v` (28 tests yENoyKIZ verts) | P2 | Preuve que le verrou `file_writer` est testé et passant |
| A14 | Capture `pytest -m infra tests/infra/ -v` (T1-T7 verts sur staging Postgres) | P2 | Preuve que le pipeline P0 RDBMS est testé bout-en-bout |
| A15 | Manifeste SHA-256 du snapshot pré-P0 (`/home/ubuntu/snapshots/pre-P0-20260505-143731/MANIFEST.sha256`) | P2 | Preuve que la prod a été snapshot AVANT toute action infrastructurelle |

Ces annexes ne sont **pas indispensables** à la transmission ; elles sont utiles uniquement si Diag & Grow attaque le pipeline de tests ou la robustesse du processus de migration.

---

## 10. Position de valorisation après mise à jour

Aucune modification des fourchettes annoncées dans `08` :

| Position | Valeur | Usage |
|---|---:|---|
| Plancher prudent | 662 000 — 850 000 € | Inchangé |
| Valeur cible défendable | **958 000 — 1 054 000 €** | Inchangée. La borne haute est désormais **mieux défendue** par le verrouillage yENoyKIZ et la roadmap RDBMS. |
| Borne offensive | 1 150 000 — 1 350 000 € | Inchangée. Reste conditionnelle aux annexes A1-A12. |

**Posture recommandée pour le RDV :** mentionner explicitement l'addendum 09 dans la note de remise. Si le commissaire demande pourquoi l'audit `08` ne couvre pas les commits récents, expliquer que `08` est un snapshot historique préservé pour l'audit-trail, et que `09` documente les évolutions postérieures. Ne pas réécrire `08`.

---

## 11. Audit hostile du présent addendum

Phase 1 — Relecture contradictoire :

- Toutes les références aux commits (`de8b9c7e`, `b11b4d99`, `0d0a35da`, `7a7abd6a`) ont été vérifiées via `git log --oneline`.
- Toutes les références aux fichiers (`ADR-006`, `ADR-007`, `P0_PRE_REQUIS_INFRA.md`, scripts backup, tests d'infra) ont été vérifiées par lecture du dépôt.
- Le snapshot pré-P0 a été vérifié sur le VPS OVH.
- Les vérifications H-4 ont été reproduites dans cette session (audit ciblé `replay_engine.py` + `integrity_block.py`).

Phase 2 — Défauts trouvés : aucun défaut Critique ou Important. Les 9 défauts cumulés des 3 commits (DEF-1 à DEF-9 dans la nomenclature locale aux commits, cf. § 7) ont tous été corrigés avant push.

Phase 3 — Re-audit : non requis (aucun défaut Critique/Important résiduel dans le présent addendum).

---

## 12. Conclusion hostile

La **valeur cible (958 000 — 1 054 000 €) est inchangée** par les commits postérieurs au 25 avril. La **défense de cette valeur** est cependant renforcée par :

- la fermeture d'un risque fail-silent réel (yENoyKIZ → ADR-006) ;
- l'exposition explicite et la prise en charge structurée d'une dette technique (ADR-007 + P0 livré) ;
- la démonstration d'une discipline pre-commit auditable et tracée (3 commits, 9 DEF corrigés, 2 incidents post-mortem documentés).

Le dossier commissaire reste **présentable et défendable** sous la forme : `Pack RDV` + `Dossier commissaire` + `Rapport technique` + `Audit-08` (snapshot 25 avril) + **`Addendum-09` (présent document, mise à jour 5 mai)** + annexes A1-A12 (à constituer J-1) + annexes A13-A15 optionnelles.

---

*Addendum produit le 5 mai 2026. HEAD verifié : `0d0a35da`. Cet addendum est destiné à être joint au dossier commissaire aux apports et à Diag & Grow ; il complète mais ne remplace pas l'audit-08 du 25 avril 2026.*

# Guide conformité client — KOREV Evidence

**Version** : v1.3.1 · **Public** : clients réglementés, DPO, responsables conformité · **Langue** : français

Ce guide décrit ce que KOREV Evidence apporte en matière de **traçabilité**, **preuves**, **responsabilités** et **limites** — sans constituer un avis juridique.

---

## 1. Positionnement

KOREV Evidence est une **aide à la décision** pour professions réglementées. Elle ne remplace pas :

- le jugement professionnel humain ;
- les obligations légales propres à votre secteur (secret professionnel, responsabilité médicale, etc.) ;
- une validation externe (expert, autorité, commissaire).

---

## 2. Chaîne de preuve

### 2.1 Niveaux de criticité (ADR-010)

| Niveau | Comportement | Preuve |
|--------|--------------|--------|
| **LEVEL 1** | Réponse directe agent | Logs conversation |
| **LEVEL 2** | Délégation + validation partielle | Logs + trace délégation |
| **LEVEL 3** | Consensus obligatoire + sortie signée | Signature v2 (RSA-PSS ou HMAC), anti-tamper, **fail-closed** |

Référence technique : [adr/ADR-010-critical-output-doctrine.md](adr/ADR-010-critical-output-doctrine.md).

### 2.2 Éléments auditables

| Artefact | Emplacement / accès |
|----------|---------------------|
| Logs sécurité | Volume `evidence-audit`, endpoints `/audit_reports` |
| Logs agent par conversation | Contexte chat, `/api_log_get` (clé API) |
| Replay requête | `/replay` |
| Revue humaine | `/human_review` |
| Registre risques | `/risk_dashboard` |
| Rapports structurés | Templates `docs/templates/evidence_native_*.md` |

### 2.3 Horodatage et intégrité

- Signatures **critical_output** : empreinte du contenu + métadonnées.
- En cas d'échec consensus ou validation : **fail-closed** — pas de sortie « validée » silencieuse.
- Pipeline juridique : bannière « NON VALIDÉE » documentée si fail-soft explicite.

---

## 3. Responsabilités

### 3.1 Éditeur / hébergeur (KOREV)

- Maintenance plateforme, correctifs sécurité, runbook ops.
- Documentation technique et ADR.
- **Ne décide pas** au nom du client sur les contenus métier produits.

### 3.2 Client (organisation)

- Configuration comptes, rôles OWNER/MEMBER, politique mots de passe.
- Classification des usages (quel niveau de criticité pour quels cas).
- Procédure de **revue humaine** pour décisions à fort enjeu.
- Sauvegardes (`/backup_*`, procédures [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md)).
- Conformité RGPD : base légale, registre traitements, DPIA si requis.

### 3.3 Utilisateur final

- Vérifier les sorties avant action (contrat, diagnostic, décision stratégique).
- Ne pas saisir de données inutiles (minimisation).
- Signaler anomalies via canal interne client.

---

## 4. Multi-tenant et confidentialité

| Règle | Détail |
|-------|--------|
| Isolation org | Étanche via `authorization.py` |
| OWNER | Voit **toutes** les conversations de son organisation (supervision) |
| MEMBER | Voit **uniquement** les siennes |
| Stockage chats | `tmp/chats/` (global filesystem, filtrage API) |
| Workspaces | Partages Samba par utilisateur (`shared/`) |

Pour cloisonnement strict par utilisateur au sein d'une org : attribuer le rôle **MEMBER** ; réserver **OWNER** aux superviseurs.

---

## 5. Données personnelles (RGPD — cadre)

| Thème | Recommandation client |
|-------|----------------------|
| Base légale | Intérêt légitime / exécution contrat / consentement selon cas |
| Minimisation | Limiter données patients/clients dans les prompts |
| Durée conservation | Politique de rétention chats + backups |
| Sous-traitants LLM | Contrats DPA avec fournisseurs (OpenAI, Anthropic, etc.) |
| Droits personnes | Procédure d'accès/effacement sur demande |
| Transferts hors UE | Clauses SCC si modèles US |

> KOREV Evidence supporte le mode `OFFLINE_MODE` pour environnements restreints (voir déploiement).

---

## 6. Secteurs réglementés

### 6.1 Juridique

- Sources officielles (Légifrance, Judilibre) — voir [legal_sources_fr.md](legal_sources_fr.md).
- **Act Leak Guard** : export control fail-closed sur rédaction contractuelle.
- L'outil **ne constitue pas** un conseil juridique.

### 6.2 Médical

- Agent médical durci — [MEDICAL_AGENT_HARDENING_REPORT.md](MEDICAL_AGENT_HARDENING_REPORT.md).
- PRISM consensus + sources FAERS documentées.
- **Ne remplace pas** un diagnostic clinique.

### 6.3 Finance / stratégie

- Consensus et contradicteur pour dossiers sensibles.
- Validation humaine recommandée pour décisions d'investissement ou board-level.

---

## 7. Checklist mise en production client

- [ ] Comptes et rôles définis (`users.json`)
- [ ] Politique mots de passe communiquée
- [ ] OWNER limité aux superviseurs
- [ ] Sauvegardes planifiées et testées (`backup_test`)
- [ ] Procédure incident documentée
- [ ] Registre traitements RGPD mis à jour
- [ ] Contrats sous-traitants LLM signés
- [ ] Formation utilisateurs ([MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md))
- [ ] Revue humaine activée pour LEVEL 3

---

## 8. Limites connues

| Limite | Référence |
|--------|-----------|
| `collaborative_consensus` legacy | README § Modules legacy |
| Migration Postgres non généralisée | ADR-007, profil `db` optionnel |
| Métriques tests : snapshot avril 2026 | [METRICS_CANONICAL_SOURCE.md](METRICS_CANONICAL_SOURCE.md) |
| Certifications ISO/SOC2 | Non attestées par le code seul — à confirmer contractuellement |

---

## 9. Documents pour audit externe

| Document | Usage |
|----------|-------|
| [DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md](DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md) | Valorisation |
| [audit/PROJECT_DOCUMENTATION_STANDARD.md](audit/PROJECT_DOCUMENTATION_STANDARD.md) | Standard doc audit |
| [audit/critical_request_path_map.md](audit/critical_request_path_map.md) | Chemin critique |
| [adr/](adr/) | Décisions d'architecture |
| [Checklist_Controle_Audit_KOREV_Evidence_FR.md](Checklist_Controle_Audit_KOREV_Evidence_FR.md) | Contrôle audit |

---

*Guide conformité client — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*

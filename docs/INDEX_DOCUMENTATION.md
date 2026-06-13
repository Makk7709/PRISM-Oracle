# Index de la documentation — KOREV Evidence

**Version produit** : v1.3.1 · **Dernière mise à jour** : 2026-06-13

Ce document classe **toute la documentation active** par persona et par thème. En cas de divergence entre un document archivé et le code, **le code et les ADR les plus récents font foi**.

---

## Carte par persona

| Persona | Par où commencer | Documents clés |
|---------|------------------|----------------|
| **Utilisateur final** | [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) | Chat, criticité, scheduler, fichiers, rôles |
| **Superviseur / OWNER** | Manuel §8 + [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) | Visibilité org, audit, revue humaine |
| **Administrateur IT** | [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md) | Install, multi-user, Samba, Docker |
| **Opérateur / SRE** | [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md) + [deploy/RUNBOOK.md](../deploy/RUNBOOK.md) | Health, logs, incidents, backup |
| **Développeur** | [DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md](DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md) | Code, extensions, tests |
| **Architecte** | [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md) | Vue synthèse + liens vérifiés |
| **Intégrateur API** | [API_REFERENCE.md](API_REFERENCE.md) | ~71 endpoints REST |
| **Auditeur / DD** | README racine § Auditeurs + [PROJECT_DOCUMENTATION_STANDARD.md](audit/PROJECT_DOCUMENTATION_STANDARD.md) | ADR, chemin critique, métriques |
| **Commissaire aux apports** | [DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md](DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md) | Valorisation, preuves |

---

## 1. Utilisation & exploitation

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) | FR | Utilisateurs | **Manuel principal** — connexion, chat, criticité, scheduler, fichiers |
| [usage.md](usage.md) | EN | Utilisateurs | Guide générique (héritage Agent Zero) — boutons, outils, pièces jointes |
| [quickstart.md](quickstart.md) | EN | Utilisateurs | Démarrage rapide |
| [troubleshooting.md](troubleshooting.md) | EN | Utilisateurs | FAQ et dépannage générique |
| [notifications.md](notifications.md) | EN | Utilisateurs | Système de notifications |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | FR | Tous | Notes de version par release |
| [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) | FR | Clients réglementés | Traçabilité, preuves, responsabilités |

---

## 2. Installation & déploiement

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [installation.md](installation.md) | EN | IT / dev | Installation locale (framework générique) |
| [MANUEL_INSTALLATION_CLIENT.md](MANUEL_INSTALLATION_CLIENT.md) | FR | Client | Installation chez le client |
| [GUIDE_RAPIDE_INSTALLATION.md](GUIDE_RAPIDE_INSTALLATION.md) | FR | IT | Installation rapide |
| [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md) | FR | IT | Serveur + postes Windows + multi-user |
| [deploy/RUNBOOK.md](../deploy/RUNBOOK.md) | EN/FR | Ops | Procédures opérationnelles Docker |
| [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md) | FR | Ops / SRE | Surveillance, incidents, scheduler, backup |
| [connectivity.md](connectivity.md) | EN | Intégrateurs | Connexion externe (générique) |
| [tunnel.md](tunnel.md) | EN | IT | Tunnel externe |
| [mcp_setup.md](mcp_setup.md) | EN | IT / dev | Configuration MCP |

---

## 3. Architecture & technique

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md) | FR | Architecte / dev | **Vue synthèse Evidence** (pas Agent Zero seul) |
| [architecture.md](architecture.md) | EN | Dev | Framework générique (agents, outils, mémoire) |
| [architecture/C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md) | FR | Architecte | Diagrammes C4 (contexte, conteneurs, composants) |
| [architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) | FR | Dev / audit | Délégation agents — ancré code |
| [architecture/CHAT_DELEGATION_PIPELINE_MAP.md](architecture/CHAT_DELEGATION_PIPELINE_MAP.md) | FR | Dev | Pipeline post-chat |
| [architecture/PIPELINE_PAS_A_PAS_pour_Aya.md](architecture/PIPELINE_PAS_A_PAS_pour_Aya.md) | FR | Onboarding | Pipeline pas à pas |
| [audit/critical_request_path_map.md](audit/critical_request_path_map.md) | FR | Audit | Chemin critique réel |
| [adr/](adr/) | FR | Audit / dev | ADR-006 → ADR-010 |
| [consensus/OUTPUT_CONTRACT.md](consensus/OUTPUT_CONTRACT.md) | FR | Dev / UI | Contrat de sortie consensus |
| [API_REFERENCE.md](API_REFERENCE.md) | FR | Intégrateurs | Catalogue des endpoints REST |

---

## 4. Agents, délégation & prompts

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [PROFILS_AGENTS_REFERENCE.md](PROFILS_AGENTS_REFERENCE.md) | FR | **Interne** | Référence des 11 profils agents |
| [AUTO_PROMPT_PRODUCTION_SYNC_AND_VALIDATION.md](AUTO_PROMPT_PRODUCTION_SYNC_AND_VALIDATION.md) | FR | Ops / dev | Prompt de validation production |
| [reports/MCP_QUALITY_CONTROL_PROMPT_ULTRA.md](reports/MCP_QUALITY_CONTROL_PROMPT_ULTRA.md) | FR | Interne | Contrôle qualité MCP |

> Les prompts runtime vivent dans `prompts/` et `agents/*/prompts/` — ce ne sont pas des documents utilisateur.

---

## 5. Sécurité, multi-tenant & conformité

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [SPEC_MULTI_USER_WORKSPACE.md](SPEC_MULTI_USER_WORKSPACE.md) | FR | Dev / audit | Isolation fichiers (R1–R10) |
| [CONTROLE_FINAL_MULTI_USER.md](CONTROLE_FINAL_MULTI_USER.md) | FR | Audit | Validation multi-user |
| [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) | FR | Client | AI Act / RGPD — posture produit |
| Politique sécurité (modules + CI) | — | Tous | `python/security/`, `.github/workflows/security_ci.yml` — pas de `SECURITY.md` racine au 2026-06-13 |
| [reports/MULTI_TENANT_AUTHZ_AUDIT_MATRIX.md](reports/MULTI_TENANT_AUTHZ_AUDIT_MATRIX.md) | FR | Audit | Matrice autorisation |

---

## 6. Pipelines métier

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [legal_pipeline.md](legal_pipeline.md) | FR | Juridique | Pipeline Legal-Safe |
| [legal_pipeline_ops.md](legal_pipeline_ops.md) | FR | Ops juridique | Exploitation pipeline legal |
| [legal_sources_fr.md](legal_sources_fr.md) | FR | Juridique | Sources juridiques FR |
| [DEMONSTRATION_CABINET_AVOCATS.md](DEMONSTRATION_CABINET_AVOCATS.md) | FR | Commercial | Démo cabinet avocats |
| [MEDICAL_AGENT_HARDENING_REPORT.md](MEDICAL_AGENT_HARDENING_REPORT.md) | FR | Médical | Durcissement agent médical |

---

## 7. Développement & contribution

| Document | Langue | Public | Contenu |
|----------|--------|--------|---------|
| [DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md](DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md) | FR | Dev | Onboarding développeur |
| [ONBOARDING_DEVELOPPEUR_30_60_90.md](ONBOARDING_DEVELOPPEUR_30_60_90.md) | FR | Dev | Plan 30/60/90 jours |
| [development.md](development.md) | EN | Dev | Environnement de dev |
| [extensibility.md](extensibility.md) | EN | Dev | Extensions |
| [contribution.md](contribution.md) | EN | Contributeurs | Contribution |
| [METRICS_CANONICAL_SOURCE.md](METRICS_CANONICAL_SOURCE.md) | FR | Audit | Source canonique métriques tests |

---

## 8. Audits, valorisation & archives

| Document | Statut | Public |
|----------|--------|--------|
| [audit/PROJECT_DOCUMENTATION_STANDARD.md](audit/PROJECT_DOCUMENTATION_STANDARD.md) | Actif | Auditeur externe |
| [audit/documentation_cleanup_report_2026-05-31.md](audit/documentation_cleanup_report_2026-05-31.md) | Actif | Documentaliste |
| [DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md](DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md) | Actif (daté) | Commissaire |
| [archive/](archive/) | **Archivé** | Historique uniquement |

> **Règle** : tout document dans `docs/archive/` est historique — ne pas l'utiliser comme référence courante.

---

## Documents volontairement hors dépôt

| Document | Raison |
|----------|--------|
| `INFRA_SERVEUR_OVH.md` | Topologie production sensible — référence interne hors git public |
| `PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md` | Plan RH interne — voir [ONBOARDING_DEVELOPPEUR_30_60_90.md](ONBOARDING_DEVELOPPEUR_30_60_90.md) |

---

## Arborescence recommandée (nouveaux documents)

```text
docs/
├── INDEX_DOCUMENTATION.md          ← ce fichier (carte globale)
├── MANUEL_UTILISATEUR.md           ← utilisateur final (FR)
├── ARCHITECTURE_EVIDENCE.md        ← architecture synthèse
├── GUIDE_OPERATEUR.md              ← ops / SRE
├── GUIDE_CONFORMITE_CLIENT.md      ← conformité client
├── API_REFERENCE.md                ← intégrateurs
├── RELEASE_NOTES.md                ← versions
├── ONBOARDING_DEVELOPPEUR_30_60_90.md
├── architecture/
│   ├── C4_DIAGRAMS.md              ← diagrammes C4
│   ├── EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md
│   ├── CHAT_DELEGATION_PIPELINE_MAP.md
│   └── PIPELINE_PAS_A_PAS_pour_Aya.md
├── adr/                            ← décisions d'architecture
├── audit/                          ← audits techniques
└── archive/                        ← documents historiques
```

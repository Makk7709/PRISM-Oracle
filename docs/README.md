![KOREV Evidence Logo](../webui/public/korev-evidence-logo.svg)

# Documentation KOREV Evidence

**Version** : v1.3.1 · **Index principal** : [INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md)

Ce répertoire contient la documentation active du produit KOREV Evidence. En cas de divergence avec un document archivé, **le code et les ADR récents font foi**.

---

## Par où commencer ?

| Persona | Document |
|---------|----------|
| Utilisateur | [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) |
| Client / conformité | [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) |
| IT / installation | [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md) |
| Opérateur / SRE | [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md) |
| Développeur | [DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md](DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md) · [ONBOARDING_DEVELOPPEUR_30_60_90.md](ONBOARDING_DEVELOPPEUR_30_60_90.md) |
| Architecte | [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md) · [architecture/C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md) |
| Intégrateur API | [API_REFERENCE.md](API_REFERENCE.md) |
| Auditeur | [audit/PROJECT_DOCUMENTATION_STANDARD.md](audit/PROJECT_DOCUMENTATION_STANDARD.md) |

---

## Documents Evidence (français, prioritaires)

| Document | Contenu |
|----------|---------|
| [INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md) | **Carte complète** par persona et thème |
| [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) | Manuel utilisateur |
| [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md) | Ops, incidents, scheduler |
| [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) | Traçabilité, RGPD, responsabilités |
| [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md) | Synthèse architecture |
| [API_REFERENCE.md](API_REFERENCE.md) | 71 endpoints REST |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Notes de version |
| [ONBOARDING_DEVELOPPEUR_30_60_90.md](ONBOARDING_DEVELOPPEUR_30_60_90.md) | Plan 30/60/90 jours |

---

## Guides héritage Agent Zero (anglais)

Documentation générique du framework sous-jacent — utile pour installation locale et extensions :

- [installation.md](installation.md) — Installation et mise à jour
- [usage.md](usage.md) — Utilisation GUI
- [development.md](development.md) — Environnement de développement
- [extensibility.md](extensibility.md) — Extensions personnalisées
- [connectivity.md](connectivity.md) — Connexion externe
- [architecture.md](architecture.md) — Architecture framework (générique)
- [contribution.md](contribution.md) — Contribution
- [troubleshooting.md](troubleshooting.md) — FAQ et dépannage
- [quickstart.md](quickstart.md) — Démarrage rapide
- [notifications.md](notifications.md) — Notifications
- [mcp_setup.md](mcp_setup.md) — Configuration MCP
- [tunnel.md](tunnel.md) — Tunnel externe

> Pour l'architecture **Evidence** (criticité, consensus, fail-closed), préférer [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md) plutôt que `architecture.md` seul.

---

## Architecture détaillée

| Document | Contenu |
|----------|---------|
| [architecture/C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md) | Diagrammes C4 |
| [architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) | Délégation vérifiée |
| [architecture/CHAT_DELEGATION_PIPELINE_MAP.md](architecture/CHAT_DELEGATION_PIPELINE_MAP.md) | Pipeline post-chat |
| [audit/critical_request_path_map.md](audit/critical_request_path_map.md) | Chemin critique |
| [adr/](adr/) | ADR-006 → ADR-010 |

---

## Archives

Les documents obsolètes sont dans [archive/](archive/) — ne pas utiliser pour l'état actuel du produit.

Rapport de nettoyage : [audit/documentation_cleanup_report_2026-05-31.md](audit/documentation_cleanup_report_2026-05-31.md).

---

## Ressources externes

- Site : [korev.ai](https://korev.ai)
- Issues : [GitHub Issues](https://github.com/korevai/korev-evidence/issues)
- Sécurité : modules [`python/security/`](../python/security/) · CI [`.github/workflows/security_ci.yml`](../.github/workflows/security_ci.yml)

---

*README documentation — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*

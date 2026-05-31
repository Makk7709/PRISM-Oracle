# Documentation archivée — KOREV Evidence

> Ce dossier regroupe la documentation **non opérationnelle** : documents obsolètes ou historiques,
> conservés pour la **traçabilité**, l'**historique de conception** et la **due diligence** (commissaire aux apports).
>
> **La documentation active est prioritaire sur les documents archivés.**
> Aucun fichier de ce dossier ne doit être utilisé comme référence opérationnelle courante.

**Date de constitution** : 2026-05-31 (mission d'audit documentaire).

---

## Structure

| Dossier | Contenu |
|---|---|
| [`obsolete/`](./obsolete/) | Documents **contradictoires avec l'état réel du code** (ex. décrivent une architecture ou des modules supprimés). À ne plus utiliser. |
| [`historical/`](./historical/) | Documents **datés et corrects à leur époque**, désormais remplacés par une source plus récente. Utiles pour la traçabilité et la valorisation. |

---

## `obsolete/`

| Document | Raison | Remplacé par |
|---|---|---|
| `ARCHITECTURE_CURRENT.md` | Présente des modules supprimés (`consensus_integration.py`, `consensus_mcp_integration.py`) comme entrypoints actuels | `docs/audit/critical_request_path_map.md`, `docs/adr/ADR-010-critical-output-doctrine.md` |

## `historical/`

| Document | Date d'origine | Remplacé par |
|---|---|---|
| `ARCHITECTURE_TARGET.md` | 2026-01 | `docs/adr/ADR-008…`, `docs/adr/ADR-010…` |
| `CONSENSUS_AUDIT_REPORT_2026-01-28.md` | 2026-01-28 | `docs/audit/critical_path_remediation_report.md` |
| `CONSENSUS_CRITICAL_REPORT.md` | 2026-01-25 | `docs/audit/critical_path_remediation_report.md`, `docs/adr/ADR-010…` |
| `_consensus_paths_inventory.md` | 2026-01-25 | `docs/audit/critical_request_path_map.md` |
| `reasoning_validation_report.md` | 2026-01-24 | README §ReasoningEngine + code |
| `RENAME_ROADMAP.md` | — | néant (migration terminée) |
| `AUDIT_OCR_2026-02-11.md` | 2026-02-11 | code `python/helpers/pdf_extraction/` |
| `AUDIT_PRE_DEPLOIEMENT_2026-02-11.md` | 2026-02-11 | `docs/reports/PROD_READINESS_AUDIT.md` |
| `SESSION_REPORT_2026-03-30_MULTI_TENANT_SCHEDULER_NOTIFICATIONS.md` | 2026-03-30 | néant (trace de session) |
| `KOREV_Evidence_Dossier_Strategique_20260131_132242.md` | 2026-01-31 | `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` |

---

Voir le rapport de constitution : [`docs/audit/documentation_cleanup_report_2026-05-31.md`](../audit/documentation_cleanup_report_2026-05-31.md).

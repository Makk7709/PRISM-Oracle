# ADR-009 — Désactivation du gate de validation au point de sortie (`response`)

**Date :** 29 mai 2026
**Statut :** Accepté (état transitoire) — **Tranche B tranchée par `ADR-010-critical-output-doctrine.md`** (30 mai 2026)
**Auteur :** Amine Mohamed
**Périmètre :** `python/tools/response.py`, `python/helpers/critical_decision_gate.py`

> **Mise à jour 30/05/2026 :** l'arbitrage fail-closed/fail-soft laissé ouvert ci-dessous (section
> « Doctrine cible (provisoire) » et « Critères de réactivation ») est désormais **tranché** par
> **ADR-010** : fail-closed par défaut sur le chemin critique, fail-soft uniquement si policy explicite,
> signature obligatoire. Ce document reste la trace de l'état transitoire « gate désactivé ».

## Contexte

`python/tools/response.py` (`ResponseTool.execute`) est le point de sortie unique des réponses
finales de l'agent. Le module a été conçu pour intégrer le `CriticalDecisionGate` afin de valider
chaque réponse avant émission (consensus, evidence stricte, claims non sourcées, bannière de
fiabilité).

L'audit de mise en production du 29 mai 2026 (`docs/reports/PROD_READINESS_AUDIT.md`) a établi deux
faits vérifiés :

1. **Le gate n'est jamais exécuté.** `ResponseTool.execute` effectue un `return` direct de la
   réponse **avant** d'atteindre le bloc d'appel au gate. Tout le code de validation situé après ce
   `return` est **inatteignable (code mort)**.
2. **Le docstring du module affirmait une garantie fausse** : « Aucune réponse critique ne peut
   sortir sans validation du gate. » Cette affirmation ne correspondait pas au comportement réel.

### Cause historique de la désactivation

L'implémentation de référence (toujours présente comme code mort) est **fail-soft + fail-open** :
elle ne bloque jamais une réponse en dur ; lorsque `gate_result.can_emit` est faux, elle ajoute une
bannière « Avertissement de fiabilité / Non validé par consensus » (méthode
`_create_reliability_warning`) puis émet quand même. En cas d'exception, elle passe (fail-open).

Le symptôme à l'origine du court-circuit n'était donc pas un blocage dur, mais le déclenchement de
cette bannière sur **quasiment toutes les réponses** : hors pipeline de recherche, `consensus_result`
est presque toujours `None`, donc `can_emit` est faux, donc la bannière s'affichait
systématiquement. Le gate a été court-circuité par un `return` anticipé pour supprimer ce bruit —
supprimant du même coup toute la garantie de validation.

## Décision

1. **Acter et documenter l'état réel** : le gate de sortie est **DÉSACTIVÉ**. Le docstring du module
   et de `execute()` sont corrigés pour refléter ce fait sans ambiguïté, et renvoient au présent ADR.
2. **Ne pas changer le comportement métier maintenant.** Conformément à l'arbitrage en cours
   (doctrine fail-closed vs fail-soft non tranchée), aucune réactivation n'est effectuée dans cette
   itération. Le `return` anticipé est conservé.
3. **Conserver le code mort comme implémentation de référence** pour la réactivation (Tranche B), en
   le marquant explicitement comme inatteignable.

## Doctrine cible (provisoire, à confirmer après tests E2E)

- **Fail-soft contrôlé** hors criticité absolue : émettre avec bannière « NON VALIDÉ » visible et
  tracée (continuité de service, traçabilité).
- **Fail-closed** uniquement sur les décisions à impact fort (LEVEL 3 / actions critiques), après
  tests end-to-end et politique explicite.
- La bannière ne doit se déclencher que sur du **vrai LEVEL 3**, pas par défaut sur toute réponse.

## Critères de réactivation (Tranche B — bloquants)

La réactivation du gate ne sera effectuée que lorsque **tous** les points suivants seront satisfaits :

1. `consensus_result` est **réellement alimenté** sur le chemin de sortie (pas systématiquement
   `None` hors recherche).
2. Le déclenchement de la bannière fail-soft est **limité au LEVEL 3** (et non à toute réponse non
   accompagnée d'un consensus).
3. Doctrine fail-closed vs fail-soft **arbitrée et écrite** (politique).
4. **Tests end-to-end** entrée critique → sortie (validée / bannière / blocage selon doctrine),
   verts, exécutés dans l'environnement CI canonique (Python 3.11+/Docker).
5. Vérification qu'aucune régression de « bannière systématique » ne réapparaît.

## Conséquences

### Positives

- La fausse garantie de sécurité est levée : la documentation ne ment plus sur l'état du système.
- La dette est tracée et conditionnée à des critères objectifs et testables.
- L'implémentation fail-soft de référence reste disponible pour la réactivation.

### Négatives

- Tant que la Tranche B n'est pas réalisée, **aucune validation de sortie** (consensus/gate/evidence
  stricte) n'est appliquée aux réponses critiques émises par ce point de sortie. Ce risque est
  documenté comme **RISK-01 (CRITIQUE, ouvert)** dans `PROD_READINESS_AUDIT.md`.
- Les corrections anti-bypass (`original_query`, cf. DEF-CDG-2) restent **inertes** sur ce chemin
  jusqu'à réactivation.

## Références

- `docs/reports/PROD_READINESS_AUDIT.md` (registre de risques RISK-01, RISK-02).
- `docs/adr/ADR-008-consensus-v1-to-v2-migration.md` (point d'entrée consensus v2).
- `python/tools/response.py` (`ResponseTool.execute`, `_create_reliability_warning`).

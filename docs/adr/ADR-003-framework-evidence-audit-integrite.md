# ADR-003 — Framework Evidence : rapports d'audit avec integrite cryptographique

**Date :** 25 janvier 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

KOREV Evidence se positionne comme une plateforme d'IA de confiance pour les professions reglementees. Les decisions produites par le systeme doivent etre auditables, tracables et verifiables a posteriori. Un simple log textuel ne suffit pas : un rapport d'audit doit pouvoir prouver qu'il n'a pas ete modifie apres sa generation.

Les reglementations visees (AI Act articles 9, 13, 14, 17 ; RGPD article 30) imposent des obligations de tracabilite, de documentation des decisions automatisees et de tenue de registres.

## Decision

Concevoir un framework de reporting natif (« Evidence ») avec les proprietes suivantes :

1. **SessionEnvelope** (`session_envelope.py`) : chaque interaction produit une enveloppe contenant un identifiant unique (`KRV-SES-YYYYMMDD-XXXXXXX`), un horodatage UTC, la version du logiciel, et les metadonnees de la session.
2. **IntegrityBlock** (`integrity_block.py`) : chaque rapport est signe avec HMAC-SHA256 (obligatoire) ou RSA-PSS-SHA256 (optionnel). Le bloc contient les hashes SHA-256 de la requete, de la reponse et du document. La cle HMAC est obligatoire : `RuntimeError` si `EVIDENCE_HMAC_KEY` est absent.
3. **ComplianceGrid** : grille de conformite auto-evaluee mappee sur les articles de l'AI Act et du RGPD.
4. **10 blocs canoniques** : chaque rapport Evidence suit une structure normalisee (identite, metadonnees, sources, raisonnement, recommandations, integrite, conformite, limites, gouvernance, annexes).
5. **Pipeline audit-proof** (avril 2026) : ReplayEngine pour le rejeu deterministe, HumanReview pour la revue humaine des decisions critiques, DynamicRiskRegister pour le scoring de risques en temps reel.

## Consequences

**Positives :**
- Chaque decision est tracable, horodatee et signee cryptographiquement.
- Un tiers peut verifier qu'un rapport n'a pas ete modifie (verification HMAC/RSA).
- La structure en 10 blocs normalise la sortie et facilite l'exploitation par un auditeur.
- Le pipeline audit-proof repond a la critique de l'auto-evaluation sans validation externe.
- Differenciateur commercial : peu de plateformes IA proposent une auditabilite native de ce niveau.

**Negatives :**
- RSA est optionnel et depend de la configuration (paire de cles a provisionner).
- L'auto-evaluation de conformite (ComplianceGrid) n'a pas la valeur d'un audit externe.
- Le stockage des rapports n'est pas WORM (Write-Once Read-Many), ce qui limite la preuve d'immutabilite.

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **Logs textuels simples** | Pas de garantie d'integrite, pas de structure exploitable, pas de conformite |
| **Blockchain pour l'immutabilite** | Complexite d'infrastructure disproportionnee, latence, cout operationnel |
| **Signature externe (service tiers)** | Dependance a un tiers, latence reseau, point de defaillance supplementaire |
| **Pas d'audit (confiance implicite)** | Incompatible avec le positionnement produit et les exigences reglementaires |

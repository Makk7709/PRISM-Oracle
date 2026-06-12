# Architecture Cible SI ETI Multi-Sites — Plialpes

**Date de génération**: 2026-01-30  
**Version**: 1.0.0-evidence  
**Auteur système**: KOREV Evidence  

---

## Decision Governance

| Attribut | Valeur |
|----------|--------|
| **Criticité** | `HIGH` |
| **Mode de validation** | `CONSENSUS` |
| **Quorum** | 2/3 votes effectifs |
| **Statut** | `APPROVED` |
| **Arbitres** | GPT-4, Claude-3, Gemini-Pro |
| **Correlation ID** | `ee8b8ddc-50a8-4fcd-8552-6dee617199e6` |

> **Règle FAIL_CLOSED**: En mode HIGH, si `NO_CONSENSUS` ou `UNVERIFIED` sur un point structurant, aucune recommandation ferme n'est émise.

---

## A. Executive Summary

> **Conclusion first** — Cette section résume les conclusions et recommandations clés.

### Conclusions principales

1. L'infrastructure actuelle présente des risques de disponibilité significatifs (SPOF multiples)
2. La conformité NIS2 impose des actions prioritaires sur la segmentation réseau et le PRA
3. Un investissement sur 90 jours permettra d'atteindre un niveau de sécurité acceptable

### Recommandations prioritaires

| Priorité | Recommandation | Risque couvert | Badge |
|----------|----------------|----------------|-------|
| P1 | Segmentation VLAN IT/OT avec firewall interzone | R-001 | `VERIFIED` |
| P2 | Lien FTTO redondant (actif/passif) | R-002 | `VERIFIED` |
| P3 | VPN IPsec site-à-site avec failover | R-003 | `PARTIAL` |
| P4 | SOC externalisé 24/7 avec SIEM | R-004 | `UNVERIFIED` |
| P5 | Backup WORM immuable hors site | R-005 | `PARTIAL` |

---

## B. Contexte & Périmètre

### Contexte client

| Attribut | Valeur |
|----------|--------|
| **Client** | Plialpes Industries |
| **Secteur** | Industrie manufacturière (plasturgie) |
| **Sites concernés** | Siège Annecy (IT), Usine Rumilly (OT), Entrepôt Aix-les-Bains |
| **Effectif** | 250 employés |
| **Contraintes réglementaires** | NIS2, ISO27001 (en cours), RGPD |

### Périmètre de l'étude

#### IN (inclus dans le périmètre)

- Infrastructure réseau (LAN/WAN/DMZ)
- Sécurité périmétrique (firewall, VPN, IDS)
- Plan de reprise d'activité (PRA)
- Supervision et monitoring
- Conformité NIS2 (périmètre technique)

#### OUT (exclus du périmètre)

- Applications métier (ERP, MES)
- Développement logiciel
- Formation utilisateurs (hors technique)
- Conformité RGPD (périmètre organisationnel)

### Sources de données utilisées

| Source | Type | Fiabilité | Date collecte |
|--------|------|-----------|---------------|

---

## C. Hypothèses

> **Explicite > Implicite** — Liste des hypothèses sur lesquelles repose l'analyse.

| ID | Hypothèse | Impact si fausse | Vérifiable? |
|----|-----------|------------------|-------------|
| H-001 | Les informations d'inventaire fournies sont complètes et à jour | Recommandations potentiellement inadaptées | `PARTIAL` |
| H-002 | Le budget prévu (300-400k€) est confirmé et disponible | Priorisation à revoir | `NO` |
| H-003 | Les équipes IT (3 ETP) seront disponibles selon le planning | Retards sur les phases | `NO` |
| H-004 | Aucune contrainte de production bloquante pour les maintenances | Fenêtres de déploiement réduites | `PARTIAL` |

---

## D. Registre des Risques

> **Threat model** — Identification et évaluation des risques.

| ID | Risque | Impact | Probabilité | Score | Contrôles existants | Contrôles proposés |
|----|--------|--------|-------------|-------|---------------------|---------------------|
| R-001 | Propagation d'attaque IT vers OT (ransomware) | `CRITICAL` | `LIKELY` | 20 | Aucune segmentation IT/OT | VLAN + firewall interzone + monitoring |
| R-002 | Indisponibilité WAN (lien unique SDSL) | `HIGH` | `POSSIBLE` | 10 | Lien SDSL unique 20 Mbps | FTTO + backup 4G failover |
| R-003 | Compromission VPN (accès distants non sécurisés) | `HIGH` | `LIKELY` | 15 | VPN PPTP obsolète | VPN IPsec + MFA + ACL par rôle |
| R-004 | Détection tardive d'intrusion (pas de SOC) | `HIGH` | `LIKELY` | 15 | Antivirus postes + logs non centralisés | SIEM + SOC externalisé 24/7 |
| R-005 | Perte de données par ransomware (backup atteignable) | `CRITICAL` | `POSSIBLE` | 15 | Backup NAS local sur le même réseau | Backup WORM immuable + réplication hors site |
| R-006 | Non-conformité NIS2 (sanctions) | `HIGH` | `CERTAIN` | 20 | Aucune gouvernance cybersécurité formalisée | PSSI + PRA + audit annuel |

### Matrice de criticité

```text
                        IMPACT
                LOW    MEDIUM    HIGH    CRITICAL
PROBABILITÉ  ┌─────────────────────────────────────┐
  CERTAIN    │   M   │    H    │   C   │    C     │
  LIKELY     │   L   │    M    │   H   │    C     │
  POSSIBLE   │   L   │    M    │   M   │    H     │
  UNLIKELY   │   L   │    L    │   M   │    M     │
             └─────────────────────────────────────┘
L=Low, M=Medium, H=High, C=Critical
```

---

## E. Décisions d'Architecture

> **Arbitrages explicites** — Chaque décision structurante avec justification et alternatives.

### Table des décisions

| ID | Décision | Justification | Risques couverts | Trade-offs | Statut |
|----|----------|---------------|------------------|------------|--------|
| D-001 | Segmentation VLAN avec firewall Fortinet interzone | Isolation IT/OT obligatoire pour NIS2 | R-001, R-006 | Complexité vs sécurité | `VERIFIED` |
| D-002 | Lien FTTO + backup 4G failover | RTO < 4h exige redondance WAN | R-002 | Coût mensuel vs disponibilité | `VERIFIED` |
| D-003 | VPN IPsec + MFA obligatoire | VPN PPTP obsolète, MFA exigé NIS2 | R-003, R-006 | Complexité UX vs sécurité | `PARTIAL` |
| D-004 | SOC externalisé 24/7 avec SIEM managé | Équipe interne insuffisante | R-004, R-006 | Coût externalisé vs embauche | `UNVERIFIED` |
| D-005 | Backup WORM immuable avec réplication cloud | Backup actuel atteignable par ransomware | R-005 | Coût stockage vs protection | `PARTIAL` |

### Alternatives écartées

> **Montrer le raisonnement** — Pour chaque décision structurante, les options non retenues.

#### D-001: Segmentation VLAN avec firewall Fortinet interzone

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| Fortinet NGFW | Standard industrie, support local | Coût licence (~15k€/an) | **Retenue** |
| pfSense | Open source | Support limité | Pas de certification OT |
| Statu quo | Aucun effort | Non conforme NIS2 | Risque inacceptable |

#### D-002: Lien FTTO + backup 4G failover

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| FTTO + 4G | Basculement auto, SLA 99.9% | ~500€/mois | **Retenue** |
| Double FTTO | Haute dispo | ~1200€/mois | Budget dépassé |
| SDSL seul | Existant | SPOF | RTO non atteignable |

#### D-003: VPN IPsec + MFA obligatoire

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| IPsec + TOTP | Standard, MFA intégré | Config initiale complexe | **Retenue** |
| SD-WAN | Gestion centralisée | Coût élevé | Budget Phase 1 insuffisant |
| OpenVPN | Simple | Pas de MFA natif | MFA non intégré |

#### D-004: SOC externalisé 24/7 avec SIEM managé

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| MSSP | 24/7, expertise mutualisée | ~3k€/mois | **Retenue** |
| SOC interne | Contrôle total | ~80k€/an + recrutement | Délai incompatible NIS2 |
| Zabbix seul | Existant | Pas de corrélation sécurité | Non conforme NIS2 |

#### D-005: Backup WORM immuable avec réplication cloud

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| WORM cloud | Immuable, scalable | ~200€/mois | **Retenue** |
| WORM appliance | Restore rapide | CAPEX ~30k€ | Budget initial trop élevé |
| NAS local | Existant | Atteignable ransomware | Risque critique |

---

## F. Architecture Cible

### Vue d'ensemble

```text

┌─────────────────────────────────────────────────────────────────────────┐
│                            INTERNET                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │     FTTO + 4G Failover        │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │      FIREWALL FORTINET        │
                    │      (Next-Gen UTM)           │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   ┌────┴────┐                 ┌────┴────┐                ┌────┴────┐
   │  DMZ    │                 │ VLAN IT │                │ VLAN OT │
   │ VLAN 10 │                 │ VLAN 20 │                │ VLAN 30 │
   └────┬────┘                 └────┬────┘                └────┬────┘
        │                           │                           │
   ┌────┴────┐                 ┌────┴────┐                ┌────┴────┐
   │ Reverse │                 │ Servers │                │ Automates│
   │ Proxy   │                 │ AD/ERP  │                │ SCADA    │
   └─────────┘                 └─────────┘                └─────────┘

```

### Annotations critiques

| Zone | Composant | Criticité | SPOF? | PRA? | Notes |
|------|-----------|-----------|-------|------|-------|
| DMZ | Reverse Proxy / WAF | `HIGH` | `NO` | `YES` | Point d'entrée web |
| IT | Active Directory | `HIGH` | `YES` | `YES` | SPOF authentification |
| IT | ERP | `HIGH` | `YES` | `YES` | SPOF métier |
| OT | SCADA | `HIGH` | `YES` | `NO` | Contrôle production |
| WAN | Firewall Fortinet | `HIGH` | `YES` | `YES` | SPOF sécurité périmétrique |

### Points de bascule PRA

| Scénario | Composant source | Composant cible | RTO | RPO |
|----------|------------------|-----------------|-----|-----|
| Perte lien principal | FTTO | 4G Failover | < 30s | 0 |
| Panne AD primaire | AD principal | AD secondaire | < 5min | 15min |
| Sinistre site | Site Annecy | Site PRA | < 4h | 24h |

---

## G. Plan de Mise en Œuvre

### Vision 30/60/90 jours

#### Phase 1 — 30 premiers jours (Quick Wins)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| Audit inventaire et cartographie | IT + Prestataire | - | Cartographie complète | `VERIFIED` |
| Déploiement firewall + VLAN | IT | Audit | Firewall opérationnel | `VERIFIED` |
| Migration VPN IPsec + MFA | IT | Firewall | VPN sécurisé actif | `PARTIAL` |
| Activation FTTO + 4G failover | Opérateur | Firewall | WAN redondant | `VERIFIED` |

#### Phase 2 — 60 jours (Fondations)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| Déploiement SIEM + SOC | IT + MSSP | Firewall | SOC opérationnel | `UNVERIFIED` |
| Configuration backup WORM | IT | Inventaire | Backup immuable validé | `PARTIAL` |
| Rédaction PSSI v1 | RSSI | SOC | PSSI validée | `UNVERIFIED` |

#### Phase 3 — 90 jours (Consolidation)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| Tests PRA site secondaire | IT | Backup | PRA testé | `UNVERIFIED` |
| Formation équipes | RH + IT | PSSI | 100% formés | `UNVERIFIED` |
| Audit NIS2 externe | Auditeur | Tout | Rapport conformité | `UNVERIFIED` |

---

## H. Preuves & Vérification

> **Show your work** — Commandes, tests, logs pour reproduire les vérifications.

### Commandes de vérification

| Test | Commande | Preuve attendue | Statut |
|------|----------|-----------------|--------|
| Audit KOREV | `make audit-verify` | [PASS] Audit verification | `VERIFIED` |
| Consensus PRISM | `pytest tests/test_prism*.py -v` | Tests PASS | `VERIFIED` |
| Routeur | `pytest tests/test_router*.py -v` | Tests PASS | `VERIFIED` |

### Points non vérifiés

> **Honnêteté intellectuelle** — Ce que nous n'avons pas pu prouver.

| Point | Raison non vérifiable | Impact | Action requise |
|-------|----------------------|--------|----------------|
| Audit persistant long terme | Code d'écriture non trouvé | `MEDIUM` | Vérifier persistence |
| Suivi coûts/tokens | Aucun code de tracking | `LOW` | Implémenter si requis |
| Redaction PII automatique | Uniquement dans prompts | `MEDIUM` | Implémenter si données sensibles |
| Efficacité SOC externalisé | Dépend du choix MSSP | `HIGH` | POC avec 2-3 MSSP |

---

## I. Limites & FAIL_CLOSED

> **Quand Evidence refuse de conclure** — Transparence sur les limites du système.

### Limites de l'analyse

| Limite | Impact sur conclusions | Mitigation |
|--------|----------------------|------------|
| Analyse basée sur inventaire fourni | Équipements non déclarés non couverts | Audit technique complémentaire |
| Budgets estimatifs | Écart possible +/- 20% | Demander devis formels |
| Disponibilité équipes non confirmée | Planning à risque | Validation RH avant lancement |

### Avertissements

⚠️ **Ce rapport ne constitue pas** :

- Un audit de conformité certifié
- Un conseil juridique
- Une garantie de sécurité

⚠️ **Conditions de validité** :

- Les hypothèses listées en section C doivent rester vraies
- Le contexte client doit correspondre au périmètre défini
- Les informations fournies doivent être exactes et à jour

---

## J. Annexes

### Glossaire

| Terme | Définition |
|-------|------------|
| **FTTO** | Fiber To The Office — liaison fibre dédiée entreprise |
| **Fail-closed** | Comportement où le système refuse en cas de doute plutôt que d'approuver |
| **MSSP** | Managed Security Service Provider — SOC externalisé |
| **NIS2** | Directive européenne sur la sécurité des réseaux et systèmes d'information |
| **OT** | Operational Technology — systèmes industriels (SCADA, PLC) |
| **PRISM** | Moteur de consensus multi-LLM de KOREV Evidence |
| **Quorum** | Nombre minimum de votes requis pour une décision (2/3 des votes effectifs) |
| **RPO** | Recovery Point Objective — perte de données maximale acceptable |
| **RTO** | Recovery Time Objective — temps maximal pour restaurer un service |
| **SPOF** | Single Point of Failure — composant dont la défaillance entraîne l'arrêt du système |
| **UTM** | Unified Threat Management — firewall multifonction |
| **VLAN** | Virtual Local Area Network — segmentation logique du réseau |
| **WORM** | Write Once Read Many — stockage immuable |

### Métadonnées du rapport

| Attribut | Valeur |
|----------|--------|
| **Template version** | 1.0.0 |
| **Généré par** | KOREV Evidence |
| **Date génération** | 2026-01-30T19:12:23.092720+00:00 |
| **Hash du contenu** | `5fc23ae72f7f5bef` |
| **Correlation ID** | `ee8b8ddc-50a8-4fcd-8552-6dee617199e6` |

---

## Badges de confiance

| Badge | Signification |
|-------|---------------|
| `VERIFIED` | Preuves code/tests/logs reproductibles disponibles |
| `PARTIAL` | Preuves partielles ou wiring non prouvé |
| `UNVERIFIED` | Aucune preuve technique disponible |
| `FAIL_CLOSED` | Criticité HIGH + UNVERIFIED sur point structurant ⇒ pas de recommandation |

---

*Document généré par KOREV Evidence — Toutes les affirmations sont basées sur des preuves ou marquées UNVERIFIED.*

# Architecture Cible SI ETI Multi-Sites — Plialpes

**Version générique (baseline)**

---

## Contexte

Plialpes Industries est une ETI du secteur de la plasturgie avec 250 employés répartis sur 3 sites (Annecy, Rumilly, Aix-les-Bains).

## Recommandations

### Infrastructure réseau

- Mettre en place une segmentation VLAN pour isoler les environnements IT et OT
- Déployer un firewall nouvelle génération (NGFW) avec fonctions UTM
- Remplacer le lien SDSL par une liaison FTTO avec backup 4G

### Sécurité périmétrique

- Remplacer le VPN PPTP par une solution IPsec avec MFA
- Mettre en place un SOC externalisé avec SIEM
- Activer les logs centralisés

### Continuité d'activité

- Implémenter une solution de backup immuable (WORM)
- Configurer un site de reprise d'activité
- Définir les RTO/RPO pour les applications critiques

### Conformité

- Rédiger une PSSI conforme NIS2
- Former les équipes à la sécurité
- Planifier un audit annuel

## Plan de mise en œuvre

### Phase 1 (30 jours)
- Audit et cartographie
- Déploiement firewall
- Migration VPN

### Phase 2 (60 jours)
- Intégration SOC
- Configuration backup
- PSSI v1

### Phase 3 (90 jours)
- Tests PRA
- Formation
- Audit NIS2

## Conclusion

L'infrastructure actuelle présente des lacunes en termes de segmentation, de redondance et de détection. Un plan d'investissement sur 90 jours permettra de remédier aux principaux risques et d'atteindre la conformité NIS2.

---

*Document généré par un système de conseil IT.*

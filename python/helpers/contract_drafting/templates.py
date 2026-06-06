"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CONTRACT DRAFTING GUARDED — TEMPLATES CONTRACTUELS                ║
║                                                                              ║
║  Templates de contrat de licence ON-PREM + maintenance/support.             ║
║  Variables injectables: {client_name}, {editor_name}, {software_name}, etc. ║
║                                                                              ║
║  Sections:                                                                   ║
║    CP       — Conditions Particulières                                       ║
║    CG       — Conditions Générales                                           ║
║    ANNEXE_1 — Description du logiciel                                       ║
║    ANNEXE_2 — SLA / Support / Maintenance                                   ║
║    ANNEXE_3 — Sécurité                                                      ║
║    ANNEXE_4 — DPA RGPD (conditionnel)                                       ║
║    ANNEXE_5 — Réversibilité / Fin de contrat                                ║
║    ANNEXE_6 — Grille tarifaire                                              ║
║                                                                              ║
║  SÉCURITÉ:                                                                   ║
║    - Aucun template ne doit contenir de remise/cession de code source       ║
║    - DPA conditionnel uniquement si accès distant                           ║
║    - Plafond de responsabilité obligatoire                                  ║
║    - Primauté des CP sur les CG (art. 1171)                                ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from datetime import date
from typing import Dict, List

from python.helpers.contract_drafting.models import TemplateVersion

# Constantes (déduplication littéraux — python:S1192)
_REVIEWER_INTERNAL = "KOREV Legal — Internal Review"
_SEP_LINE = "══════════════════════════════════════════════════════"


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: CONDITIONS PARTICULIÈRES (CP)
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_CP = """
═══════════════════════════════════════════════════════
PROJET DE CONTRAT — À VALIDER PAR UN JURISTE QUALIFIÉ
═══════════════════════════════════════════════════════

CONDITIONS PARTICULIÈRES
CONTRAT DE LICENCE LOGICIEL ON-PREMISE + MAINTENANCE/SUPPORT

Entre les soussignés :

L'ÉDITEUR :
    Raison sociale : {editor_name}
    Adresse : {editor_address}
    SIRET : {editor_siret}
    Ci-après dénommé « l'Éditeur »

LE CLIENT :
    Raison sociale : {client_name}
    Adresse : {client_address}
    SIRET : {client_siret}
    Ci-après dénommé « le Client »

IL A ÉTÉ CONVENU CE QUI SUIT :

Article CP.1 — Objet
Le présent contrat a pour objet la concession par l'Éditeur au Client d'un droit
d'usage (licence) du logiciel {software_name}, dans les conditions définies ci-après
et dans les Conditions Générales jointes.

Article CP.2 — Logiciel licencié
Nom : {software_name}
Version : {software_version}
Description : voir Annexe 1

Article CP.3 — Métrique de licence
Mode de licence : {licence_metric}
Nombre initial : {initial_posts} poste(s)
Extension maximale : {max_posts} poste(s)
Les extensions au-delà du nombre initial font l'objet d'un avenant.

Article CP.4 — Déploiement
Mode : ON-PREMISE (installation sur postes du Client)
Phase pilote : {initial_posts} poste(s) pendant {pilot_duration}
Déploiement progressif : jusqu'à {max_posts} poste(s)

Article CP.5 — Durée
Durée initiale : {contract_duration}
Renouvellement : tacite reconduction par périodes de {renewal_period}, sauf
dénonciation par l'une des Parties avec un préavis de {notice_period}.

Article CP.6 — Prix
Voir Annexe 6 — Grille tarifaire

Article CP.7 — Juridiction et droit applicable
Droit applicable : Droit français
Juridiction compétente : {jurisdiction}

Article CP.8 — Hiérarchie des documents contractuels
En cas de contradiction entre les documents contractuels, les Conditions
Particulières prévalent sur les Conditions Générales et les Annexes.
Les Annexes complètent les Conditions Générales et Particulières.

Article CP.9 — Contacts
Contact Éditeur : {editor_contact}
Contact Client : {client_contact}

═══════════════════════════════════════════════════════
PROJET — Ce document n'a pas de valeur contractuelle.
À valider par un juriste qualifié avant toute signature.
═══════════════════════════════════════════════════════
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: CONDITIONS GÉNÉRALES (CG)
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_CG = """
CONDITIONS GÉNÉRALES DE LICENCE LOGICIEL ON-PREMISE

Article 1 — Définitions
« Logiciel » : le logiciel {software_name} tel que décrit à l'Annexe 1.
« Licence » : droit d'usage non exclusif, non cessible, non transférable.
« Client » : la personne morale identifiée aux Conditions Particulières.
« Éditeur » : la société {editor_name}, titulaire des droits de propriété
intellectuelle sur le Logiciel.
« Poste » : une station de travail physique ou virtuelle sur laquelle le
Logiciel est installé.
« Utilisateur » : toute personne physique autorisée par le Client à utiliser
le Logiciel dans les limites de la Licence.

Article 2 — Objet
Les présentes Conditions Générales définissent les droits et obligations des
Parties dans le cadre de la licence d'usage du Logiciel accordée par l'Éditeur
au Client.

Article 3 — Licence d'usage
3.1 L'Éditeur concède au Client une licence d'usage non exclusive, non cessible
et non transférable du Logiciel, pour un usage strictement interne au Client.
3.2 La licence est limitée au nombre de postes et/ou d'utilisateurs défini aux
Conditions Particulières.
3.3 Le Client s'interdit de :
    a) mettre le Logiciel à disposition de tiers ;
    b) sous-licencier, revendre ou céder le Logiciel ;
    c) procéder au reverse engineering, à la décompilation ou au désassemblage
       du Logiciel (sauf dans les limites prévues par les articles L.122-6-1
       et suivants du Code de la propriété intellectuelle) ;
    d) extraire massivement les données, prompts, modèles ou algorithmes ;
    e) contourner les mesures techniques de protection ou de sécurité.

Article 4 — Propriété intellectuelle
4.1 Le Logiciel, ses mises à jour, sa documentation, son architecture, ses
prompts, modèles et algorithmes sont et demeurent la propriété exclusive de
l'Éditeur. Aucun transfert de propriété n'est opéré par le présent contrat.
4.2 La licence accordée constitue uniquement un droit d'usage dans les
conditions définies au présent contrat.
4.3 Développements spécifiques : sauf stipulation contraire aux Conditions
Particulières, les développements spécifiques réalisés par l'Éditeur pour
le compte du Client restent la propriété de l'Éditeur. Le Client bénéficie
d'une licence d'usage sur ces développements.
4.4 Clause « feedback » : les retours, suggestions et signalements du Client
peuvent être librement réutilisés par l'Éditeur pour améliorer le Logiciel,
sans compensation additionnelle.

Article 5 — Maintenance et support
Les conditions de maintenance et de support sont définies à l'Annexe 2.

Article 6 — Sécurité
Les mesures de sécurité sont définies à l'Annexe 3.

Article 7 — Données personnelles
7.1 En mode ON-PREMISE, les données traitées par le Logiciel sont hébergées
et stockées exclusivement sur les infrastructures du Client. Le Client est
responsable de traitement au sens du RGPD.
7.2 L'Éditeur n'accède aux données du Client que dans le cadre d'un support
technique expressément autorisé par le Client, dans les conditions définies
à l'Annexe 3 (Sécurité) et, le cas échéant, à l'Annexe 4 (DPA RGPD).
7.3 Si un accès distant par l'Éditeur implique un traitement de données
personnelles, l'Annexe 4 (DPA RGPD art. 28) s'applique obligatoirement.

Article 8 — Confidentialité
8.1 Chaque Partie s'engage à ne pas divulguer les informations confidentielles
de l'autre Partie, pendant la durée du contrat et 5 ans après son terme.
8.2 Sont confidentielles : les spécifications techniques, les données
commerciales, les conditions financières, le code et l'architecture du Logiciel.

Article 9 — Responsabilité
9.1 Plafond : la responsabilité totale de l'Éditeur, toutes causes confondues,
ne saurait excéder le montant total payé par le Client au titre du contrat
sur les 12 derniers mois précédant le fait générateur.
9.2 Exclusion des dommages indirects : l'Éditeur ne pourra être tenu responsable
des dommages indirects (perte de chiffre d'affaires, perte de données,
préjudice d'image, manque à gagner).
9.3 Carve-outs : les limitations ci-dessus ne s'appliquent pas en cas de :
    a) dol ou faute lourde ;
    b) violation des obligations de confidentialité ;
    c) violation imputable d'obligations RGPD ;
    d) atteinte aux droits de propriété intellectuelle de l'Éditeur.
9.4 Obligation essentielle (art. 1170 C. civ.) : aucune clause du présent
contrat ne saurait vider de sa substance l'obligation essentielle de l'Éditeur
de fournir une licence d'usage fonctionnelle et un support/maintenance conforme.

Article 10 — Durée et résiliation
10.1 La durée est définie aux Conditions Particulières.
10.2 Résiliation pour faute : en cas de manquement grave non remédié dans un
délai de 30 jours suivant mise en demeure par LRAR.
10.3 Effets de la résiliation : voir Annexe 5 (Réversibilité).

Article 11 — Hiérarchie et interprétation
11.1 En cas de contradiction entre les Conditions Particulières et les
Conditions Générales, les Conditions Particulières prévalent (art. 1171 C. civ.).
11.2 Le présent contrat est le fruit d'une négociation réelle entre les Parties
(contrat négocié, non contrat d'adhésion).

Article 12 — Droit applicable et litiges
12.1 Le présent contrat est régi par le droit français.
12.2 En cas de litige, les Parties s'engagent à rechercher une solution amiable
pendant un délai de 60 jours. À défaut, le litige sera porté devant la
juridiction compétente définie aux Conditions Particulières.
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 1 — Description du logiciel
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_1 = """
ANNEXE 1 — DESCRIPTION DU LOGICIEL

1. Nom du logiciel : {software_name}
   Version : {software_version}

2. Description fonctionnelle
   {software_description}

3. Modules inclus
   {software_modules}

4. Limites d'usage
   - Le Logiciel est conçu pour un usage professionnel interne au Client.
   - Nombre maximal de postes : {max_posts}
   - Le Client ne dispose d'aucun droit sur le code source, l'architecture
     interne, les prompts ou les modèles du Logiciel.
   - Toute utilisation hors du périmètre défini requiert un avenant écrit.

5. Pré-requis techniques
   - Système d'exploitation : {os_requirements}
   - Configuration minimale : {hardware_requirements}
   - Réseau : {network_requirements}
   - Droits d'administration locale requis pour l'installation.
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 2 — SLA / Support / Maintenance
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_2 = """
ANNEXE 2 — SUPPORT / MAINTENANCE / NIVEAUX DE SERVICE

1. Périmètre de la maintenance
   La maintenance comprend :
   - Correctifs de sécurité (patches critiques)
   - Mises à jour fonctionnelles (évolutions mineures et majeures)
   - Livraison en mode ON-PREM : package d'installation + notes de version

2. Canal de support
   - Canal : ticket par email ({support_email})
   - Horaires : jours ouvrés, 9h — 18h (heure de Paris)

3. Niveaux de criticité

   P1 — CRITIQUE
   Définition : Logiciel totalement indisponible ou perte de données imminente.
   Délai de prise en charge : 4 heures ouvrées
   Délai de résolution cible : 1 jour ouvré
   Escalade : automatique si non résolu sous 8h ouvrées

   P2 — MAJEUR
   Définition : Fonctionnalité essentielle dégradée, contournement possible.
   Délai de prise en charge : 8 heures ouvrées
   Délai de résolution cible : 3 jours ouvrés

   P3 — MINEUR
   Définition : Anomalie mineure, pas d'impact significatif sur la production.
   Délai de prise en charge : 2 jours ouvrés
   Délai de résolution cible : prochaine version planifiée

4. Exclusions
   - Dysfonctionnements causés par une modification du Logiciel par le Client
   - Utilisation non conforme à la documentation
   - Problèmes liés à l'infrastructure du Client (réseau, OS, matériel)

5. Procédure de mise à jour ON-PREM
   - Fréquence : {update_frequency}
   - Livraison : package d'installation signé + checksum
   - Le Client est responsable de la sauvegarde préalable de ses données
   - L'Éditeur fournit les notes de version et la procédure d'installation
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 3 — Sécurité
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_3 = """
ANNEXE 3 — SÉCURITÉ

1. Principes généraux
   - Le Client héberge le Logiciel sur ses propres infrastructures.
   - L'Éditeur n'a aucun accès permanent aux données ou systèmes du Client.

2. Accès support à distance (si applicable)
   - Tout accès distant de l'Éditeur aux systèmes du Client requiert une
     autorisation écrite préalable du Client.
   - L'accès est limité dans le temps (session unique, durée définie).
   - L'accès se fait via un canal sécurisé (VPN, outil de prise en main agréé).

3. Journalisation et traçabilité
   - Toute intervention de support à distance fait l'objet d'un compte-rendu
     écrit transmis au Client sous 48h ouvrées.
   - Les logs d'accès sont conservés {log_retention_period}.
   - Le Client peut auditer les logs d'accès sur demande écrite.

4. Mesures de sécurité de l'Éditeur
   - Chiffrement des communications (TLS 1.2 minimum)
   - Authentification forte pour tout accès aux environnements de production
   - Tests de sécurité réguliers (au minimum annuels)
   - Notification d'incident de sécurité sous 72h

5. Responsabilité du Client
   - Le Client est responsable de la sécurité de son infrastructure.
   - Le Client s'assure que les postes respectent les pré-requis techniques
     (voir Annexe 1) et sont protégés par un antivirus à jour.
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 4 — DPA RGPD (conditionnel)
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_4_CONDITIONAL = """
ANNEXE 4 — ACCORD DE TRAITEMENT DES DONNÉES PERSONNELLES (DPA)
[Cette annexe est conditionnelle — applicable uniquement si l'Éditeur
accède à distance aux systèmes du Client ou traite des données personnelles
pour le compte du Client. Si non applicable, cette annexe est sans objet.]

Statut : {dpa_status}

En application de l'article 28 du RGPD, les Parties conviennent de ce qui suit :

1. Rôles
   - Responsable de traitement : {client_name} (le Client)
   - Sous-traitant : {editor_name} (l'Éditeur)

2. Objet du traitement
   Le traitement est limité aux opérations de support technique à distance
   nécessitant un accès aux données hébergées par le Client.

3. Types de données personnelles
   {data_types}

4. Catégories de personnes concernées
   {data_subjects}

5. Durée du traitement
   Limitée à la durée de chaque intervention de support autorisée.

6. Obligations du sous-traitant
   a) Ne traiter les données que sur instruction documentée du Responsable ;
   b) Garantir la confidentialité (engagement des personnes autorisées) ;
   c) Mettre en œuvre les mesures de sécurité de l'Annexe 3 ;
   d) Ne pas engager de sous-traitant ultérieur sans autorisation écrite ;
   e) Assister le Responsable pour les demandes d'exercice de droits ;
   f) Notifier toute violation de données sous 72h ;
   g) Au terme du traitement : supprimer ou restituer les données, au choix
      du Responsable.

7. Audit
   Le Responsable peut auditer le respect du présent DPA avec un préavis de
   15 jours ouvrés, dans la limite d'un audit par an.
""".strip()

_TEMPLATE_ANNEXE_4_NOT_APPLICABLE = """
ANNEXE 4 — ACCORD DE TRAITEMENT DES DONNÉES PERSONNELLES (DPA)
[Cette annexe est conditionnelle et non applicable dans la configuration actuelle.]

Statut : NON APPLICABLE

En mode ON-PREMISE sans accès distant de l'Éditeur, le Client héberge et
traite les données personnelles uniquement sur ses propres infrastructures.
L'Éditeur n'accède à aucune donnée personnelle du Client.

Si l'Éditeur devait être amené à accéder à distance aux systèmes du Client
(support technique, maintenance), un avenant activant la présente annexe
devra être signé préalablement, conformément à l'article 28 du RGPD.
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 5 — Réversibilité / Fin de contrat
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_5 = """
ANNEXE 5 — RÉVERSIBILITÉ / FIN DE CONTRAT

1. Principe
   À l'issue du contrat (expiration ou résiliation), le Client conserve les
   dernières versions du Logiciel livrées et installées sur ses postes,
   sous forme exécutable uniquement.

2. Obligations de l'Éditeur en fin de contrat
   a) Fournir au Client la documentation utilisateur à jour ;
   b) Assister le Client pour la transition (si option d'assistance souscrite) ;
   c) Désactiver les éventuels accès distants de l'Éditeur aux systèmes Client.

3. Obligations du Client en fin de contrat
   a) Cesser toute utilisation du Logiciel sauf droit de survie ci-après ;
   b) Supprimer le Logiciel de tous les postes non couverts ;
   c) Restituer tout matériel ou documentation appartenant à l'Éditeur.

4. Droit de survie
   Le Client peut continuer à utiliser la dernière version livrée, sans
   maintenance ni support, pendant une période de {survival_period} suivant
   la fin du contrat, le temps de migrer vers une solution alternative.

5. Suppression des accès
   L'Éditeur procède à la suppression et désactivation de tous ses accès
   aux systèmes du Client sous 10 jours ouvrés suivant la fin du contrat.
   Un certificat de suppression est remis au Client sur demande.

6. Données du Client
   En mode ON-PREMISE, les données restent sur les infrastructures du Client.
   L'Éditeur ne détient aucune copie des données du Client.
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE: ANNEXE 6 — Grille tarifaire
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_ANNEXE_6 = """
ANNEXE 6 — GRILLE TARIFAIRE + CONDITIONS DE FACTURATION

1. Redevance de licence
   Métrique : {licence_metric}
   Tarif unitaire : {unit_price} EUR HT / {billing_period}
   Nombre de postes initial : {initial_posts}
   Montant initial : {initial_amount} EUR HT / {billing_period}

2. Frais d'onboarding (option)
   {onboarding_fee}

3. Maintenance et support
   Inclus dans la redevance de licence / {maintenance_pricing}

4. Développements spécifiques (sur devis)
   Taux journalier : {daily_rate} EUR HT
   Minimum facturable : {min_billing_unit}

5. Conditions de paiement
   - Facturation : {billing_frequency}
   - Paiement : 30 jours fin de mois (art. L.441-10 du Code de commerce)
   - Retard de paiement : intérêts de retard au taux légal majoré de 3 points
     + indemnité forfaitaire de recouvrement de 40 EUR (art. D.441-5 C. com.)

6. Révision tarifaire
   Les tarifs sont révisables annuellement selon l'indice Syntec ou, à défaut,
   l'indice des prix à la consommation (IPC).
   Notification : 3 mois avant la date d'effet.

7. Pénalités (SLA)
   En cas de non-respect des niveaux de service de l'Annexe 2 :
   {sla_penalties}
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE PACK
# ═══════════════════════════════════════════════════════════════════════════════

def get_template_pack() -> Dict[str, str]:
    """Retourne le pack complet de templates contractuels.
    
    Returns:
        Dict[str, str]: Dictionnaire section_name → template_text
    """
    return {
        "CP": _TEMPLATE_CP,
        "CG": _TEMPLATE_CG,
        "ANNEXE_1": _TEMPLATE_ANNEXE_1,
        "ANNEXE_2": _TEMPLATE_ANNEXE_2,
        "ANNEXE_3": _TEMPLATE_ANNEXE_3,
        "ANNEXE_4": _TEMPLATE_ANNEXE_4_CONDITIONAL,
        "ANNEXE_5": _TEMPLATE_ANNEXE_5,
        "ANNEXE_6": _TEMPLATE_ANNEXE_6,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

_VARIABLE_PATTERN = re.compile(r"\{(\w+)\}")


def render_template(template: str, variables: Dict[str, str]) -> str:
    """Rend un template en remplaçant les variables.
    
    Variables fournies → remplacées par leur valeur.
    Variables non fournies → remplacées par [À COMPLÉTER: nom_variable].
    
    Args:
        template:  Le texte template avec des {variables}
        variables: Dictionnaire variable_name → valeur
    
    Returns:
        Le texte rendu
    """
    def _replace(match):
        var_name = match.group(1)
        if var_name in variables and variables[var_name]:
            return variables[var_name]
        return f"[À COMPLÉTER: {var_name}]"
    
    return _VARIABLE_PATTERN.sub(_replace, template)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE VERSIONING REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE_VERSIONS: Dict[str, TemplateVersion] = {
    "CP": TemplateVersion(
        section="CP",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — CP licence ON-PREM",
        ],
        legal_basis="Art. 1101+ C. civ., Art. L.122-6 CPI",
    ),
    "CG": TemplateVersion(
        section="CG",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — CG licence ON-PREM avec PI, responsabilité, résiliation",
        ],
        legal_basis="Art. 1170, 1171, 1231-5 C. civ., Art. L.122-6 et L.122-6-1 CPI",
    ),
    "ANNEXE_1": TemplateVersion(
        section="ANNEXE_1",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — description logiciel + modules + pré-requis",
        ],
        legal_basis="Obligation d'information pré-contractuelle (art. 1112-1 C. civ.)",
    ),
    "ANNEXE_2": TemplateVersion(
        section="ANNEXE_2",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — SLA P1/P2/P3, support, maintenance ON-PREM",
        ],
        legal_basis="Obligation de moyens (art. 1231-1 C. civ.)",
    ),
    "ANNEXE_3": TemplateVersion(
        section="ANNEXE_3",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — sécurité, accès distant, journalisation",
        ],
        legal_basis="RGPD art. 32 (mesures de sécurité), Directive NIS2",
    ),
    "ANNEXE_4": TemplateVersion(
        section="ANNEXE_4",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — DPA art. 28 RGPD (conditionnel si accès distant)",
        ],
        legal_basis="RGPD art. 28, 32, 33, 36 ; CNIL recommandations sous-traitance",
    ),
    "ANNEXE_5": TemplateVersion(
        section="ANNEXE_5",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — réversibilité, fin contrat, droit de survie",
        ],
        legal_basis="Art. 1103, 1104 C. civ. (bonne foi contractuelle)",
    ),
    "ANNEXE_6": TemplateVersion(
        section="ANNEXE_6",
        version="1.0.0",
        last_review_date=date(2026, 2, 1),
        reviewer=_REVIEWER_INTERNAL,
        changelog=[
            "1.0.0 (2026-02-01): Version initiale — grille tarifaire, indexation Syntec, pénalités SLA",
        ],
        legal_basis="Art. L.441-10, D.441-5 C. com., Art. 1164 C. civ. (indexation)",
    ),
}


def get_template_versions() -> Dict[str, TemplateVersion]:
    """Retourne le registre complet des versions de templates.
    
    Returns:
        Dict section_name → TemplateVersion
    """
    return dict(_TEMPLATE_VERSIONS)


def get_template_version(section: str) -> TemplateVersion:
    """Retourne la version d'un template spécifique.
    
    Args:
        section: Nom de la section (ex: "CP", "CG", "ANNEXE_1")
    
    Returns:
        TemplateVersion
    
    Raises:
        KeyError: si la section n'existe pas
    """
    if section not in _TEMPLATE_VERSIONS:
        raise KeyError(f"Section inconnue: {section}. Sections disponibles: {list(_TEMPLATE_VERSIONS.keys())}")
    return _TEMPLATE_VERSIONS[section]


def get_stale_templates() -> List[TemplateVersion]:
    """Retourne la liste des templates périmés (> 12 mois sans revue).
    
    Returns:
        Liste des TemplateVersion périmés
    """
    return [v for v in _TEMPLATE_VERSIONS.values() if v.is_stale()]


def get_template_versions_summary() -> str:
    """Génère un résumé textuel des versions de tous les templates.
    
    Returns:
        str — résumé formaté
    """
    lines = [
        _SEP_LINE,
        "        REGISTRE DES VERSIONS — TEMPLATES CONTRACTUELS",
        _SEP_LINE,
        "",
    ]
    for section, tv in sorted(_TEMPLATE_VERSIONS.items()):
        stale_marker = " ⚠️ PÉRIMÉ" if tv.is_stale() else ""
        lines.append(f"  {section:12s} v{tv.version}  revue: {tv.last_review_date}  par: {tv.reviewer}{stale_marker}")
        if tv.legal_basis:
            lines.append(f"               base: {tv.legal_basis}")
    lines.append("")
    lines.append(_SEP_LINE)
    return "\n".join(lines)

#!/usr/bin/env python3
"""
Index RGPD (Règlement (UE) 2016/679) articles into the legal FTS5 database.

Source: EUR-Lex, texte officiel en français.
Licence: Droit de l'UE, réutilisation libre (Décision 2011/833/UE).
"""

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python.legal_sources.models import (
    AccessMode,
    DocumentType,
    Jurisdiction,
    LegalChunk,
    LegalDoc,
    LegalSource,
    Provenance,
)
from python.legal_sources.indexing import LegalIndex

RGPD_ARTICLES = {
    "1": {
        "title": "Article 1 — Objet et objectifs",
        "text": (
            "1. Le présent règlement établit des règles relatives à la protection des personnes physiques "
            "à l'égard du traitement des données à caractère personnel et des règles relatives à la libre "
            "circulation de ces données.\n\n"
            "2. Le présent règlement protège les libertés et droits fondamentaux des personnes physiques, "
            "et en particulier leur droit à la protection des données à caractère personnel.\n\n"
            "3. La libre circulation des données à caractère personnel au sein de l'Union n'est ni limitée "
            "ni interdite pour des motifs liés à la protection des personnes physiques à l'égard du "
            "traitement des données à caractère personnel."
        ),
    },
    "2": {
        "title": "Article 2 — Champ d'application matériel",
        "text": (
            "1. Le présent règlement s'applique au traitement de données à caractère personnel, "
            "automatisé en tout ou en partie, ainsi qu'au traitement non automatisé de données à "
            "caractère personnel contenues ou appelées à figurer dans un fichier.\n\n"
            "2. Le présent règlement ne s'applique pas au traitement de données à caractère personnel "
            "effectué:\n"
            "a) dans le cadre d'une activité qui ne relève pas du champ d'application du droit de l'Union;\n"
            "b) par les États membres dans le cadre d'activités qui relèvent du champ d'application du "
            "chapitre 2 du titre V du traité sur l'Union européenne;\n"
            "c) par une personne physique dans le cadre d'une activité strictement personnelle ou domestique;\n"
            "d) par les autorités compétentes à des fins de prévention et de détection des infractions "
            "pénales, d'enquêtes et de poursuites en la matière ou d'exécution de sanctions pénales, "
            "y compris la protection contre des menaces pour la sécurité publique et la prévention de "
            "telles menaces.\n\n"
            "3. Le règlement (CE) n° 45/2001 s'applique au traitement de données à caractère personnel "
            "par les institutions, organes et organismes de l'Union. Le règlement (CE) n° 45/2001 et les "
            "autres actes juridiques de l'Union applicables audit traitement de données à caractère "
            "personnel sont adaptés aux principes et aux règles du présent règlement conformément à "
            "l'article 98.\n\n"
            "4. Le présent règlement s'applique sans préjudice de la directive 2000/31/CE, et notamment "
            "de ses articles 12 à 15 relatifs à la responsabilité des prestataires de services intermédiaires."
        ),
    },
    "3": {
        "title": "Article 3 — Champ d'application territorial",
        "text": (
            "1. Le présent règlement s'applique au traitement des données à caractère personnel effectué "
            "dans le cadre des activités d'un établissement d'un responsable du traitement ou d'un "
            "sous-traitant sur le territoire de l'Union, que le traitement ait lieu ou non dans l'Union.\n\n"
            "2. Le présent règlement s'applique au traitement des données à caractère personnel relatives "
            "à des personnes concernées qui se trouvent sur le territoire de l'Union par un responsable du "
            "traitement ou un sous-traitant qui n'est pas établi dans l'Union, lorsque les activités de "
            "traitement sont liées:\n"
            "a) à l'offre de biens ou de services à ces personnes concernées dans l'Union, qu'un paiement "
            "soit exigé ou non desdites personnes; ou\n"
            "b) au suivi du comportement de ces personnes, dans la mesure où il s'agit d'un comportement "
            "qui a lieu au sein de l'Union.\n\n"
            "3. Le présent règlement s'applique au traitement de données à caractère personnel par un "
            "responsable du traitement qui n'est pas établi dans l'Union mais dans un lieu où le droit "
            "d'un État membre s'applique en vertu du droit international public."
        ),
    },
    "4": {
        "title": "Article 4 — Définitions",
        "text": (
            "Aux fins du présent règlement, on entend par:\n\n"
            "1) «données à caractère personnel», toute information se rapportant à une personne physique "
            "identifiée ou identifiable (ci-après dénommée «personne concernée»); est réputée être une "
            "«personne physique identifiable» une personne physique qui peut être identifiée, directement "
            "ou indirectement, notamment par référence à un identifiant, tel qu'un nom, un numéro "
            "d'identification, des données de localisation, un identifiant en ligne, ou à un ou plusieurs "
            "éléments spécifiques propres à son identité physique, physiologique, génétique, psychique, "
            "économique, culturelle ou sociale;\n\n"
            "2) «traitement», toute opération ou tout ensemble d'opérations effectuées ou non à l'aide de "
            "procédés automatisés et appliquées à des données ou des ensembles de données à caractère "
            "personnel, telles que la collecte, l'enregistrement, l'organisation, la structuration, la "
            "conservation, l'adaptation ou la modification, l'extraction, la consultation, l'utilisation, "
            "la communication par transmission, la diffusion ou toute autre forme de mise à disposition, "
            "le rapprochement ou l'interconnexion, la limitation, l'effacement ou la destruction;\n\n"
            "7) «responsable du traitement», la personne physique ou morale, l'autorité publique, le "
            "service ou un autre organisme qui, seul ou conjointement avec d'autres, détermine les "
            "finalités et les moyens du traitement;\n\n"
            "8) «sous-traitant», la personne physique ou morale, l'autorité publique, le service ou un "
            "autre organisme qui traite des données à caractère personnel pour le compte du responsable "
            "du traitement;\n\n"
            "11) «consentement» de la personne concernée, toute manifestation de volonté, libre, "
            "spécifique, éclairée et univoque par laquelle la personne concernée accepte, par une "
            "déclaration ou par un acte positif clair, que des données à caractère personnel la "
            "concernant fassent l'objet d'un traitement;\n\n"
            "12) «violation de données à caractère personnel», une violation de la sécurité entraînant, "
            "de manière accidentelle ou illicite, la destruction, la perte, l'altération, la divulgation "
            "non autorisée de données à caractère personnel transmises, conservées ou traitées d'une "
            "autre manière, ou l'accès non autorisé à de telles données."
        ),
    },
    "5": {
        "title": "Article 5 — Principes relatifs au traitement des données à caractère personnel",
        "text": (
            "1. Les données à caractère personnel doivent être:\n\n"
            "a) traitées de manière licite, loyale et transparente au regard de la personne concernée "
            "(«licéité, loyauté, transparence»);\n\n"
            "b) collectées pour des finalités déterminées, explicites et légitimes, et ne pas être "
            "traitées ultérieurement d'une manière incompatible avec ces finalités; le traitement "
            "ultérieur à des fins archivistiques dans l'intérêt public, à des fins de recherche "
            "scientifique ou historique ou à des fins statistiques n'est pas considéré, conformément "
            "à l'article 89, paragraphe 1, comme incompatible avec les finalités initiales "
            "(«limitation des finalités»);\n\n"
            "c) adéquates, pertinentes et limitées à ce qui est nécessaire au regard des finalités "
            "pour lesquelles elles sont traitées («minimisation des données»);\n\n"
            "d) exactes et, si nécessaire, tenues à jour; toutes les mesures raisonnables doivent être "
            "prises pour que les données à caractère personnel qui sont inexactes, eu égard aux finalités "
            "pour lesquelles elles sont traitées, soient effacées ou rectifiées sans tarder "
            "(«exactitude»);\n\n"
            "e) conservées sous une forme permettant l'identification des personnes concernées pendant "
            "une durée n'excédant pas celle nécessaire au regard des finalités pour lesquelles elles "
            "sont traitées («limitation de la conservation»);\n\n"
            "f) traitées de façon à garantir une sécurité appropriée des données à caractère personnel, "
            "y compris la protection contre le traitement non autorisé ou illicite et contre la perte, "
            "la destruction ou les dégâts d'origine accidentelle, à l'aide de mesures techniques ou "
            "organisationnelles appropriées («intégrité et confidentialité»).\n\n"
            "2. Le responsable du traitement est responsable du respect du paragraphe 1 et est en mesure "
            "de démontrer que celui-ci est respecté («responsabilité»)."
        ),
    },
    "6": {
        "title": "Article 6 — Licéité du traitement",
        "text": (
            "1. Le traitement n'est licite que si, et dans la mesure où, au moins une des conditions "
            "suivantes est remplie:\n\n"
            "a) la personne concernée a consenti au traitement de ses données à caractère personnel pour "
            "une ou plusieurs finalités spécifiques;\n\n"
            "b) le traitement est nécessaire à l'exécution d'un contrat auquel la personne concernée est "
            "partie ou à l'exécution de mesures précontractuelles prises à la demande de celle-ci;\n\n"
            "c) le traitement est nécessaire au respect d'une obligation légale à laquelle le responsable "
            "du traitement est soumis;\n\n"
            "d) le traitement est nécessaire à la sauvegarde des intérêts vitaux de la personne concernée "
            "ou d'une autre personne physique;\n\n"
            "e) le traitement est nécessaire à l'exécution d'une mission d'intérêt public ou relevant de "
            "l'exercice de l'autorité publique dont est investi le responsable du traitement;\n\n"
            "f) le traitement est nécessaire aux fins des intérêts légitimes poursuivis par le responsable "
            "du traitement ou par un tiers, à moins que ne prévalent les intérêts ou les libertés et "
            "droits fondamentaux de la personne concernée qui exigent une protection des données à "
            "caractère personnel, notamment lorsque la personne concernée est un enfant.\n\n"
            "Le point f) du premier alinéa ne s'applique pas au traitement effectué par les autorités "
            "publiques dans l'exécution de leurs missions.\n\n"
            "2. Les États membres peuvent maintenir ou introduire des dispositions plus spécifiques pour "
            "adapter l'application des règles du présent règlement pour ce qui est du traitement dans le "
            "but de respecter le paragraphe 1, points c) et e), en définissant plus précisément les "
            "exigences spécifiques applicables au traitement ainsi que d'autres mesures visant à garantir "
            "un traitement licite et loyal.\n\n"
            "3. Le fondement du traitement visé au paragraphe 1, points c) et e), est défini par:\n"
            "a) le droit de l'Union; ou\n"
            "b) le droit de l'État membre auquel le responsable du traitement est soumis.\n\n"
            "4. Lorsque le traitement à une fin autre que celle pour laquelle les données ont été "
            "collectées n'est pas fondé sur le consentement de la personne concernée ou sur le droit de "
            "l'Union ou le droit d'un État membre, le responsable du traitement, afin de déterminer si "
            "le traitement à une autre fin est compatible avec la finalité pour laquelle les données à "
            "caractère personnel ont été initialement collectées, tient compte, entre autres:\n"
            "a) de l'existence éventuelle d'un lien entre les finalités pour lesquelles les données à "
            "caractère personnel ont été collectées et les finalités du traitement ultérieur envisagé;\n"
            "b) du contexte dans lequel les données à caractère personnel ont été collectées, en "
            "particulier en ce qui concerne la relation entre les personnes concernées et le responsable "
            "du traitement;\n"
            "c) de la nature des données à caractère personnel, en particulier si le traitement porte sur "
            "des catégories particulières de données à caractère personnel, en vertu de l'article 9, ou "
            "si des données à caractère personnel relatives à des condamnations pénales et à des "
            "infractions sont traitées, en vertu de l'article 10;\n"
            "d) des conséquences possibles du traitement ultérieur envisagé pour les personnes concernées;\n"
            "e) de l'existence de garanties appropriées, qui peuvent comprendre le chiffrement ou la "
            "pseudonymisation."
        ),
    },
    "7": {
        "title": "Article 7 — Conditions applicables au consentement",
        "text": (
            "1. Dans les cas où le traitement repose sur le consentement, le responsable du traitement "
            "est en mesure de démontrer que la personne concernée a donné son consentement au traitement "
            "de ses données à caractère personnel.\n\n"
            "2. Si le consentement de la personne concernée est donné dans le cadre d'une déclaration "
            "écrite qui concerne également d'autres questions, la demande de consentement est présentée "
            "sous une forme qui la distingue clairement de ces autres questions, sous une forme "
            "compréhensible et aisément accessible, et formulée en des termes clairs et simples.\n\n"
            "3. La personne concernée a le droit de retirer son consentement à tout moment. Le retrait "
            "du consentement ne compromet pas la licéité du traitement fondé sur le consentement effectué "
            "avant ce retrait. La personne concernée en est informée avant de donner son consentement. "
            "Il est aussi simple de retirer que de donner son consentement.\n\n"
            "4. Au moment de déterminer si le consentement est donné librement, il y a lieu de tenir le "
            "plus grand compte de la question de savoir, entre autres, si l'exécution d'un contrat, y "
            "compris la fourniture d'un service, est subordonnée au consentement au traitement de "
            "données à caractère personnel qui n'est pas nécessaire à l'exécution dudit contrat."
        ),
    },
    "8": {
        "title": "Article 8 — Conditions applicables au consentement des enfants en ce qui concerne les services de la société de l'information",
        "text": (
            "1. Lorsque l'article 6, paragraphe 1, point a), s'applique, en ce qui concerne l'offre "
            "directe de services de la société de l'information aux enfants, le traitement des données "
            "à caractère personnel relatives à un enfant est licite lorsque l'enfant est âgé d'au moins "
            "16 ans. Lorsque l'enfant est âgé de moins de 16 ans, ce traitement n'est licite que si, et "
            "dans la mesure où, le consentement est donné ou autorisé par le titulaire de la "
            "responsabilité parentale à l'égard de l'enfant.\n\n"
            "Les États membres peuvent prévoir par la loi un âge inférieur pour ces finalités pour autant "
            "que cet âge inférieur ne soit pas en dessous de 13 ans.\n\n"
            "2. Le responsable du traitement s'efforce raisonnablement de vérifier, en pareil cas, que "
            "le consentement est donné ou autorisé par le titulaire de la responsabilité parentale à "
            "l'égard de l'enfant, compte tenu des moyens technologiques disponibles.\n\n"
            "3. Le paragraphe 1 ne porte pas atteinte au droit général des contrats des États membres, "
            "tel que les règles concernant la validité, la formation ou les effets d'un contrat à "
            "l'égard d'un enfant."
        ),
    },
    "9": {
        "title": "Article 9 — Traitement portant sur des catégories particulières de données à caractère personnel",
        "text": (
            "1. Le traitement des données à caractère personnel qui révèle l'origine raciale ou ethnique, "
            "les opinions politiques, les convictions religieuses ou philosophiques ou l'appartenance "
            "syndicale, ainsi que le traitement des données génétiques, des données biométriques aux fins "
            "d'identifier une personne physique de manière unique, des données concernant la santé ou des "
            "données concernant la vie sexuelle ou l'orientation sexuelle d'une personne physique sont "
            "interdits.\n\n"
            "2. Le paragraphe 1 ne s'applique pas si l'une des conditions suivantes est remplie:\n"
            "a) la personne concernée a donné son consentement explicite;\n"
            "b) le traitement est nécessaire aux fins de l'exécution des obligations et de l'exercice "
            "des droits propres au responsable du traitement ou à la personne concernée en matière de "
            "droit du travail, de la sécurité sociale et de la protection sociale;\n"
            "c) le traitement est nécessaire à la sauvegarde des intérêts vitaux de la personne concernée "
            "ou d'une autre personne physique;\n"
            "d) le traitement est effectué, dans le cadre de leurs activités légitimes et moyennant les "
            "garanties appropriées, par une fondation, une association ou tout autre organisme à but non "
            "lucratif et poursuivant une finalité politique, philosophique, religieuse ou syndicale;\n"
            "e) le traitement porte sur des données à caractère personnel qui sont manifestement rendues "
            "publiques par la personne concernée;\n"
            "f) le traitement est nécessaire à la constatation, à l'exercice ou à la défense d'un droit "
            "en justice;\n"
            "g) le traitement est nécessaire pour des motifs d'intérêt public important;\n"
            "h) le traitement est nécessaire aux fins de la médecine préventive ou de la médecine du "
            "travail, de l'appréciation de la capacité de travail du travailleur, de diagnostics "
            "médicaux, de la prise en charge sanitaire ou sociale;\n"
            "i) le traitement est nécessaire pour des motifs d'intérêt public dans le domaine de la "
            "santé publique;\n"
            "j) le traitement est nécessaire à des fins archivistiques dans l'intérêt public, à des "
            "fins de recherche scientifique ou historique ou à des fins statistiques."
        ),
    },
    "12": {
        "title": "Article 12 — Transparence des informations et des communications et modalités de l'exercice des droits de la personne concernée",
        "text": (
            "1. Le responsable du traitement prend des mesures appropriées pour fournir toute information "
            "visée aux articles 13 et 14 ainsi que pour procéder à toute communication au titre des "
            "articles 15 à 22 et de l'article 34 en ce qui concerne le traitement à la personne "
            "concernée d'une façon concise, transparente, compréhensible et aisément accessible, en des "
            "termes clairs et simples, en particulier pour toute information destinée spécifiquement à "
            "un enfant.\n\n"
            "2. Le responsable du traitement facilite l'exercice des droits conférés à la personne "
            "concernée au titre des articles 15 à 22.\n\n"
            "3. Le responsable du traitement fournit à la personne concernée des informations sur les "
            "mesures prises à la suite d'une demande formulée en application des articles 15 à 22, dans "
            "les meilleurs délais et en tout état de cause dans un délai d'un mois à compter de la "
            "réception de la demande.\n\n"
            "5. Aucun paiement n'est exigé pour fournir les informations au titre des articles 13 et 14 "
            "et pour procéder à toute communication et prendre toute mesure au titre des articles 15 à "
            "22 et de l'article 34."
        ),
    },
    "13": {
        "title": "Article 13 — Informations à fournir lorsque des données à caractère personnel sont collectées auprès de la personne concernée",
        "text": (
            "1. Lorsque des données à caractère personnel relatives à une personne concernée sont "
            "collectées auprès de cette personne, le responsable du traitement lui fournit, au moment "
            "où les données en question sont obtenues, toutes les informations suivantes:\n"
            "a) l'identité et les coordonnées du responsable du traitement;\n"
            "b) le cas échéant, les coordonnées du délégué à la protection des données;\n"
            "c) les finalités du traitement auquel sont destinées les données à caractère personnel "
            "ainsi que la base juridique du traitement;\n"
            "d) lorsque le traitement est fondé sur l'article 6, paragraphe 1, point f), les intérêts "
            "légitimes poursuivis par le responsable du traitement ou par un tiers;\n"
            "e) les destinataires ou les catégories de destinataires des données à caractère personnel;\n"
            "f) le cas échéant, le fait que le responsable du traitement a l'intention d'effectuer un "
            "transfert de données à caractère personnel vers un pays tiers.\n\n"
            "2. En plus des informations visées au paragraphe 1, le responsable du traitement fournit "
            "à la personne concernée les informations complémentaires suivantes:\n"
            "a) la durée de conservation des données à caractère personnel;\n"
            "b) l'existence du droit de demander au responsable du traitement l'accès aux données, "
            "la rectification ou l'effacement de celles-ci, ou une limitation du traitement, "
            "le droit de s'opposer au traitement et le droit à la portabilité des données;\n"
            "c) le droit de retirer son consentement à tout moment;\n"
            "d) le droit d'introduire une réclamation auprès d'une autorité de contrôle;\n"
            "e) des informations sur la question de savoir si l'exigence de fourniture de données à "
            "caractère personnel a un caractère réglementaire ou contractuel;\n"
            "f) l'existence d'une prise de décision automatisée, y compris un profilage."
        ),
    },
    "15": {
        "title": "Article 15 — Droit d'accès de la personne concernée",
        "text": (
            "1. La personne concernée a le droit d'obtenir du responsable du traitement la confirmation "
            "que des données à caractère personnel la concernant sont ou ne sont pas traitées et, "
            "lorsqu'elles le sont, l'accès auxdites données à caractère personnel ainsi que les "
            "informations suivantes:\n"
            "a) les finalités du traitement;\n"
            "b) les catégories de données à caractère personnel concernées;\n"
            "c) les destinataires ou catégories de destinataires;\n"
            "d) lorsque cela est possible, la durée de conservation des données envisagée;\n"
            "e) l'existence du droit de demander la rectification ou l'effacement des données;\n"
            "f) le droit d'introduire une réclamation auprès d'une autorité de contrôle;\n"
            "g) lorsque les données ne sont pas collectées auprès de la personne concernée, toute "
            "information disponible quant à leur source;\n"
            "h) l'existence d'une prise de décision automatisée, y compris un profilage.\n\n"
            "3. Le responsable du traitement fournit une copie des données à caractère personnel "
            "faisant l'objet d'un traitement. Le responsable du traitement peut exiger le paiement "
            "de frais raisonnables basés sur les coûts administratifs pour toute copie supplémentaire "
            "demandée par la personne concernée."
        ),
    },
    "16": {
        "title": "Article 16 — Droit de rectification",
        "text": (
            "La personne concernée a le droit d'obtenir du responsable du traitement, dans les "
            "meilleurs délais, la rectification des données à caractère personnel la concernant qui "
            "sont inexactes. Compte tenu des finalités du traitement, la personne concernée a le droit "
            "d'obtenir que les données à caractère personnel incomplètes soient complétées, y compris "
            "en fournissant une déclaration complémentaire."
        ),
    },
    "17": {
        "title": "Article 17 — Droit à l'effacement («droit à l'oubli»)",
        "text": (
            "1. La personne concernée a le droit d'obtenir du responsable du traitement l'effacement, "
            "dans les meilleurs délais, de données à caractère personnel la concernant et le responsable "
            "du traitement a l'obligation d'effacer ces données à caractère personnel dans les meilleurs "
            "délais, lorsque l'un des motifs suivants s'applique:\n"
            "a) les données à caractère personnel ne sont plus nécessaires au regard des finalités;\n"
            "b) la personne concernée retire le consentement sur lequel est fondé le traitement;\n"
            "c) la personne concernée s'oppose au traitement en vertu de l'article 21;\n"
            "d) les données à caractère personnel ont fait l'objet d'un traitement illicite;\n"
            "e) les données à caractère personnel doivent être effacées pour respecter une obligation "
            "légale;\n"
            "f) les données à caractère personnel ont été collectées dans le cadre de l'offre de "
            "services de la société de l'information visée à l'article 8, paragraphe 1.\n\n"
            "2. Lorsqu'il a rendu publiques les données à caractère personnel et qu'il est tenu de les "
            "effacer, le responsable du traitement prend des mesures raisonnables pour informer les "
            "responsables du traitement qui traitent ces données que la personne concernée a demandé "
            "l'effacement de tout lien vers ces données, ou de toute copie ou reproduction de celles-ci.\n\n"
            "3. Les paragraphes 1 et 2 ne s'appliquent pas dans la mesure où ce traitement est "
            "nécessaire:\n"
            "a) à l'exercice du droit à la liberté d'expression et d'information;\n"
            "b) pour respecter une obligation légale;\n"
            "c) pour des motifs d'intérêt public dans le domaine de la santé publique;\n"
            "d) à des fins archivistiques dans l'intérêt public, à des fins de recherche scientifique "
            "ou historique ou à des fins statistiques;\n"
            "e) à la constatation, à l'exercice ou à la défense de droits en justice."
        ),
    },
    "18": {
        "title": "Article 18 — Droit à la limitation du traitement",
        "text": (
            "1. La personne concernée a le droit d'obtenir du responsable du traitement la limitation "
            "du traitement lorsque l'un des éléments suivants s'applique:\n"
            "a) l'exactitude des données à caractère personnel est contestée par la personne concernée;\n"
            "b) le traitement est illicite et la personne concernée s'oppose à leur effacement;\n"
            "c) le responsable du traitement n'a plus besoin des données à caractère personnel aux fins "
            "du traitement mais celles-ci sont encore nécessaires à la personne concernée pour la "
            "constatation, l'exercice ou la défense de droits en justice;\n"
            "d) la personne concernée s'est opposée au traitement en vertu de l'article 21."
        ),
    },
    "20": {
        "title": "Article 20 — Droit à la portabilité des données",
        "text": (
            "1. Les personnes concernées ont le droit de recevoir les données à caractère personnel les "
            "concernant qu'elles ont fournies à un responsable du traitement, dans un format structuré, "
            "couramment utilisé et lisible par machine, et ont le droit de transmettre ces données à un "
            "autre responsable du traitement sans que le responsable du traitement auquel les données à "
            "caractère personnel ont été communiquées y fasse obstacle.\n\n"
            "2. Lorsque la personne concernée exerce son droit à la portabilité des données en "
            "application du paragraphe 1, elle a le droit d'obtenir que les données à caractère "
            "personnel soient transmises directement d'un responsable du traitement à un autre, "
            "lorsque cela est techniquement possible."
        ),
    },
    "21": {
        "title": "Article 21 — Droit d'opposition",
        "text": (
            "1. La personne concernée a le droit de s'opposer à tout moment, pour des raisons tenant "
            "à sa situation particulière, à un traitement des données à caractère personnel la "
            "concernant fondé sur l'article 6, paragraphe 1, point e) ou f). Le responsable du "
            "traitement ne traite plus les données à caractère personnel, à moins qu'il ne démontre "
            "qu'il existe des motifs légitimes et impérieux pour le traitement qui prévalent sur les "
            "intérêts et les droits et libertés de la personne concernée, ou pour la constatation, "
            "l'exercice ou la défense de droits en justice.\n\n"
            "2. Lorsque les données à caractère personnel sont traitées à des fins de prospection, "
            "la personne concernée a le droit de s'opposer à tout moment au traitement des données "
            "à caractère personnel la concernant à de telles fins de prospection, y compris au "
            "profilage dans la mesure où il est lié à une telle prospection.\n\n"
            "3. Lorsque la personne concernée s'oppose au traitement à des fins de prospection, les "
            "données à caractère personnel ne sont plus traitées à ces fins."
        ),
    },
    "25": {
        "title": "Article 25 — Protection des données dès la conception et protection des données par défaut",
        "text": (
            "1. Compte tenu de l'état des connaissances, des coûts de la mise en œuvre et de la "
            "nature, de la portée, du contexte et des finalités du traitement ainsi que des risques, "
            "dont le degré de probabilité et de gravité varie, que présente le traitement pour les "
            "droits et libertés des personnes physiques, le responsable du traitement met en œuvre, "
            "tant au moment de la détermination des moyens du traitement qu'au moment du traitement "
            "lui-même, des mesures techniques et organisationnelles appropriées, telles que la "
            "pseudonymisation, qui sont destinées à mettre en œuvre les principes relatifs à la "
            "protection des données, par exemple la minimisation des données, de façon effective et "
            "à assortir le traitement des garanties nécessaires.\n\n"
            "2. Le responsable du traitement met en œuvre les mesures techniques et organisationnelles "
            "appropriées pour garantir que, par défaut, seules les données à caractère personnel qui "
            "sont nécessaires au regard de chaque finalité spécifique du traitement sont traitées."
        ),
    },
    "28": {
        "title": "Article 28 — Sous-traitant",
        "text": (
            "1. Lorsqu'un traitement doit être effectué pour le compte d'un responsable du traitement, "
            "celui-ci fait uniquement appel à des sous-traitants qui présentent des garanties "
            "suffisantes quant à la mise en œuvre de mesures techniques et organisationnelles "
            "appropriées de manière à ce que le traitement réponde aux exigences du présent règlement "
            "et garantisse la protection des droits de la personne concernée.\n\n"
            "3. Le traitement par un sous-traitant est régi par un contrat ou un autre acte juridique "
            "qui lie le sous-traitant à l'égard du responsable du traitement, définit l'objet et la "
            "durée du traitement, la nature et la finalité du traitement, le type de données à "
            "caractère personnel et les catégories de personnes concernées, et les obligations et les "
            "droits du responsable du traitement."
        ),
    },
    "30": {
        "title": "Article 30 — Registre des activités de traitement",
        "text": (
            "1. Chaque responsable du traitement et, le cas échéant, le représentant du responsable "
            "du traitement tient un registre des activités de traitement effectuées sous sa "
            "responsabilité. Ce registre comporte toutes les informations suivantes:\n"
            "a) le nom et les coordonnées du responsable du traitement;\n"
            "b) les finalités du traitement;\n"
            "c) une description des catégories de personnes concernées et des catégories de données;\n"
            "d) les catégories de destinataires;\n"
            "e) les transferts de données vers un pays tiers;\n"
            "f) les délais prévus pour l'effacement des différentes catégories de données;\n"
            "g) une description générale des mesures de sécurité techniques et organisationnelles.\n\n"
            "5. Les obligations visées aux paragraphes 1 et 2 ne s'appliquent pas à une entreprise ou "
            "un organisme comptant moins de 250 employés, sauf si le traitement qu'ils effectuent est "
            "susceptible de comporter un risque pour les droits et les libertés des personnes concernées, "
            "s'il n'est pas occasionnel ou s'il porte sur des catégories particulières de données."
        ),
    },
    "32": {
        "title": "Article 32 — Sécurité du traitement",
        "text": (
            "1. Compte tenu de l'état des connaissances, des coûts de la mise en œuvre et de la "
            "nature, de la portée, du contexte et des finalités du traitement ainsi que des risques, "
            "dont le degré de probabilité et de gravité varie, pour les droits et libertés des "
            "personnes physiques, le responsable du traitement et le sous-traitant mettent en œuvre "
            "les mesures techniques et organisationnelles appropriées afin de garantir un niveau de "
            "sécurité adapté au risque, y compris, entre autres, selon les besoins:\n"
            "a) la pseudonymisation et le chiffrement des données à caractère personnel;\n"
            "b) des moyens permettant de garantir la confidentialité, l'intégrité, la disponibilité "
            "et la résilience constantes des systèmes et des services de traitement;\n"
            "c) des moyens permettant de rétablir la disponibilité des données à caractère personnel "
            "et l'accès à celles-ci dans des délais appropriés en cas d'incident physique ou technique;\n"
            "d) une procédure visant à tester, à analyser et à évaluer régulièrement l'efficacité des "
            "mesures techniques et organisationnelles pour assurer la sécurité du traitement.\n\n"
            "2. Lors de l'évaluation du niveau de sécurité approprié, il est tenu compte en particulier "
            "des risques que présente le traitement, résultant notamment de la destruction, de la perte, "
            "de l'altération, de la divulgation non autorisée de données à caractère personnel ou de "
            "l'accès non autorisé à de telles données."
        ),
    },
    "33": {
        "title": "Article 33 — Notification à l'autorité de contrôle d'une violation de données à caractère personnel",
        "text": (
            "1. En cas de violation de données à caractère personnel, le responsable du traitement en "
            "notifie la violation en question à l'autorité de contrôle compétente en vertu de l'article "
            "55, dans les meilleurs délais et, si possible, 72 heures au plus tard après en avoir pris "
            "connaissance, à moins que la violation en question ne soit pas susceptible d'engendrer un "
            "risque pour les droits et libertés des personnes physiques.\n\n"
            "3. La notification visée au paragraphe 1 doit, à tout le moins:\n"
            "a) décrire la nature de la violation de données à caractère personnel;\n"
            "b) communiquer le nom et les coordonnées du délégué à la protection des données;\n"
            "c) décrire les conséquences probables de la violation;\n"
            "d) décrire les mesures prises ou que le responsable du traitement propose de prendre."
        ),
    },
    "34": {
        "title": "Article 34 — Communication à la personne concernée d'une violation de données à caractère personnel",
        "text": (
            "1. Lorsqu'une violation de données à caractère personnel est susceptible d'engendrer un "
            "risque élevé pour les droits et libertés d'une personne physique, le responsable du "
            "traitement communique la violation de données à caractère personnel à la personne "
            "concernée dans les meilleurs délais.\n\n"
            "3. La communication à la personne concernée visée au paragraphe 1 n'est pas nécessaire si "
            "l'une ou l'autre des conditions suivantes est remplie:\n"
            "a) le responsable du traitement a mis en œuvre les mesures de protection techniques et "
            "organisationnelles appropriées et ces mesures ont été appliquées aux données à caractère "
            "personnel affectées par ladite violation, en particulier les mesures qui rendent les "
            "données à caractère personnel incompréhensibles pour toute personne qui n'est pas autorisée "
            "à y avoir accès, telles que le chiffrement;\n"
            "b) le responsable du traitement a pris des mesures ultérieures qui garantissent que le "
            "risque élevé pour les droits et libertés des personnes concernées n'est plus susceptible "
            "de se matérialiser;\n"
            "c) elle exigerait des efforts disproportionnés."
        ),
    },
    "35": {
        "title": "Article 35 — Analyse d'impact relative à la protection des données",
        "text": (
            "1. Lorsqu'un type de traitement, en particulier par le recours à de nouvelles technologies, "
            "et compte tenu de la nature, de la portée, du contexte et des finalités du traitement, est "
            "susceptible d'engendrer un risque élevé pour les droits et libertés des personnes physiques, "
            "le responsable du traitement effectue, avant le traitement, une analyse de l'impact des "
            "opérations de traitement envisagées sur la protection des données à caractère personnel.\n\n"
            "3. L'analyse d'impact relative à la protection des données est, en particulier, requise "
            "dans les cas suivants:\n"
            "a) l'évaluation systématique et approfondie d'aspects personnels concernant des personnes "
            "physiques, qui est fondée sur un traitement automatisé, y compris le profilage;\n"
            "b) le traitement à grande échelle de catégories particulières de données visées à "
            "l'article 9, paragraphe 1, ou de données à caractère personnel relatives à des "
            "condamnations pénales et à des infractions visées à l'article 10;\n"
            "c) la surveillance systématique à grande échelle d'une zone accessible au public.\n\n"
            "7. L'analyse contient au moins:\n"
            "a) une description systématique des opérations de traitement envisagées et des finalités;\n"
            "b) une évaluation de la nécessité et de la proportionnalité des opérations de traitement;\n"
            "c) une évaluation des risques pour les droits et libertés des personnes concernées;\n"
            "d) les mesures envisagées pour faire face aux risques."
        ),
    },
    "37": {
        "title": "Article 37 — Désignation du délégué à la protection des données",
        "text": (
            "1. Le responsable du traitement et le sous-traitant désignent en tout état de cause un "
            "délégué à la protection des données lorsque:\n"
            "a) le traitement est effectué par une autorité publique ou un organisme public;\n"
            "b) les activités de base du responsable du traitement ou du sous-traitant consistent en "
            "des opérations de traitement qui, du fait de leur nature, de leur portée et/ou de leurs "
            "finalités, exigent un suivi régulier et systématique à grande échelle des personnes "
            "concernées;\n"
            "c) les activités de base du responsable du traitement ou du sous-traitant consistent en "
            "un traitement à grande échelle de catégories particulières de données visées à l'article 9 "
            "ou de données à caractère personnel relatives à des condamnations pénales et à des "
            "infractions visées à l'article 10."
        ),
    },
    "44": {
        "title": "Article 44 — Principe général applicable aux transferts",
        "text": (
            "Un transfert vers un pays tiers ou à une organisation internationale de données à "
            "caractère personnel qui font ou sont destinées à faire l'objet d'un traitement après ce "
            "transfert ne peut avoir lieu que si, sous réserve des autres dispositions du présent "
            "règlement, les conditions définies dans le présent chapitre sont respectées par le "
            "responsable du traitement et le sous-traitant, y compris pour les transferts ultérieurs "
            "de données à caractère personnel au départ du pays tiers ou de l'organisation "
            "internationale vers un autre pays tiers ou à une autre organisation internationale."
        ),
    },
    "77": {
        "title": "Article 77 — Droit d'introduire une réclamation auprès d'une autorité de contrôle",
        "text": (
            "1. Sans préjudice de tout autre recours administratif ou juridictionnel, toute personne "
            "concernée a le droit d'introduire une réclamation auprès d'une autorité de contrôle, en "
            "particulier dans l'État membre dans lequel se trouve sa résidence habituelle, son lieu de "
            "travail ou le lieu où la violation aurait été commise, si elle considère que le traitement "
            "de données à caractère personnel la concernant constitue une violation du présent règlement.\n\n"
            "2. L'autorité de contrôle auprès de laquelle la réclamation a été introduite informe "
            "l'auteur de la réclamation de l'état d'avancement et de l'issue de la réclamation, y "
            "compris de la possibilité d'un recours juridictionnel en vertu de l'article 78."
        ),
    },
    "82": {
        "title": "Article 82 — Droit à réparation et responsabilité",
        "text": (
            "1. Toute personne ayant subi un dommage matériel ou moral du fait d'une violation du "
            "présent règlement a le droit d'obtenir du responsable du traitement ou du sous-traitant "
            "réparation du préjudice subi.\n\n"
            "2. Tout responsable du traitement ayant participé au traitement est responsable du "
            "dommage causé par le traitement qui constitue une violation du présent règlement.\n\n"
            "3. Un responsable du traitement ou un sous-traitant est exonéré de responsabilité, "
            "en vertu du paragraphe 2, s'il prouve que le fait qui a provoqué le dommage ne lui est "
            "nullement imputable."
        ),
    },
    "83": {
        "title": "Article 83 — Conditions générales pour imposer des amendes administratives",
        "text": (
            "1. Chaque autorité de contrôle veille à ce que les amendes administratives imposées en "
            "vertu du présent article pour des violations du présent règlement soient, dans chaque cas, "
            "effectives, proportionnées et dissuasives.\n\n"
            "4. Les violations des dispositions suivantes font l'objet, conformément au paragraphe 2, "
            "d'amendes administratives pouvant s'élever jusqu'à 10 000 000 EUR ou, dans le cas d'une "
            "entreprise, jusqu'à 2 % du chiffre d'affaires annuel mondial total de l'exercice "
            "précédent, le montant le plus élevé étant retenu.\n\n"
            "5. Les violations des dispositions suivantes font l'objet, conformément au paragraphe 2, "
            "d'amendes administratives pouvant s'élever jusqu'à 20 000 000 EUR ou, dans le cas d'une "
            "entreprise, jusqu'à 4 % du chiffre d'affaires annuel mondial total de l'exercice "
            "précédent, le montant le plus élevé étant retenu:\n"
            "a) les principes de base du traitement, y compris les conditions applicables au "
            "consentement en vertu des articles 5, 6, 7 et 9;\n"
            "b) les droits dont bénéficient les personnes concernées en vertu des articles 12 à 22;\n"
            "c) les transferts de données à caractère personnel à un destinataire dans un pays tiers "
            "en vertu des articles 44 à 49;\n"
            "d) toute obligation découlant du droit d'un État membre adopté en vertu du chapitre IX;\n"
            "e) le non-respect d'une injonction, d'une limitation temporaire ou définitive du "
            "traitement ou de la suspension des flux de données ordonnée par l'autorité de contrôle."
        ),
    },
}


def make_doc_id(article_num: str) -> str:
    key = f"legi:RGPD-ART-{article_num}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    key = f"{doc_id}:{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def index_rgpd(index_dir: Path) -> dict:
    idx = LegalIndex(index_dir)
    stats = {"docs_added": 0, "chunks_added": 0, "skipped": 0}

    for art_num, art_data in RGPD_ARTICLES.items():
        doc_id = make_doc_id(art_num)
        origin_id = f"RGPD-ART-{art_num}"
        citation = f"RGPD, art. {art_num}"

        provenance = Provenance(
            source=LegalSource.LEGI,
            source_name="EUR-Lex (Union européenne)",
            origin_id=origin_id,
            origin_url=f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32016R0679#art_{art_num}",
            license_name="Réutilisation libre (Décision 2011/833/UE)",
            license_url="https://eur-lex.europa.eu/content/legal-notice/legal-notice.html",
            terms_name="EUR-Lex réutilisation",
            terms_url="https://eur-lex.europa.eu/content/legal-notice/legal-notice.html",
            access_mode=AccessMode.OPEN_DOWNLOAD,
        )

        doc = LegalDoc(
            doc_id=doc_id,
            source=LegalSource.LEGI,
            origin_id=origin_id,
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title=art_data["title"],
            citation=citation,
            date=datetime(2016, 4, 27),
            code_name="RGPD (UE) 2016/679",
            article_number=art_num,
            text=art_data["text"],
            provenance=provenance,
        )

        if idx.add_doc(doc):
            stats["docs_added"] += 1
        else:
            stats["skipped"] += 1

        text = art_data["text"]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunk_idx = 0
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) > 800 and current_chunk:
                chunk = LegalChunk(
                    chunk_id=make_chunk_id(doc_id, chunk_idx),
                    doc_id=doc_id,
                    chunk_index=chunk_idx,
                    text=f"[{citation}]\n\n{current_chunk}",
                    source=LegalSource.LEGI,
                    document_type=DocumentType.CODE,
                    citation=citation,
                    pinpoint=f"Art. {art_num}",
                    provenance=Provenance(
                        source=LegalSource.LEGI,
                        source_name="EUR-Lex (Union européenne)",
                        origin_id=origin_id,
                        origin_url=provenance.origin_url,
                        license_name=provenance.license_name,
                        license_url=provenance.license_url,
                        terms_name=provenance.terms_name,
                        terms_url=provenance.terms_url,
                        access_mode=AccessMode.OPEN_DOWNLOAD,
                        pinpoint=f"Art. {art_num}",
                        chunk_index=chunk_idx,
                    ),
                )
                if idx.add_chunk(chunk):
                    stats["chunks_added"] += 1
                chunk_idx += 1
                current_chunk = para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip()

        if current_chunk:
            chunk = LegalChunk(
                chunk_id=make_chunk_id(doc_id, chunk_idx),
                doc_id=doc_id,
                chunk_index=chunk_idx,
                text=f"[{citation}]\n\n{current_chunk}",
                source=LegalSource.LEGI,
                document_type=DocumentType.CODE,
                citation=citation,
                pinpoint=f"Art. {art_num}",
                provenance=Provenance(
                    source=LegalSource.LEGI,
                    source_name="EUR-Lex (Union européenne)",
                    origin_id=origin_id,
                    origin_url=provenance.origin_url,
                    license_name=provenance.license_name,
                    license_url=provenance.license_url,
                    terms_name=provenance.terms_name,
                    terms_url=provenance.terms_url,
                    access_mode=AccessMode.OPEN_DOWNLOAD,
                    pinpoint=f"Art. {art_num}",
                    chunk_index=chunk_idx,
                ),
            )
            if idx.add_chunk(chunk):
                stats["chunks_added"] += 1

    return stats


if __name__ == "__main__":
    index_dir = PROJECT_ROOT / "data" / "legal" / "index"
    print(f"Indexing RGPD into {index_dir}")
    stats = index_rgpd(index_dir)
    print(f"Done: {stats}")

    idx = LegalIndex(index_dir)
    results = idx.search("RGPD article 6 licéité traitement", limit=3)
    print(f"\nVerification search 'RGPD article 6': {len(results)} results")
    for r in results:
        print(f"  - {r.citation}: {r.text_snippet[:100]}...")

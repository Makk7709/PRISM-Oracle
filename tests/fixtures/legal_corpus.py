"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL CORPUS FIXTURE — P2.b                               ║
║                                                                              ║
║  Corpus minimal officiel pour tests E2E du pipeline juridique.              ║
║  20 documents : Code civil, Code du travail, Jurisprudence Cass.           ║
║                                                                              ║
║  Utilisation:                                                                ║
║    from tests.fixtures.legal_corpus import create_test_index, CORPUS        ║
║    index = create_test_index(tmp_path)                                      ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

# ═══════════════════════════════════════════════════════════════════════════════
# CORPUS DATA — CODE CIVIL
# ═══════════════════════════════════════════════════════════════════════════════

CODE_CIVIL_ARTICLES = [
    {
        "origin_id": "LEGIARTI000006436298",
        "article_number": "1103",
        "title": "Article 1103 - Force obligatoire des contrats",
        "text": "Les contrats légalement formés tiennent lieu de loi à ceux qui les ont faits.",
        "citation": "Art. 1103 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006436298",
            "license_name": "Licence Ouverte 2.0",
            "license_url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006436532",
        "article_number": "1134",
        "title": "Article 1134 - Conventions légalement formées (ancien)",
        "text": "Les conventions légalement formées tiennent lieu de loi à ceux qui les ont faites. "
                "Elles ne peuvent être révoquées que de leur consentement mutuel, ou pour les causes que la loi autorise. "
                "Elles doivent être exécutées de bonne foi.",
        "citation": "Art. 1134 C. civ. (ancien)",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006436532",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000032041570",
        "article_number": "1104",
        "title": "Article 1104 - Bonne foi contractuelle",
        "text": "Les contrats doivent être négociés, formés et exécutés de bonne foi. "
                "Cette disposition est d'ordre public.",
        "citation": "Art. 1104 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041570",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000032041489",
        "article_number": "1112",
        "title": "Article 1112 - Négociation précontractuelle",
        "text": "L'initiative, le déroulement et la rupture des négociations précontractuelles sont libres. "
                "Ils doivent impérativement satisfaire aux exigences de la bonne foi.",
        "citation": "Art. 1112 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041489",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000032041459",
        "article_number": "1128",
        "title": "Article 1128 - Conditions de validité du contrat",
        "text": "Sont nécessaires à la validité d'un contrat : "
                "1° Le consentement des parties ; "
                "2° Leur capacité de contracter ; "
                "3° Un contenu licite et certain.",
        "citation": "Art. 1128 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041459",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006438318",
        "article_number": "1240",
        "title": "Article 1240 - Responsabilité délictuelle (ancien 1382)",
        "text": "Tout fait quelconque de l'homme, qui cause à autrui un dommage, "
                "oblige celui par la faute duquel il est arrivé à le réparer.",
        "citation": "Art. 1240 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006438318",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006438320",
        "article_number": "1241",
        "title": "Article 1241 - Responsabilité pour négligence",
        "text": "Chacun est responsable du dommage qu'il a causé non seulement par son fait, "
                "mais encore par sa négligence ou par son imprudence.",
        "citation": "Art. 1241 C. civ.",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006438320",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# CORPUS DATA — CODE DU TRAVAIL
# ═══════════════════════════════════════════════════════════════════════════════

CODE_TRAVAIL_ARTICLES = [
    {
        "origin_id": "LEGIARTI000006901120",
        "article_number": "L1121-1",
        "title": "Article L1121-1 - Libertés et droits fondamentaux",
        "text": "Nul ne peut apporter aux droits des personnes et aux libertés individuelles et collectives "
                "de restrictions qui ne seraient pas justifiées par la nature de la tâche à accomplir "
                "ni proportionnées au but recherché.",
        "citation": "Art. L1121-1 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006901120",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006901170",
        "article_number": "L1221-1",
        "title": "Article L1221-1 - Forme du contrat de travail",
        "text": "Le contrat de travail est soumis aux règles du droit commun. "
                "Il peut être établi selon les formes que les parties contractantes décident d'adopter.",
        "citation": "Art. L1221-1 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006901170",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000033020658",
        "article_number": "L1237-11",
        "title": "Article L1237-11 - Rupture conventionnelle",
        "text": "L'employeur et le salarié peuvent convenir en commun des conditions de la rupture "
                "du contrat de travail qui les lie. La rupture conventionnelle, exclusive du licenciement "
                "ou de la démission, ne peut être imposée par l'une ou l'autre des parties.",
        "citation": "Art. L1237-11 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033020658",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006901212",
        "article_number": "L1225-1",
        "title": "Article L1225-1 - Protection de la maternité",
        "text": "L'employeur ne doit pas prendre en considération l'état de grossesse d'une femme "
                "pour refuser de l'embaucher, pour rompre son contrat de travail au cours d'une période d'essai "
                "ou pour prononcer une mutation d'emploi.",
        "citation": "Art. L1225-1 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006901212",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006902882",
        "article_number": "L1152-1",
        "title": "Article L1152-1 - Harcèlement moral",
        "text": "Aucun salarié ne doit subir les agissements répétés de harcèlement moral "
                "qui ont pour objet ou pour effet une dégradation de ses conditions de travail "
                "susceptible de porter atteinte à ses droits et à sa dignité, d'altérer sa santé physique "
                "ou mentale ou de compromettre son avenir professionnel.",
        "citation": "Art. L1152-1 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006902882",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "LEGIARTI000006904019",
        "article_number": "L3121-27",
        "title": "Article L3121-27 - Durée légale du travail",
        "text": "La durée légale de travail effectif des salariés à temps complet est fixée "
                "à trente-cinq heures par semaine.",
        "citation": "Art. L3121-27 C. trav.",
        "code_name": "Code du travail",
        "provenance": {
            "source": "legi",
            "source_name": "Légifrance",
            "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006904019",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# CORPUS DATA — JURISPRUDENCE CASSATION
# ═══════════════════════════════════════════════════════════════════════════════

JURISPRUDENCE_CASS = [
    {
        "origin_id": "JURITEXT000007029988",
        "ecli": "ECLI:FR:CCASS:2002:SO01234",
        "court": "Cour de cassation",
        "chamber": "Chambre sociale",
        "date": "2002-07-10",
        "title": "Clause de non-concurrence - Contrepartie financière",
        "text": "La clause de non-concurrence n'est licite que si elle est indispensable "
                "à la protection des intérêts légitimes de l'entreprise, limitée dans le temps et dans l'espace, "
                "qu'elle tient compte des spécificités de l'emploi du salarié et comporte l'obligation "
                "pour l'employeur de verser au salarié une contrepartie financière.",
        "citation": "Cass. soc., 10 juill. 2002, n° 00-45.135",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000007029988",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000007046555",
        "ecli": "ECLI:FR:CCASS:2001:SO02345",
        "court": "Cour de cassation",
        "chamber": "Chambre sociale",
        "date": "2001-03-28",
        "title": "Licenciement - Cause réelle et sérieuse",
        "text": "Le licenciement pour motif personnel doit être fondé sur une cause réelle et sérieuse. "
                "La cause réelle est celle qui existe objectivement et qui peut être vérifiée. "
                "La cause sérieuse est celle qui rend impossible le maintien du salarié dans l'entreprise.",
        "citation": "Cass. soc., 28 mars 2001, n° 99-41.258",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000007046555",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000020050015",
        "ecli": "ECLI:FR:CCASS:2008:CO03456",
        "court": "Cour de cassation",
        "chamber": "Chambre commerciale",
        "date": "2008-06-03",
        "title": "Obligation d'information précontractuelle",
        "text": "Manque à son obligation précontractuelle d'information le vendeur professionnel "
                "qui omet d'informer l'acquéreur non professionnel de l'existence d'un défaut "
                "affectant la chose vendue et dont il avait connaissance.",
        "citation": "Cass. com., 3 juin 2008, n° 07-14.102",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000020050015",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000033456789",
        "ecli": "ECLI:FR:CCASS:2016:CI04567",
        "court": "Cour de cassation",
        "chamber": "Première chambre civile",
        "date": "2016-09-14",
        "title": "RGPD - Droit à l'effacement",
        "text": "Le responsable du traitement est tenu d'effacer les données à caractère personnel "
                "dans les meilleurs délais lorsque les données ne sont plus nécessaires au regard des finalités "
                "pour lesquelles elles ont été collectées ou traitées.",
        "citation": "Cass. 1re civ., 14 sept. 2016, n° 15-17.729",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000033456789",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000037891234",
        "ecli": "ECLI:FR:CCASS:2018:SO05678",
        "court": "Cour de cassation",
        "chamber": "Chambre sociale",
        "date": "2018-11-21",
        "title": "Télétravail - Accident du travail",
        "text": "L'accident survenu sur le lieu où est exercé le télétravail pendant l'exercice "
                "de l'activité professionnelle du télétravailleur est présumé être un accident de travail "
                "au sens de l'article L. 411-1 du code de la sécurité sociale.",
        "citation": "Cass. soc., 21 nov. 2018, n° 17-19.524",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000037891234",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000042567890",
        "ecli": "ECLI:FR:CCASS:2020:CI06789",
        "court": "Cour de cassation",
        "chamber": "Première chambre civile",
        "date": "2020-02-05",
        "title": "Consentement - Vice du consentement",
        "text": "Le dol est une cause de nullité de la convention lorsque les manœuvres pratiquées "
                "par l'une des parties sont telles qu'il est évident que, sans ces manœuvres, "
                "l'autre partie n'aurait pas contracté.",
        "citation": "Cass. 1re civ., 5 févr. 2020, n° 18-25.147",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000042567890",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
    {
        "origin_id": "JURITEXT000045678901",
        "ecli": "ECLI:FR:CCASS:2022:SO07890",
        "court": "Cour de cassation",
        "chamber": "Chambre sociale",
        "date": "2022-04-13",
        "title": "Discrimination - Charge de la preuve",
        "text": "En cas de litige relatif à une discrimination, le salarié présente des éléments de fait "
                "laissant supposer l'existence d'une discrimination. Au vu de ces éléments, "
                "il incombe à l'employeur de prouver que sa décision est justifiée par des éléments objectifs "
                "étrangers à toute discrimination.",
        "citation": "Cass. soc., 13 avr. 2022, n° 20-22.058",
        "provenance": {
            "source": "cass",
            "source_name": "Jurisprudence Cour de cassation",
            "origin_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000045678901",
            "license_name": "Licence Ouverte 2.0",
            "access_mode": "api",
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED CORPUS
# ═══════════════════════════════════════════════════════════════════════════════

CORPUS = CODE_CIVIL_ARTICLES + CODE_TRAVAIL_ARTICLES + JURISPRUDENCE_CASS


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX CREATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def create_test_index(index_dir: Path) -> "LegalIndex":
    """
    Create a test FTS5 index populated with the corpus.
    
    Args:
        index_dir: Directory to create the index in
        
    Returns:
        LegalIndex instance ready for search
    """
    from python.legal_sources.indexing import LegalIndex
    from python.legal_sources.models import LegalDocument, LegalChunk, Provenance
    
    # Ensure directory exists
    index_dir.mkdir(parents=True, exist_ok=True)
    
    # Create index
    index = LegalIndex(index_dir)
    
    # Insert documents
    for i, doc_data in enumerate(CORPUS):
        # Create provenance
        prov_data = doc_data.get("provenance", {})
        provenance = Provenance(
            source=prov_data.get("source", "legi"),
            source_name=prov_data.get("source_name", "Légifrance"),
            origin_id=doc_data["origin_id"],
            origin_url=prov_data.get("origin_url", ""),
            license_name=prov_data.get("license_name", "Licence Ouverte 2.0"),
            license_url=prov_data.get("license_url", ""),
            access_mode=prov_data.get("access_mode", "api"),
        )
        
        # Create document
        doc = LegalDocument(
            doc_id=f"doc_{i:03d}",
            source=prov_data.get("source", "legi"),
            origin_id=doc_data["origin_id"],
            document_type="article" if "article_number" in doc_data else "jurisprudence",
            jurisdiction="fr",
            title=doc_data.get("title", ""),
            citation=doc_data.get("citation", ""),
            date=doc_data.get("date", ""),
            code_name=doc_data.get("code_name", "Code civil"),
            article_number=doc_data.get("article_number", ""),
            court=doc_data.get("court", ""),
            chamber=doc_data.get("chamber", ""),
            ecli=doc_data.get("ecli", ""),
            provenance=provenance,
        )
        
        # Create chunk
        chunk = LegalChunk(
            chunk_id=f"chunk_{i:03d}",
            doc_id=doc.doc_id,
            chunk_index=0,
            source=doc.source,
            document_type=doc.document_type,
            citation=doc.citation,
            pinpoint="",
            text=doc_data["text"],
            provenance=provenance,
        )
        
        # Index document and chunk
        index.index_document(doc, [chunk])
    
    return index


def get_corpus_size() -> int:
    """Return the number of documents in the corpus."""
    return len(CORPUS)


def get_corpus_citations() -> List[str]:
    """Return all citations in the corpus."""
    return [doc["citation"] for doc in CORPUS]


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "CORPUS",
    "CODE_CIVIL_ARTICLES",
    "CODE_TRAVAIL_ARTICLES",
    "JURISPRUDENCE_CASS",
    "create_test_index",
    "get_corpus_size",
    "get_corpus_citations",
]

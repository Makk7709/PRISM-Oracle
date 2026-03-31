"""
Tests unitaires SESSION 4 — Source Taxonomy

Couverture :
- SourceTypeFR enum : exhaustivite, valeurs
- SourceOrigin enum : exhaustivite, valeurs
- Inference type : 25+ sources reelles (Cass, CE, CA, CJUE, CEDH, Art. L, loi, decret,
  reglement UE, directive UE, circulaire, avis CNIL, rapport officiel, convention collective,
  doctrine, reponse ministerielle)
- CEDH ≠ CJUE : separation stricte
- Inference origin : URL et publisher
- Fiabilite : calibration par type
- classify_source : integration complete
- Retrocompatibilite SourceNote : legacy sans nouveaux champs
- SourceNote.to_dict : inclut les nouveaux champs
"""

import pytest

from python.helpers.source_taxonomy import (
    SourceTypeFR,
    SourceOrigin,
    infer_source_type,
    infer_source_origin,
    get_reliability_for_type,
    classify_source,
    _RELIABILITY_BY_TYPE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceTypeFREnum:
    def test_has_15_members(self):
        assert len(SourceTypeFR) == 15

    def test_cedh_distinct_from_cjue(self):
        assert SourceTypeFR.JURISPRUDENCE_CEDH != SourceTypeFR.JURISPRUDENCE_CJUE
        assert SourceTypeFR.JURISPRUDENCE_CEDH.value != SourceTypeFR.JURISPRUDENCE_CJUE.value

    def test_all_values_are_strings(self):
        for member in SourceTypeFR:
            assert isinstance(member.value, str)

    def test_from_string(self):
        assert SourceTypeFR("jurisprudence_cass") == SourceTypeFR.JURISPRUDENCE_CASS


class TestSourceOriginEnum:
    def test_has_12_members(self):
        assert len(SourceOrigin) == 12

    def test_hudoc_exists(self):
        assert SourceOrigin.HUDOC.value == "hudoc"

    def test_from_string(self):
        assert SourceOrigin("legifrance") == SourceOrigin.LEGIFRANCE


# ═══════════════════════════════════════════════════════════════════════════════
# Inference type — Sources reelles (25+ cas)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferSourceType:
    # -- Jurisprudence Cass --
    def test_cass_com(self):
        assert infer_source_type(title="Cass. com., 18 mai 2021, n°19-21.260") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_cass_soc(self):
        assert infer_source_type(title="Cass. soc., 15 mars 2023, n°21-12.345") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_cass_civ1(self):
        assert infer_source_type(title="Cass. 1re civ., 12 janvier 2022") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_cass_crim(self):
        assert infer_source_type(title="Cass. crim., 25 nov. 2020") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_cass_ass_plen(self):
        assert infer_source_type(title="Cass. ass. plén., 5 oct. 2018") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_pourvoi_number(self):
        assert infer_source_type(title="n°19-21.260") == SourceTypeFR.JURISPRUDENCE_CASS

    def test_cour_de_cassation(self):
        assert infer_source_type(title="Cour de cassation, chambre sociale") == SourceTypeFR.JURISPRUDENCE_CASS

    # -- Jurisprudence CE --
    def test_conseil_etat(self):
        assert infer_source_type(title="CE, 10 février 2023, n°456123") == SourceTypeFR.JURISPRUDENCE_CE

    def test_conseil_etat_full(self):
        assert infer_source_type(title="Conseil d'État, 15 mars 2022") == SourceTypeFR.JURISPRUDENCE_CE

    def test_ce_sect(self):
        assert infer_source_type(title="CE, sect., 12 mai 2021") == SourceTypeFR.JURISPRUDENCE_CE

    # -- Jurisprudence CA --
    def test_cour_appel_paris(self):
        assert infer_source_type(title="CA Paris, 5 septembre 2023") == SourceTypeFR.JURISPRUDENCE_CA

    def test_cour_appel_full(self):
        assert infer_source_type(title="Cour d'appel de Lyon, 12 mars 2022") == SourceTypeFR.JURISPRUDENCE_CA

    # -- CEDH (doit etre distinct de CJUE) --
    def test_cedh_explicit(self):
        assert infer_source_type(title="CEDH, 15 mars 2022, X c. France") == SourceTypeFR.JURISPRUDENCE_CEDH

    def test_cedh_cour_europeenne_droits(self):
        assert infer_source_type(title="Cour européenne des droits de l'homme, 3 oct. 2019") == SourceTypeFR.JURISPRUDENCE_CEDH

    def test_cedh_c_france(self):
        assert infer_source_type(title="Arrêt c. France du 15 mars 2022") == SourceTypeFR.JURISPRUDENCE_CEDH

    # -- CJUE --
    def test_cjue_explicit(self):
        assert infer_source_type(title="CJUE, C-265/19, 8 sept. 2020") == SourceTypeFR.JURISPRUDENCE_CJUE

    def test_cjce(self):
        assert infer_source_type(title="CJCE, 12 nov. 2003") == SourceTypeFR.JURISPRUDENCE_CJUE

    def test_cjue_c_number(self):
        assert infer_source_type(title="Affaire C-311/18 Schrems II") == SourceTypeFR.JURISPRUDENCE_CJUE

    # -- Texte legislatif --
    def test_article_code_commerce(self):
        assert infer_source_type(title="Art. L441-10 Code de commerce") == SourceTypeFR.TEXTE_LEGISLATIF

    def test_loi(self):
        assert infer_source_type(title="Loi n°2024-120 du 15 mars 2024") == SourceTypeFR.TEXTE_LEGISLATIF

    def test_ordonnance(self):
        assert infer_source_type(title="Ordonnance n°2019-359 du 24 avril 2019") == SourceTypeFR.TEXTE_LEGISLATIF

    def test_code_civil(self):
        assert infer_source_type(title="Code civil, art. 1103") == SourceTypeFR.TEXTE_LEGISLATIF

    def test_code_du_travail(self):
        assert infer_source_type(title="C. trav. L1234-5") == SourceTypeFR.TEXTE_LEGISLATIF

    # -- Texte reglementaire --
    def test_decret(self):
        assert infer_source_type(title="Décret n°2023-456 du 12 mai 2023") == SourceTypeFR.TEXTE_REGLEMENTAIRE

    def test_arrete(self):
        assert infer_source_type(title="Arrêté ministériel du 15 janvier 2024") == SourceTypeFR.TEXTE_REGLEMENTAIRE

    # -- Reglement UE --
    def test_rgpd(self):
        assert infer_source_type(title="RGPD art. 17") == SourceTypeFR.REGLEMENT_UE

    def test_ai_act(self):
        assert infer_source_type(title="AI Act, Annexe III") == SourceTypeFR.REGLEMENT_UE

    def test_reglement_ue_numero(self):
        assert infer_source_type(title="Règlement (UE) n°2024/1689") == SourceTypeFR.REGLEMENT_UE

    # -- Directive UE --
    def test_directive_ue(self):
        assert infer_source_type(title="Directive (UE) 2019/1152") == SourceTypeFR.DIRECTIVE_UE

    def test_directive_short(self):
        assert infer_source_type(title="Directive 93/13") == SourceTypeFR.DIRECTIVE_UE

    # -- Circulaire --
    def test_circulaire_dgfip(self):
        assert infer_source_type(title="Circ. DGFIP du 12/01/2024") == SourceTypeFR.CIRCULAIRE

    def test_circulaire_full(self):
        assert infer_source_type(title="Circulaire du 15 mars 2023") == SourceTypeFR.CIRCULAIRE

    # -- Avis d'autorite --
    def test_cnil_deliberation(self):
        assert infer_source_type(title="Délibération CNIL n°2023-001") == SourceTypeFR.AVIS_AUTORITE

    def test_amf(self):
        assert infer_source_type(title="Recommandation AMF n°2023-04") == SourceTypeFR.AVIS_AUTORITE

    def test_avis_cnil(self):
        assert infer_source_type(title="Avis du CNIL sur l'utilisation de l'IA") == SourceTypeFR.AVIS_AUTORITE

    def test_cnil_in_text(self):
        assert infer_source_type(excerpt="La CNIL a émis une sanction...") == SourceTypeFR.AVIS_AUTORITE

    # -- Rapport officiel --
    def test_rapport_senat(self):
        assert infer_source_type(title="Rapport du Sénat n°123") == SourceTypeFR.RAPPORT_OFFICIEL

    def test_reponse_ministerielle(self):
        assert infer_source_type(title="Réponse ministérielle n°456") == SourceTypeFR.RAPPORT_OFFICIEL

    def test_rapport_cour_comptes(self):
        assert infer_source_type(title="Rapport de la Cour des comptes 2023") == SourceTypeFR.RAPPORT_OFFICIEL

    # -- Convention collective --
    def test_ccn(self):
        assert infer_source_type(title="CCN Métallurgie") == SourceTypeFR.CONVENTION_COLLECTIVE

    def test_convention_collective(self):
        assert infer_source_type(title="Convention collective nationale des cadres") == SourceTypeFR.CONVENTION_COLLECTIVE

    def test_idcc(self):
        assert infer_source_type(title="IDCC 3248 — Métallurgie") == SourceTypeFR.CONVENTION_COLLECTIVE

    def test_accord_branche(self):
        assert infer_source_type(title="Accord de branche du 15 mars 2023") == SourceTypeFR.CONVENTION_COLLECTIVE

    # -- Autre --
    def test_unknown_text(self):
        assert infer_source_type(title="Document interne de travail") == SourceTypeFR.AUTRE

    def test_none_inputs(self):
        assert infer_source_type() == SourceTypeFR.AUTRE

    def test_empty_inputs(self):
        assert infer_source_type(title="", excerpt="") == SourceTypeFR.AUTRE

    # -- Priorite title > excerpt > publisher --
    def test_title_priority_over_excerpt(self):
        result = infer_source_type(
            title="CEDH, 15 mars 2022",
            excerpt="La CJUE a confirmé...",
        )
        assert result == SourceTypeFR.JURISPRUDENCE_CEDH

    def test_excerpt_fallback(self):
        result = infer_source_type(
            title=None,
            excerpt="Cass. com., 18 mai 2021",
        )
        assert result == SourceTypeFR.JURISPRUDENCE_CASS


# ═══════════════════════════════════════════════════════════════════════════════
# Inference origin
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferSourceOrigin:
    def test_legifrance_url(self):
        assert infer_source_origin(url="https://www.legifrance.gouv.fr/juri/id/12345") == SourceOrigin.LEGIFRANCE

    def test_eur_lex_url(self):
        assert infer_source_origin(url="https://eur-lex.europa.eu/legal-content/FR/TXT/") == SourceOrigin.EUR_LEX

    def test_judilibre_url(self):
        assert infer_source_origin(url="https://www.courdecassation.fr/decision/123") == SourceOrigin.JUDILIBRE

    def test_hudoc_url(self):
        assert infer_source_origin(url="https://hudoc.echr.coe.int/eng?i=001-123") == SourceOrigin.HUDOC

    def test_cnil_url(self):
        assert infer_source_origin(url="https://www.cnil.fr/fr/deliberation-2023") == SourceOrigin.CNIL

    def test_amf_url(self):
        assert infer_source_origin(url="https://www.amf-france.org/fr/reglementation") == SourceOrigin.AMF

    def test_senat_url(self):
        assert infer_source_origin(url="https://www.senat.fr/rap/l22-123/l22-123.html") == SourceOrigin.SENAT

    def test_publisher_legifrance(self):
        assert infer_source_origin(publisher="Legifrance") == SourceOrigin.LEGIFRANCE

    def test_publisher_cnil(self):
        assert infer_source_origin(publisher="CNIL") == SourceOrigin.CNIL

    def test_publisher_conseil_etat(self):
        assert infer_source_origin(publisher="Conseil d'État") == SourceOrigin.CONSEIL_ETAT

    def test_url_priority_over_publisher(self):
        result = infer_source_origin(
            url="https://eur-lex.europa.eu/doc",
            publisher="Legifrance",
        )
        assert result == SourceOrigin.EUR_LEX

    def test_unknown(self):
        assert infer_source_origin(url="https://example.com") == SourceOrigin.AUTRE

    def test_none_inputs(self):
        assert infer_source_origin() == SourceOrigin.AUTRE


# ═══════════════════════════════════════════════════════════════════════════════
# Fiabilite
# ═══════════════════════════════════════════════════════════════════════════════

class TestReliability:
    def test_all_types_have_reliability(self):
        for member in SourceTypeFR:
            score = get_reliability_for_type(member)
            assert 0 <= score <= 100, f"{member}: {score}"

    def test_texte_legislatif_highest(self):
        assert get_reliability_for_type(SourceTypeFR.TEXTE_LEGISLATIF) >= 90

    def test_doctrine_lower_than_jurisprudence(self):
        assert get_reliability_for_type(SourceTypeFR.DOCTRINE) < get_reliability_for_type(SourceTypeFR.JURISPRUDENCE_CASS)

    def test_autre_lowest(self):
        scores = [get_reliability_for_type(t) for t in SourceTypeFR if t != SourceTypeFR.AUTRE]
        assert get_reliability_for_type(SourceTypeFR.AUTRE) <= min(scores)

    def test_reglementaire_lower_than_legislatif(self):
        assert get_reliability_for_type(SourceTypeFR.TEXTE_REGLEMENTAIRE) <= get_reliability_for_type(SourceTypeFR.TEXTE_LEGISLATIF)

    def test_circulaire_lower_than_avis(self):
        assert get_reliability_for_type(SourceTypeFR.CIRCULAIRE) <= get_reliability_for_type(SourceTypeFR.AVIS_AUTORITE)


# ═══════════════════════════════════════════════════════════════════════════════
# classify_source (integration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifySource:
    def test_full_classification(self):
        src_type, origin, reliability = classify_source(
            title="Cass. com., 18 mai 2021, n°19-21.260",
            url="https://www.legifrance.gouv.fr/juri/id/12345",
        )
        assert src_type == SourceTypeFR.JURISPRUDENCE_CASS
        assert origin == SourceOrigin.LEGIFRANCE
        assert reliability == 90

    def test_cedh_hudoc(self):
        src_type, origin, reliability = classify_source(
            title="CEDH, 15 mars 2022, X c. France",
            url="https://hudoc.echr.coe.int/eng?i=001-123",
        )
        assert src_type == SourceTypeFR.JURISPRUDENCE_CEDH
        assert origin == SourceOrigin.HUDOC
        assert reliability == 88

    def test_cjue_eurlex(self):
        src_type, origin, reliability = classify_source(
            title="CJUE, C-265/19",
            url="https://eur-lex.europa.eu/doc",
        )
        assert src_type == SourceTypeFR.JURISPRUDENCE_CJUE
        assert origin == SourceOrigin.EUR_LEX
        assert reliability == 90

    def test_unknown_fallback(self):
        src_type, origin, reliability = classify_source(title="Random text")
        assert src_type == SourceTypeFR.AUTRE
        assert origin == SourceOrigin.AUTRE
        assert reliability == 50


# ═══════════════════════════════════════════════════════════════════════════════
# Retrocompatibilite SourceNote
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceNoteRetrocompat:
    """Verifie que les SourceNote existantes (sans nouveaux champs) fonctionnent."""

    @pytest.fixture(autouse=True)
    def _disable_p5(self, monkeypatch):
        """Desactive le P5 version enforcement pour les tests de retrocompat."""
        monkeypatch.setenv("LEGAL_VERSION_ENFORCEMENT", "0")

    def _make_legacy_dict(self):
        """Dict SourceNote au format pre-SESSION 4 (sans taxonomy)."""
        from python.helpers.legal_agent_contracts import compute_excerpt_hash
        excerpt = "Art. 1103 du Code civil"
        return {
            "origin_url": "https://www.legifrance.gouv.fr/codes/id/123",
            "publisher": "legifrance",
            "jurisdiction": "fr",
            "excerpt": excerpt,
            "excerpt_hash": compute_excerpt_hash(excerpt),
            "chunk_id": "chunk_legacy_001",
            "confidence": 0.9,
        }

    def test_legacy_from_dict_no_crash(self):
        from python.helpers.legal_agent_contracts import SourceNote
        d = self._make_legacy_dict()
        sn = SourceNote.from_dict(d)
        assert sn.source_type_fr is None
        assert sn.source_origin is None
        assert sn.reliability_percent is None
        assert sn.agent_attribution is None

    def test_legacy_to_dict_excludes_none_taxonomy(self):
        from python.helpers.legal_agent_contracts import SourceNote
        d = self._make_legacy_dict()
        sn = SourceNote.from_dict(d)
        out = sn.to_dict()
        assert "source_type_fr" not in out
        assert "source_origin" not in out
        assert "reliability_percent" not in out
        assert "agent_attribution" not in out

    def test_new_fields_in_to_dict_when_set(self):
        from python.helpers.legal_agent_contracts import SourceNote
        d = self._make_legacy_dict()
        d["source_type_fr"] = "jurisprudence_cass"
        d["source_origin"] = "legifrance"
        d["reliability_percent"] = 90
        d["agent_attribution"] = "legal_safe"
        sn = SourceNote.from_dict(d)
        out = sn.to_dict()
        assert out["source_type_fr"] == "jurisprudence_cass"
        assert out["source_origin"] == "legifrance"
        assert out["reliability_percent"] == 90
        assert out["agent_attribution"] == "legal_safe"

    def test_create_factory_with_taxonomy(self):
        from python.helpers.legal_agent_contracts import SourceNote
        sn = SourceNote.create(
            origin_url="https://www.legifrance.gouv.fr/codes/id/123",
            publisher="legifrance",
            jurisdiction="fr",
            excerpt="Art. 1103 du Code civil",
            chunk_id="chunk_001",
            source_type_fr="texte_legislatif",
            source_origin="legifrance",
            reliability_percent=95,
            agent_attribution="legal_safe",
        )
        assert sn.source_type_fr == "texte_legislatif"
        assert sn.reliability_percent == 95

    def test_from_dict_roundtrip_with_taxonomy(self):
        from python.helpers.legal_agent_contracts import SourceNote
        d = self._make_legacy_dict()
        d["source_type_fr"] = "texte_legislatif"
        d["source_origin"] = "legifrance"
        d["reliability_percent"] = 95
        d["agent_attribution"] = "researcher"
        sn = SourceNote.from_dict(d)
        out = sn.to_dict()
        sn2 = SourceNote.from_dict(out)
        assert sn2.source_type_fr == sn.source_type_fr
        assert sn2.source_origin == sn.source_origin
        assert sn2.reliability_percent == sn.reliability_percent
        assert sn2.agent_attribution == sn.agent_attribution


# ═══════════════════════════════════════════════════════════════════════════════
# CEDH ≠ CJUE — Test explicite de non-confusion
# ═══════════════════════════════════════════════════════════════════════════════

class TestCEDHvsCJUE:
    """L'auto-audit exige une distinction stricte CEDH/CJUE."""

    def test_cedh_not_classified_as_cjue(self):
        result = infer_source_type(title="CEDH, 15 mars 2022, X c. France")
        assert result == SourceTypeFR.JURISPRUDENCE_CEDH
        assert result != SourceTypeFR.JURISPRUDENCE_CJUE

    def test_cjue_not_classified_as_cedh(self):
        result = infer_source_type(title="CJUE, C-265/19, 8 sept. 2020")
        assert result == SourceTypeFR.JURISPRUDENCE_CJUE
        assert result != SourceTypeFR.JURISPRUDENCE_CEDH

    def test_cour_europeenne_droits_is_cedh(self):
        result = infer_source_type(title="Cour européenne des droits de l'homme")
        assert result == SourceTypeFR.JURISPRUDENCE_CEDH

    def test_cour_de_justice_ue_is_cjue(self):
        result = infer_source_type(title="Cour de justice de l'UE")
        assert result == SourceTypeFR.JURISPRUDENCE_CJUE

    def test_c_number_is_cjue(self):
        result = infer_source_type(title="C-311/18 (Schrems II)")
        assert result == SourceTypeFR.JURISPRUDENCE_CJUE

    def test_hudoc_origin_for_cedh(self):
        _, origin, _ = classify_source(
            title="CEDH", url="https://hudoc.echr.coe.int/eng"
        )
        assert origin == SourceOrigin.HUDOC

    def test_eurlex_origin_for_cjue(self):
        _, origin, _ = classify_source(
            title="CJUE", url="https://eur-lex.europa.eu/doc"
        )
        assert origin == SourceOrigin.EUR_LEX

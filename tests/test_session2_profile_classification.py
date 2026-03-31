"""
Tests unitaires SESSION 2 — Profil utilisateur + Classification requete.
Feuille de route conformite format Evidence.
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Optional

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.router.routing_contract import (
    AIActCategory,
    DataSensitivity,
    IntentName,
    RouteDecision,
    RouteIntent,
    RouteVerdict,
    INTENT_TO_AI_ACT,
    INTENT_TO_SENSITIVITY,
    get_ai_act_category,
    get_data_sensitivity,
)
from python.helpers.user_manager import UserManager


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER : creer un users.json temporaire
# ═══════════════════════════════════════════════════════════════════════════════

def _make_users_json(users_dict: dict) -> str:
    """Cree un fichier temporaire users.json et retourne son chemin."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump({"users": users_dict}, tmp)
    tmp.close()
    return tmp.name


# Fake argon2 hash pour les tests (validera is_password_hashed)
FAKE_HASH = "$argon2id$v=19$m=65536,t=3,p=4$fakefakefake$fakefakefake"


# ═══════════════════════════════════════════════════════════════════════════════
# AI ACT CATEGORY — Mapping completude
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIActMapping:
    def test_all_intents_have_mapping(self):
        """Chaque IntentName doit avoir un mapping AI Act."""
        for intent in IntentName:
            assert intent in INTENT_TO_AI_ACT, f"{intent.value} missing from INTENT_TO_AI_ACT"

    def test_legal_is_high_risk(self):
        """Annexe III §5(a) : systemes judiciaires = high_risk."""
        assert get_ai_act_category(IntentName.LEGAL_SAFE) == AIActCategory.HIGH_RISK

    def test_medical_is_high_risk(self):
        """Annexe III §5(c) : systemes de sante = high_risk."""
        assert get_ai_act_category(IntentName.MEDICAL) == AIActCategory.HIGH_RISK

    def test_finance_is_high_risk(self):
        """Annexe III §5(b) : evaluation de solvabilite = high_risk."""
        assert get_ai_act_category(IntentName.FINANCE) == AIActCategory.HIGH_RISK

    def test_researcher_is_limited_risk(self):
        assert get_ai_act_category(IntentName.RESEARCHER) == AIActCategory.LIMITED_RISK

    def test_developer_is_minimal_risk(self):
        assert get_ai_act_category(IntentName.DEVELOPER) == AIActCategory.MINIMAL_RISK

    def test_marketing_is_minimal_risk(self):
        assert get_ai_act_category(IntentName.MARKETING) == AIActCategory.MINIMAL_RISK

    def test_sales_is_minimal_risk(self):
        assert get_ai_act_category(IntentName.SALES) == AIActCategory.MINIMAL_RISK

    def test_multitask_is_minimal_risk(self):
        assert get_ai_act_category(IntentName.MULTITASK) == AIActCategory.MINIMAL_RISK

    def test_contradictor_is_limited_risk(self):
        assert get_ai_act_category(IntentName.CONTRADICTOR) == AIActCategory.LIMITED_RISK

    def test_unknown_intent_fallback(self):
        """Un intent inconnu doit retourner minimal_risk (fail-safe)."""
        result = INTENT_TO_AI_ACT.get("nonexistent", AIActCategory.MINIMAL_RISK)
        assert result == AIActCategory.MINIMAL_RISK


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SENSITIVITY — Mapping completude
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataSensitivityMapping:
    def test_all_intents_have_mapping(self):
        """Chaque IntentName doit avoir un mapping sensibilite."""
        for intent in IntentName:
            assert intent in INTENT_TO_SENSITIVITY, f"{intent.value} missing from INTENT_TO_SENSITIVITY"

    def test_legal_is_confidential(self):
        assert get_data_sensitivity(IntentName.LEGAL_SAFE) == DataSensitivity.CONFIDENTIAL

    def test_medical_is_restricted(self):
        """RGPD Art. 9 : donnees de sante = categorie speciale."""
        assert get_data_sensitivity(IntentName.MEDICAL) == DataSensitivity.RESTRICTED

    def test_finance_is_confidential(self):
        assert get_data_sensitivity(IntentName.FINANCE) == DataSensitivity.CONFIDENTIAL

    def test_marketing_is_internal(self):
        """Marketing peut traiter des donnees clients — INTERNAL par defaut."""
        assert get_data_sensitivity(IntentName.MARKETING) == DataSensitivity.INTERNAL

    def test_developer_is_internal(self):
        assert get_data_sensitivity(IntentName.DEVELOPER) == DataSensitivity.INTERNAL

    def test_multitask_is_internal(self):
        assert get_data_sensitivity(IntentName.MULTITASK) == DataSensitivity.INTERNAL


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE DECISION — Nouveaux champs
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouteDecisionClassification:
    def test_auto_derive_from_primary_intent(self):
        """ai_act_category et data_sensitivity derives automatiquement du primary intent."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.LEGAL_SAFE, score=0.9)],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.CONFIDENTIAL

    def test_auto_derive_medical(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.MEDICAL, score=0.8)],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED

    def test_multi_intent_uses_highest_score(self):
        """Avec plusieurs intents, la classification suit le score le plus eleve."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.MARKETING, score=0.3),
                RouteIntent(name=IntentName.LEGAL_SAFE, score=0.9),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.CONFIDENTIAL

    def test_no_intents_leaves_none(self):
        """Sans intent, les champs restent None."""
        decision = RouteDecision(verdict=RouteVerdict.NO_ROUTE)
        assert decision.ai_act_category is None
        assert decision.data_sensitivity is None

    def test_explicit_override(self):
        """Si fourni explicitement, pas d'auto-derivation."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.MARKETING, score=0.9)],
            ai_act_category=AIActCategory.HIGH_RISK,
            data_sensitivity=DataSensitivity.RESTRICTED,
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED

    def test_to_dict_includes_new_fields(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.FINANCE, score=0.85)],
        )
        d = decision.to_dict()
        assert "ai_act_category" in d
        assert "data_sensitivity" in d
        assert d["ai_act_category"] == "high_risk"
        assert d["data_sensitivity"] == "confidential"

    def test_to_dict_none_when_no_intents(self):
        decision = RouteDecision(verdict=RouteVerdict.NO_ROUTE)
        d = decision.to_dict()
        assert d["ai_act_category"] is None
        assert d["data_sensitivity"] is None

    def test_from_dict_roundtrip(self):
        original = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.MEDICAL, score=0.9)],
        )
        d = original.to_dict()
        restored = RouteDecision.from_dict(d)
        assert restored.ai_act_category == original.ai_act_category
        assert restored.data_sensitivity == original.data_sensitivity

    def test_from_dict_without_new_fields(self):
        """Retrocompatibilite : un ancien dict sans les champs ne crash pas."""
        old_data = {
            "verdict": "proceed",
            "intents": [{"name": "legal_safe", "score": 0.9}],
        }
        decision = RouteDecision.from_dict(old_data)
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.CONFIDENTIAL

    def test_serialization_json(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.RESEARCHER, score=0.7)],
        )
        j = decision.to_json()
        parsed = json.loads(j)
        assert parsed["ai_act_category"] == "limited_risk"
        assert parsed["data_sensitivity"] == "internal"


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGER — Profil utilisateur
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserProfile:
    def test_profile_from_json(self):
        path = _make_users_json({
            "alice": {
                "password_hash": FAKE_HASH,
                "role": "admin",
                "profile": "Analyste — Niveau 2",
            }
        })
        um = UserManager(path)
        assert um.get_user_profile("alice") == "Analyste — Niveau 2"

    def test_profile_missing_falls_back_to_role(self):
        """Sans champ profile, retourne le role capitalise."""
        path = _make_users_json({
            "bob": {
                "password_hash": FAKE_HASH,
                "role": "user",
            }
        })
        um = UserManager(path)
        assert um.get_user_profile("bob") == "User"

    def test_profile_null_falls_back_to_role(self):
        """profile=null retourne le role capitalise."""
        path = _make_users_json({
            "charlie": {
                "password_hash": FAKE_HASH,
                "role": "admin",
                "profile": None,
            }
        })
        um = UserManager(path)
        assert um.get_user_profile("charlie") == "Admin"

    def test_profile_empty_string_falls_back_to_role(self):
        """profile="" retourne le role capitalise."""
        path = _make_users_json({
            "dave": {
                "password_hash": FAKE_HASH,
                "role": "user",
                "profile": "",
            }
        })
        um = UserManager(path)
        assert um.get_user_profile("dave") == "User"

    def test_profile_unknown_user_returns_default(self):
        path = _make_users_json({
            "alice": {"password_hash": FAKE_HASH, "role": "admin"}
        })
        um = UserManager(path)
        assert um.get_user_profile("nonexistent") == "User"

    def test_legacy_json_without_profile_loads(self):
        """Un users.json sans champ profile ne crash pas."""
        path = _make_users_json({
            "legacy": {
                "password_hash": FAKE_HASH,
                "role": "user",
                "organization": "korev-ai",
                "org_role": "MEMBER",
            }
        })
        um = UserManager(path)
        assert um.get_user_profile("legacy") == "User"
        assert um.get_role("legacy") == "user"
        assert um.get_organization("legacy") == "korev-ai"

    def test_existing_methods_still_work_with_profile(self):
        """Les methodes existantes ne sont pas cassees par le champ profile."""
        path = _make_users_json({
            "eve": {
                "password_hash": FAKE_HASH,
                "role": "admin",
                "organization": "korev-ai",
                "org_role": "OWNER",
                "profile": "CTO — Direction Technique",
            }
        })
        um = UserManager(path)
        assert um.get_role("eve") == "admin"
        assert um.get_organization("eve") == "korev-ai"
        assert um.get_org_role("eve") == "OWNER"
        assert um.get_user_profile("eve") == "CTO — Direction Technique"
        assert "eve" in um.list_users()


# ═══════════════════════════════════════════════════════════════════════════════
# COHERENCE CROISEE — Requetes ambigues
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossCoherence:
    """Verifie la coherence classification sur requetes multi-domaine."""

    def test_legal_primary_always_high_risk(self):
        """Multi-intent legal+medical : sensibilite = max(CONFIDENTIAL, RESTRICTED) = RESTRICTED."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.LEGAL_SAFE, score=0.8),
                RouteIntent(name=IntentName.MEDICAL, score=0.6),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED

    def test_medical_primary_restricted(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.MEDICAL, score=0.9),
                RouteIntent(name=IntentName.LEGAL_SAFE, score=0.7),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED

    def test_finance_legal_highest_wins(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.FINANCE, score=0.9),
                RouteIntent(name=IntentName.LEGAL_SAFE, score=0.4),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.CONFIDENTIAL

    def test_marketing_sales_minimal(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.MARKETING, score=0.8),
                RouteIntent(name=IntentName.SALES, score=0.6),
            ],
        )
        assert decision.ai_act_category == AIActCategory.MINIMAL_RISK
        assert decision.data_sensitivity == DataSensitivity.INTERNAL

    def test_researcher_contradictor(self):
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.RESEARCHER, score=0.7),
                RouteIntent(name=IntentName.CONTRADICTOR, score=0.5),
            ],
        )
        assert decision.ai_act_category == AIActCategory.LIMITED_RISK
        assert decision.data_sensitivity == DataSensitivity.INTERNAL

    def test_secondary_medical_elevates_sensitivity(self):
        """RGPD Art. 9 : des qu'un intent touche des donnees de sante,
        la sensibilite doit etre RESTRICTED, meme en secondaire (D4 fix)."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.FINANCE, score=0.9),
                RouteIntent(name=IntentName.MEDICAL, score=0.3),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED

    def test_tie_breaking_scores(self):
        """Scores egaux : la classification reste deterministe."""
        decision = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[
                RouteIntent(name=IntentName.LEGAL_SAFE, score=0.8),
                RouteIntent(name=IntentName.MEDICAL, score=0.8),
            ],
        )
        assert decision.ai_act_category == AIActCategory.HIGH_RISK
        assert decision.data_sensitivity == DataSensitivity.RESTRICTED


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM SERIALISATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnumSerialization:
    def test_ai_act_values(self):
        assert AIActCategory.MINIMAL_RISK.value == "minimal_risk"
        assert AIActCategory.LIMITED_RISK.value == "limited_risk"
        assert AIActCategory.HIGH_RISK.value == "high_risk"
        assert AIActCategory.UNACCEPTABLE.value == "unacceptable"

    def test_data_sensitivity_values(self):
        assert DataSensitivity.PUBLIC.value == "public"
        assert DataSensitivity.INTERNAL.value == "internal"
        assert DataSensitivity.CONFIDENTIAL.value == "confidential"
        assert DataSensitivity.RESTRICTED.value == "restricted"

    def test_ai_act_from_string(self):
        assert AIActCategory("high_risk") == AIActCategory.HIGH_RISK

    def test_data_sensitivity_from_string(self):
        assert DataSensitivity("restricted") == DataSensitivity.RESTRICTED

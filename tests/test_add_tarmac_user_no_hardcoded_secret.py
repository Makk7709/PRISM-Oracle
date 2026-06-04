"""Régression SonarQube python:S2068 — `scripts/add_tarmac_user.py` ne doit pas
embarquer de hash de mot de passe en dur ; il doit le lire dans l'environnement
et échouer proprement (fail-closed) si absent ou si ce n'est pas un hash argon2.
"""

import importlib.util
import os

import pytest

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "scripts", "add_tarmac_user.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("add_tarmac_user", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_source_has_no_hardcoded_argon2_hash():
    with open(_SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    assert "$argon2id$v=19$m=65536" not in src, (
        "un hash argon2id réel est encore codé en dur (S2068)"
    )


def test_require_password_hash_fails_when_absent(monkeypatch):
    mod = _load_module()
    monkeypatch.delenv(mod.PASSWORD_HASH_ENV, raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.require_password_hash()
    assert exc.value.code == 2


def test_require_password_hash_rejects_plaintext(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv(mod.PASSWORD_HASH_ENV, "monMotDePasse")
    with pytest.raises(SystemExit) as exc:
        mod.require_password_hash()
    assert exc.value.code == 2


def test_require_password_hash_accepts_argon2(monkeypatch):
    mod = _load_module()
    fake_hash = "$argon2id$v=19$m=65536,t=3,p=4$" + "A" * 22 + "$" + "B" * 43
    monkeypatch.setenv(mod.PASSWORD_HASH_ENV, fake_hash)
    assert mod.require_password_hash() == fake_hash
    user = mod.build_tarmac_user(fake_hash)
    assert user["password_hash"] == fake_hash
    assert user["organization"] == "TARMAC"

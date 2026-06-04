"""Régression SonarQube python:S2612 — `delete_dir` ne doit jamais poser des droits
world-accessible (0o777) lors de la suppression forcée.

Finding cabinet de valo : `python/helpers/files.py:345,348` utilisait `os.chmod(.., 0o777)`
dans le fallback de suppression. Les droits **propriétaire** (0o700) suffisent pour
supprimer une arborescence ; 0o777 ouvre une fenêtre world-writable inutile.

Le test force le chemin « aggressive » (un sous-dossier en lecture seule empêche le
premier rmtree), espionne os.chmod, et vérifie que (a) l'arbo est bien supprimée et
(b) aucun mode posé n'accorde de droit groupe/autres en écriture.
"""

import os
import shutil

import pytest

from python.helpers import files as files_mod


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


@pytest.mark.skipif(_is_root(), reason="root bypass les permissions POSIX")
def test_delete_dir_does_not_grant_world_write(monkeypatch):
    rel = f"tmp/_perm_test_{os.getpid()}"
    base = files_mod.get_abs_path(rel)
    sub = os.path.join(base, "locked")

    # nettoyage défensif d'un run précédent
    if os.path.exists(base):
        for root, dirs, fs in os.walk(base):
            os.chmod(root, 0o700)
        shutil.rmtree(base, ignore_errors=True)

    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "f.txt"), "w", encoding="utf-8") as f:
        f.write("x")
    # sous-dossier read+execute SANS write -> le premier rmtree échoue -> branche aggressive
    os.chmod(sub, 0o500)

    recorded_modes = []
    real_chmod = os.chmod

    def spy_chmod(path, mode, *a, **k):
        recorded_modes.append(mode)
        return real_chmod(path, mode, *a, **k)

    monkeypatch.setattr(os, "chmod", spy_chmod)

    try:
        files_mod.delete_dir(rel)
    finally:
        monkeypatch.undo()
        if os.path.exists(base):
            for root, dirs, fs in os.walk(base):
                try:
                    os.chmod(root, 0o700)
                except OSError:
                    pass
            shutil.rmtree(base, ignore_errors=True)

    assert not os.path.exists(base), "delete_dir aurait dû supprimer l'arborescence"
    assert recorded_modes, "la branche de suppression forcée (chmod) n'a pas été exercée"
    for mode in recorded_modes:
        assert mode & 0o022 == 0, (
            f"delete_dir a posé un mode group/other-writable: {oct(mode)} "
            f"(S2612 — utiliser 0o700)"
        )

"""Régression : `usedforsecurity=False` ne doit pas altérer les digests MD5
utilisés comme checksums/IDs non cryptographiques (knowledge_import,
routing_contract, strategic_charts). Garde aussi contre un remplacement
accidentel de l'algorithme."""
import hashlib
import os
import tempfile

import pytest


def test_usedforsecurity_does_not_change_md5_digest():
    payloads = [b"", b"x", b"KOREV", b"\x00\x01\x02", "accentué éàç".encode()]
    for p in payloads:
        assert (
            hashlib.md5(p, usedforsecurity=False).hexdigest()
            == hashlib.md5(p).hexdigest()
        )


def test_calculate_checksum_stable():
    from python.helpers.knowledge_import import calculate_checksum

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"contenu de reference KOREV")
        path = f.name
    try:
        expected = hashlib.md5(b"contenu de reference KOREV").hexdigest()
        assert calculate_checksum(path) == expected
    finally:
        os.unlink(path)

from python.helpers.path_aliases import (
    normalize_container_path,
    normalize_legacy_paths_in_code,
)


def test_normalize_container_path_korev_to_app():
    assert normalize_container_path("/korev/tmp/uploads/a.pdf") == "/app/tmp/uploads/a.pdf"


def test_normalize_container_path_a0_to_app():
    assert normalize_container_path("/a0/tmp/generated/out.png") == "/app/tmp/generated/out.png"


def test_normalize_container_path_keeps_app():
    assert normalize_container_path("/app/tmp/uploads/a.pdf") == "/app/tmp/uploads/a.pdf"


def test_normalize_legacy_paths_in_code_rewrites_korev_and_a0():
    code = """
input_path = '/korev/tmp/uploads/factures.pdf'
logo_path = "/a0/tmp/generated/logo.png"
"""
    out = normalize_legacy_paths_in_code(code)
    assert "/korev/" not in out
    assert "/a0/" not in out
    assert "/app/tmp/uploads/factures.pdf" in out
    assert "/app/tmp/generated/logo.png" in out


def test_normalize_legacy_paths_in_code_keeps_relative_paths():
    code = "p = 'tmp/uploads/f.pdf'"
    assert normalize_legacy_paths_in_code(code) == code


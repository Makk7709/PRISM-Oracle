"""Durcissement S-4 (audit qualité 2026-06) — vérification des clés d'hôte SSH.

Le shell SSH de l'agent ne se connecte qu'à son propre sandbox de code-exec
(loopback : localhost / host.docker.internal). Sur loopback, l'auto-trust de la
clé d'hôte n'expose à aucun MITM. Pour tout hôte NON-loopback, on doit charger
les known_hosts et REJETER une clé inconnue (paramiko.RejectPolicy), au lieu de
l'auto-ajouter aveuglément (AutoAddPolicy).
"""
import paramiko
import pytest

# Pré-import pour briser un cycle pré-existant (strings <-> files) déclenché si
# shell_ssh est le premier module helper importé à la collecte.
import python.helpers.files  # noqa: F401

from python.helpers.shell_ssh import (
    _is_loopback_host,
    _configure_host_key_verification,
)


@pytest.mark.parametrize(
    "host", ["localhost", "127.0.0.1", "::1", "host.docker.internal", "LOCALHOST", " localhost "]
)
def test_loopback_detected(host):
    assert _is_loopback_host(host) is True


@pytest.mark.parametrize("host", ["10.0.0.5", "example.com", "192.168.1.10", "", None])
def test_non_loopback_detected(host):
    assert _is_loopback_host(host) is False


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "host.docker.internal"])
def test_loopback_uses_autoadd_policy(host):
    client = paramiko.SSHClient()
    _configure_host_key_verification(client, host)
    assert isinstance(client._policy, paramiko.AutoAddPolicy)


@pytest.mark.parametrize("host", ["10.0.0.5", "example.com", "192.168.1.10"])
def test_remote_uses_reject_policy(host):
    client = paramiko.SSHClient()
    _configure_host_key_verification(client, host)
    assert isinstance(client._policy, paramiko.RejectPolicy)


def test_optin_env_forces_autoadd_on_remote(monkeypatch):
    monkeypatch.setenv("KOREV_SSH_TRUST_UNKNOWN_HOSTS", "1")
    client = paramiko.SSHClient()
    _configure_host_key_verification(client, "10.0.0.5")
    assert isinstance(client._policy, paramiko.AutoAddPolicy)


def test_optin_env_off_keeps_reject_on_remote(monkeypatch):
    monkeypatch.delenv("KOREV_SSH_TRUST_UNKNOWN_HOSTS", raising=False)
    client = paramiko.SSHClient()
    _configure_host_key_verification(client, "10.0.0.5")
    assert isinstance(client._policy, paramiko.RejectPolicy)

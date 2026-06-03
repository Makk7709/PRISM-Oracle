"""Régression de l'incident prod « bloqué sur user message » (2026-06-03).

Cause racine : l'init/connexion d'un serveur MCP local (stdio) spawn un
sous-processus SANS timeout dur. Sous pression de file descriptors, le spawn
pend indéfiniment alors que `MCPConfig.__lock` est tenu → tout `get_tools_prompt()`
(construction du prompt à CHAQUE message) bloque sur ce verrou → aucun appel LLM
n'est émis → l'agent reste figé sur le message utilisateur.

Doctrine : l'établissement d'une session MCP doit être borné par un timeout dur
qui couvre AUSSI le spawn du transport, puis échouer en fail-open (le serveur est
marqué en erreur, l'agent répond sans cet outil). Le verrou est toujours relâché.
"""

import asyncio
import time
from contextlib import AsyncExitStack
from types import SimpleNamespace

import pytest

from python.helpers.mcp_handler import MCPClientBase


class _HangingStdioClient(MCPClientBase):
    """Client MCP dont le spawn du transport pend (simule l'épuisement de FD)."""

    async def _create_stdio_transport(self, current_exit_stack: AsyncExitStack):
        # Jamais atteint dans le temps du test : simule un spawn qui ne rend pas la main.
        await asyncio.sleep(30)
        raise AssertionError("unreachable: le spawn aurait dû être interrompu par le timeout")


def _make_client() -> _HangingStdioClient:
    # MCPClientBase.__init__ ne connecte pas ; il a juste besoin d'un server avec un nom.
    fake_server = SimpleNamespace(name="hanging_server", init_timeout=0, tool_timeout=0)
    return _HangingStdioClient(fake_server)


async def test_execute_with_session_is_bounded_when_spawn_hangs():
    """Un spawn qui pend doit être interrompu par un timeout dur, pas bloquer pour toujours."""
    client = _make_client()

    async def op(_session):  # pragma: no cover - jamais atteint
        return "ok"

    read_timeout = 1  # le timeout dur = read_timeout + buffer interne (< 11s)
    start = time.monotonic()
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        # Garde-fou à 20s : en RED (aucun timeout interne) c'est CETTE garde qui
        # finit par sauter (~20s) -> l'assertion d'elapsed ci-dessous échoue.
        # En GREEN le timeout interne saute bien avant (~read_timeout + buffer).
        await asyncio.wait_for(
            client._execute_with_session(op, read_timeout_seconds=read_timeout),
            timeout=20,
        )
    elapsed = time.monotonic() - start

    # Doit échouer VITE via le timeout interne, et non pendre jusqu'à la garde de 20s.
    assert elapsed < 11, (
        f"_execute_with_session n'est pas borné : a mis {elapsed:.1f}s "
        f"(le spawn MCP peut donc bloquer la boucle de message)"
    )


async def test_update_tools_fails_open_on_hanging_spawn(monkeypatch):
    """update_tools() doit retourner (fail-open) et marquer l'erreur, sans pendre."""
    # Évite la lecture des settings réels : timeout d'init court et déterministe.
    from python.helpers import settings as settings_mod

    monkeypatch.setattr(
        settings_mod,
        "get_settings",
        lambda: {"mcp_client_init_timeout": 1, "mcp_client_tool_timeout": 5},
    )

    client = _make_client()

    start = time.monotonic()
    result = await asyncio.wait_for(client.update_tools(), timeout=20)
    elapsed = time.monotonic() - start

    assert elapsed < 11, f"update_tools a pendu {elapsed:.1f}s au lieu de fail-open"
    assert result is client
    assert client.get_tools() == [], "les outils doivent être vides en cas d'échec d'init"
    assert client.error, "une erreur doit être enregistrée (fail-open tracé)"

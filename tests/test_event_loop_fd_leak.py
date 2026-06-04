"""Régression de la fuite de file descriptors (incident prod 2026-06-03, cause profonde).

Diagnostic terrain : après ~18h, le backend détenait 95 epoll + ~203 sockets pour
seulement 46 threads -> ~49 boucles asyncio abandonnées. Chaque boucle non fermée
fuit 1 epoll (anon_inode) + 2 socketpair (self-pipe) = ~3 FD.

Cause : `EventLoopThread.terminate()` faisait `self.loop = None` SANS `loop.close()`.
Les boucles encore référencées (callbacks/tâches en attente) ne sont pas récupérées
par le GC -> leurs FD fuient définitivement, jusqu'à saturer le plafond et bloquer
le spawn des serveurs MCP (voir tests/test_mcp_init_timeout.py).

Doctrine : toute boucle créée par EventLoopThread DOIT être fermée (`loop.close()`)
au terme de son thread, ce qui libère déterministiquement epoll + socketpair.
"""

import asyncio
import gc
import os
import time

import pytest

from python.helpers.defer import EventLoopThread


def _proc_fd_supported() -> bool:
    return os.path.isdir("/proc/self/fd")


def _fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


async def _noop():
    return 42


def _wait_closed(loop, timeout=5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if loop.is_closed():
            return True
        time.sleep(0.02)
    return loop.is_closed()


def test_terminate_closes_the_loop():
    """terminate() doit fermer la boucle (sinon epoll + socketpair fuient)."""
    elt = EventLoopThread("fdtest-close")
    loop = elt.loop  # on garde la référence : empêche le GC de masquer la fuite
    assert elt.run_coroutine(_noop()).result(timeout=5) == 42

    thread = elt.thread
    elt.terminate()
    if thread:
        thread.join(timeout=5)

    assert _wait_closed(loop), (
        "la boucle n'est pas fermée après terminate() : "
        "ses FD (epoll + socketpair) fuient"
    )


def test_restart_does_not_keep_old_loop_open():
    """Après recréation, l'ancienne boucle doit être fermée, pas accumulée."""
    elt = EventLoopThread("fdtest-restart")
    old_loop = elt.loop
    elt.run_coroutine(_noop()).result(timeout=5)

    old_thread = elt.thread
    elt.terminate()
    if old_thread:
        old_thread.join(timeout=5)

    # recrée une nouvelle boucle/thread via run_coroutine -> _start
    elt.run_coroutine(_noop()).result(timeout=5)
    new_loop = elt.loop

    assert new_loop is not old_loop, "une nouvelle boucle doit être créée après terminate"
    assert _wait_closed(old_loop), "l'ancienne boucle doit être fermée (pas de fuite)"
    assert not new_loop.is_closed(), "la nouvelle boucle doit être opérationnelle"

    # nettoyage
    t = elt.thread
    elt.terminate()
    if t:
        t.join(timeout=5)


@pytest.mark.skipif(not _proc_fd_supported(), reason="requires /proc (Linux)")
def test_no_fd_leak_across_terminate_cycles():
    """Test exigeant : 15 cycles create->terminate ne doivent pas faire croître les FD.

    On conserve une référence vers chaque boucle (fidèle à la prod où des callbacks
    retiennent la boucle) pour que la fuite ne soit pas masquée par le GC.
    En RED : ~3 FD/boucle -> +~45. En GREEN : stable (close libère les FD).
    """
    held_loops = []
    gc.collect()
    base = _fd_count()

    for _ in range(15):
        elt = EventLoopThread("fdtest-cycle")
        held_loops.append(elt.loop)
        elt.run_coroutine(_noop()).result(timeout=5)
        thread = elt.thread
        elt.terminate()
        if thread:
            thread.join(timeout=5)

    gc.collect()
    after = _fd_count()

    assert len(held_loops) == 15  # garde les refs vivantes jusqu'ici
    assert (after - base) < 8, (
        f"fuite de FD : +{after - base} descripteurs sur 15 cycles "
        f"(base={base}, after={after}) — les boucles ne sont pas fermées"
    )

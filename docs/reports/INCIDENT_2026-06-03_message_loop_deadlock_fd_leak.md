# Incident 2026-06-03 — « bloqué sur user message » : deadlock boucle de message + fuite de file descriptors

**Statut :** résolu (mitigation immédiate + 2 correctifs durables, dont la cause racine)
**Sévérité :** P1 — indisponibilité serveur Evidence côté clients
**Environnement :** prod OVH (`evidence-backend`, Python 3.11.15, Docker)

---

## 1. Symptômes

- Les utilisateurs signalent que la version serveur d'Evidence **reste bloquée sur « user message »** : la requête est acceptée mais aucune réponse n'arrive.
- Aucun appel LLM émis, aucun log d'inférence.
- Le service répond au healthcheck mais ne traite plus les messages.

## 2. Diagnostic terrain

Accès SSH au conteneur live (`/proc/1/fd`, `/proc/1/task`) :

| Métrique | Valeur après ~18h | Interprétation |
|---|---:|---|
| FD totaux (pid 1) | 317 (vs ~82 au boot) | **+235 FD en 18h** |
| `socket:` | 203 | dont ~190 = socketpair self-pipe de boucles asyncio |
| `anon_inode:[eventpoll]` | 95 | **95 descripteurs epoll = ~95 boucles asyncio** |
| `pipe:` | 2 | normal |
| `/tmp/tmpXXX (deleted)` | ~10 | tempfiles MCP (`_create_stdio_transport`) — fuite secondaire mineure |
| Threads (`/proc/1/task`) | 46 | **< 95 epoll → ~49 boucles abandonnées sans thread vivant** |

**Signature :** 95 epoll + ~203 sockets pour seulement 46 threads. Chaque boucle
asyncio Linux possède **1 epoll (anon_inode) + 2 socketpair (self-pipe)** = ~3 FD.
Le nombre de boucles dépasse largement le nombre de threads → des boucles sont
**créées puis abandonnées sans être fermées**, leurs FD ne sont jamais libérés.

## 3. Cause racine

`python/helpers/defer.py :: EventLoopThread.terminate()` faisait :

```python
def terminate(self):
    if self.loop and self.loop.is_running():
        self.loop.stop()      # appelé depuis le MAUVAIS thread -> inopérant
    self.loop = None          # référence larguée SANS loop.close()
    self.thread = None
```

Deux défauts cumulés :

1. `loop.stop()` appelé depuis un autre thread que celui de la boucle ⇒ `run_forever()`
   ne rend pas toujours la main (vérifié en test : `running=True closed=False` après
   `terminate()`).
2. **Aucun `loop.close()`** ⇒ epoll + socketpair jamais libérés. Les boucles encore
   référencées par des callbacks/tâches en attente échappent au GC ⇒ **fuite définitive
   de ~3 FD par boucle terminée/remplacée**.

**Chemin déclencheur :** `kill(terminate_thread=True)` (utilisé par `browser_agent`,
boucle dédiée `"BrowserAgent"+context.id`) et `restart()`.

**Effet domino → deadlock :** une fois les FD saturés, le spawn `stdio_client` d'un
serveur MCP (qui ouvre pipes + sous-processus) **pend indéfiniment**, alors que le
verrou global `MCPConfig.__lock` est tenu. Or `get_tools_prompt()` (construit le prompt
à **chaque** message) prend ce même verrou ⇒ **toute la boucle de message se fige** ⇒
« bloqué sur user message ».

## 4. Mitigation immédiate

Reboot du serveur depuis le mode rescue → remise à zéro du compteur de FD → spawns MCP
de nouveau fonctionnels → service rétabli. (Stopgap, ne corrige pas la cause.)

## 5. Correctifs durables

### 5.1 Borne dure sur l'init MCP (fail-open) — commit `9d9caf29`

`_execute_with_session` enveloppé dans `asyncio.wait_for(..., timeout=hard_timeout)`.
Le spawn/init MCP ne peut plus pendre indéfiniment : au-delà de la borne, on échoue en
**fail-open** (serveur marqué en erreur, l'agent répond sans cet outil, verrou relâché).
Test : `tests/test_mcp_init_timeout.py`. → **traite le symptôme (deadlock)**.

### 5.2 Fermeture déterministe des boucles asyncio — *ce commit* — **CAUSE RACINE**

`python/helpers/defer.py` :

- `_run_event_loop()` : `run_forever()` dans un `try/finally` qui **annule les tâches en
  attente, draine, puis `loop.close()`** au terme du thread ⇒ libération déterministe de
  l'epoll + des socketpair.
- `terminate()` : `loop.stop()` désormais **planifié sur le thread de la boucle**
  (`call_soon_threadsafe`) + `thread.join(timeout=5)` ⇒ garantit que le `close()` a bien
  eu lieu. Garde anti-deadlock si appelé depuis le thread de la boucle.
- `DeferredTask.kill(terminate_thread=True)` : `cleanup()` interne (fragile,
  `run_until_complete` sur boucle en cours) supprimé au profit de `terminate()`.

`python/tools/browser_agent.py` : `loop.close()` déplacé dans un `finally` (fuite
secondaire si `browser_session.close()` levait).

Tests : `tests/test_event_loop_fd_leak.py`

- `test_terminate_closes_the_loop` (déterministe, portable) — RED avant / GREEN après.
- `test_restart_does_not_keep_old_loop_open` — l'ancienne boucle est fermée, pas accumulée.
- `test_no_fd_leak_across_terminate_cycles` (Linux/`proc`) — 15 cycles, croissance FD < 8.

### 5.3 Preuve empirique sur Linux de prod

Script de repro exécuté **dans le conteneur prod** (ancien `terminate` vs nouveau,
20 cycles create→terminate, références de boucles conservées) :

```text
ANCIEN (sans close):  delta = +60 FD  (= exactement 3 FD / boucle)
NOUVEAU (avec close): delta = +0  FD
```

+60/20 = **3 FD par boucle**, soit exactement 1 epoll + 2 socketpair : cohérent au FD près
avec la signature terrain (95 epoll + ~203 sockets).

## 6. Audit hostile (Phase 2)

| DEF | Sévérité | Description | Décision |
|---|:---:|---|---|
| DEF-1 | Modéré | `terminate()` peut bloquer l'appelant jusqu'à 5 s (`thread.join`) | Accepté : `kill_task` browser est rare et hors chemin de réponse user |
| DEF-2 | Modéré | Une tâche pathologique ignorant `cancel()` pourrait faire pendre le drain `run_until_complete` ; bornée par `join(timeout=5)` (le FD reste alors détenu par un thread zombie) | Résiduel documenté ; non observé |
| DEF-3 | Mineur | Si `terminate()` ferme une boucle **partagée** (`thread_name` commun), les tâches co-locataires sont annulées | **Théorique** : seul appelant réel = `browser_agent` (boucle unique par contexte) ; `restart()` n'a aucun appelant. Vérifié par grep. |
| DEF-4 | Mineur | Tempfiles MCP `(deleted)` (~10) non fermés — fuite distincte et lente | Hors périmètre de ce correctif ; faible débit |

**Re-audit total :** la correction n'introduit pas de défaut Critique/Important. Les
seuls appelants de `terminate_thread=True` (browser, boucle dédiée) et l'absence
d'appelant de `restart()` ont été vérifiés par recherche sur tout le dépôt → **0 défaut
résiduel Critique/Important**.

## 7. Risques résiduels & dette restante

- **P1 — autres sources de sockets** : la signature terrain est expliquée à ~100 % par les
  boucles fuitées, mais une fuite réseau secondaire (aiohttp/httpx non fermés) n'est pas
  formellement exclue. À surveiller via observabilité FD.
- **P2 — périmètre du verrou `MCPConfig.__lock`** : ne pas le tenir pendant le spawn/les
  appels d'outils (défense en profondeur contre tout futur blocage).
- **Filet recommandé (non implémenté ici)** : watchdog FD en lecture seule — log structuré
  - alerte quand `len(/proc/self/fd)` franchit un seuil, pour détecter toute régression tôt
  (sans auto-kill, pour éviter d'induire une coupure).

## 8. Validation post-déploiement attendue

Après déploiement, contrôler sur le conteneur live, à plusieurs heures d'intervalle :

```bash
ls /proc/1/fd | wc -l
ls -l /proc/1/fd | grep -c 'anon_inode:\[eventpoll\]'
```

Le compteur epoll doit **se stabiliser** (≈ nombre de threads vivants) et ne plus croître
de façon monotone.

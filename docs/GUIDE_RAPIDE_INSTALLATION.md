# Guide Rapide d'Installation

## KOREV Evidence - Version condensée (1 page)

---

## METHODE RECOMMANDEE : DOCKER (One-Click)

### Prérequis

- Windows 10/11 (64-bit) ou macOS 11+
- 8 Go RAM minimum
- **Docker Desktop** installé : <https://docker.com/products/docker-desktop/>

### Installation en 3 étapes

```text
1. DOCKER DESKTOP
   → Installer Docker Desktop depuis docker.com
   → Lancer Docker Desktop (attendre icône baleine verte)

2. CONFIGURATION
   → Copier .env.example vers .env
   → Ouvrir .env et ajouter votre clé API :
     API_KEY_OPENROUTER=votre-cle-ici

3. LANCEMENT
   → Windows : double-cliquer sur scripts/deploy-docker.bat
   → Mac/Linux : ./scripts/deploy-docker.sh
   → Evidence s'ouvre sur http://localhost:50080
```

### Commandes utiles (Docker)

| Action | Commande |
|--------|----------|
| Démarrer | `docker start korev-evidence` |
| Arrêter | `docker stop korev-evidence` |
| Voir les logs | `docker logs -f korev-evidence` |
| Supprimer | `docker compose -f docker/run/docker-compose.yml down` |

---

## METHODE ALTERNATIVE : INSTALLATION LOCALE

### Prérequis

- **Python 3.11+** : <https://python.org/downloads>
- Windows : cocher "Add Python to PATH" lors de l'installation

### Installation en 3 étapes

```text
1. PYTHON
   → Télécharger depuis python.org/downloads
   → Installer en cochant "Add Python to PATH"

2. CONFIGURATION
   → Copier .env.example vers .env
   → Ajouter votre clé API :
     API_KEY_OPENROUTER=votre-cle-ici

3. LANCEMENT
   → Windows : double-cliquer sur scripts/install-windows.bat
   → Mac/Linux : ./scripts/install-mac.sh
   → Evidence s'ouvre sur http://localhost:5050
```

### Relancement (local)

| Windows | Mac/Linux |
|---------|-----------|
| `venv\Scripts\activate` | `source venv/bin/activate` |
| `python run_ui.py` | `python run_ui.py` |

---

## Clés API

| Provider | URL | Variable .env |
|----------|-----|---------------|
| **OpenRouter** (recommandé) | openrouter.ai | `API_KEY_OPENROUTER=...` |
| OpenAI (optionnel, images) | platform.openai.com | Se configure dans l'interface |

---

## Accès

| Mode | URL |
|------|-----|
| Docker | **<http://localhost:50080>** |
| Local | **<http://localhost:5050>** |

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Docker Desktop non lancé | Lancer Docker Desktop, attendre icône verte |
| Port 50080 occupé | `EVIDENCE_PORT=50081 ./scripts/deploy-docker.sh` |
| "Python non reconnu" (local) | Réinstaller Python avec "Add to PATH" coché |
| "Module not found" (local) | `pip install -r requirements.txt` |
| Port 5050 occupé (local) | Changer `WEB_UI_PORT=5051` dans `.env` |
| Page ne charge pas | Attendre 30s, essayer <http://127.0.0.1:50080> |

---

## Support

- **Email** : <support@korev.ai>
- **Documentation complète** : voir `MANUEL_INSTALLATION_CLIENT.md`

---

*KOREV Evidence - Guide rapide v3.0*

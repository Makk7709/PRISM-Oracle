# Guide d'Installation - KOREV Evidence

## Methode Recommandee : Docker (One-Click)

### Prerequis

1. **Docker Desktop** - [Telecharger ici](https://www.docker.com/products/docker-desktop/)
   - Windows, macOS ou Linux
   - Lancez Docker Desktop apres installation

### Installation One-Click

#### Sur macOS / Linux

```bash
cd korev-evidence/scripts
chmod +x deploy-docker.sh
./deploy-docker.sh
```

#### Sur Windows

```text
1. Ouvrez le dossier "scripts"
2. Double-cliquez sur "deploy-docker.bat"
3. Suivez les instructions a l'ecran
4. Evidence s'ouvre automatiquement sur http://localhost:50080
```

Le script `deploy-docker` fait tout automatiquement :

- Verifie Docker Desktop
- Configure le fichier `.env`
- Construit l'image KOREV Evidence (~10-20 min la premiere fois)
- Demarre le container
- Ouvre le navigateur

### Commandes utiles

| Action | Commande |
|--------|----------|
| Voir les logs | `docker logs -f korev-evidence` |
| Arreter Evidence | `docker stop korev-evidence` |
| Redemarrer Evidence | `docker start korev-evidence` |
| Supprimer completement | `docker compose -f docker/run/docker-compose.yml down` |
| Reconstruire l'image | `docker build -f DockerfileLocal -t korev-evidence:local .` |

---

## Installation Manuelle (Docker)

Si vous preferez les commandes manuelles :

```bash
# 1. Construire l'image
cd korev-evidence
docker build -f DockerfileLocal -t korev-evidence:local .

# 2. Configurer .env (copier et editer)
cp .env.example .env
# Editez .env et ajoutez votre cle API_KEY_OPENROUTER

# 3. Demarrer
cd docker/run
docker compose up -d

# 4. Acceder
open http://localhost:50080
```

---

## Methode Alternative : Installation Locale (sans Docker)

### Prerequis

#### Windows

1. **Python 3.11+** - [Telecharger ici](https://www.python.org/downloads/)
   - IMPORTANT : Cochez "Add Python to PATH" lors de l'installation

#### macOS

1. **Python 3.11+** - Deja installe ou via Homebrew :

   ```bash
   brew install python@3.11
   ```

#### Linux

1. **Python 3.11+**

   ```bash
   sudo apt install python3.11 python3.11-venv
   ```

### Installation Rapide (locale)

#### Sur Windows

```text
1. Ouvrez le dossier "scripts"
2. Double-cliquez sur "install-windows.bat"
3. Attendez l'installation des dependances
4. Evidence s'ouvre automatiquement sur http://localhost:5050
```

#### Sur macOS / Linux

```bash
cd korev-evidence/scripts
chmod +x install-mac.sh
./install-mac.sh
```

---

## Configuration

### Fichier .env

Le fichier `.env` a la racine contient la configuration. Ajoutez au moins une cle API :

```env
# Cle API (requise) — https://openrouter.ai/keys
API_KEY_OPENROUTER=sk-or-votre-cle

# Configuration
WEB_UI_PORT=5050
DEFAULT_USER_TIMEZONE=Europe/Paris
```

---

## Mise a jour

### Docker

```bash
cd korev-evidence
docker compose -f docker/run/docker-compose.yml down
docker build -f DockerfileLocal -t korev-evidence:local .
cd docker/run && docker compose up -d
```

### Installation locale

#### Windows

```text
Double-cliquez sur scripts/update-windows.bat
```

#### macOS / Linux

```bash
cd korev-evidence
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
pip install -r requirements2.txt --upgrade
```

---

## Lancement manuel

### Docker

```bash
docker start korev-evidence
# Acces sur http://localhost:50080
```

### Installation locale

#### Windows

```cmd
cd korev-evidence
venv\Scripts\activate
python run_ui.py
```

#### macOS / Linux

```bash
cd korev-evidence
source venv/bin/activate
python run_ui.py
```

---

## Acces

| Mode | URL |
|------|-----|
| Docker | **<http://localhost:50080>** |
| Local | **<http://localhost:5050>** |

---

## Desinstallation

### Docker

```bash
docker compose -f docker/run/docker-compose.yml down
docker rmi korev-evidence:local
```

### Installation locale (Windows)

```text
Double-cliquez sur scripts/uninstall-windows.bat
```

Ce script supprime :

- `venv/` (environnement virtuel, ~2-5 GB)
- `__pycache__/`, `.pytest_cache/`, `*.pyc`
- `logs/`, `tmp/`

Ce script **NE supprime PAS** :

- `.env` (votre configuration)
- `data/` (vos donnees)
- Le code source

---

## Depannage

### Docker Desktop ne demarre pas

- Windows : Verifiez que la virtualisation est activee dans le BIOS
- macOS : Allez dans Docker Desktop > Settings > Advanced > "Allow the default Docker socket"

### "Port 50080 deja utilise"

```bash
EVIDENCE_PORT=50081 ./scripts/deploy-docker.sh
```

### "Python n'est pas reconnu" (mode local)

- Windows : Reinstallez Python en cochant "Add Python to PATH"
- Mac : `brew install python@3.11`

### "Module not found" (mode local)

```bash
pip install -r requirements.txt
pip install -r requirements2.txt
```

---

## Support

- **Email** : <support@korev.ai>

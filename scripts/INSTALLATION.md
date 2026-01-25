# Guide d'Installation - Korev Oracle

## Prérequis

### Windows
1. **Docker Desktop** - [Télécharger ici](https://www.docker.com/products/docker-desktop/)
   - Lors de l'installation, cochez "Use WSL 2 instead of Hyper-V"
   - Redémarrez le PC après l'installation
2. **WSL2** (recommandé) - S'installe automatiquement avec Docker Desktop

### macOS
1. **Docker Desktop** - [Télécharger ici](https://www.docker.com/products/docker-desktop/)
   - Ou alternatives: Colima, Podman

### Linux
1. **Docker Engine** + **docker-compose**
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

---

## Installation Rapide

### Sur Windows

**Option 1 : Double-clic (simple)**
```
1. Ouvrez le dossier "scripts"
2. Double-cliquez sur "install-windows.bat"
3. Suivez les instructions
```

**Option 2 : PowerShell (avancé)**
```powershell
# Ouvrir PowerShell en Administrateur
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd chemin\vers\agent-zero\scripts
.\install-windows.ps1
```

### Sur macOS

```bash
cd /chemin/vers/agent-zero/scripts
chmod +x install-mac.sh
./install-mac.sh
```

### Sur Linux

```bash
cd /chemin/vers/agent-zero/scripts
chmod +x install-mac.sh
./install-mac.sh  # Même script
```

---

## Configuration

### Fichier .env

Avant de lancer Oracle, créez un fichier `.env` à la racine du projet :

```env
# Clés API (au moins une obligatoire)
API_KEY_OPENAI=sk-votre-cle-openai
API_KEY_OPENROUTER=sk-votre-cle-openrouter

# Configuration
WEB_UI_PORT=5050
DEFAULT_USER_TIMEZONE=Europe/Paris
ANONYMIZED_TELEMETRY=false
```

### Clés API supportées

| Provider | Variable | Où l'obtenir |
|----------|----------|--------------|
| OpenAI | `API_KEY_OPENAI` | https://platform.openai.com/api-keys |
| OpenRouter | `API_KEY_OPENROUTER` | https://openrouter.ai/keys |
| Anthropic | `API_KEY_ANTHROPIC` | https://console.anthropic.com/ |
| Google | `API_KEY_GOOGLE` | https://aistudio.google.com/apikey |
| Mistral | `API_KEY_MISTRAL` | https://console.mistral.ai/ |

---

## Accès à Oracle

Après installation, Oracle est accessible sur :

| Mode | URL |
|------|-----|
| Docker | http://localhost:50080 |
| Dev local | http://localhost:5050 |

---

## Commandes Utiles

### Gestion du conteneur Docker

```bash
# Voir les logs
docker logs -f korev-oracle

# Arrêter Oracle
docker stop korev-oracle

# Démarrer Oracle
docker start korev-oracle

# Redémarrer Oracle
docker restart korev-oracle

# Supprimer le conteneur (pour réinstallation)
docker rm -f korev-oracle
```

### Mise à jour

```bash
cd agent-zero/docker/run
docker compose down
docker pull korevai/korev-oracle:latest
docker compose up -d
```

---

## Dépannage

### "Docker n'est pas lancé"
- Ouvrez Docker Desktop
- Attendez que l'icône devienne verte (prêt)
- Relancez le script

### "Port 50080 déjà utilisé"
```bash
# Trouver le processus
# Windows:
netstat -ano | findstr :50080
# Mac/Linux:
lsof -i :50080

# Changer le port dans docker-compose.yml
ports:
  - "50081:80"  # Utiliser 50081 au lieu de 50080
```

### "Pas de clé API"
1. Créez un compte sur OpenAI ou OpenRouter
2. Générez une clé API
3. Ajoutez-la dans le fichier `.env`

### "Image Docker introuvable"
```bash
# Télécharger manuellement
docker pull korevai/korev-oracle-base:latest
```

---

## Structure des fichiers

```
agent-zero/
├── .env                    # Configuration (clés API)
├── docker/
│   └── run/
│       └── docker-compose.yml
├── scripts/
│   ├── install-mac.sh      # Installation Mac/Linux
│   ├── install-windows.ps1 # Installation Windows (PowerShell)
│   ├── install-windows.bat # Installation Windows (simple)
│   └── INSTALLATION.md     # Ce fichier
└── ...
```

---

## Support

En cas de problème :
1. Vérifiez les logs : `docker logs korev-oracle`
2. Consultez la documentation
3. Contactez l'équipe Korev

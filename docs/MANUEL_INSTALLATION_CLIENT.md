# Manuel d'Installation KOREV Evidence

## Guide Client — Version 4.1

---

# Table des matières

1. [Introduction](#1-introduction)
2. [Prérequis système](#2-prérequis-système)
3. [Méthode Recommandée : Docker (Production)](#3-méthode-recommandée--docker-production)
4. [Méthode Alternative : Installation locale](#4-méthode-alternative--installation-locale)
5. [Configuration initiale](#5-configuration-initiale)
6. [Premier lancement](#6-premier-lancement)
7. [Utilisation quotidienne](#7-utilisation-quotidienne)
8. [Mise à jour](#8-mise-à-jour)
9. [Dépannage](#9-dépannage)
10. [Support technique](#10-support-technique)

---

# 1. Introduction

## Qu'est-ce que KOREV Evidence ?

KOREV Evidence est un assistant IA avancé conçu pour vous aider dans vos tâches quotidiennes. Il peut :
- Rechercher des informations scientifiques et académiques
- Analyser des documents PDF
- Générer et assembler des rapports PDF
- Générer des images (publicités, infographies, storyboards)
- Automatiser des tâches complexes via des agents spécialisés

## Deux méthodes d'installation

| Méthode | Recommandée | Temps estimé | Difficulté |
|---------|:-----------:|:------------:|:----------:|
| **Docker** (Production) | Oui | 15-30 min | Facile |
| **Locale** (Développement) | Alternative | 20-30 min | Intermédiaire |

> **Nous recommandons Docker** : installation plus simple, plus fiable, et identique sur tous les systèmes. Inclut HTTPS, reverse proxy et sécurité production.

---

# 2. Prérequis système

## Configuration minimale

| Composant | Serveur (recommandé) | Poste local |
|-----------|----------------------|-------------|
| **Système** | Ubuntu 22.04+ / Debian 12+ | Windows 10+, macOS 12+ |
| **CPU** | 4 vCPU minimum | 4 cœurs |
| **RAM** | 16 Go (8 Go minimum) | 8 Go minimum |
| **Stockage** | 50 Go SSD | 20 Go disponibles |
| **Connexion** | Internet haut débit | Internet haut débit |

## Logiciels requis

| Méthode | Logiciel |
|---------|----------|
| **Docker** | Docker Engine 24+ et Docker Compose v2 |
| **Locale** | Python 3.11+, Node.js 20+, Tesseract OCR, WeasyPrint (voir section 4) |

---

# 3. Méthode Recommandée : Docker (Production)

## Architecture

```
Internet / LAN
      │
  [ Caddy ]  ← Reverse proxy (HTTPS, headers sécurité)
      │
  [ Flask ]  ← Backend Python + WebUI
      │
  [ Samba ]  ← Partage de fichiers Windows (optionnel)
```

Tous les services tournent dans des conteneurs Docker isolés, orchestrés par Docker Compose.

---

## Étape 1 : Installer Docker

### Sur Ubuntu / Debian (serveur)

```bash
# Installer Docker Engine
curl -fsSL https://get.docker.com | sudo sh

# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Déconnecter/reconnecter pour appliquer le groupe
exit
# puis se reconnecter

# Vérifier l'installation
docker --version
docker compose version
```

### Sur Windows / Mac (poste local)

1. Téléchargez Docker Desktop : **https://www.docker.com/products/docker-desktop/**
2. Installez et lancez Docker Desktop
3. **Important** : dans Settings > Resources, allouez au minimum **8 Go de RAM**

### Ouvrir les ports (serveur uniquement)

```bash
# Si un pare-feu est actif (ufw, firewalld), ouvrir les ports HTTP/HTTPS :
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## Étape 2 : Récupérer les fichiers

### Option A : Depuis Git (recommandé)

```bash
git clone https://github.com/Makk7709/PRISM-Oracle.git
cd PRISM-Oracle
```

### Option B : Depuis une archive

Décompressez l'archive fournie :
```bash
tar xzf korev-evidence-v1.0.0.tar.gz
cd korev-evidence
```

### Structure du dossier

```
PRISM-Oracle/                          ← Dossier racine du projet
├── deploy/
│   ├── Dockerfile.backend             ← Image Docker backend
│   ├── docker-compose.yml             ← Orchestration des services
│   ├── .env.example                   ← Template de configuration
│   ├── users.json.example             ← Template multi-utilisateurs
│   └── config/
│       └── Caddyfile                  ← Configuration reverse proxy
├── python/                            ← Code backend
├── webui/                             ← Interface web
├── tmp/                               ← Données runtime (chats, uploads, images)
├── requirements.txt                   ← Dépendances Python
├── run_ui.py                          ← Point d'entrée serveur
└── .env.example                       ← Template config (racine)
```

> **Note** : si vous utilisez l'archive, le dossier s'appelle `korev-evidence/` au lieu de `PRISM-Oracle/`.

---

## Étape 3 : Configurer l'environnement

### 3.1 Créer le fichier .env

```bash
cd deploy
cp .env.example .env
```

### 3.2 Configurer les clés API (OBLIGATOIRE)

Ouvrez `.env` avec un éditeur de texte et remplissez **au minimum** :

```bash
# Clé API pour les modèles IA (au moins UNE obligatoire)
API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici

# Identifiants de connexion
AUTH_LOGIN=admin
AUTH_PASSWORD=VotreMotDePasseFort123!
```

> Voir la section [Configuration initiale](#5-configuration-initiale) pour obtenir une clé API.

### 3.3 Configurer HTTPS (recommandé en production)

Par défaut, Caddy écoute en HTTP sur le port 80. Pour activer HTTPS :

1. Associez un nom de domaine à l'IP de votre serveur (DNS A record)
2. Éditez `deploy/config/Caddyfile` — remplacez la première ligne :

```
# Avant (HTTP uniquement) :
:80 {

# Après (HTTPS automatique via Let's Encrypt) :
evidence.votre-domaine.fr {
```

3. Caddy obtient automatiquement un certificat Let's Encrypt au premier démarrage

> **Sans nom de domaine** : Caddy fonctionne en HTTP sur le port 80. L'application reste pleinement fonctionnelle, mais la connexion n'est pas chiffrée.

### 3.4 Configurer Samba (optionnel)

Si vous souhaitez que les utilisateurs accèdent aux fichiers depuis l'Explorateur Windows :

```bash
# Adapter les noms et mots de passe à vos utilisateurs
SMB_USER_1=marie;MotDePasse1!
SMB_USER_2=jean;MotDePasse2!
# ... etc.
SMB_USER_ADMIN=admin;AdminPass!
```

> Sans configuration Samba, l'application fonctionne normalement. Samba ajoute uniquement l'accès aux fichiers partagés via le réseau Windows (SMB).

---

## Étape 4 : Construire et lancer

Toutes les commandes ci-dessous s'exécutent depuis le dossier `deploy/`.

### Build de l'image

```bash
cd deploy
docker compose build evidence-backend
```

> La première construction prend 10-20 minutes (téléchargement des dépendances). Les constructions suivantes sont plus rapides grâce au cache.

### Lancement

**Sans Samba (recommandé pour un premier test) :**
```bash
docker compose up -d evidence-backend evidence-caddy
```

**Avec tous les services :**
```bash
docker compose up -d
```

### Vérifier le bon fonctionnement

```bash
# Vérifier que les conteneurs tournent
docker compose ps

# Vérifier le health check
curl http://localhost/healthz
# Réponse attendue : {"status":"ok"}

# Consulter les logs en temps réel
docker compose logs -f evidence-backend
```

### Résultat attendu

```
NAME                STATUS              PORTS
evidence-backend    Up (healthy)        5050/tcp
evidence-caddy      Up (healthy)        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

Accédez à l'interface : **http://VOTRE_IP** (ou **https://VOTRE_DOMAINE** si HTTPS configuré)

---

# 4. Méthode Alternative : Installation locale

> Cette méthode convient pour le développement ou un test rapide sur un poste local.

## Étape 1 : Installer les prérequis

### Python 3.11+

**Windows :**
1. Téléchargez sur **https://www.python.org/downloads/**
2. **IMPORTANT** : Cochez **"Add Python to PATH"**
3. Installez

**Mac :**
```bash
brew install python@3.11
```

**Ubuntu / Debian :**
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv
```

### Node.js 20+ (pour les MCP servers)

```bash
# Mac
brew install node@20

# Ubuntu / Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs
```

### Dépendances système (PDF, OCR, images)

**Ubuntu / Debian :**
```bash
sudo apt install -y \
    tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libcairo2 libffi-dev libglib2.0-0 \
    poppler-utils \
    fonts-liberation fonts-dejavu-core
```

**Mac :**
```bash
brew install tesseract pango cairo poppler
```

**Windows :**
- Installez Tesseract OCR depuis **https://github.com/UB-Mannheim/tesseract/wiki**
- Les dépendances WeasyPrint sont incluses via pip

> Sans ces dépendances, la génération de PDF et l'OCR ne fonctionneront pas.

## Étape 2 : Configurer et lancer

```bash
cd PRISM-Oracle

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Installer les dépendances Python
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Éditer .env avec vos clés API

# Lancer
python run_ui.py
```

Accédez à **http://localhost:5050**

---

# 5. Configuration initiale

## Obtenir les clés API

Evidence utilise **OpenRouter** comme fournisseur principal pour accéder à tous les modèles IA.

### Clé OpenRouter (REQUISE)

1. Allez sur **https://openrouter.ai/**
2. Créez un compte ou connectez-vous
3. Allez dans **Keys** (menu en haut)
4. Cliquez sur **"Create Key"**
5. Copiez la clé (commence par `sk-or-v1-...`)
6. Collez-la dans `.env` :
   ```
   API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici
   ```

### Clé OpenAI (OPTIONNEL)

Pour la génération d'images (GPT-Image, DALL-E) :
1. Allez sur **https://platform.openai.com/api-keys**
2. Créez une clé
3. Collez-la dans `.env` :
   ```
   API_KEY_OPENAI=sk-votre-cle-ici
   ```

---

# 6. Premier lancement

## Accéder à Evidence

1. Ouvrez votre navigateur web
2. Tapez l'adresse correspondant à votre installation :

| Méthode | URL |
|---------|-----|
| Docker (serveur) | **http://VOTRE_IP** ou **https://VOTRE_DOMAINE** |
| Docker (local) | **http://localhost** |
| Locale | **http://localhost:5050** |

3. Connectez-vous avec les identifiants configurés dans `.env` (`AUTH_LOGIN` / `AUTH_PASSWORD`)

## Écran d'accueil

Vous devriez voir l'interface **KOREV Evidence** avec :
- Le logo et le titre "KOREV Evidence"
- Un champ pour taper vos questions
- La barre latérale avec les conversations

## Premier test

Tapez une question :
```
Bonjour, peux-tu te présenter ?
```

Evidence devrait répondre en quelques secondes.

---

# 7. Utilisation quotidienne

## Démarrer Evidence

### Mode Docker

```bash
cd PRISM-Oracle/deploy
docker compose up -d
```

### Mode Local

```bash
cd PRISM-Oracle
source venv/bin/activate
python run_ui.py
```

## Arrêter Evidence

### Docker
```bash
cd PRISM-Oracle/deploy
docker compose down
```

### Local
- Appuyez sur **Ctrl + C** dans le terminal

---

# 8. Mise à jour

### Mode Docker

```bash
# Depuis la racine du projet (pas deploy/)
cd PRISM-Oracle
git pull

# Reconstruire et relancer
cd deploy
docker compose build evidence-backend
docker compose up -d
```

> Les données (conversations, fichiers uploadés, images générées, mémoire de l'agent) sont persistées dans des volumes Docker. La mise à jour ne supprime rien.

### Mode Local

```bash
cd PRISM-Oracle
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

# 9. Dépannage

## Problèmes Docker

### "Cannot connect to the Docker daemon"

**Solution :**
1. Lancez Docker Desktop (local) ou le service Docker (serveur) :
   ```bash
   sudo systemctl start docker
   ```
2. Vérifiez : `docker info`

### Le conteneur ne démarre pas

**Solution :**
```bash
# Consulter les logs
docker compose logs evidence-backend

# Erreurs courantes :
# - "ImportError" → image corrompue, reconstruire :
docker compose build --no-cache evidence-backend

# - "Address already in use" → port occupé :
docker compose down
docker compose up -d
```

### Build échoue avec "cannot allocate memory"

**Solution :**
- Serveur : vérifiez `free -h`, minimum 4 Go disponibles pendant le build
- Docker Desktop : Settings > Resources > augmenter la mémoire à 8 Go+

### L'interface ne charge pas

**Solution :**
1. Vérifiez les conteneurs : `docker compose ps`
2. Attendez 60 secondes (le backend a un `start_period` de 60s)
3. Testez le health check : `curl http://localhost/healthz`
4. Consultez les logs : `docker compose logs -f`

## Problèmes généraux

### "Erreur de clé API"

**Solution :**
1. Vérifiez la clé dans `.env` (pas d'espaces, pas de guillemets)
2. Vérifiez votre crédit sur le compte OpenRouter/OpenAI
3. Relancez après modification : `docker compose restart evidence-backend`

### Les images générées ne se téléchargent pas

**Solution :** Actualisez la page du navigateur (F5 / Cmd+R). Un correctif récent gère le protocole `sandbox://` utilisé par certains modèles.

### Mes données ont disparu après un redémarrage

Les données sont stockées dans des volumes Docker persistants. Vérifiez qu'ils existent :
```bash
docker volume ls | grep evidence
```

Volumes attendus : `evidence-data`, `evidence-logs`, `evidence-audit`, `evidence-shared`, `evidence-tmp`, `evidence-memory`.

> **Attention** : `docker compose down -v` supprime les volumes et donc **toutes** les données. N'utilisez jamais l'option `-v` sauf pour une réinitialisation complète.

---

# 10. Support technique

## Informations à fournir

En cas de problème :
1. Système d'exploitation et version
2. Méthode d'installation (Docker ou locale)
3. Sortie de `docker compose ps` et `docker compose logs --tail=50 evidence-backend`
4. Message d'erreur exact ou capture d'écran
5. Version : `cat deploy/.env | grep EVIDENCE_VERSION`

## Commandes de diagnostic

Toutes les commandes ci-dessous s'exécutent depuis le dossier `PRISM-Oracle/deploy/` :

```bash
# État des services
docker compose ps

# Logs du backend (dernières 100 lignes)
docker compose logs --tail=100 evidence-backend

# Utilisation des ressources
docker stats --no-stream

# Espace disque des volumes
docker system df -v

# Vérifier les volumes persistants
docker volume ls | grep evidence
```

## Contact

- **Email** : support@korev.ai

---

*Document mis à jour le 8 février 2026*
*Version : 4.1*
*KOREV Evidence — Guide d'installation client*

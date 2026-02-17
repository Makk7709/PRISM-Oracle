# Manuel d'Installation KOREV Evidence

## Guide Client - Version 4.0

---

# Table des matieres

1. [Introduction](#1-introduction)
2. [Prerequis systeme](#2-prerequis-systeme)
3. [Methode Recommandee : Docker (Production)](#3-methode-recommandee--docker-production)
4. [Methode Alternative : Installation locale](#4-methode-alternative--installation-locale)
5. [Configuration initiale](#5-configuration-initiale)
6. [Premier lancement](#6-premier-lancement)
7. [Utilisation quotidienne](#7-utilisation-quotidienne)
8. [Mise a jour](#8-mise-a-jour)
9. [Depannage](#9-depannage)
10. [Support technique](#10-support-technique)

---

# 1. Introduction

## Qu'est-ce que KOREV Evidence ?

KOREV Evidence est un assistant IA avance concu pour vous aider dans vos taches quotidiennes. Il peut :
- Rechercher des informations scientifiques et academiques
- Analyser des documents PDF
- Generer et assembler des rapports PDF
- Generer des images (publicites, infographies, storyboards)
- Automatiser des taches complexes via des agents specialises

## Deux methodes d'installation

| Methode | Recommandee | Temps estime | Difficulte |
|---------|:-----------:|:------------:|:----------:|
| **Docker** (Production) | Oui | 15-30 min | Facile |
| **Locale** (Developpement) | Alternative | 15-25 min | Intermediaire |

> **Nous recommandons Docker** : installation plus simple, plus fiable, et identique sur tous les systemes. Inclut HTTPS, reverse proxy et securite production.

---

# 2. Prerequis systeme

## Configuration minimale

| Composant | Serveur (recommande) | Poste local |
|-----------|----------------------|-------------|
| **Systeme** | Ubuntu 22.04+ / Debian 12+ | Windows 10+, macOS 12+ |
| **CPU** | 4 vCPU minimum | 4 coeurs |
| **RAM** | 16 Go (8 Go minimum) | 8 Go minimum |
| **Stockage** | 50 Go SSD | 20 Go disponibles |
| **Connexion** | Internet haut debit | Internet haut debit |

## Logiciels requis

| Methode | Logiciel |
|---------|----------|
| **Docker** | Docker Engine 24+ et Docker Compose v2 |
| **Locale** | Python 3.11+, Node.js 20+ |

---

# 3. Methode Recommandee : Docker (Production)

## Architecture

```
Internet / LAN
      |
  [ Caddy ]  ← Reverse proxy (HTTPS, headers securite)
      |
  [ Flask ]  ← Backend Python + WebUI
      |
  [ Samba ]  ← Partage de fichiers Windows (optionnel)
```

Tous les services tournent dans des conteneurs Docker isoles, orchestres par Docker Compose.

---

## Etape 1 : Installer Docker

### Sur Ubuntu / Debian (serveur)

```bash
# Installer Docker Engine
curl -fsSL https://get.docker.com | sudo sh

# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Deconnecter/reconnecter pour appliquer le groupe
exit
# puis se reconnecter

# Verifier l'installation
docker --version
docker compose version
```

### Sur Windows / Mac (poste local)

1. Telechargez Docker Desktop : **https://www.docker.com/products/docker-desktop/**
2. Installez et lancez Docker Desktop
3. **Important** : dans Settings > Resources, allouez au minimum **8 Go de RAM**

---

## Etape 2 : Recuperer les fichiers

### Option A : Depuis Git (recommande)

```bash
git clone https://github.com/Makk7709/PRISM-Oracle.git -b security-phase1-p0
cd PRISM-Oracle
```

### Option B : Depuis une archive

Decompressez l'archive fournie :
```bash
tar xzf korev-evidence-v1.0.0.tar.gz
cd korev-evidence
```

### Structure du dossier

```
korev-evidence/
├── deploy/
│   ├── Dockerfile.backend       ← Image Docker backend
│   ├── docker-compose.yml       ← Orchestration des services
│   ├── .env.example             ← Template de configuration
│   ├── users.json.example       ← Template multi-utilisateurs
│   └── config/
│       └── Caddyfile            ← Configuration reverse proxy
├── python/                      ← Code backend
├── webui/                       ← Interface web
├── requirements.txt             ← Dependances Python
├── run_ui.py                    ← Point d'entree serveur
└── .env.example                 ← Template config (racine)
```

---

## Etape 3 : Configurer l'environnement

### 3.1 Creer le fichier .env

```bash
cd deploy
cp .env.example .env
```

### 3.2 Configurer les cles API (OBLIGATOIRE)

Ouvrez `.env` avec un editeur de texte et remplissez **au minimum** :

```bash
# Cle API pour les modeles IA (au moins UNE obligatoire)
API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici

# Identifiants de connexion
AUTH_LOGIN=admin
AUTH_PASSWORD=VotreMotDePasseFort123!
```

> Voir la section [Configuration initiale](#5-configuration-initiale) pour obtenir une cle API.

### 3.3 Configurer Samba (optionnel)

Si vous souhaitez que les utilisateurs accedent aux fichiers depuis l'Explorateur Windows :

```bash
# Adapter les noms et mots de passe a vos utilisateurs
SMB_USER_1=marie;MotDePasse1!
SMB_USER_2=jean;MotDePasse2!
# ... etc.
SMB_USER_ADMIN=admin;AdminPass!
```

> Sans configuration Samba, l'application fonctionne normalement. Samba ajoute uniquement l'acces aux fichiers partages via le reseau Windows (SMB).

---

## Etape 4 : Construire et lancer

### Build de l'image

```bash
cd deploy
docker compose build evidence-backend
```

> La premiere construction prend 10-20 minutes (telechargement des dependances). Les constructions suivantes sont plus rapides grace au cache.

### Lancement

**Sans Samba (recommande pour un premier test) :**
```bash
docker compose up -d evidence-backend evidence-caddy
```

**Avec tous les services :**
```bash
docker compose up -d
```

### Verifier le bon fonctionnement

```bash
# Verifier que les conteneurs tournent
docker compose ps

# Verifier le health check
curl http://localhost/healthz
# Reponse attendue : {"status":"ok"}

# Consulter les logs en temps reel
docker compose logs -f evidence-backend
```

### Resultat attendu

```
NAME                STATUS              PORTS
evidence-backend    Up (healthy)        5050/tcp
evidence-caddy      Up (healthy)        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

Accedez a l'interface : **http://VOTRE_IP** (ou **https://VOTRE_DOMAINE** si DNS configure)

---

# 4. Methode Alternative : Installation locale

> Cette methode convient pour le developpement ou un test rapide sur un poste local.

## Etape 1 : Installer les prerequis

### Python 3.11+

**Windows :**
1. Telechargez sur **https://www.python.org/downloads/**
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

## Etape 2 : Configurer et lancer

```bash
cd korev-evidence

# Creer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Installer les dependances
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Editer .env avec vos cles API

# Lancer
python run_ui.py
```

Accedez a **http://localhost:5050**

---

# 5. Configuration initiale

## Obtenir les cles API

Evidence utilise **OpenRouter** comme fournisseur principal pour acceder a tous les modeles IA.

### Cle OpenRouter (REQUISE)

1. Allez sur **https://openrouter.ai/**
2. Creez un compte ou connectez-vous
3. Allez dans **Keys** (menu en haut)
4. Cliquez sur **"Create Key"**
5. Copiez la cle (commence par `sk-or-v1-...`)
6. Collez-la dans `.env` :
   ```
   API_KEY_OPENROUTER=sk-or-v1-votre-cle-ici
   ```

### Cle OpenAI (OPTIONNEL)

Pour la generation d'images (GPT-Image, DALL-E) :
1. Allez sur **https://platform.openai.com/api-keys**
2. Creez une cle
3. Collez-la dans `.env` :
   ```
   API_KEY_OPENAI=sk-votre-cle-ici
   ```

---

# 6. Premier lancement

## Acceder a Evidence

1. Ouvrez votre navigateur web
2. Tapez l'adresse correspondant a votre installation :

| Methode | URL |
|---------|-----|
| Docker (serveur) | **http://VOTRE_IP** ou **https://VOTRE_DOMAINE** |
| Docker (local) | **http://localhost** |
| Locale | **http://localhost:5050** |

3. Connectez-vous avec les identifiants configures dans `.env` (`AUTH_LOGIN` / `AUTH_PASSWORD`)

## Ecran d'accueil

Vous devriez voir l'interface **KOREV Evidence** avec :
- Le logo et le titre "KOREV Evidence"
- Un champ pour taper vos questions
- La barre laterale avec les conversations

## Premier test

Tapez une question :
```
Bonjour, peux-tu te presenter ?
```

Evidence devrait repondre en quelques secondes.

---

# 7. Utilisation quotidienne

## Demarrer Evidence

### Mode Docker

```bash
cd deploy
docker compose up -d
```

### Mode Local

```bash
cd korev-evidence
source venv/bin/activate
python run_ui.py
```

## Arreter Evidence

### Docker
```bash
cd deploy
docker compose down
```

### Local
- Appuyez sur **Ctrl + C** dans le terminal

---

# 8. Mise a jour

### Mode Docker

```bash
cd deploy

# Recuperer les derniers changements
git pull

# Reconstruire et relancer
docker compose build evidence-backend
docker compose up -d
```

> Les donnees sont persistees dans des volumes Docker. La mise a jour ne supprime pas vos conversations ni fichiers.

### Mode Local

```bash
cd korev-evidence
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

# 9. Depannage

## Problemes Docker

### "Cannot connect to the Docker daemon"

**Solution :**
1. Lancez Docker Desktop (local) ou le service Docker (serveur) :
   ```bash
   sudo systemctl start docker
   ```
2. Verifiez : `docker info`

### Le conteneur ne demarre pas

**Solution :**
```bash
# Consulter les logs
docker compose logs evidence-backend

# Erreurs courantes :
# - "ImportError" → image corrompue, reconstruire :
docker compose build --no-cache evidence-backend

# - "Address already in use" → port occupe :
docker compose down
docker compose up -d
```

### Build echoue avec "cannot allocate memory"

**Solution :**
- Serveur : verifiez `free -h`, minimum 4 Go disponibles pendant le build
- Docker Desktop : Settings > Resources > augmenter la memoire a 8 Go+

### L'interface ne charge pas

**Solution :**
1. Verifiez les conteneurs : `docker compose ps`
2. Attendez 60 secondes (le backend a un `start_period` de 60s)
3. Testez le health check : `curl http://localhost/healthz`
4. Consultez les logs : `docker compose logs -f`

## Problemes generaux

### "Erreur de cle API"

**Solution :**
1. Verifiez la cle dans `.env` (pas d'espaces, pas de guillemets)
2. Verifiez votre credit sur le compte OpenRouter/OpenAI
3. Relancez apres modification : `docker compose restart evidence-backend`

### Les images generees ne se telechargent pas

**Solution :** Actualisez la page du navigateur (F5 / Cmd+R). Un correctif recent gere le protocole `sandbox://` utilise par certains modeles.

---

# 10. Support technique

## Informations a fournir

En cas de probleme :
1. Systeme d'exploitation et version
2. Methode d'installation (Docker ou locale)
3. Sortie de `docker compose ps` et `docker compose logs --tail=50 evidence-backend`
4. Message d'erreur exact ou capture d'ecran
5. Version : `cat deploy/.env | grep EVIDENCE_VERSION`

## Commandes de diagnostic

```bash
# Etat des services
docker compose ps

# Logs du backend (derniers 100 lignes)
docker compose logs --tail=100 evidence-backend

# Utilisation des ressources
docker stats --no-stream

# Espace disque des volumes
docker system df -v
```

## Contact

- **Email** : support@korev.ai

---

*Document mis a jour le 17 fevrier 2026*
*Version : 4.0*
*KOREV Evidence - Guide d'installation client*

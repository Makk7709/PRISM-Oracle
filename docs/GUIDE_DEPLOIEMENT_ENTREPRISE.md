# KOREV Evidence — Guide de Déploiement Entreprise

## Document destiné aux prestataires techniques

**Version :** 3.0
**Date :** 2026-03-31
**Classification :** CONFIDENTIEL — Usage interne prestataires
**Périmètre :** 1 serveur central + N postes Windows + dossiers partagés multi-utilisateurs + isolation multi-tenant par organisation

---

# Table des matières

1. [Comprendre KOREV Evidence](#1-comprendre-korev-evidence)
2. [Architecture cible](#2-architecture-cible)
3. [Phase 0 — Audit pré-déploiement](#3-phase-0--audit-pré-déploiement)
4. [Phase 1 — Préparation du serveur](#4-phase-1--préparation-du-serveur)
5. [Phase 2 — Installation du serveur](#5-phase-2--installation-du-serveur)
6. [Phase 3 — Configuration multi-utilisateurs](#6-phase-3--configuration-multi-utilisateurs)
7. [Phase 4 — Configuration applicative](#7-phase-4--configuration-applicative)
8. [Phase 5 — Tests de validation](#8-phase-5--tests-de-validation)
9. [Phase 6 — Déploiement postes Windows (×7)](#9-phase-6--déploiement-postes-windows-7)
10. [Phase 7 — Sécurisation production](#10-phase-7--sécurisation-production)
11. [Maintenance et support](#11-maintenance-et-support)
12. [Annexes](#12-annexes)

> **Temps estimé total :** ~3-4 heures (serveur + multi-user) + ~45 minutes (7 postes × 6 min)

---

# 1. Comprendre KOREV Evidence

## 1.1. Qu'est-ce que KOREV Evidence ?

KOREV Evidence est une **plateforme d'agents IA de confiance**. Ce n'est PAS un simple chatbot.

C'est un système multi-agents composé de **12 agents spécialisés** (juridique, rédaction contractuelle, médical, financier, recherche scientifique, stratégie, marketing, cybersécurité, développement, commercial, etc.) pilotés par un **orchestrateur central** (Agent 0) qui :

- **Cite systématiquement ses sources** : chaque affirmation est liée à un PMID, DOI, article de loi, ou référence vérifiable.
- **Valide par consensus multi-LLM** : les réponses critiques sont votées par 3 modèles d'IA indépendants (quorum 2/3).
- **Refuse plutôt qu'inventer** : philosophie "fail-closed" — si l'IA n'est pas sûre, elle refuse de répondre plutôt que d'halluciner.
- **Trace tout** : audit trail complet avec correlation IDs, evidence packs, bundle d'audit déterministe.
- **Exécute du code** : l'IA peut écrire et exécuter du Python, analyser des fichiers CSV/Excel, générer des PDF professionnels.
- **Recherche en temps réel** : via des serveurs MCP (Model Context Protocol) connectés à ArXiv, Semantic Scholar, PubMed, Légifrance, etc.

## 1.2. Architecture technique

```
┌──────────────────────────────────────────────────────────────────┐
│                        SERVEUR CENTRAL                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │  Flask/WSGI  │  │  Agent 0     │  │  MCP Servers  │          │
│  │  (port 5050) │──│  Orchestrator│──│  (11 services)│          │
│  └──────┬───────┘  └──────────────┘  └───────────────┘          │
│         │                                                        │
│  ┌──────┴───────┐  ┌──────────────┐  ┌───────────────┐          │
│  │  WebUI       │  │  Mémoire     │  │  Index légal  │          │
│  │  (statique)  │  │  (FAISS/SQLite│  │  (Légifrance) │          │
│  └──────────────┘  └──────────────┘  └───────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  VOLUME PARTAGÉ (/app/shared)                         │       │
│  │  ├── users/                                           │       │
│  │  │   ├── nicolas/    {documents/, rapports/, tmp/}   │       │
│  │  │   ├── luc/        {documents/, rapports/, tmp/}   │       │
│  │  │   ├── ... (jeremie, coralie, dominique, laurianne, sarah) │
│  │  │   └── amine/      {documents/, rapports/, tmp/}   │       │
│  │  ├── commun/     ← accessible par tous               │       │
│  │  └── audit/      ← file_operations.jsonl             │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  Volumes persistants :                                           │
│  /data  /logs  /audit  /shared  /tmp/settings.json  .env        │
└──────────────────────────────────────────────────────────────────┘
         │                              │
         │  HTTP/HTTPS (port 80/443)    │  SMB (port 445)
         │  via Caddy reverse proxy     │  via Samba container
         │                              │
┌────────┼──────────────────────────────┼───────────────────────┐
│   ┌────┴────┐  ┌─────────┐  ┌────────┴┐  ...  (×7)          │
│   │ Poste 1 │  │ Poste 2 │  │ Poste 3 │                     │
│   │ Chrome  │  │ Chrome  │  │ Chrome  │                     │
│   │ + drive │  │ + drive │  │ + drive │                     │
│   │ M:\     │  │ M:\     │  │ M:\     │                     │
│   └─────────┘  └─────────┘  └─────────┘                     │
│                POSTES WINDOWS                                 │
│   Chaque poste accède à son dossier personnel via            │
│   le lecteur réseau M:\ (SMB) + à Evidence via Chrome       │
└───────────────────────────────────────────────────────────────┘
```

**Principe :** Le serveur fait tout le travail (IA, calculs, MCP). Les postes Windows accèdent à Evidence via un **navigateur web** (Chrome/Edge) et à leurs **dossiers personnels** via un **lecteur réseau SMB** (M:\). Chaque utilisateur a son propre compte, son propre espace de fichiers, et ne voit PAS les dossiers des autres.

## 1.3. Composants

| Composant | Rôle | Technologie |
|-----------|------|-------------|
| Backend | Serveur principal IA + API | Python 3.11, Flask |
| WebUI | Interface utilisateur | HTML/CSS/JS statique (servi par Flask) |
| MCP Servers | Connecteurs de recherche (ArXiv, PubMed, etc.) | Node.js / Python (stdio) |
| FAISS | Mémoire vectorielle | Python (faiss-cpu) |
| SQLite | Index légal, settings, mémoire | Fichier local |
| WeasyPrint | Génération de PDF professionnels | Python + C libs |
| Caddy | Reverse proxy HTTPS (production) | Go (binaire) |

---

# 2. Architecture cible

## 2.1. Scénario retenu : Docker sur serveur + accès navigateur

### Option A — Production recommandée (`deploy/`)

```
Serveur entreprise (Linux ou Windows Server)
├── Docker Compose (deploy/)
│   ├── evidence-backend  (Flask, Python 3.11 + Node.js, port interne 5050)
│   ├── evidence-caddy    (Caddy reverse proxy, ports 80/443 sur l'hôte)
│   └── evidence-samba    (Partage SMB, port 445 sur l'hôte)
│
├── Volumes Docker persistants
│   ├── evidence-data     → données, mémoire, projets
│   ├── evidence-shared   → ★ dossiers partagés par utilisateur ★
│   ├── evidence-logs     → journaux d'activité
│   ├── evidence-audit    → audit trail (rétention 90j)
│   └── caddy-data        → certificats HTTPS
│
├── deploy/.env           → clés API, auth, config réseau
└── deploy/users.json     → ★ comptes utilisateurs (multi-user) ★

7 postes Windows :
  → Chrome/Edge → http://<IP_SERVEUR>/          (interface web Evidence)
  → Lecteur M:\ → \\<IP_SERVEUR>\<username>    (dossier personnel SMB)
  → Lecteur N:\ → \\<IP_SERVEUR>\commun        (dossier partagé commun)
```

### Option B — Développement / test rapide (`docker/run/`)

```
Serveur
├── Docker Compose (docker/run/)
│   └── korev-evidence (tout-en-un, port 50080 sur l'hôte)
│
└── .env (à la racine du projet)

Accès → http://<IP_SERVEUR>:50080/
```

**Pour un déploiement client, utiliser l'Option A (`deploy/`).**

## 2.2. Configuration matérielle requise

### Serveur (OBLIGATOIRE)

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| **OS** | Ubuntu 22.04 LTS / Windows Server 2022 | Ubuntu 24.04 LTS |
| **CPU** | 4 cores | 8 cores |
| **RAM** | 8 Go | 16 Go |
| **Disque** | 50 Go SSD | 100 Go NVMe |
| **Réseau** | 100 Mbps LAN | 1 Gbps LAN |
| **Internet** | Requis (API IA) | Fibre recommandée |

### Postes Windows (×7)

| Composant | Minimum |
|-----------|---------|
| **OS** | Windows 10/11 (64-bit) |
| **Navigateur** | Chrome 120+ ou Edge 120+ |
| **RAM** | 4 Go (le navigateur suffit) |
| **Réseau** | Connecté au même LAN que le serveur |

---

# 3. Phase 0 — Audit pré-déploiement

**Objectif :** Vérifier que l'infrastructure est prête AVANT de commencer l'installation.

## 3.1. Checklist serveur

```
□  Le serveur est allumé et accessible en SSH ou RDP
□  L'OS est à jour (apt update && apt upgrade ou Windows Update)
□  Le serveur a une IP fixe sur le réseau local (ex: 192.168.1.100)
□  Le serveur a accès à Internet (tester : curl https://api.openai.com)
□  Au moins 50 Go d'espace disque libre (vérifier : df -h)
□  Au moins 8 Go de RAM disponible (vérifier : free -h)
□  Aucun service n'utilise les ports 80, 443, 445 (vérifier : sudo lsof -i :80 -i :443 -i :445)
□  Le firewall autorise les connexions entrantes sur 80, 443 ET 445 (SMB) depuis le LAN
□  Docker est installé OU peut être installé (droits admin)
□  Git est installé OU peut être installé
```

## 3.2. Checklist réseau

```
□  Les 7 postes Windows peuvent pinger l'IP du serveur
□  Le DNS local peut résoudre un nom (ex: evidence.local) vers l'IP serveur
     OU les postes utiliseront directement l'IP (http://192.168.1.100)
□  Pas de proxy HTTP bloquant entre les postes et le serveur
□  Le serveur peut accéder aux domaines suivants (requis pour les API IA) :
     - api.openai.com
     - openrouter.ai
     - api.anthropic.com
     - api.semanticscholar.org
     - export.arxiv.org
     - api.firecrawl.dev
     - fonts.googleapis.com (pour les PDF)
```

## 3.3. Checklist clés API

**KOREV Evidence nécessite au minimum UNE clé API de modèle IA.**
Le donneur d'ordre (le client) doit fournir :

```
□  Clé API OpenRouter (OBLIGATOIRE) — https://openrouter.ai/keys
     Format : sk-or-v1-xxxxxxxxxxxx
     Coût estimé : ~50-200€/mois selon l'usage

□  OU Clé API OpenAI (alternative) — https://platform.openai.com/api-keys
     Format : sk-proj-xxxxxxxxxxxx
     Coût estimé : ~30-150€/mois selon l'usage

□  (Optionnel) Firecrawl API — https://www.firecrawl.dev/app/api-keys
     Pour le web scraping avancé

□  (Optionnel) Brave Search API — https://brave.com/search/api/
     Pour la recherche web (2000 req/mois gratuites)

□  (Optionnel) Tavily API — https://tavily.com/
     Pour la recherche IA

□  (Optionnel) NCBI/PubMed API — https://www.ncbi.nlm.nih.gov/account/settings/
     Pour la recherche biomédicale
```

## 3.4. Points de vigilance (angles morts)

⚠️ **Vérifiez ces points que l'on oublie souvent :**

| Angle mort | Risque | Vérification |
|------------|--------|-------------|
| **Proxy d'entreprise** | Docker pull échoue, API IA inaccessibles | Tester `curl -I https://api.openai.com` depuis le serveur. Si proxy, configurer `HTTP_PROXY` et `HTTPS_PROXY` dans `/etc/environment` ET dans `/etc/systemd/system/docker.service.d/proxy.conf` pour Docker |
| **Antivirus sur serveur** | Peut bloquer Docker, les ports, ou le Python | Ajouter des exclusions pour le dossier d'installation et les ports 5050/80/443/445 |
| **Firewall Windows** | Les postes ne peuvent pas joindre le serveur | Créer une règle entrante TCP pour les ports 80, 443 et 445 (SMB) sur le serveur |
| **DNS local non configuré** | Les postes doivent taper l'IP au lieu d'un nom | Configurer `evidence.local` dans le DNS local ou dans `C:\Windows\System32\drivers\etc\hosts` de chaque poste |
| **Disque plein** | Les logs et la mémoire IA s'accumulent | Configurer le log rotation (fait automatiquement par Docker : max 50 Mo × 5 fichiers) |
| **Timeout API** | Les requêtes IA échouent en entreprise | Vérifier que le MTU réseau est standard (1500) et que le NAT fonctionne |
| **Certificat HTTPS** | Chrome affiche "Non sécurisé" | Utiliser Caddy avec un certificat Let's Encrypt ou auto-signé (voir Phase 6) |
| **Mises à jour automatiques** | Le serveur redémarre pendant la nuit | Désactiver les mises à jour automatiques ou les planifier hors heures de travail |
| **Permissions Docker** | L'utilisateur ne peut pas lancer Docker | Ajouter l'utilisateur au groupe `docker` : `sudo usermod -aG docker $USER` |
| **BIND_HOST=127.0.0.1** | Par défaut, Caddy n'écoute que sur localhost (les postes ne peuvent pas se connecter) | **OBLIGATOIRE :** Mettre `BIND_HOST=0.0.0.0` dans `deploy/.env` |
| **Port 80 déjà pris** | Apache ou Nginx déjà installé sur le serveur | Arrêter le serveur web existant : `sudo systemctl stop apache2 nginx` ou changer `HTTP_PORT=8080` dans `.env` |
| **Port 445 déjà pris** | Un serveur Samba natif tourne déjà | Arrêter : `sudo systemctl stop smbd nmbd` ou changer `SMB_PORT` dans `.env` |
| **`users.json` non créé** | Tous les utilisateurs partagent le même compte (mode mono-user) | Créer `deploy/users.json` à partir de `users.json.example` avec les hash Argon2 |
| **Mot de passe Samba ≠ Evidence** | L'utilisateur a un mot de passe SMB différent de son login Evidence | S'assurer que les mots de passe dans `.env` (SMB_USER_x) correspondent à `users.json` |
| **Volume partagé plein** | Les rapports générés s'accumulent dans les workspaces | Surveiller `docker system df -v` et purger régulièrement `{user}/tmp/` |

---

# 4. Phase 1 — Préparation du serveur

## 4.1. Installation Docker (Ubuntu)

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
sudo apt install -y docker.io docker-compose-plugin

# Activer Docker au démarrage
sudo systemctl enable docker
sudo systemctl start docker

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# IMPORTANT : déconnexion/reconnexion nécessaire
exit
# Se reconnecter en SSH

# Vérifier
docker --version
docker compose version
```

## 4.2. Installation Docker (Windows Server)

```powershell
# PowerShell en tant qu'administrateur
Install-WindowsFeature -Name Containers
Install-Module DockerMsftProvider -Force
Install-Package Docker -ProviderName DockerMsftProvider -Force

# Redémarrer le serveur
Restart-Computer

# Après redémarrage, vérifier
docker --version
```

## 4.3. Installation Git

```bash
# Ubuntu
sudo apt install -y git

# Windows (télécharger depuis https://git-scm.com/download/win)
```

## 4.4. Cloner le projet

```bash
# Créer le répertoire de travail
sudo mkdir -p /opt/korev-evidence
sudo chown $USER:$USER /opt/korev-evidence
cd /opt/korev-evidence

# Cloner le dépôt (le client fournira l'URL et le token d'accès)
git clone https://<TOKEN>@github.com/Makk7709/PRISM-Oracle.git .

# Vérifier que le clone est complet
ls -la
# On doit voir : run_ui.py, docker/, deploy/, webui/, python/, .env, etc.
```

---

# 5. Phase 2 — Installation du serveur

## 5.1. Méthode recommandée : Docker Compose Production (`deploy/`)

### Étape 1 — Copier les fichiers de configuration

```bash
cd /opt/korev-evidence/deploy

# Copier le template .env
cp .env.example .env

# OBLIGATOIRE : copier aussi users.json (même si vous le remplirez plus tard)
# Docker a besoin que ce fichier EXISTE avant le premier lancement.
cp users.json.example users.json

# Éditer le fichier .env
nano .env
```

> **ATTENTION :** Si `users.json` n'existe pas au moment du `docker compose up`, Docker crée un **dossier** au lieu d'un fichier, ce qui bloque le déploiement. Copiez toujours le template AVANT le premier lancement.

### Étape 2 — Configurer le .env

**Modifier au minimum les lignes marquées XXXXX :**

```env
# ═══════════════════════════════════════════════════════════════
# CLÉS API — OBLIGATOIRE (au moins UNE)
# ═══════════════════════════════════════════════════════════════
API_KEY_OPENROUTER=sk-or-v1-XXXXX_FOURNIR_PAR_LE_CLIENT_XXXXX

# ═══════════════════════════════════════════════════════════════
# AUTHENTIFICATION — OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════
AUTH_LOGIN=admin
AUTH_PASSWORD=XXXXX_MOT_DE_PASSE_FORT_XXXXX

# ═══════════════════════════════════════════════════════════════
# RÉSEAU — Caddy expose les ports 80/443 sur le LAN
# ═══════════════════════════════════════════════════════════════
BIND_HOST=0.0.0.0
HTTP_PORT=80
HTTPS_PORT=443

# Le reste est pré-configuré (serveur, fuseau horaire, sécurité...)
# Voir le fichier .env.example complet pour toutes les options
```

### Étape 3 — Construire et lancer

```bash
cd /opt/korev-evidence/deploy

# Construire les images (première fois, ~10-15 minutes)
docker compose build

# Lancer en arrière-plan
docker compose up -d

# Vérifier que les 3 containers tournent
docker compose ps
# On doit voir : evidence-backend (healthy) + evidence-caddy (healthy) + evidence-samba (running)

# Suivre les logs (Ctrl+C pour quitter)
docker compose logs -f --tail=50
```

> **Architecture Docker :**
> - `evidence-backend` : Flask + WebUI + MCP (port interne 5050, **non exposé**)
> - `evidence-caddy` : Reverse proxy Caddy (ports **80/443** exposés sur le LAN)
> - Les postes accèdent à `http://<IP_SERVEUR>/` (port 80, standard)
> - `WEB_UI_HOST=0.0.0.0` est déjà configuré dans le Dockerfile, pas besoin de le mettre dans `.env`

### Étape 4 — Vérifier le démarrage

```bash
# Attendre ~60 secondes (le backend doit démarrer avant Caddy)
# Tester le healthcheck :
curl http://localhost/healthz
# Résultat attendu : {"status": "ok"}

# Tester la page d'accueil :
curl -s http://localhost | head -5
# On doit voir du HTML

# Depuis un poste Windows (remplacer par l'IP réelle) :
# Ouvrir http://192.168.1.100 dans Chrome
```

## 5.2. Méthode alternative : Installation locale (sans Docker / sans Caddy)

**Utiliser uniquement si Docker n'est pas possible. L'accès sera sur le port 5050.**

```bash
cd /opt/korev-evidence

# Installer Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Créer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Installer WeasyPrint (pour les PDF)
pip install weasyprint markdown

# Dépendances système pour WeasyPrint
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0

# Installer Node.js (pour les MCP servers)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# npx est inclus avec npm, pas besoin de l'installer séparément
# Les MCP servers sont lancés automatiquement via npx au démarrage d'Evidence

# Lancer le serveur (IMPORTANT : 0.0.0.0 pour l'accès réseau)
WEB_UI_HOST=0.0.0.0 python run_ui.py
```

---

# 6. Phase 3 — Configuration multi-utilisateurs

> **NOUVEAU v2.0 :** Evidence supporte désormais **plusieurs utilisateurs** avec des **dossiers isolés**. Chaque employé a son propre login, son propre espace de travail, et ne voit PAS les fichiers des autres.

## 6.1. Configurer le fichier `users.json`

Ce fichier a déjà été copié depuis le template en Phase 2 (Étape 1). Il contient des hash fictifs qu'il faut maintenant remplacer par les vrais hash Argon2 de chaque utilisateur.

```bash
cd /opt/korev-evidence/deploy

# Le fichier existe déjà (copié en Phase 2)
# Vérifier :
cat users.json
# On doit voir les entrées avec "REMPLACEZ_PAR_HASH_REEL"

# Éditer
nano users.json
```

### Étape 1 — Générer les hash Argon2 pour chaque utilisateur

```bash
cd /opt/korev-evidence

# Activer le venv (si installation locale) ou exécuter dans Docker
source venv/bin/activate   # local
# OU
docker compose exec evidence-backend bash   # Docker

# Générer un hash pour chaque utilisateur
python3 -c "from python.security.auth import hash_password; print(hash_password('MotDePasseMarie2026!'))"
# Résultat : $argon2id$v=19$m=65536,t=3,p=4$xxxxxxxxxxxxx

python3 -c "from python.security.auth import hash_password; print(hash_password('MotDePasseJean2026!'))"
# etc. pour chaque utilisateur
```

### Étape 2 — Remplir `users.json`

```json
{
  "users": {
    "amine": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "admin"
    },
    "nicolas": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "luc": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "jeremie": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "coralie": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "dominique": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "laurianne": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    },
    "sarah": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$HASH_GENERE_CI_DESSUS",
      "role": "user"
    }
  }
}
```

> **Rôles :**
> - `user` : accès à son workspace + dossier commun uniquement. **Pas d'accès aux paramètres système** (clés API, modèles IA, configuration MCP).
> - `admin` : accès à TOUS les workspaces + gestion des utilisateurs + **accès exclusif aux paramètres système** (bouton "Paramètres" visible uniquement pour les admin).

### Étape 3 — Configurer Samba dans `.env`

Ajouter les identifiants Samba dans `deploy/.env`. **Les logins doivent correspondre à `users.json` :**

```env
# Utilisateurs Samba (format: "login;motdepasse")
# Le mot de passe ici est en CLAIR (Samba l'exige). C'est le même mot de passe
# que celui qui a été haché en Argon2 dans users.json.
SMB_USER_1=nicolas;MotDePasseNicolas2026!
SMB_USER_2=luc;MotDePasseLuc2026!
SMB_USER_3=jeremie;MotDePasseJeremie2026!
SMB_USER_4=coralie;MotDePasseCoralie2026!
SMB_USER_5=dominique;MotDePasseDominique2026!
SMB_USER_6=laurianne;MotDePasseLaurianne2026!
SMB_USER_7=sarah;MotDePasseSarah2026!
SMB_USER_ADMIN=amine;MotDePasseAmine2026!

# Port SMB (445 = standard Windows, ne pas changer sauf conflit)
SMB_PORT=445

# Dossier partagé (ne pas changer, correspond au volume Docker)
EVIDENCE_SHARED_DIR=/app/shared
```

### Étape 4 — Mettre à jour les partages Samba dans `docker-compose.yml`

Le fichier `deploy/docker-compose.yml` contient par défaut la configuration Samba pour **8 utilisateurs** (nicolas, luc, jeremie, coralie, dominique, laurianne, sarah + amine admin). **Vérifiez que les noms et partages correspondent bien à vos utilisateurs réels**, et adaptez si nécessaire. Voici la configuration par défaut :

```yaml
    command: >
      -n
      -p
      -u "${SMB_USER_1:-nicolas;pass}"
      -u "${SMB_USER_2:-luc;pass}"
      -u "${SMB_USER_3:-jeremie;pass}"
      -u "${SMB_USER_4:-coralie;pass}"
      -u "${SMB_USER_5:-dominique;pass}"
      -u "${SMB_USER_6:-laurianne;pass}"
      -u "${SMB_USER_7:-sarah;pass}"
      -u "${SMB_USER_ADMIN:-amine;pass}"
      -s "nicolas;/shared/users/nicolas;yes;no;no;nicolas,amine;;;Espace Nicolas"
      -s "luc;/shared/users/luc;yes;no;no;luc,amine;;;Espace Luc"
      -s "jeremie;/shared/users/jeremie;yes;no;no;jeremie,amine;;;Espace Jeremie"
      -s "coralie;/shared/users/coralie;yes;no;no;coralie,amine;;;Espace Coralie"
      -s "dominique;/shared/users/dominique;yes;no;no;dominique,amine;;;Espace Dominique"
      -s "laurianne;/shared/users/laurianne;yes;no;no;laurianne,amine;;;Espace Laurianne"
      -s "sarah;/shared/users/sarah;yes;no;no;sarah,amine;;;Espace Sarah"
      -s "commun;/shared/commun;yes;no;no;nicolas,luc,jeremie,coralie,dominique,laurianne,sarah,amine;;;Dossier commun"
```

> **Règle d'isolation :** Chaque ligne `-s` accorde l'accès à l'utilisateur concerné + amine (admin) uniquement.
> Nicolas ne voit que `nicolas` et `commun`. Il ne voit PAS `luc`, `jeremie`, etc.

### Étape 5 — Reconstruire et relancer

```bash
cd /opt/korev-evidence/deploy

# Reconstruire (intègre les nouvelles config)
docker compose build

# Relancer
docker compose up -d

# Vérifier les 3 containers
docker compose ps
# On doit voir :
#   evidence-backend  (healthy)
#   evidence-caddy    (healthy)
#   evidence-samba    (running)
```

## 6.2. Structure des dossiers partagés

Après le premier login de chaque utilisateur, la structure suivante est automatiquement créée :

```
/app/shared/                      (volume Docker evidence-shared)
├── users/
│   ├── nicolas/
│   │   ├── documents/            ← Nicolas dépose ses fichiers ici (via SMB)
│   │   ├── rapports/             ← Evidence dépose les résultats ici
│   │   └── tmp/                  ← fichiers temporaires Evidence
│   ├── luc/
│   │   ├── documents/
│   │   ├── rapports/
│   │   └── tmp/
│   ├── ... (jeremie, coralie, dominique, laurianne, sarah)
│   └── amine/
│       ├── documents/
│       ├── rapports/
│       └── tmp/
├── commun/                       ← accessible par TOUS les utilisateurs
│   └── (templates, ressources partagées...)
└── audit/
    └── file_operations.jsonl     ← journal de TOUTES les opérations fichier
```

### Qui a accès à quoi ?

| Utilisateur | Son dossier | Dossiers des autres | Dossier commun | Audit |
|-------------|:-----------:|:-------------------:|:--------------:|:-----:|
| **nicolas** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **luc** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **jeremie** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **coralie** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **dominique** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **laurianne** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **sarah** | Lecture + Écriture | INTERDIT | Lecture + Écriture | Non |
| **amine** (admin) | Lecture + Écriture | Lecture + Écriture (tous) | Lecture + Écriture | Oui |

> **Sécurité :** L'isolation est appliquée à DEUX niveaux :
> 1. **Côté Evidence (Python)** : le `WorkspaceManager` valide chaque accès fichier et rejette les tentatives de traversée de répertoire (`../`, symlinks, etc.)
> 2. **Côté Samba (SMB)** : chaque partage réseau est restreint par utilisateur Samba

## 6.3. Mode mono-utilisateur (fallback)

Si `users.json` n'existe PAS, Evidence fonctionne comme avant :
- Un seul couple `AUTH_LOGIN`/`AUTH_PASSWORD` défini dans `.env`
- Pas de workspace par utilisateur
- Pas de dossier partagé
- Comportement identique à la v1.0

---

# 7. Phase 4 — Configuration applicative

## 7.1. Premier accès

1. Ouvrir un navigateur sur le serveur : `http://localhost` (deploy/) ou `http://localhost:5050` (local)
2. Se connecter avec le login d'un utilisateur défini dans `users.json` (ou `AUTH_LOGIN`/`AUTH_PASSWORD` en mono-user)
3. L'interface KOREV Evidence apparaît avec la page d'accueil "KOREV *Evidence*"

## 7.2. Configuration des modèles IA

Accéder aux **Settings** (icône engrenage en bas de la sidebar) :

| Paramètre | Valeur recommandée | Description |
|-----------|-------------------|-------------|
| Chat Model Provider | `openrouter` | Fournisseur principal |
| Chat Model | `openai/gpt-4.1` | Modèle principal (meilleur rapport qualité/prix) |
| Utility Model | `openai/gpt-4.1-mini` | Modèle utilitaire (plus rapide, moins cher) |
| Embedding Model | `huggingface` / `all-MiniLM-L6-v2` | Recherche sémantique (LOCAL, gratuit) |
| Temperature | `0.5` | Équilibre créativité/précision |

## 7.3. Configuration de l'exécution de code

**IMPORTANT — le paramètre `shell_interface` doit être :**

| Contexte | Valeur | Fichier |
|----------|--------|---------|
| Docker | `local` (par défaut) | `tmp/settings.json` |
| Installation locale | `local` | `tmp/settings.json` |

> **Note :** En Docker, le défaut est `local` (Local Python TTY). Si la mention "Unable to connect to port 55022" apparaît, c'est que `ssh` est sélectionné par erreur — utiliser `local`.

Si la mention "accès à l'automatisation Python non disponible" apparaît, modifier dans `tmp/settings.json` :

```json
"shell_interface": "local"
```

## 7.4. Configuration des MCP Servers

Les MCP (Model Context Protocol) servers sont des connecteurs de recherche. Ils sont configurés dans `mcp_config.json` :

| Serveur | Fonction | Pré-requis |
|---------|----------|-----------|
| `fetch` | Récupération de pages web | Aucun |
| `arxiv` | Articles scientifiques ArXiv | Aucun |
| `semanticscholar` | Articles académiques | Aucun |
| `openalex` | Données académiques OpenAlex | Node.js |
| `firecrawl` | Web scraping avancé | Clé API Firecrawl |
| `tavily` | Recherche IA | Clé API Tavily |
| `pubmed` | Articles biomédicaux | Clé API NCBI (optionnel) |
| `playwright` | Automatisation navigateur | Playwright installé |
| `filesystem` | Accès fichiers | Aucun |
| `brave-search` | Recherche web Brave | Clé API Brave |
| `puppeteer` | Automatisation navigateur | Chromium |

**Vérification :** après le démarrage, les logs doivent afficher :
```
✓ MCP config loaded from .../mcp_config.json: 11 servers
MCPClientBase (web_fetch): Tools updated. Found 1 tools.
MCPClientBase (arxiv_papers): Tools updated. Found 4 tools.
MCPClientBase (semantic_scholar): Tools updated. Found 12 tools.
```

---

# 8. Phase 5 — Tests de validation

## 8.1. Test de base

Ouvrir le chat Evidence et taper :

```
Bonjour, quel est ton nom et quels agents sont disponibles ?
```

**Résultat attendu :** Evidence se présente et liste ses agents spécialisés.

## 8.2. Test de recherche (MCP)

```
Recherche les 3 derniers articles sur l'IA générative dans la santé sur ArXiv
```

**Résultat attendu :** Evidence retourne des articles avec titres, auteurs, dates, DOI.

## 8.3. Test d'exécution Python

```
Écris un script Python qui génère un graphique de la fonction sinus et sauvegarde-le
```

**Résultat attendu :** Evidence écrit et exécute du code Python, produit un fichier image.

## 8.4. Test de génération PDF

```
Rédige un rapport de 2 pages sur les avantages de l'IA en entreprise et génère-le en PDF
```

**Résultat attendu :** Un PDF avec la charte PRISM (Playfair Display, couverture noire, tableaux professionnels) est téléchargeable.

## 8.5. Test multi-utilisateur et isolation

**Ce test est CRITIQUE. Il valide l'isolation entre utilisateurs.**

### Test A — Deux utilisateurs simultanes

1. Sur le **Poste 1** : ouvrir Chrome → `http://<IP_SERVEUR>` → login avec **nicolas**
2. Sur le **Poste 2** : ouvrir Chrome → `http://<IP_SERVEUR>` → login avec **luc**
3. Vérifier que chaque session est indépendante (conversations séparées)
4. Vérifier que les réponses arrivent sans latence excessive (<30s)

### Test B — Isolation des dossiers SMB

1. Sur le **Poste 1** (Nicolas) : ouvrir l'Explorateur → `\\<IP_SERVEUR>\nicolas`
   - Nicolas DOIT voir ses dossiers `documents/`, `rapports/`, `tmp/`
   - Nicolas DOIT pouvoir créer un fichier test dans `documents/`
2. Sur le **Poste 1** (Nicolas) : essayer d'accéder à `\\<IP_SERVEUR>\luc`
   - Nicolas NE DOIT PAS avoir accès → erreur "Accès refusé"
3. Sur le **Poste 1** (Nicolas) : ouvrir `\\<IP_SERVEUR>\commun`
   - Nicolas DOIT pouvoir lire et écrire dans le dossier commun

### Test C — Evidence lit les fichiers utilisateur

1. Sur le **Poste 1** : via l'explorateur, déposer un fichier `test.txt` dans `\\<IP_SERVEUR>\nicolas\documents\`
2. Dans Evidence (chat Nicolas) : demander "Lis le fichier test.txt dans mon dossier documents"
3. **Résultat attendu** : Evidence lit le contenu du fichier de Nicolas

### Test D — Evidence génère un rapport dans le workspace

1. Dans Evidence (chat Nicolas) : demander "Génère un rapport PDF sur l'IA en entreprise"
2. **Résultat attendu** : Le PDF est généré dans `\\<IP_SERVEUR>\nicolas\rapports\`
3. Vérifier que le fichier est accessible depuis l'Explorateur Windows de Nicolas

## 8.6. Grille de validation

| # | Test | Résultat attendu | Validé ? |
|---|------|----------|----------|
| 1 | Page d'accueil accessible | Page KOREV Evidence avec logo | □ |
| 2 | Login Nicolas | Login fonctionne avec identifiants de `users.json` | □ |
| 3 | Login Luc (simultané) | Session indépendante de Nicolas | □ |
| 4 | Chat simple | Réponse en français, cohérente | □ |
| 5 | Recherche ArXiv | Articles retournés avec DOI | □ |
| 6 | Exécution Python | Code exécuté, résultat affiché | □ |
| 7 | Génération PDF | PDF téléchargeable, charte PRISM | □ |
| 8 | Recherche Semantic Scholar | Articles scientifiques trouvés | □ |
| 9 | Mémoire | Evidence se souvient du contexte | □ |
| 10 | Performance | Réponse en <30s pour une question simple | □ |
| 11 | **SMB — Nicolas voit son dossier** | `\\serveur\nicolas` accessible | □ |
| 12 | **SMB — Nicolas PAS accès à Luc** | `\\serveur\luc` → Accès refusé | □ |
| 13 | **SMB — Dossier commun** | `\\serveur\commun` accessible en lecture/écriture | □ |
| 14 | **Evidence lit fichier Nicolas** | Fichier déposé via SMB lisible par Evidence | □ |
| 15 | **Evidence écrit rapport Nicolas** | Rapport dans `rapports/` visible via SMB | □ |
| 16 | **Audit trail** | `file_operations.jsonl` contient les opérations | □ |
| 17 | **Healthcheck** | `curl http://localhost/healthz` → `{"status":"ok"}` | □ |

---

# 9. Phase 6 — Déploiement postes Windows (×7)

## 9.1. Principe

**Les postes Windows n'ont RIEN à installer.**
KOREV Evidence est une application web servie par le serveur central.
Les utilisateurs accèdent via :
1. **Un navigateur web** (Chrome/Edge) pour l'interface IA Evidence
2. **Un lecteur réseau SMB** (M:\ et N:\) pour leurs dossiers personnels et le dossier commun

## 9.2. Procédure pour chaque poste (6 minutes/poste)

### Étape 1 — Vérifier la connectivité

```
# Ouvrir CMD ou PowerShell sur le poste Windows
ping 192.168.1.100
# (remplacer par l'IP réelle du serveur)
# Résultat attendu : réponse en <1ms
```

### Étape 2 — Configurer le raccourci

**Option A — Raccourci bureau (recommandé)**

1. Clic droit sur le bureau → Nouveau → Raccourci
2. Emplacement : `http://192.168.1.100` (ou `https://evidence.local` si HTTPS configuré)
3. Nom : `KOREV Evidence`
4. Changer l'icône (optionnel) : utiliser le favicon de l'application (`webui/public/favicon.svg`) converti en `.ico`

**Option B — Favoris Chrome/Edge**

1. Ouvrir Chrome ou Edge
2. Aller sur `http://192.168.1.100`
3. Cliquer sur l'étoile (favoris) → Ajouter aux favoris
4. Placer dans la barre de favoris pour un accès rapide

**Option C — Application web (PWA-like)**

1. Ouvrir Chrome → `http://192.168.1.100`
2. Menu ⋮ → "Installer KOREV Evidence..." (ou "Créer un raccourci...")
3. Cocher "Ouvrir dans une fenêtre" → Créer
4. L'application apparaît dans le menu Démarrer et le bureau

### Étape 3 — Connecter les lecteurs réseau (dossier personnel + commun)

**C'est l'étape la plus importante pour que les utilisateurs puissent échanger des fichiers avec Evidence.**

#### Lecteur M:\ — Dossier personnel de l'utilisateur

1. Ouvrir l'**Explorateur de fichiers** Windows
2. Clic droit sur **Ce PC** → **Connecter un lecteur réseau...**
3. Lecteur : **M:**
4. Dossier : `\\192.168.1.100\nicolas` (remplacer `192.168.1.100` par l'IP du serveur et `nicolas` par le login de l'utilisateur)
5. Cocher **Se reconnecter lors de la connexion**
6. Cocher **Se connecter avec d'autres informations d'identification**
7. Entrer le login et le mot de passe **Samba** de l'utilisateur (défini dans `.env`)
8. Cliquer **Terminer**

> Le lecteur M:\ contient : `documents/` (fichiers de l'utilisateur), `rapports/` (résultats Evidence), `tmp/`

#### Lecteur N:\ — Dossier commun partagé

1. Même procédure que ci-dessus
2. Lecteur : **N:**
3. Dossier : `\\192.168.1.100\commun`
4. Mêmes identifiants que le lecteur M:\
5. **Terminer**

> Le lecteur N:\ est partagé entre TOUS les utilisateurs. Idéal pour les templates et documents de référence.

#### Vérification rapide

```
# Sur le poste, ouvrir CMD :
dir M:\documents
# Résultat attendu : le dossier est vide (ou contient les fichiers déjà déposés)

dir N:\
# Résultat attendu : le dossier commun est accessible
```

### Étape 4 — Configurer le fichier hosts (si pas de DNS local)

Si le DNS local n'est pas configuré, ajouter l'entrée manuellement :

```
# Ouvrir le Bloc-notes en tant qu'administrateur
# Fichier → Ouvrir → C:\Windows\System32\drivers\etc\hosts

# Ajouter cette ligne à la fin :
192.168.1.100    evidence.local
```

Ensuite les utilisateurs accèdent à `http://evidence.local` (deploy/ avec Caddy) ou `http://evidence.local:5050` (installation locale).

### Étape 5 — Premier login Evidence

1. Ouvrir KOREV Evidence dans le navigateur
2. Entrer l'identifiant et le mot de passe **de l'utilisateur** (défini dans `users.json`)
3. Vérifier que la page d'accueil s'affiche correctement
4. Envoyer un message test : "Bonjour"
5. Vérifier que le lecteur M:\ montre bien les sous-dossiers `documents/`, `rapports/`, `tmp/`

### Étape 6 — Configuration poste (optionnel)

Pour une expérience optimale, vérifier sur chaque poste :

```
□  Chrome/Edge est à jour (version 120+)
□  Pas de bloqueur de publicité interférant avec Evidence
□  Le zoom du navigateur est à 100%
□  Les cookies sont autorisés pour le domaine du serveur
□  Les pop-ups sont autorisés pour le domaine (pour les téléchargements PDF)
```

## 9.3. Déploiement automatisé (GPO / Script)

Pour déployer le raccourci + les lecteurs réseau sur les 7 postes via GPO Active Directory ou un script :

```powershell
# Script PowerShell à exécuter sur chaque poste (ou via GPO)
# deploy_evidence_workstation.ps1
#
# PARAMÈTRES À MODIFIER :
param(
    [string]$ServerIP = "192.168.1.100",
    [string]$Username = "",           # Login de l'utilisateur (ex: "nicolas")
    [string]$Password = ""            # Mot de passe Samba
)

if (-not $Username) {
    $Username = Read-Host "Entrez le login Evidence de cet utilisateur"
}

$URL = "http://${ServerIP}"
$ShortcutName = "KOREV Evidence"

# ─── 1. Raccourci bureau ───
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut("$DesktopPath\$ShortcutName.lnk")
$Shortcut.TargetPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$Shortcut.Arguments = "--app=$URL"
$Shortcut.Description = "KOREV Evidence — Plateforme d'agents IA de confiance"
$Shortcut.Save()

# ─── 2. Lecteur réseau M:\ (dossier personnel) ───
$PersonalShare = "\\${ServerIP}\${Username}"
net use M: $PersonalShare /user:$Username $Password /persistent:yes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Lecteur M:\ connecte a $PersonalShare"
} else {
    Write-Host "[ERREUR] Impossible de connecter M:\ a $PersonalShare"
}

# ─── 3. Lecteur réseau N:\ (dossier commun) ───
$CommunShare = "\\${ServerIP}\commun"
net use N: $CommunShare /user:$Username $Password /persistent:yes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Lecteur N:\ connecte a $CommunShare"
} else {
    Write-Host "[ERREUR] Impossible de connecter N:\ a $CommunShare"
}

# ─── 4. Fichier hosts (si pas de DNS local) ───
$HostsFile = "C:\Windows\System32\drivers\etc\hosts"
$Entry = "$ServerIP    evidence.local"
if (-not (Get-Content $HostsFile | Select-String "evidence.local")) {
    Add-Content -Path $HostsFile -Value $Entry
    Write-Host "[OK] Entree hosts ajoutee : evidence.local"
}

Write-Host ""
Write-Host "=== KOREV Evidence configure ==="
Write-Host "  Web : $URL"
Write-Host "  Dossier perso : M:\ ($PersonalShare)"
Write-Host "  Dossier commun : N:\ ($CommunShare)"
Write-Host "  Login : $Username"
```

**Utilisation :**
```powershell
# En tant qu'administrateur sur le poste de Nicolas
.\deploy_evidence_workstation.ps1 -ServerIP "192.168.1.100" -Username "nicolas" -Password "MotDePasseNicolas2026!"
```

---

# 10. Phase 7 — Sécurisation production

## 10.1. HTTPS avec Caddy (certificat auto-signé)

Pour un réseau local sans nom de domaine public :

```bash
cd /opt/korev-evidence

# Générer un certificat auto-signé
mkdir -p deploy/certs
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout deploy/certs/evidence.key \
  -out deploy/certs/evidence.crt \
  -subj "/CN=evidence.local/O=KOREV/C=FR"
```

Modifier le fichier `deploy/config/Caddyfile` pour activer HTTPS :

```caddyfile
evidence.local {
    tls /etc/caddy/certs/evidence.crt /etc/caddy/certs/evidence.key

    # Tout le trafic est relayé vers le backend Flask
    reverse_proxy evidence-backend:5050

    encode gzip zstd

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}
```

Puis décommenter la ligne de montage des certificats dans `deploy/docker-compose.yml` (service `evidence-caddy`) :

```yaml
volumes:
  - ./config/Caddyfile:/etc/caddy/Caddyfile:ro
  - caddy-data:/data
  - caddy-config:/config
  - ./certs:/etc/caddy/certs:ro    # ← décommenter cette ligne
```

## 10.2. Authentification

### Mode multi-utilisateurs (recommandé en entreprise)

L'authentification multi-utilisateurs est configurée via `deploy/users.json` (voir Phase 3).

Chaque mot de passe est stocké en **Argon2id** (hachage cryptographique, jamais en clair).

```
Résumé de la configuration :
  - deploy/users.json     → comptes Evidence (hash Argon2)
  - deploy/.env           → comptes Samba (plaintext, exigé par Samba)
  - Les LOGINS doivent être identiques dans les deux fichiers
  - Les MOTS DE PASSE doivent correspondre
```

### Contrôle d'accès aux paramètres système

Les paramètres système (clés API, configuration des modèles IA, serveurs MCP) sont **réservés aux administrateurs** :

| Rôle | Accès chat / agents | Bouton "Paramètres" | API settings |
|------|---------------------|---------------------|--------------|
| `admin` | Oui | **Visible** | Autorisé (200) |
| `user` | Oui | **Masqué** | Refusé (403) |

- En **mode mono-utilisateur**, le compte est automatiquement `admin` — aucun changement de comportement.
- En **mode multi-utilisateur**, seuls les comptes avec `"role": "admin"` dans `users.json` voient le bouton et peuvent modifier les paramètres.

> **Sécurité :** La protection est appliquée à la fois côté frontend (bouton masqué) ET côté backend (rejet HTTP 403). Même une requête directe à l'API `/settings_get` ou `/settings_set` sera refusée pour un utilisateur non-admin.

### Mode mono-utilisateur (fallback)

Si `users.json` n'existe pas, configurer dans `.env` :

```env
AUTH_LOGIN=admin
AUTH_PASSWORD=MotDePasseFort2026!
```

> **Recommandation :** Utiliser le mode multi-utilisateurs dès que plus d'une personne utilise Evidence.

## 10.3. Firewall serveur

```bash
# Ubuntu - UFW
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow from 192.168.1.0/24 to any port 80     # Caddy HTTP
sudo ufw allow from 192.168.1.0/24 to any port 443    # Caddy HTTPS
sudo ufw allow from 192.168.1.0/24 to any port 445    # Samba SMB
# NE PAS exposer le port 5050 (le backend est derrière Caddy)
# NE PAS exposer le port 445 sur Internet (Samba = LAN uniquement)
```

> **IMPORTANT :** Le port 445 (Samba) ne doit JAMAIS être accessible depuis Internet.
> N'autoriser que le sous-réseau local (192.168.1.0/24 dans l'exemple).

## 10.4. Sauvegardes automatiques

```bash
# Script de backup quotidien
cat > /opt/korev-evidence/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/evidence"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Sauvegarder les volumes Docker (données + audit + dossiers partagés)
docker run --rm \
  -v evidence-data:/data:ro \
  -v evidence-audit:/audit:ro \
  -v evidence-shared:/shared:ro \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/evidence-backup-$DATE.tar.gz /data /audit /shared

# Sauvegarder le .env et users.json (ATTENTION: contient les clés API et les hash)
cp /opt/korev-evidence/deploy/.env $BACKUP_DIR/env-backup-$DATE
cp /opt/korev-evidence/deploy/users.json $BACKUP_DIR/users-backup-$DATE.json 2>/dev/null || true

# Rotation : garder les 30 derniers
ls -t $BACKUP_DIR/evidence-backup-*.tar.gz | tail -n +31 | xargs rm -f

echo "✅ Backup complété : evidence-backup-$DATE.tar.gz"
EOF

chmod +x /opt/korev-evidence/backup.sh

# Crontab : backup chaque nuit à 3h
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/korev-evidence/backup.sh >> /var/log/evidence-backup.log 2>&1") | crontab -
```

---

# 11. Maintenance et support

## 11.1. Commandes utiles

```bash
# Se placer dans le répertoire de déploiement
cd /opt/korev-evidence/deploy

# Voir les logs en temps réel (les 3 containers)
docker compose logs -f

# Logs du backend uniquement
docker compose logs -f evidence-backend

# Redémarrer Evidence
docker compose restart

# Arrêter Evidence
docker compose down

# Mettre à jour Evidence
cd /opt/korev-evidence
git pull origin main
cd deploy
docker compose build   # Rebuild les images avec le nouveau code
docker compose up -d   # Relancer
```

## 11.2. Commandes multi-utilisateurs

```bash
# Voir les connexions SMB actives
docker exec evidence-samba smbstatus

# Ajouter un nouvel utilisateur (nécessite redémarrage Samba)
# 1. Ajouter dans deploy/users.json (avec hash Argon2)
# 2. Ajouter SMB_USER_X dans deploy/.env
# 3. Ajouter un partage -s dans docker-compose.yml
# 4. Relancer : docker compose restart evidence-samba

# Voir les logs d'audit des fichiers
docker exec evidence-backend cat /app/shared/audit/file_operations.jsonl | tail -20

# Voir l'espace utilisé par chaque utilisateur
docker exec evidence-backend du -sh /app/shared/users/*/

# Réinitialiser le workspace d'un utilisateur (ATTENTION : supprime ses fichiers)
# docker exec evidence-backend rm -rf /app/shared/users/nicolas/tmp/*
```

## 11.3. Problèmes courants

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Page blanche | Le backend n'a pas fini de démarrer | Attendre 30s et rafraîchir. Vérifier `docker compose logs` |
| "Unable to connect to port 55022" | `shell_interface` est sur `ssh` | Mettre `"shell_interface": "local"` dans `tmp/settings.json` |
| "API key not found" | Clé API manquante dans `.env` | Vérifier `.env`, ajouter la clé, redémarrer |
| MCP servers ne se connectent pas | `tmp/settings.json` écrase `mcp_config.json` | Supprimer `tmp/settings.json` et redémarrer (sera recréé) |
| PDF sans les bonnes polices | Google Fonts inaccessible | Vérifier accès à `fonts.googleapis.com`. Alternative : installer les fonts localement |
| "Rate limited" sur l'IA | Trop de requêtes API | Normal en usage intensif. Attendre quelques secondes. Envisager un plan API supérieur |
| Le serveur redémarre tout seul | `restart: unless-stopped` après un crash | Vérifier les logs pour la cause du crash : `docker compose logs --tail=100` |
| Mémoire saturée | Conversations longues en mémoire | Purger les anciennes conversations dans l'interface |
| Lecteur réseau M:\ inaccessible | Samba container pas démarré ou mot de passe incorrect | Vérifier `docker compose ps evidence-samba`. Vérifier les mots de passe dans `.env` |
| "Accès refusé" sur le partage SMB | L'utilisateur essaie d'accéder au dossier d'un autre | Normal ! L'isolation fonctionne. Chaque user n'accède qu'à son dossier + commun |
| Evidence ne trouve pas le fichier déposé | Le fichier a été déposé hors du workspace | Vérifier que le fichier est dans `M:\documents\` et non à la racine de M:\ |
| Audit trail vide | Evidence n'a pas encore effectué d'opération fichier | L'audit se remplit au fur et à mesure. Vérifier avec `docker exec evidence-backend cat /app/shared/audit/file_operations.jsonl` |

## 11.4. Monitoring

```bash
# Vérifier que Evidence est en ligne
curl -sf http://localhost/healthz && echo " ✅ ONLINE" || echo "❌ OFFLINE"

# Espace disque des volumes
docker system df -v

# Ressources des containers
docker stats --no-stream

# Vérifier Samba
docker exec evidence-samba smbstatus --brief

# Vérifier l'espace des workspaces
docker exec evidence-backend du -sh /app/shared/users/*/
```

---

# 12. Annexes

## 12.1. Structure des fichiers

```
/opt/korev-evidence/
├── .env.example                   # Template configuration (à la racine)
├── run_ui.py                      # Point d'entrée du serveur Flask
├── requirements.txt               # Dépendances Python
├── mcp_config.json                # Configuration des 11 MCP servers
├── deploy/                        # ★ DÉPLOIEMENT PRODUCTION ★
│   ├── .env.example               # Template config production (copier → .env)
│   ├── .env                       # ← VOS CLÉS API ICI (à créer)
│   ├── users.json.example         # ★ Template comptes multi-utilisateurs
│   ├── users.json                 # ← COMPTES UTILISATEURS (à créer)
│   ├── docker-compose.yml         # Orchestration : backend + Caddy + Samba
│   ├── Dockerfile.backend         # Image autonome (Python + Node.js + tout)
│   └── config/
│       └── Caddyfile              # Reverse proxy Caddy
├── docker/
│   └── run/
│       └── docker-compose.yml     # Déploiement local (dev/test)
├── python/
│   ├── helpers/                   # Modules utilitaires
│   │   ├── evidence_pdf_engine.py # Moteur PDF PRISM (WeasyPrint)
│   │   ├── evidence_document/     # Système de documents AST
│   │   ├── user_manager.py        # ★ Gestionnaire multi-utilisateurs
│   │   └── user_workspace.py      # ★ Isolation workspace par utilisateur
│   ├── security/                  # Auth Argon2, rate limiting, CSRF
│   └── tools/                     # Outils de l'agent IA
├── webui/                         # Interface web (HTML/CSS/JS)
│   ├── components/                # Composants UI
│   ├── css/                       # Feuilles de style
│   └── public/                    # Assets (logos, icônes)
├── mcp_servers/                   # Code local des MCP servers
├── agents/                        # Définitions des 9+ agents
├── prompts/                       # Prompts système
├── fonts/                         # Polices embarquées
└── data/                          # Données persistantes (volume Docker)
    ├── legal/                     # Index juridique
    └── memory/                    # Mémoire IA
```

## 12.2. Ports utilisés (deploy/)

| Port | Service | Container | Exposition |
|------|---------|-----------|-----------|
| 80 | Caddy HTTP (reverse proxy) | evidence-caddy | LAN — accès postes |
| 443 | Caddy HTTPS (reverse proxy) | evidence-caddy | LAN — accès postes |
| 445 | Samba SMB (dossiers partagés) | evidence-samba | LAN — lecteurs réseau |
| 5050 | Flask backend (interne Docker) | evidence-backend | **NON exposé** |
| 22 | SSH serveur | Hôte | Admin uniquement |

> **Note :** En mode `docker/run/`, le port exposé est **50080** (tout-en-un, sans Caddy).
> En mode local (sans Docker), le port est **5050** directement.

## 12.3. Variables d'environnement critiques (`deploy/.env`)

| Variable | Obligatoire | Description |
|----------|:-----------:|-------------|
| `API_KEY_OPENROUTER` | ✅ | Clé API pour les modèles IA (fournisseur principal) |
| `AUTH_LOGIN` | Mono-user | Nom d'utilisateur (si pas de `users.json`) |
| `AUTH_PASSWORD` | Mono-user | Mot de passe (si pas de `users.json`) |
| `BIND_HOST` | ✅ | Adresse d'écoute Caddy : `0.0.0.0` pour accès LAN |
| `HTTP_PORT` | Non | Port HTTP Caddy sur l'hôte (défaut : 80) |
| `HTTPS_PORT` | Non | Port HTTPS Caddy sur l'hôte (défaut : 443) |
| `EVIDENCE_SHARED_DIR` | Multi-user | Racine des workspaces partagés (défaut : `/app/shared`) |
| `SMB_PORT` | Multi-user | Port Samba sur l'hôte (défaut : 445) |
| `SMB_USER_1..N` | Multi-user | Comptes Samba, format `login;password` |
| `SMB_USER_ADMIN` | Multi-user | Compte admin Samba |
| `KOREV_PRODUCTION` | Non | Mode production : `true` (défaut dans docker-compose) |
| `DEFAULT_USER_TIMEZONE` | Non | Fuseau horaire (défaut : Europe/Paris) |
| `CPU_LIMIT` | Non | Limite CPU du backend (défaut : 4.0) |
| `MEMORY_LIMIT` | Non | Limite RAM du backend (défaut : 8G) |

## 12.4. Fichier `users.json` — Référence

```json
{
  "users": {
    "<login>": {
      "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$<hash>",
      "role": "user"    // ou "admin"
    }
  }
}
```

| Champ | Description |
|-------|-------------|
| `<login>` | Nom d'utilisateur (identique au login Samba) |
| `password_hash` | Hash Argon2id du mot de passe |
| `role` | `user` = accès à son workspace + commun (pas de paramètres). `admin` = accès à tout + paramètres système |

**Générer un hash :**
```bash
python3 -c "from python.security.auth import hash_password; print(hash_password('MonMotDePasse'))"
```

## 12.5. Contact support

En cas de problème non résolu par ce guide :

1. Collecter les logs : `cd /opt/korev-evidence/deploy && docker compose logs --tail=500 > /tmp/evidence-logs.txt`
2. Collecter les infos système : `docker info > /tmp/docker-info.txt`
3. Noter le symptôme exact et les étapes pour le reproduire
4. Transmettre au donneur d'ordre

---

**Document rédigé le 2026-02-09, mis à jour le 2026-03-31 — KOREV Evidence v3.0**
**Classification : CONFIDENTIEL — Prestataires uniquement**

**Changelog v3.0 (2026-03-31) :**
- Isolation multi-tenant par organisation (organization_uuid canonical, normalisation case-insensitive)
- 12 agents spécialisés (ajout : legal_drafting_guarded, hacker)
- Pipeline rédaction contractuelle (Act Leak Guard, Gate fail-closed, templates CP/CG + 6 annexes)
- Pipeline stratégique v2.0 (4 agents + consolidation LLM dynamique, export PDF automatique)
- Protocole A2A (Agent-to-Agent) : serveur + client FastA2A
- Système de notifications scoppées par utilisateur/organisation
- Scheduler de tâches programmées (fail-closed sur tâches non scoppées)
- Chat rename par les utilisateurs
- Backup/Restore natif (APIs complètes)
- Observabilité : logs JSON structurés, métriques, smoke tests post-déploiement
- Speech : Whisper (transcription) + Kokoro TTS (synthèse vocale)
- Ancrage temporel (date du jour injectée dans tous les prompts agents)
- 2768 tests automatisés (137 fichiers de tests)
- Deterministic Router v2 (routage policy-driven, anti-injection, 40+ keywords board-level)

**Changelog v2.1 :**
- Accès aux paramètres système réservé au rôle `admin` (frontend + backend 403)
- Documentation des rôles mise à jour (user vs admin)

**Changelog v2.0 :**
- Ajout du système multi-utilisateurs (`users.json`, `UserManager`, `WorkspaceManager`)
- Ajout du partage SMB (container Samba) pour les dossiers par utilisateur
- Ajout de l'isolation stricte des workspaces (audit trail, protection path traversal)
- Ajout des lecteurs réseau (M:\ personnel, N:\ commun) sur les postes Windows
- Ajout du script PowerShell de déploiement automatisé (`deploy_evidence_workstation.ps1`)
- Grille de validation étendue (17 tests au lieu de 10)
- Suite de tests automatisés

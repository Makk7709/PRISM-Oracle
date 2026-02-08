# Manuel d'Installation KOREV Evidence

## Guide Client - Version 3.0

---

# Table des matières

1. [Introduction](#1-introduction)
2. [Prérequis système](#2-prérequis-système)
3. [Méthode Recommandée : Docker (One-Click)](#3-méthode-recommandée--docker-one-click)
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
- Répondre à vos questions complexes
- Automatiser certaines tâches

## Deux méthodes d'installation

| Méthode | Recommandée | Temps estimé | Difficulté |
|---------|:-----------:|:------------:|:----------:|
| **Docker** (One-Click) | Oui | 10-20 min | Facile |
| **Locale** (Python) | Alternative | 15-25 min | Intermédiaire |

> **Nous recommandons Docker** : installation plus simple, plus fiable, et identique sur tous les systèmes.

---

# 2. Prérequis système

## Configuration minimale

| Composant | Windows | Mac |
|-----------|---------|-----|
| **Système** | Windows 10/11 (64-bit) | macOS 11 (Big Sur) ou plus récent |
| **RAM** | 8 Go minimum (16 Go recommandé) | 8 Go minimum |
| **Stockage** | 10 Go disponibles | 10 Go disponibles |
| **Connexion** | Internet haut débit | Internet haut débit |

## Logiciel requis

| Méthode | Logiciel |
|---------|----------|
| **Docker** | Docker Desktop (gratuit) |
| **Locale** | Python 3.11+ (gratuit) |

---

# 3. Méthode Recommandée : Docker (One-Click)

## Étape 1 : Installer Docker Desktop

### 1.1 Télécharger Docker Desktop

1. Ouvrez votre navigateur web
2. Allez sur : **https://www.docker.com/products/docker-desktop/**
3. Cliquez sur le bouton de téléchargement correspondant à votre système

### 1.2 Installer Docker Desktop

**Sur Windows :**
1. Double-cliquez sur le fichier téléchargé
2. Suivez l'assistant d'installation (options par défaut)
3. Redémarrez l'ordinateur si demandé

**Sur Mac :**
1. Ouvrez le fichier `.dmg` téléchargé
2. Glissez Docker dans le dossier Applications
3. Lancez Docker Desktop depuis Applications

### 1.3 Démarrer Docker Desktop

1. Lancez Docker Desktop
2. Attendez que l'icône Docker (baleine) apparaisse dans la barre de tâches
3. Attendez que le statut indique **"Docker Desktop is running"**

> **Important macOS :** Dans Docker Desktop → Settings → Advanced, activez **"Allow the default Docker socket to be used"**.

---

## Étape 2 : Copier les fichiers Evidence

### 2.1 Récupérer les fichiers

Vous avez reçu un dossier nommé `korev-evidence` (sur clé USB ou par téléchargement).

1. Copiez ce dossier sur votre ordinateur
2. **Emplacement recommandé** :
   - Windows : `C:\Users\VotreNom\Documents\korev-evidence`
   - Mac : `~/Documents/korev-evidence`

> ⚠️ **Évitez** les emplacements avec des espaces ou caractères spéciaux.

### 2.2 Structure du dossier

Vérifiez que le dossier contient :

```
korev-evidence/
├── scripts/
│   ├── deploy-docker.sh       ← Script Docker (Mac/Linux)
│   ├── deploy-docker.bat      ← Script Docker (Windows)
│   ├── install-mac.sh         ← Script local (Mac/Linux)
│   └── install-windows.bat    ← Script local (Windows)
├── docker/
│   └── run/
│       └── docker-compose.yml
├── DockerfileLocal
├── webui/
├── python/
├── .env.example
├── requirements.txt
└── run_ui.py
```

---

## Étape 3 : Configurer le fichier .env

### 3.1 Préparer la configuration

1. Ouvrez le dossier `korev-evidence`
2. Trouvez le fichier `.env.example`
3. **Copiez-le** et renommez la copie en `.env`

   > **Si vous ne voyez pas le fichier** :
   > - Windows : Dans l'Explorateur → Affichage → Éléments masqués
   > - Mac : Appuyez sur **Cmd + Shift + .** (point)

### 3.2 Modifier le fichier .env

1. Ouvrez `.env` avec un éditeur de texte (Bloc-notes, TextEdit)
2. Remplissez votre clé API :

```
API_KEY_OPENROUTER=votre-cle-openrouter-ici
```

3. Enregistrez le fichier

> La section [Configuration initiale](#5-configuration-initiale) explique comment obtenir cette clé.

---

## Étape 4 : Lancer l'installation Docker

### Sur Windows

1. **Vérifiez** que Docker Desktop est lancé (icône baleine visible)
2. Ouvrez le dossier `korev-evidence/scripts`
3. **Double-cliquez** sur `deploy-docker.bat`
4. Suivez les instructions à l'écran
5. Evidence s'ouvre automatiquement sur **http://localhost:50080**

### Sur Mac / Linux

1. **Vérifiez** que Docker Desktop est lancé
2. Ouvrez le **Terminal**
3. Tapez les commandes suivantes :

```bash
cd ~/Documents/korev-evidence/scripts
chmod +x deploy-docker.sh
./deploy-docker.sh
```

4. Suivez les instructions à l'écran
5. Evidence s'ouvre automatiquement sur **http://localhost:50080**

### Résultat attendu

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       KOREV EVIDENCE — Installation Terminee                  ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║   Acces:  http://localhost:50080                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

> **Durée** : La première installation prend 10-20 minutes (téléchargement de l'image de base). Les lancements suivants seront quasi-instantanés.

---

# 4. Méthode Alternative : Installation locale

> Cette méthode est une alternative si vous ne souhaitez pas utiliser Docker.

## Étape 1 : Installer Python

### Sur Windows

1. Allez sur **https://www.python.org/downloads/**
2. Téléchargez Python 3.12.x
3. **⚠️ TRÈS IMPORTANT** : Cochez **"Add Python to PATH"**
4. Cliquez sur "Install Now"

### Sur Mac

Python est souvent pré-installé. Vérifiez :
```bash
python3 --version
```
Si absent : `brew install python@3.11`

## Étape 2 : Lancer l'installation

### Sur Windows
1. Ouvrez `korev-evidence/scripts`
2. Double-cliquez sur `install-windows.bat`
3. Attendez (~10-15 min)
4. Evidence s'ouvre sur **http://localhost:5050**

### Sur Mac / Linux
```bash
cd ~/Documents/korev-evidence/scripts
chmod +x install-mac.sh
./install-mac.sh
```

---

# 5. Configuration initiale

## Obtenir les clés API

Evidence utilise **OpenRouter** comme fournisseur principal pour accéder à tous les modèles IA.

### Clé OpenRouter (REQUISE)

1. Allez sur **https://openrouter.ai/**
2. Créez un compte ou connectez-vous
3. Allez dans **Keys** (menu en haut)
4. Cliquez sur **"Create Key"**
5. Copiez la clé
6. Collez-la dans `.env` :
   ```
   API_KEY_OPENROUTER=votre-cle-ici
   ```

### Génération d'image (OPTIONNEL)

Pour la génération d'images avec DALL-E 3 :
1. La clé OpenAI sera fournie séparément par Korev
2. Elle se configure dans **Paramètres → Génération d'image**

---

# 6. Premier lancement

## Accéder à Evidence

1. Ouvrez votre navigateur web
2. Tapez l'adresse correspondant à votre installation :

| Méthode | URL |
|---------|-----|
| Docker | **http://localhost:50080** |
| Locale | **http://localhost:5050** |

3. Appuyez sur Entrée

## Écran d'accueil

Vous devriez voir l'interface **KOREV Evidence** avec :
- Le logo et le titre "KOREV Evidence"
- Un champ pour taper vos questions
- Le design avec la typographie Playfair Display

## Premier test

Tapez une question :
```
Bonjour, peux-tu te présenter ?
```

Evidence devrait répondre en quelques secondes.

---

# 7. Utilisation quotidienne

## Démarrer Evidence

### Mode Docker (recommandé)

**Windows :**
- Lancez Docker Desktop
- Double-cliquez sur `scripts/deploy-docker.bat`

**Ou manuellement :**
```bash
docker start korev-evidence
```
Accès sur **http://localhost:50080**

**Mac / Linux :**
```bash
docker start korev-evidence
```
Accès sur **http://localhost:50080**

### Mode Local

**Windows :**
```cmd
cd korev-evidence
venv\Scripts\activate
python run_ui.py
```

**Mac / Linux :**
```bash
cd korev-evidence
source venv/bin/activate
python run_ui.py
```

## Arrêter Evidence

### Docker
```bash
docker stop korev-evidence
```

### Local
- Fermez la fenêtre du terminal
- Ou appuyez sur **Ctrl + C**

---

# 8. Mise à jour

### Mode Docker
```bash
# Arrêter et reconstruire
docker stop korev-evidence
docker rm korev-evidence
cd korev-evidence
docker build -f DockerfileLocal -t korev-evidence:local .
cd docker/run && docker compose up -d
```

### Mode Local

**Windows :** Double-cliquez sur `scripts/update-windows.bat`

**Mac / Linux :**
```bash
cd korev-evidence
source venv/bin/activate
pip install -r requirements.txt --upgrade
pip install -r requirements2.txt --upgrade
```

---

# 9. Dépannage

## Problèmes Docker

### "Docker Desktop n'est pas lancé"

**Solution :**
1. Lancez Docker Desktop
2. Attendez que l'icône baleine soit verte
3. Relancez le script `deploy-docker`

### "Port 50080 déjà utilisé"

**Solution :**
```bash
EVIDENCE_PORT=50081 ./scripts/deploy-docker.sh
```

### Le container ne démarre pas

**Solution :**
```bash
# Voir les logs
docker logs korev-evidence

# Reconstruire
docker build -f DockerfileLocal -t korev-evidence:local .
```

## Problèmes Installation Locale

### "Python n'est pas reconnu" (Windows)

**Solution :**
1. Désinstallez Python
2. Réinstallez en cochant **"Add Python to PATH"**
3. Redémarrez l'ordinateur

### "Module not found"

**Solution :**
```bash
pip install -r requirements.txt
pip install -r requirements2.txt
```

### "Port 5050 déjà utilisé"

**Solution :**
Modifiez le port dans `.env` :
```
WEB_UI_PORT=5051
```

### "Erreur de clé API"

**Solution :**
1. Vérifiez que la clé est correcte dans `.env`
2. Pas d'espaces avant/après la clé
3. Vérifiez votre crédit sur le compte API

### "La page ne charge pas"

**Solution :**
1. Vérifiez que le terminal affiche "Running on http://..."
2. Attendez 30 secondes après le lancement
3. Essayez http://127.0.0.1:50080 (Docker) ou http://127.0.0.1:5050 (local)

---

# 10. Support technique

## Informations à fournir

En cas de problème :
1. Système d'exploitation et version
2. Méthode d'installation (Docker ou locale)
3. Message d'erreur exact
4. Capture d'écran

## Contact

- **Email** : support@korev.ai

---

*Document mis à jour le 8 février 2026*
*Version : 3.0*
*KOREV Evidence - Guide d'installation client*

# Manuel d'Installation Korev Oracle

## Guide Client - Version 1.0

---

# Table des matières

1. [Introduction](#1-introduction)
2. [Prérequis système](#2-prérequis-système)
3. [Installation sur Windows](#3-installation-sur-windows)
4. [Installation sur Mac](#4-installation-sur-mac)
5. [Configuration initiale](#5-configuration-initiale)
6. [Premier lancement](#6-premier-lancement)
7. [Utilisation quotidienne](#7-utilisation-quotidienne)
8. [Dépannage](#8-dépannage)
9. [Support technique](#9-support-technique)

---

# 1. Introduction

## Qu'est-ce que Korev Oracle ?

Korev Oracle est un assistant IA avancé conçu pour vous aider dans vos tâches quotidiennes. Il peut :
- Rechercher des informations scientifiques et académiques
- Analyser des documents PDF
- Répondre à vos questions complexes
- Automatiser certaines tâches

## Durée d'installation

| Système | Temps estimé |
|---------|--------------|
| Windows | 20-30 minutes |
| Mac | 15-20 minutes |

> **Note** : La première installation prend plus de temps car elle télécharge les composants nécessaires (~4-5 Go).

---

# 2. Prérequis système

## Configuration minimale

| Composant | Windows | Mac |
|-----------|---------|-----|
| **Système** | Windows 10/11 (64-bit) | macOS 11 (Big Sur) ou plus récent |
| **RAM** | 8 Go minimum (16 Go recommandé) | 8 Go minimum |
| **Stockage** | 10 Go disponibles | 10 Go disponibles |
| **Connexion** | Internet haut débit | Internet haut débit |

## Logiciels requis

- **Docker Desktop** (gratuit) - sera installé pendant le processus

---

# 3. Installation sur Windows

## Étape 1 : Installer Docker Desktop

### 1.1 Télécharger Docker Desktop

1. Ouvrez votre navigateur web
2. Allez sur : **https://www.docker.com/products/docker-desktop/**
3. Cliquez sur le bouton **"Download for Windows"**

![Téléchargement Docker](https://docs.docker.com/desktop/images/download-docker-desktop.png)

### 1.2 Installer Docker Desktop

1. Double-cliquez sur le fichier téléchargé `Docker Desktop Installer.exe`
2. **IMPORTANT** : Cochez l'option **"Use WSL 2 instead of Hyper-V"**
   
   ```
   ☑ Use WSL 2 instead of Hyper-V (recommended)
   ☑ Add shortcut to desktop
   ```

3. Cliquez sur **"Ok"** puis **"Install"**
4. Attendez la fin de l'installation (5-10 minutes)
5. Cliquez sur **"Close and restart"**

> ⚠️ **Votre ordinateur va redémarrer automatiquement**

### 1.3 Finaliser l'installation Docker

1. Après le redémarrage, Docker Desktop se lance automatiquement
2. Acceptez les conditions d'utilisation
3. **Attendez que l'icône Docker devienne verte** dans la barre des tâches (en bas à droite)
   
   - 🟡 Jaune/Orange = Docker démarre (patientez)
   - 🟢 Vert = Docker est prêt

> **Temps d'attente** : 2-5 minutes au premier démarrage

---

## Étape 2 : Copier les fichiers Oracle

### 2.1 Récupérer les fichiers

Vous avez reçu un dossier nommé `korev-oracle` (sur clé USB ou par téléchargement).

1. Copiez ce dossier sur votre ordinateur
2. **Emplacement recommandé** : `C:\Users\VotreNom\Documents\korev-oracle`

> ⚠️ **Évitez** les emplacements avec des espaces ou caractères spéciaux dans le chemin.

### 2.2 Structure du dossier

Vérifiez que le dossier contient bien ces éléments :

```
korev-oracle/
├── docker/
│   └── run/
│       └── docker-compose.yml
├── scripts/
│   ├── install-windows.bat
│   └── install-windows.ps1
├── .env                    ← Fichier de configuration
└── ...
```

---

## Étape 3 : Configurer Oracle

### 3.1 Configurer le fichier .env

1. Ouvrez le dossier `korev-oracle`
2. Trouvez le fichier `.env`
   
   > **Si vous ne voyez pas le fichier .env** : Dans l'Explorateur Windows, cliquez sur "Affichage" → cochez "Éléments masqués"

3. Ouvrez le fichier avec le **Bloc-notes** (clic droit → Ouvrir avec → Bloc-notes)

4. Remplissez vos clés API :

```
API_KEY_OPENAI=sk-votre-cle-ici
API_KEY_OPENROUTER=sk-votre-cle-ici
```

5. Enregistrez le fichier (Ctrl + S)

> **Où obtenir les clés API ?** Voir la section [5. Configuration initiale](#5-configuration-initiale)

---

## Étape 4 : Lancer l'installation

### 4.1 Méthode simple (recommandée)

1. Ouvrez le dossier `korev-oracle/scripts`
2. **Double-cliquez** sur `install-windows.bat`
3. Une fenêtre noire s'ouvre avec le processus d'installation
4. Attendez le message **"INSTALLATION TERMINÉE"**
5. Tapez `o` et appuyez sur Entrée pour ouvrir Oracle dans votre navigateur

### 4.2 Résultat attendu

```
╔═══════════════════════════════════════════════════════════════╗
║           ✓ INSTALLATION TERMINÉE                             ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Oracle est accessible sur:                                   ║
║  → http://localhost:50080                                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

# 4. Installation sur Mac

## Étape 1 : Installer Docker Desktop

### 1.1 Télécharger Docker Desktop

1. Ouvrez Safari ou Chrome
2. Allez sur : **https://www.docker.com/products/docker-desktop/**
3. Cliquez sur **"Download for Mac"**
4. Choisissez la version correspondant à votre Mac :
   - **Apple Silicon** (M1, M2, M3) - Mac récents depuis 2020
   - **Intel** - Mac plus anciens

> **Comment savoir ?** Cliquez sur le menu Apple (🍎) → "À propos de ce Mac" → regardez "Puce" ou "Processeur"

### 1.2 Installer Docker Desktop

1. Ouvrez le fichier téléchargé `Docker.dmg`
2. Glissez l'icône Docker vers le dossier Applications
3. Ouvrez Docker depuis le dossier Applications
4. Cliquez sur **"Ouvrir"** si macOS demande confirmation
5. Entrez votre mot de passe administrateur si demandé
6. Acceptez les conditions d'utilisation

### 1.3 Vérifier que Docker fonctionne

1. Regardez dans la barre de menus (en haut à droite)
2. Vous devez voir l'icône Docker (une baleine 🐳)
3. Cliquez dessus → doit afficher **"Docker Desktop is running"**

---

## Étape 2 : Copier les fichiers Oracle

### 2.1 Récupérer les fichiers

1. Copiez le dossier `korev-oracle` sur votre Mac
2. **Emplacement recommandé** : `/Users/VotreNom/Documents/korev-oracle`

### 2.2 Vérifier la structure

Ouvrez le Finder et vérifiez que le dossier contient :
- Un dossier `docker/`
- Un dossier `scripts/`
- Un fichier `.env`

---

## Étape 3 : Configurer Oracle

### 3.1 Afficher les fichiers cachés

Le fichier `.env` est masqué par défaut. Pour l'afficher :

1. Ouvrez le dossier `korev-oracle` dans le Finder
2. Appuyez sur **Cmd + Shift + .** (point)
3. Les fichiers cachés apparaissent (légèrement transparents)

### 3.2 Modifier le fichier .env

1. Faites un clic droit sur `.env`
2. Choisissez **"Ouvrir avec"** → **"TextEdit"**
3. Remplissez vos clés API :

```
API_KEY_OPENAI=sk-votre-cle-ici
API_KEY_OPENROUTER=sk-votre-cle-ici
```

4. Enregistrez (Cmd + S)

---

## Étape 4 : Lancer l'installation

### 4.1 Ouvrir le Terminal

1. Appuyez sur **Cmd + Espace** (Spotlight)
2. Tapez **"Terminal"**
3. Appuyez sur Entrée

### 4.2 Lancer le script d'installation

Copiez et collez ces commandes dans le Terminal :

```bash
cd ~/Documents/korev-oracle/scripts
chmod +x install-mac.sh
./install-mac.sh
```

> **Adaptez le chemin** si vous avez mis le dossier ailleurs que dans Documents.

### 4.3 Suivre l'installation

Le script affiche sa progression :
```
[1/5] Vérification de Docker...          ✅
[2/5] Vérification de docker-compose...  ✅
[3/5] Téléchargement de l'image...       ✅
[4/5] Vérification du fichier .env...    ✅
[5/5] Lancement d'Oracle...              ✅
```

---

# 5. Configuration initiale

## Obtenir les clés API

Oracle a besoin d'au moins **une clé API** pour fonctionner.

### Option A : OpenAI (recommandé)

1. Allez sur **https://platform.openai.com/**
2. Créez un compte ou connectez-vous
3. Allez dans **API Keys** (menu de gauche)
4. Cliquez sur **"Create new secret key"**
5. Copiez la clé (commence par `sk-...`)
6. Collez-la dans votre fichier `.env` :
   ```
   API_KEY_OPENAI=sk-votre-cle-copiee
   ```

> ⚠️ **Tarification** : OpenAI facture à l'utilisation. Comptez ~$5-20/mois pour un usage normal.

### Option B : OpenRouter (alternative)

1. Allez sur **https://openrouter.ai/**
2. Créez un compte
3. Allez dans **Keys**
4. Créez une nouvelle clé
5. Collez-la dans `.env` :
   ```
   API_KEY_OPENROUTER=sk-or-votre-cle
   ```

> **Avantage** : OpenRouter permet d'accéder à plusieurs modèles IA avec une seule clé.

---

# 6. Premier lancement

## Accéder à Oracle

1. Ouvrez votre navigateur web (Chrome, Firefox, Safari, Edge)
2. Tapez dans la barre d'adresse : **http://localhost:50080**
3. Appuyez sur Entrée

## Écran d'accueil

Vous devriez voir l'interface de Korev Oracle :

```
┌─────────────────────────────────────────────────┐
│                                                 │
│             🌟 Korev Oracle                     │
│                                                 │
│     Bienvenue ! Comment puis-je vous aider ?   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ Tapez votre question ici...             │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Premier test

Essayez de taper une question simple :
```
Bonjour, est-ce que tu fonctionnes correctement ?
```

Oracle devrait répondre dans les 5-10 secondes.

---

# 7. Utilisation quotidienne

## Démarrer Oracle

### Windows
1. Lancez Docker Desktop (si pas déjà ouvert)
2. Attendez l'icône verte
3. Ouvrez **http://localhost:50080** dans votre navigateur

### Mac
1. Lancez Docker Desktop depuis Applications
2. Attendez que Docker soit prêt
3. Ouvrez **http://localhost:50080** dans votre navigateur

## Arrêter Oracle

### Méthode 1 : Via Docker Desktop
1. Ouvrez Docker Desktop
2. Trouvez le conteneur "korev-oracle"
3. Cliquez sur le bouton Stop (⏹)

### Méthode 2 : Via le Terminal/PowerShell
```bash
docker stop korev-oracle
```

## Redémarrer Oracle

```bash
docker restart korev-oracle
```

---

# 8. Dépannage

## Problèmes courants

### ❌ "La page ne se charge pas"

**Causes possibles :**
1. Docker n'est pas lancé
2. Oracle n'est pas démarré

**Solutions :**
1. Vérifiez que Docker Desktop est ouvert et l'icône est verte
2. Relancez le script d'installation

### ❌ "Docker n'est pas lancé"

**Solution :**
1. Ouvrez Docker Desktop
2. Attendez 2-3 minutes que l'icône devienne verte
3. Relancez le script

### ❌ "Erreur de clé API"

**Solution :**
1. Vérifiez que votre clé API est correcte dans `.env`
2. Assurez-vous qu'il n'y a pas d'espaces avant ou après la clé
3. Vérifiez que votre compte API a du crédit

### ❌ "Port 50080 déjà utilisé"

**Solution Windows :**
```powershell
netstat -ano | findstr :50080
taskkill /PID <numero_affiché> /F
```

**Solution Mac :**
```bash
lsof -i :50080
kill -9 <PID>
```

### ❌ "Téléchargement très lent"

C'est normal lors de la première installation. L'image Docker fait ~2-3 Go.
- Utilisez une connexion filaire si possible
- Évitez les heures de pointe

---

## Réinitialisation complète

Si rien ne fonctionne, réinitialisez tout :

### Windows (PowerShell en administrateur)
```powershell
docker rm -f korev-oracle
docker rmi korevai/korev-oracle-base:latest
# Puis relancez install-windows.bat
```

### Mac (Terminal)
```bash
docker rm -f korev-oracle
docker rmi korevai/korev-oracle-base:latest
# Puis relancez ./install-mac.sh
```

---

# 9. Support technique

## Informations à fournir

En cas de problème, préparez ces informations :

1. **Système d'exploitation** : Windows 10/11 ou macOS (version)
2. **Message d'erreur** : Copiez le texte exact
3. **Logs Docker** : 
   ```bash
   docker logs korev-oracle > logs.txt
   ```
4. **Captures d'écran** si possible

## Contact

- **Email** : support@korev.ai
- **Documentation** : https://docs.korev.ai

---

## Annexe : Commandes utiles

| Action | Commande |
|--------|----------|
| Voir les logs | `docker logs -f korev-oracle` |
| Arrêter Oracle | `docker stop korev-oracle` |
| Démarrer Oracle | `docker start korev-oracle` |
| Redémarrer | `docker restart korev-oracle` |
| Statut | `docker ps` |
| Version Docker | `docker --version` |

---

*Document généré le 24 janvier 2026*
*Version : 1.0*
*Korev Oracle - Guide d'installation client*

# Manuel d'Installation Korev Evidence

## Guide Client - Version 2.0

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

## Qu'est-ce que Korev Evidence ?

Korev Evidence est un assistant IA avancé conçu pour vous aider dans vos tâches quotidiennes. Il peut :
- Rechercher des informations scientifiques et académiques
- Analyser des documents PDF
- Répondre à vos questions complexes
- Automatiser certaines tâches

## Durée d'installation

| Système | Temps estimé |
|---------|--------------|
| Windows | 15-25 minutes |
| Mac | 10-20 minutes |

> **Note** : La première installation télécharge les dépendances Python (~1-2 Go).

---

# 2. Prérequis système

## Configuration minimale

| Composant | Windows | Mac |
|-----------|---------|-----|
| **Système** | Windows 10/11 (64-bit) | macOS 11 (Big Sur) ou plus récent |
| **RAM** | 8 Go minimum (16 Go recommandé) | 8 Go minimum |
| **Stockage** | 5 Go disponibles | 5 Go disponibles |
| **Connexion** | Internet haut débit | Internet haut débit |

## Logiciels requis

- **Python 3.11+** (gratuit) - sera installé pendant le processus

---

# 3. Installation sur Windows

## Étape 1 : Installer Python

### 1.1 Télécharger Python

1. Ouvrez votre navigateur web
2. Allez sur : **https://www.python.org/downloads/**
3. Cliquez sur le bouton **"Download Python 3.12.x"** (ou version récente)

### 1.2 Installer Python

1. Double-cliquez sur le fichier téléchargé
2. **⚠️ TRÈS IMPORTANT** : Cochez la case **"Add Python to PATH"** en bas de la fenêtre
   
   ```
   ☑ Add Python 3.12 to PATH    ← COCHEZ CETTE CASE !
   ```

3. Cliquez sur **"Install Now"**
4. Attendez la fin de l'installation
5. Cliquez sur **"Close"**

### 1.3 Vérifier l'installation

1. Ouvrez le menu Démarrer
2. Tapez **"cmd"** et appuyez sur Entrée
3. Dans la fenêtre noire, tapez :
   ```
   python --version
   ```
4. Vous devez voir : `Python 3.12.x` (ou similaire)

> Si vous voyez une erreur, redémarrez votre ordinateur et réessayez.

---

## Étape 2 : Copier les fichiers Evidence

### 2.1 Récupérer les fichiers

Vous avez reçu un dossier nommé `korev-evidence` (sur clé USB ou par téléchargement).

1. Copiez ce dossier sur votre ordinateur
2. **Emplacement recommandé** : `C:\Users\VotreNom\Documents\korev-evidence`

> ⚠️ **Évitez** les emplacements avec des espaces ou caractères spéciaux.

### 2.2 Structure du dossier

Vérifiez que le dossier contient :

```
korev-evidence/
├── scripts/
│   └── install-windows.bat    ← Script d'installation
├── webui/                      ← Interface web
├── python/                     ← Code Python
├── .env                        ← Configuration
├── requirements.txt
└── run_ui.py
```

---

## Étape 3 : Configurer Evidence

### 3.1 Configurer le fichier .env

1. Ouvrez le dossier `korev-evidence`
2. Trouvez le fichier `.env`
   
   > **Si vous ne voyez pas le fichier .env** : Dans l'Explorateur, cliquez sur "Affichage" → cochez "Éléments masqués"

3. Ouvrez le fichier avec le **Bloc-notes** (clic droit → Ouvrir avec → Bloc-notes)

4. Remplissez vos clés API :

```
API_KEY_OPENAI=sk-votre-cle-ici
```

5. Enregistrez le fichier (Ctrl + S)

---

## Étape 4 : Lancer l'installation

### 4.1 Lancer le script

1. Ouvrez le dossier `korev-evidence/scripts`
2. **Double-cliquez** sur `install-windows.bat`
3. Une fenêtre noire s'ouvre avec le processus d'installation
4. Attendez l'installation des dépendances (5-15 minutes)
5. Evidence s'ouvre automatiquement dans votre navigateur

### 4.2 Résultat attendu

```
╔═══════════════════════════════════════════════════════════════╗
║           ✓ INSTALLATION TERMINEE                             ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Korev Evidence demarre sur:                                    ║
║  → http://localhost:5050                                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

# 4. Installation sur Mac

## Étape 1 : Vérifier Python

### 1.1 Vérifier si Python est installé

1. Ouvrez le **Terminal** (Cmd + Espace, tapez "Terminal")
2. Tapez :
   ```bash
   python3 --version
   ```
3. Si vous voyez `Python 3.10+`, passez à l'étape 2

### 1.2 Installer Python (si nécessaire)

**Option A : Via le site officiel**
1. Allez sur **https://www.python.org/downloads/**
2. Téléchargez la version Mac
3. Installez le .pkg

**Option B : Via Homebrew (recommandé)**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11
```

---

## Étape 2 : Copier les fichiers Evidence

1. Copiez le dossier `korev-evidence` sur votre Mac
2. **Emplacement recommandé** : `~/Documents/korev-evidence`

---

## Étape 3 : Configurer Evidence

### 3.1 Afficher les fichiers cachés

1. Ouvrez le dossier `korev-evidence` dans le Finder
2. Appuyez sur **Cmd + Shift + .** (point)
3. Le fichier `.env` apparaît

### 3.2 Modifier le fichier .env

1. Ouvrez `.env` avec **TextEdit**
2. Ajoutez votre clé API :

```
API_KEY_OPENAI=sk-votre-cle-ici
```

3. Enregistrez (Cmd + S)

---

## Étape 4 : Lancer l'installation

### 4.1 Ouvrir le Terminal

1. Appuyez sur **Cmd + Espace**
2. Tapez **"Terminal"**
3. Appuyez sur Entrée

### 4.2 Lancer le script

```bash
cd ~/Documents/korev-evidence/scripts
chmod +x install-mac.sh
./install-mac.sh
```

### 4.3 Suivre l'installation

Le script affiche sa progression :
```
[1/6] Vérification de Python...         ✅
[2/6] Environnement virtuel...          ✅
[3/6] Installation dépendances...       ✅
[4/6] Vérification configuration...     ✅
[5/6] Installation Playwright...        ✅
[6/6] Lancement de Korev Evidence...      ✅
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
5. Copiez la clé (commence par `sk-or-...`)
6. Collez-la dans `.env` :
   ```
   API_KEY_OPENROUTER=sk-or-votre-cle
   ```

### Génération d'image (OPTIONNEL)

Pour la génération d'images avec DALL-E 3 :
1. La clé OpenAI sera fournie séparément par Korev
2. Elle se configure dans **Paramètres → Génération d'image**

---

# 6. Premier lancement

## Accéder à Evidence

1. Ouvrez votre navigateur web
2. Tapez : **http://localhost:5050**
3. Appuyez sur Entrée

## Écran d'accueil

Vous devriez voir l'interface **Korev Evidence** avec :
- Le logo et le titre "Korev Evidence"
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

### Windows
1. Ouvrez le dossier `korev-evidence`
2. Double-cliquez sur `scripts/install-windows.bat`

**Ou manuellement :**
```cmd
cd korev-evidence
venv\Scripts\activate
python run_ui.py
```

### Mac
```bash
cd ~/Documents/korev-evidence
source venv/bin/activate
python run_ui.py
```

## Arrêter Evidence

- Fermez la fenêtre du terminal
- Ou appuyez sur **Ctrl + C**

---

# 8. Dépannage

## Problèmes courants

### ❌ "Python n'est pas reconnu" (Windows)

**Solution :**
1. Désinstallez Python
2. Réinstallez en cochant **"Add Python to PATH"**
3. Redémarrez l'ordinateur

### ❌ "Module not found"

**Solution :**
```bash
pip install -r requirements.txt
pip install -r requirements2.txt
```

### ❌ "Port 5050 déjà utilisé"

**Solution :**
Modifiez le port dans `.env` :
```
WEB_UI_PORT=5051
```

### ❌ "Erreur de clé API"

**Solution :**
1. Vérifiez que la clé est correcte dans `.env`
2. Pas d'espaces avant/après la clé
3. Vérifiez votre crédit sur le compte API

### ❌ "La page ne charge pas"

**Solution :**
1. Vérifiez que le terminal affiche "Running on http://..."
2. Attendez 30 secondes après le lancement
3. Essayez http://127.0.0.1:5050 au lieu de localhost

---

# 9. Support technique

## Informations à fournir

En cas de problème :
1. Système d'exploitation et version
2. Message d'erreur exact
3. Capture d'écran

## Contact

- **Email** : support@korev.ai

---

*Document généré le 25 janvier 2026*
*Version : 2.0*
*Korev Evidence - Guide d'installation client*

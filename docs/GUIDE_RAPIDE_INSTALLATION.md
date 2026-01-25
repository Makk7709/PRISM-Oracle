# Guide Rapide d'Installation
## Korev Oracle - Version condensée (1 page)

---

## 🖥️ WINDOWS

### Prérequis
- Windows 10/11 (64-bit)
- 8 Go RAM minimum

### Installation en 4 étapes

```
1. PYTHON
   → Télécharger : python.org/downloads
   → Installer en cochant "Add Python to PATH" ⚠️
   → Redémarrer le PC

2. FICHIERS
   → Copier le dossier korev-oracle sur votre PC
   → Emplacement : C:\Users\VotreNom\Documents\korev-oracle

3. CONFIGURATION
   → Ouvrir le fichier .env avec Bloc-notes
   → Ajouter votre clé API :
     API_KEY_OPENAI=sk-votre-cle-ici

4. LANCEMENT
   → Double-cliquer sur scripts/install-windows.bat
   → Attendre l'installation (~10 min la 1ère fois)
   → Oracle s'ouvre sur http://localhost:5050
```

---

## 🍎 MAC

### Prérequis
- macOS 11+ (Big Sur)
- 8 Go RAM minimum

### Installation en 4 étapes

```
1. PYTHON (vérifier)
   → Terminal : python3 --version
   → Si absent : brew install python@3.11

2. FICHIERS
   → Copier le dossier korev-oracle
   → Emplacement : ~/Documents/korev-oracle

3. CONFIGURATION
   → Cmd+Shift+. pour voir fichiers cachés
   → Ouvrir .env avec TextEdit
   → Ajouter votre clé API :
     API_KEY_OPENAI=sk-votre-cle-ici

4. LANCEMENT (Terminal)
   → cd ~/Documents/korev-oracle/scripts
   → chmod +x install-mac.sh
   → ./install-mac.sh
   → Oracle s'ouvre sur http://localhost:5050
```

---

## 🔑 Clés API

| Provider | URL | Variable |
|----------|-----|----------|
| OpenAI | platform.openai.com | `API_KEY_OPENAI=sk-...` |
| OpenRouter | openrouter.ai | `API_KEY_OPENROUTER=sk-or-...` |

---

## 📋 Commandes de relancement

### Windows
```cmd
cd korev-oracle
venv\Scripts\activate
python run_ui.py
```

### Mac/Linux
```bash
cd korev-oracle
source venv/bin/activate
python run_ui.py
```

---

## ❓ Problèmes fréquents

| Problème | Solution |
|----------|----------|
| "Python non reconnu" | Réinstaller Python avec "Add to PATH" coché |
| "Module not found" | `pip install -r requirements.txt` |
| Port 5050 occupé | Changer WEB_UI_PORT=5051 dans .env |
| Page ne charge pas | Attendre 30s, essayer http://127.0.0.1:5050 |

---

## 📞 Support

- **URL Oracle** : http://localhost:5050
- **Email** : support@korev.ai
- **Documentation** : voir MANUEL_INSTALLATION_CLIENT.md

---

*Korev Oracle - Guide rapide v2.0*

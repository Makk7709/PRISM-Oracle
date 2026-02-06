# Guide d'Installation - Korev Evidence

## Prérequis

### Windows
1. **Python 3.11+** - [Télécharger ici](https://www.python.org/downloads/)
   - ⚠️ **IMPORTANT** : Cochez "Add Python to PATH" lors de l'installation

### macOS
1. **Python 3.11+** - Déjà installé ou via Homebrew :
   ```bash
   brew install python@3.11
   ```

### Linux
1. **Python 3.11+**
   ```bash
   sudo apt install python3.11 python3.11-venv
   ```

---

## Installation Rapide

### Sur Windows

```
1. Ouvrez le dossier "scripts"
2. Double-cliquez sur "install-windows.bat"
3. Attendez l'installation des dépendances
4. Evidence s'ouvre automatiquement sur http://localhost:5050
```

### Sur macOS / Linux

```bash
cd /chemin/vers/korev-evidence/scripts
chmod +x install-mac.sh
./install-mac.sh
```

---

## Configuration

### Fichier .env

Le fichier `.env` à la racine contient la configuration. Ajoutez au moins une clé API :

```env
# Clés API (au moins une obligatoire)
API_KEY_OPENAI=sk-votre-cle-openai
API_KEY_OPENROUTER=sk-votre-cle-openrouter

# Configuration
WEB_UI_PORT=5050
DEFAULT_USER_TIMEZONE=Europe/Paris
```

---

## Mise à jour

### Windows
```
Double-cliquez sur scripts/update-windows.bat
```

### macOS / Linux
```bash
cd korev-evidence
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
pip install -r requirements2.txt --upgrade
```

---

## Lancement manuel

Après l'installation initiale, pour relancer Evidence :

### Windows
```cmd
cd korev-evidence
venv\Scripts\activate
python run_ui.py
```

### macOS / Linux
```bash
cd korev-evidence
source venv/bin/activate
python run_ui.py
```

---

## Accès

Evidence est accessible sur : **http://localhost:5050**

---

## Dépannage

### "Python n'est pas reconnu"
- Windows : Réinstallez Python en cochant "Add Python to PATH"
- Mac : `brew install python@3.11`

### "Module not found"
```bash
pip install -r requirements.txt
pip install -r requirements2.txt
```

### "Port 5050 déjà utilisé"
Changez le port dans `.env` :
```env
WEB_UI_PORT=5051
```

---

## Support

- **Email** : support@korev.ai

# Guide Rapide d'Installation
## Korev Oracle - Version condensée (1 page)

---

## 🖥️ WINDOWS

### Prérequis
- Windows 10/11 (64-bit)
- 8 Go RAM minimum
- 10 Go espace disque

### Installation en 4 étapes

```
1. DOCKER
   → Télécharger : docker.com/products/docker-desktop
   → Installer (cocher "Use WSL 2")
   → Redémarrer le PC
   → Lancer Docker Desktop → attendre icône verte

2. FICHIERS
   → Copier le dossier korev-oracle sur votre PC
   → Emplacement : C:\Users\VotreNom\Documents\korev-oracle

3. CONFIGURATION
   → Ouvrir le fichier .env avec Bloc-notes
   → Ajouter votre clé API :
     API_KEY_OPENAI=sk-votre-cle-ici

4. LANCEMENT
   → Double-cliquer sur scripts/install-windows.bat
   → Attendre "INSTALLATION TERMINÉE"
   → Ouvrir http://localhost:50080
```

---

## 🍎 MAC

### Prérequis
- macOS 11+ (Big Sur)
- 8 Go RAM minimum
- 10 Go espace disque

### Installation en 4 étapes

```
1. DOCKER
   → Télécharger : docker.com/products/docker-desktop
   → Choisir Apple Silicon (M1/M2) ou Intel
   → Installer et lancer
   → Attendre l'icône baleine 🐳 dans la barre de menus

2. FICHIERS
   → Copier le dossier korev-oracle sur votre Mac
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
   → Ouvrir http://localhost:50080
```

---

## 🔑 Clés API

| Provider | URL | Variable |
|----------|-----|----------|
| OpenAI | platform.openai.com | `API_KEY_OPENAI=sk-...` |
| OpenRouter | openrouter.ai | `API_KEY_OPENROUTER=sk-or-...` |

---

## 📋 Commandes utiles

| Action | Commande |
|--------|----------|
| Voir les logs | `docker logs -f korev-oracle` |
| Arrêter | `docker stop korev-oracle` |
| Démarrer | `docker start korev-oracle` |
| Redémarrer | `docker restart korev-oracle` |

---

## ❓ Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Page ne charge pas | Vérifier Docker est lancé (icône verte) |
| Docker non lancé | Ouvrir Docker Desktop, attendre 2-3 min |
| Erreur clé API | Vérifier .env, pas d'espaces autour de la clé |
| Port occupé | `docker rm -f korev-oracle` puis relancer |

---

## 📞 Support

- **URL Oracle** : http://localhost:50080
- **Email** : support@korev.ai
- **Documentation complète** : voir MANUEL_INSTALLATION_CLIENT.md

---

*Korev Oracle - Guide rapide v1.0*

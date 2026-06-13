# Manuel utilisateur — KOREV Evidence

**Version** : v1.3.1 · **Public** : utilisateurs finaux et superviseurs · **Langue** : français

Ce manuel décrit l'utilisation quotidienne de KOREV Evidence : connexion, chat, criticité, planificateur de tâches, fichiers et rôles. Pour l'installation, voir [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md).

---

## Table des matières

1. [Présentation](#1-présentation)
2. [Connexion et compte](#2-connexion-et-compte)
3. [Interface principale](#3-interface-principale)
4. [Conversations (chat)](#4-conversations-chat)
5. [Niveaux de criticité et consensus](#5-niveaux-de-criticité-et-consensus)
6. [Pièces jointes et fichiers](#6-pièces-jointes-et-fichiers)
7. [Planificateur de tâches](#7-planificateur-de-tâches)
8. [Rôles et visibilité (multi-utilisateur)](#8-rôles-et-visibilité-multi-utilisateur)
9. [Notifications et revue humaine](#9-notifications-et-revue-humaine)
10. [Paramètres et préférences](#10-paramètres-et-préférences)
11. [Dépannage rapide](#11-dépannage-rapide)

---

## 1. Présentation

KOREV Evidence est une plateforme d'agents IA conçue pour les secteurs réglementés. Chaque réponse **critique** peut être :

- **contre-vérifiée** par consensus multi-LLM ;
- **signée** cryptographiquement (HMAC/RSA) ;
- **auditée** (chaîne de preuve horodatée).

L'interface web est accessible via navigateur (Chrome, Edge, Firefox). Aucune installation locale n'est requise sur le poste utilisateur en déploiement entreprise.

---

## 2. Connexion et compte

### 2.1 Se connecter

1. Ouvrez l'URL fournie par votre administrateur (ex. `https://www.korev-evidence.com/login`).
2. Saisissez votre **identifiant** et **mot de passe**.
3. Cliquez sur **Se connecter**.

La page de connexion indique que vous pouvez changer votre mot de passe après connexion (icône clé en bas de la barre latérale).

### 2.2 Changer son mot de passe

Disponible en mode **multi-utilisateur** uniquement (comptes définis dans `users.json`).

1. En bas de la barre latérale, cliquez sur l'icône **clé** (à côté de déconnexion).
2. Renseignez :
   - mot de passe actuel ;
   - nouveau mot de passe (minimum **12 caractères**, au moins **une lettre** et **un chiffre**) ;
   - confirmation.
3. Validez.

Le changement est immédiat. Le nouveau hash Argon2id est stocké dans un fichier overlay (`data/users.local.json`) car `users.json` est en lecture seule en production.

> En mode mono-utilisateur (identifiants dans `.env`), seul l'administrateur gère le mot de passe — cette fonctionnalité est désactivée.

### 2.3 Se déconnecter

Cliquez sur l'icône **déconnexion** en bas de la barre latérale. La session est effacée côté serveur.

---

## 3. Interface principale

### 3.1 Barre latérale

| Zone | Contenu |
|------|---------|
| **En-tête** | Logo KOREV Evidence, statut Online |
| **Navigation** | Accueil, Chat, Images |
| **Système** | Mémoire, Projets ; **Paramètres** (admin uniquement) |
| **Conversations** | Liste des chats — sélection, renommage (double-clic), suppression |
| **Tâches** | Aperçu des tâches planifiées (état, accès détail) |
| **Bas** | Préférences (thème, langue), identifiant, clé, déconnexion |

### 3.2 Replier / rouvrir la barre latérale

Le bouton **hamburger** (☰) en haut à gauche replie ou rouvre la barre latérale. Il reste visible même lorsque la barre est repliée.

### 3.3 Zone de chat centrale

- Champ de saisie avec bouton d'envoi.
- Boutons d'action sous le champ :
  - **Pause / Reprendre** l'agent ;
  - **Importer** dans la base de connaissances ;
  - **Fichiers** (navigateur de fichiers) ;
  - **Historique** (JSON du contexte LLM) ;
  - **Contexte** (fenêtre de contexte envoyée au modèle) ;
  - **Nudge** (relance si l'agent est bloqué).

### 3.4 Accueil (dashboard)

La page d'accueil présente l'écosystème KOREV : couche Evidence (cognitive), PRISM (infrastructure), NEXUS.

---

## 4. Conversations (chat)

### 4.1 Créer une conversation

- Cliquez sur **Chat** ou **Nouvelle conversation** dans la navigation.
- Une nouvelle session est créée et apparaît dans la liste **Conversations**.

### 4.2 Envoyer un message

1. Tapez votre message dans le champ central.
2. Optionnel : joignez des fichiers (icône 📎).
3. Appuyez sur Entrée ou cliquez **Envoyer**.

L'agent traite la requête, peut déléguer à des agents spécialisés (juridique, médical, finance, etc.) et affiche sa réponse progressivement.

### 4.3 Gérer les conversations

| Action | Comment |
|--------|---------|
| **Sélectionner** | Cliquer sur un chat dans la liste |
| **Renommer** | Double-clic sur le nom |
| **Supprimer** | Bouton ✕ sur la ligne |
| **Exporter** | Via les outils admin ou API |
| **Réinitialiser** | Remet le contexte à zéro (conserve le chat) |

### 4.4 Indicateurs dans les réponses

Selon le niveau de criticité, vous pouvez voir :

- badges ou sections **consensus** (accord / désaccord des modèles) ;
- tableaux **conformité** et **sources** (traçabilité des affirmations) ;
- bannières **NON VALIDÉE** ou **revue humaine requise** sur les sorties non finalisées.

> Si ces éléments n'apparaissent pas après une mise à jour, videz le cache du navigateur (Cmd+Shift+R).

---

## 5. Niveaux de criticité et consensus

KOREV Evidence classe chaque requête selon trois niveaux (voir [ADR-010](adr/ADR-010-critical-output-doctrine.md)) :

| Niveau | Exemples | Consensus |
|--------|----------|-----------|
| **LEVEL 1** | Définition, résumé simple, calcul | Non requis |
| **LEVEL 2** | Analyse, comparaison, conseil professionnel | Sur demande (« par consensus », « /consensus », « second avis ») |
| **LEVEL 3** | Décision, litige, responsabilité, cas réel critique | **Toujours requis** — fail-closed si échec |

### Ce que cela signifie pour vous

- **LEVEL 1** : réponse directe, rapide.
- **LEVEL 2** : réponse standard ; demandez explicitement un consensus si vous voulez une double vérification.
- **LEVEL 3** : la plateforme bloque ou signale toute sortie non validée — ne vous fiez pas à une réponse non signée pour une décision engageante.

### Demander un consensus (LEVEL 2)

Formulations reconnues : « par consensus », « /consensus », « second avis », « validez en croisé », etc.

---

## 6. Pièces jointes et fichiers

### 6.1 Joindre un fichier au chat

1. Cliquez sur l'icône **📎** à gauche du champ de saisie.
2. Sélectionnez un ou plusieurs fichiers (PDF, images, CSV, HTML, JSON, MD, TXT…).
3. Envoyez votre message — l'agent peut lire et traiter les fichiers joints.

### 6.2 Navigateur de fichiers (bouton Files)

Permet de parcourir, télécharger et supprimer des fichiers dans l'environnement de travail de l'agent.

### 6.3 Lecteur réseau (déploiement entreprise)

En déploiement multi-utilisateur avec Samba, chaque utilisateur dispose d'un lecteur réseau (ex. `M:\`) mappé sur son workspace :

```text
M:\
├── documents/    ← vos fichiers
├── rapports/     ← sorties Evidence
└── tmp/          ← temporaires
```

Voir [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md) § configuration postes Windows.

---

## 7. Planificateur de tâches

Le planificateur permet d'automatiser des requêtes récurrentes (veille, rapports, envoi d'emails…).

### 7.1 Accéder au planificateur

**Paramètres** (admin) → onglet **Task Scheduler** / **Planificateur de tâches**.

La barre latérale affiche aussi un aperçu des tâches dans la section **Tâches**.

### 7.2 Types de tâches

| Type | Description |
|------|-------------|
| **Planifiée (Scheduled)** | Exécution selon une expression cron (ex. chaque lundi 08:00) |
| **Ponctuelle (Ad-hoc)** | Déclenchée manuellement ou par token |
| **Prévue (Planned)** | Liste de dates/heures à exécuter séquentiellement |

### 7.3 États d'une tâche

| État | Signification |
|------|---------------|
| `idle` | En attente de la prochaine exécution |
| `running` | En cours d'exécution |
| `error` | Dernière exécution en échec — **les tâches cron sont réessayées automatiquement** à la prochaine occurrence planifiée (depuis v1.3.1) |
| `disabled` | Désactivée manuellement — ne repart pas seule |

### 7.4 Créer une tâche planifiée

1. Cliquez **Nouvelle tâche**.
2. Renseignez : nom, type **Planifiée**, expression cron (minute, heure, jour, fuseau `Europe/Paris` recommandé).
3. Définissez le **prompt système** et le **prompt utilisateur** (instructions de la tâche).
4. Optionnel : pièces jointes, projet associé, contexte dédié.
5. Enregistrez.

### 7.5 Exécuter manuellement

Sélectionnez une tâche → **Run** / **Exécuter**. Une tâche en `error` est remise en `idle` avant exécution manuelle.

### 7.6 Notifications de fin

À la fin d'une tâche, une notification apparaît :

- **Tâche terminée : {nom}** (succès)
- **Tâche échouée : {nom}** (erreur)

---

## 8. Rôles et visibilité (multi-utilisateur)

### 8.1 Rôles plateforme (`role`)

| Rôle | Droits |
|------|--------|
| `admin` | Accès **Paramètres** système (modèles, MCP, backup…) |
| `user` | Utilisation standard sans paramètres système |

### 8.2 Rôles organisation (`org_role`)

| Rôle | Conversations visibles | Tâches visibles |
|------|------------------------|-----------------|
| **OWNER** | Toutes les conversations de l'organisation | Toutes les tâches de l'organisation |
| **MEMBER** | Uniquement **ses propres** conversations | Uniquement **ses propres** tâches |

> Si vous êtes OWNER et voyez les chats d'un collègue MEMBER, c'est le **comportement prévu** (supervision), pas une faille. Les utilisateurs d'une **autre organisation** ne voient rien de votre organisation.

### 8.3 Rôles conformité (`compliance_role`)

Rôles optionnels : `DPO`, `RSSI`, `COMPLIANCE_OFFICER`. Ils donnent accès aux rapports d'audit, revue humaine, replay et tableau de risques (en plus ou à la place du OWNER selon configuration).

---

## 9. Notifications et revue humaine

### 9.1 Cloche de notifications

L'icône cloche en haut à droite affiche :

- notifications de tâches terminées/échouées ;
- alertes système ;
- demandes de revue.

Cliquez pour ouvrir la liste ; marquez comme lues ou effacez.

### 9.2 Revue humaine

Pour les analyses juridiques ou critiques, une bannière **Validation humaine requise** peut apparaître. Un professionnel habilité (DPO, RSSI, ou rôle conformité) doit valider avant diffusion.

Accès : **Paramètres** → section conformité, ou endpoints dédiés pour les rôles autorisés.

---

## 10. Paramètres et préférences

### 10.1 Préférences (tous utilisateurs)

En bas de la barre latérale → **Préférences** :

- défilement automatique ;
- mode sombre / clair ;
- langue (FR / EN selon déploiement).

### 10.2 Paramètres système (admin uniquement)

Onglets disponibles :

| Onglet | Contenu |
|--------|---------|
| Agent Settings | Modèles LLM, prompts système |
| External Services | Clés API externes |
| MCP/A2A | Serveurs MCP, connexions agent-to-agent |
| Developer | Options développeur |
| Task Scheduler | Planificateur complet |
| Backup & Restore | Sauvegarde et restauration |
| Legal | Mentions légales |

---

## 11. Dépannage rapide

| Problème | Action |
|----------|--------|
| Page blanche après login | Vider le cache (Cmd+Shift+R) ; vérifier que le serveur répond (`/healthz`) |
| Agent bloqué | Bouton **Nudge** ou **Pause/Reprendre** |
| Tableaux conformité absents | Cache navigateur obsolète — rechargement forcé |
| Impossible de changer le mot de passe | Vérifier mode multi-user ; politique 12 car. + lettre + chiffre |
| Tâche bloquée en `error` | Attendre la prochaine occurrence cron (retry auto) ou exécution manuelle |
| Tâche bloquée en `running` > 1 h | Contacter l'ops — récupération automatique après TTL 3600 s |
| Bouton sidebar disparu | Recharger la page — le toggle ☰ doit rester en haut à gauche |

Pour les incidents serveur : [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md). Pour l'usage avancé en anglais : [usage.md](usage.md).

---

*KOREV Evidence v1.3.1 — Korev AI — Document utilisateur. Dernière révision : 2026-06-13.*

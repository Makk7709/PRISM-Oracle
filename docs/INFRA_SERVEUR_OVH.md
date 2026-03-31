# Infrastructure serveur OVH — KOREV Evidence

**Usage** : Reference interne pour les connexions, deploiements et operations serveur.  
**Derniere mise a jour** : 2026-03-31

---

## Acces SSH

| Parametre | Valeur |
|---|---|
| **Nom du VPS** | `vps-f3469e31.vps.ovh.net` |
| **IPv4** | `54.37.226.42` |
| **IPv6** | `2001:41d0:305:2100::1:157a` |
| **Utilisateur** | `ubuntu` |
| **Cle SSH locale** | `~/.ssh/korev_admin_ed25519` |
| **Auth mot de passe** | Desactivee (`PasswordAuthentication no`) |

### Commande de connexion

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42
```

---

## Specs serveur

| Parametre | Valeur |
|---|---|
| **OS** | Ubuntu 24.04.4 LTS (Noble Numbat) |
| **Architecture** | x86_64 |
| **RAM** | 22 Go |
| **Disque** | 193 Go (`/dev/sda1`) |
| **Docker** | 29.2.1 |
| **Docker Compose** | v5.0.2 |

---

## Architecture Docker

### Containers

| Container | Image | Role |
|---|---|---|
| `evidence-backend` | `korev/evidence-backend:1.0.0` | Backend principal (production) |
| `evidence-backend-demo` | `korev/evidence-backend:1.0.0` | Instance demo isolee |
| `evidence-caddy` | `caddy:2-alpine` | Reverse proxy HTTPS (Let's Encrypt) |
| `evidence-samba` | `dperson/samba:amd64` | Partage fichiers (local only, `127.0.0.1:445`) |

### Fichiers deploy

```
/home/ubuntu/PRISM-Oracle/
├── deploy/
│   ├── docker-compose.yml          # Compose principal
│   ├── mcp_config.production.json  # Config MCP production
│   ├── users.json                  # Comptes production
│   └── users.demo.json             # Comptes demo
```

### Volumes Docker

| Volume | Contenu |
|---|---|
| `evidence-data` | Donnees persistantes |
| `evidence-logs` | Logs applicatifs |
| `evidence-audit` | Logs d'audit |
| `evidence-shared` | Fichiers partages (Samba) |
| `evidence-tmp` | Fichiers temporaires (chats, uploads) |
| `evidence-memory` | Bases FAISS (memoire agent) |

---

## Domaine

| | Valeur |
|---|---|
| **Domaine** | `korev-evidence.com` |
| **HTTPS** | Let's Encrypt via Caddy (auto-renew) |
| **Ports exposes** | `80/tcp`, `443/tcp` (Caddy) |

---

## Securite

### Firewall (UFW)

| Regle | Port | Source |
|---|---|---|
| HTTP | `80/tcp` | Anywhere |
| HTTPS | `443/tcp` | Anywhere |
| SSH | `22/tcp` | IPs admin autorisees uniquement |

- Default policy : `deny incoming`
- `fail2ban` actif (jail `sshd`)
- SSH durci : `PermitRootLogin no`, `MaxAuthTries 3`, `AllowUsers ubuntu`, `PubkeyAuthentication yes`

### Ajouter une IP SSH autorisee

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 \
  "sudo ufw allow from <NOUVELLE_IP> to any port 22 proto tcp comment 'Description'"
```

---

## Deploiement

### Procedure standard (git pull + rebuild)

```bash
# 1. Push local
git push origin main

# 2. Pull sur le serveur + rebuild + restart
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 \
  "cd PRISM-Oracle && git stash && git pull origin main && docker compose -f deploy/docker-compose.yml up -d --build"
```

### Commande one-liner depuis le poste local

```bash
git push origin main && ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "cd PRISM-Oracle && git stash && git pull origin main && docker compose -f deploy/docker-compose.yml up -d --build"
```

### Verification post-deploy

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

---

## Operations courantes

### Voir les logs d'un container

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "docker logs evidence-backend --tail 50"
```

### Restart sans rebuild

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "cd PRISM-Oracle && docker compose -f deploy/docker-compose.yml restart evidence-backend"
```

### Executer une commande dans le container

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "docker exec evidence-backend python -c 'print(\"OK\")'"
```

### Espace disque

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "df -h / && echo '---' && docker system df"
```

### Nettoyage Docker (cache build > 48h)

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "docker builder prune --filter until=48h -f && docker image prune -f"
```

### Modifier users.json (production)

```bash
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "nano /home/ubuntu/PRISM-Oracle/deploy/users.json"
# Puis restart :
ssh -i ~/.ssh/korev_admin_ed25519 ubuntu@54.37.226.42 "cd PRISM-Oracle && docker compose -f deploy/docker-compose.yml restart evidence-backend"
```

---

## Git (sur le serveur)

| | Valeur |
|---|---|
| **Repo local** | `/home/ubuntu/PRISM-Oracle` |
| **Remote** | `git@github.com:Makk7709/PRISM-Oracle.git` (SSH) |
| **Deploy key** | `~/.ssh/id_ed25519` (read-only, GitHub ID `145315656`) |

---

## Troubleshooting

### SSH refuse la connexion

1. Verifier que ton IP est autorisee dans UFW (se connecter via console KVM OVH)
2. Ajouter l'IP : `sudo ufw allow from <IP> to any port 22 proto tcp`

### Container pas healthy apres deploy

```bash
docker logs evidence-backend --tail 100
docker inspect evidence-backend --format '{{.State.Health.Status}}'
```

### Fichiers locaux en conflit au git pull

```bash
cd PRISM-Oracle && git stash && git pull origin main
```

### Espace disque plein

```bash
docker builder prune --filter until=48h -f
docker image prune -f
docker volume prune -f
```

# Déploiement Reverse-Proxy TLS — Workflow MediaPipe

Ce guide documente la mise en place d'un reverse-proxy TLS (Nginx ou Caddy) devant
l'application Flask/Gunicorn (`127.0.0.1:5003`) pour un déploiement de production
sécurisé.

---

## Architecture

```
Navigateur ──[HTTPS :443]──> Reverse-Proxy (Nginx/Caddy) ──[HTTP :5003]──> Gunicorn/Flask
                                │
                                ├── Certificat TLS (Let's Encrypt)
                                ├── HSTS, CSP, headers de sécurité
                                └── Rate limiting, buffering
```

---

## Option A : Nginx + Let's Encrypt (certbot)

### 1. Installation

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Configuration Nginx

Créer `/etc/nginx/sites-available/workflow-mediapipe` :

```nginx
# Upstream vers Gunicorn/Flask
upstream workflow_backend {
    server 127.0.0.1:5003 fail_timeout=0;
}

# Redirection HTTP → HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name workflow.example.com;

    # Challenge ACME pour Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# Serveur HTTPS principal
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name workflow.example.com;

    # --- Certificats TLS (gérés par certbot) ---
    ssl_certificate     /etc/letsencrypt/live/workflow.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/workflow.example.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # --- Headers de sécurité ---
    # HSTS (2 ans, inclure les sous-domaines, preload)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none';" always;

    # Protection XSS et sniffing
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # --- Logs ---
    access_log /var/log/nginx/workflow-access.log;
    error_log  /var/log/nginx/workflow-error.log;

    # --- Limites ---
    client_max_body_size 200M;          # Uploads vidéo volumineux
    client_body_timeout 300s;
    proxy_read_timeout 900s;            # Étapes longues (STEP5 tracking)

    # --- Compression ---
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    gzip_min_length 1000;

    # --- Proxy vers Gunicorn ---
    location / {
        proxy_pass http://workflow_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Désactiver le buffering pour le streaming SSE / polling
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Servir les fichiers statiques directement (optionnel, bypass Gunicorn)
    location /static/ {
        alias /opt/workflow_mediapipe/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. Activer le site et obtenir le certificat

```bash
sudo ln -s /etc/nginx/sites-available/workflow-mediapipe /etc/nginx/sites-enabled/
sudo mkdir -p /var/www/certbot

# Test syntaxe
sudo nginx -t

# Obtenir certificat (répondre aux questions interactives)
sudo certbot --nginx -d workflow.example.com

# Renouvellement automatique (déjà configuré par certbot)
sudo systemctl reload nginx
```

### 4. Renouvellement automatique

Certbot installe un timer systemd automatiquement. Vérifier :

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

---

## Option B : Caddy (configuration simplifiée)

Caddy gère automatiquement les certificats Let's Encrypt sans certbot.

### 1. Installation

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### 2. Caddyfile (`/etc/caddy/Caddyfile`)

```caddyfile
workflow.example.com {
    # TLS automatique via Let's Encrypt
    tls admin@example.com

    # Headers de sécurité globaux
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none';"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
    }

    # Proxy vers Gunicorn
    reverse_proxy 127.0.0.1:5003 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        # Timeouts pour les étapes longues
        transport http {
            read_timeout 900s
            write_timeout 900s
        }

        # Pas de buffering pour SSE/polling
        flush_interval -1
    }

    # Servir les fichiers statiques
    handle_path /static/* {
        root * /opt/workflow_mediapipe/static/
        file_server {
            precompressed gzip
        }
    }

    # Logs
    log {
        output file /var/log/caddy/workflow-access.log
        format json
    }
}
```

---

## Démarrage Gunicorn en production

```bash
# Depuis le répertoire du projet
gunicorn -c gunicorn.conf.py wsgi:APP_FLASK
```

Contenu minimal de `gunicorn.conf.py` :

```python
bind = "127.0.0.1:5003"
workers = 4
worker_class = "sync"
threads = 2
timeout = 900
keepalive = 5
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"
```

---

## Vérification post-déploiement

```bash
# Vérifier que le reverse-proxy écoute sur 443
curl -sI https://workflow.example.com/ | head -20

# Vérifier HSTS
curl -sI https://workflow.example.com/ | grep -i strict-transport

# Vérifier absence de worker_token dans le HTML
curl -s https://workflow.example.com/ | grep -o 'worker.token'

# Vérifier que les endpoints protégés rejettent sans token
curl -s -X POST https://workflow.example.com/api/step4/lemonfox_audio \
  -H "Content-Type: application/json" \
  -d '{"project_name":"test","video_name":"test.mp4"}' | jq .

# Qualité SSL (outil externe)
curl -s https://www.ssllabs.com/ssltest/analyze.html?d=workflow.example.com
```

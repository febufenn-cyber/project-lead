#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# LeadGen AI — Oracle Cloud VPS one-shot setup script
# Tested on: Ubuntu 22.04 LTS (ARM / AMD)
#
# Run as root or with sudo:
#   curl -sO https://raw.githubusercontent.com/febufenn-cyber/project-lead/main/deploy/setup.sh
#   chmod +x setup.sh && sudo bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_USER="leadgen"
APP_DIR="/opt/leadgen"
REPO="https://github.com/febufenn-cyber/project-lead.git"
PYTHON="/usr/bin/python3.12"
PG_DB="leadgen"
PG_USER="leadgen"
PG_PASS="$(openssl rand -hex 16)"   # auto-generated strong password

echo "========================================"
echo " LeadGen AI — Server Setup"
echo "========================================"

# ── 1. System packages ──────────────────────────────────────────────────────
echo "[1/9] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    git curl wget unzip \
    nginx \
    python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib \
    redis-server \
    ufw \
    certbot python3-certbot-nginx

# ── 2. Create app user ───────────────────────────────────────────────────────
echo "[2/9] Creating app user '$APP_USER'..."
id "$APP_USER" &>/dev/null || useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER"

# ── 3. PostgreSQL ────────────────────────────────────────────────────────────
echo "[3/9] Setting up PostgreSQL..."
systemctl enable --now postgresql
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'\"" | grep -q 1 || \
    su - postgres -c "psql -c \"CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';\""
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='$PG_DB'\"" | grep -q 1 || \
    su - postgres -c "psql -c \"CREATE DATABASE $PG_DB OWNER $PG_USER;\""
echo "PostgreSQL password for '$PG_USER': $PG_PASS"
echo "SAVE THIS PASSWORD ↑"

# ── 4. Redis ─────────────────────────────────────────────────────────────────
echo "[4/9] Starting Redis..."
systemctl enable --now redis-server

# ── 5. Clone repo ────────────────────────────────────────────────────────────
echo "[5/9] Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 6. Python venv + dependencies ───────────────────────────────────────────
echo "[6/9] Setting up Python virtualenv..."
su - "$APP_USER" -s /bin/bash -c "
    $PYTHON -m venv $APP_DIR/.venv
    $APP_DIR/.venv/bin/pip install --upgrade pip -q
    $APP_DIR/.venv/bin/pip install -r $APP_DIR/backend/requirements.txt -q
"

# ── 7. Write .env ────────────────────────────────────────────────────────────
echo "[7/9] Writing .env (edit this with your real keys)..."
PUBLIC_IP=$(curl -s --max-time 5 http://checkip.amazonaws.com || echo "YOUR_SERVER_IP")

cat > "$APP_DIR/.env" <<EOF
APP_NAME=LeadGen AI
API_PREFIX=/api/v1
DEBUG=false

DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASS}@localhost:5432/${PG_DB}
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ── Fill these in ──
GOOGLE_PLACES_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=

HUNTER_API_KEY=
SNOV_API_KEY=
APOLLO_API_KEY=
CLEARBIT_API_KEY=

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Vertex AI / Gemini
VERTEX_PROJECT_ID=platinum-goods-488817-s0
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-2.5-pro
GOOGLE_APPLICATION_CREDENTIALS=
ENRICHMENT_TIMEOUT=30

PROXY_LIST=
CORS_ORIGINS=http://${PUBLIC_IP},http://localhost:8080
REQUEST_TIMEOUT_SECONDS=20

N8N_WEBHOOK_URL=
YETIFORCE_API_URL=
OPENCLAW_GATEWAY_URL=http://localhost:8000
EOF

chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# ── 8. systemd service ───────────────────────────────────────────────────────
echo "[8/9] Installing systemd service..."
cp "$APP_DIR/deploy/leadgen.service" /etc/systemd/system/leadgen.service
systemctl daemon-reload
systemctl enable leadgen
systemctl restart leadgen
sleep 3
systemctl is-active --quiet leadgen && echo "✅ API service running" || echo "❌ API service failed — check: journalctl -u leadgen -n 50"

# ── 9. Nginx ─────────────────────────────────────────────────────────────────
echo "[9/9] Configuring nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/leadgen
ln -sf /etc/nginx/sites-available/leadgen /etc/nginx/sites-enabled/leadgen
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── Firewall ─────────────────────────────────────────────────────────────────
echo "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           Setup Complete!                            ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Frontend : http://${PUBLIC_IP}                      ║"
echo "║  API docs : http://${PUBLIC_IP}/api/docs             ║"
echo "║  API base : http://${PUBLIC_IP}/api/v1               ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Next steps:                                         ║"
echo "║  1. Edit /opt/leadgen/.env with your API keys        ║"
echo "║  2. sudo systemctl restart leadgen                   ║"
echo "║  3. (Optional) Add a domain + run certbot            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "PostgreSQL credentials:"
echo "  DB: $PG_DB  User: $PG_USER  Password: $PG_PASS"

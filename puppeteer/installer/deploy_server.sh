#!/usr/bin/env bash
# Master of Puppets — Server Deployment Script (Remote Linux)
# Usage: ./deploy_server.sh [hostname]

set -euo pipefail

# --- Defaults ---
SERVER_HOSTNAME="${1:-$(hostname -I | awk '{print $1}')}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Color Helpers ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[Deploy]${NC} $1"; }
log_green() { echo -e "${GREEN}[Deploy]${NC} $1"; }

log "Starting Master of Puppets Server Deployment..."
log "Detected Hostname/IP: ${SERVER_HOSTNAME}"

# 1. Dependency Check
if ! command -v docker &> /dev/null; then
    log "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! docker compose version &> /dev/null; then
    log "Docker Compose not found. Please install the docker-compose-plugin."
    exit 1
fi

# 2. Environment Setup
cd "$PROJECT_ROOT"
if [ ! -f .env ]; then
    log "Creating .env from example..."
    cp .env.example .env
    # Generate secrets if needed
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$(openssl rand -hex 32)/" .env
    sed -i "s/API_KEY=.*/API_KEY=mop_$(openssl rand -hex 16)/" .env
    sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=puppet_$(openssl rand -hex 8)/" .env
fi

# Set SERVER_HOSTNAME in .env so Caddy picks it up
if grep -q "SERVER_HOSTNAME=" .env; then
    sed -i "s|SERVER_HOSTNAME=.*|SERVER_HOSTNAME=${SERVER_HOSTNAME}|" .env
else
    echo "SERVER_HOSTNAME=${SERVER_HOSTNAME}" >> .env
fi

# 3. Pull/Build and Launch
log "Building and launching stack..."
docker compose -f compose.server.yaml up -d --build

# 4. Success & Instructions
log_green "🚀 Master of Puppets Server is running!"
log ""
log "Dashboard: https://${SERVER_HOSTNAME}"
log "Bootstrap (Node Enrollment):"
log "  1. Log in to dashboard"
log "  2. Go to 'Nodes' > 'Generate Join Token'"
log "  3. On a remote node, run:"
log "     curl -sSL http://${SERVER_HOSTNAME}/api/installer.sh | bash"
log ""
log "Note: Caddy may take a moment to generate certificates."
log "If you get SSL errors, visit http://${SERVER_HOSTNAME}/system/root-ca-installer first."

#!/usr/bin/env bash
# Master of Puppets - Universal Installer (v1.0) - Linux/macOS
# Usage:
#   curl -sSL https://server:8001/api/installer.sh | bash -s -- --token "eyJ..."
#   ./install_universal.sh --token "eyJ..." --count 3
#   ./install_universal.sh --platform docker  # Force Docker

set -euo pipefail

# --- Defaults ---
ROLE="node"
TOKEN=""
SERVER_URL="https://localhost:8001"
COUNT=1
PLATFORM=""
TAGS=""

# --- Color Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${CYAN}[Installer]${NC} $1"
}

log_green() {
    echo -e "${GREEN}[Installer]${NC} $1"
}

log_error() {
    echo -e "${RED}[Error]${NC} $1" >&2
    exit 1
}

# --- CA Installation (Hardening) ---
install_ca() {
    if [[ $EUID -ne 0 ]]; then
        log "Warning: Not running as root. Skipping system CA installation."
        return
    fi

    log "Installing Root CA to system trust store..."
    if [[ -f /etc/debian_version ]]; then
        cp bootstrap_ca.crt /usr/local/share/ca-certificates/mop-root.crt
        update-ca-certificates
    elif [[ -f /etc/redhat-release ]]; then
        cp bootstrap_ca.crt /etc/pki/ca-trust/source/anchors/mop-root.crt
        update-ca-trust
    else
        log "Unsupported OS for auto-CA installation. Please install bootstrap_ca.crt manually."
    fi
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --role)
            ROLE="$2"
            shift 2
            ;;
        --token)
            TOKEN="$2"
            shift 2
            ;;
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --count)
            COUNT="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --tags)
            TAGS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# --- Platform Detection ---
HAS_DOCKER=$(command -v docker &>/dev/null && echo 1 || echo 0)
HAS_PODMAN=$(command -v podman &>/dev/null && echo 1 || echo 0)

if [[ -z "$PLATFORM" ]]; then
    # Auto-detect
    if [[ $HAS_DOCKER -eq 0 && $HAS_PODMAN -eq 0 ]]; then
        log_error "Neither Docker nor Podman found. Please install one first."
    elif [[ $HAS_DOCKER -eq 1 && $HAS_PODMAN -eq 1 ]]; then
        echo ""
        echo -e "${YELLOW}Both Docker and Podman detected. Please choose:${NC}"
        echo -e "  ${CYAN}[1] Docker${NC}"
        echo -e "  ${CYAN}[2] Podman${NC}"
        read -p "Select runtime [1/2]: " CHOICE
        if [[ "$CHOICE" == "2" ]]; then
            PLATFORM="podman"
        else
            PLATFORM="docker"
        fi
    elif [[ $HAS_DOCKER -eq 1 ]]; then
        PLATFORM="docker"
        log_green "Auto-detected: Docker"
    else
        PLATFORM="podman"
        log_green "Auto-detected: Podman"
    fi
else
    log "Using specified platform: $PLATFORM"
fi

# Normalize to lowercase
PLATFORM=$(echo "$PLATFORM" | tr '[:upper:]' '[:lower:]')

log "Initializing Universal Installer ($ROLE on $PLATFORM)..."

# --- Validate Platform ---
if [[ "$PLATFORM" == "podman" ]]; then
    if [[ $HAS_PODMAN -eq 0 ]]; then
        log_error "Podman is not installed."
    fi
    # Check for podman-compose
    if ! command -v podman-compose &>/dev/null; then
        log_error "podman-compose is not installed. Install with: pip install podman-compose"
    fi
elif [[ "$PLATFORM" == "docker" ]]; then
    if [[ $HAS_DOCKER -eq 0 ]]; then
        log_error "Docker is not installed."
    fi
    # Check for docker compose (plugin) or docker-compose
    if ! docker compose version &>/dev/null && ! command -v docker-compose &>/dev/null; then
        log_error "Docker Compose is not found (checked 'docker compose' and 'docker-compose')."
    fi
fi

# --- Token Handling (Node Role) ---
if [[ "$ROLE" == "node" ]]; then
    if [[ -z "$TOKEN" ]]; then
        read -p "Enter Join Token: " TOKEN
    fi

    log "Parsing Token..."
    # Decode Base64 token and extract CA
    # NOTE: Use printf '%s' (not echo) to preserve literal \n escape sequences in the CA PEM.
    # The token JSON encodes the CA as a JSON string with \n characters. bash's echo interprets
    # \n as actual newlines, which corrupts the JSON. printf '%s' passes the string verbatim.
    JSON_PAYLOAD=$(echo "$TOKEN" | base64 -d 2>/dev/null || echo "")
    if [[ -z "$JSON_PAYLOAD" ]]; then
        log_error "Invalid Token Format. Ensure you are using a v0.8+ Token."
    fi

    # Extract CA using jq if available, then python3, then grep/sed fallback
    # All branches use printf '%s' to preserve literal \n in the JSON string value.
    if command -v jq &>/dev/null; then
        CA_CONTENT=$(printf '%s' "$JSON_PAYLOAD" | jq -r '.ca // empty')
    elif command -v python3 &>/dev/null; then
        CA_CONTENT=$(printf '%s' "$JSON_PAYLOAD" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('ca',''))" 2>/dev/null || echo "")
    else
        # Last-resort fallback: grep/sed (fragile — only works if JSON has no spaces around colon)
        CA_CONTENT=$(printf '%s' "$JSON_PAYLOAD" | grep -o '"ca": *"[^"]*"' | sed 's/"ca": *"//; s/"$//' | sed 's/\\n/\n/g')
    fi

    if [[ -z "$CA_CONTENT" ]]; then
        log_error "Could not extract CA from token."
    fi

    echo "$CA_CONTENT" > bootstrap_ca.crt
    log_green "✅ Trust Root extracted to bootstrap_ca.crt"
    
    # Try to install CA to system trust store if possible
    install_ca
fi

# --- Fetch Configuration ---
if [[ "$ROLE" == "node" ]]; then
    log "Fetching Node Configuration from ${SERVER_URL}..."
    
    # If we are using a remote hostname, ensure we use the right URL
    if [[ "$SERVER_URL" == *"localhost"* && -n "${SERVER_HOSTNAME:-}" ]]; then
        SERVER_URL="${SERVER_URL/localhost/$SERVER_HOSTNAME}"
        log "Updating Server URL to use SERVER_HOSTNAME: ${SERVER_URL}"
    fi

    COMPOSE_URL="${SERVER_URL}/api/node/compose?token=${TOKEN}&platform=${PLATFORM}"
    if [[ -n "$TAGS" ]]; then
        COMPOSE_URL="${COMPOSE_URL}&tags=${TAGS}"
    fi
    
    curl -sSfL --cacert bootstrap_ca.crt "$COMPOSE_URL" -o node-compose.yaml || \
        curl -sSfLk "$COMPOSE_URL" -o node-compose.yaml  # Fallback insecure if CA fails
    
    log_green "✅ node-compose.yaml downloaded."

    log "Fetching Validation Key..."
    KEY_URL="${SERVER_URL}/verification-key"
    curl -sSfL --cacert bootstrap_ca.crt "$KEY_URL" -o verification.key || \
        curl -sSfLk "$KEY_URL" -o verification.key || echo "Warning: Could not fetch verification key."
    
    if [[ -s verification.key ]]; then
        log_green "✅ Verification Key downloaded."
    fi
elif [[ "$ROLE" == "agent" ]]; then
    log "Agent (Server) deployment not yet fully automated via script (Use git clone + compose)."
    exit 0
fi

# --- Deployment ---
log "Starting Containers (x$COUNT) using $PLATFORM..."

if [[ "$PLATFORM" == "podman" ]]; then
    podman-compose -f node-compose.yaml up -d --scale puppet="$COUNT"
elif [[ "$PLATFORM" == "docker" ]]; then
    # Prefer 'docker compose' (plugin)
    if docker compose version &>/dev/null; then
        docker compose -f node-compose.yaml up -d --scale puppet="$COUNT"
    else
        docker-compose -f node-compose.yaml up -d --scale puppet="$COUNT"
    fi
fi

if [[ $? -eq 0 ]]; then
    log_green "🚀 Deployment Complete!"
    if [[ "$PLATFORM" == "podman" ]]; then
        log "Run 'podman logs -f <container_name>' to view status."
    else
        log "Run 'docker logs -f <container_name>' to view status."
    fi
else
    log_error "Deployment failed."
fi

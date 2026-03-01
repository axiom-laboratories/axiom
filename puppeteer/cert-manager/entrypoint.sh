#!/bin/sh

# Ensure certs directory exists
mkdir -p /etc/certs

# Generate Internal Root CA for mTLS if missing
if [ ! -f /etc/certs/root_ca.crt ]; then
    echo "[cert-manager] Generating Root CA..."
    step certificate create "Puppet Master Root CA" \
        /etc/certs/root_ca.crt /etc/certs/root_ca.key \
        --profile root-ca \
        --no-password --insecure
fi

# Generate Caddy TLS certificate signed by Root CA (if missing or hostname changed)
# SERVER_HOSTNAME can be an IP or FQDN for your closed-network host (e.g. 192.168.1.10)
CADDY_SANS="localhost,127.0.0.1"
if [ -n "$SERVER_HOSTNAME" ]; then
    CADDY_SANS="${CADDY_SANS},${SERVER_HOSTNAME}"
fi

# Rebuild cert if SANs changed
SANS_FILE=/etc/certs/.caddy_sans
if [ ! -f /etc/certs/caddy.crt ] || [ "$(cat "$SANS_FILE" 2>/dev/null)" != "$CADDY_SANS" ]; then
    echo "[cert-manager] Generating Caddy TLS certificate (SANs: ${CADDY_SANS})..."
    # Build --san flags from comma-separated list
    SAN_FLAGS=""
    for SAN in $(echo "$CADDY_SANS" | tr ',' ' '); do
        SAN_FLAGS="$SAN_FLAGS --san $SAN"
    done
    # shellcheck disable=SC2086
    step certificate create "Puppet Master Dashboard" \
        /etc/certs/caddy.crt /etc/certs/caddy.key \
        --profile leaf \
        --ca /etc/certs/root_ca.crt \
        --ca-key /etc/certs/root_ca.key \
        --not-after 8760h \
        --no-password --insecure \
        $SAN_FLAGS
    echo "$CADDY_SANS" > "$SANS_FILE"
    echo "[cert-manager] Caddy TLS certificate generated."
fi

# Bring Caddy to foreground
caddy run --config /etc/caddy/Caddyfile

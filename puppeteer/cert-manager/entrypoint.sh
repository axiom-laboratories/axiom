#!/bin/sh

# Ensure certs directory exists
mkdir -p /etc/certs

# Generate Internal Root CA for mTLS if missing
if [ ! -f /etc/certs/root_ca.crt ]; then
    echo "Generating Internal Root CA..."
    # Create a simple root CA for mTLS client auth
    step certificate create "Puppet Master Root CA" \
        /etc/certs/root_ca.crt /etc/certs/root_ca.key \
        --profile root-ca \
        --no-password --insecure
fi

# Bring Caddy to foreground
caddy run --config /etc/caddy/Caddyfile

FROM docker.io/library/caddy:builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/duckdns \
    --with github.com/caddy-dns/cloudflare

FROM docker.io/library/caddy:alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# Install step-cli for potential future mTLS extensions or debugging
RUN apk add --no-cache curl step-cli

COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /bin/entrypoint.sh
RUN chmod +x /bin/entrypoint.sh

ENTRYPOINT ["/bin/entrypoint.sh"]

FROM python:3.12-slim AS builder
WORKDIR /docs

# Install MkDocs dependencies
COPY docs/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install FastAPI app dependencies (needed for export script to import agent_service)
COPY puppeteer/requirements.txt /tmp/app-requirements.txt
RUN pip install --no-cache-dir -r /tmp/app-requirements.txt

# Copy MkDocs source
COPY docs/ .

# Copy export script and agent_service for OpenAPI generation
COPY puppeteer/scripts/export_openapi.py /tmp/export_openapi.py
COPY puppeteer/agent_service /tmp/agent_service

# Generate openapi.json from FastAPI app (no running server required)
# DATABASE_URL: use postgresql+asyncpg (asyncpg is in requirements, aiosqlite is not)
# ENCRYPTION_KEY: prevents Fernet(key) import-time failure in security.py
# API_KEY: prevents sys.exit(1) in security.py module-level guard
RUN DATABASE_URL=postgresql+asyncpg://dummy:dummy@localhost/dummy \
    ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
    API_KEY=dummy-build-key \
    PYTHONPATH=/tmp \
    python /tmp/export_openapi.py docs/api-reference/openapi.json

# Build MkDocs site (--strict: any warning = build failure)
RUN mkdocs build --strict

FROM nginx:alpine
COPY --from=builder /docs/site /usr/share/nginx/html
COPY docs/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

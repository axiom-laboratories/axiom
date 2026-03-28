# Axiom Licences (private)

Private repository for EE licence issuance tooling and audit records.

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`

## Key Material

`keys/licence.key` is the Ed25519 private signing key. It is chmod 600 and must never be shared or committed outside this repository.

The corresponding public key is embedded in `puppeteer/agent_service/services/licence_service.py` in the main Master of Puppets repository as `_LICENCE_PUBLIC_KEY_PEM`.

## Issuing a Licence

```bash
python tools/issue_licence.py \
  --customer <customer-id> \
  --tier ee \
  --nodes 10 \
  --expiry 2027-01-01 \
  --issued-to "Customer Name" \
  --contact-email customer@example.com \
  --features sso,webhooks
```

Key resolution: the tool reads `AXIOM_LICENCE_SIGNING_KEY` env var (path to the key file) or accepts `--key <path>`. One of these must be set.

GitHub token: `AXIOM_GITHUB_TOKEN` must be set with `contents:write` scope on this repository for the YAML audit record to be committed automatically.

## Air-Gap / Local Mode

Add `--no-remote` to skip the GitHub API commit. The YAML audit record is written to `{customer_id}-{licence_id}.yml` in the current directory and the JWT is printed to stdout:

```bash
python tools/issue_licence.py \
  --key keys/licence.key \
  --customer acme-corp \
  --tier ee \
  --nodes 5 \
  --expiry 2027-01-01 \
  --issued-to "Acme Corp" \
  --no-remote
```

## Listing Issued Licences

```bash
python tools/list_licences.py
```

Reads all `licenses/issued/*.yml` files and prints a table sorted by expiry (soonest first). Add `--json` for machine-readable output.

## Key Rotation

When rotating the signing keypair:

1. Generate a new keypair: update `keys/licence.key` with the new private key.
2. Update `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py` in the main repository.
3. Note: licences signed with the old key will continue to validate until they expire if the previous public key is retained in a `_LEGACY_PUBLIC_KEY_PEM` constant. Decide on the transition window before rotating.

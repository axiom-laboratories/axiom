# Phase 78: CLI Signing UX - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the `AXIOM_URL` env var mismatch in the CLI and add two new subcommands (`key generate` and `init`) so a new user can generate an Ed25519 signing keypair and register it with the server using only `axiom-push` — no openssl ceremony required. Update `first-job.md` to present this as the primary getting-started path. No backend API changes.

</domain>

<decisions>
## Implementation Decisions

### AXIOM_URL fix
- `cli.py` line 51: change `os.getenv("MOP_URL")` → `os.getenv("AXIOM_URL")`
- Keep `--url` flag override as the highest priority (already correct)
- Default fallback stays `http://localhost:8001`

### Key file location
- Keys stored at `~/.axiom/signing.key` (private) and `~/.axiom/verification.key` (public)
- Use `Path.home() / ".axiom"` — works on Windows, macOS, and Linux without additional dependencies
- Migrate `CredentialStore` default path from `~/.mop/credentials.json` → `~/.axiom/credentials.json`
- `key generate` refuses to overwrite existing keys without `--force` flag (warn and exit)
- After generation, print the public key PEM to stdout so users can copy-paste it

### `key generate` subcommand
- New subparser: `axiom-push key generate [--force]`
- Uses `cryptography` lib (already a dependency via `signer.py`) — no openssl required
- Generates Ed25519 keypair, writes PEM files to `~/.axiom/`
- Creates `~/.axiom/` dir if it doesn't exist
- Prints public key PEM to stdout + confirms file paths

### `init` flow design
- New subparser: `axiom-push init`
- Three-step sequence:
  1. **Login**: Check `~/.axiom/credentials.json` — if token exists, print "Already logged in as `<username>`" and skip device flow. Otherwise run full OAuth Device Flow.
  2. **Key generation**: Check if `~/.axiom/signing.key` exists — if yes, print "Keys already exist — using `~/.axiom/signing.key`" and skip generation. Otherwise generate new keypair.
  3. **Register public key**: POST to `/signatures` with `{ name: "<username>@<hostname>", public_key: <PEM> }`. Key name auto-generated using `socket.gethostname()` and the logged-in username from credentials.
- On success, print the registered Key ID and an example `job push` command:
  ```
  Setup complete.
  Key ID: <id>

  Push your first job:
    axiom-push job push --script hello.py --key ~/.axiom/signing.key --key-id <id>
  ```

### Claude's Discretion
- Error handling for network failures during `POST /signatures`
- Whether to add a `--name` flag to `init` to override the auto-generated key name
- Progress output formatting (plain print vs rich/click styling — keep consistent with existing CLI style)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_sdk/signer.py`: `Signer.load_private_key()` and `Signer.sign_payload()` — Ed25519 via `cryptography` lib already in place. Key generation will use the same lib.
- `mop_sdk/auth.py` `CredentialStore`: already handles `~/.mop/` with `Path.home()` — rename dir and reuse pattern.
- `mop_sdk/client.py`: `MOPClient.from_store()` — has `push_signature` or similar; need to confirm `/signatures` POST is wired. If not, add it.
- `cli.py` `do_login()`: existing device flow handler — `init` calls this logic directly.

### Established Patterns
- CLI uses `argparse` with nested subparsers (`job` → `push`/`create`) — `key` → `generate` and top-level `init` follow the same pattern
- Error handling: `except Exception as e: print(f"Error: {e}"); sys.exit(1)` — keep consistent
- `verify_ssl=False` passed throughout — keep for `init`'s server calls

### Integration Points
- `POST /signatures` endpoint: accepts `{ name: str, public_key: str (PEM) }`, returns `{ id, name, public_key, uploaded_by, created_at }` — `init` uses this to register the key and capture the Key ID for display
- `mop_sdk/client.py` needs a `register_signature(name, public_key)` method if not already present

</code_context>

<specifics>
## Specific Ideas

- The `init` output should show the exact `job push` command with real values substituted in — not a template. User should be able to copy-paste it immediately.
- `AXIOM_URL` should appear as the very first line in the first-job.md Quick Start section (`export AXIOM_URL=https://your-host`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 78-cli-signing-ux*
*Context gathered: 2026-03-27*

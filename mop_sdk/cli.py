import argparse
import sys
import logging
import webbrowser
import os
import socket
from pathlib import Path
from .auth import DeviceFlowHandler, CredentialStore
from .client import MOPClient
from cryptography.hazmat.primitives.asymmetric import ed25519 as ed25519_lib
from cryptography.hazmat.primitives import serialization

def main():
    parser = argparse.ArgumentParser(prog="mop-push", description="Master of Puppets (MoP) CLI")
    parser.add_argument("--url", help="Base URL of the MoP control plane")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # login command
    login_parser = subparsers.add_parser("login", help="Authenticate via OAuth Device Flow")

    # job command
    job_parser = subparsers.add_parser("job", help="Manage job definitions")
    job_subparsers = job_parser.add_subparsers(dest="subcommand", help="Job commands")

    # job push
    push_parser = job_subparsers.add_parser("push", help="Sign and push a job definition (DRAFT)")
    push_parser.add_argument("--name", help="Name for new job")
    push_parser.add_argument("--id", help="ID of existing job to update")
    push_parser.add_argument("--script", required=True, help="Path to script file")
    push_parser.add_argument("--key", required=True, help="Path to Ed25519 private key")
    push_parser.add_argument("--key-id", required=True, help="ID of the registered public key")

    # job create
    create_parser = job_subparsers.add_parser("create", help="Create a fully-scheduled ACTIVE job")
    create_parser.add_argument("--name", required=True, help="Name for the job")
    create_parser.add_argument("--script", required=True, help="Path to script file")
    create_parser.add_argument("--key", required=True, help="Path to Ed25519 private key")
    create_parser.add_argument("--key-id", required=True, help="ID of the registered public key")
    create_parser.add_argument("--cron", help="Cron schedule")
    create_parser.add_argument("--tags", help="Comma-separated target tags")

    # key command
    key_parser = subparsers.add_parser("key", help="Manage signing keys")
    key_subparsers = key_parser.add_subparsers(dest="subcommand", help="Key commands")
    generate_parser = key_subparsers.add_parser("generate", help="Generate an Ed25519 signing keypair")
    generate_parser.add_argument("--force", action="store_true", help="Overwrite existing keys")

    # init command
    init_parser = subparsers.add_parser("init", help="Set up login, signing key, and server registration")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Prioritize URL: global arg > env > default
    base_url = args.url or os.getenv("AXIOM_URL") or "http://localhost:8001"

    if args.command == "login":
        do_login(base_url)
    elif args.command == "job":
        do_job(args)
    elif args.command == "key":
        do_key_generate(force=getattr(args, "force", False))
    elif args.command == "init":
        do_init(base_url)
    else:
        parser.print_help()
    sys.stdout.flush()

def do_key_generate(force: bool = False) -> str:
    """Generates an Ed25519 signing keypair in ~/.axiom/. Returns the public key PEM string."""
    axiom_dir = Path.home() / ".axiom"
    priv_path = axiom_dir / "signing.key"
    pub_path = axiom_dir / "verification.key"

    if priv_path.exists() and not force:
        print("Keys already exist at ~/.axiom/signing.key. Use --force to overwrite.")
        sys.exit(1)

    axiom_dir.mkdir(parents=True, exist_ok=True)

    priv = ed25519_lib.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_pem)
    os.chmod(priv_path, 0o600)
    pub_path.write_bytes(pub_pem)
    os.chmod(pub_path, 0o644)

    pub_pem_str = pub_pem.decode("utf-8")
    print(f"Generated keypair:\n  Private key: {priv_path}\n  Public key:  {pub_path}\n")
    print("Public key (copy this to register with the server):")
    print(pub_pem_str)
    return pub_pem_str


def do_init(base_url: str):
    """Idempotent setup: login → key generation → register key → print usage."""
    try:
        # Step 1: Check credentials
        store = CredentialStore()
        creds = store.load()

        if creds and creds.get("access_token"):
            username = creds.get("username", "unknown")
            print(f"Already logged in as {username} — skipping login.")
        else:
            do_login(base_url)
            creds = store.load()
            # Persist username if not already stored
            if creds and not creds.get("username"):
                try:
                    client_tmp = MOPClient(base_url=creds["base_url"], verify_ssl=False)
                    client_tmp.token = creds["access_token"]
                    me = client_tmp.get_me()
                    creds["username"] = me["username"]
                    store.save(creds)
                except Exception:
                    pass  # username is best-effort

        # Step 2: Key generation
        axiom_dir = Path.home() / ".axiom"
        priv_path = axiom_dir / "signing.key"
        pub_path = axiom_dir / "verification.key"

        if priv_path.exists():
            print(f"Keys already exist — using {priv_path}")
            pub_pem = pub_path.read_bytes().decode("utf-8")
        else:
            pub_pem = do_key_generate(force=False)

        # Step 3: Register public key (idempotent — preflight GET first)
        client = MOPClient.from_store(verify_ssl=False)
        hostname = socket.gethostname()
        username = (creds or {}).get("username", "user") if creds else "user"
        key_name = f"{username}@{hostname}"

        existing = client.list_signatures()
        match = next((s for s in existing if s["name"] == key_name), None)
        if match:
            key_id = match["id"]
            print(f"Key '{key_name}' already registered (ID: {key_id}) — skipping registration.")
        else:
            result = client.register_signature(name=key_name, public_key=pub_pem)
            key_id = result["id"]

        # Step 4: Print completion message
        print(f"\nSetup complete.")
        print(f"Key ID: {key_id}")
        print(f"\nPush your first job:")
        print(f"  axiom-push job push --script hello.py --key {priv_path} --key-id {key_id}")

    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def do_job(args):
    from .signer import Signer
    
    try:
        client = MOPClient.from_store(verify_ssl=False)
        
        # Load and sign
        with open(args.script, "r") as f:
            script_content = f.read()
        
        priv_key = Signer.load_private_key(args.key)
        signature = Signer.sign_payload(priv_key, script_content)
        
        if args.subcommand == "push":
            print(f"Pushing job {args.name or args.id}...")
            result = client.push_job(
                script_content=script_content,
                signature=signature,
                signature_id=args.key_id,
                name=args.name,
                id=args.id
            )
            print(f"Successfully pushed job. ID: {result['id']}, Status: {result['status']}")
            
        elif args.subcommand == "create":
            print(f"Creating job {args.name}...")
            tags = args.tags.split(",") if args.tags else None
            result = client.create_job_definition(
                name=args.name,
                script_content=script_content,
                signature=signature,
                signature_id=args.key_id,
                schedule_cron=args.cron,
                target_tags=tags
            )
            print(f"Successfully created job. ID: {result['id']}, Status: {result['status']}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def do_login(base_url: str):
    handler = DeviceFlowHandler(base_url, verify_ssl=False) # Allow self-signed for dev
    try:
        print(f"Initiating login to {base_url}...")
        sys.stdout.flush()
        device_data = handler.start_flow()
        
        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri_complete"]
        
        print("\n" + "="*40)
        print(f"USER CODE: {user_code}")
        sys.stdout.flush()
        print("="*40)
        print(f"\nPlease approve this request in your browser:")
        print(f"{verification_uri}")
        
        if os.getenv("MOP_NO_BROWSER") != "1":
            print("\nAttempting to open browser automatically...")
            webbrowser.open(verification_uri)
        
        print("\nWaiting for approval...")
        token_data = handler.poll_for_token(
            device_data["device_code"],
            device_data["interval"],
            device_data["expires_in"]
        )
        
        if token_data:
            store = CredentialStore()
            creds = {
                "base_url": base_url,
                "access_token": token_data["access_token"],
                "role": token_data["role"],
                # We could add more if backend returns it
            }
            store.save(creds)
            print("\nSuccessfully authenticated and saved credentials.")
        else:
            print("\nLogin failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nError during login: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

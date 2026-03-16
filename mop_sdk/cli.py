import argparse
import sys
import logging
import webbrowser
import os
from .auth import DeviceFlowHandler, CredentialStore

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

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Prioritize URL: global arg > env > default
    base_url = args.url or os.getenv("MOP_URL") or "http://localhost:8001"

    if args.command == "login":
        do_login(base_url)
    elif args.command == "job":
        do_job(args)
    else:
        parser.print_help()
    sys.stdout.flush()

def do_job(args):
    from .client import MOPClient
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

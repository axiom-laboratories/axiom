import paramiko
import os
import time

REMOTE_DIR = "/home/speedy/master_of_puppets"

def read_secrets():
    secrets = {}
    with open("secrets.env", "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                secrets[k] = v
    return secrets

def run_command(client, command, print_output=True):
    print(f"REMOTE: {command}")
    stdin, stdout, stderr = client.exec_command(command, get_pty=True)
    out_lines = []
    while True:
        if stdout.channel.recv_ready():
            try:
                data = stdout.channel.recv(4096).decode('utf-8', errors='replace')
                if print_output: print(data, end="")
                out_lines.append(data)
            except: pass
        if stdout.channel.exit_status_ready():
            break
        time.sleep(0.1)
    return "".join(out_lines)

def deploy_server():
    creds = read_secrets()
    ip = creds.get("speedy_mini_ip")
    user = creds.get("speedy_mini_username")
    password = creds.get("speedy_mini_password")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {ip}...")
    client.connect(ip, username=user, password=password)

    try:
        sftp = client.open_sftp()
        
        # 1. Upload Code (Agent Service)
        print("--- Uploading Puppeteer Code ---")
        run_command(client, f"mkdir -p {REMOTE_DIR}/puppeteer/agent_service")
        local_main = "puppeteer/agent_service/main.py"
        remote_main = f"{REMOTE_DIR}/puppeteer/agent_service/main.py"
        sftp.put(local_main, remote_main)
        # Upload Compose File
        sftp.put("puppeteer/compose.server.yaml", f"{REMOTE_DIR}/puppeteer/compose.server.yaml")
        
        # Upload DB schema too just in case
        local_db = "puppeteer/agent_service/db.py"
        remote_db = f"{REMOTE_DIR}/puppeteer/agent_service/db.py"
        sftp.put(local_db, remote_db)

        # Upload Containerfile and Requirements
        print("--- Uploading Build Files ---")
        sftp.put("puppeteer/Containerfile.server", f"{REMOTE_DIR}/puppeteer/Containerfile.server")
        sftp.put("puppeteer/requirements.txt", f"{REMOTE_DIR}/puppeteer/requirements.txt")
        # Agent service also needs 'installer' and 'docs' directories for static serving (as per Containerfile)
        # We need to upload them. run_command mkdir first.
        run_command(client, f"mkdir -p {REMOTE_DIR}/puppeteer/installer")
        run_command(client, f"mkdir -p {REMOTE_DIR}/puppeteer/docs")
        
        # We need to upload directory contents. sftp.put doesn't do recursive.
        # We can implement a helper or just zip.
        # Since we are already editing this, let's just zip the 'puppeteer' folder exclude problematic things? 
        # No, let's keep it simple and just use the existing patterns or zip just what we need.
        # Let's add zip util to this script similar to deploy_dashboard.py if it's too many files.
        # But for now, let's just upload the few files we know are needed if small.
        # Actually 'docs' has 9 files. 'installer' has 4.
        # Let's just upload them one by one for robustness or assume they are synced?
        # They are NOT synced.
        
        # Let's use recursive upload helper.
        def upload_dir(local, remote):
            for item in os.listdir(local):
                 l = os.path.join(local, item)
                 r = f"{remote}/{item}"
                 if os.path.isfile(l):
                     sftp.put(l, r)
        
        upload_dir("puppeteer/installer", f"{REMOTE_DIR}/puppeteer/installer")
        upload_dir("puppeteer/docs", f"{REMOTE_DIR}/puppeteer/docs")

        # 2. Upload Secrets (Certs)
        print("--- Uploading New Certificates ---")
        # Ensure remote secrets dir exists
        run_command(client, f"mkdir -p {REMOTE_DIR}/puppeteer/secrets/ca")
        
        # List of secrets to upload
        secrets_files = [
            "puppeteer/secrets/server.crt",
            "puppeteer/secrets/server.key",
            "puppeteer/secrets/cert.pem",
            "puppeteer/secrets/key.pem",
            "puppeteer/secrets/verification.key",
            "puppeteer/secrets/root_ca.crt", # Legacy path if used?
            "puppeteer/secrets/ca/root_ca.crt",
            "puppeteer/secrets/ca/root_ca.key"
        ]
        
        for secret in secrets_files:
            if os.path.exists(secret):
                remote_path = f"{REMOTE_DIR}/{secret}"
                # ensure dir
                # sftp.put won't create dirs, but we made secrets/ca above
                print(f"Uploading {secret}...")
                sftp.put(secret, remote_path)

        sftp.close()

        # 3. Restart Agent Service
        print("--- Restarting Puppeteer Stack ---")
        # Just restart the agent container to pick up code and certs
        # (Assuming mapped volumes for secrets? or needs rebuild?)
        # Inspecting previous diagnostics, secrets seem to be mounted or copied?
        # If copied in build, we need to rebuild server.
        # Generally server is built via docker build .
        
        run_command(client, f"cd {REMOTE_DIR}/puppeteer && docker compose -f compose.server.yaml build agent")
        run_command(client, f"cd {REMOTE_DIR}/puppeteer && docker compose -f compose.server.yaml up -d agent --force-recreate")
        
        print("Waiting 10s for Puppeteer Startup...")
        time.sleep(10)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    deploy_server()

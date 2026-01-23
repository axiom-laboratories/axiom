import paramiko
import time

REMOTE_DIR = "/home/speedy/master_of_puppets"
LOCAL_PATH = "puppets/environment_service/node.py"

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
            if stdout.channel.recv_ready():
                try: 
                    data = stdout.channel.recv(4096).decode('utf-8', errors='replace')
                    if print_output: print(data, end="")
                    out_lines.append(data)
                except: pass
            break
        time.sleep(0.1)
    
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        return False, "".join(out_lines)
    return True, "".join(out_lines)

def sync_and_rebuild():
    creds = read_secrets()
    ip = creds.get("speedy_mini_ip")
    user = creds.get("speedy_mini_username")
    password = creds.get("speedy_mini_password")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {ip}...")
    client.connect(ip, username=user, password=password)

    try:
        print("--- Uploading Patched Puppet Code ---")
        sftp = client.open_sftp()
        # Upload using same relative path
        run_command(client, f"mkdir -p {REMOTE_DIR}/puppets/environment_service")
        sftp.put(LOCAL_PATH, f"{REMOTE_DIR}/puppets/environment_service/node.py")
        
        print("--- Uploading Puppet Build Files ---")
        sftp.put("puppets/Containerfile.node", f"{REMOTE_DIR}/puppets/Containerfile.node")
        sftp.put("puppets/requirements.txt", f"{REMOTE_DIR}/puppets/requirements.txt")
        
        sftp.close()
        
        print("--- Overwriting Remote Compose Config ---")
        
        # Generator Join Token dynamically
        print("--- Fetching Admin Access Token ---")
        # 1. Login as Admin
        success, login_json = run_command(client, "curl -s -X POST -d 'username=admin&password=admin' https://localhost:8001/auth/login -k", print_output=False)
        
        import json
        admin_token = ""
        try:
            login_data = json.loads(login_json)
            admin_token = login_data.get("access_token")
            if not admin_token:
                 print(f"FAILED TO LOGIN: {login_json}")
                 return
        except Exception as e:
             print(f"LOGIN ERROR: {e} - Output: {login_json}")
             return

        print("--- Generating Join Token ---")
        # 2. Generate Join Token using Bearer Auth
        success, token_json = run_command(client, f"curl -s -X POST -H 'Authorization: Bearer {admin_token}' -H 'Content-Type: application/json' https://localhost:8001/admin/generate-token -k", print_output=True)
        
        import json
        try:
            token_data = json.loads(token_json)
            # API returns a full token string usually? Or object? 
            # Endpoints usually return {"token": "..."} or similar.
            # Let's check api. 
            # actually looking at agent_service code (implied), it returns JSON.
            # diagnostic showed `JOIN_TOKEN` is a b64 blob.
            # The API /admin/generate-token likely returns that blob in a field.
            # Let's assume it returns {"token": "..."} or similar.
            # If we can't parse, we fail.
            if "token" in token_data:
                full_token = token_data["token"] 
                # This token is ALREADY the base64 blob we need if it comes from generate-token endpoint?
                # Usually that endpoint returns the full blob.
                token_b64 = full_token
            else:
                 print(f"FAILED TO PARSE TOKEN: {token_json}")
                 return
        except Exception as e:
            print(f"FAILED TO GET TOKEN: {e} - Output: {token_json}")
            # Fallback to hardcoded just in case? No, it will fail.
            return
        
        # Define fresh template to avoid corruption
        NODES_COUNT = 4
        
        compose_content = 'version: "3"\nservices:\n'
        for i in range(1, NODES_COUNT + 1):
             compose_content += f"""
  puppet-{i}:
    image: localhost/puppets-node:latest
    environment:
      - AGENT_URL=https://host.docker.internal:8001
      - JOIN_TOKEN={token_b64}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - PYTHONUNBUFFERED=1

    extra_hosts:
      - "host.docker.internal:host-gateway"

    restart: always

"""
        
        # Write back
        sftp = client.open_sftp()
        with sftp.file(f"{REMOTE_DIR}/puppets/node-compose-scale.yaml", "w") as f:
            f.write(compose_content)
        sftp.close()
        
        print("--- Rebuilding Puppet Image ---")
        run_command(client, f"cd {REMOTE_DIR}/puppets && docker build --no-cache -t localhost/puppets-node:latest -f Containerfile.node .")
        
        print("--- Redeploying ---")
        run_command(client, f"cd {REMOTE_DIR}/puppets && docker compose -f node-compose-scale.yaml up -d --force-recreate")
        
        print("Waiting 15s...")
        time.sleep(15)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    sync_and_rebuild()

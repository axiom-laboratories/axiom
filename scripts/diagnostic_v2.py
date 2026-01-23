import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

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

def diagnostic():
    creds = read_secrets()
    ip = creds.get("speedy_mini_ip")
    user = creds.get("speedy_mini_username")
    password = creds.get("speedy_mini_password")
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {ip}...")
    client.connect(ip, username=user, password=password)

    try:
        print("\n--- Network Check ---")
        run_command(client, "docker network ls")

        print("\n--- Inspect Puppet Compose ---")
        run_command(client, f"cat {REMOTE_DIR}/puppets/node-compose-scale.yaml")

        print("\n--- Docker PS (All) ---")
        run_command(client, "docker ps -a")
        
        print("\n--- Logs of a Puppet ---")
        _, nodes_list = run_command(client, "docker ps --format '{{.Names}}' | grep -E 'node|puppet' | head -n 1", print_output=False)
        node = nodes_list.strip()
        if node:
            print(f"Logs for {node}:")
            run_command(client, f"docker logs {node} 2>&1 | tail -n 20")
        else:
            print("No Puppet container found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    diagnostic()

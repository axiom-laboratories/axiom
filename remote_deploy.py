import os
import paramiko
import sys
import zipfile
import time
from scp import SCPClient
from dotenv import dotenv_values

def log(msg):
    # Removing emojis to avoid UnicodeEncodeError in Windows terminal
    print(msg)
    sys.stdout.flush()

def run_cmd(ssh, command):
    log(f"Executing: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return exit_status, out, err

def deploy():
    # Load credentials
    secrets = dotenv_values("secrets.env")
    host = secrets.get("speedy_mini_ip")
    user = secrets.get("speedy_mini_username")
    password = secrets.get("speedy_mini_password")
    
    if not host or not user or not password:
        log("Error: Missing credentials in secrets.env")
        return

    log(f"Connecting to {user}@{host}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=30)
    except Exception as e:
        log(f"Connection Failed: {e}")
        return

    remote_path = "/home/speedy/puppeteer_stack"
    
    log(f"Cleaning up and creating {remote_path}...")
    run_cmd(ssh, f"rm -rf {remote_path} && mkdir -p {remote_path}")
    
    log("Zipping Puppeteer folder (excluding node_modules)...")
    zip_path = "puppeteer.zip"
    if os.path.exists(zip_path): os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("puppeteer"):
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, full_path)
    
    log("Starting SCP Transfer...")
    try:
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(zip_path, remote_path + "/" + zip_path)
            if os.path.exists("secrets.env"):
                scp.put("secrets.env", remote_path + "/secrets.env")
        log("Transfer Complete.")
    except Exception as e:
        log(f"Transfer Failed: {e}")
        ssh.close()
        return
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    
    # Extraction
    log("Checking for unzip on remote...")
    status, out, err = run_cmd(ssh, "unzip -v")
    if status != 0:
        log("unzip not found, using python3...")
        extract_cmd = f"cd {remote_path} && python3 -m zipfile -e {zip_path} ."
    else:
        extract_cmd = f"cd {remote_path} && unzip -o {zip_path}"
    
    status, out, err = run_cmd(ssh, extract_cmd)
    if status != 0:
        log(f"Extraction failed: {err}")
        ssh.close()
        return

    # Clean up zip
    run_cmd(ssh, f"rm {remote_path}/{zip_path}")

    # Build and Run
    actual_code_path = f"{remote_path}/puppeteer"
    
    # 1. Build
    log("Building Loader...")
    build_cmd = f"cd {actual_code_path} && podman build -t puppeteer-loader -f loader/Containerfile ."
    status, out, err = run_cmd(ssh, build_cmd)
    if status != 0:
        log(f"Build Failed:\n{err}\n{out}")
        ssh.close()
        return
    log("Build successful.")

    # 2. Run
    log("Launching Stack via Loader...")
    socket_path = "/run/user/1000/podman/podman.sock"
    
    # Ensure secrets.env is available for the loader
    run_cmd(ssh, f"cp {remote_path}/secrets.env {actual_code_path}/secrets.env")

    # Remove previous container if exists
    run_cmd(ssh, "podman rm -f puppeteer-loader-run")
    
    log("Force-cleaning stack images to ensure fresh build...")
    # Clean up the side-by-side containers BEFORE building the loader to avoid socket being blocked or stale images used
    run_cmd(ssh, f"cd {actual_code_path} && podman-compose -f compose.server.yaml down")
    run_cmd(ssh, "podman rmi -f localhost/master-of-puppets-dashboard:latest localhost/master-of-puppets-server:latest localhost/app_cert-manager:latest")

    # MOUNT /etc/containers from host to loader to avoid seccomp mismatch
    # ALSO mount /usr/share/containers just in case
    run_cmd_remote = f"cd {actual_code_path} && podman run --privileged -d --name puppeteer-loader-run " + \
                     f"-v {socket_path}:/run/podman/podman.sock " + \
                     f"-v /etc/containers:/etc/containers:ro " + \
                     f"-v /usr/share/containers:/usr/share/containers:ro " + \
                     f"-v {actual_code_path}/secrets.env:/app/secrets.env puppeteer-loader"
    
    status, out, err = run_cmd(ssh, run_cmd_remote)
    if status == 0:
        log(f"Loader started! Container ID: {out}")
    else:
        log(f"Launch Failed:\n{err}\n{out}")

    log("Waiting 60 seconds for initial logs...")
    time.sleep(60)

    log("Loader Logs (First 60s):")
    status, out, err = run_cmd(ssh, "podman logs puppeteer-loader-run")
    log(out)
    
    log("Waiting another 240 seconds for stack build...")
    time.sleep(240)

    log("Final Stack Status:")
    status, out, err = run_cmd(ssh, "podman ps -a")
    log(out)
    
    log("Final Loader Logs:")
    status, out, err = run_cmd(ssh, "podman logs puppeteer-loader-run")
    log(out)

    ssh.close()
    log("Deployment Process Finished.")

if __name__ == "__main__":
    deploy()

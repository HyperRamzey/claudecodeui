#!/usr/bin/env python3
"""Start the ClaudeCodeUI stack (llama-server, nginx, ClaudeCodeUI).

Does NOT kill llama-server — only stops nginx and ClaudeCodeUI.

Environment variables:
    CCUI_DIR          - ClaudeCodeUI project directory (default: current directory)
    NODE              - Node.js executable path (default: node from PATH)
    CCUI_SERVER       - Server entry point (default: dist-server/server/index.js)
    CCUI_PORT         - ClaudeCodeUI port (default: 3001)
    NGINX             - nginx executable path (default: nginx from PATH)
    NGINX_HTTP        - nginx HTTP port (default: 80)
    NGINX_HTTPS       - nginx HTTPS port (default: 443)
    LLAMA_SCRIPT      - llama-server start script path (default: empty — skip start)
    LLAMA_PORT        - llama-server port (default: 8080)
"""

import os
import subprocess
import sys
import time

# ---- Configuration (env vars override defaults) ----

CCUI_DIR = os.environ.get("CCUI_DIR", os.path.dirname(os.path.abspath(__file__)))
NODE = os.environ.get("NODE", "node")
CCUI_SERVER = os.environ.get("CCUI_SERVER", "dist-server/server/index.js")
CCUI_PORT = int(os.environ.get("CCUI_PORT", "3001"))

NGINX = os.environ.get("NGINX", "nginx")
NGINX_HTTP = int(os.environ.get("NGINX_HTTP", "80"))
NGINX_HTTPS = int(os.environ.get("NGINX_HTTPS", "443"))

LLAMA_SCRIPT = os.environ.get("LLAMA_SCRIPT", "")
LLAMA_PORT = int(os.environ.get("LLAMA_PORT", "8080"))

def get_listening_ports():
    """Get dict of port -> PID for all LISTENING TCP connections."""
    result = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True
    )
    ports = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
            addr = parts[1]  # LOCAL address (has the port)
            if ":" in addr:
                try:
                    port = int(addr.rsplit(":", 1)[-1])
                    pid = int(parts[4])
                    ports[port] = pid
                except ValueError:
                    pass
    return ports

def kill_port(port):
    """Kill process on a port."""
    ports = get_listening_ports()
    if port in ports:
        try:
            subprocess.run(["taskkill", "/PID", str(ports[port]), "/F"],
                         capture_output=True)
            print(f"  Stopped process on port {port} (PID {ports[port]})")
            return True
        except Exception:
            return False
    return False

def wait_for_port(port, timeout=120):
    """Wait for a port to become LISTENING."""
    start = time.time()
    while time.time() - start < timeout:
        ports = get_listening_ports()
        if port in ports:
            return True
        time.sleep(2)
    return False

def main():
    print("========================================")
    print("Starting ClaudeCodeUI Stack")
    print("========================================\n")

    # ---- Kill nginx and ClaudeCodeUI (NOT llama-server) ----
    print("Stopping existing services...")
    kill_port(CCUI_PORT)
    kill_port(NGINX_HTTPS)
    kill_port(NGINX_HTTP)

    # Stop nginx gracefully
    subprocess.run([NGINX, "-s", "stop"], capture_output=True)
    time.sleep(2)

    # ---- Start llama-server only if NOT already running ----
    if LLAMA_SCRIPT:
        print(f"\nChecking llama-server (port {LLAMA_PORT})...")
        ports = get_listening_ports()
        if LLAMA_PORT in ports:
            print(f"  llama-server is already running (port {LLAMA_PORT}), skipping start\n")
        else:
            print(f"Starting llama-server (port {LLAMA_PORT})...")
            llama_dir = os.path.dirname(os.path.abspath(LLAMA_SCRIPT))
            os.chdir(llama_dir)
            subprocess.Popen(
                ["cmd", "/k", "call", LLAMA_SCRIPT],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            print(f"\nWaiting for llama-server to start (port {LLAMA_PORT})...")
            if wait_for_port(LLAMA_PORT):
                print("  llama-server is ready\n")
            else:
                print("  ERROR: llama-server did not start after 120 seconds",
                      file=sys.stderr)
                sys.exit(1)

    # ---- Start nginx ----
    print("Starting nginx (ports 80, 443)...")
    nginx_dir = os.path.dirname(os.path.abspath(NGINX))
    os.chdir(nginx_dir)
    subprocess.run([NGINX, "-t"], capture_output=True)
    subprocess.Popen([NGINX], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    time.sleep(2)

    # ---- Start ClaudeCodeUI ----
    print(f"\nStarting ClaudeCodeUI (port {CCUI_PORT})...")
    os.chdir(CCUI_DIR)
    subprocess.Popen(
        [NODE, CCUI_SERVER],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

    print("\n========================================")
    print("All services started!")
    print("========================================\n")
    print(f"  ClaudeCodeUI:    http://127.0.0.1:{CCUI_PORT}")
    print(f"  nginx HTTPS:     https://127.0.0.1:{NGINX_HTTPS}")
    print(f"  nginx HTTP:      http://127.0.0.1:{NGINX_HTTP}\n")
    if LLAMA_SCRIPT:
        print(f"  llama-server:    http://127.0.0.1:{LLAMA_PORT}\n")
    print("Press any key to close this window...")
    input()

if __name__ == "__main__":
    main()

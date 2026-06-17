#!/usr/bin/env python3
"""Stop nginx and ClaudeCodeUI. Does NOT stop llama-server.

Environment variables:
    NODE              - Node.js executable path (default: node from PATH)
    CCUI_SERVER       - Server entry point (default: dist-server/server/index.js)
    CCUI_PORT         - ClaudeCodeUI port (default: 3001)
    NGINX             - nginx executable path (default: nginx from PATH)
    NGINX_HTTP        - nginx HTTP port (default: 80)
    NGINX_HTTPS       - nginx HTTPS port (default: 443)
"""

import os
import subprocess

# ---- Configuration (env vars override defaults) ----

NODE = os.environ.get("NODE", "node")
CCUI_SERVER = os.environ.get("CCUI_SERVER", "dist-server/server/index.js")
CCUI_PORT = int(os.environ.get("CCUI_PORT", "3001"))

NGINX = os.environ.get("NGINX", "nginx")
NGINX_HTTP = int(os.environ.get("NGINX_HTTP", "80"))
NGINX_HTTPS = int(os.environ.get("NGINX_HTTPS", "443"))

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

def main():
    print("========================================")
    print("Stopping ClaudeCodeUI Stack")
    print("========================================\n")

    print("Stopping ClaudeCodeUI (port 3001)...")
    kill_port(CCUI_PORT)

    print("\nStopping nginx (ports 80, 443)...")
    kill_port(NGINX_HTTPS)
    kill_port(NGINX_HTTP)
    subprocess.run([NGINX, "-s", "stop"], capture_output=True)

    print("\n  (llama-server is NOT stopped — kill it manually)")

    print("\n========================================")
    print("nginx and ClaudeCodeUI stopped!")
    print("========================================")
    input("\nPress any key to close this window...")

if __name__ == "__main__":
    main()

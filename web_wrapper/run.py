import subprocess
import sys
import os
import time
from pathlib import Path

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

def main():
    base_dir = Path(__file__).parent.absolute()
    backend_dir = base_dir / "backend"
    frontend_dir = base_dir / "frontend"

    print("Starting Backend...")
    backend_process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(backend_dir),
        shell=True
    )

    print("Starting Frontend...")
    # Using npm run dev
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        shell=True
    )

    local_ip = get_local_ip()
    print("\nServices are running!")
    print(f"Local:   http://localhost:5173")
    print(f"Network: http://{local_ip}:5173")
    print("\nPress Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()

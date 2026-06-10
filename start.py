# -*- coding: utf-8 -*-
"""
AI Research Assistant -- One-click Launcher
Usage: double-click this file, or run: python start.py
"""
import sys
import os
import subprocess
import time
import webbrowser
import shutil
from pathlib import Path

# ──────────────────────────────────────────────
# Output helpers (ASCII-safe for Windows cp950)
# ──────────────────────────────────────────────
def ok(msg):   print(f"  [OK]  {msg}")
def info(msg): print(f"  -->   {msg}")
def warn(msg): print(f"  [!!]  {msg}")
def err(msg):  print(f"  [X]   {msg}")
def title(msg):
    bar = "-" * 52
    print(f"\n{bar}\n  {msg}\n{bar}")

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
ROOT     = Path(__file__).parent.resolve()
BACKEND  = ROOT / "backend"
FRONTEND = ROOT / "frontend"

BACKEND_PORT  = 8000
FRONTEND_PORT = 5173
FRONTEND_URL  = f"http://localhost:{FRONTEND_PORT}"

# ──────────────────────────────────────────────
# Step 1: Find Python
# ──────────────────────────────────────────────
def find_python():
    candidates = [
        sys.executable,
        r"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe",
        r"C:\Users\User\anaconda3\python.exe",
        "python3",
        "python",
    ]
    for py in candidates:
        if not py:
            continue
        try:
            r = subprocess.run(
                [py, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and "Python 3" in (r.stdout + r.stderr):
                return py
        except Exception:
            continue
    return None

# ──────────────────────────────────────────────
# Step 2: Find npm
# ──────────────────────────────────────────────
def find_npm():
    candidates = [
        r"C:\Program Files\nodejs\npm.cmd",
        shutil.which("npm"),
    ]
    for npm in candidates:
        if npm and Path(npm).exists():
            return npm
    try:
        r = subprocess.run(["where", "npm"], capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if line:
                return line
    except Exception:
        pass
    return None

# ──────────────────────────────────────────────
# Step 3: Install backend packages
# ──────────────────────────────────────────────
def install_backend(python):
    req = BACKEND / "requirements.txt"
    if not req.exists():
        warn("requirements.txt not found, skipping")
        return
    info("Installing backend packages (pip install -r requirements.txt) ...")
    subprocess.run(
        [python, "-m", "pip", "install", "-r", str(req),
         "--quiet", "--no-warn-script-location"],
        cwd=str(BACKEND)
    )
    ok("Backend packages installed")

# ──────────────────────────────────────────────
# Step 4: Install frontend node_modules
# ──────────────────────────────────────────────
def install_frontend(npm):
    node_modules = FRONTEND / "node_modules"
    if not (FRONTEND / "package.json").exists():
        warn("package.json not found, skipping npm install")
        return
    if node_modules.exists():
        ok("node_modules already exists, skipping npm install")
        return
    info("Installing frontend packages (npm install) -- may take 1-2 min ...")
    subprocess.run([npm, "install"], cwd=str(FRONTEND))
    ok("Frontend packages installed")

# ──────────────────────────────────────────────
# Step 5: Fix PowerShell execution policy
# ──────────────────────────────────────────────
def fix_ps_policy():
    try:
        subprocess.run(
            ["powershell", "-Command",
             "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"],
            capture_output=True, timeout=10
        )
        ok("PowerShell execution policy set to RemoteSigned")
    except Exception:
        pass

# ──────────────────────────────────────────────
# Step 6: Start backend in new window
# ──────────────────────────────────────────────
def start_backend(python):
    info(f"Starting backend server on port {BACKEND_PORT} ...")
    cmd = f'cmd /k ""{python}" main.py"'
    subprocess.Popen(
        cmd,
        cwd=str(BACKEND),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    ok("Backend window opened")

# ──────────────────────────────────────────────
# Step 7: Start frontend in new window
# ──────────────────────────────────────────────
def start_frontend(npm):
    info(f"Starting frontend dev server on port {FRONTEND_PORT} ...")
    cmd = f'cmd /k ""{npm}" run dev"'
    subprocess.Popen(
        cmd,
        cwd=str(FRONTEND),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    ok("Frontend window opened")

# ──────────────────────────────────────────────
# Step 8: Wait and open browser
# ──────────────────────────────────────────────
def open_browser():
    info("Waiting 6 seconds for servers to start ...")
    for i in range(6, 0, -1):
        print(f"\r  ...  Opening browser in {i}s", end="", flush=True)
        time.sleep(1)
    print()
    webbrowser.open(FRONTEND_URL)
    ok(f"Browser opened: {FRONTEND_URL}")

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    print()
    print("=" * 52)
    print("  AI Research Assistant -- One-click Launcher")
    print("=" * 52)

    title("Step 1: Check environment")
    python = find_python()
    if not python:
        err("Python 3 not found! Install from https://python.org")
        input("\nPress Enter to exit...")
        sys.exit(1)
    ok(f"Python: {python}")

    npm = find_npm()
    if not npm:
        err("npm not found! Install Node.js from https://nodejs.org")
        input("\nPress Enter to exit...")
        sys.exit(1)
    ok(f"npm: {npm}")

    fix_ps_policy()

    title("Step 2: Install packages")
    install_backend(python)
    install_frontend(npm)

    title("Step 3: Start servers")
    start_backend(python)
    time.sleep(1)
    start_frontend(npm)

    title("Step 4: Open browser")
    open_browser()

    print()
    print("=" * 52)
    print("  Launch complete!")
    print(f"  Frontend : http://localhost:{FRONTEND_PORT}")
    print(f"  Backend  : http://localhost:{BACKEND_PORT}")
    print()
    print("  Keep the two black windows open.")
    print("  Closing them will stop the servers.")
    print("=" * 52)
    input("\nPress Enter to close this window...")

if __name__ == "__main__":
    main()

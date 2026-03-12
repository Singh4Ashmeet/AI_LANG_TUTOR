from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def load_vite_env(repo_root: Path) -> dict[str, str]:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return {}

    vite_env: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith("VITE_"):
            vite_env[key] = value
    return vite_env


def terminate_process(proc: subprocess.Popen, name: str) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    frontend_dir = repo_root / "frontend"

    env = os.environ.copy()
    env.update(load_vite_env(repo_root))

    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--reload"]
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd = [npm_cmd, "run", "dev"]

    if not frontend_dir.exists():
        print(f"Frontend directory not found: {frontend_dir}")
        return 1

    backend = subprocess.Popen(backend_cmd, cwd=repo_root, env=env)
    frontend = subprocess.Popen(frontend_cmd, cwd=frontend_dir, env=env)

    try:
        while True:
            backend_exit = backend.poll()
            frontend_exit = frontend.poll()
            if backend_exit is not None or frontend_exit is not None:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_process(frontend, "frontend")
        terminate_process(backend, "backend")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

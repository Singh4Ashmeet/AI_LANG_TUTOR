import asyncio
import os
import signal
import sys
import webbrowser
from pathlib import Path
import httpx

BACKEND_HOST = "localhost"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
HEALTH_CHECK_RETRIES = 30
HEALTH_CHECK_INTERVAL = 1.0

def load_env(repo_root: Path) -> dict:
    env_path = repo_root / ".env"
    env = os.environ.copy()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

async def run_process(cmd: list[str], cwd: Path, env: dict, name: str):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    print(f"[{name}] Started with PID {process.pid}")

    async def log_stream(stream, prefix):
        while True:
            line = await stream.readline()
            if not line: break
            print(f"[{prefix}] {line.decode().strip()}")

    await asyncio.gather(
        log_stream(process.stdout, name),
        log_stream(process.stderr, f"{name}:ERR"),
    )
    return await process.wait()

async def health_check_loop():
    url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
    print(f"[Launcher] Waiting for backend at {url}...")
    async with httpx.AsyncClient() as client:
        for _ in range(HEALTH_CHECK_RETRIES):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    print("[Launcher] Backend is healthy! 🚀")
                    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
                    return
            except httpx.RequestError:
                pass
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
    print("[Launcher] Backend failed to start.")

async def main():
    repo_root = Path(__file__).resolve().parent
    frontend_dir = repo_root / "frontend"
    env = load_env(repo_root)
    
    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", BACKEND_HOST, "--port", str(BACKEND_PORT), "--reload"]
    npm = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd = [npm, "run", "dev"]

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    def handle_signal(): stop_event.set()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError: pass # Windows

    asyncio.create_task(run_process(backend_cmd, repo_root, env, "Backend"))
    asyncio.create_task(run_process(frontend_cmd, frontend_dir, env, "Frontend"))
    asyncio.create_task(health_check_loop())

    await stop_event.wait()

if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())

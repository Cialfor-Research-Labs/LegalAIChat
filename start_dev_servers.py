from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent

BACKEND_PORT = 9001
FRONTEND_PORT = 3000
HOST = "0.0.0.0"

BACKEND_OUT_LOG = REPO_ROOT / "tllac_backend.out.log"
BACKEND_ERR_LOG = REPO_ROOT / "tllac_backend.err.log"
FRONTEND_OUT_LOG = REPO_ROOT / "ui_dev.out.log"
FRONTEND_ERR_LOG = REPO_ROOT / "ui_dev.err.log"


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def get_lan_ip() -> str:
    """Return the best LAN IP for sharing dev URLs on the local network."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())


def pids_on_port(port: int) -> set[int]:
    """Return listening process IDs for a TCP port on macOS."""
    result = _run_command(["lsof", "-ti", f"tcp:{port}"])
    pids: set[int] = set()

    if result.returncode != 0 and not result.stdout.strip():
        return pids

    for token in result.stdout.replace("\n", " ").split():
        token = token.strip()
        if token.isdigit():
            pids.add(int(token))
    return pids


def kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)

    os.kill(pid, signal.SIGKILL)


def wait_for_port_to_close(port: int, timeout_seconds: float = 10) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not pids_on_port(port) and not _port_is_open(port):
            return
        time.sleep(0.3)
    raise TimeoutError(f"Port {port} did not close within {timeout_seconds} seconds.")


def wait_for_port_to_open(port: int, timeout_seconds: float = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _port_is_open(port):
            return
        time.sleep(0.3)
    raise TimeoutError(f"Port {port} did not open within {timeout_seconds} seconds.")


def stop_processes_on_ports(ports: Iterable[int]) -> None:
    seen_pids: set[int] = set()
    for port in ports:
        for pid in pids_on_port(port):
            if pid in seen_pids:
                continue
            print(f"Stopping PID {pid} on port {port}...")
            kill_pid(pid)
            seen_pids.add(pid)

    for port in ports:
        wait_for_port_to_close(port)


def _clear_log_files(paths: Iterable[Path]) -> None:
    for path in paths:
        path.write_text("", encoding="utf-8")


def _backend_command() -> list[str]:
    python_candidates = (
        REPO_ROOT / "tllac" / ".venv" / "bin" / "python",
        REPO_ROOT / "tllac" / "venv" / "bin" / "python",
        REPO_ROOT / "venv" / "bin" / "python",
        Path(sys.executable or "python3"),
    )
    python_executable = next((path for path in python_candidates if path.exists()), Path("python3"))

    return [
        str(python_executable),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        HOST,
        "--port",
        str(BACKEND_PORT),
    ]


def _frontend_command() -> list[str]:
    vite_executable = Path("node_modules") / ".bin" / "vite"
    return [str(vite_executable), "--port", str(FRONTEND_PORT), "--host", HOST]


def _spawn_service(command: list[str], cwd: Path, stdout_path: Path, stderr_path: Path) -> subprocess.Popen[bytes]:
    stdout_handle = open(stdout_path, "ab")
    stderr_handle = open(stderr_path, "ab")

    popen_kwargs = {
        "cwd": str(cwd),
        "stdout": stdout_handle,
        "stderr": stderr_handle,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }

    popen_kwargs["start_new_session"] = True

    return subprocess.Popen(command, **popen_kwargs)


def main() -> int:
    print("Checking dev ports...")
    stop_processes_on_ports([BACKEND_PORT, FRONTEND_PORT])

    print("Resetting logs...")
    _clear_log_files(
        [
            BACKEND_OUT_LOG,
            BACKEND_ERR_LOG,
            FRONTEND_OUT_LOG,
            FRONTEND_ERR_LOG,
        ]
    )

    print("Starting backend...")
    _spawn_service(
        _backend_command(),
        REPO_ROOT / "tllac",
        BACKEND_OUT_LOG,
        BACKEND_ERR_LOG,
    )

    print("Starting frontend...")
    _spawn_service(
        _frontend_command(),
        REPO_ROOT / "ui",
        FRONTEND_OUT_LOG,
        FRONTEND_ERR_LOG,
    )

    wait_for_port_to_open(BACKEND_PORT)
    wait_for_port_to_open(FRONTEND_PORT)

    lan_ip = get_lan_ip()

    print(f"Backend is listening on http://{HOST}:{BACKEND_PORT}")
    print(f"Frontend is listening on http://{HOST}:{FRONTEND_PORT}")
    print(f"Local frontend: http://127.0.0.1:{FRONTEND_PORT}")
    print(f"Team LAN URL: http://{lan_ip}:{FRONTEND_PORT}")
    print(f"LAN backend URL: http://{lan_ip}:{BACKEND_PORT}")
    print(f"Backend logs: {BACKEND_OUT_LOG.name}, {BACKEND_ERR_LOG.name}")
    print(f"Frontend logs: {FRONTEND_OUT_LOG.name}, {FRONTEND_ERR_LOG.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Failed to start dev servers: {exc}", file=sys.stderr)
        raise SystemExit(1)

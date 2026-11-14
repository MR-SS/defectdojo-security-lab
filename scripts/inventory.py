"""Initial repository inventory command.

This command is read-only and records tool output without secrets.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def run(command: list[str]) -> dict[str, object]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a read-only lab inventory")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    tools = ["docker", "git", "python3", "kubectl", "minikube", "helm"]
    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "tools": {tool: shutil.which(tool) for tool in tools},
        "commands": {
            "docker_version": run(["docker", "--version"]),
            "compose_version": run(["docker", "compose", "version"]),
            "git_version": run(["git", "--version"]),
            "kubectl_context": run(["kubectl", "config", "current-context"]),
            "minikube_profiles": run(["minikube", "profile", "list", "--output", "json"]),
            "listeners": run(["ss", "-ltn"]),
        },
    }
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

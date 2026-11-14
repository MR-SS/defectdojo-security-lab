"""Generate ignored, lab-only deployment secrets without printing values."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

NAMES = (
    "DD_SECRET_KEY",
    "DD_CREDENTIAL_AES_256_KEY",
    "DD_DATABASE_PASSWORD",
)


def generate(path: Path) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing secret file: {path}")
    values = {
        "DD_PROJECT_NAME": "ddslab",
        "DD_UI_BIND": "127.0.0.1",
        "DD_UI_PORT": "18080",
        "DD_DATABASE_USER": "ddslab_user",
        "DD_DATABASE_URL": "postgresql://ddslab_user@postgres:5432/defectdojo",
        "DD_SECRET_KEY": secrets.token_urlsafe(48),
        "DD_CREDENTIAL_AES_256_KEY": secrets.token_urlsafe(48),
        "DD_DATABASE_PASSWORD": secrets.token_urlsafe(32),
    }
    content = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    old_umask = os.umask(0o177)
    try:
        path.write_text(content, encoding="utf-8")
    finally:
        os.umask(old_umask)
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".env.lab"))
    args = parser.parse_args()
    generate(args.output)
    print(f"generated lab credentials at {args.output} with mode 0600")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

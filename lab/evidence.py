"""Write sanitized, immutable evidence manifests for offline runs."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .models import EvidenceManifest

_SECRET_KEY = re.compile(r"(token|password|secret|api[_-]?key|authorization|cookie)", re.I)


def sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def safe_run_id(run_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError("run_id contains unsafe path characters")
    return run_id


def write_manifest(root: Path, manifest: EvidenceManifest) -> Path:
    safe_run_id(manifest.run_id)
    root = root.resolve()
    destination = (root / manifest.run_id).resolve()
    if destination.parent != root:
        raise ValueError("evidence destination escapes root")
    destination.mkdir(parents=True, exist_ok=False)
    payload = sanitize(manifest.model_dump(mode="json"))
    (destination / "manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def utc_now() -> datetime:
    return datetime.now(UTC)

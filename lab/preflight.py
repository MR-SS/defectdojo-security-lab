from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LAB_ROOT = Path(__file__).resolve().parents[1]
HEX_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(r"^[a-z0-9./_-]+:[^:@\s]+@sha256:[0-9a-f]{64}$")
SECRET_NAMES = {"DD_SECRET_KEY", "DD_CREDENTIAL_AES_256_KEY", "DD_DATABASE_PASSWORD"}


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    message: str
    severity: str = "error"


def load_versions(path: Path = LAB_ROOT / "configs/versions.yaml") -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("versions"), dict):
        raise ValueError("versions metadata must contain a versions mapping")
    return data


def selected_version(name: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    versions = (data or load_versions())["versions"]
    try:
        selected = versions[name]
    except KeyError as exc:
        raise ValueError(f"unknown version selection: {name}") from exc
    if not isinstance(selected, dict):
        raise ValueError("selected version metadata must be a mapping")
    return selected


def validate_image_reference(reference: str | None) -> list[PreflightIssue]:
    if not reference:
        return [PreflightIssue("missing_image", "image reference is missing")]
    if ":latest" in reference or reference.endswith(":latest"):
        return [PreflightIssue("floating_image", "floating latest image tags are forbidden")]
    if not IMAGE_REF.fullmatch(reference):
        return [PreflightIssue("unverifiable_image", "image must include a sha256 digest")]
    return []


def validate_selection(name: str, data: dict[str, Any] | None = None) -> list[PreflightIssue]:
    version = selected_version(name, data)
    issues: list[PreflightIssue] = []
    if name == "development" and not version.get("source_sha"):
        issues.append(
            PreflightIssue("development_unpinned", "development requires an explicit source SHA")
        )
    for key in ("image", "image_digest"):
        if not version.get(key):
            issues.append(
                PreflightIssue("missing_artifact_metadata", f"missing version field: {key}")
            )
    issues.extend(validate_image_reference(version.get("image")))
    return issues


def validate_environment(env: dict[str, str] | None = None) -> list[PreflightIssue]:
    values = dict(os.environ) if env is None else env
    required = {"DD_PROJECT_NAME", "DD_UI_BIND", "DD_UI_PORT", *SECRET_NAMES}
    issues = [
        PreflightIssue("missing_environment", f"missing required variable: {key}")
        for key in sorted(required)
        if not values.get(key)
    ]
    if values.get("DD_UI_BIND") != "127.0.0.1":
        issues.append(
            PreflightIssue("non_loopback_bind", "UI binding must be the loopback address")
        )
    for key in SECRET_NAMES:
        if values.get(key) in {"admin", "defectdojo", "password", "changeme"}:
            issues.append(
                PreflightIssue("unsafe_credential", f"default credential detected in {key}")
            )
    return issues


def validate_project_name(name: str, existing_names: set[str]) -> list[PreflightIssue]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,30}", name):
        return [
            PreflightIssue("invalid_project_name", "project name is not a safe Compose identifier")
        ]
    if name in existing_names:
        return [
            PreflightIssue(
                "conflicting_project_name", "project name conflicts with an existing project"
            )
        ]
    return []


def inspect_compose_model(model: dict[str, Any], lab_root: Path = LAB_ROOT) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    services = model.get("services", {})
    for service_name, service in services.items():
        for port in service.get("ports", []) or []:
            published = port.get("published") if isinstance(port, dict) else None
            host_ip = port.get("host_ip") if isinstance(port, dict) else None
            if host_ip != "127.0.0.1":
                issues.append(
                    PreflightIssue("public_port", f"{service_name} port is not loopback-bound")
                )
            if published and int(published) in {3000, 5432, 8080, 8443}:
                issues.append(
                    PreflightIssue(
                        "conflicting_port", f"reserved/conflicting host port: {published}"
                    )
                )
        for volume in service.get("volumes", []) or []:
            source = volume.get("source") if isinstance(volume, dict) else None
            if source and Path(source).is_absolute():
                issues.append(
                    PreflightIssue(
                        "unexpected_bind_mount", f"absolute host mount in {service_name}"
                    )
                )
            if source and source.startswith("."):
                resolved = (lab_root / source).resolve()
                if lab_root not in resolved.parents and resolved != lab_root:
                    issues.append(
                        PreflightIssue("outside_lab_path", f"mount escapes lab root: {source}")
                    )
    return issues


def render_compose(
    env: dict[str, str], compose_file: Path = LAB_ROOT / "compose.lab.yaml"
) -> tuple[int, str, str]:
    if shutil.which("docker") is None:
        return 127, "", "docker is not installed"
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "config"],
        cwd=LAB_ROOT,
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def preflight(version_name: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    values = dict(os.environ) if env is None else env
    issues = validate_selection(version_name) + validate_environment(values)
    return {
        "version": version_name,
        "status": "BLOCKED" if issues else "PASS",
        "issues": [issue.__dict__ for issue in issues],
        "services": [
            "nginx",
            "uwsgi",
            "celeryworker",
            "celerybeat",
            "initializer",
            "postgres",
            "valkey",
        ],
        "network_policy": "loopback-only host exposure; postgres and valkey unexposed",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="baseline")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = preflight(args.version)
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

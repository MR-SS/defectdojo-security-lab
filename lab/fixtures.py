"""Deterministic synthetic fixtures for offline parser and reimport scenarios."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

GENERATOR_VERSION = "1.0.0"


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    parser: str
    content: bytes
    valid: bool
    parameters: dict[str, object]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def _finding(index: int,
    *,
    changed_identity: bool = False,
    missing_optional: bool = False,
) -> dict[str, object]:
    finding_id = f"finding-{index + (1000 if changed_identity else 0):04d}"
    finding: dict[str, object] = {
        "title": f"Synthetic finding {index}",
        "description": "Offline synthetic fixture; not production data.",
        "severity": ["Low", "Medium", "High"][index % 3],
        "unique_id_from_tool": finding_id,
        "scanner_confidence": "Certain",
        "static_finding": True,
        "file_path": f"src/example_{index}.py",
        "line": index + 1,
    }
    if missing_optional:
        finding.pop("description")
        finding["mitigation"] = ""
    return finding


def generic_findings(
    count: int, *, seed: int = 7, missing_optional: bool = False, changed_identity: bool = False
) -> Fixture:
    if count < 0:
        raise ValueError("count must be non-negative")
    random.Random(seed).random()  # Explicitly consume the deterministic seed.
    payload = {
        "version": "1.0.0",
        "name": "Synthetic Generic Findings Import",
        "findings": [
            _finding(i, changed_identity=changed_identity, missing_optional=missing_optional)
            for i in range(count)
        ],
    }
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return Fixture("generic-findings", "Generic Findings Import", content, True, {
        "count": count,
        "seed": seed,
        "missing_optional": missing_optional,
        "changed_identity": changed_identity,
    })


def nmap_xml(count: int, *, malformed: bool = False, missing_optional: bool = False) -> Fixture:
    if count < 0:
        raise ValueError("count must be non-negative")
    root = Element("nmaprun", {"scanner": "nmap", "version": "7.95"})
    for index in range(count):
        host = SubElement(root, "host")
        SubElement(host, "status", {"state": "up"})
        if not missing_optional:
            SubElement(host, "hostnames").append(Element("hostname", {"name": f"host-{index}"}))
        SubElement(host, "address", {"addr": f"192.0.2.{index + 1}", "addrtype": "ipv4"})
        ports = SubElement(host, "ports")
        port = SubElement(ports, "port", {"protocol": "tcp", "portid": "443"})
        SubElement(port, "state", {"state": "open"})
        SubElement(port, "service", {"name": "https", "product": "synthetic"})
    content = tostring(root, encoding="utf-8", xml_declaration=True)
    if malformed:
        content = content[:-12]
    return Fixture("nmap", "Nmap XML", content, not malformed, {
        "count": count, "malformed": malformed, "missing_optional": missing_optional
    })


def json_fixture(parser: str, count: int, *, malformed: bool = False) -> Fixture:
    payload = {
        "tool": parser,
        "findings": [_finding(index) for index in range(count)],
    }
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if malformed:
        content = content[:-2]
    return Fixture(
        parser.lower(), parser, content, not malformed, {"count": count, "malformed": malformed}
    )


def write_fixture(fixture: Fixture, directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".xml" if fixture.parser == "Nmap XML" else ".json"
    path = directory / f"{fixture.fixture_id}{suffix}"
    path.write_bytes(fixture.content)
    metadata = {
        "fixture_id": fixture.fixture_id,
        "parser": fixture.parser,
        "valid": fixture.valid,
        "sha256": fixture.sha256,
        "generator_version": GENERATOR_VERSION,
        "parameters": fixture.parameters,
    }
    (directory / f"{fixture.fixture_id}.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"path": str(path), **metadata}

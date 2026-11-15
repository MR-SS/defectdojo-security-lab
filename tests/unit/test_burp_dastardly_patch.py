"""Patch-proposal verification for the Burp Dastardly root-validation fix.

Local (offline) tests verify the patch applies cleanly to the pinned source
and contains the required structure. Parser behavior is verified inside the
running container via `tests/xml_patch_probe.py` (stdin-only, writes nothing),
because `dojo` and `defusedxml` are importable only there.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

PINNED_PARSER = Path(
    "/home/sajjad/.hermes/cache/scratch/ddslab-source-clean/3.5.101"
    "/dojo/tools/burp_dastardly/parser.py"
)
PROPOSED_PATCH = Path("upstream-proposals/0001-burp-dastardly-root-validation.patch")
CONTAINER_PROBE = Path("tests/integration/test_burp_dastardly_patch_probe.py")


def test_patch_applies_cleanly_to_pinned_source(tmp_path: Path) -> None:
    target = tmp_path / "parser.py"
    target.write_text(PINNED_PARSER.read_text())
    result = subprocess.run(
        ["patch", "--force", str(target), "-i", str(PROPOSED_PATCH.resolve())],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    patched = target.read_text()
    # Structural guarantees of the proposal.
    assert "ALLOWED_ROOTS" in patched
    assert '"testsuites", "testsuite"' in patched
    assert "raise ValueError" in patched
    assert "getroot()" in patched
    # Must not blanket-catch exceptions or alter the malformed-XML path.
    assert "except Exception" not in patched


def test_probe_script_exists_and_writes_nothing() -> None:
    source = CONTAINER_PROBE.read_text()
    # Probe drives docker from the host; the container side is stdin-only
    # (python -) and never mounts volumes or copies files into the container.
    assert "docker" in source  # host-side driver
    assert '"-v"' not in source and "docker cp" not in source
    assert '"python", "-"' in source  # stdin-only exec
    assert "open(" not in source.replace("io.BytesIO", "").replace(
        'ORIG_PARSER.read_text()', ""
    )


def test_patch_is_minimal() -> None:
    """The proposal must touch exactly one upstream file."""
    changed = [
        line
        for line in PROPOSED_PATCH.read_text().splitlines()
        if line.startswith(("--- a/", "+++ b/"))
    ]
    assert len(changed) == 2  # header pair for exactly one file
    assert all("burp_dastardly/parser.py" in line for line in changed)

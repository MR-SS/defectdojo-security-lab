"""Container-probe validation of the proposed Burp Dastardly root-validation fix.

Read-only with respect to the container: the patched parser source is passed
via stdin and exec'd in memory; no container files are written.
Skipped when the ddslab environment is unavailable.
"""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest

PATCH = Path("upstream-proposals/0001-burp-dastardly-root-validation.patch")
ORIG_PARSER = Path(
    "/home/sajjad/.hermes/cache/scratch/ddslab-source-clean/3.5.101"
    "/dojo/tools/burp_dastardly/parser.py"
)

CASES = {
    "baseline": ("fixtures/xml-6b/baseline.xml", None),
    "valid_empty": ("fixtures/xml-6b/valid-empty.xml", None),
    "unexpected": ("fixtures/xml-6b/unexpected-root.xml", None),
    "malformed": ("fixtures/xml-6b/malformed.xml", None),
    "bare_suite": (
        b'<?xml version="1.0"?><testsuite failures="0" name="https://example.test/" '
        b'tests="1"><testcase name="none"/></testsuite>',
        None,
    ),
}

_SCRIPT = (
    "import json\n"
    "CASES = {name: b64 for name, b64 in _PAYLOAD['cases'].items()}\n"
)
_SCRIPT_BODY = '''
import base64, io, json, sys, types
dojo = types.ModuleType('dojo'); models = types.ModuleType('dojo.models')
class Finding:
    def __init__(self, **kw): self.__dict__.update(kw)
models.Finding = Finding; dojo.models = models
sys.modules['dojo'] = dojo; sys.modules['dojo.models'] = models
ns = {}
exec(compile(_PAYLOAD['parser_src'], 'patched_parser.py', 'exec'), ns)
Parser = ns['BurpDastardlyParser']
out = {}
for name, b64 in _PAYLOAD['cases'].items():
    raw = base64.b64decode(b64)
    try:
        findings = Parser().get_findings(io.BytesIO(raw), None)
        out[name] = {'result': 'ok', 'count': len(findings)}
    except Exception as exc:
        out[name] = {'result': type(exc).__name__}
print('PROBE:' + json.dumps(out))
'''


def _docker_available() -> bool:
    result = subprocess.run(["docker", "inspect", "ddslab-uwsgi-1"], capture_output=True)
    return result.returncode == 0


def _patched_source(tmp_path: Path) -> str:
    target = tmp_path / "parser.py"
    target.write_text(ORIG_PARSER.read_text())
    result = subprocess.run(
        ["patch", "--force", str(target), "-i", str(PATCH.resolve())],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return target.read_text()


@pytest.mark.skipif(not _docker_available(), reason="ddslab container not running")
def test_patched_parser_behavior(tmp_path: Path) -> None:
    cases: dict[str, str] = {}
    for name, (source, _) in CASES.items():
        raw = source if isinstance(source, bytes) else Path(source).read_bytes()
        cases[name] = base64.b64encode(raw).decode()
    payload = {"parser_src": _patched_source(tmp_path), "cases": cases}
    full = (
        "import json\n"
        f"_PAYLOAD = {payload!r}\n"
    ) + _SCRIPT_BODY
    result = subprocess.run(
        ["docker", "exec", "-i", "ddslab-uwsgi-1", "python", "-"],
        input=full, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "PROBE:" in result.stdout, result.stdout + result.stderr
    out = json.loads(result.stdout.split("PROBE:")[-1])

    assert out["baseline"] == {"result": "ok", "count": 3}
    assert out["valid_empty"] == {"result": "ok", "count": 0}
    assert out["bare_suite"] == {"result": "ok", "count": 0}
    assert out["unexpected"] == {"result": "ValueError"}
    assert out["malformed"] == {"result": "ParseError"}

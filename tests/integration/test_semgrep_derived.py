"""Exactly one approved synthetic experiment. No retries or cleanup."""

import hashlib
import ipaddress
import json
import os
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from lab.experiment_runner import normalize, redact
from lab.finding_pages import IncompleteReadback, read_findings
from lab.semgrep_control import evaluate, require_complete
from lab.semgrep_derived import derived_pair
from lab.semgrep_preflight import preflight


@pytest.mark.integration
def test_semgrep_derived():
    if (
        os.getenv("DDSLAB_RUN_INTEGRATION") != "1"
        or os.getenv("DDSLAB_APPROVE_SCENARIO") != "SEMGREP-14205-DERIVED"
    ):
        pytest.skip("separate exact scenario approval required")
    credentials = dict(
        line.split("=", 1) for line in Path(".venv/ddslab-integration.env").read_text().splitlines()
    )
    assert credentials["DDSLAB_PRODUCT_TYPE_ID"] == "3"
    url, token = credentials["DDSLAB_API_BASE_URL"], credentials["DDSLAB_API_TOKEN"]
    target = urlsplit(url)
    assert target.scheme == "http" and ipaddress.ip_address(target.hostname).is_loopback
    assert not target.username and not target.password and target.path in ("", "/")
    blobs = tuple(
        Path(f"fixtures/semgrep-derived-{p}.json").read_bytes() for p in ("initial", "changed")
    )
    assert blobs == derived_pair()
    expected = json.loads(Path("configs/semgrep-derived-checksums.json").read_text())
    assert [hashlib.sha256(b).hexdigest() for b in blobs] == expected
    name = "ddslab-semgrep-derived-" + uuid.uuid4().hex
    path = Path("evidence") / name
    path.mkdir(mode=0o700)

    def save(label, obj):
        with (path / (label + ".json")).open("x") as stream:
            json.dump(redact(obj, token), stream, indent=2)

    mutated = False
    try:
        gate = preflight(os.environ["DDSLAB_SOURCE_CHECKOUT"], blobs)
        save("preflight", gate)
        save("checksums", expected)
        with httpx.Client(
            base_url=url,
            headers={"Authorization": "Token " + token},
            trust_env=False,
            follow_redirects=False,
            timeout=90,
        ) as client:

            def request(label, method, endpoint, **kwargs):
                nonlocal mutated
                save(
                    label + "-intent",
                    {
                        "method": method,
                        "endpoint": endpoint,
                        "parameters": kwargs.get("json", kwargs.get("data")),
                    },
                )
                if method == "POST":
                    mutated = True
                response = client.request(method, "/api/v2/" + endpoint, **kwargs)
                save(label, {"status": response.status_code, "body": response.json()})
                assert response.status_code == (201 if method == "POST" else 200)
                return response.json()

            scope = request("ready", "GET", "product_types/3/")
            assert scope["name"] == "DDSLAB Integration"
            assert request("isolation", "GET", "products/", params={"name": name})["count"] == 0
            product = request(
                "product",
                "POST",
                "products/",
                json={"name": name, "description": "Synthetic derived control", "prod_type": 3},
            )
            assert (
                request("product-readback", "GET", f"products/{product['id']}/")["prod_type"] == 3
            )
            engagement = request(
                "engagement",
                "POST",
                "engagements/",
                json={
                    "name": name,
                    "product": product["id"],
                    "target_start": date.today().isoformat(),
                    "target_end": date.today().isoformat(),
                    "status": "In Progress",
                    "engagement_type": "CI/CD",
                    "deduplication_on_engagement": True,
                },
            )
            er = request("engagement-readback", "GET", f"engagements/{engagement['id']}/")
            assert er["product"] == product["id"] and er["deduplication_on_engagement"] is True
            tid, states = None, []
            for phase, blob in zip(("initial", "changed"), blobs, strict=True):
                form = dict(
                    scan_type="SARIF",
                    minimum_severity="Info",
                    deduplication_execution_mode="sync",
                    auto_create_context="false",
                    push_to_jira="false",
                    close_old_findings_product_scope="false",
                    close_old_findings="true" if tid else "false",
                )
                form.update(
                    {"test": str(tid), "do_not_reactivate": "false"}
                    if tid
                    else {"engagement": str(engagement["id"])}
                )
                body = request(
                    phase,
                    "POST",
                    "reimport-scan/" if tid else "import-scan/",
                    data=form,
                    files={"file": ("synthetic.sarif", blob, "application/json")},
                )
                require_complete(body)
                assert tid is None or body["test_id"] == tid
                tid = body["test_id"]
                assert (
                    request(phase + "-test", "GET", f"tests/{tid}/")["engagement"]
                    == engagement["id"]
                )
                rows = read_findings(
                    client, tid, lambda label, obj, p=phase: save(p + "-" + label, obj)
                )
                normalized = normalize(dict(count=len(rows), next=None, results=rows), tid)
                rules = {r["id"]: r["vuln_id_from_tool"] for r in rows}
                for row in normalized:
                    row["vuln_id_from_tool"] = rules[row["id"]]
                save(phase + "-findings", normalized)
                states.append(normalized)
                if phase == "initial":
                    assert len(normalized) == 143
                    assert all(
                        r["active"] and not r["is_mitigated"] and not r["duplicate"]
                        for r in normalized
                    )
                    assert {r["hash_code"]: r["vuln_id_from_tool"] for r in normalized} == {
                        r["hash"]: r["rule"] for r in gate["parsed"][0]
                    }
            evaluate(*states, *gate["parsed"], tid)
            save("summary", dict(outcome="PASS", test=tid, before=states[0], after=states[1]))
    except Exception as exc:
        outcome = "FAIL" if isinstance(exc, AssertionError) and mutated else "INCONCLUSIVE"
        if isinstance(exc, IncompleteReadback):
            outcome = "INCONCLUSIVE"
        save(
            "failure",
            dict(
                outcome=outcome,
                exception_type=type(exc).__name__,
                mutation_may_have_occurred=mutated,
                retry=False,
            ),
        )
        raise RuntimeError(
            "Stopped; inspect sanitized evidence, never retry automatically"
        ) from None

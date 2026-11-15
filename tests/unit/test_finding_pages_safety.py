import httpx
import pytest

from lab.experiment_runner import redact
from lab.finding_pages import IncompleteReadback, read_findings


def test_real_page_shape_and_metadata_redaction():
    calls = []
    evidence = []

    def handle(request):
        calls.append(request)
        offset = int(request.url.params["offset"])
        ids = range(offset + 1, min(offset + 101, 144))
        return httpx.Response(
            200,
            json=dict(
                count=143,
                results=[dict(id=i, test=7) for i in ids],
                next=(
                    "http://127.0.0.1:18080/api/v2/findings/?test=7&limit=100&offset=100&ordering=id"
                    if offset == 0
                    else None
                ),
            ),
        )

    with httpx.Client(
        base_url="http://127.0.0.1:18080", transport=httpx.MockTransport(handle)
    ) as client:
        rows = read_findings(client, 7, lambda name, obj: evidence.append(obj))
    assert len(rows) == 143 and len(calls) == 2
    assert "synthetic-secret" not in str(redact({"text": "synthetic-secret"}, "synthetic-secret"))
    assert not any("Authorization" in str(x) for x in evidence)


@pytest.mark.parametrize("status", [301, 302, 307, 500])
def test_redirect_and_missing_page(status):
    with httpx.Client(
        base_url="http://127.0.0.1:18080",
        transport=httpx.MockTransport(lambda r: httpx.Response(status)),
    ) as client:
        with pytest.raises(IncompleteReadback):
            read_findings(client, 7, lambda *args: None)


def test_page_bound_and_ownership():
    with httpx.Client(base_url="http://127.0.0.1:18080") as client:
        with pytest.raises(IncompleteReadback):
            read_findings(client, 7, lambda *args: None, max_pages=0)
    body = dict(count=1, next=None, results=[dict(id=1, test=8)])
    with httpx.Client(
        base_url="http://127.0.0.1:18080",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    ) as client:
        with pytest.raises(IncompleteReadback):
            read_findings(client, 7, lambda *args: None)

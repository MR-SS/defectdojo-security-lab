import httpx
import pytest

from lab.finding_pages import IncompleteReadback, read_findings


def run(pages):
    calls = []

    def handle(request):
        calls.append(str(request.url))
        item = pages[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return httpx.Response(200, json=item)

    with httpx.Client(
        base_url="http://127.0.0.1:18080", transport=httpx.MockTransport(handle)
    ) as client:
        return read_findings(client, 9, lambda *args: None)


def page(ids, count, next_url=None):
    return dict(count=count, next=next_url, results=[dict(id=i, test=9) for i in ids])


NEXT = "http://127.0.0.1:18080/api/v2/findings/?test=9&limit=100&offset=1&ordering=id"


def test_complete_pages():
    assert len(run([page([1], 1)])) == 1
    assert len(run([page([1], 2, NEXT), page([2], 2)])) == 2


@pytest.mark.parametrize(
    "pages",
    [
        [page([1], 2, NEXT), page([1], 2)],
        [page([1], 3, NEXT), page([2], 3, NEXT)],
        [page([1], 2, "https://example.org/")],
        [page([1], 2, NEXT), page([2], 3)],
        [page([1], 2, NEXT), page([], 2, NEXT)],
        [page([1], 2)],
        [page([1], 2, NEXT), httpx.ReadTimeout("private detail")],
        [dict(results=[], next=None)],
    ],
)
def test_incomplete(pages):
    with pytest.raises(IncompleteReadback):
        run(pages)

"""Fail-closed readbacks; never follow server-provided URLs or redirects."""

from urllib.parse import parse_qs, urlsplit

import httpx


class IncompleteReadback(RuntimeError):
    """An INCONCLUSIVE readback, not a product vulnerability."""


def read_findings(client, test_id, save, max_pages=20):
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise IncompleteReadback("invalid page bound")
    origin = urlsplit(str(client.base_url))
    rows, ids, cursors = [], set(), set()
    offset, total = 0, None
    for number in range(max_pages):
        try:
            response = client.get(
                "/api/v2/findings/",
                params={"test": test_id, "limit": 100, "offset": offset, "ordering": "id"},
                follow_redirects=False,
            )
            save(f"page-{number}", {"status": response.status_code, "offset": offset})
            if response.status_code != 200:
                raise IncompleteReadback("unexpected status or redirect")
            body = response.json()
            count, batch, following = body["count"], body["results"], body["next"]
            if type(count) is not int or count < 0 or not isinstance(batch, list):
                raise IncompleteReadback("invalid count/results")
            total = count if total is None else total
            if total != count:
                raise IncompleteReadback("count drift")
            for row in batch:
                if type(row.get("id")) is not int or row["id"] in ids or row.get("test") != test_id:
                    raise IncompleteReadback("duplicate identity or ownership")
                ids.add(row["id"])
            rows.extend(batch)
            save(
                f"page-{number}-metadata",
                {
                    "count": count,
                    "received": len(batch),
                    "ids": [r["id"] for r in batch],
                    "has_next": following is not None,
                },
            )
            if following is None:
                if len(rows) != total:
                    raise IncompleteReadback("truncated readback")
                return rows
            if not batch or len(rows) >= total or not isinstance(following, str):
                raise IncompleteReadback("empty or excess continuation")
            target = urlsplit(following)
            if (
                (target.scheme, target.hostname, target.port)
                != (origin.scheme, origin.hostname, origin.port)
                or target.username
                or target.password
                or target.fragment
                or target.path != "/api/v2/findings/"
            ):
                raise IncompleteReadback("unsafe next URL")
            query = parse_qs(target.query, strict_parsing=True)
            expected = {
                "test": [str(test_id)],
                "limit": ["100"],
                "offset": [str(offset + len(batch))],
                "ordering": ["id"],
            }
            if query != expected or following in cursors:
                raise IncompleteReadback("invalid or repeated cursor")
            cursors.add(following)
            offset += len(batch)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            save(
                f"page-{number}-error",
                {"outcome": "INCONCLUSIVE", "exception_type": type(exc).__name__},
            )
            raise IncompleteReadback("unavailable or malformed page") from None
    raise IncompleteReadback("page bound exceeded")

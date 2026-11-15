"""Exact set oracle for the sanitized 143-to-142 control."""

from lab.finding_pages import IncompleteReadback


def require_complete(body):
    if (
        body.get("deduplication_complete") is not True
        or body.get("deduplication_execution_mode") != "sync"
    ):
        raise IncompleteReadback("processing incomplete")


def evaluate(before, after, initial, changed, tid):
    expected = {r["hash"]: r["rule"] for r in initial}
    retained = {r["hash"]: r["rule"] for r in changed}
    assert len(initial) == len(expected) == 143
    assert len(changed) == len(retained) == 142
    assert retained.items() <= expected.items()
    assert len(expected.keys() - retained.keys()) == 1
    old = {r["id"]: r for r in before}
    new = {r["id"]: r for r in after}
    assert len(before) == len(after) == len(old) == len(new) == 143
    assert old.keys() == new.keys()
    for rows in (before, after):
        assert {r["hash_code"]: r["vuln_id_from_tool"] for r in rows} == expected
        assert all(r["test"] == tid and r["duplicate"] is False for r in rows)
    for fid, row in old.items():
        assert row["active"] is True and row["is_mitigated"] is False
        final = new[fid]
        assert final["hash_code"] == row["hash_code"]
        assert final["vuln_id_from_tool"] == row["vuln_id_from_tool"]
        removed = row["hash_code"] not in retained
        assert final["active"] is (not removed)
        assert final["is_mitigated"] is removed

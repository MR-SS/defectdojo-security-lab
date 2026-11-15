import copy

import pytest


def test_exact_oracle():
    from lab.semgrep_control import evaluate, require_complete

    parsed = [dict(hash=str(i), rule=f"r{i}", uid=None) for i in range(143)]
    before = [
        dict(
            id=i + 1,
            test=7,
            hash_code=str(i),
            vuln_id_from_tool=f"r{i}",
            unique_id_from_tool=None,
            active=True,
            is_mitigated=False,
            duplicate=False,
        )
        for i in range(143)
    ]
    after = copy.deepcopy(before)
    after[1].update(active=False, is_mitigated=True)
    evaluate(before, after, parsed, parsed[:1] + parsed[2:], 7)
    for mutation in ("mass", "replace", "missing", "duplicate", "ownership", "wrong_removed"):
        bad = copy.deepcopy(after)
        if mutation == "mass":
            bad[0].update(active=False, is_mitigated=True)
        elif mutation == "replace":
            bad[0]["id"] = 999
        elif mutation == "missing":
            bad.pop()
        elif mutation == "duplicate":
            bad[-1] = bad[0]
        elif mutation == "ownership":
            bad[0]["test"] = 8
        else:
            bad[1].update(active=True, is_mitigated=False)
            bad[2].update(active=False, is_mitigated=True)
        with pytest.raises(AssertionError):
            evaluate(before, bad, parsed, parsed[:1] + parsed[2:], 7)
    require_complete(dict(deduplication_complete=True, deduplication_execution_mode="sync"))
    with pytest.raises(RuntimeError):
        require_complete(dict(deduplication_complete=False, deduplication_execution_mode="async"))

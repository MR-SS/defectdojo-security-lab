import pytest

from lab.semgrep_analysis import identity_statistics


def test_ambiguous_placeholder_and_hash_retention():
    before = [dict(raw='requires login', uid=None, hash=str(i)) for i in range(3)]
    after = before[:2]
    result = identity_statistics(before, after)
    assert result['initial']['raw_collision_rows'] == 3
    assert result['initial']['effective_nulls'] == 3
    assert result['retained_hashes'] == 2
    assert result['removed_hashes'] == 1
    assert result['added_hashes'] == 0
    assert result['unambiguous_hash_control'] is True


def test_hash_collision_is_not_a_valid_control():
    rows = [dict(raw='same', uid=None, hash='same') for _ in range(2)]
    assert not identity_statistics(rows, rows)['unambiguous_hash_control']


def test_missing_hash_rejected():
    with pytest.raises(ValueError):
        identity_statistics([dict(raw=None, uid=None, hash=None)], [])

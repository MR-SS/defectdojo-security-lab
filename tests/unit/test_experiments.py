import json

import pytest

from lab import experiments
from lab.experiment_runner import evaluate, normalize, redact, run
from lab.fixtures import generic_findings


def test_mutations_change_only_one_controlled_field():
    baseline = json.loads(generic_findings(3).content)
    for case, field in [('M1-A', 'file_path'), ('M1-B', 'unique_id_from_tool'),
                        ('M1-C', 'severity')]:
        mutated = json.loads(experiments.fixture(case))
        assert mutated['findings'][1:] == baseline['findings'][1:]
        changed = {k for k in baseline['findings'][0]
                   if baseline['findings'][0][k] != mutated['findings'][0][k]}
        assert changed == {field}
        assert experiments.fixture(case) == experiments.fixture(case)


def test_redaction_in_nested_keys_and_free_text():
    value = {'cookie': 'private', 'nested': {'password': 'private'}, 'message': 'a live-token'}
    text = json.dumps(redact(value, 'live-token'))
    assert 'private' not in text and 'live-token' not in text


def test_denied_execution_never_probes(monkeypatch):
    monkeypatch.delenv('DDSLAB_RUN_INTEGRATION', raising=False)
    monkeypatch.delenv('DDSLAB_APPROVE_SCENARIO', raising=False)
    with pytest.raises(PermissionError):
        run('M1-A')


def test_normalization_keeps_repeated_uid_and_checks_ownership():
    rows = [{'id': i, 'test': 20, 'unique_id_from_tool': 'same',
             'active': True, 'is_mitigated': False, 'duplicate': False} for i in (1, 2)]
    body = {'count': 2, 'results': rows, 'next': None}
    assert len(normalize(body, 20)) == 2
    with pytest.raises(ValueError):
        normalize(body, 21)
    body['count'] = 3
    with pytest.raises(ValueError):
        normalize(body, 20)


@pytest.mark.parametrize('case', experiments.CASES)
def test_oracle_rejects_unintended_reactivation(case):
    before = [{'id': i, 'test': 20, 'unique_id_from_tool': f'finding-{i:04d}',
               'hash_code': str(i), 'active': True, 'is_mitigated': False,
               'duplicate': False} for i in range(3)]
    after = [dict(r) for r in before]
    after[2]['is_mitigated'] = True
    with pytest.raises(AssertionError):
        evaluate(case, before, after)

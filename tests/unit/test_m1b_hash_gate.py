import json

import pytest

from lab import experiments
from lab.fixtures import generic_findings


@pytest.mark.parametrize('always', [[], ['service']])
def test_m1b_hash_equivalence(always):
    config = dict(algorithm='hash_code', hash_fields=None, always=always,
                  custom_hash_override=False)
    result = experiments.validate_m1b_hash(
        config, generic_findings(3).content, experiments.fixture('M1-B'))
    assert result['before_hashes'] == result['after_hashes']
    assert result['services'] == [None, None, None]
    assert result['changed_hash_indices'] == []


@pytest.mark.parametrize('key,value', [
    ('always', ['service', 'service']), ('always', ['severity']),
    ('always', ['service', 'severity']), ('hash_fields', ['title']),
    ('custom_hash_override', True), ('custom_hash_override', None),
    ('algorithm', 'unique_id_from_tool'),
])
def test_m1b_reject_configuration(key, value):
    config = dict(algorithm='hash_code', hash_fields=None, always=['service'],
                  custom_hash_override=False)
    config[key] = value
    with pytest.raises(ValueError):
        experiments.validate_m1b_hash(
            config, generic_findings(3).content, experiments.fixture('M1-B'))


@pytest.mark.parametrize('index,key,value', [
    (0, 'service', ''), (1, 'service', 'explicit'),
    (0, 'file_path', 'changed.py'), (1, 'unique_id_from_tool', 'changed-control'),
    (0, 'unique_id_from_tool', 'finding-0000'),
])
def test_m1b_reject_fixture_drift(index, key, value):
    changed = json.loads(experiments.fixture('M1-B'))
    changed['findings'][index][key] = value
    config = dict(algorithm='hash_code', hash_fields=None, always=['service'],
                  custom_hash_override=False)
    with pytest.raises(ValueError):
        experiments.validate_m1b_hash(config, generic_findings(3).content, json.dumps(changed))

import json

import pytest

from lab import experiments
from lab.fixtures import generic_findings


@pytest.mark.parametrize('always', [[], ['service']])
def test_m1c_hash_equivalence(always):
    config = dict(algorithm='hash_code', hash_fields=None, always=always,
                  custom_hash_override=False)
    result = experiments.validate_m1c_hash(
        config, generic_findings(3).content, experiments.fixture('M1-C'))
    assert result['before_hashes'] == result['after_hashes']
    assert result['services'] == [None, None, None]


@pytest.mark.parametrize('key,value', [
    ('always', ['severity']), ('always', ['service', 'service']),
    ('hash_fields', ['title']), ('custom_hash_override', True),
    ('algorithm', 'unique_id_from_tool'),
])
def test_m1c_reject_configuration(key, value):
    config = dict(algorithm='hash_code', hash_fields=None, always=['service'],
                  custom_hash_override=False)
    config[key] = value
    with pytest.raises(ValueError):
        experiments.validate_m1c_hash(
            config, generic_findings(3).content, experiments.fixture('M1-C'))


@pytest.mark.parametrize('index,key,value', [
    (0, 'service', ''), (1, 'service', 'explicit'),
    (0, 'file_path', 'changed.py'), (1, 'severity', 'Critical'),
    (0, 'severity', 'Low'), (0, 'unique_id_from_tool', 'changed'),
])
def test_m1c_reject_fixture_drift(index, key, value):
    changed = json.loads(experiments.fixture('M1-C'))
    changed['findings'][index][key] = value
    config = dict(algorithm='hash_code', hash_fields=None, always=['service'],
                  custom_hash_override=False)
    with pytest.raises(ValueError):
        experiments.validate_m1c_hash(config, generic_findings(3).content, json.dumps(changed))

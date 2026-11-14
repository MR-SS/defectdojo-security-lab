import json

import pytest

from lab import experiments
from lab.fixtures import generic_findings


def test_m1a_service_gate():
    config = {'algorithm': 'hash_code', 'hash_fields': None,
              'always': ['service'], 'custom_hash_override': False}
    result = experiments.validate_m1a_hash(config, generic_findings(3).content,
                                         experiments.fixture('M1-A'))
    assert result['services'] == [None, None, None]
    assert result['changed_hash_indices'] == [0]


@pytest.mark.parametrize('key,value', [
    ('always', ['severity']), ('always', ['service', 'service']),
    ('hash_fields', ['file_path']), ('custom_hash_override', True),
    ('algorithm', 'unique_id_from_tool'),
])
def test_reject_unsupported_hash_configuration(key, value):
    config = {'algorithm': 'hash_code', 'hash_fields': None,
              'always': ['service'], 'custom_hash_override': False}
    config[key] = value
    with pytest.raises(ValueError):
        experiments.validate_m1a_hash(config, generic_findings(3).content,
                                     experiments.fixture('M1-A'))


@pytest.mark.parametrize('service', ['', 'explicit-service', 0])
def test_reject_service_drift(service):
    changed = json.loads(experiments.fixture('M1-A'))
    changed['findings'][0]['service'] = service
    config = {'algorithm': 'hash_code', 'hash_fields': None,
              'always': ['service'], 'custom_hash_override': False}
    with pytest.raises(ValueError):
        experiments.validate_m1a_hash(config, generic_findings(3).content,
                                     json.dumps(changed))


def test_allow_empty_always_and_explicit_null():
    changed = json.loads(experiments.fixture('M1-A'))
    changed['findings'][0]['service'] = None
    config = {'algorithm': 'hash_code', 'hash_fields': [],
              'always': [], 'custom_hash_override': False}
    assert experiments.validate_m1a_hash(config, generic_findings(3).content,
                                         json.dumps(changed))['changed_hash_indices'] == [0]

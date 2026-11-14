"""Deterministic identity experiments; no network access at import time."""
import hashlib
import json

from lab.fixtures import generic_findings

CASES = ('R1', 'I1', 'M1-A', 'M1-B', 'M1-C')


def fixture(case):
    payload = json.loads(generic_findings(3).content)
    if case in ('R1', 'I1'):
        payload['findings'] = [payload['findings'][i] for i in (0, 2)]
    elif case == 'M1-A':
        payload['findings'][0]['file_path'] = 'src/moved_example_0.py'
    elif case == 'M1-B':
        payload['findings'][0]['unique_id_from_tool'] = 'finding-mutated-0000'
    elif case == 'M1-C':
        payload['findings'][0]['severity'] = 'Critical'
    else:
        raise ValueError('unknown experiment')
    return (json.dumps(payload, indent=2, sort_keys=True) + '\n').encode()


def validate_m1a_hash(config, initial, changed):
    """Validate only the prepared no-service M1-A contract; fail closed."""
    return _validate_identity_hash(config, initial, changed, 'file_path', [0])


def validate_m1b_hash(config, initial, changed):
    """Require UID-only mutation and identical legacy hashes for all findings."""
    return _validate_identity_hash(config, initial, changed, 'unique_id_from_tool', [])


def validate_m1c_hash(config, initial, changed):
    """Require severity-only mutation and identical hashes, not severity reconciliation."""
    return _validate_identity_hash(config, initial, changed, 'severity', [])


def _validate_identity_hash(config, initial, changed, field, expected_indices):
    if (config.get('algorithm') != 'hash_code'
            or config.get('hash_fields') not in (None, [])
            or config.get('always') not in ([], ['service'])
            or config.get('custom_hash_override') is not False):
        raise ValueError('unsupported hash configuration')
    left, right = json.loads(initial)['findings'], json.loads(changed)['findings']
    if len(left) != 3 or len(right) != 3:
        raise ValueError('expected three findings')
    services = [r.get('service') for r in left]
    if services != [r.get('service') for r in right]:
        raise ValueError('unequal effective service values')
    # Runner omits request service; explicit fixture services would also change closure scope.
    if any(s is not None for s in services):
        raise ValueError('prepared experiment requires absent/null service')
    for i, (a, b) in enumerate(zip(left, right, strict=True)):
        differences = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
        if differences != ({field} if i == 0 else set()):
            raise ValueError('unexpected fixture mutation')

    def digest(row):
        text = (row['title'] + str(row.get('cwe', 0)) + str(row.get('line'))
                + str(row.get('file_path')) + row['description'])
        return hashlib.sha256(text.casefold().encode('utf-8').strip()).hexdigest()

    before, after = [digest(r) for r in left], [digest(r) for r in right]
    changed_indices = [i for i in range(3) if before[i] != after[i]]
    if changed_indices != expected_indices:
        raise ValueError('effective hash delta does not match scenario')
    return {'services': services, 'before_hashes': before, 'after_hashes': after,
            'changed_hash_indices': changed_indices}

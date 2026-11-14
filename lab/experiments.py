"""Deterministic identity experiments; no network access at import time."""
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

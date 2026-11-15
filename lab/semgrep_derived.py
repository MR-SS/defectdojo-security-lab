"""Mechanism-derived synthetic reports; never read original report content."""
import json


def derived_pair():
    results = []
    for index in range(143):
        results.append({
            'ruleId': f'ddslab/rule-{index % 30:02d}',
            'level': 'warning',
            'message': {'text': f'Synthetic finding {index:03d}'},
            'fingerprints': {'matchBasedId/v1': 'requires login'},
            'locations': [{'physicalLocation': {
                'artifactLocation': {'uri': f'synthetic/file-{index:03d}.py'},
                'region': {'startLine': 10}}}],
        })
    blobs = []
    for rows in (results, results[:1] + results[2:]):
        report = {'version': '2.1.0', 'runs': [{
            'tool': {'driver': {'name': 'DDSLAB derived synthetic SARIF'}},
            'results': rows}]}
        blobs.append((json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    return tuple(blobs)

"""Synthetic parser-only ReplicaSet rollout controls; no application writes."""

import copy
import json

HANDLERS = ('vulnerabilities', 'checks', 'secrets')


def pair(handler):
    entries = {
        'vulnerabilities': dict(vulnerabilityID='CVE-2023-23914', severity='HIGH',
                               resource='synthetic-package', installedVersion='1.0',
                               fixedVersion='1.1', title='Synthetic vulnerability'),
        'checks': dict(checkID='KSV001', severity='HIGH', title='Synthetic check',
                       description='Synthetic configuration observation'),
        'secrets': dict(ruleID='synthetic-rule', severity='HIGH', title='Synthetic marker',
                        category='synthetic', match='NOT_A_CREDENTIAL', target='synthetic.txt'),
    }
    kinds = dict(vulnerabilities='VulnerabilityReport', checks='ConfigAuditReport',
                 secrets='ExposedSecretReport')
    reports = []
    for name in ('alpha-6b7c8d9f5b', 'beta-6b7c8d9f5b'):
        reports.append(dict(kind=kinds[handler], metadata=dict(labels={
            'trivy-operator.resource.kind': 'ReplicaSet',
            'trivy-operator.resource.name': name,
            'trivy-operator.resource.namespace': 'synthetic',
            'trivy-operator.container.name': 'app',
        }), report={handler: [entries[handler]],
                    'artifact': {'repository': 'synthetic/image', 'tag': 'fixed',
                                 'digest': 'sha256:' + 'a' * 64}}))
    changed = copy.deepcopy(reports)
    changed[0]['metadata']['labels']['trivy-operator.resource.name'] = 'alpha-7c8d9f6b5c'
    return tuple((json.dumps(r, indent=2, sort_keys=True) + '\n').encode()
                 for r in (reports, changed))

"""Separately authorized SARIF control; never run during offline validation."""
import hashlib
import json
import os
import subprocess
import uuid
from datetime import date
from pathlib import Path

import httpx
import pytest

from lab.experiment_runner import normalize, redact
from lab.sarif_identity import evaluate_sarif, sarif_fixture
from lab.sarif_regressions import evaluate, load_pair


@pytest.mark.integration
@pytest.mark.parametrize('case', ['SARIF-14205', 'S2', 'S3-A', 'S3-B'])
def test_sarif_identity(case):
    if (os.getenv('DDSLAB_RUN_INTEGRATION') != '1'
            or os.getenv('DDSLAB_APPROVE_SCENARIO') != case):
        pytest.skip('separate exact-scenario authorization required')
    source = os.environ['DDSLAB_SOURCE_CHECKOUT']
    sha = subprocess.check_output(['git', '-C', source, 'rev-parse', 'HEAD'], text=True).strip()
    assert sha == subprocess.check_output(
        ['git', '-C', source, 'rev-parse', '3.5.101^{commit}'], text=True).strip()
    code = '''import json
from django.conf import settings
from dojo.utils import get_custom_method
print('CONFIG:'+json.dumps([settings.DEDUPLICATION_ALGORITHM_PER_PARSER.get('SARIF'),
settings.HASHCODE_FIELDS_PER_SCANNER.get('SARIF'),settings.HASH_CODE_FIELDS_ALWAYS,
bool(get_custom_method('FINDING_COMPUTE_HASH_METHOD'))]))'''
    raw = subprocess.check_output(['docker', 'exec', 'ddslab-uwsgi-1', 'python',
                                   'manage.py', 'shell', '-c', code], text=True)
    config = json.loads(raw.split('CONFIG:')[-1])
    assert config[0] == 'unique_id_from_tool_or_hash_code'
    assert config[1] in (None, []) and config[2] in ([], ['service']) and config[3] is False
    import ipaddress
    from urllib.parse import urlsplit
    url = os.environ['DDSLAB_API_BASE_URL']
    assert ipaddress.ip_address(urlsplit(url).hostname).is_loopback
    assert os.environ['DDSLAB_PRODUCT_TYPE_ID'] == '3'
    token = os.environ['DDSLAB_API_TOKEN']
    name = 'ddslab-sarif-' + uuid.uuid4().hex
    path = Path('evidence') / name
    path.mkdir(mode=0o700)

    def save(label, value):
        with (path / (label + '.json')).open('x') as stream:
            json.dump(redact(value, token), stream, indent=2)

    save('source-config', {'source': sha, 'config': config})
    blobs = ((sarif_fixture(10), sarif_fixture(11)) if case == 'SARIF-14205'
             else load_pair(case))
    parser_code = '''import io,json
from dojo.tools.sarif.parser import SarifParser
from dojo.tools.utils import drop_ambiguous_repeated_unique_ids
reports = ''' + repr([b.decode() for b in blobs]) + '''
out=[]
for report in reports:
    rows=SarifParser().get_findings(io.StringIO(report),None)
    parsed=[{'rule':f.vuln_id_from_tool,'uid':f.unique_id_from_tool} for f in rows]
    drop_ambiguous_repeated_unique_ids(rows)
    out.append({'parsed':parsed,'effective':[{'rule':f.vuln_id_from_tool,
        'uid':f.unique_id_from_tool,'hash':f.compute_hash_code_legacy()} for f in rows]})
print('PARSED:'+json.dumps(out))'''
    parsed_raw = subprocess.check_output(
        ['docker', 'exec', 'ddslab-uwsgi-1', 'python', 'manage.py', 'shell', '-c', parser_code],
        text=True)
    parsed = json.loads(parsed_raw.split('PARSED:')[-1])
    save('parsed-identities', parsed)
    for blob, result in zip(blobs, parsed, strict=True):
        assert len(result['effective']) == len(json.loads(blob)['runs'][0]['results'])
    with httpx.Client(base_url=url, headers={'Authorization': 'Token ' + token},
                      trust_env=False, follow_redirects=False, timeout=90) as client:
        def request(label, method, endpoint, **kwargs):
            save(label + '-intent', {'method': method, 'endpoint': endpoint,
                                     'parameters': kwargs.get('json', kwargs.get('data'))})
            response = client.request(method, '/api/v2/' + endpoint, **kwargs)
            save(label, {'status': response.status_code, 'body': response.json()})
            assert response.status_code == (201 if method == 'POST' else 200)
            return response.json()

        request('ready', 'GET', 'product_types/3/')
        assert request('isolation', 'GET', 'products/', params={'name': name})['count'] == 0
        product = request('product', 'POST', 'products/', json={
            'name': name, 'description': 'Synthetic SARIF control', 'prod_type': 3})
        request('product-readback', 'GET', f'products/{product["id"]}/')
        engagement = request('engagement', 'POST', 'engagements/', json={
            'name': name, 'product': product['id'], 'target_start': date.today().isoformat(),
            'target_end': date.today().isoformat(), 'status': 'In Progress',
            'engagement_type': 'CI/CD', 'deduplication_on_engagement': True})
        request('engagement-readback', 'GET', f'engagements/{engagement["id"]}/')
        tid = None
        states = []
        for label, blob in zip(('initial', 'changed'), blobs, strict=True):
            save(label + '-fixture', {'sha256': hashlib.sha256(blob).hexdigest(),
                                     'payload': json.loads(blob)})
            data = {'scan_type': 'SARIF', 'minimum_severity': 'Info',
                    'deduplication_execution_mode': 'sync', 'auto_create_context': 'false',
                    'push_to_jira': 'false', 'close_old_findings_product_scope': 'false',
                    'close_old_findings': 'true' if tid else 'false'}
            data.update({'test': str(tid), 'do_not_reactivate': 'false'} if tid else
                        {'engagement': str(engagement['id'])})
            response = request(label, 'POST', 'reimport-scan/' if tid else 'import-scan/',
                               data=data,
                               files={'file': ('synthetic.sarif', blob, 'application/json')})
            assert response['deduplication_complete'] is True
            current = response['test_id']
            assert tid is None or current == tid
            tid = current
            test = request(label + '-test', 'GET', f'tests/{tid}/')
            assert test['engagement'] == engagement['id']
            body = request(label + '-findings', 'GET', 'findings/',
                           params={'test': tid, 'limit': 100})
            rows = normalize(body, tid)
            rules = {row['id']: row.get('vuln_id_from_tool') for row in body['results']}
            for row in rows:
                row['vuln_id_from_tool'] = rules[row['id']]
            states.append(rows)
        if case == 'SARIF-14205':
            evaluate_sarif(*states)
        else:
            evaluate(case, *states)
        save('summary', {'outcome': 'PASS', 'before': states[0], 'after': states[1]})

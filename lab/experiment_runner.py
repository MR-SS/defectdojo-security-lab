"""Bounded, independently authorized experiments. Never retry a mutation."""
import hashlib
import ipaddress
import json
import os
import subprocess
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from lab.evidence import sanitize
from lab.experiments import CASES, fixture, validate_m1a_hash, validate_m1b_hash, validate_m1c_hash
from lab.fixtures import generic_findings


def redact(value, token):
    """Redact structured secrets and the supplied token even inside free text."""
    text = json.dumps(sanitize(value), default=str)
    return json.loads(text.replace(token, '[REDACTED]')) if token else json.loads(text)


def probe(test_id=None):
    """Read-only application DB and effective matching configuration probe."""
    code = (
        'import json; from django.db import connection; from django.conf import settings; '
        'from dojo.utils import get_custom_method; connection.ensure_connection(); '
        'd={"database_ready":True, "algorithm":'
        'settings.DEDUPLICATION_ALGORITHM_PER_PARSER.get("Generic Findings Import"),'
        '"hash_fields":settings.HASHCODE_FIELDS_PER_SCANNER.get("Generic Findings Import"),'
        '"always":getattr(settings,"HASH_CODE_FIELDS_ALWAYS",[]),'
        '"custom_hash_override":bool(get_custom_method("FINDING_COMPUTE_HASH_METHOD"))}; '
    )
    if test_id is not None:
        if type(test_id) is not int:
            raise ValueError('invalid Test ID')
        code += (
            f'from dojo.models import Test; t=Test.objects.get(pk={test_id}); '
            'd.update(algorithm=t.deduplication_algorithm,hash_fields=t.hash_code_fields); '
        )
    code += 'print("LABJSON:"+json.dumps(d))'
    result = subprocess.run(
        ['docker', 'exec', 'ddslab-uwsgi-1', 'python', 'manage.py', 'shell', '-c', code],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if result.returncode:
        raise RuntimeError('read-only DB/config probe failed')
    return json.loads(result.stdout.split('LABJSON:')[-1])


def normalize(body, tid):
    rows = body.get('results')
    if not isinstance(rows, list) or body.get('next') or body.get('count') != len(rows):
        raise ValueError('incomplete finding response')
    keys = ('id', 'test', 'unique_id_from_tool', 'hash_code', 'active', 'is_mitigated',
            'mitigated', 'duplicate', 'duplicate_finding', 'false_p', 'out_of_scope',
            'risk_accepted', 'service', 'severity', 'file_path', 'line')
    for row in rows:
        if type(row.get('id')) is not int or row.get('test') != tid:
            raise ValueError('ambiguous identity or ownership')
        if any(type(row.get(k)) is not bool for k in ('active', 'is_mitigated', 'duplicate')):
            raise ValueError('ambiguous lifecycle state')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate response IDs')
    # Do not index by UID: M1-A intentionally retains a UID across two rows.
    return sorted([{k: r.get(k) for k in keys} for r in rows], key=lambda r: r['id'])


def evaluate(case, before, after, second=None):
    assert len(before) == 3
    assert all(r['active'] and not r['is_mitigated'] and not r['duplicate'] for r in before)
    old = {r['id']: r for r in before}
    current = {r['id']: r for r in after}
    assert old.keys() <= current.keys()
    for fid, row in old.items():
        new = current[fid]
        closed = (case in ('R1', 'I1') and row['unique_id_from_tool'] == 'finding-0001')
        closed |= case == 'M1-A' and row['unique_id_from_tool'] == 'finding-0000'
        assert new['test'] == row['test'] and new['hash_code'] == row['hash_code']
        assert new['active'] is (not closed) and new['is_mitigated'] is closed
        assert not new['duplicate']
    if case == 'M1-A':
        added = [r for r in after if r['id'] not in old]
        assert len(after) == 4 and len(added) == 1
        a = next(r for r in before if r['unique_id_from_tool'] == 'finding-0000')
        assert added[0]['unique_id_from_tool'] == a['unique_id_from_tool']
        assert added[0]['hash_code'] != a['hash_code']
        assert added[0]['active'] and not added[0]['is_mitigated']
    else:
        assert len(after) == 3
    if case == 'I1':
        assert second is not None and len(second) == 2
        assert {r['unique_id_from_tool'] for r in second} == {'finding-0000', 'finding-0002'}
        assert all(r['id'] not in old and r['test'] != before[0]['test'] for r in second)
    # Severity/UID field reconciliation is observed, not conflated with matching.


def run(case, root=Path('evidence')):
    if case not in CASES or os.getenv('DDSLAB_APPROVE_SCENARIO') != case:
        raise PermissionError('explicit per-scenario approval required')
    if os.getenv('DDSLAB_RUN_INTEGRATION') != '1':
        raise PermissionError('integration opt-in required')
    url = os.environ['DDSLAB_API_BASE_URL']
    parsed = urlsplit(url)
    if not ipaddress.ip_address(parsed.hostname).is_loopback or parsed.username or parsed.password:
        raise ValueError('literal loopback endpoint without credentials required')
    token = os.environ['DDSLAB_API_TOKEN']
    run_dir = root / (case + '-' + uuid.uuid4().hex)
    run_dir.mkdir(parents=True, mode=0o700)

    def save(name, obj):
        with (run_dir / (name + '.json')).open('x') as stream:
            json.dump(redact(obj, token), stream, indent=2)

    config = probe()
    save('configuration', config)
    source = Path(os.environ['DDSLAB_SOURCE_CHECKOUT'])
    commit = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True, timeout=30,
    ).strip()
    tag = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', '3.5.101^{commit}'], text=True, timeout=30,
    ).strip()
    if commit != tag:
        raise RuntimeError('BLOCKED: source checkout is not pinned release')
    save('source', {'commit': commit, 'tag': '3.5.101'})
    images = json.loads(subprocess.check_output(
        ['docker', 'inspect', 'ddslab-uwsgi-1', 'ddslab-nginx-1'], timeout=30,
    ))
    save('images', [{'name': x['Name'], 'image_id': x['Image'],
                     'reference': x['Config']['Image']} for x in images])
    if config['algorithm'] != 'hash_code':
        raise RuntimeError('BLOCKED: expected hash_code algorithm')
    if config['custom_hash_override']:
        raise RuntimeError('BLOCKED: custom hash method')

    initial, changed = generic_findings(3).content, fixture(case)
    if case == 'M1-A':
        save('hash-invariants', validate_m1a_hash(config, initial, changed))
    if case == 'M1-B':
        save('hash-invariants', validate_m1b_hash(config, initial, changed))
    if case == 'M1-C':
        save('hash-invariants', validate_m1c_hash(config, initial, changed))
    save('fixtures', {k: {'sha256': hashlib.sha256(v).hexdigest(), 'payload': json.loads(v)}
                      for k, v in [('initial', initial), ('changed', changed)]})
    with httpx.Client(base_url=url, timeout=90, trust_env=False, follow_redirects=False,
                      headers={'Authorization': 'Token ' + token}) as client:
        def request(name, method, path, **kwargs):
            save(name + '-intent', {'method': method, 'path': path,
                                   'data': kwargs.get('data', kwargs.get('json')),
                                   'params': kwargs.get('params')})
            response = client.request(method, path, **kwargs)
            try:
                body = response.json()
            except ValueError:
                save(name, {'status': response.status_code, 'non_json': True})
                raise RuntimeError('non-JSON API response') from None
            save(name, {'status': response.status_code, 'body': body})
            if response.status_code != (201 if method == 'POST' else 200):
                raise RuntimeError('unexpected HTTP status; do not retry')
            return body

        try:
            for endpoint in ('products', 'engagements', 'tests', 'findings'):
                request('baseline-' + endpoint, 'GET', f'/api/v2/{endpoint}/', params={'limit': 1})
            name = 'ddslab-' + case.lower() + '-' + uuid.uuid4().hex
            assert request('isolation', 'GET', '/api/v2/products/',
                           params={'name': name})['count'] == 0
            p = request('product', 'POST', '/api/v2/products/', json={
                'name': name, 'description': 'Synthetic bounded experiment',
                'prod_type': int(os.environ['DDSLAB_PRODUCT_TYPE_ID'])})
            request('product-readback', 'GET', f'/api/v2/products/{p["id"]}/')
            e = request('engagement', 'POST', '/api/v2/engagements/', json={
                'name': name, 'product': p['id'], 'target_start': date.today().isoformat(),
                'target_end': date.today().isoformat(), 'status': 'In Progress',
                'engagement_type': 'CI/CD', 'deduplication_on_engagement': True})
            er = request('engagement-readback', 'GET', f'/api/v2/engagements/{e["id"]}/')
            assert er['product'] == p['id'] and er['deduplication_on_engagement'] is True
            assert request('empty-tests', 'GET', '/api/v2/tests/',
                           params={'engagement': e['id']})['count'] == 0

            def scan(tag, content, tid=None, close=False):
                form = {'scan_type': 'Generic Findings Import', 'minimum_severity': 'Info',
                        'deduplication_execution_mode': 'sync',
                        'close_old_findings_product_scope': 'false',
                        'auto_create_context': 'false', 'push_to_jira': 'false',
                        'close_old_findings': str(close).lower()}
                if tid is None:
                    form.update(engagement=str(e['id']), test_title=name + '-' + tag)
                else:
                    form.update(test=str(tid), do_not_reactivate='false')
                endpoint = 'import-scan' if tid is None else 'reimport-scan'
                b = request(tag, 'POST', f'/api/v2/{endpoint}/', data=form,
                            files={'file': ('synthetic.json', content, 'application/json')})
                result = b.get('test_id', b.get('test'))
                assert type(result) is int and b.get('test', result) == result
                assert b.get('deduplication_complete') is True
                t = request(tag + '-test', 'GET', f'/api/v2/tests/{result}/')
                assert t['engagement'] == e['id']
                return result

            def states(tag, tid):
                return normalize(request(tag, 'GET', '/api/v2/findings/',
                                         params={'test': tid, 'limit': 100}), tid)

            t1 = scan('initial-import', initial)
            before = states('before', t1)
            effective = probe(t1)
            save('effective-algorithm', effective)
            assert effective['algorithm'] == config['algorithm']
            assert effective['hash_fields'] == config['hash_fields']
            assert len(before) == 3
            assert all(r['active'] and not r['is_mitigated'] for r in before)
            t2 = scan('changed-scan', changed, None if case == 'I1' else t1, True)
            assert (t1 != t2) == (case == 'I1')
            after = states('after-t1', t1)
            second = states('after-t2', t2) if case == 'I1' else None
            evaluate(case, before, after, second)
            save('summary', {'outcome': 'PASS', 'case': case, 'product': p['id'],
                             'engagement': e['id'], 't1': t1, 't2': t2,
                             'before': before, 'after': after, 'second': second})
        except Exception as exc:
            save('failure', {'outcome': 'INCONCLUSIVE', 'exception_type': type(exc).__name__,
                             'instruction': 'Preserve records; never retry automatically.'})
            raise RuntimeError('Experiment stopped; inspect sanitized evidence') from None
    return run_dir

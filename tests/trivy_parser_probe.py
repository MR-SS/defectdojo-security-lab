"""Run unsaved parser/hash research in the existing pinned container only."""
import json
import subprocess
from pathlib import Path

from lab.trivy_identity import HANDLERS

CODE = '''import io,json,sys
from django.conf import settings
from django.db import connections
from dojo.tools.trivy_operator.parser import TrivyOperatorParser
from dojo.models import Test, Test_Type
from dojo.utils import get_custom_method
from contextlib import ExitStack
config=dict(algorithm=settings.DEDUPLICATION_ALGORITHM_PER_PARSER.get('Trivy Operator Scan'),
 fields=settings.HASHCODE_FIELDS_PER_SCANNER.get('Trivy Operator Scan'),
 always=settings.HASH_CODE_FIELDS_ALWAYS)
assert config['algorithm']=='hash_code'
assert config['fields']==['title','severity','vulnerability_ids','description']
assert config['always']==['service']
assert not get_custom_method('FINDING_COMPUTE_HASH_METHOD')
def readonly(execute,sql,params,many,context):
 assert sql.lstrip().upper().startswith('SELECT'), 'Non-SELECT SQL forbidden'
 return execute(sql,params,many,context)
out={}
test=Test(test_type=Test_Type(name='Trivy Operator Scan'))
with ExitStack() as stack:
 for connection in connections.all(): stack.enter_context(connection.execute_wrapper(readonly))
 for name,text in json.load(sys.stdin).items():
  reports=json.loads(text)
  rows=TrivyOperatorParser().get_findings(io.StringIO(text),test)
  assert len(rows)==2 and all(f.pk is None for f in rows)
  result=[]
  for report,f in zip(reports,rows):
   labels=report['metadata']['labels']
   baseline=f.compute_hash_code()
   service=f.service
   f.service='synthetic-stable-request'
   override=f.compute_hash_code()
   result.append(dict(resource_kind=labels['trivy-operator.resource.kind'],
    resource_name=labels['trivy-operator.resource.name'],service=service,
    description=f.description,hash=baseline,stable_request_hash=override,
    title=f.title,severity=f.severity,vulnerability_ids=f.unsaved_vulnerability_ids))
  out[name]=result
print('DATA:'+json.dumps(dict(config=config,parsed=out),sort_keys=True))
'''


def run():
    blobs = {f'{h}-{p}': Path(f'fixtures/trivy-{h}-{p}.json').read_text()
             for h in HANDLERS for p in ('initial', 'changed')}
    result = subprocess.run(
        ['docker', 'exec', '-i', 'ddslab-uwsgi-1', 'python', 'manage.py', 'shell', '-c', CODE],
        input=json.dumps(blobs), text=True, capture_output=True, timeout=90, check=True)
    data = json.loads(result.stdout.split('DATA:')[-1])
    for handler in HANDLERS:
        a, b = (data['parsed'][f'{handler}-{p}'] for p in ('initial', 'changed'))
        assert len(a) == len(b) == 2
        assert a[1] == b[1]
        for field in ('hash', 'stable_request_hash', 'service', 'description'):
            assert a[0][field] != b[0][field]
        assert a[0]['hash'] != a[1]['hash']
        assert b[0]['hash'] != b[1]['hash']
        expected = a[0]['description'].replace('alpha-6b7c8d9f5b', 'alpha-7c8d9f6b5c')
        assert expected == b[0]['description']
    return data


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))

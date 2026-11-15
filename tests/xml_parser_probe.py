"""Bounded parser and exception-boundary probe; never invokes import/save APIs."""
import hashlib
import json
import subprocess
from pathlib import Path

CODE = r'''
import io,json,sys,signal,resource
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
from django.db import connections
from dojo.models import Test
from dojo.tools.burp_dastardly.parser import BurpDastardlyParser
from dojo.importers.base_importer import BaseImporter
from dojo.api_v2.exception_handler import custom_exception_handler
from defusedxml import ElementTree
import defusedxml
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
signal.alarm(20)
def blocked(*args,**kwargs):
 raise AssertionError('Database/network access forbidden')
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo'): blocked()
sys.addaudithook(audit)
rows=[]
with ExitStack() as stack:
 for connection in connections.all(): stack.enter_context(connection.execute_wrapper(blocked))
 stack.enter_context(patch('dojo.api_v2.exception_handler.System_Settings.objects.get',
  return_value=SimpleNamespace(api_expose_error_details=False)))
 stack.enter_context(patch('dojo.api_v2.exception_handler.ErrorPageProductAnnouncement'))
 stack.enter_context(patch('dojo.api_v2.exception_handler._log_server_error'))
 for name,text in json.load(sys.stdin).items():
  raw=text.encode('utf-8')
  assert len(raw)<=2048
  parser=BurpDastardlyParser()
  result={'case':name,'returned':None,'constructed':0}
  from dojo.models import Finding
  def construct(**kwargs):
   result['constructed']+=1
   return Finding(**kwargs)
  with patch('dojo.tools.burp_dastardly.parser.Finding',side_effect=construct):
   try:
    findings=parser.get_findings(io.BytesIO(raw),Test())
    result.update(returned=len(findings),exception=None)
    assert all(f.pk is None for f in findings)
   except Exception as e:
    result.update(exception=type(e).__module__+'.'+type(e).__name__,message=str(e))
  # Call only the real parse seam with an unsaved Test; not importer constructor/process_scan.
  seam=SimpleNamespace(test=Test(),finalize_parsed_findings=lambda rows:rows)
  try:
   findings=BaseImporter.parse_findings_static_test_type(seam,io.BytesIO(raw),parser)
   result.update(boundary_exception=None,boundary_returned=len(findings),handler_status=None)
  except Exception as e:
   response=custom_exception_handler(e,{})
   result.update(boundary_exception=type(e).__module__+'.'+type(e).__name__,
    handler_status=response.status_code,handler_body=response.data)
  rows.append(result)
p=ElementTree.XMLParser()
print('DATA:'+json.dumps(dict(defusedxml=defusedxml.__version__,
 configuration={k:getattr(p,k) for k in ('forbid_dtd','forbid_entities','forbid_external')},
 results=rows)))
'''


def run():
    paths = sorted(Path('fixtures/xml-14752').glob('*.xml'))
    assert paths
    payload = {p.stem: p.read_text() for p in paths}
    assert all(len(v.encode()) <= 2048 for v in payload.values())
    result = subprocess.run(
        ['docker', 'exec', '-i', 'ddslab-uwsgi-1', 'python', 'manage.py', 'shell', '-c', CODE],
        input=json.dumps(payload), capture_output=True, text=True, timeout=35, check=True,
    )
    data = json.loads(result.stdout.split('DATA:')[-1])
    for row in data['results']:
        row['sha256'] = hashlib.sha256(payload[row['case']].encode()).hexdigest()
    return data


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))

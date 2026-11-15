"""Bounded parser-only empty-report experiment; no importer or persistence calls."""
import json
import subprocess
from pathlib import Path

CODE = r'''
import io,json,resource,signal,sys
from dojo.models import Test
from dojo.tools.burp_dastardly.parser import BurpDastardlyParser
from defusedxml import ElementTree
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
signal.alarm(20)
out=[]
for name,text in json.load(sys.stdin).items():
 raw=text.encode('utf-8')
 assert len(raw) <= 4096
 parser=BurpDastardlyParser()
 row={'case':name,'sha256':__import__('hashlib').sha256(raw).hexdigest()}
 try:
  findings=parser.get_findings(io.BytesIO(raw),Test())
  row.update(parse='success',cardinality=len(findings),
            identities=[(f.title,f.severity,f.url,f.description) for f in findings])
 except Exception as exc:
  row.update(parse='exception',exception=type(exc).__module__+'.'+type(exc).__name__,
             message=str(exc))
 out.append(row)
print('DATA:'+json.dumps({'results':out,'parser':'BurpDastardlyParser','xml_library':'defusedxml.ElementTree'}))
'''


def run():
    paths = sorted(Path('fixtures/xml-6b').glob('*.xml'))
    payload = {p.stem: p.read_text() for p in paths}
    assert payload and all(len(v.encode()) <= 4096 for v in payload.values())
    result = subprocess.run(
        ['docker', 'exec', '-i', 'ddslab-uwsgi-1', 'python', 'manage.py', 'shell', '-c', CODE],
        input=json.dumps(payload), capture_output=True, text=True, timeout=35, check=True,
    )
    return json.loads(result.stdout.split('DATA:')[-1])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))

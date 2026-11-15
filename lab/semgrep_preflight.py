"""Read-only provenance and parser gates for the derived control."""

import json
import subprocess
from pathlib import Path

import yaml


def output(args):
    return subprocess.check_output(args, text=True, timeout=90)


def preflight(source, blobs):
    version = yaml.safe_load(Path("configs/versions.yaml").read_text())["versions"]["baseline"]
    sha = output(["git", "-C", source, "rev-parse", "HEAD"]).strip()
    assert sha == version["source_sha"]
    assert sha == output(["git", "-C", source, "rev-parse", "3.5.101^{commit}"]).strip()
    images = json.loads(output(["docker", "inspect", "ddslab-uwsgi-1", "ddslab-nginx-1"]))
    for image, key in zip(images, ("image", "nginx_image"), strict=True):
        assert image["Config"]["Image"] == version[key]
        assert (
            image["Image"]
            == json.loads(output(["docker", "image", "inspect", version[key]]))[0]["Id"]
        )
    for name in (
        "dojo/tools/sarif/parser.py",
        "dojo/tools/utils.py",
        "dojo/importers/base_importer.py",
        "dojo/importers/default_reimporter.py",
        "dojo/finding/models.py",
    ):
        pinned = output(["git", "-C", source, "show", "HEAD:" + name])
        running = output(
            [
                "docker",
                "exec",
                "ddslab-uwsgi-1",
                "python",
                "-c",
                "import pathlib; print(pathlib.Path(" + repr(name) + ').read_text(),end="")',
            ]
        )
        assert pinned == running
    code = """import io,json,sys
from django.conf import settings
from django.contrib.auth import get_user_model
from dojo.models import Product_Type,Product,System_Settings
from dojo.authorization.authorization import user_has_permission
from dojo.tools.sarif.parser import SarifParser
from dojo.tools.utils import drop_ambiguous_repeated_unique_ids
from dojo.utils import get_custom_method
u=get_user_model().objects.get(username='ddslab-integration')
pt=Product_Type.objects.get(pk=3)
assert u.is_active and not u.is_staff and not u.is_superuser
assert list(Product_Type.objects.filter(authorized_users=u).values_list('pk',flat=True))==[3]
assert not Product.objects.filter(authorized_users=u).exists()
assert not u.groups.exists() and not u.user_permissions.exists()
assert user_has_permission(u,pt,'add') and user_has_permission(u,pt,'import')
config=dict(algorithm=settings.DEDUPLICATION_ALGORITHM_PER_PARSER.get('SARIF'),
 fields=settings.HASHCODE_FIELDS_PER_SCANNER.get('SARIF'),always=settings.HASH_CODE_FIELDS_ALWAYS,
 global_deduplication=System_Settings.objects.get().enable_deduplication,
 custom=bool(get_custom_method('FINDING_COMPUTE_HASH_METHOD')))
assert config['algorithm']=='unique_id_from_tool_or_hash_code'
assert config['fields'] in (None,[]) and config['always']==['service']
assert not config['global_deduplication'] and not config['custom']
out=[]
for text in json.load(sys.stdin):
 rows=SarifParser().get_findings(io.StringIO(text),None)
 raw=[f.unique_id_from_tool for f in rows]
 assert set(raw)=={'requires login'}
 drop_ambiguous_repeated_unique_ids(rows)
 assert all(f.unique_id_from_tool is None and f.service is None for f in rows)
 out.append([dict(raw=u,uid=f.unique_id_from_tool,
  hash=f.compute_hash_code_legacy(),rule=f.vuln_id_from_tool) for u,f in zip(raw,rows)])
print('DATA:'+json.dumps(dict(config=config,parsed=out)))"""
    result = subprocess.run(
        ["docker", "exec", "-i", "ddslab-uwsgi-1", "python", "manage.py", "shell", "-c", code],
        input=json.dumps([b.decode() for b in blobs]),
        text=True,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, "read-only gate failed"
    data = json.loads(result.stdout.split("DATA:")[-1])
    a, b = data["parsed"]
    assert len(a) == 143 and len(b) == 142
    old, new = ({r["hash"]: r["rule"] for r in rows} for rows in (a, b))
    assert len(old) == 143 and len(new) == 142 and new.items() <= old.items()
    data.update(
        source=sha, images=[{"reference": i["Config"]["Image"], "id": i["Image"]} for i in images]
    )
    return data

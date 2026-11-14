import ipaddress
import json
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

from lab.provisioning_diagnostics import instrument

if os.environ.get("DDSLAB_APPROVE_PROVISIONING") != "1":
    raise SystemExit("BLOCKED: separate provisioning approval required")

ROOT = Path("/home/sajjad/research/defectdojo-security-lab")
target = ROOT / ".venv/ddslab-integration.env"
assert not target.exists()
subprocess.run(["git", "check-ignore", "-q", str(target)], cwd=ROOT, check=True)
os.umask(0o077)
code = """
import json
from django.contrib.auth import get_user_model
from django.db import transaction
from dojo.models import Product_Type, Product, Engagement, Test, Finding, Dojo_User
from dojo.authorization.authorization import user_has_permission
from rest_framework.authtoken.models import Token
U=get_user_model()
with transaction.atomic():
    assert not U.objects.filter(username='ddslab-integration').exists()
    assert not Product_Type.objects.filter(name__iexact='DDSLAB Integration').exists()
    pt=Product_Type.objects.create(
        name='DDSLAB Integration',description='Dedicated synthetic integration-test scope')
    u=U.objects.create_user(username='ddslab-integration',password=None,is_active=True,is_staff=False,is_superuser=False)
    pt.authorized_users.add(u.pk)
    assert not Dojo_User.force_password_reset(u)

    actions=['view','add','import','delete','staff_only']
    permissions={a:user_has_permission(u,pt,a) for a in actions}
    assert permissions == {'view':True,'add':True,'import':True,'delete':False,'staff_only':False}
    memberships=Product_Type.objects.filter(authorized_users=u.pk)
    assert list(memberships.values_list('pk',flat=True)) == [pt.pk]
    assert not u.is_staff and not u.is_superuser and u.is_active
    assert not u.groups.exists() and not u.user_permissions.exists()
    unrelated_p=list(Product.objects.exclude(prod_type=pt))
    unrelated_e=list(Engagement.objects.exclude(product__prod_type=pt))
    assert all(not user_has_permission(u,x,a) for x in unrelated_p+unrelated_e
               for a in ['view','add','edit','import','delete'])
    token,created=Token.objects.get_or_create(user=u)
    assert Token.objects.filter(user=u).count()==1
    result={'token':token.key,'account_id':u.pk,'product_type_id':pt.pk,
            'permissions':permissions,'unrelated_products':[x.pk for x in unrelated_p],
            'unrelated_engagements':[x.pk for x in unrelated_e]}
print('PRIVATE:'+json.dumps(result))
"""
r = subprocess.run(
    ["docker", "exec", "ddslab-uwsgi-1", "python", "manage.py", "shell", "-c", instrument(code)],
    capture_output=True,
    text=True,
    timeout=90,
)
if r.returncode:
    diagnostic = next(
        (line for line in r.stdout.splitlines() if line.startswith("DIAGNOSTIC:")), None
    )
    if diagnostic:
        print(diagnostic)
    print(
        json.dumps(
            {
                "operation": "provisioning_child",
                "exit_code": r.returncode,
                "category": "child_failed",
                "rollback": "unverified_requires_readback",
            }
        )
    )
    raise SystemExit(1)
data = json.loads(r.stdout.split("PRIVATE:")[-1])
# Resolve the already-published loopback binding without reading credentials.
info = json.loads(subprocess.check_output(["docker", "inspect", "ddslab-nginx-1"]))[0]
binding = next(
    b
    for values in info["NetworkSettings"]["Ports"].values()
    if values
    for b in values
    if b["HostPort"] == "18080"
)
assert ipaddress.ip_address(binding["HostIp"]).is_loopback
url = "http://" + binding["HostIp"] + ":" + binding["HostPort"]
fd, tmp = tempfile.mkstemp(prefix=".credential-", dir=target.parent)
with os.fdopen(fd, "w") as f:
    f.write(
        "DDSLAB_API_BASE_URL="
        + url
        + "\nDDSLAB_API_TOKEN="
        + data["token"]
        + "\nDDSLAB_PRODUCT_TYPE_ID="
        + str(data["product_type_id"])
        + "\n"
    )
    f.flush()
    os.fsync(f.fileno())
os.link(tmp, target)  # Atomic publication; fails rather than overwriting.
os.unlink(tmp)
assert target.stat().st_mode & 0o777 == 0o600
results = {}
with httpx.Client(base_url=url, trust_env=False, follow_redirects=False, timeout=30) as c:
    results["unauthenticated"] = c.get("/api/v2/products/").status_code
    results["invalid_token"] = c.get(
        "/api/v2/products/", headers={"Authorization": "Token invalid-ddslab-negative-check"}
    ).status_code
    c.headers["Authorization"] = "Token " + data["token"]
    response = c.get("/api/v2/products/")
    results["authenticated"] = response.status_code
    assert response.status_code == 200 and response.json()["count"] == 0
    assert results["unauthenticated"] in (401, 403) and results["invalid_token"] in (401, 403)
    results["negative_products"] = {
        str(i): c.get(f"/api/v2/products/{i}/").status_code for i in data["unrelated_products"]
    }
    results["negative_engagements"] = {
        str(i): c.get(f"/api/v2/engagements/{i}/").status_code
        for i in data["unrelated_engagements"]
    }
    assert all(
        s in (403, 404)
        for group in ("negative_products", "negative_engagements")
        for s in results[group].values()
    )
data.pop("token")
data.update(
    http=results,
    credential_source="ignored local file",
    credential_file=str(target),
    mode="0600",
    account="ddslab-integration",
    is_staff=False,
    is_superuser=False,
)
evidence = ROOT / "evidence/credential-provisioning"
evidence.mkdir(mode=0o700)
with (evidence / "summary.json").open("x") as f:
    json.dump(data, f, indent=2)
print(json.dumps(data, indent=2))

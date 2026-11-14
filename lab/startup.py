"""Read-only startup gates and additive local first-boot provisioning."""
import argparse
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

FIRST_BOOT = ('DD_ADMIN_PASSWORD', 'DD_JIRA_WEBHOOK_SECRET')


def parse_env(text):
    values = {}
    for line in text.splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            if key in values:
                raise ValueError('Duplicate environment field')
            values[key] = value
    return values


def provision(path):
    if path.is_symlink():
        raise ValueError('Symlink refused')
    original = path.read_text()
    values = parse_env(original)
    for key in FIRST_BOOT:
        if key in values and not values[key]:
            raise ValueError('Existing first-boot credential is empty')
    additions = {key: secrets.token_urlsafe(32) for key in FIRST_BOOT if key not in values}
    if not additions:
        path.chmod(0o600)
        return
    content = original + ('' if original.endswith('\n') else '\n')
    content += ''.join(f'{key}={value}\n' for key, value in additions.items())
    fd, name = tempfile.mkstemp(prefix='.credentials-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_text() != original:
            raise ValueError('Environment changed during provisioning')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check_result(service, code, output):
    if code is None:
        raise RuntimeError(f'{service}: readiness timeout')
    if code != 0:
        raise RuntimeError(f'{service}: readiness failed (details withheld)')


def run(command, env=None):
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        check_result('command', None, '')
    return result


def gate(root):
    env = dict(os.environ)
    env.update(parse_env((root / '.env.lab').read_text()))
    for key in (*FIRST_BOOT, 'DD_DATABASE_PASSWORD', 'DD_DATABASE_USER',
                'DD_SECRET_KEY', 'DD_CREDENTIAL_AES_256_KEY'):
        if not env.get(key):
            raise ValueError('Missing required local credential field')
    version = yaml.safe_load((root / 'configs/versions.yaml').read_text())['versions']['baseline']
    env.update(DD_DJANGO_IMAGE=version['image'], DD_NGINX_IMAGE=version['nginx_image'])
    rendered = run(['docker', 'compose', '-p', 'ddslab', '-f', str(root / 'compose.lab.yaml'),
                    'config', '--format', 'json'], env)
    check_result('compose', rendered.returncode, '')
    model = json.loads(rendered.stdout)
    from lab.preflight import inspect_compose_model
    if inspect_compose_model(model):
        raise ValueError('Compose preflight failed')
    url = urlsplit(model['services']['initializer']['environment']['DD_DATABASE_URL'])
    inspected = run(['docker', 'inspect', 'ddslab-postgres-1', 'ddslab-valkey-1'])
    check_result('inspect', inspected.returncode, '')
    pg, broker = json.loads(inspected.stdout)
    for container in (pg, broker):
        if container['Config']['Labels'].get('com.docker.compose.project') != 'ddslab':
            raise ValueError('Resource ownership mismatch')
        if not container['State']['Running']:
            raise ValueError('Required infrastructure is not running')
    pg_env = dict(item.split('=', 1) for item in pg['Config']['Env'])
    if (unquote(url.password or '') != pg_env['POSTGRES_PASSWORD']
            or url.username != pg_env['POSTGRES_USER']
            or url.path != '/' + pg_env['POSTGRES_DB'] or url.hostname != 'postgres'):
        raise ValueError('Database configuration mismatch')
    env['PGPASSWORD'] = unquote(url.password)
    result = run(['docker', 'exec', '-e', 'PGPASSWORD', '-e', 'PGCONNECT_TIMEOUT=5',
                  '-e', 'PGOPTIONS=-c statement_timeout=5000', 'ddslab-postgres-1',
                  'psql', '-w', '-h', 'postgres', '-U', url.username, '-d', url.path[1:],
                  '-Atc', 'BEGIN READ ONLY; SELECT 1; COMMIT;'], env)
    check_result('postgres', result.returncode, '')
    result = run(['docker', 'exec', 'ddslab-valkey-1', 'valkey-cli', '-h', 'valkey', 'ping'])
    check_result('valkey', result.returncode, '')
    if result.stdout.strip() != 'PONG':
        raise RuntimeError('Valkey authentication/readiness mismatch')
    return {'postgres': 'PASS', 'valkey': 'PASS', 'compose': 'PASS',
            'limitation': 'TCP probes originate inside existing infrastructure containers, '
                          'not an application container; no containers created or started.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provision', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.provision:
        provision(root / '.env.lab')
    print(json.dumps(gate(root), indent=2))


if __name__ == '__main__':
    main()

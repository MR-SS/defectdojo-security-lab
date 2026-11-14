import os

import pytest

from lab.startup import check_result, provision


def test_preservation_and_permissions(tmp_path):
    p = tmp_path / 'env'
    p.write_text('DD_DATABASE_PASSWORD=existing\nOTHER=unchanged\n')
    provision(p)
    first = p.read_bytes()
    assert first.startswith(b'DD_DATABASE_PASSWORD=existing\nOTHER=unchanged\n')
    assert p.stat().st_mode & 0o777 == 0o600
    provision(p)
    assert p.read_bytes() == first


def test_atomic_failure_preserves_original(tmp_path, monkeypatch):
    p = tmp_path / 'env'
    p.write_text('OTHER=unchanged\n')
    original = p.read_bytes()
    def fail(*args):
        raise OSError('failure')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError):
        provision(p)
    assert p.read_bytes() == original


@pytest.mark.parametrize('service', ['postgres', 'valkey'])
def test_readiness_failure_redacted(service):
    with pytest.raises(RuntimeError, match=service) as exc:
        check_result(service, 2, 'secret-password')
    assert 'secret-password' not in str(exc.value)


def test_invalid_credentials():
    with pytest.raises(RuntimeError):
        check_result('postgres', 2, 'authentication failed')


def test_timeout():
    with pytest.raises(RuntimeError, match='timeout'):
        check_result('postgres', None, '')


def test_empty_existing_secret_not_overwritten(tmp_path):
    p = tmp_path / 'env'
    p.write_text('DD_ADMIN_PASSWORD=\n')
    with pytest.raises(ValueError):
        provision(p)
    assert p.read_text() == 'DD_ADMIN_PASSWORD=\n'

import pytest

from lab.provisioning_diagnostics import instrument


def test_failure_reports_stage_without_exception_text(capsys):
    code = instrument("raise TypeError('secret-value')")
    with pytest.raises(SystemExit) as exc:
        exec(code, {})
    output = capsys.readouterr().out
    assert exc.value.code == 1
    assert 'TypeError' in output and 'secret-value' not in output
    assert 'operation' in output and 'rollback' in output


def test_membership_uses_scalar_identity():
    from pathlib import Path
    source = Path('scripts/provision_ddslab_integration.py').read_text()
    assert 'pt.authorized_users.add(u.pk)' in source
    assert "user_has_permission(u,p,'add')" not in source

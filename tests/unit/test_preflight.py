from lab.preflight import (
    inspect_compose_model,
    validate_environment,
    validate_image_reference,
    validate_project_name,
    validate_selection,
)


def complete_env():
    return {
        "DD_PROJECT_NAME": "ddslab",
        "DD_UI_BIND": "127.0.0.1",
        "DD_UI_PORT": "18080",
        "DD_SECRET_KEY": "local-random-secret",
        "DD_CREDENTIAL_AES_256_KEY": "local-random-key",
        "DD_DATABASE_PASSWORD": "local-db-password",
    }


def test_invalid_image_reference_is_rejected():
    assert validate_image_reference("example/app:latest")
    assert validate_image_reference("example/app:3.5.101")


def test_digest_pinned_image_reference_is_accepted():
    assert validate_image_reference("example/app:3.5.101@sha256:" + "a" * 64) == []


def test_missing_artifact_metadata_blocks_selection():
    data = {"versions": {"baseline": {"application": "3.5.101"}}}
    codes = {issue.code for issue in validate_selection("baseline", data)}
    assert "missing_artifact_metadata" in codes


def test_development_requires_source_sha():
    data = {"versions": {"development": {"application": "development"}}}
    codes = {issue.code for issue in validate_selection("development", data)}
    assert "development_unpinned" in codes


def test_missing_credentials_are_reported():
    codes = {issue.code for issue in validate_environment({})}
    assert "missing_environment" in codes


def test_non_loopback_binding_is_reported():
    env = complete_env()
    env["DD_UI_BIND"] = "0.0.0.0"
    codes = {issue.code for issue in validate_environment(env)}
    assert "non_loopback_bind" in codes


def test_default_credentials_are_reported():
    env = complete_env()
    env["DD_DATABASE_PASSWORD"] = "password"
    codes = {issue.code for issue in validate_environment(env)}
    assert "unsafe_credential" in codes


def test_invalid_project_name_is_reported():
    assert validate_project_name("Bad Name", set())


def test_conflicting_project_name_is_reported():
    codes = {issue.code for issue in validate_project_name("ddslab", {"ddslab"})}
    assert "conflicting_project_name" in codes


def test_public_port_is_reported():
    model = {"services": {"nginx": {"ports": [{"published": 18080, "host_ip": "0.0.0.0"}]}}}
    codes = {issue.code for issue in inspect_compose_model(model)}
    assert "public_port" in codes


def test_unexpected_absolute_mount_is_reported():
    model = {"services": {"app": {"volumes": [{"source": "/etc", "target": "/app"}]}}}
    codes = {issue.code for issue in inspect_compose_model(model)}
    assert "unexpected_bind_mount" in codes


def test_safe_loopback_compose_model_has_no_port_issue():
    model = {
        "services": {
            "nginx": {"ports": [{"published": 18080, "host_ip": "127.0.0.1"}]},
            "postgres": {},
            "valkey": {},
        }
    }
    codes = {issue.code for issue in inspect_compose_model(model)}
    assert "public_port" not in codes
    assert "conflicting_port" not in codes

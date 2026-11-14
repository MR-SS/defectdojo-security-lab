import pytest

from lab.preflight import inspect_compose_model


@pytest.mark.parametrize("service,entrypoint", [
    ("initializer", "/entrypoint-initializer.sh"),
    ("uwsgi", "/entrypoint-uwsgi.sh"),
    ("celeryworker", "/entrypoint-celery-worker.sh"),
    ("celerybeat", "/entrypoint-celery-beat.sh"),
])
def test_release_contract_accepts_correct_service(service, entrypoint):
    spec = {
        "entrypoint": [entrypoint],
        "environment": {"DD_DATABASE_URL": "postgresql://user:synthetic@postgres/db"},
        "depends_on": {"initializer": {"condition": "service_completed_successfully"}},
    }
    assert not inspect_compose_model({"services": {service: spec}})
    spec["entrypoint"] = ["/wrong-script"]
    assert "application_entrypoint" in {
        issue.code for issue in inspect_compose_model({"services": {service: spec}})
    }


def test_application_contract_rejects_missing_password_and_entrypoint():
    model = {"services": {"uwsgi": {"environment": {"DD_DATABASE_URL": "postgresql://user@postgres/db"}}}}
    codes = {issue.code for issue in inspect_compose_model(model)}
    assert {"database_credentials", "application_entrypoint", "initializer_dependency"} <= codes

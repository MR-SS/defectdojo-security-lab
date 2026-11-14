from lab.preflight import inspect_compose_model


def test_pg18_rejects_legacy_mount():
    model = {"services": {"postgres": {
        "image": "postgres:18.6-alpine",
        "environment": {"PGDATA": "/var/lib/postgresql/18/docker"},
        "volumes": [{"type": "volume", "source": "lab", "target": "/var/lib/postgresql/data"}],
    }}}
    assert "postgres18_layout" in {i.code for i in inspect_compose_model(model)}


def test_pg18_accepts_parent_mount():
    model = {"services": {"postgres": {
        "image": "postgres:18.6-alpine",
        "environment": {"PGDATA": "/var/lib/postgresql/18/docker"},
        "volumes": [{"type": "volume", "source": "lab", "target": "/var/lib/postgresql"}],
    }}}
    assert not inspect_compose_model(model)

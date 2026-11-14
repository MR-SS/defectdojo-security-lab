# Compose preflight

This lab-owned file is a static, non-starting Compose configuration derived from the upstream Open Source Compose service inventory. It is not a replacement for the official upstream file and does not modify the sibling checkout.

## Services

The isolated configuration declares `nginx`, `uwsgi`, `celeryworker`, `celerybeat`, `initializer`, `postgres`, and `valkey`. Only `nginx` publishes the UI port. PostgreSQL and Valkey have no host ports. Volumes are named `ddslab_media`, `ddslab_postgres`, and `ddslab_valkey`.

## Security policy

- UI binding must be `127.0.0.1`.
- The UI port is selected through `DD_UI_PORT`; the preflight must check it immediately before deployment.
- Secrets are required through environment variables and are never committed.
- No `latest` or tag-only application image is accepted. Application image metadata must include an immutable digest.
- Development selections require an explicit source SHA.
- No host bind mounts are used by the lab Compose file.
- `docker compose config` is the only Compose command used by preflight. No `up`, `pull`, `down`, `rm`, volume operation, or Kubernetes command is part of this milestone.

## Preflight checks

The offline validators cover image references, missing artifact metadata, development SHA pinning, missing/default credentials, non-loopback bindings, project-name conflicts, public ports, reserved ports, absolute bind mounts, and paths outside the lab root. The report format is JSON and uses `PASS` or `BLOCKED`; a blocked provenance or safety check is not a product failure.

Example metadata-only invocation after local secrets are generated:

```text
python3 -m lab.preflight --version baseline --output evidence/preflight-baseline.json
```

This command is expected to remain `BLOCKED` until exact application image references/digests and local required variables are supplied. It does not start services.

## Artifact verification captured

- Git tags `3.5.101` and `3.4.304` exist remotely and resolve to independently recorded tag objects and peeled commit SHAs.
- Official release API metadata exists for both releases. Publication dates and Helm chart tarball asset names are recorded in `docs/version-matrix.md`.
- The registry manifest endpoint initially returned HTTP 403, but Docker Hub read-only `docker manifest inspect` and `docker buildx imagetools inspect` succeeded for both selected releases. Application image digests and platforms are now recorded in `configs/artifacts.yaml` and `configs/versions.yaml`.
- The checked-out chart metadata is not silently reused: exact release chart packages report appVersions matching 3.5.101 and 3.4.304, with chart versions 1.9.67 and 1.9.64 respectively.
- Development remains BLOCKED until an explicit immutable source SHA is entered.

## Deployment prerequisites

Before a future controlled deployment, verify artifact metadata, generate local ignored secrets, choose an unused loopback port, run the preflight report, review the rendered config, and obtain explicit approval to start the dedicated Compose project. Do not run deployment commands while the preflight is blocked.

## Rollback and cleanup

The first deployment must use only the lab Compose project and its three `ddslab_*` named volumes. Normal rollback is a project-scoped stop operation after explicit approval. Volume deletion is not part of this milestone and requires separate approval. Never use global prune or remove commands.

## Limitations

No image was pulled, no service was started, no registry authentication was attempted, and no chart was installed. Image architecture compatibility and chart/appVersion compatibility remain unverified until public metadata or approved local artifacts are available.

# Environment Report

Inventory timestamp: 2026-11-14T09:37:04+03:30

This report contains non-secret host characteristics only. Values masked by the execution proxy are preserved as masks and are not placeholders to repair.

## Host

- OS: Ubuntu 26.04.1 LTS, codename `resolute`
- Architecture: x86_64
- CPU: 20 logical CPUs; Intel Core i5-14600K; 14 cores, 20 threads
- Memory: 14 GiB total; approximately 6.4 GiB available during inventory
- Swap: 4.0 GiB total
- Root filesystem: 228G total, 164G used, 53G available, 76% used
- Resource policy: sequential Compose/Minikube operation; no simultaneous stacks

## Tooling

- Docker Engine: 29.9.2
- Compose: v5.6.1
- Git: 2.53.0
- Python: 3.14.9
- kubectl client: v1.37.1; Kustomize v5.8.1
- Minikube: v1.39.0; profile runtime containerd; Docker driver
- Helm: v3.22.1

## Kubernetes and Minikube

- Current context: `minikube`
- Existing profile: `minikube`, stopped, one node, Docker driver
- Read-only API query attempted and failed because the stopped profile API endpoint was unreachable (`no route to host`)
- No profile was started, reset, deleted, or modified

## Existing containers and networks

Existing running containers observed:

- `admin-panel`, image ID `a395465d1daa`, published `0.0.0.0:3000->3000/tcp`, healthy
- `chat-meilisearch`, image `getmeili/meilisearch:v1.35.1`, no published host port shown

Existing Docker networks observed:

- `ai-security-gate_default`
- `bridge`
- `host`
- `librechat_default`
- `minikube`
- `none`
- `pipelineguard_default`
- `project-hunter_default`

The lab must use a distinct Compose project, distinct network, distinct named volumes, and an unused loopback port. No existing resource is adopted or altered.

## Listeners and conflicts

The inventory showed existing listeners including ports 3000, 8080, 8005, 10808, 10809, 10813, 11434, 34243, and 631, plus DNS and other UDP listeners. The lab must preflight its selected port immediately before binding and choose a non-conflicting loopback port. The default future UI port is not assumed safe.

## Network and proxy

No `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or `NO_PROXY` variables were present in the captured environment. DNS resolved `github.com`, and an HTTPS HEAD request to the upstream repository succeeded with HTTP 200. This confirms network reachability only; it does not authorize external testing or publication.

## Upstream checkout safety

Sibling checkout `../defect_dojo/django-DefectDojo` is on `master`, at `3.4.202-dirty`, behind `origin/master`, with local modifications in Helm files. Sibling `../defect_dojo/defectdojo-docs` is on branch `docs/helm-smtp-setup`, at `nightly-dev-2-g7a2b0c245`. Both are outside this repository and must remain untouched.

Upstream contributor guidance requires development work on `dev`, not `master`.
The relevant development and parser guidance was reviewed before planning. No
upstream code was changed.

## Limitations

- This is a point-in-time inventory; re-run before each bind or environment start.
- Disk usage is high enough that image pulls and large benchmark artifacts require monitoring.
- The existing Minikube profile is not usable while stopped; starting it would be a state-changing operation and is intentionally deferred.
- Version/image/chart availability has not yet been independently verified for every target.

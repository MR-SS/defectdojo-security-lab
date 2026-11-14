# Version Matrix

Machine-readable source of truth: `configs/versions.yaml`.

Verification statuses: VERIFIED means the exact artifact was independently observed; UNVERIFIED means metadata is missing or compatibility is not established; UNAVAILABLE means the metadata endpoint was inaccessible; NOT_APPLICABLE means the artifact does not apply.

| Selection | Source tag | Peeled commit SHA | Release published | Chart asset/version | Image reference/digest | Architecture | Documentation | Deployment status |
|---|---|---|---|---|---|---|---|---|
| baseline | 3.5.101 | `32aea6841a019b050737c8874b939b236095333e` | 2026-11-11T14:16:08Z | `defectdojo-1.9.67.tgz` / 1.9.67 | UNAVAILABLE: registry manifest returned HTTP 403 | UNVERIFIED | VERIFIED: HTTP 200 | BLOCKED pending image metadata |
| previous | 3.4.304 | `c360df03a9399cbe6b26138bd0289949c27eb732` | 2026-10-30T02:26:51Z | `defectdojo-1.9.64.tgz` / 1.9.64 | UNAVAILABLE: registry manifest returned HTTP 403 | UNVERIFIED | VERIFIED: HTTP 200 | BLOCKED pending image metadata |
| development | explicit SHA required | not supplied | NOT_APPLICABLE | NOT_APPLICABLE until selected | NOT_APPLICABLE until selected | NOT_APPLICABLE | UNVERIFIED | BLOCKED |

## Exact source tag observations

Remote tag queries returned tag objects and peeled commits:

- `3.5.101`: tag object `a90dc607136ba1a982cc250d9af076f641e8992a`, peeled commit `32aea6841a019b050737c8874b939b236095333e`
- `3.4.304`: tag object `6473abc788fb0ed2a2e5071fca13421e5e4e39e2`, peeled commit `c360df03a9399cbe6b26138bd0289949c27eb732`

The release API confirmed both releases exist and supplied publication timestamps and chart asset names. The registry manifest endpoint returned HTTP 403 for unauthenticated metadata reads; no image digest or architecture was invented. No image was pulled.

## Chart compatibility

The selected release assets identify chart packages independently from application source tags. The dirty sibling checkout's `Chart.yaml` reports `version: 1.9.61` and `appVersion: 3.4.202`; it is not used as compatibility evidence for either selected release. Chart/appVersion compatibility remains UNVERIFIED until the exact chart package metadata is obtained and inspected.

## Documentation

The official installation and OS upgrade documentation endpoints returned HTTP 200 during metadata-only verification. Release notes for both versions direct users to the OS upgrade guide. Documentation availability is not proof of image or chart compatibility.

## Development policy

A development comparison cannot be selected until `source_sha` is an explicit immutable SHA. A branch name or moving branch tip is rejected. Image references must include a tag plus immutable digest before deployment.

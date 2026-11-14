# Version Matrix

Machine-readable source of truth: `configs/versions.yaml`.

| Role | Application version | Source ref/SHA | Image reference/digest | Helm chart | Availability | Verification |
|---|---|---|---|---|---|---|
| Default baseline | 3.5.101 | `3.5.101` | TBD | TBD | NOT VERIFIED | Must verify independently |
| Previous comparison | 3.4.304 | `3.4.304` | TBD | TBD | NOT VERIFIED | Must verify independently |
| Development comparison | pinned SHA | Explicit user/config selection required | TBD | TBD | BLOCKED until SHA supplied | Never substitute branch tip |

## Verification policy

A version is selectable only after the source tag or SHA, container image digest, and chart version are recorded independently. Documentation and upgrade notes are checked separately. If an artifact cannot be verified, the related scenario is BLOCKED; the lab never silently chooses a nearby version.

The existing sibling checkout reports tag `3.4.202-dirty` and therefore is not evidence for either requested release target.

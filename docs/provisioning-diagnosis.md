# Provisioning failure diagnosis

No provisioning was retried during diagnosis. The original parent exited 1;
its child return code and stderr were discarded and cannot be recovered from
the script. Do not claim an exact historical child exit code or exception.

Best-supported first failure: original scratch script line 26,
`pt.authorized_users.add(u)`. `get_user_model()` returns auth.User, whereas
Product_Type.authorized_users targets the dojo.Dojo_User proxy. Django's
ManyRelatedManager._get_target_ids rejects a Model that is not an instance of
its target proxy. Read-only invocation of this validation helper with an
unsaved auth.User reproduced TypeError; scalar primary-key validation passed.
No add(), save(), or other mutation was invoked in that probe.

A second defect at original line 32 tested an unsaved Product and Engagement.
The pinned dojo/authorization/authorization.py:125-144 checks persisted
Product IDs via authorized_product_id_set, whose implementation in
query_registrations.py:94-123 queries existing membership and product rows.
An unsaved Product has no authorized persisted ID. This assertion would fail
even after repairing membership assignment.

Model metadata confirms username and Product Type name uniqueness, supported
create_user keyword names, nullable Product Type description, default booleans,
and a one-to-one DRF token user relation. Dojo_User is a proxy for auth.User.
DRF Token.save generates a key when absent. No missing required-field defect
was established. The original transaction.atomic encompasses scope, account,
membership and token creation; an uncaught exception rolls it back. Readback
confirmed zero dedicated users, scopes and tokens. This is consistent with
rollback, not proof of which historical statement raised first.

The tracked replacement is scripts/provision_ddslab_integration.py, invoked
as a module only after separate approval. The original scratch artifact remains
unchanged for investigation. The replacement uses scalar membership identity,
validates persisted scope membership and actual scope permissions, and avoids
pretending unsaved objects prove descendant access. Descendant access remains
source-derived until separately authorized scenario records exist.

lab/provisioning_diagnostics.py wraps child operations with stage names and
allowlisted exception classes, a fixed secret-free category, exit code, and
explicitly unverified rollback status. It never outputs exception messages,
raw stderr or tracebacks. The parent preserves the actual child return code.
Private success output is captured in memory and is emitted only after commit;
it must never be run directly or copied to evidence. Credential-file publication
and post-commit API validation remain separate from database atomicity: failure
there must not trigger automatic retry or imply database rollback.

Limitations: historical stderr is unavailable; no live success is proven.
Parent-side transport/storage failures still require careful diagnosis, and the
current replacement is not yet approved for execution. No credential was read
or created during this investigation.

<!-- capsule-v2 -->
# Notification-Failure Audit Trail — persist the bad news on its own commit

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does a best-effort notifier tell the operator the human was never pinged — without rolling back or dying itself?

## One AuditEntry row, own-commit, swallow-and-log on failure-to-record
**Path/Symbol:** `packages/python/awaithumans/server/services/notification_audit.py` — rationale docstring (:1-19), `record_notification_failure` (:33-77).
**Signature:** `async record_notification_failure(session, *, task_id, task_status, channel, recipient, reason, message) -> None`.
**Data Shape:** `AuditEntry(action="notification_failed", from_status=None, to_status=<current>, actor_type="system", channel=...)`; extra_data carries `{recipient, reason, message}` machine-readably.

### Decisive source
```python
session.add(entry)
try:
    await session.commit()      # notify runs AFTER the parent transaction closed —
except Exception:               # there is no outer commit to piggy-back on
    logger.exception("Failed to record notification_failed audit entry ...")
    await session.rollback()
```
Docstring: a failure to persist the audit row must not itself silently drop — log loudly and swallow so the notification loop continues for OTHER recipients.

**Flow:** notifier catches a send failure → calls this helper with the machine reason + human message → helper commits standalone → dashboard task panel + page banner surface it. `to_status` is REQUIRED by the model but nothing transitioned, so the CURRENT status is passed to show the task stayed put.
**Invariant:** never raise into the notification loop; never skip the commit (the parent tx is already gone); `from_status=None` is the deliberate marker that no transition occurred.
**Probe:** `packages/python/tests/services/test_notification_audit.py` (`test_writes_audit_entry_with_full_context`:30, `test_persists_independently_per_call`:58, `test_commits_inside_helper`:86) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "record_notification_failure AuditEntry notification_failed", limit: 4 });
```
Live rank-1 line-exact (:33-77).

## Verdict
Adopt the own-commit audit helper and the loud-swallow posture; adapt action names/extra_data keys to your audit vocabulary; omit the banner UI coupling if you have another operator-surface — the DB contract stands alone.

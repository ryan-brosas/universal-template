<!-- capsule-v2 -->
# Channel-Scoped HKDF Handoff URLs — how does one root key sign five primitives without cross-channel forgery?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you mint a signed URL that clears a login wall for a Slack/email-only human without creating a universal login?

## Pipe-canonical HMAC under per-primitive salt, expiry = task timeout
**Path/Symbol:** `server/core/slack_handoff.py` — `sign_handoff` (:79–90), `verify_handoff` (:93–117), `_canonical_message` (:69–76); mirror `email_handoff.py` (:65–126 with `_normalize_recipient` :76–83); salts in `utils/constants.py` (:273–283).
**Signature:** `sign_handoff(*, user_id|recipient, task_id, exp_unix) -> str` (urlsafe b64, stripped padding); `verify_handoff(...) -> None` (raises `InvalidHandoffError`, returns None on success).
**Data Shape:** URL `/api/auth/slack-handoff?u=<uid>&t=<task>&e=<exp>&s=<sig>`; message = `f"{user_id}|{task_id}|{exp}"`; key = HKDF-SHA256(root=PAYLOAD_KEY, salt=`b"awaithumans-slack-handoff"` / `b"awaithumans-email-handoff"`, info=`b"v1"`).

### Decisive source
```python
# slack_handoff._canonical_message docstring:
#   Pipe-separator avoids JSON ambiguity (key ordering, whitespace) for
#   a 3-field tuple. None of the values can contain a literal `|`.
# email_handoff adds:
def _normalize_recipient(recipient: str) -> str:
    if "|" in recipient:
        raise InvalidHandoffError("recipient contains '|' — refused")
    return recipient.lower()
```

**Flow:** sign at notification-post time (expiry = `task.timeout_at` so a day-6 click on a 7-day approval still works) → recipient clicks → verify ladder: signature present → base64 decode → length == 32 → constant-time compare → expiry check → endpoint exchanges URL for a real session cookie bound to THAT user + task.
**Invariant:** task-bound (`t`) so a leaked URL can't read other tasks; deliberately NOT single-use ("adding a consumed_token row would block the legitimate 'I closed the tab, click again' flow"); email twin lowercases + REFUSES `|` because RFC 5321 addresses can theoretically contain it. Same root key NEVER signs two primitives — each gets its own salt (webhook/dashboard-session/magic-link/slack-handoff/email-handoff).
**Probe:** `tests/auth/test_slack_handoff_signing.py` (:38 roundtrip, :45 deterministic, :55 any-field-change resigns, :69/:78 wrong user/task rejected, :87 expired rejected, :97/:104/:109 garbage/empty/wrong-length); route tests `test_slack_handoff_route.py`, `test_email_handoff_signing.py`, `test_email_handoff_route.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "sign_handoff verify_handoff _normalize_recipient HKDF", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pipe-canonical messages, per-primitive HKDF salts with versioned info tags, task-binding, expiry-at-task-timeout, and the deliberate no-single-use ruling with its UX justification. Adapt the param names to your router. Omit the email auto-provision behavior unless your directory also treats notify= as implicit consent.

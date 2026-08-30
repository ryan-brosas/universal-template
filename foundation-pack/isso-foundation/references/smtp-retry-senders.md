<!-- capsule-v2 -->
# SMTP connection + retry senders — how do notification sends survive a cold mail server?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What are the two send transports and their retry semantics?

## Context-manager SMTP + dual dispatch
**Path/Symbol:** `isso/ext/notifications.py:SMTPConnection` (30–51), `SMTP.sendmail/_sendmail/_retry` (172–215); constructor connectivity probe (62–67).
**Signature:** `sendmail(subject, body, thread, comment, to=None, headers=None)` → uwsgi spool OR `start_new_thread(self._retry, ...)`; `_retry` loops `for x in range(5)`.
**Data Shape:** security = none|starttls|ssl selects class; spooler args are BYTES keys (`b"subject"`, `b"body"`, `b"to"`, `b"headers"`).

### Decisive source
```python
def __enter__(self):
    klass = smtplib.SMTP_SSL if self.conf.get("security") == "ssl" else smtplib.SMTP
    self.client = klass(host=..., port=..., timeout=...)
    if self.conf.get("security") == "starttls":
        self.client.starttls(context=ssl.create_default_context())
...
if uwsgi:
    uwsgi.spool({b"subject": ..., b"body": ..., b"to": ..., b"headers": ...})
else:
    start_new_thread(self._retry, (subject, body, to, headers))

def _retry(self, subject, body, to, headers):
    for x in range(5):
        try:
            self._sendmail(subject, body, to, headers)
        except smtplib.SMTPConnectError:
            time.sleep(60)
        else:
            break
```

**Flow:** startup verifies connectivity (log-only failure). Under uWSGI, sends are SPOOLED to disk with a registered spooler returning `SPOOL_RETRY` on SMTPConnectError (uWSGI redelivers) / `SPOOL_OK` otherwise. Otherwise each send runs in a fresh daemon thread retrying connect errors up to 5×60s; other exceptions kill that thread silently.
**Invariant:** Sends NEVER block the request path; only CONNECT errors are retried — content rejections are terminal. Empty subject falls back to `"isso notification"` because an empty Subject is invalid.
**Probe:** `grep -c 'for x in range(5)' isso/ext/notifications.py` (`1`); `grep -c SPOOL_RETRY isso/ext/notifications.py` (`1`).
**Test:** no offline SMTP tests (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "SMTPConnection starttls spool retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fire-and-forget with transport-specific retries; adapt the uWSGI branch to your task queue. Keep the startup probe — it converts config typos into immediate log evidence.

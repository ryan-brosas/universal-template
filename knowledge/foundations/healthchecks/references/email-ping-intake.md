<!-- capsule-v2 -->
# Email ping intake — SMTP as a heartbeat transport with RCPT-time validation

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does inbound email become a classified ping without becoming a spam-amplification hole, and why does the handler bridge async to sync?

## smtpd command: PingHandler / _process_message
**Path/Symbol:** `hc/api/management/commands/smtpd.py:_process_message` (:50-102), `PingHandler.handle_RCPT` (:110-125), `handle_DATA` (:127-140), `Command.handle` (:154-165); regexes RE_UUID (:22) and RE_PING_KEY_SLUG (:26).
**Signature:** `_process_message(remote_addr: str, mailfrom: str, mailto: str, data: bytes) -> str`; `handle_RCPT(...) -> "250 OK" | "550 5.1.1 ..."`; `self.process_message = sync_to_async(_process_message)`.
**Data Shape:** Mailbox grammar 1: `<check-uuid>@PING_EMAIL_DOMAIN`; grammar 2: `<22-char-ping-key>+<slug>@...` (slug lookup may hit MultipleObjectsReturned). Keyword classification mirrors the HTTP path: failure_kw > success_kw > start_kw > filter_default_fail > ign, over subject+plain+html2text(body).

### Decisive source
```python
# hc/api/management/commands/smtpd.py — reject at RCPT, classify at DATA
async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
    mbox, domain = address.split("@", maxsplit=1)
    if domain != settings.PING_EMAIL_DOMAIN:
        return "550 5.1.1 Recipient rejected"
    if not RE_UUID.match(mbox) and not RE_PING_KEY_SLUG.match(mbox):
        return "550 5.1.1 Invalid mailbox"
    envelope.rcpt_tos.append(address)
    return "250 OK"

def _process_message(remote_addr, mailfrom, mailto, data):
    if not connection.in_atomic_block:
        close_old_connections()      # aiosmtpd thread may hold a dead connection
    ...
    if check.filter_subject or check.filter_body:
        message = email.message_from_bytes(data, policy=email.policy.SMTP)
        text = _to_text(message, check.filter_subject, check.filter_body)
        if check.failure_kw and match_keywords(text, check.failure_kw): action = "fail"
        elif ...success_kw...: action = "success"
        elif ...start_kw...:   action = "start"
        elif check.filter_default_fail: action = "fail"
        else: action = "ign"

    check.ping(remote_addr, scheme="email", method="", ua=f"Email from {mailfrom}",
               body=data, action=action, rid=None)
```

**Flow:** Command starts an aiosmtpd Controller (background thread) then main thread sleeps 2**32 catching KeyboardInterrupt for a clean controller.stop(). handle_DATA loops rcpt_tos (multi-recipient = multi-check fan-out from one message), awaiting the sync_to_async-wrapped processor so Django ORM runs outside the event loop.
**Invariant:** RCPT-time grammar rejection is the abuse boundary: invalid mailboxes get 550 BEFORE DATA, so the server never accepts delivery it cannot route — but note lookups still happen at DATA time where DoesNotExist/MultipleObjectsReturned degrade into per-recipient strings rather than bounces. Keyword precedence is IDENTICAL to views.ping by contract (tests duplicate across both suites); manual_resume beats keywords because Check.ping rewrites action to "ign" while paused. filter_http_body is deliberately NOT honored here (HTTP-only channel filter — test_it_ignores_http_body_filters pins it). The HTML leg runs through html2text with script/style stripped so keyword matching can't be poisoned by markup.
**Probe:** `hc/api/tests/test_smtpd.py::test_it_works` (scheme=="email", ua=="Email from foo@example.org"), `test_rcpt_handler_rejects_non_uuid_mailboxes`, `test_it_handles_ambiguous_slug`, `test_manual_resume_takes_precedence_over_keywords`, `test_it_handles_non_ascii_keywords`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "smtpd ping handler rcpt process message", limit: 10 });
```
Resolves line-exact: PingHandler methods :110-140.

## Verdict
Adopt recipient-grammar gating at protocol time, shared keyword-precedence classification with the HTTP path, async-to-sync ORM bridging, and per-recipient error isolation. Adapt the SMTP library, mailbox grammar, and domain pinning. Omit the slug alias if UUID-only pings suffice — but keep "reject early at RCPT, never trust content before acceptance".

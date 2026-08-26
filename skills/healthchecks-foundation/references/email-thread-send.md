<!-- capsule-v2 -->
# Email thread send — background threads with bounded retry, blocking-mode seams, and bounce-address plumbing

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does a request path send transactional email without blocking on SMTP, yet keep alerts/reports synchronous enough to be testable and retry-tolerant?

## hc/lib/emails.py: EmailThread / make_message / send
**Path/Symbol:** `hc/lib/emails.py:EmailThread.run` (:19-33), `make_message` (:36-66), `send` (:68-82), per-name helpers (`alert` :92-102 block=True, `login`/`verify_email`/`sms_limit` non-blocking); template triple `emails/<name>-{subject,body-text,body-html}`; consumer discipline in Channel.notify & Profile.send_report.
**Signature:** `send(message: Message, block: bool = False) -> None`; `make_message(name, to, ctx, headers=None) -> EmailMultiAlternatives`; `EmailThread.MAX_TRIES = 3`.
**Data Shape:** Headers dict carries List-Unsubscribe(+Post One-Click), X-Bounce-ID (popped and folded into MAIL FROM via settings.EMAIL_MAIL_FROM_TMPL), From display override. Message-ID domain derived from DEFAULT_FROM_EMAIL.

### Decisive source
```python
# hc/lib/emails.py — retry ONLY transient SMTP classes, 1s between, then re-raise
def run(self) -> None:
    for attempt in range(self.MAX_TRIES):
        try:
            self.message.send()
            return
        except (SMTPServerDisconnected, SMTPDataError):
            if attempt + 1 == self.MAX_TRIES:
                raise
            time.sleep(1)

# ...and the test seam:
def send(message, block=False):
    assert settings.MAILERS, "No SMTP configuration..."
    t = EmailThread(message)
    if block or hasattr(settings, "BLOCKING_EMAILS"):
        t.run()      # in tests: synchronous, inspectable via mail.outbox
    else:
        t.start()
```

**Flow:** make_message renders subject/text/html from the name-keyed template triple, strips \xa0 (non-breaking spaces double SMS cost and mangle text parts — same substitution as transports.tmpl), attaches html alternative, sets Message-ID domain and display-From, converts X-Bounce-ID into a signed envelope sender when EMAIL_MAIL_FROM_TMPL is set. Callers choose the mode: login links fire-and-forget (user waits for nothing), while alert/report/nag/flapping/deletion mail passes block=True because the sending loop already throttles and wants synchronous failure semantics.
**Invariant:** The exception tuple is the policy: SMTPServerDisconnected/SMTPDataError are retry-worthy; anything else surfaces immediately. block=True + thread.run() (not start()) is what makes Django's mail.outbox deterministic in tests AND makes alert-sends observable to the notify ladder's error capture — swapping it for always-async would strand both. The MAILERS assert turns "email silently never sent" into a loud misconfiguration. BLOCKING_EMAILS hasattr-detection exists so self-hosters can force sync without code changes.
**Probe:** `hc/lib/tests/test_emails.py::test_it_retries` (call_count 2 after one disconnect), `test_it_limits_retries` (3 then raise), `test_it_retries_smtp_data_error`, `test_it_requires_smtp_configuration` (AssertionError under empty MAILERS), `hc/accounts/tests/test_profile_model.py::test_send_report_sets_custom_mail_from` (r.<username>@ envelope, From header preserved).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "emailthread send message retry smtp", limit: 10 });
```
Resolves line-exact: test pins hc/lib/tests/test_emails.py :14-47.
**Retrieve:** see above block (kept single retrieval per capsule contract).

## Verdict
Adopt named-template-triple message construction, class-scoped transient-retry with hard cap, dual sync/async dispatch with an explicit test seam, and bounce-id-to-envelope folding. Adapt to your mail stack (celery tasks replace threads cleanly if you keep block semantics for alert-class mail). Omit UCS2 economics at your peril only if you never text-ify HTML.

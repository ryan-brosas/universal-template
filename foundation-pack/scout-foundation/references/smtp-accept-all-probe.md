<!-- capsule-v2 -->
# SMTP accept-all probe — how do you verify a bare address exists without a verification API?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does raw SMTP RCPT distinguish real mailboxes from catch-all servers, and what does a failed handshake do to the score?

## MX-pick → real-RCPT vs fake-RCPT differential, exception = weak positive
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._verify_email_smtp` (:301-338).
**Signature:** `_verify_email_smtp(email) -> Dict{'exists': bool, 'accept_all': bool, 'score': int}`.
**Data Shape:** malformed input (`!=` 2 `@`-parts) short-circuits to all-false/0; MX resolution failure ditto (no partial credit); success path scores: MX found +10, RCPT 250 +80, fake-RCPT-also-250 ⇒ accept_all=True and score FLOORED to `max(score-40, 30)`; connection-level exceptions (SMTPServerDisconnected/SMTPConnectError/socket.timeout/ConnectionRefusedError/OSError) add +20 as a weak-existence hedge.

### Decisive source
```python
mx_records = dns.resolver.resolve(domain, 'MX')
mx_host = str(sorted(mx_records, key=lambda x: x.preference)[0].exchange).rstrip('.')
...
smtp.helo('scout-verify.local')
smtp.mail('verify@scout-verify.local')
code, msg = smtp.rcpt(email)
if code == 250: result['exists'] = True; result['score'] += 80

fake = f'zzznonexistent999@{domain}'          # the differential twin
code2, _ = smtp.rcpt(fake)
if code2 == 250:                               # server accepts anything
    result['accept_all'] = True
    result['score'] = max(result['score'] - 40, 30)   # floor at 30, never zero
```

**Flow:** parse domain → resolve MX, sort by preference, take lowest → connect :25 → HELO/MAIL FROM with a clearly-fake local sender → RCPT the target (250 ⇒ exists) → RCPT a garbage address on the same domain (also 250 ⇒ catch-all, downgrade but don't discard).
**Invariant:** the two RCPTs are a DIFFERENTIAL pair — neither alone decides; accept-all servers still yield score 30, not 0, because a catch-all domain usually belongs to a real company. Exceptions are scored POSITIVELY (+20): greylisting/timeouts mean the server talked back, which is evidence of life. A porter who treats exceptions as failure inverts the semantics.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "smtp.rcpt\|zzznonexistent\|x.preference" app/scrapers/enrichment.py` → exactly 2 rcpt sites (:321, :328), the fake twin (:327), and the preference sort (:310); `grep -n "max(result\['score'\] - 40, 30)" app/scrapers/enrichment.py` pins the floor.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_verify_email_smtp MX rcpt accept_all", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the differential-RCPT contract (real vs garbage recipient), the preference-sorted MX pick, and the exception-as-weak-positive scoring; adapt HELO/sender domains (use your own, some servers reject `scout-verify.local`-shaped senders silently) and score weights; omit nothing structural — but remember this only runs when the funnel has ZERO cheaper candidates (see `candidate-funnel`), so it is a last-resort verifier, not a bulk validator.

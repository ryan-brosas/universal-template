<!-- capsule-v2 -->
# SMTP verify + accept-all detector — how do you test an inbox exists WITHOUT landing on catch-all servers?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What is the RCPT-probe sequence that distinguishes a real mailbox from an accept-all server, and what does each outcome do to the score?

## MX-priority connect, real-then-fake RCPT pair, asymmetric penalties
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._verify_email_smtp` (:301-338); consumer gates :84, :365-368.
**Signature:** `_verify_email_smtp(email: str) -> Dict{'exists': bool, 'accept_all': bool, 'score': int}`.
**Data Shape:** connects to lowest-preference MX host on port 25 with `timeout=10`; HELO/MAIL FROM use the throwaway domain `scout-verify.local`.

### Decisive source
```python
mx_records = dns.resolver.resolve(domain, 'MX')
mx_host = str(sorted(mx_records, key=lambda x: x.preference)[0].exchange).rstrip('.')
result['score'] += 10                                  # valid MX alone earns 10

with smtplib.SMTP(timeout=10) as smtp:
    smtp.connect(mx_host, 25)
    smtp.helo('scout-verify.local')
    smtp.mail('verify@scout-verify.local')
    code, msg = smtp.rcpt(email)
    if code == 250: result['exists'] = True; result['score'] += 80

    fake = f'zzznonexistent999@{domain}'                # SAME domain control probe
    code2, _ = smtp.rcpt(fake)
    if code2 == 250:
        result['accept_all'] = True
        result['score'] = max(result['score'] - 40, 30)  # floor at 30, never below
except (...socket.timeout, ConnectionRefusedError, OSError):
    result['score'] += 20                               # unreachable server still counts FOR
```

**Flow:** resolve MX → sort by preference, take primary → HELO/MAIL FROM from `.local` → RCPT the real address → immediately RCPT a garbage local-part on the same domain. If the garbage is ALSO accepted (250), every address on that domain would "verify", so `accept_all=True` caps confidence (score floored at 30; callers additionally require `not accept_all` before trusting an smtp_guess).
**Invariant:** the fake-address control MUST target the same domain as the candidate — that's what makes it a differential test rather than another guess. The except-path ADDS 20 points: network failure is treated as weak positive evidence (domain exists, mail infra present), distinct from hard rejection. Score floors prevent negative-confidence emails.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "zzznonexistent999\|accept_all" enrichment.py` pins the control probe (:327-331) and both consumer gates (:84, :367); graph retrieval resolves `Scout.app.scrapers.enrichment.LeadEnricher._verify_email_smtp`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_verify_email_smtp rcpt accept_all", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-RCPT differential probe and the score floor; adapt HELO identity (porters should use their own domain — `.local` sender domains get rejected by stricter MTAs) and add rate limiting/politeness delays Scout doesn't have; omit port-25 assumptions where outbound SMTP is blocked (cloud hosts) — degrade to MX-exists-only scoring.

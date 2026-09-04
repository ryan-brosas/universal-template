<!-- capsule-v2 -->
# Bounce pipeline — signed reply-to addresses, DSN status classification, and always-200 webhooks

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you ingest asynchronous SMTP bounces to auto-disable dead alert channels without letting the mail provider retry-loop you?

## bounces view + sign_bounce_id + HexTimestampSigner
**Path/Symbol:** `hc/api/views.py:bounces` (:881-948), `notification_status` (:814-852, the Twilio twin); `hc/lib/signing.py:HexTimestampSigner/ShortHexTimestampSigner/sign_bounce_id/unsign_bounce_id` (:1-62).
**Signature:** `sign_bounce_id(s: str) -> str`; `unsign_bounce_id(s: str, max_age: int) -> str`; view is @csrf_exempt POST at `/api/v1..3/bounces/`.
**Data Shape:** Signed payload grammar: `n.<notification-uuid>` (per-notification) and `r.<username>` (report-level), timestamp appended after "." sep, hex-encoded. EMAIL_MAIL_FROM_TMPL="%s@bounces.example.org" turns bounce ids into envelope senders; X-Bounce-ID header carries them otherwise.

### Decisive source
```python
# hc/lib/signing.py — short signatures because email local-parts cap at 64 chars
def signature(self, value):
    full = hex_hmac(self.salt + "signer", value, key, algorithm=self.algorithm)
    # Chop off ... The goal is to make a signed "n.<uuid>" or "r.<uuid>" string
    # fit in 64 characters so it can be used in the local-part of an email address.
    return full[:16]

# hc/api/views.py — DSN walk and the 5.x/4.x decision
status, diagnostic = "", ""
for part in msg.walk():
    if "Status" in part and "Action" in part:
        status = part["Status"]
        diagnostic = part.get("Diagnostic-Code", "")
        ...
permanent = status.startswith("5.")
transient = status.startswith("4.")
if status == "5.4.4":      # unable to route (DNS) — recoverable in practice
    permanent = False
    transient = True

if permanent:
    channel_q.update(disabled=True)
```

**Flow:** Every alert email carries X-Bounce-ID + signed MAIL FROM. A bounce POST unsigns with max_age=48h (bad signature → literal "OK (bad signature)" 200 so the provider stops retrying), walks MIME parts for Status/Diagnostic-Code, classifies, then: `n.` payload → stamp Notification.error + Channel.last_error (+disabled if permanent, within 48h of creation); `r.` + permanent → switch reports off AND clear nag_period entirely.
**Invariant:** Bounce/status endpoints ALWAYS answer 200 — non-2xx teaches the remote MTA/API to redeliver forever against data you already classified. Age gates run both on the signature (48h) and the row (Notification created <48h ago) because a stale signature can still match a live-ish row you no longer trust. The 5.4.4 special case proves classification is semantic, not prefix-mechanical. ShortHexTimestampSigner's truncated MAC is an explicit RFC-5321 length trade-off, dual-verified by test_it_does_not_exceed_64_characters; unsign tries FULL hex sha1 first then SHORT — signers may differ by sender path.
**Probe:** `hc/api/tests/test_bounces.py::test_it_handles_permanent_notification_bounce`, `test_it_categorizes_5_4_4_as_transient`, `test_it_handles_bad_signature`, `test_it_checks_notification_age`, `hc/lib/tests/test_signing.py::SignBounceIdTestCase::test_it_does_not_exceed_64_characters`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "bounce unsign notification dsn status", limit: 10 });
```
Resolves line-exact via signing symbols and test pins in test_bounces.py :76-187.

## Verdict
Adopt signed per-message return addresses, always-200 webhook posture, dual age-gating, and semantic DSN classification with named exceptions. Adapt the signer stack to your framework's timestamped signers (keep the local-part budget rule). Omit the report-suppression (`r.`) branch if you send no recurring mail — but keep "transient bounces degrade, permanent bounces disable".

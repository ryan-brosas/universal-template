<!-- capsule-v2 -->
# sns-signature-verification-cache — How is an SNS/SES webhook payload authenticated without trusting its own URLs?

**Source:** listmonk AGPL-3.0 (patterns only) `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What does correct SNS SignatureVersion-1 verification look like, including the certificate-fetch guard?

## Cert-URL allowlist + SHA1WithRSA canonical serialization
**Path/Symbol:** `internal/bounce/webhooks/ses.go` — regex `sesRegCertURL` (:26), `buildSignature` (:177-198), `verifyNotif` (:200-216), `getCert` (:218-274).
**Signature:** `func (s *SES) verifyNotif(n sesNotif) error` → `cert.CheckSignature(x509.SHA1WithRSA, s.buildSignature(n), sign)`.
**Data Shape:** sesNotif carries Message/MessageId/Timestamp/Token/TopicArn/Type (+optional Subject/SubscribeURL); certs cached map[certPath]*x509.Certificate under RWMutex.

### Decisive source
```go
var sesRegCertURL = regexp.MustCompile(
	`(?i)^https://sns\.[a-z0-9\-]+\.amazonaws\.com(\.cn)?/SimpleNotificationService\-[a-z0-9]+\.pem$`)
...
// getCert: fetch ONLY after the URL matches the Amazon pattern; cache by u.Path
s.mu.RLock(); c, ok := s.certs[u.Path]; s.mu.RUnlock()
if ok { return c, nil }
resp, err := http.Get(certURL) ...
// double-check after fetch: another goroutine may have cached while we fetched
if c2, ok := s.certs[u.Path]; ok && c2 != nil { s.mu.Unlock(); return c2, nil }
if err == nil { s.certs[u.Path] = cert } // never cache parse failures
```

**Flow:** parse envelope → fetch cert (URL MUST match the SNS host pattern — blocks SSRF-by-SigningCertURL) → rebuild the canonical newline-delimited "Field\nValue\n" byte stream in FIXED order (Message, MessageId, optional Subject, optional SubscribeURL, Timestamp, Token, TopicArn, Type) → SHA1WithRSA over it vs base64 Signature. SubscriptionConfirmation then GETs the SubscribeURL (also Amazon-controlled) to activate the topic. Timestamp parsing uses a custom unmarshaller with nanosecond layout `2006-01-02T15:04:05.999999999Z`.
**Invariant:** The cert-URL allowlist runs BEFORE any outbound request — verifying the signature of an attacker-chosen cert is worthless if the cert comes from the attacker. The post-fetch double-check makes concurrent first requests safe without singleflight. Never cache x509 parse failures.
**Probe:** `bash -c "cd <repo> && sed -n '26p' internal/bounce/webhooks/ses.go | grep -c 'SimpleNotificationService-'"` → 1; `grep -cF 'x509.SHA1WithRSA' internal/bounce/webhooks/ses.go` → 1; `grep -cF 'another goroutine already cached it' internal/bounce/webhooks/ses.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "getCert verifyNotif signature", limit: 10 });
```
## Verdict
Adopt for any SNS-style inbound webhook (also matches Azure Event Grid validation shape). Adapt hash algo per provider spec. Omit region regex breadth if your provider list is fixed.

<!-- capsule-v2 -->
# multi-provider-webhook-dispatch — One endpoint, many providers: how are registration handshakes and payload parsers routed?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How does BounceWebhook route per provider, and what must a new provider integration implement?

## switch-true service router with per-provider handshake headers
**Path/Symbol:** `cmd/bounce.go:BounceWebhook` (:124-288); field validator `validateBounceFields` (:290-312); engines under `internal/bounce/webhooks/` (ses.go :74-78 NewSES; azure.go; sendgrid.go; postmark.go; forwardemail.go; lettermint.go); raw-body rationale comment (:137-139).
**Signature:** handler reads `c.Param("service")`; each engine exposes `ProcessBounce(...) ([]models.Bounce, error)` plus an optional `ProcessSubscription/ProcessSubscription` registration arm.
**Data Shape:** nil-engine check per provider (`a.bounce.SES != nil` etc.) because engines are constructed only when configured.

### Decisive source
```go
rawReq, err := io.ReadAll(c.Request().Body) // NOT c.Bind(): keep full raw body as bounce Meta
...
case service == "ses" && a.bounce.SES != nil:
	switch c.Request().Header.Get("X-Amz-Sns-Message-Type") {
	case "SubscriptionConfirmation", "UnsubscribeConfirmation":
		if err := a.bounce.SES.ProcessSubscription(rawReq); err != nil { ... }
	case "Notification": ...
	}
...
for _, b := range bounces {
	if err := a.bounce.Record(b); err != nil {
		a.log.Printf("error recording bounce: %v", err) // log-only: webhook still 200s
	}
}
```

**Flow:** read RAW body once → route on `:service`: native (JSON body validated by validateBounceFields), ses (SNS header picks Subscription vs Notification), azure (`aeg-event-type` header, validation reply echoes the JSON response), sendgrid (`X-Twilio-Email-Event-Webhook-Signature`+Timestamp ECCE verify inside engine), postmark (echo.HTTPError passthrough), forwardemail (`X-Webhook-Signature` HMAC), lettermint → collect []Bounce → Record each with log-only failure → always respond 200 okResp.
**Invariant:** Handshake headers differ PER PROVIDER (SNS message-type vs Event Grid vs signature headers) — a generic middleware would misroute. Parse failures return 400 BEFORE any recording; record failures never fail the webhook (provider retries would duplicate). Raw body preservation is deliberate: unparseable payloads still land in meta for forensics.
**Probe:** `bash -c "cd <repo> && grep -oE 'service == \"[a-z]+\"' cmd/bounce.go | sort -u"` → azure, forwardemail, lettermint, postmark, sendgrid, ses (6 + native empty-string arm); `grep -cF 'a.bounce == nil' cmd/bounce.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "BounceWebhook ses", limit: 10 });
```
## Verdict
Adopt single-endpoint routing keyed on path param + provider-specific handshake headers, parse-gate-then-record-fail-open. Adapt engines to your ESP set. Omit vendor signature schemes you don't use (each capsule-worthy in its own right — see SNS twin below).

<!-- capsule-v2 -->
# Webhook retry funnel — how do you deliver event webhooks with bounded retries and a full attempt audit trail?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does an event become per-subscriber webhook requests, how are failures retried, and what gets recorded?

## WebhookRequest.trigger + WebhookDeliveryService
**Path/Symbol:** `app/models/webhook_request.rb:trigger` (41–49); `app/services/webhook_delivery_service.rb` (RETRIES :5, call :11–18, generate_payload :27–33, send_request :36–43, record_attempt :45–66, appreciate_http_result :68–77, update_webhook_request :80–90); claim job `app/lib/worker/jobs/process_webhook_requests_job.rb:lock_request_for_processing` (26–32).
**Signature:** `WebhookRequest.trigger(server, event, payload = {})`; `WebhookDeliveryService#call → void`, `#success? → Boolean`.
**Data Shape:** request row `{event, payload(serialized Hash), url, uuid, attempts, retry_after, locked_by/at}`; RETRIES = `{1=>2.min, 2=>3.min, 3=>6.min, 4=>10.min, 5=>15.min}`; delivery ledger row in the server's message DB: `{event, url, webhook_id, attempt, timestamp, payload, uuid, status_code, body, will_retry}`.

### Decisive source
```ruby
# fan-out: one event → one request ROW per matching webhook (enabled + all_events OR specific)
webhooks = server.webhooks.enabled.includes(:webhook_events).references(:webhook_events)
             .where("webhooks.all_events = ? OR webhook_events.event = ?", true, event)
webhooks.each { |webhook| server.webhook_requests.create!(event:, payload:, webhook:, url: webhook.url) }

def call   # five ordered steps inside one tagged-logger block
  generate_payload                       # {event, timestamp, payload, uuid} → JSON
  send_request                           # Postal::HTTP.post(url, sign: true, json:, timeout: 5)
  record_attempt                         # attempts += 1; retry_after = success ? nil : RETRIES[attempts]&.from_now
  appreciate_http_result                 # 2xx ⇒ destroy! + webhook.last_used_at; else set error string
  update_webhook_request                 # retry_after ? unlock+save : destroy! (give up)
end

# the give-up boundary is RETRIES[attempts] == nil at attempts >= 6:
@attempt = @webhook_request.server.message_db.webhooks.record(
  ..., attempt: @webhook_request.attempts, will_retry: @webhook_request.retry_after.present?)
```

**Flow:** trigger fans out synchronously into durable rows → the worker job claims ONE unlocked+ready request via the same UPDATE…LIMIT stamp pattern as messages (`WebhookRequest.unlocked.ready.limit(1)`) → delivery service runs its 5 steps → 2xx destroys the request; anything else schedules `retry_after` from the fixed ladder keyed by the NEW attempt count and unlocks the row for another worker → after attempt 5 fails there is no ladder entry, so `retry_after` stays nil and step 5 destroys the request. Every attempt (success or failure) writes an immutable ledger row including response body.
**Invariant:** the ladder is FIXED and small (2/3/6/10/15 min ≈ done within ~36 min) — no exponential explosion hammering dead endpoints. The attempt ledger lives in the per-server message DB (not the control-plane row), so the customer-visible history survives even after the queue row is destroyed; `will_retry` is computed from `retry_after.present?` so it can never disagree with scheduling. Signing uses the same RSA JWK headers as all Postal HTTP (`X-Postal-Signature-KID/-Signature/-Signature-256`). Blocked/private destinations don't raise: AddressGuard's −4 code flows through `send_request` as a normal non-2xx failure and gets retried on schedule.
**Probe:** `spec/services/webhook_delivery_service_spec.rb:39–141` (200⇒destroy + last_used_at; first 500⇒unlock + retry_after≈2 min; second⇒3 min; sixth⇒destroy + ledger row `will_retry?: false`; blocked URL ⇒ no HTTP request made + retry scheduled); `spec/lib/worker/jobs/process_webhook_requests_job_spec.rb`. Deterministic probe executed this pass: ladder boundaries (1→120 s … 5→900 s, 6→nil).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "WebhookDeliveryService record_attempt appreciate_http_result trigger", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-subscriber request rows fanned out at trigger time, the fixed-ladder retry with attempt-keyed give-up, unlock-on-failure claiming symmetry with the message queue, signed 5-second-timeout posts, and the separate append-only attempt ledger. Adapt ladder values, signature scheme (HMAC instead of RSA-JWK), and payload envelope shape to your host.

<!-- capsule-v2 -->
# HMAC webhook delivery — how is an outgoing delivery signed, timed out, and classified for failure?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** What must a porter replicate so consumers can verify authenticity and so failures land in the right handling branch?

## Signing and transport contract
**Path/Symbol:** `lib/webhooks/trigger.rb:Webhooks::Trigger#request_headers` (lines 54-63) and `perform_request` (41-52).
**Signature:** `request_headers(body) -> Hash`; `execute` → `perform_request` → `SafeFetch.fetch(url, method: :post, body:, headers:, open_timeout:, read_timeout:, validate_content_type: false) { |_response| nil }`.
**Data Shape:** body = `payload.to_json`; optional headers `X-Chatwoot-Delivery` (uuid), `X-Chatwoot-Timestamp` (unix seconds string), `X-Chatwoot-Signature` (`sha256=<hex>`); secret is the per-webhook row secret.

### Decisive source
```ruby
def request_headers(body)
  headers = { 'Content-Type' => 'application/json', 'Accept' => 'application/json' }
  headers['X-Chatwoot-Delivery'] = @delivery_id if @delivery_id.present?
  if @secret.present?
    ts = Time.now.to_i.to_s
    headers['X-Chatwoot-Timestamp'] = ts
    headers['X-Chatwoot-Signature'] = "sha256=#{OpenSSL::HMAC.hexdigest('SHA256', @secret, \"#{ts}.#{body}\")}"
  end
  headers
end
```

**Flow:** job calls `Webhooks::Trigger.execute(url, payload, type, secret:, delivery_id:)` → serialize payload once (`body`) so signed bytes equal sent bytes → SafeFetch POST with both open and read timeouts from `GlobalConfig.get_value('WEBHOOK_TIMEOUT')` defaulting to **5** seconds when blank/non-positive (lines 118-123) → any raised StandardError routes to retry classification or `handle_failure`.
**Invariant:** The HMAC input is `"#{timestamp}.#{body}"` — timestamp PREFIXED to the raw serialized body, dot-separated — not the body alone; consumers replay this construction to verify. Signing happens per attempt (fresh `Time.now.to_i`), so retries carry fresh timestamps. Timeouts apply to BOTH open and read phases.
**Probe:** `grep -n '"#{ts}.#{body}"' lib/webhooks/trigger.rb` → line 60 (single decisive site); direct test `spec/lib/webhooks/trigger_spec.rb` line 235 pins `'signs timestamp.body not just body'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "Webhooks Trigger request_headers X-Chatwoot-Signature HMAC", limit: 5 });
```
Rank-1: `Webhooks::Trigger.retryable_agent_bot_error? lib/webhooks/trigger.rb 125-127`; `execute` at 26-32 rank-2 in the same class cluster.

## Verdict
Adopt the `sha256=HMAC(secret, "{ts}.{body}")` scheme with per-attempt timestamps and dual open/read timeout defaulting. Adapt GlobalConfig lookup to your settings layer and SafeFetch to your HTTP client. Omit the specific header names only if your consumers are new (they are the wire contract for existing Chatwoot consumers).

<!-- capsule-v2 -->
# Agent-bot retry ladder — when does a delivery retry instead of fail, and what runs after the last attempt?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does the same Trigger class produce retry-then-compensate for agent bots but immediate-compensate for every other webhook type?

## RetryableError classification and ActiveJob handoff
**Path/Symbol:** `lib/webhooks/trigger.rb:Webhooks::Trigger.execute` (lines 26-32), `RETRYABLE_AGENT_BOT_STATUSES = [429, 500]` (line 3); `app/jobs/agent_bots/webhook_job.rb:AgentBots::WebhookJob` (whole file, 16 lines).
**Signature:** `retry_on Webhooks::Trigger::RetryableError, wait: 3.seconds, attempts: 3 do |job, error| ... end`; `http_status(error) = error.message[/\A(\d{3})\b/, 1]&.to_i` only for `SafeFetch::HttpError`.
**Data Shape:** `RetryableError(status:, message:)` carries the HTTP status parsed out of SafeFetch's `"{code} {message}"` string; queue is `:high` (vs parent's `:medium`).

### Decisive source
```ruby
# lib/webhooks/trigger.rb
def execute
  perform_request
rescue StandardError => e
  raise RetryableError.new(status: http_status(e), message: e.message) if retryable_agent_bot_error?(e)
  handle_failure(e)
end

def retryable_agent_bot_error?(error)
  @webhook_type == :agent_bot_webhook && RETRYABLE_AGENT_BOT_STATUSES.include?(http_status(error))
end

# app/jobs/agent_bots/webhook_job.rb
retry_on Webhooks::Trigger::RetryableError, wait: 3.seconds, attempts: 3 do |job, error|
  url, payload, webhook_type = job.arguments
  kwargs = job.arguments.last.is_a?(Hash) ? job.arguments.last : {}
  Webhooks::Trigger.new(url, payload, webhook_type || :agent_bot_webhook, secret: kwargs[:secret],
                          delivery_id: kwargs[:delivery_id]).handle_failure(error)
end
```

**Flow:** bot delivery fails with HTTP 429/500 → execute re-raises as RetryableError → ActiveJob discards/re-enqueues with fixed 3s wait up to 3 total attempts → on final discard the retry_on BLOCK runs → reconstructs the exact original arguments (including kwargs hash detection, because plain positional args carry no secret) → calls handle_failure directly, which runs the compensation logic once. Any other status or webhook type goes straight to handle_failure inside the first attempt with no retries.
**Invariant:** Retry eligibility requires BOTH conditions — webhook_type is :agent_bot_webhook AND status ∈ {429,500}; the compensation block fires exactly once per delivery lifecycle (only at final discard), so pending-conversation reopening cannot run mid-retry. A porter who lets account_webhooks raise RetryableError gets infinite-ish Sidekiq noise; one who forgets the closure loses compensation entirely after exhausted retries.
**Probe:** `grep -n 'attempts: 3' app/jobs/agent_bots/webhook_job.rb` → line 3; `grep -n 'RETRYABLE_AGENT_BOT_STATUSES = ' lib/webhooks/trigger.rb` → line 3; direct test `spec/lib/webhooks/trigger_spec.rb` lines 77-104 pins "raises 500 errors for retry and does not reopen conversation immediately" / "raises 429 errors for retry...".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AgentBots WebhookJob retry_on RetryableError attempts", limit: 5 });
```
Cluster resolves around `lib/webhooks/trigger.rb` symbols (`execute`, `RetryableError`, `retryable_agent_bot_error?`) rank 1-3.

## Verdict
Adopt the two-condition classification + final-attempt compensation-closure pattern; it decouples "is this transient?" from "who owns the failure?". Adapt the 3s/attempts-3 numbers and ActiveJob retry_on to your job framework's equivalent. Omit Chatwoot's queue-name split unless you mirror its medium/high topology.

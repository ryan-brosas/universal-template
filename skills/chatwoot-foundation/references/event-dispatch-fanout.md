<!-- capsule-v2 -->
# Event dispatch fanout — how does one model event reach every subscriber exactly once per target class?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does a Rails callback fan one domain event out to account webhooks and channel inbox webhooks without double delivery or leaking to disabled accounts?

## Listener fanout with dual target classes
**Path/Symbol:** `app/listeners/webhook_listener.rb:WebhookListener.deliver_webhook_payloads` (lines 130-133) and `deliver_account_webhooks` (110-120).
**Signature:** `deliver_webhook_payloads(payload, inbox)` → `deliver_account_webhooks(payload, inbox.account)` + `deliver_api_inbox_webhooks(payload, inbox)`.
**Data Shape:** payload = `model.webhook_data.merge(event: __method__.to_s[, changed_attributes:])` — a flat JSON-serializable hash whose `event:` key names the event; inbox supplies both the account scope and the API-channel webhook URL.

### Decisive source
```ruby
def deliver_account_webhooks(payload, account)
  return unless account.api_and_webhooks_enabled?

  account.webhooks.account_type.each do |webhook|
    next unless webhook.subscriptions.include?(payload[:event])

    WebhookJob.perform_later(webhook.url, payload, :account_webhook,
                             secret: webhook.secret,
                             delivery_id: SecureRandom.uuid)
  end
end
```

**Flow:** model after_commit → `Rails.configuration.dispatcher.dispatch(EVENT, Time.zone.now, ...)` → listener method named exactly after the event (e.g. `conversation_status_changed`) → build payload from presenter data → fan to (1) every `account_type` Webhook row of the account whose jsonb `subscriptions` includes the event name and (2) the single `api_inbox_webhook` if `inbox.channel_type == 'Channel::Api'` and its `webhook_url` present → each becomes an async `WebhookJob.perform_later`. Contact/inbox events bypass the inbox and call `deliver_account_webhooks` directly.
**Invariant:** The account-level gate `api_and_webhooks_enabled?` short-circuits BOTH target classes; on self-host it is hard-coded `true` (`app/models/account.rb:166`) while enterprise/cloud gates it behind the `api_and_webhooks` feature flag (`enterprise/app/models/enterprise/account.rb:76`). A porter who drops the gate breaks cloud licensing; a porter who keeps only the account loop loses Channel::Api deliveries.
**Probe:** `grep -c 'deliver_webhook_payloads(payload, inbox)' app/listeners/webhook_listener.rb` from repo root → `8` (six conversation/message/typing events + typing handler's shared tail); `grep -n 'account.webhooks.account_type' app/listeners/webhook_listener.rb` → line 113 only.
**Probe:** direct test `spec/listeners/webhook_listener_spec.rb` pins "does not trigger account webhooks / still triggers API inbox webhooks" split behavior around lines 54-92.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "WebhookListener deliver_account_webhooks subscriptions", limit: 5 });
```
Rank-1: `WebhookListener.deliver_account_webhooks app/listeners/webhook_listener.rb 110-120`.

## Verdict
Adopt the dual-target fanout shape (subscription-filtered account rows + one channel endpoint), the `event:` key convention, and the account-level kill switch position. Adapt dispatcher/listener wiring to your host's pub-sub. Omit Chatwoot's specific event vocabulary unless porting the whole surface; note the runner caveat: rspec suite requires a provisioned Rails test DB (not executed this pass — evidence is byte-exact source reads plus spec titles cited).

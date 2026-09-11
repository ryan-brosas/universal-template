<!-- capsule-v2 -->
# Webhook subscription model — what makes a subscription row valid, and which events may it receive?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How are webhook endpoints registered per account so the dispatcher can trust subscriptions at fanout time?

## Webhook model validation contract
**Path/Symbol:** `app/models/webhook.rb:Webhook` (lines 21-46).
**Signature:** `validates :url, uniqueness: { scope: [:account_id] }, format: URI::DEFAULT_PARSER.make_regexp(%w[http https])`; `enum webhook_type: { account_type: 0, inbox_type: 1 }`.
**Data Shape:** columns `name, secret, subscriptions (jsonb array of event-name strings), url, webhook_type, account_id, inbox_id (optional)`; index `index_webhooks_on_account_id_and_url UNIQUE`.

### Decisive source
```ruby
ALLOWED_WEBHOOK_EVENTS = %w[conversation_status_changed conversation_updated conversation_created contact_created contact_updated
                            message_created message_updated webwidget_triggered inbox_created inbox_updated
                            conversation_typing_on conversation_typing_off].freeze

def validate_webhook_subscriptions
  invalid_subscriptions = !subscriptions.instance_of?(Array) ||
                          subscriptions.blank? ||
                          (subscriptions.uniq - ALLOWED_WEBHOOK_EVENTS).length.positive?
  errors.add(:subscriptions, I18n.t('errors.webhook.invalid')) if invalid_subscriptions
end
```

**Flow:** API creates Webhook row → presence of account_id, http(s) URL format + uniqueness scoped to account, and subscription-array validation run → listener fanout later does `webhook.subscriptions.include?(payload[:event])` trusting the stored array. The allowlist exactly mirrors the twelve listener methods in `WebhookListener`, so a new event requires touching both the listener and this constant.
**Invariant:** Subscriptions must be a NON-EMPTY Array whose deduplicated members are all inside ALLOWED_WEBHOOK_EVENTS; blank or unknown-event subscriptions are rejected at write time so the read-side `include?` filter can never face malformed data. `(account_id,url)` uniqueness prevents duplicate deliveries to the same endpoint within one tenant while permitting the same URL across tenants.
**Probe:** `grep -n 'subscriptions.uniq - ALLOWED_WEBHOOK_EVENTS' app/models/webhook.rb` → line 41; `grep -n 'UNIQUE' app/models/webhook.rb` → line 18 (schema comment for the composite unique index).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "Webhook validate_webhook_subscriptions ALLOWED_WEBHOOK_EVENTS", limit: 5 });
```
Rank-1: `Webhook.validate_webhook_subscriptions app/models/webhook.rb 38-43`.

## Verdict
Adopt the write-time allowlist + non-empty-Array rule and the tenant-scoped URL uniqueness. Adapt event names to your domain's vocabulary and jsonb to your DB's JSON type. Omit the Chatwoot event list itself unless porting the full listener surface.

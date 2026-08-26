<!-- capsule-v2 -->
# Webhook error compensation — what state change repairs a conversation/message when a delivery fails mid-flight?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** After a bot or api-inbox webhook permanently fails, how does the system un-stick the waiting conversation or message without touching unrelated events?

## Event-gated compensation switch
**Path/Symbol:** `lib/webhooks/trigger.rb:Webhooks::Trigger#handle_error` (lines 65-75) with `SUPPORTED_ERROR_HANDLE_EVENTS = %w[message_created message_updated]` (line 2).
**Signature:** `handle_failure(error) → handle_error(error) + warn log`; `handle_error` dispatches on `@webhook_type`: `:agent_bot_webhook → update_conversation_status(message)`; `:api_inbox_webhook → update_message_status(error)`.
**Data Shape:** payload must carry `payload[:id]` (message id) for `message` lookup; compensation is a no-op otherwise.

### Decisive source
```ruby
def handle_error(error)
  return unless SUPPORTED_ERROR_HANDLE_EVENTS.include?(@payload[:event])
  return unless message

  case @webhook_type
  when :agent_bot_webhook
    update_conversation_status(message)
  when :api_inbox_webhook
    update_message_status(error)
  end
end

def update_conversation_status(message)
  conversation = message.conversation
  return unless conversation&.pending?
  return if conversation&.account&.keep_pending_on_bot_failure

  conversation.open!
  create_agent_bot_error_activity(conversation)
end
```

**Flow:** permanent delivery failure on a message_created/updated payload → look up the message once (memoized) → agent-bot path: only pending conversations flip to open via `conversation.open!` (which emits the normal status events), plus an I18n activity message enqueued through `Conversations::ActivityMessageJob` — UNLESS the account set `keep_pending_on_bot_failure`, which intentionally leaves the conversation parked for manual triage → api-inbox path: `Messages::StatusUpdateService.new(message, 'failed', error.message).perform` marks delivery failed so the UI shows it.
**Invariant:** Compensation is DOUBLE-GATED — event name ∈ {message_created, message_updated} AND webhook type ∈ {agent_bot_webhook, api_inbox_webhook}; account/contact/inbox webhooks never mutate domain state on failure (they just log). The pending→open move honors the per-account opt-out flag checked BEFORE opening, so the flag wins over the default self-heal.
**Probe:** `grep -n 'keep_pending_on_bot_failure' lib/webhooks/trigger.rb` → line 80 exactly; direct test `spec/lib/webhooks/trigger_spec.rb` lines 136-166 pins "keeps conversation pending when keep_pending_on_bot_failure setting is enabled" and "reopens... when disabled"; line 260 pins no status update "for other events".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "Webhooks Trigger update_conversation_status pending keep_pending_on_bot_failure", limit: 5 });
```
Resolves inside the `lib/webhooks/trigger.rb` Webhooks::Trigger method cluster (update_conversation_status 77-84).

## Verdict
Adopt double-gated compensation with an explicit event allowlist and per-tenant opt-out flag; adopt "failure of a notification must not silently strand the waiting entity". Adapt the specific repairs (open! / status='failed') to your domain's recovery verbs. Omit the activity-message side channel if you have no audit trail requirement.

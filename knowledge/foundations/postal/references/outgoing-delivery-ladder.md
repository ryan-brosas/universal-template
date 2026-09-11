<!-- capsule-v2 -->
# Outgoing delivery ladder — which gates run, in what order, and how does suppression self-heal?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** What is the exact ordered pre-send gate sequence for outgoing mail, and how do send limits and the suppression list interact with outcomes?

## OutgoingMessageProcessor
**Path/Symbol:** `app/lib/message_dequeuer/outgoing_message_processor.rb:process` (6–29), check_send_limits (118–131), send_message_to_sender (134–145), add_recipient_to_suppression_list_on_too_many_hard_fails (148–166), remove_recipient_from_suppression_list_on_success (168–176), finish_processing (178–190).
**Signature:** `process → void` (result recorded via deliveries); internal `@result`/`@additional_delivery_details` feed `log_sender_result`.
**Data Shape:** Server columns used as a tri-state latch: `send_limit_exceeded_at`, `send_limit_approaching_at` (+ `*_notified_at`); suppression rows `{type: :recipient, address, reason, keep_until}`.

### Decisive source
```ruby
# process — ORDER IS THE CONTRACT
check_domain; check_rcpt_to; add_tag
hold_if_credential_is_set_to_hold          # credential.hold? ⇒ Held (manual sends bypass)
hold_if_recipient_on_suppression_list      # manual sends bypass — see below
parse_content                              # only if !parsed?
inspect_message                            # spam_score >= server.outbound_spam_threshold ⇒ spam=true
fail_if_spam                               # spam ⇒ HardFail
add_outgoing_headers                       # X-Postal-MsgID + DKIM if missing
check_send_limits                          # exceeded⇒Held / approaching⇒flag-only / else clear flags
increment_live_stats
hold_if_server_development_mode            # Development servers hold non-manual mail
send_message_to_sender                     # @state.send_result reuse across batch!
add_recipient_to_suppression_list_on_too_many_hard_fails
remove_recipient_from_suppression_list_on_success
log_sender_result
finish_processing                          # result.retry ? retry_later : remove_from_queue

def check_send_limits
  if queued_message.server.send_limit_exceeded?
    queued_message.server.update_columns(send_limit_exceeded_at: Time.now, send_limit_approaching_at: nil)
    create_delivery "Held", details: "Message held because send limit (#{...}) has been reached."
    remove_from_queue; stop_processing
  elsif queued_message.server.send_limit_approaching?
    queued_message.server.update_columns(send_limit_approaching_at: Time.now, send_limit_exceeded_at: nil)
  else
    queued_message.server.update_columns(send_limit_approaching_at: nil, send_limit_exceeded_at: nil)
  end
end
```

**Flow:** cheap data-shape checks first, policy holds next, content work (parse/inspect/headers) only once (`should_parse?`, `inspected`, `has_outgoing_headers?` idempotence gates), then the send. After sending, outcome-driven side effects: HardFail counts recent HardFails to the same recipient within 24 h via the message DB (`where: {rcpt_to:, status:"HardFail", timestamp:{greater_than: 24.hours.ago.to_f}}, count: true`) and adds the recipient to the suppression list when ≥1 exists; Sent removes them again. `finish_processing`: `@result.retry` truthy → `retry_later(Integer or default)` + stop; else destroy.
**Invariant:** manual (`manual: true`) queue entries bypass ALL hold gates (credential hold, suppression, development-mode) so an operator can force delivery through — but NOT the hard-fail gates (spam, max attempts). The suppression list is self-healing: one success re-admits the recipient, so stale entries never need manual pruning. Send-limit state is stored as timestamp columns where "approaching" and "exceeded" are mutually exclusive on every write.
**Probe:** `spec/lib/message_dequeuer/outgoing_message_processor_spec.rb:265–320` (exceeded/approaching/clear tri-state), :402–461 (hard-fail suppression add after 2 HardFails incl. logged reason; manual+Sent removes from suppression list); deterministic probe executed this pass: retry-time extraction & suppression count queries.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "OutgoingMessageProcessor check_send_limits suppression_list finish_processing", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ordered gate ladder with idempotent per-stage guards, outcome-triggered suppression add/remove (self-healing blocklist), the tri-state send-limit latch, and the manual-send bypass matrix. Adapt threshold columns and the 24 h window constants. Omit DKIM/X-Postal header specifics unless porting the full MTA.

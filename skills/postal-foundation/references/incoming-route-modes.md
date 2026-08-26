<!-- capsule-v2 -->
# Incoming route modes — how does inbound mail become a bounce link, a quarantine, or an endpoint forward?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How are bounce messages linked back to originals, and what do route spam/mode settings do to an accepted message?

## IncomingMessageProcessor
**Path/Symbol:** `app/lib/message_dequeuer/incoming_message_processor.rb:process` (8–27), handle_bounces (33–61), inspect_message (65–91), find_route (93–101), hold_or_reject_spam (103–120), accept_mail_without_endpoints (122–129), hold_messages (131–144), bounce_messages (146–158), send_message_to_sender (160–182), finish_processing (200–214).
**Signature:** `process → void`; `attr_reader route` set by `find_route`.
**Data Shape:** Route has `mode ∈ {Accept, Hold, Bounce, Reject}` + `spam_mode ∈ {Quarantine, Fail, …}`; endpoint polymorphism via `endpoint_type`: SMTPEndpoint | HTTPEndpoint | AddressEndpoint.

### Decisive source
```ruby
def handle_bounces
  return unless queued_message.message.bounce
  original_messages = queued_message.message.original_messages
  unless original_messages.empty?
    original_messages.each do |orig_msg|
      queued_message.message.update(bounce_for_id: orig_msg.id, domain_id: orig_msg.domain_id)
      create_delivery "Processed", details: "...bounce message for <msg:#{orig_msg.id}>."
      orig_msg.bounce!(queued_message.message)      # mark original Bounced + webhook event
    end
    remove_from_queue; stop_processing              # linked bounces never route further
  end
  return unless queued_message.message.route_id.nil?   # unmatched bounce WITH no route…
  create_delivery "HardFail", details: "…couldn't link it with any outgoing message…"
  remove_from_queue; stop_processing                 # …is dropped here
end

def send_message_to_sender
  @result = @state.send_result          # batch reuse: first failure cached for siblings
  return if @result
  case queued_message.message.endpoint
  when SMTPEndpoint    then sender = @state.sender_for(SMTPSender, domain, nil, servers: [ep.to_smtp_client_server])
  when HTTPEndpoint    then sender = @state.sender_for(HTTPSender, ep)
  when AddressEndpoint then sender = @state.sender_for(SMTPSender, ep.domain, nil, rcpt_to: ep.address)
  else create_delivery "HardFail", details: "Invalid endpoint for route."; remove_from_queue; stop_processing
  end
end

def finish_processing
  if @result.retry
    queued_message.retry_later(@result.retry.is_a?(Integer) ? @result.retry : nil)
    queued_message.allocate_ip_address                       # retry re-rolls the sending IP
    queued_message.update_column(:ip_address_id, queued_message.ip_address&.id)
    stop_processing
  end
  queued_message.message.endpoint.mark_as_used
  remove_from_queue
end
```

**Flow:** bounce detection runs FIRST (link-to-original or drop) → live-stats increment → spam inspection writes X-Postal-Spam/Threat headers using server `spam_threshold` → `spam_failure_threshold` HardFails before routing is even considered → route resolution → route.spam_mode Quarantine⇒Held / Fail⇒HardFail (manual bypasses) → route.mode Accept⇒Processed-without-endpoint / Hold⇒Held (manual ⇒ Processed) / Bounce|Reject⇒generate bounce message + HardFail → otherwise forward to the typed endpoint sender.
**Invariant:** incoming uses `>` against `spam_threshold`/`spam_failure_threshold` while OUTGOING uses `>=` against `outbound_spam_threshold` — flipping those comparisons in a port changes which borderline messages fail. Unmatched bounces with no route are HardFailed, not retried. On retry, `ip_address_id` is re-allocated BEFORE requeueing so pool rotation happens per attempt; endpoint `mark_as_used` only fires on non-retry completion.
**Probe:** `spec/lib/message_dequeuer/incoming_message_processor_spec.rb:17–100` (unlinked-bounce HardFail; linked bounce sets Processed on received + Bounced delivery on original + MessageBounced webhook); deterministic probes executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "IncomingMessageProcessor handle_bounces hold_or_reject_spam send_bounce_on_hard_fail", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt bounce-link-before-routing, the mode×spam-mode route matrix with terminal Held/Processed/HardFail outcomes, endpoint-type-dispatched senders through shared State, and IP re-roll on retry. Adapt route/endpoint models to your tenancy shape. Omit webhook event names and header literals unless building a Postal-compatible surface.

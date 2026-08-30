<!-- capsule-v2 -->
# Dequeuer guard chain — how do you structure multi-stage message processing where every gate can terminate the pipeline?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How do you keep a 20-step delivery pipeline readable when any step may end processing, and how does batch state survive across steps?

## MessageDequeuer processor family
**Path/Symbol:** `app/lib/message_dequeuer/base.rb:Base` (StopProcessing :6, catch_stops :37, hold_if_server_development_mode :60, handle_exception :86, remove_from_queue, create_delivery), `initial_processor.rb:process` (10–30) + `find_other_messages_for_batch` (57–64), `single_message_processor.rb:process` (6–31), `state.rb:State` (7–19).
**Signature:** `MessageDequeuer.process(message, logger:)` → InitialProcessor; `SingleMessageProcessor.process(qm, logger:, state:)`; `catch_stops { … } → true|false`.
**Data Shape:** every processor takes the same `(queued_message, logger:, state:)`; State memoizes `send_result` and cached senders keyed `[klass, args, kwargs]` with `.finished` calling `finish` on each.

### Decisive source
```ruby
# base.rb — termination IS control flow: a gate ends with create_delivery + destroy + stop_processing
def stop_processing = raise StopProcessing
def catch_stops
  yield if block_given?; true
rescue StopProcessing; false; end

# initial_processor.rb — shared state + guaranteed teardown around a whole batch
begin
  catch_stops do
    check_message_exists        # backend row gone → destroy queue row, stop
    check_message_is_ready      # not due → UNLOCK (keep for later), stop
    find_other_messages_for_batch  # error here → unlock then RE-RAISE
    process_message(@queued_message)
    @other_messages&.each { |m| process_message(m) }
  end
ensure
  @state.finished               # finish SMTP sessions even on abort
end

# single_message_processor.rb — scope dispatch is itself a guarded gate
case queued_message.message.scope
when "incoming" then processor = IncomingMessageProcessor
when "outgoing" then processor = OutgoingMessageProcessor
else create_delivery "HardFail", details: "Scope #{...} is not valid"; remove_from_queue; stop_processing
end
```

**Flow:** claim → InitialProcessor validates existence/readiness, assembles the batch → per message SingleMessageProcessor runs pre-flight gates (exists / server not suspended / attempts < max / raw message present — max-attempts also sends bounces or suppresses the recipient) → scope router picks Incoming/Outgoing processor → that processor runs its ordered gate chain (see sibling capsules) → terminal states always pair a delivery record with queue removal.
**Invariant:** three exit flavors are deliberately distinct: (1) `stop_processing` = handled outcome, delivery already recorded, queue row destroyed; (2) "unlock and keep" = not-yet-due rows must be UNLOCKED, never destroyed (`check_message_is_ready`, `find_other_messages_for_batch` rescue); (3) unexpected exceptions = `handle_exception` → `retry_later` + an "Error" delivery so senders see why, only if the row still exists (`unless queued_message.destroyed?`). `state.finished` sits in `ensure` so SMTP sessions close even when a mid-batch exception escapes.
**Probe:** `spec/lib/message_dequeuer/initial_message_processor_spec.rb:22–99` (missing message destroys; not-ready unlocks-and-keeps; batch fan-out gated by config; find-error unlocks+raises); `spec/lib/message_dequeuer/state_spec.rb:14–40` (sender caching by args, finished calls finish on all); `spec/lib/message_dequeuer/base_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "StopProcessing catch_stops handle_exception InitialProcessor SingleMessageProcessor", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the StopProcessing guard-chain idiom (gates read top-to-bottom like a spec, no boolean plumbing), the shared-State-with-ensure teardown for batched sends, and the three-flavor exit contract (handled-stop vs defer-unlock vs crash-requeue). Adapt exception type to your language's control-flow norms. Omit Rails tagging/logger specifics.

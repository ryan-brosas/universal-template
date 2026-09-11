<!-- capsule-v2 -->
# Held message expiry — how do held messages get a bounded lifetime without a per-message timer?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does Postal guarantee that quarantined/held mail is eventually released or at least visibly cancelled, and what exactly happens on expiry?

## create_delivery hold stamping + ExpireHeldMessagesScheduledTask
**Path/Symbol:** `lib/postal/message_db/message.rb:create_delivery` (129–134), `cancel_hold` (543–547), hold_expiry reader (115–117); task `app/scheduled_tasks/expire_held_messages_scheduled_task.rb` (1–13); sweep `app/scheduled_tasks/tidy_queued_messages_task.rb` (1–18).
**Signature:** `Message#create_delivery(status, **opts) → Delivery`; `cancel_hold → void|Delivery`; `ExpireHeldMessagesScheduledTask#call`.
**Data Shape:** message columns `status, held, last_delivery_attempt, hold_expiry (float epoch)`; queue rows swept via `with_stale_lock`.

### Decisive source
```ruby
# EVERY delivery attempt stamps status + hold_expiry atomically on the message row
def create_delivery(status, options = {})
  delivery = Delivery.create(self, options.merge(status: status))
  hold_expiry = status == "Held" ?
    Postal::Config.postal.default_maximum_hold_expiry_days.days.from_now.to_f : nil
  update(status: status, last_delivery_attempt: delivery.timestamp.to_f,
         held: status == "Held", hold_expiry: hold_expiry)
  delivery
end

def cancel_hold   # expiry action = a terminal audit record, NOT a re-send
  return unless status == "Held"
  create_delivery("HoldCancelled", details: "The hold on this message has been removed without action.")
end

# the sweeper: one scheduled pass over ALL servers, no per-message timers
messages = server.message_db.messages(where: { status: "Held",
                                               hold_expiry: { less_than: Time.now.to_f } })
messages.each(&:cancel_hold)
```

**Flow:** any gate that holds (`suspend`, send limit, suppression list, development mode, quarantine route) lands in `create_delivery("Held")`, which simultaneously writes `hold_expiry = now + default_maximum_hold_expiry_days`. The hourly-ish tasks thread later finds Held messages whose stamp passed and records HoldCancelled — flipping status so the next sweep skips them. Separately, `TidyQueuedMessagesTask` destroys QUEUE rows whose `locked_at` is older than `queued_message_lock_stale_days`, cleaning up crashed workers rather than held messages.
**Invariant:** hold state lives on TWO artifacts with different lifecycles: the message-DB row (status+hold_expiry — customer-visible, expires by policy) and the control-plane queued_message row (lock/retry mechanics — swept when stale). Expiry produces an explicit HoldCancelled delivery instead of silently mutating or requeueing: operators see why mail vanished. Non-Held deliveries always null out `hold_expiry`, so a later Sent/HardFail clears any armed expiry.
**Probe:** `spec/scheduled_tasks/tidy_queued_messages_task_spec.rb` (stale-lock destruction); deterministic probe executed this pass verified the two-artifact split semantics from source. No upstream spec covers ExpireHeldMessages directly (needs a live message DB); caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "cancel_hold hold_expiry ExpireHeldMessagesScheduledTask", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt stamping hold TTLs onto the record AT HOLD TIME inside the same write that sets status, sweeping expired holds in bulk on a schedule, and emitting an explicit cancellation record; keep queue-mechanics cleanup separate from business hold policy. Adapt the expiry constant and whether expired mail requeues vs archives.

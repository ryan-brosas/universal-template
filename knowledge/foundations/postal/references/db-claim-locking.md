<!-- capsule-v2 -->
# DB claim locking — how do you build a safe message queue on plain SQL rows without a broker?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does Postal atomically claim queued messages across N worker threads/processes so no message is processed twice or lost?

## QueuedMessage / HasLocking
**Path/Symbol:** `app/models/queued_message.rb:QueuedMessage` (39–77), `app/models/concerns/has_locking.rb:HasLocking` (18–45), `app/lib/worker/jobs/process_queued_messages_job.rb:lock_message_for_processing` (45–51).
**Signature:** `QueuedMessage.batchable_messages(limit = 10) → Array<QueuedMessage>`; `retry_later(time = nil)`; scopes `.ready_with_delayed_retry`, `.with_stale_lock`, `.unlocked`, `.ready`.
**Data Shape:** columns `locked_by:string, locked_at:datetime, retry_after:datetime, attempts:int(default 0), batch_key:string, ip_address_id:int?`. "Ready" = `retry_after IS NULL OR retry_after < now`.

### Decisive source
```ruby
# app/models/concerns/has_locking.rb — retry bumps attempts and clears the lock in ONE update_columns
def retry_later(time = nil)
  retry_time = time || calculate_retry_time(attempts, 5.minutes)   # (1.3 ** attempts) * initial
  self.locked_by = nil; self.locked_at = nil
  update_columns(locked_by: nil, locked_at: nil,
                 retry_after: Time.now + retry_time, attempts: attempts + 1)
end

# app/lib/worker/jobs/process_queued_messages_job.rb — the claim is an atomic conditional UPDATE..LIMIT
@locker  = Postal.locker_name_with_suffix(SecureRandom.hex(8))      # unique per attempt
@lock_time = Time.current
QueuedMessage.where(ip_address_id: [nil, @ip_addresses])            # only IPs this host owns (or unassigned)
             .where(locked_by: nil, locked_at: nil)                 # unlocked only
             .ready_with_delayed_retry                              # due (retries debounced 30s)
             .limit(1)
             .update_all(locked_by: @locker, locked_at: @lock_time) # single-statement claim
@messages_to_process = QueuedMessage.where(locked_by: @locker, locked_at: @lock_time)

# app/models/queued_message.rb — batch siblings claimed under the SAME (locker, lock_time) stamp
self.class.ready.where(batch_key: batch_key, ip_address_id: ip_address_id,
                       locked_by: nil, locked_at: nil).limit(limit)
    .update_all(locked_by: locker, locked_at: time)
QueuedMessage.where(batch_key: batch_key, ip_address_id: ip_address_id,
                    locked_by: locker, locked_at: time).where.not(id: id)
```

**Flow:** job generates a globally-unique `(locker, lock_time)` pair per tick → one conditional `UPDATE … LIMIT 1` flips ownership of exactly one row (MySQL executes it atomically; losers simply update 0 rows) → the worker re-reads by that exact pair so it can never see a foreign claim even under identical names → dequeuer processes → terminal outcomes `destroy` the row, transient ones call `retry_later`. Batch mode co-claims up to 100 same-key siblings with the same stamp before processing.
**Invariant:** ownership is proven by re-reading `(locked_by == my locker AND locked_at == my exact timestamp)` — never by "I ran an UPDATE". The lock is advisory-only state: every terminal branch must either destroy the row or clear both columns (`unlock`, `retry_later`), or the message would be stuck until the stale-lock sweep. `batchable_messages` raises unless the caller already holds its own lock ("Must lock current message before locking any friends").
**Probe:** `spec/lib/worker/jobs/process_queued_messages_job_spec.rb:80–110` (message for an IP not on this host stays locked=false and untouched; ours gets `locked_by =~ /\A#{Postal.locker_name} [a-f0-9]{16}\z/`); `spec/models/queued_message_spec.rb:172–220` (batch claims match key+IP+ready only, all returned rows are locked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "batchable_messages lock_message_for_processing ready_with_delayed_retry", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-column lock contract, the atomic `UPDATE…LIMIT` + read-back-by-exact-pair claiming, batch co-claiming keyed by `(group_key, routing_key)`, the 1.3^n backoff with a floor debounce, and the scheduled sweep that destroys days-old dead locks instead of resurrecting them. Adapt column names, the IP-ownership filter (replace with your shard/routing predicate), and locker identity format to your host. Omit the Rails scope DSL if you hand-roll SQL elsewhere.

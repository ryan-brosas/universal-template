<!-- capsule-v2 -->
# Worker role election — how do you elect one leader among N workers with a single DB row and no lease daemon?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does exactly-one worker win the "tasks" role while letting a dead worker's role be taken over?

## WorkerRole
**Path/Symbol:** `app/models/worker_role.rb:WorkerRole.acquire` (24–42), `.release` (47–50); caller `app/lib/worker/process.rb:run_tasks` (216–238).
**Signature:** `WorkerRole.acquire(role) → :renewed | :stolen | :created | false`; `WorkerRole.release(role) → Boolean`.
**Data Shape:** table `worker_roles { role:string UNIQUE, worker:string, acquired_at:datetime }` — one row per role name is the whole election state.

### Decisive source
```ruby
def acquire(role)
  # 1. renew our own lock — heartbeat by timestamp bump
  updates = where(role: role, worker: Postal.locker_name).update_all(acquired_at: Time.current)
  return :renewed if updates.positive?

  # 2. steal from a worker idle > 5 minutes (dead or wedged)
  updates = where(role: role).where("acquired_at is null OR acquired_at < ?", 5.minutes.ago)
                             .update_all(acquired_at: Time.current, worker: Postal.locker_name)
  return :stolen if updates.positive?

  # 3. create the row if it doesn't exist yet (UNIQUE constraint arbitrates races)
  begin
    create!(role: role, worker: Postal.locker_name, acquired_at: Time.current)
    :created
  rescue ActiveRecord::RecordNotUnique, ActiveRecord::RecordInvalid
    false   # someone else won it between steps — stay a follower this tick
  end
end

def release(role) = where(role: role, worker: Postal.locker_name).delete_all.positive?
```

**Flow:** every tick every worker runs `acquire(:tasks)` → the returned symbol decides behavior: followers (`false`) skip task execution but keep polling so they can steal promptly; winners run all due TASKS then re-acquire next tick. On shutdown the tasks thread deletes its own row so failover happens in seconds instead of waiting out the 5-minute staleness window. The worker identity is `host:<hostname> pid:<pid> thread:<native_thread_id>` (`Postal.locker_name`, lib/postal/config.rb:98–103).
**Invariant:** each step is a single conditional UPDATE or an INSERT guarded by UNIQUE — no SELECT-then-act race exists. Steal requires BOTH `acquired_at` null-or-stale AND the atomic update winning; two thieves cannot both succeed. Losing (`false`) must never be treated as an error — it's the normal steady state for N−1 workers.
**Probe:** `spec/models/worker_role_spec.rb`; deterministic probe executed this pass re-derived the ladder (stale other → `:stolen`, own fresh → `:renewed`, absent → `:created`, contended insert → `false`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "WorkerRole acquire release", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the renew→steal→create ladder as a dependency-free leader election for any system with a transactional DB; keep the four-valued result (callers distinguish first-win from heartbeat). Adapt the 5-minute staleness to your failure-detection budget and the locker identity format. Omit nothing — the whole contract is ~30 lines.

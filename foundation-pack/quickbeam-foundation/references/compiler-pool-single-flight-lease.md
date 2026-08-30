<!-- capsule-v2 -->
# compiler-pool-single-flight-lease — How do you bound a compile-on-demand module cache so concurrent misses share one compile and a runaway compile cannot take the node down?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** What is the full lifecycle of a generated-module slot: miss → single-flight compile → lease → LRU evict/quarantine → drain?

## Single-flight leased slot seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/pool.ex` (828L) — `checkout/3` (:35-41), `checkout_miss/4` (:379-396), `start_compilation/5` (:438-473), `monitor_waiter/3` (:480-485), `finish_compilation/3` (:487-504), `issue_lease/3` (:547-572), `fetch_lease/3` (:574-584), `select_eviction/1` (:405-414), `retire_slot/2` (:416-436), `admit_hot_region/2` (:642-656), `handle_info({:compile_timeout,...})` (:301-313), `drain` handlers (:225-231, :700-729).
**Signature:** `checkout(server, key, input) :: {:ok, Lease.t()} | {:error, term()}` (GenServer call `:infinity`); `Lease = %{pool, module, key, epoch, generation, token, owner}`.
**Data Shape:** state = 32 fixed slots (`free | compiling | ready | quarantined`, each with generation + lease_count + last_used clock), key_index, bounded skip_index (≤8×capacity), region_admissions + region_hot set (≤capacity/2), leases + monitor_index, monotonic epoch + clock.

### Decisive source
```elixir
task =
  Task.Supervisor.async_nolink(state.task_supervisor, fn ->
    Process.flag(:max_heap_size, %{
      size: max_heap_words,
      kill: true,
      error_logger: false
    })

    backend.compile(key, module, input)
  end)

timer = Process.send_after(self(), {:compile_timeout, task.ref}, state.compile_timeout)
```
```elixir
defp fetch_lease(%Lease{} = lease, caller, state) do
  with true <- lease.pool == self(),
       true <- lease.owner == caller,
       {:ok, record} <- Map.fetch(state.leases, lease.token),
       true <- record.lease == lease do
    {:ok, record}
  else
    false when lease.owner != caller -> {:error, :compiler_lease_owner_mismatch}
    _other -> {:error, :stale_compiler_lease}
  end
end
```

**Flow:** checkout miss → free slot? compile there; else evict LRU among ready slots with zero leases; retire failure QUARANTINES the slot instead of freeing; no candidate → `{:error, :compiler_pool_busy}`. Compilation runs in an async_nolink task under `max_heap_size kill:true` plus a send_after timeout that `terminate_child`s the runaway and fails all waiters with `{:compile_timeout, ms}`. Concurrent checkouts of the same key become monitored waiters on the one compiling slot and are answered with per-owner unique leases on success. Every lease is monitored; owner death releases it via DOWN without orphaning. Ready-slot eviction bumps generation; outstanding leases from older generations fail as `:stale_compiler_lease`. Drain mode rejects new work, cancels tasks, retires idle ready slots, and replies `{:error, {:compiler_pool_shutdown_timeout, leases}}` if leases don't drain in time.
**Invariant:** (1) One backend compile per key regardless of racer count — pool_test spawns 20 racers on one blocked key and asserts exactly one compile_started, one compiles[key], twenty distinct lease tokens. (2) Compiles are resource-fenced twice: heap-size kill inside the task, wall-clock timeout in the pool. (3) Only idle ready slots are evicted; a slot whose backend misbehaves is quarantined (never reused until restart) rather than silently recycled. (4) Lease identity is quadruple-checked (pool pid, owner pid, live token, exact struct match) — forged or stale leases get typed errors, not execution in someone else's slot. (5) Negative lowering results are cached but bounded (LRU skip_index), so adversarial never-compilable programs can't grow the pool unboundedly.
**Probe:** `grep -n 'region_admission_threshold 3' lib/quickbeam/vm/compiler/pool.ex` → line 20 (observed); quarantine status appears at lines 429/539/684/750 (observed).
**Probe:** `grep -c 'max_heap_size' lib/quickbeam/vm/compiler/pool.ex` → 1 (:446, observed).
**Probe (test):** pool_test.exs "joins concurrent cache misses into one supervised compilation" (:109-151) and "removes a dead single-flight waiter without creating an orphan lease" (:153+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "single flight compilation lease waiter join cache miss", limit: 5 });
```
(observed rank-1..5: pool.checkout_miss :379-396, add_waiter :475, monitor_waiter :480, remove_waiter :608, demonitor_waiter :613)

## Verdict
Adopt for any dynamic codegen/artifact cache: single-flight keyed compilation, heap+time double fencing, LRU eviction restricted to lease-free entries, quarantine on backend failure, monitor-based orphan reaping, epoch/generation stale-lease detection. Adapt capacity/slot mechanics to your runtime's module identity constraints (see compiler-contract-slot-pool-keys). Omit the region hot-set if you have no sub-unit tier. Coverage: cited path no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.

<!-- capsule-v2 -->
# lock-manager-shared-exclusive-state-machine — How do you implement Web Locks API semantics (shared/exclusive, ifAvailable, holder death) in one GenServer?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What state machine gives correct shared/exclusive grant algebra, a non-blocking ifAvailable path, and automatic release when the lock-holding process dies — across multiple JS runtimes?

## Held/pending lock state machine seam
**Path/Symbol:** `lib/quickbeam/lock_manager.ex` whole (138L): `request_lock/4` (:20-22), `release_lock/2` (:24-26), `handle_call({:request,...})` (:38-61), `handle_call({:release,...})` (:63-74), `handle_info({:DOWN,...})` (:91-112), `can_grant?/3` (:114-122), `try_grant_pending/1` (:124-138). App child at `application.ex:18`; JS bridge `locks_api.ex` (23L) + `runtime.ex:180-182` (`{:with_caller}` dispatch passes the JS runtime pid as holder).
**Signature:** `request_lock(name, mode, holder_pid, if_available \ false) :: :granted | :not_available | :holder_down` (blocking `GenServer.call(..., :infinity)`); `release_lock(name, holder_pid) :: :ok`; `query() :: %{held: [%{name, mode}], pending: [%{name, mode}]}`.
**Data Shape:** state `%{held: [%Lock{name, mode, holder, ref}], pending: [%PendingRequest{name, mode, from, holder, ref, if_available}]}` — plain lists; `ref` is the `Process.monitor(holder_pid)` ref.

### Decisive source
```elixir
def handle_call({:request, name, mode, holder_pid, if_available}, from, state) do
  ref = Process.monitor(holder_pid)

  if can_grant?(state.held, name, mode) do
    lock = %Lock{name: name, mode: mode, holder: holder_pid, ref: ref}
    {:reply, :granted, %{state | held: [lock | state.held]}}
  else
    if if_available do
      Process.demonitor(ref, [:flush])
      {:reply, :not_available, state}
    else
      pending = %PendingRequest{
        name: name, mode: mode, from: from, holder: holder_pid,
        ref: ref, if_available: false
      }
      {:noreply, %{state | pending: state.pending ++ [pending]}}
    end
  end
end

defp can_grant?(held, name, mode) do
  existing = Enum.filter(held, &(&1.name == name))

  cond do
    existing == [] -> true
    mode == "shared" -> Enum.all?(existing, &(&1.mode == "shared"))
    true -> false
  end
end

defp try_grant_pending(state) do
  {granted, still_pending} =
    Enum.reduce(state.pending, {[], []}, fn req, {granted, pending} ->
      if can_grant?(state.held ++ granted, req.name, req.mode) do
        lock = %Lock{name: req.name, mode: req.mode, holder: req.holder, ref: req.ref}
        GenServer.reply(req.from, :granted)
        {[lock | granted], pending}
      else
        {granted, [req | pending]}
      end
    end)

  %{state | held: state.held ++ granted, pending: Enum.reverse(still_pending)}
end
```

**Flow:** request → monitor the holder FIRST (so even an immediately-granted lock is covered by death recovery) → grant if `can_grant?` (empty name → yes; shared joins only all-shared; exclusive needs the name free) → otherwise ifAvailable takes the fast path: demonitor with `[:flush]` (no DOWN message to clean up) and reply `:not_available` → otherwise enqueue the GenServer `from` tuple and block (`:infinity`) → release matches on name AND holder (a process can only release its own locks), demonitors, then re-scans pending → holder DOWN releases every held lock with that ref AND cancels every pending request with that ref, replying `:holder_down` asynchronously via `GenServer.reply(req.from, ...)` before re-granting.
**Invariant:** (1) Death is the only automatic release: there are no timeouts — a live holder that never releases blocks forever by design (the JS layer's finally-block is the normal release path, see `locks-js-callback-release-contract`). (2) Every monitor created in `handle_call` is either kept (grant/pending) or flushed immediately (ifAvailable) — no orphan monitors accumulate. (3) Re-grant after any release/DOWN walks the queue in FIFO order but WITHOUT head-of-line blocking: an exclusive waiter that cannot be granted does not stop later shared waiters from being granted against `held ++ granted` — deliberate simplicity with a documented starvation caveat (an endless stream of shared requests can starve an exclusive waiter). (4) Single app-level instance means locks span runtimes: the cross-runtime test holds a lock in rt1 for 500 ms and observes rt2's ifAvailable request return `not_available`. (5) `query/0` exposes only name+mode pairs — holder pids and refs never leave the manager.
**Probe:** `grep -n 'Process.monitor\|Process.demonitor\|GenServer.reply' lib/quickbeam/lock_manager.ex` → 5 hits (:39/:46/:69/:99/:129); `grep -n 'defp can_grant?\|defp try_grant_pending' lib/quickbeam/lock_manager.ex` → 2 hits (:114/:124); key-def census ×15 executed this pass.
**Probe:** `test/web_apis/locks_test.exs` whole (129L, 9 tests): exclusive callback result, lock object name/mode, shared mode, ifAvailable→null while held, release-after-callback-completion, query snapshot held/empty, and the cross-runtime test (rt1 holds 500 ms → rt2 ifAvailable → `"not_available"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "LockManager can_grant? try_grant_pending PendingRequest DOWN holder_down", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt monitor-first-then-decide for any resource grant where the requester may die while waiting or holding: create the monitor before the branch so every path is covered, and use `demonitor(ref, [:flush])` on the no-wait path to keep the message space clean. Adopt the three-arm grant algebra (free / shared-joins-shared / exclusive-needs-free) and the single re-grant scan triggered from both release and DOWN. Adapt the no-head-of-line-blocking reduce if your port needs strict fairness — add head-of-line blocking (stop scanning at the first non-grantable request) and accept the lower throughput; keep the async `GenServer.reply` for cancelled waiters so DOWN handling never blocks on a dead caller's mailbox. Omit query exposure of internal refs as QuickBEAM does. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

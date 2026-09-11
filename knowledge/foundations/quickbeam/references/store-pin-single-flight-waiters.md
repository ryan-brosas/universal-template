<!-- capsule-v2 -->
# store-pin-single-flight-waiters — How do you coalesce concurrent first-time pins of the same identity so N racers produce ONE slot and N valid leases?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What mechanism makes concurrent first-pins of a missing key converge on one install, and who answers the waiters?

## Stored-call-waiters single-flight seam
**Path/Symbol:** `lib/quickbeam/vm/program/store.ex:reserve_missing/4` waiter branch (:248-251), `complete_install/5` waiter loop (:361-366), `handle_info({:DOWN,...})` pending-cancel branch (:221-233).
**Signature:** `pin(program, server)` — first caller gets `{:install, token, slot}`; concurrent callers get NO reply until `GenServer.reply(waiter, {:ok, waiter_lease})` (or `:unavailable`) fires from inside the server process.
**Data Shape:** `pending[key] = %{slot, token, owner, monitor, waiters: [from | ...], residency_bytes}` where each waiter is the raw GenServer `{pid, tag}` call tuple.

### Decisive source
```elixir
defp reserve_missing(key, residency_bytes, from, state) do
    case state.pending do
      %{^key => pending} ->
        pending = %{pending | waiters: [from | pending.waiters]}
        {:noreply, put_in(state.pending[key], pending)}
      # ... else grant {slot, token}, monitor owner, reply {:install, token, slot}
    end
  end

  # in complete_install/5, after granting the owner its own lease:
    entry =
      Enum.reduce(pending.waiters, entry, fn waiter, entry ->
        {waiter_lease, entry} = grant_lease(state, key, entry, waiter)
        GenServer.reply(waiter, {:ok, waiter_lease})
        entry
      end)
```

**Flow:** first pin of a missing key creates the pending entry and does the persistence work itself → every concurrent pin of the same key is parked as a stored `from` tuple (no reply yet) → on commit, the server grants the owner a lease, then loops waiters granting each a lease and replying directly → if the owner DIES mid-install, the DOWN handler erases the persisted slot and replies `:unavailable` to every waiter.
**Invariant:** (1) At most one pending entry per key — admission is serialized by the GenServer mailbox, no locks. (2) Every waiter is answered exactly once across complete / cancel / owner-DOWN. (3) Owner death cancels the WHOLE install (durable erase + all waiters `:unavailable`) — a dead installer never leaves a half-installed slot. Contrast with `compiler-pool-single-flight-lease`: same contract, different mechanism — there a Task.Supervisor task compiles and waiters are monitored pids; here the CALLER process IS the single-flight worker and waiting costs only a parked call.
**Probe:** `grep -c 'waiters' lib/quickbeam/vm/program/store.ex` → 5.
**Probe:** `test/vm/program/store_test.exs:8-24` "coalesces concurrent first pin admission by program identity" — 20 concurrent `Store.pin` tasks → `length(Enum.uniq(pinned)) == 1`, then checkout/fetch/unpin all succeed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Store reserve_missing waiters single flight pin coalesce", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stored-call-tuple waiters whenever your single-flight unit is "one caller does the slow work" — it needs no supervisor, no timeout bookkeeping, and cancellation falls out of one monitor. Adapt the pending-entry shape to your artifact type; omit QuickBEAM's persistent-term medium. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte.

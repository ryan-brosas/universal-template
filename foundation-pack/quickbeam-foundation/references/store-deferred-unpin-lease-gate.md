<!-- capsule-v2 -->
# store-deferred-unpin-lease-gate — How do you retire a shared artifact while workers still hold it, without killing anyone?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What state machine lets unpin mean "retire when the last lease ends" instead of "erase now"?

## Deferred-unpin / retiring-state seam
**Path/Symbol:** `lib/quickbeam/vm/program/store.ex:handle_call({:unpin, key})` (:191-204), `handle_info({:checkin, lease})` (:206-219), `maybe_release_entry/3` (:466-473), `drop_owner_lease/2` (:444-453), `owner_lease/2` (:455-464), `grant_lease/3` + monitor-skip comment (:424-442).
**Signature:** `unpin(%Pinned{} | %Program{}, server) :: :ok | :not_pinned`; erasure is a side effect of `checkin` or owner `DOWN`, never of `unpin` itself while leases remain.
**Data Shape:** entry `%{key, slot, token, leases: %{lease_id => monitor}, unpin?: bool, residency_bytes}`; retiring = `unpin?: true` with `leases` non-empty.

### Decisive source
```elixir
def handle_call({:unpin, key}, _from, state) do
    case state.entries do
      %{^key => %{leases: leases} = entry} when map_size(leases) == 0 ->
        :persistent_term.erase(storage_key(state.name, entry.slot))
        {:reply, :ok, remove_entry(state, key, entry.slot)}

      %{^key => entry} ->
        {:reply, :ok, put_in(state.entries[key], %{entry | unpin?: true})}
      # ... else {:reply, :not_pinned, state}
    end
  end

  defp maybe_release_entry(state, key, entry) do
    if map_size(entry.leases) == 0 and entry.unpin? do
      :persistent_term.erase(storage_key(state.name, entry.slot))
      remove_entry(state, key, entry.slot)
    else
      put_in(state.entries[key], entry)
    end
  end
```

**Flow:** unpin with zero leases erases immediately → unpin with live leases sets `unpin?: true` (retiring): new `checkout` → `:unavailable`, replacement `pin` → `:retiring`, but ACTIVE leases keep fetching fine → each lease ends via `{:checkin, lease}` (fire-and-forget send from the eval process) or via owner `DOWN` (monitor) → the FIRST event that brings `leases` to 0 while `unpin?` erases the persistent term and removes the entry → afterwards `fetch(lease)` returns `{:error, :stale_lease}`.
**Invariant:** (1) Erasure happens exactly once and only when BOTH `leases == 0` AND `unpin?` — either condition alone must not erase. (2) Engine evals skip their own monitor (source comment :424-429): that process either sends `{:checkin, lease}` or dies, so a self-monitor would double-report; direct store users get a caller-from monitor so death completes deferred unpinning. (3) `checkin` never blocks evaluation — it is a plain `send`, and a dead store is a no-op (`whereis` guard). (4) Retiring is visible to the API as distinct atoms (`:retiring` vs `:unavailable`) so callers can tell "being retired" from "never pinned / full".
**Probe:** `grep -c 'unpin?' lib/quickbeam/vm/program/store.ex` → 6; `grep -n ':retiring' lib/quickbeam/vm/program/store.ex` → 2 (:42 spec, :158 reserve reply).
**Probe:** `test/vm/program/store_test.exs:28-63` "pins one immutable program under concurrent bounded leases" — unpin with 20 active leases: fetch still ok, checkout `:unavailable`, pin `:retiring`; after all checkins, `eventually(unpin == :not_pinned)` and every lease fetches `{:error, :stale_lease}`. Also :133-152 "owner death returns a lease and completes deferred unpinning".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Store unpin deferred retiring lease checkin stale_lease", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-condition release gate (`leases==0 AND unpin?`) plus distinct retiring/unavailable API atoms for any shared-artifact store with long-lived readers; adapt the checkin transport (send vs call) to your crash semantics; omit QuickBEAM's persistent-term medium. Pairs with `vm-pin-store-lease` (engine-side protocol this state machine serves). Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte.

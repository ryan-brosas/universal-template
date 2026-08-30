<!-- capsule-v2 -->
# store-install-reserve-commit-recover — How do you install a large immutable artifact into shared fixed slots without holding the server critical section during persistence, and recover from a crash mid-install?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Where does the durable write happen relative to the GenServer state machine, and what makes commit/crash recovery safe?

## Two-phase reserve→persist→commit install seam
**Path/Symbol:** `lib/quickbeam/vm/program/store.ex:reserve_missing/4` (:246-276), `install_reserved/5` (:388-401), `persist_program/5` (:490-495), `handle_call({:commit,...})` (:169-179), `handle_call({:cancel,...})` (:181-189), `recover_or_erase_install/5` (:403-411), `erase_if_owned/4` (:420-423), `persisted?/4` (:486-488), `safe_store_call/2` (:414-418).
**Signature:** `pin/2` → `{:reserve, key, residency_bytes}` → `{:install, token, slot}` → caller persists → `{:commit, key, token}` | `{:cancel, key, token}`.
**Data Shape:** pending entry `%{slot, token: make_ref(), owner: pid, monitor, waiters: [from...], residency_bytes}`; durable value `{key, token, %Program{}}` under persistent-term key `{Store, registered_name, slot}`; `safe_store_call` maps every `:exit` to `:unavailable`.

### Decisive source
```elixir
defp install_reserved(server, key, token, slot, program) do
    name = store_name(server)

    result =
      case persist_program(name, slot, key, token, program) do
        :ok -> safe_store_call(server, {:commit, key, token})
        :error -> safe_store_call(server, {:cancel, key, token})
      end

    case result do
      :unavailable -> recover_or_erase_install(server, name, slot, key, token)
      installed -> installed
    end
  end

def handle_call({:commit, key, token}, {owner, _tag}, state) do
    case state.pending do
      %{^key => %{owner: ^owner, token: ^token} = pending} ->
        if persisted?(state.name, pending.slot, key, token),
          do: complete_install(key, token, owner, pending, state),
          else: cancel_install(key, pending, state)
```

**Flow:** reserve grants `{slot, token}`, monitors the owner process, and replies `{:install, token, slot}` → the CALLER writes the persistent term outside any server critical section → `:commit` re-checks `persisted?` against DURABLE storage (not in-memory state) before `complete_install` → if the store died between persist and commit, `safe_store_call` catches `:exit` → `recover_or_erase_install`: if the restarted store restored the slot, `{:checkout_existing, key}` returns a fresh lease; otherwise `erase_if_owned` erases ONLY when the exact `{key, token}` is still persisted.
**Invariant:** (1) No persistence inside `handle_call` — the critical section only mutates in-memory maps; the slow write is owned by the caller. (2) Commit trusts durable storage over memory (`persisted?` gate) — a lost commit reply cannot double-install. (3) Erasure requires proof of exact-token ownership — never erase a slot re-pinned to another program. (4) Every path answers every waiter exactly once (complete / cancel / DOWN).
**Probe:** `grep -n 'recover_or_erase_install' lib/quickbeam/vm/program/store.ex` → 2 hits (:398 call site, :403 def).
**Probe:** `test/vm/program/store_test.exs:66-79` "restores fixed persistent slots after the store restarts" (kill the store, supervisor restarts it, checkout/fetch of the same pinned program still works).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Store reserve commit cancel persist_program recover_or_erase_install", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase pattern for any bounded shared-artifact store: reserve state in the server, persist outside the critical section, commit against a durable re-check, and make crash recovery = "adopt if restored, erase only if still owned". Adapt slot/token shapes and the persistent-term medium to your host; omit QuickBEAM's specific Program struct. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte.

<!-- capsule-v2 -->
# store-restore-namespaced-slots — How do you restart a supervised artifact store so it restores its own slots, re-verifies them, and never inherits another store's slots?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What does restart-time slot restoration check, and how is cross-store contamination impossible?

## Namespaced persistent-slot restore seam
**Path/Symbol:** `lib/quickbeam/vm/program/store.ex:init/1` (:120-139), `restore_slots/2` (:302-325), `restore_program_slot/8` (:327-347), `storage_key/2` (:506), `store_name/1` (:497-504); supervised as an app child (`lib/quickbeam/application.ex:20`).
**Signature:** `init({name, opts})` — capacity must be an integer in 1..32 or `{:stop, {:invalid_capacity, capacity}}`; then `restore_slots(name, capacity)` scans slots 0..capacity-1.
**Data Shape:** durable key `{__MODULE__, registered_name, slot}` → value `{key::binary, token::reference, %Program{}}`; restored entry starts `%{leases: %{}, unpin?: false, residency_bytes: measured}`.

### Decisive source
```elixir
defp restore_slots(name, capacity) do
    Enum.reduce(0..(capacity - 1), {%{}, %{}, 0}, fn slot, {entries, slots, residency_bytes} ->
      case :persistent_term.get(storage_key(name, slot), :missing) do
        {key, token, %Program{} = program} when is_binary(key) and is_reference(token) ->
          restore_program_slot(name, program, key, token, slot, entries, slots, residency_bytes)
        :missing ->
          {entries, slots, residency_bytes}
        _other ->
          :persistent_term.erase(storage_key(name, slot))
          {entries, slots, residency_bytes}
      end
    end)
  end

  defp restore_program_slot(name, program, key, token, slot, entries, slots, total_bytes) do
    with :ok <- Verifier.verify_identity(program),
         {:ok, program_bytes} <- program_residency(program),
         true <- program_bytes <= @maximum_program_residency_bytes,
         true <- total_bytes + program_bytes <= @maximum_total_residency_bytes do
      # ... restore entry with leases: %{}, unpin?: false
    else
      _invalid_or_oversized ->
        :persistent_term.erase(storage_key(name, slot))
        {entries, slots, total_bytes}
    end
  end
```

**Flow:** init validates capacity → for each slot index, read the namespaced persistent term → shape gate (`{binary, ref, %Program{}}`) → re-verify program identity (`Verifier.verify_identity`) → re-measure residency against per-program (32 MiB) and running-total (128 MiB) budgets → restore entry lease-free; ANY failure erases the slot and continues.
**Invariant:** (1) Namespacing by the store's REGISTERED name (`{Store, name, slot}`) makes cross-store inheritance structurally impossible — a store started under another name cannot see this store's slots. (2) Restore re-verifies identity and re-measures size — durable content is never trusted on shape alone. (3) Restoration is read-only except for erasing invalid/foreign slots; restored entries start with zero leases and `unpin?: false`, so a restarted store never resurrects "retiring" state. (4) Caveat: if capacity SHRINKS across restart, slots beyond the new capacity are simply not scanned — their persistent terms are orphaned (harmless but unreclaimed).
**Probe:** `grep -n 'defp storage_key' lib/quickbeam/vm/program/store.ex` → 1 (:506, `{__MODULE__, name, slot}`).
**Probe:** `test/vm/program/store_test.exs:66-79` "restores fixed persistent slots after the store restarts" (kill + supervisor restart → same pinned program still checkouts/fetches); :185-205 "persistent slots are namespaced by the store's registered name" (OtherStore with capacity 1 sees none of the default store's slots and rejects its own second pin independently).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Store restore_slots verify_identity storage_key namespaced persistent term", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt namespaced durable keys + shape-gate + re-verify + re-measure at restore time for any supervised bounded-artifact store; keep retirement state non-restorable; adapt the medium (persistent_term here) and budget numbers; omit QuickBEAM's Program-specific verification. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte.

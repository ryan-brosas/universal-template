<!-- capsule-v2 -->
# store-residency-budget-no-eviction — How do you bound the total decoded-artifact memory of a fixed-slot store, including installs still in flight?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Which limits gate admission, and how do concurrent in-flight installs fail to overshoot the total budget?

## Three-tier residency budget seam
**Path/Symbol:** `lib/quickbeam/vm/program/store.ex:pin/2` guards (:46-71), `program_residency/1` (:286-290), `residency_available?/2` (:292-300), `free_slot/1` (:278-284), `remove_entry/3` (:475-484); limit attrs :24-28.
**Signature:** `pin(%Program{pin_key, bytecode_size}, server)` → `{:ok, %Pinned{}} | :unavailable | :retiring | {:error, :program_too_large | :residency_budget}`.
**Data Shape:** three tiers — `bytecode_size <= 2 MiB` (guard clause), `:erlang.external_size(program) <= 32 MiB` per program, committed + PENDING bytes `<= 128 MiB` total; capacity 8 default / 32 max fixed slots.

### Decisive source
```elixir
@default_capacity 8
@maximum_capacity 32
@maximum_pinned_bytecode_bytes 2 * 1024 * 1024
@maximum_program_residency_bytes 32 * 1024 * 1024
@maximum_total_residency_bytes 128 * 1024 * 1024

defp program_residency(program) do
    {:ok, :erlang.external_size(program)}
  rescue
    _exception -> :error
  end

  defp residency_available?(state, residency_bytes) do
    pending_bytes =
      Enum.reduce(state.pending, 0, fn {_key, pending}, total ->
        total + pending.residency_bytes
      end)

    state.residency_bytes + pending_bytes + residency_bytes <=
      @maximum_total_residency_bytes
  end
```

**Flow:** pin first checks the serialized-bytecode guard (≤2 MiB) → measures decoded residency with `external_size` (a rescue to `:error` means UNMEASURABLE programs are rejected as `:program_too_large`, not admitted) → per-program cap (32 MiB) → `reserve_missing` checks a free slot AND that committed+pending+new ≤ 128 MiB BEFORE granting the slot → exhaustion is a normal typed error (`:unavailable` for no slot, `{:error, :residency_budget}` for money); fixed slots are NEVER evicted implicitly.
**Invariant:** (1) Pending bytes count against the total budget at RESERVE time — N concurrent installs cannot collectively overshoot 128 MiB. (2) `residency_bytes` is decremented exactly once, in `remove_entry`, and pending bytes vanish with the pending entry on complete/cancel/DOWN — the ledger can never drift negative or leak. (3) Admission order is slot-first-then-budget in the `{free_slot, residency_available?}` tuple, so "no slot" reports `:unavailable` even when budget remains. (4) The measurement itself is part of the contract: anything whose external size cannot be computed is refused.
**Probe:** `grep -n '@maximum_pinned_bytecode_bytes\|@maximum_program_residency_bytes\|@maximum_total_residency_bytes\|@default_capacity\|@maximum_capacity' lib/quickbeam/vm/program/store.ex` → 10 hits (attrs :24-28 + use sites).
**Probe:** `test/vm/program/store_test.exs:82-110` — three rejection tests: bytecode 2 MiB+1 → `:program_too_large`; root 33 MiB → `:program_too_large`; four 27 MiB programs pinned then a fifth → `{:error, :residency_budget}`; :112-130 "rejects a ninth pinned program without evicting fixed slots" → `:unavailable`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Store residency_available? external_size total budget pending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier ladder (serialized size / per-artifact decoded size / total incl. in-flight) with reserve-time accounting for any bounded shared-artifact store; keep exhaustion as typed errors, never implicit eviction; adapt the four constants to your memory budget; omit QuickBEAM's Program struct. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte.

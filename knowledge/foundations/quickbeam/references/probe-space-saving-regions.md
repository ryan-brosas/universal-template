<!-- capsule-v2 -->
# probe-space-saving-regions — How do you find hot instruction regions of an interpreted program without unbounded state or atom creation?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What sampling and eviction scheme keeps "which {function, pc-window} pairs are hot" bounded at 64 integer keys while still giving an honest error bound on the dropped counts?

## Space-Saving heavy-hitter seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/region/probe.ex` whole (101L): consts (:14-16), `new/0` (:30-31), `observe/2` (:35-54), `snapshot/1` (:58-82), `increment/2` (:84-100). Wiring: `compiler.ex:start/2` (:92) creates the probe ONLY when the caller opts in with `:compiler_region_probe => true`; region admission events (`:region_attempts` :274, `:region_cold` :309, `:region_hot` :312, `:region_compiled` :363) are counted separately by `Counter`; the probe itself is pure diagnostics.
**Signature:** `new() :: %Probe{owner: pid(), sample_counter: term(), entries: map()}`; `observe(State.t(), Frame.t()) :: State.t()`; `snapshot(State.t()) :: map() | nil`.
**Data Shape:** one 1-slot `:counters` sampling clock; entries keyed `{function_id, window_start_pc}` where `window_start_pc = div(pc, 64) * 64` — INTEGER keys only; each entry `%{samples: pos_integer(), error: non_neg_integer()}`; hard cap 64 entries.

### Decisive source
```elixir
@sample_interval 16
@window_size 64
@max_entries 64

def observe(
      %State{compiler_context: %{region_probe: %__MODULE__{owner: owner} = probe} = context} =
        execution,
      %Frame{function: %{id: function_id}, pc: pc}
    )
    when owner == self() and is_integer(function_id) and function_id >= 0 and is_integer(pc) and
           pc >= 0 do
  :counters.add(probe.sample_counter, 1, 1)
  count = :counters.get(probe.sample_counter, 1)

  if rem(count, @sample_interval) == 0 do
    key = {function_id, div(pc, @window_size) * @window_size}
    probe = %{probe | entries: increment(probe.entries, key)}
    %{execution | compiler_context: %{context | region_probe: probe}}
  else
    execution
  end
end

defp increment(entries, key) do
  case Map.fetch(entries, key) do
    {:ok, entry} ->
      Map.put(entries, key, %{entry | samples: entry.samples + 1})

    :error when map_size(entries) < @max_entries ->
      Map.put(entries, key, %{samples: 1, error: 0})

    :error ->
      {victim, entry} =
        Enum.min_by(entries, fn {candidate, value} -> {value.samples, candidate} end)

      entries
      |> Map.delete(victim)
      |> Map.put(key, %{samples: entry.samples + 1, error: entry.samples})
  end
end
```

**Flow:** every observed frame bumps the lock-free sample clock (cheap, no allocation) → only every 16th observation touches the entry map → the pc is bucketed into a 64-wide window so a hot loop produces ONE key per function region → on insertion into a full table the MINIMUM-samples entry is evicted and its entire count is added to the newcomer as its `error` — the classic Space-Saving guarantee that each reported count is within `error` of the true count → `snapshot/1` sorts by `{-samples, function_id, entry_pc}` (deterministic tie-breaks) and reports `sample_interval`, `window_size`, `total_samples` metadata alongside the regions.
**Invariant:** (1) Boundedness is structural: 64 entries × fixed-size maps + one counter slot — memory cannot grow with program size or run length. (2) No atoms are ever created from program data: keys are `{integer, integer}`, so an adversarial program cannot grow the atom table through diagnostics (same discipline as the fixed Slot00..Slot31 pool in `compiler-contract-slot-pool-keys`). (3) The error field is CARRIED, not reset: when the evicted victim's count merges into the newcomer, the newcomer inherits `error = victim.samples`, preserving the heavy-hitter error bound across evictions. (4) Owner-locality mirrors the counter capsule: foreign-process `observe`/`snapshot` fall to no-op/nil clauses. (5) The probe is opt-in and never changes VM semantics — it observes canonical frames after the fact.
**Probe:** `grep -n '@sample_interval\|@window_size\|@max_entries' lib/quickbeam/vm/compiler/region/probe.ex` → 3 hits (:14-16); `grep -n 'def new\|def observe\|def snapshot\|defp increment' lib/quickbeam/vm/compiler/region/probe.ex` → 4 hits (:30/:35/:58/:84).
**Probe:** `test/vm/compiler/region/probe_test.exs:15-37` — "samples fixed-capacity integer regions in the evaluation owner": 65 distinct regions × 16 samples each → snapshot has exactly 64 regions (one evicted), `total_samples == 65`, all keys all-integer, and a foreign-process `Task.async` snapshot returns `nil`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Probe observe sample_interval window_size increment Space-Saving", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part scheme for any hot-region/hot-path diagnostic over untrusted input: (a) a lock-free sampling clock so the common path allocates nothing, (b) integer-only bucketed keys so program data can never create atoms or unbounded map keys, (c) Space-Saving eviction with carried error so the cap is honest rather than lossy-by-silence; adopt the deterministic sort tie-breaks for stable snapshots; adapt the 16/64/64 constants to your diagnostic budget; omit QuickBEAM's opt-in flag if your measurement plane is always-on. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

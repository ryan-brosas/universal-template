<!-- capsule-v2 -->
# counter-owner-local-otp-counters — How do you measure a compiled-execution tier without adding cross-process contention or per-op map updates?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Where do compiler measurement counters live, who may write them, and how does one deoptimization event become three consistent counter updates?

## Owner-local fixed-key :counters seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/counter.ex` whole (158L): `@indexes` (:17-37, 19 fixed events), offset attrs (:39-42), `new/0` (:52-53), `increment/2` (:57-68), `add_generated_steps/2` (:72-83), `interpreted_opcode/2` (:87-98), `deopt/3` (:102-108), `snapshot/1` (:111-124), `opcode_counts/2` (:144-149), `deopt_event/1` (:152-157). Wiring: `compiler.ex:start/2` (:91-104) creates the set only when `execution.measurement_target` is set; `runtime/interpreter.ex:execute_current/2` (:339-357) calls `Optimization.observe` + `Optimization.interpreted_opcode` per opcode ONLY when the instrumentation slot is non-nil; `runtime/optimization.ex:instrument/4` (:67-76) is the dynamic dispatch; `runtime.ex:288` folds `Optimization.snapshot(execution)` into the endpoint measurement message.
**Signature:** `new() :: %Counter{owner: pid(), reference: term()}`; `increment(State.t(), atom()) :: State.t()`; `snapshot(State.t()) :: map() | nil`.
**Data Shape:** ONE `:counters.new(531, [])` allocation per evaluation: 19 named event slots + 256 deopt-opcode histogram slots + 256 interpreted-opcode histogram slots (offsets at :39-42). The struct rides in `State.compiler_context.counters`; the owner pid is captured at creation.

### Decisive source
```elixir
def new,
    do: %__MODULE__{owner: self(), reference: :counters.new(@counter_count, [])}

def increment(
      %State{
        compiler_context: %{counters: %__MODULE__{owner: owner, reference: reference}}
      } = execution,
      event
    )
    when owner == self() and event in @events do
  :counters.add(reference, Map.fetch!(@indexes, event), 1)
  execution
end

def increment(%State{} = execution, _event), do: execution

def deopt(%State{} = execution, reason, %Frame{} = frame) do
  execution
  |> increment(:deoptimizations)
  |> increment(deopt_event(reason))
  |> increment_deopt_opcode(frame)
end

defp deopt_event({:guard_failed, _guard}), do: :guard_failed_deopts
defp deopt_event(_reason), do: :unsupported_semantics_deopts
```

**Flow:** `Compiler.start/2` → counters created iff the caller passed a measurement target → every interpreter opcode pays at most two bounded map checks plus (when enabled) `Optimization.observe` + `Optimization.interpreted_opcode` → compiler-tier events (`:frame_attempts`, `:generated_entries`, `:region_attempts/cold/hot/compiled`, `:reentries`) are incremented directly by `compiler.ex`/`interpreter.ex` → each validated deopt fans out through `Counter.deopt/3` into total + reason-specific + deopt-opcode-at-frame.pc → at evaluation completion `Optimization.snapshot` reads all 531 slots into a fixed-key map, name-maps both opcode histograms through `Opcode.table()`, DROPS zero entries (sparse output), and attaches the profile tag.
**Invariant:** (1) Owner-locality is enforced by GUARD, not by documentation: any call from another process falls to the no-op clause (`increment` returns execution unchanged, `snapshot` returns `nil`) — a stolen or leaked State can never corrupt or read the counters. (2) Counters are written with lock-free OTP `:counters` and read exactly once, at the measurement boundary — there is no periodic flush, no shared ETS, no cross-process write path. (3) One deopt = three consistent increments chained through the same execution value; the reason taxonomy is CLOSED (the five `deopt_event` clauses cover the full validated-reason set from `compiler-deopt-validated-boundary`, with an unknown-reason fold into `:unsupported_semantics_deopts`). (4) Opcode histograms are indexed by raw integer opcode (0..255) at write time and only converted to names at snapshot — hot-path writes never touch atoms or maps.
**Probe:** `grep -n '@opcode_slots\|@deopt_opcode_offset\|@interpreted_opcode_offset\|@counter_count' lib/quickbeam/vm/compiler/counter.ex` → 4 hits (:39-42); `grep -n 'def new\|def increment\|def add_generated_steps\|def interpreted_opcode\|def deopt\|def snapshot' lib/quickbeam/vm/compiler/counter.ex` → 6 public defs.
**Probe:** `test/vm/compiler/counter_test.exs:11-34` — "keeps fixed OTP counters in the evaluation owner": owner increments `:frame_attempts` once; a `Task.async` from a FOREIGN process increments the same State and snapshots it → foreign result is `nil`, owner's count stays exactly 1, and `deopt_opcodes` is empty (map_size 0).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Counter increment owner snapshot deopt_event opcode_counts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the owner-pid-in-guard pattern for any per-evaluation measurement state: make foreign access a silent no-op (write) / nil (read) instead of an error, so measurement can never break the measured program; adopt fixed-index `:counters` with integer-keyed histograms written raw and name-mapped only at snapshot; adopt the fan-out helper (one semantic event → N counter increments chained over the same state); adapt the 19-event taxonomy to your tier's action set; omit QuickBEAM's instrumentation-module indirection if your interpreter can call the counter module directly. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

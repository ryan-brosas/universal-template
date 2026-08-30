<!-- capsule-v2 -->
# measurement-channel-side-message — How do you report deterministic resource metrics alongside an evaluation result without coupling the interpreter to a metrics backend?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do deterministic counters (steps, logical bytes) and endpoint process observations (heap words, reductions) reach the caller when the evaluation may run in a different process than the result?

## measurement_target side-channel seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/state.ex:31` (`measurement_target: nil` field, type `{pid(), reference()} | nil` :81); `lib/quickbeam/vm/runtime/interpreter.ex:79` (seeded from opts); `lib/quickbeam/vm/runtime.ex` `measured/2` (:249-259), `finish_final/1` (:261-268), `report_measurement/1` (:276-294), `process_stat/1` (:296-300); `lib/quickbeam/vm/compiler.ex` `eval_with_metrics/2` (:73-82, same protocol for the compiled tier); `lib/quickbeam/vm/runtime/engine.ex` `measure_request/3` (:103-147, wall clock) + `measurement/1` (:376-389, struct assembly); `lib/quickbeam/vm/measurement.ex` (public struct) vs `lib/quickbeam/vm/runtime/engine/measurement.ex` (internal struct with compiler fields).
**Signature:** `measured(fun, opts) :: {Interpreter.result(), map() | nil}`; `report_measurement(%State{}) :: :ok`.
**Data Shape:** `State.measurement_target = {pid, ref} | nil`; message `{:quickbeam_vm_measurement, ref, %{steps, logical_memory_bytes, process_memory_bytes, reductions} ++ compiler snapshots}`; public `%Measurement{result, wall_time_us, steps, logical_memory_bytes, process_memory_bytes, reductions}` (compiler fields stripped).

### Decisive source
```elixir
defp measured(fun, opts) do
  ref = make_ref()
  result = fun.(Keyword.put(opts, :measurement_target, {self(), ref}))

  receive do
    {:quickbeam_vm_measurement, ^ref, metrics} -> {result, metrics}
  after
    0 -> {result, nil}
  end
end

defp finish_final({status, _value, %State{} = execution} = result)
     when status in [:ok, :error] do
  Async.cancel_operations(execution)
  finished = Interpreter.finish(result)
  report_measurement(execution)
  finished
end

defp report_measurement(%State{measurement_target: nil}), do: :ok

defp report_measurement(%State{measurement_target: {pid, ref}} = execution) do
  process_memory = process_stat(:memory)
  reductions = process_stat(:reductions)

  metrics =
    Map.merge(
      %{
        steps: execution.step_limit - execution.remaining_steps,
        logical_memory_bytes: execution.memory_used,
        process_memory_bytes: process_memory,
        reductions: reductions
      },
      Optimization.snapshot(execution)
    )

  send(pid, {:quickbeam_vm_measurement, ref, metrics})
  :ok
end
```

**Flow:** the metrics caller injects `measurement_target: {self(), ref}` into the ordinary eval options — the interpreter treats it as plain state, zero coupling → the evaluation runs to completion (including async drives) in whatever process owns it → at finish, AFTER `Async.cancel_operations` (handlers killed first so their work cannot pollute the numbers) and AFTER `Interpreter.finish` (result conversion included), `report_measurement` merges deterministic counters (`step_limit - remaining_steps`, `memory_used`) with endpoint `Process.info` observations (memory, reductions) and compiler counter/region snapshots, then `send`s the message → the caller's `receive` with `after 0` degrades gracefully: no message means metrics are simply `nil`, never a hang → engine.ex wraps the whole isolated request in `System.monotonic_time` for `wall_time_us` and folds `{result, metrics}` into the `%Measurement{}` struct; the public facade rebuilds it via `public_measurement/1` (a plain `struct/2` copy) which DROPS the compiler-only fields.
**Invariant:** (1) the interpreter never knows about metrics backends — it only carries a `{pid, ref}` in state and fires one message; (2) metrics are reported exactly once, at finish, after side-effect cancellation and result conversion; (3) the channel is best-effort — a lost message yields `{result, nil}`, not an error; (4) `steps` and `logical_memory_bytes` are deterministic (same program → same values, pinned by test), while `process_memory_bytes`, `reductions`, and `wall_time_us` are explicitly endpoint observations; (5) the ref correlation means a stale or forged measurement message cannot be mistaken for the current one.
**Probe:** `test/vm/measurement_test.exs` :6-21 (determinism: two `measure` runs of the same program give identical `steps` and `logical_memory_bytes`); :35-44 (resource rejection retains final counters — `while(true){}` at `max_steps: 100` reports `steps == 100`); :46-69 (outer timeout reports `steps == nil` because the worker died before reporting, and the outstanding handler is terminated); `test/vm/compiler/profile/pure_test.exs` :309-340 (`Engine.measure` parity across `engine: :interpreter` and `engine: :compiler`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "measurement_target report_measurement quickbeam_vm_measurement measured process_stat eval_with_metrics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the side-message measurement channel: inject a `{pid, ref}` target into evaluation state, report once at finish via plain `send`, receive with `after 0` — it adds metrics to any interpreter with zero backend coupling and graceful degradation. Adopt the deterministic-vs-endpoint split (counters from VM accounting, heap/reductions from `Process.info` at the endpoint) so benchmarks do not mistake scheduler noise for VM cost. Adapt the metric set and the cancel-before-report ordering to your runtime. Omit the compiler snapshot merge (`Optimization.snapshot`) if you have no instrumented compiled tier. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); Retrieve block is a documented live-call template, not an executed call.

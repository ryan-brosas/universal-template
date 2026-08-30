<!-- capsule-v2 -->
# vm-isolation-spawn-opt — How do you sandbox untrusted evaluations with process-level kill switches?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How are timeout and memory overruns converted into clean error tuples when the evaluator itself is a BEAM process?

## spawn_opt worker containment seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/engine.ex:eval_isolated_program/2` (:282-289), `worker_spawn_options/1` (:391-401), `await_evaluation/5` (:403-429), `evaluation_exit/2` (:431-435).
**Signature:** `:erlang.spawn_opt(fun, [:monitor, {:max_heap_size, %{size: words, kill: true, error_logger: false}}])`; defaults timeout 5000 ms, memory_limit 64 MiB, `@worker_heap_overhead 4 MiB`.
**Data Shape:** Worker sends `{reply_ref, result}`; parent monitors; three exit classes mapped to errors.

### Decisive source
```elixir
worker = fn -> send(caller, {reply_ref, safe_evaluate(program, options)}) end
{pid, monitor_ref} = :erlang.spawn_opt(worker, worker_spawn_options(options.memory_limit))
await_evaluation(pid, monitor_ref, reply_ref, options.timeout, options.memory_limit)

defp worker_spawn_options(memory_limit) do
  word_size = :erlang.system_info(:wordsize)
  max_heap_words = div(memory_limit + @worker_heap_overhead + word_size - 1, word_size)
  [:monitor, {:max_heap_size, %{size: max_heap_words, kill: true, error_logger: false}}]
end

after timeout -> Process.exit(pid, :kill); await_down(...); flush_reply(...);
               {:error, {:limit_exceeded, :timeout, timeout}}
{:DOWN, ..., :killed} when is_integer(memory_limit) ->
               {:error, {:limit_exceeded, :memory_bytes, memory_limit}}
```

**Flow:** every eval/call runs in a THROWAWAY monitored process → heap ceiling derived from the logical memory_limit (+4 MiB overhead, rounded up to words) with kill:true → overrun ⇒ VM kills worker ⇒ DOWN(:killed) maps to `{:limit_exceeded, :memory_bytes, n}` → wall-clock overrun ⇒ explicit kill + DOWN drain + reply flush + timeout error → normal completion demonitors.
**Invariant:** (1) The JS-visible "memory limit" becomes a PROCESS heap limit — that's what makes it un-interceptable: test pins that `try/catch` in JS cannot catch it (`memory limits cannot be intercepted by JavaScript catch handlers`). (2) After timeout-kill you MUST drain the late DOWN and flush any racing reply or they leak into the next receive in this process. (3) safe_evaluate also converts internal `{:suspended,_}` into `{:error, {:unsupported, :async_wait}}` — isolation mode forbids cross-process async continuation. (4) `isolation: :caller` skips all of this (trusted diagnostics only).
**Probe:** `grep -c 'max_heap_size' lib/quickbeam/vm/runtime/engine.ex` → 1.
**Probe:** `grep -c 'kill: true' lib/quickbeam/vm/runtime/engine.ex` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "max_heap_size spawn_opt kill evaluation", limit: 10 });
```

## Verdict
Adopt throwaway-process containment with heap-derived kill ceilings for any interpreter loop; adapt the overhead constant and exit-class mapping; keep the post-timeout mailbox drains — they prevent cross-request message bleed. Coverage: engine.ex no_recorded_issue+metadata_match; direct tests test/vm/memory_limit_test.exs execute both isolation modes at the pin.

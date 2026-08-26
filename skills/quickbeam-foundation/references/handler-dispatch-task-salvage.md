<!-- capsule-v2 -->
# handler-dispatch-task-salvage — How do JS→host callbacks run without blocking or crashing the runtime?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the dispatch ladder for a `Beam.call` handler message, and what guarantees the JS promise always settles?

## beam_call Task-dispatch seam
**Path/Symbol:** `lib/quickbeam/runtime.ex:handle_info({:beam_call, call_id, handler_name, args})` (:605-635); special-cased `__process_monitor/__process_demonitor` (:591-603); Context twin at `lib/quickbeam/context.ex:handle_info` (:323-385).
**Signature:** handler values are one of: plain `(args -> term)`, `{:with_caller, (args, caller_pid -> term)}`, `{:context_worker, action}`; resolution via `Native.resolve_call_term(resource, call_id, result)` / rejection via `Native.reject_call_term(resource, call_id, msg)`.
**Data Shape:** Message `{call_id, handler_name, args}` where call_id correlates the pending JS promise; args arrive as list-or-raw and are normalized with `if is_list(args), do: args, else: [args]`.

### Decisive source
```elixir
case Map.get(handlers, handler_name) do
  nil ->
    QuickBEAM.Native.reject_call_term(resource, call_id, "Unknown handler: #{handler_name}")
  handler ->
    Task.start(fn ->
      try do
        args = if is_list(args), do: args, else: [args]
        result = case handler do
          {:with_caller, fun} -> fun.(args, caller)
          fun -> fun.(args)
        end
        QuickBEAM.Native.resolve_call_term(resource, call_id, result)
      rescue
        e -> QuickBEAM.Native.reject_call_term(resource, call_id, Exception.message(e))
      end
    end)
end
{:noreply, state}
```

**Flow:** native emits {:beam_call,...} → lookup → missing handler ⇒ immediate reject (JS gets Error, never hangs) → present handler ⇒ unlinked Task runs it → return value resolves the promise; raised exception rejects with its message.
**Invariant:** (1) EVERY path terminates in exactly one resolve/reject — a porter who forgets the rescue clause leaves JS promises pending forever. (2) Tasks are deliberately UNLINKED: a handler crash must not take down the runtime GenServer. (3) `{:with_caller, fun}` exists because several APIs (spawn, ws connect, locks request) need the CALLER's pid (the runtime) to register monitors/links — passing self() inside the Task would be wrong. (4) The Context twin adds two extra arms (`{:context_worker, action}` for Worker emulation) but keeps identical resolve/rescue discipline. (5) terminate-time drain (`drain_beam_calls/2`) reuses the same handle_beam_call_sync body synchronously so shutdown doesn't strand in-flight calls.
**Probe:** `grep -c 'resolve_call_term\\|reject_call_term' lib/quickbeam/runtime.ex` → 8.
**Probe:** `grep -c 'Task.start' lib/quickbeam/context.ex` → 4 (with_caller arm, plain arm, spawn worker, terminate worker).
**Probe:** `grep -c 'drain_beam_calls' lib/quickbeam/runtime.ex` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "beam_call handler reject unknown Task start", limit: 10 });
```

## Verdict
Adopt the total-function dispatch ladder (unknown⇒reject, run-in-task, rescue⇒reject); adapt handler tagging conventions to your host; omit process_monitor special-casing if you lack BEAM monitors. Coverage: runtime.ex/context.ex no_recorded_issue; direct tests test/core/eval_vars_test.exs + context_pool_test.exs "Unknown handler" behavior exercise both branches.

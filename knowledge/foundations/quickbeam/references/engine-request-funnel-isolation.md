<!-- capsule-v2 -->
# engine-request-funnel-isolation — How do you funnel every evaluation request through one validated path with two isolation modes and a single typed result contract?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you keep eval, call, measure, and measure_call from forking into four divergent execution paths while still validating every option before any process spawns?

## Request-normalization funnel seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/engine.ex` (452L whole): `execute/3` (:69-101), `measure_request/3` (:103-147), `evaluation_options/1` (:149-169, closed 13-key allowlist), `validate_evaluation_options/1` (:171-219), `validate_server/1` (:229-230, deliberately loose), `pinned_lease/1` (:254-259), `eval_isolated_program/2` (:282-289), `safe_evaluate/2` (:306-315), `engine_crash/1` (:373-374), `await_evaluation/5` (:403-429), `evaluation_exit/2` (:431-435).
**Signature:** `execute(Program.t() | Pinned.t(), [option()], :eval | {:call, name, args}) :: result(term())`.
**Data Shape:** `request` is stashed INTO the validated options map (`Map.put(options, :request, request)`) so downstream clauses dispatch on it; failure shapes: `{:error, :invalid_program}`, `{:error, {:invalid_options, opts}}`, `{:error, {:invalid_option, name, value}}`, `{:error, {:unknown_option, key}}`, `{:error, :pinned_program_unavailable}`, `{:error, {:limit_exceeded, :timeout | :memory_bytes, limit}}`, `{:error, {:evaluation_process_exit, reason}}`, `{:error, {:interpreter_crash | :compiler_crash, exception_or_reason, stacktrace}}`.

### Decisive source
```elixir
defp safe_evaluate(program, options) do
  case evaluate(program, options) do
    {:suspended, _continuation} -> {:error, {:unsupported, :async_wait}}
    result -> result
  end
rescue
  exception -> {:error, {engine_crash(options.engine), exception, __STACKTRACE__}}
catch
  kind, reason -> {:error, {engine_crash(options.engine), {kind, reason}, __STACKTRACE__}}
end

# Deliberately loose: the interpreter engine never touches the pool, so it
# must accept the default (or any) server name even when no pool is running.
defp validate_server(server) when is_atom(server) or is_pid(server), do: :ok

defp evaluation_exit(:killed, memory_limit) when is_integer(memory_limit),
  do: {:error, {:limit_exceeded, :memory_bytes, memory_limit}}

defp evaluation_exit(reason, _memory_limit),
  do: {:error, {:evaluation_process_exit, reason}}
```

**Flow:** eval/call/measure/measure_call normalize into `execute/3` or `measure_request/3` with the request term inside the options map → `evaluation_options/1` validates the closed 13-key allowlist (isolation, engine, compiler_pool, compiler_profile, compiler_region_probe, compiler_regions, handlers, max_stack_depth, max_steps, memory_limit, profile, timeout, vars) BEFORE any process exists → `:caller` isolation runs in-process (trusted diagnostics only); `:process` isolation spawns a throwaway monitored worker (`worker_spawn_options` derives max_heap_size from the logical memory limit) → the worker wraps evaluation in `safe_evaluate`/`safe_measure`, which convert `{:suspended, _}` into `{:error, {:unsupported, :async_wait}}` (a cross-process continuation is meaningless) and rescue/catch everything into engine-tagged crash tuples → the parent await loop maps DOWN(`:killed`) to the memory limit error, timeout to kill + DOWN drain (`await_down`) + reply flush (`flush_reply`) + typed timeout error, and any other DOWN to `{:evaluation_process_exit, reason}` → pinned programs ride the same funnel with `Store.checkout → fetch → Verifier.verify_identity` and `after Store.checkin(lease)` so crashes still release the lease.
**Invariant:** (1) every option is validated before any process spawns — a bad option can never leave a worker behind; (2) the result contract is CLOSED — callers pattern-match a fixed error-tuple vocabulary, never raw raises or exits; (3) `validate_server` is intentionally loose because the interpreter never touches the pool — liveness is enforced only on the compiler path (`Compiler.ensure_pool_available/1`); (4) after a timeout kill you must drain the late DOWN and flush any racing reply or they leak into the caller's next receive.
**Probe:** `test/vm/runtime/interpreter_test.exs` :186-192 ("terminates an evaluation process at the wall-clock deadline" — `while (true) {}` with `max_steps: 1_000_000_000, timeout: 10` → `{:error, {:limit_exceeded, :timeout, 10}}`, then a finite program still evaluates); `test/vm/measurement_test.exs` :71-76 (`max_steps: 0` → `{:error, {:invalid_option, :max_steps, 0}}` before any measurement starts); `test/vm/api_test.exs` :69-72 (`refute function_exported?(VM, :worker_spawn_options, 1)` — the containment helper is internal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "safe_evaluate engine_crash evaluation_exit await_evaluation validate_evaluation_options eval_isolated_program", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-funnel request normalization with options validated before process spawn and a closed typed error vocabulary — it is what makes four public entry points maintainable as one code path. Adopt the rescue/catch-to-typed-crash-tuple wrapper for any in-process engine invocation. Adapt the 13-key allowlist and defaults (5 s timeout, 5 M steps, 1 000 stack depth, 64 MiB memory) to your host. Keep the post-timeout DOWN drain + reply flush; keep `{:suspended,_}` → `{:unsupported, :async_wait}` if your isolation model cannot resume continuations across processes. Omit the compiler engine branches if you have no compiled tier — the funnel shape does not depend on it. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); Retrieve block is a documented live-call template, not an executed call.

<!-- capsule-v2 -->
# compiler-tier-action-algebra — How does an optional JIT tier hand control back to the interpreter without ever crashing or lying about fuel?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** What is the exact contract between the bounded BEAM compiler tier and the interpreter when a frame is compiled, cached, skipped, or deoptimized?

## Orchestrator four-action seam
**Path/Symbol:** `lib/quickbeam/vm/compiler.ex:start/2` (:86-114), `execute_frame/2` (:118-143), `cache_decision/3` (:408-415), `add_generated_steps/2` (:433-437), `resume_action/2` (:456-471), `ensure_pool_available/1` (:473-481), `safe_checkin/2` (:483-487); cap at `lib/quickbeam/vm/compiler/context.ex:21` (`max_decisions: 256`).
**Signature:** `start(Program.t(), keyword()) :: {:ok, term()} | {:error, term()} | {:suspended, term()}`; internal actions `{:deopt, %Deopt{}} | {:invoke, callable, args, this, caller, execution, false} | {:skip, frame, execution} | {:error, reason}`.
**Data Shape:** Per-function decision memo in `context.decisions` keyed by function id (or `{:region, id, pc}`): `:skip | {:cached, key} | {:compile, key, template}`.

### Decisive source
```elixir
defp cache_decision(%State{compiler_context: context} = execution, function_id, decision) do
  if map_size(context.decisions) < context.max_decisions do
    context = %{context | decisions: Map.put(context.decisions, function_id, decision)}
    %{execution | compiler_context: context}
  else
    execution                      # full memo: skip recording, allow recompute
  end
end

defp resume_action({:deopt, deopt}, _execution), do: Interpreter.resume_deopt_raw(deopt)
defp resume_action({:invoke, c, a, t, caller, ex, false}, _),
  do: Interpreter.resume_compiler_invoke(c, a, t, caller, ex)
defp resume_action({:skip, frame, execution}, _), do: Interpreter.run_frame(frame, execution)
defp resume_action({:error, reason}, execution), do: {:error, {:compiler_error, reason}, execution}
defp resume_action(action, execution),
  do: {:error, {:compiler_error, {:invalid_generated_action, action}}, execution}

defp add_generated_steps(action, before) do
  update_action_execution(action, fn execution ->
    Counter.add_generated_steps(execution, max(before - execution.remaining_steps, 0))
  end)
end

defp safe_checkin(pool, lease) do
  Pool.checkin_active(pool, lease)
catch
  :exit, _reason -> :ok
end
```

**Flow:** eval → Interpreter.initialize → program identity → per-frame: pool alive gate → decisions lookup (hit: invoke/cached/skip; miss: candidacy → artifact key → checkout_cached) → generated module runs whole blocks through the canonical Runtime ABI → action returns through `add_generated_steps` (fuel restored) and `observe_action` (counters) → `resume_action/2` re-enters the interpreter for deopt/invoke/skip; errors are wrapped as `{:compiler_error, ...}`, never raised. `invoke_lease/4` always checkins in an `after`.
**Invariant:** (1) Decision memo is owner-local and hard-capped (256); overflow silently declines to memoize rather than evicting or growing. (2) Generated code may only produce the four known actions; anything else becomes a typed error — a buggy artifact cannot crash the VM. (3) Step budgets stay meaningful across tiers: steps consumed by un-charged fast blocks are credited back as "generated" steps using a before/after remaining_steps diff clamped at ≥0. (4) Pool death and pool-checkin exits degrade to values, never exits. (5) Tier parity is a tested contract: native QuickJS, interpreter, and compiler produce identical values AND identical JSError structs (orchestration_test.exs:18-53), including stack-limit behavior and tail calls under `max_stack_depth: 2` (:120-142).
**Probe:** `grep -c 'cache_decision' lib/quickbeam/vm/compiler.ex` → 12 (observed).
**Probe:** `grep -n 'max_decisions: 256' lib/quickbeam/vm/compiler/context.ex` → line 21 (observed).
**Probe (test):** orchestration_test.exs "caps owner-local eligibility metadata across many nested functions" asserts exactly 256 decisions for a 300-function source (:108-118).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "deoptimization validated owner-local boundary interpreter transition", limit: 5 });
```
(observed rank-2: compiler.deopt.validate_owner deopt.ex:119; rank-3: pool.release_monitored_owner pool.ex:596-606)

## Verdict
Adopt the four-action algebra + typed invalid-action fallback + capped decision memo + before/after step-fuel credit for any tiered interpreter (JIT, wasm fast-path, regex fast loop). Adapt the specific counter struct and Elixir AST generation to your host. Omit region-tier machinery unless you need sub-function hot entries. Coverage: both cited lib paths no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.

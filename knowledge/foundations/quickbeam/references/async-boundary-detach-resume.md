<!-- capsule-v2 -->
# async-boundary-detach-resume — How does `await` detach a coroutine without blocking the owner process, and how is stack depth restored on resume?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you split a caller stack at the nearest async boundary so the outer frames keep running while the inner frames sleep, and how does a `max_stack_depth` limit stay correct across the split?

## Await-as-caller-stack-split seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/async.ex` (366L): `enter/8` (:56-78), `resume_coroutine/3` (:86-95), `detach_await/3` (:97-104), `detach_immediate/3` (:106-112), `suspend_promise/3` (:114-127), `suspend_microtask/3` (:129-134), `detach/3` (:285-301), `deliver/2` clauses (:303-320). Interpreter entry: `interpreter.ex:171-172` (`resume_coroutine` → `execute_async`). Boundary struct: `%Boundary.Async{promise, caller, depth, mode}`.
**Signature:** `detach_await(Frame.t(), State.t(), PromiseReference.t()) :: {:ok, result()} | :no_async_boundary`; `resume_coroutine(Coroutine.t(), {:ok, term()} | {:error, term()}, State.t()) :: result()`.
**Data Shape:** `%Coroutine{frame, callers, boundary}` — `callers` holds the INNER frames only; the boundary is rewritten `%{boundary | caller: nil, depth: 0, mode: :detached}` inside the coroutine. `mode` is classified in `enter/8` from the caller term: `%Boundary.Reaction{}` → `:reaction`, `%Boundary.PromiseExecutor{}` → `:executor`, `%Boundary.Thenable{}` → `:thenable`, `tail?` → `:return`, else `:push`.

### Decisive source
```elixir
defp detach(resume_frame, execution, enqueue_resume) do
  case Enum.split_while(execution.callers, &(!match?(%Boundary.Async{}, &1))) do
    {inner_callers, [%Boundary.Async{} = boundary | outer_callers]} ->
      coroutine = %Coroutine{
        frame: resume_frame,
        callers: inner_callers,
        boundary: %{boundary | caller: nil, depth: 0, mode: :detached}
      }

      execution = %{execution | callers: outer_callers, depth: boundary.depth}
      execution = enqueue_resume.(execution, coroutine)
      {:ok, deliver(boundary, execution)}

    {_callers, []} ->
      :no_async_boundary
  end
end

def resume_coroutine(%Coroutine{} = coroutine, result, %State{} = execution) do
  callers = coroutine.callers ++ [coroutine.boundary]
  frame_depth = Enum.count(coroutine.callers, &match?(%Frame{}, &1))
  execution = %{execution | callers: callers, depth: coroutine.boundary.depth + frame_depth + 1}
  ...
end
```

**Flow:** `await` → `detach_await` splits `execution.callers` at the FIRST (nearest) `%Boundary.Async{}` → inner frames + rewritten boundary become a `%Coroutine{}` registered as a waiter on the awaited promise → outer stack stays in `execution.callers` and `execution.depth` rewinds to `boundary.depth` (the depth BEFORE the async function was entered) → `deliver/2` returns the action that hands the async function's own promise to its caller (`{:complete, promise, caller, ...}` for `:push`, `{:return, promise}` for tail, `complete_reaction` for `:reaction`, `:idle` for `:thenable`/`:detached`) → on settlement, `resume_coroutine/3` rebuilds `callers = coroutine.callers ++ [boundary]` and recomputes `depth = boundary.depth + frame_count + 1`. No boundary anywhere → `:no_async_boundary` → legacy `suspend_promise`/`suspend_microtask` `Continuation` path.
**Invariant:** depth accounting must round-trip exactly — the coroutine carries the boundary's ORIGINAL entry depth, so a detached reaction running under `max_stack_depth: 1` never trips the limit while the outer evaluation is live, and resume restores the same depth the frames had before detach. The async function's promise is created BEFORE its frame runs (`enter/8`), so the caller always has something to hold.
**Probe:** `test/vm/runtime/async_semantics_test.exs` (100L) — unit-level: `enter` yields `mode: :push`, `depth == 2`; `detach_await` yields `execution.callers == []`, `depth == 1`, exactly one coroutine waiter on the awaited promise. `test/vm/runtime/promise_test.exs` — `"abc"` nested-detach ordering (:128-143), "releases caller depth before detached reactions run" with `max_stack_depth: 1` (:183-186), "preserves deterministic limits across detached continuations" (steps limit still fires :188-194).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "detach_await resume_coroutine Boundary.Async Coroutine depth", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt await-as-stack-split: detach by splitting an explicit caller list at the nearest boundary record, park the inner half as a plain data coroutine, rewind depth to the boundary's entry depth, and recompute depth from the coroutine on resume. Adapt the boundary classification (mode from caller term) to your boundary taxonomy; the deliver/mode table is QuickBEAM-specific plumbing. Omit the legacy Continuation path if your host always has boundaries. Caveat: `resume_coroutine` counts only `%Frame{}` entries for depth — native frames in `callers` would under-count. Direct-read fallback: whole-file async.ex read + both test files whole + probe census (def ×30, detach/deliver clause sites re-grepped); no graph coverage check in-session.

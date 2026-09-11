<!-- capsule-v2 -->
# continuation-legacy-suspend-resume — How do you park a suspended legacy await as data, wait on a raw message, and resume it without re-entering the interpreter loop?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source+test read fallback). **Question:** When an `await` has no async boundary to detach from, what exact record do you hand the host, and what does the host's resume loop look like?

## Legacy continuation record + host receive-loop seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/continuation.ex` (12L whole); `lib/quickbeam/vm/runtime/async.ex` `suspend_promise/3` (:114-127) + `suspend_microtask/3` (:129-134); `lib/quickbeam/vm/runtime/interpreter.ex` `resume/2` (:133-135) + `resume_raw/2` (:161-168); `lib/quickbeam/vm/runtime.ex` `drive_with({:suspended, ...})` (:85-87) + `await_legacy_promise/2` (:211-236); frame record `lib/quickbeam/vm/runtime/frame.ex` (34L whole, `compiler_allow_reentry`/`compiler_entered`/`compiler_reentry_after_instruction` flags :13-15 consumed by `interpreter.ex resume_deopt_raw/1` :145-159).
**Signature:** `suspend_promise(Frame.t(), State.t(), PromiseReference.t()) :: result()`; `resume(Continuation.t(), {:ok, term()} | {:error, term()}) :: result()`.
**Data Shape:** `%Continuation{frame, execution, awaiting}` — `awaiting` is a `%PromiseReference{}` (host must wait for a `{:quickbeam_vm_host_reply, operation, result}` message) or the atom `:microtask` (the result is already queued in `execution.jobs`; just keep driving). The struct carries the WHOLE execution state, unlike `%Coroutine{}` which carries only inner frames.

### Decisive source
```elixir
# async.ex — the only two constructors of the legacy record
def suspend_promise(resume_frame, execution, promise) do
  case Promise.state(execution, promise) do
    :pending ->
      {:suspended, %Continuation{frame: resume_frame, execution: execution, awaiting: promise}}
    {:fulfilled, value} -> suspend_microtask(resume_frame, execution, {:ok, value})
    {:rejected, reason} -> suspend_microtask(resume_frame, execution, {:error, reason})
  end
end

# runtime.ex — the host-side wait loop
defp await_legacy_promise(%Continuation{} = continuation, finish) do
  receive do
    {:quickbeam_vm_host_reply, operation, result} ->
      case Async.settle_host_reply(continuation.execution, operation, result) do
        {:ok, execution} ->
          continuation = %{continuation | execution: execution}
          if Promise.state(execution, continuation.awaiting) == :pending do
            await_legacy_promise(continuation, finish)
          else
            result = settled_result(continuation.awaiting, execution)
            execution = %{execution | jobs: :queue.in(result, execution.jobs)}
            drive_with({:suspended, %{continuation | execution: execution, awaiting: :microtask}}, finish)
          end
        :stale -> await_legacy_promise(continuation, finish)
      end
  end
end

# interpreter.ex — resume pushes the value and keeps the SAME execution state
def resume_raw(%Continuation{} = continuation, {:ok, value}) do
  frame = %{continuation.frame | stack: [value | continuation.frame.stack]}
  run(frame, continuation.execution)
end
def resume_raw(%Continuation{} = continuation, {:error, reason}) do
  raise_js_from_caller(reason, continuation.frame, continuation.execution)
end
```

**Flow:** `await` with no `%Boundary.Async{}` in `execution.callers` → `suspend_promise` inspects the awaited promise NOW: pending → `{:suspended, %Continuation{awaiting: promise}}` returned to the host; already settled → the result is queued as a job and the continuation suspends with `awaiting: :microtask` (never blocks). Host parks on `receive` → each `{:quickbeam_vm_host_reply, ...}` is folded into `execution` via `Async.settle_host_reply/3` (stale replies are dropped and the loop continues) → when the awaited promise leaves `:pending`, its settled result is enqueued as a job, `awaiting` flips to `:microtask`, and driving resumes → `Interpreter.resume/2` pushes the settled value onto the captured frame's stack and re-enters `run/2` with the captured execution; an `{:error, reason}` resume raises through the captured caller stack instead.
**Invariant:** the continuation is a pure snapshot — resume must reuse `continuation.execution` as-is (plus folded host replies); nothing else in the process may have mutated it, because the record is the only copy of the evaluation state. A settled promise must NEVER produce a blocking continuation (`suspend_promise` checks state before constructing the record). `resume/2` vs `resume_raw/2` differ only in `finish/1` export; the in-process job loop must use the raw form or the evaluation would export mid-microtask.
**Probe:** `test/vm/runtime/interpreter_test.exs` "captures and resumes the full caller stack across a nested await" (:236-246) — `{:suspended, %Continuation{}}` out of `Interpreter.eval/2` with a pending host var, `continuation.execution.callers` still holds the caller frame, `Interpreter.resume(continuation, {:ok, "resumed"})` → `{:ok, "resumed"}`. Same file :248-262 pins that a rejected nested await unwinds into an outer catch across the resume boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Continuation suspend_promise await_legacy_promise resume_raw", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the snapshot-continuation shape: one struct holding {frame, full execution state, awaiting marker} with exactly two constructors and a resume that pushes the settled value onto the captured stack. Adapt the `awaiting` duality (promise-ref vs `:microtask`) to your host's reply protocol; the `{:quickbeam_vm_host_reply, ...}` message name is QuickBEAM-specific. Omit the legacy path entirely if your host always has async boundaries — the detached `%Coroutine{}` path (see async-boundary-detach-resume) is the modern seam and this one exists for host-var awaits without a boundary. Caveat: no dedicated continuation_test.exs exists; coverage is via interpreter_test ranges + async.ex unit paths (direct-read fallback, no graph coverage check in-session). `%Frame{}`'s `compiler_*` re-entry flags matter only to `resume_deopt_raw/1`, which validates via `Optimization.validate_deopt/1` before trusting them.

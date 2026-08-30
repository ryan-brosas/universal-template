<!-- capsule-v2 -->
# exception-boundary-settlement-map — When a throw crosses a mid-flight JS boundary (thenable, reaction, executor, iterator, async), which promise settles and what action resumes?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you map "a JS call inside protocol step X threw" to the right settlement (settle vs settle_assimilated, idle vs complete vs rethrow) without leaking the throw past the protocol?

## Boundary throw-settlement seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/exception.ex`: `throw_from_boundary/4` 11 clauses (:116-171); boundary structs `lib/quickbeam/vm/runtime/boundary/{thenable,reaction,promise_executor,then_getter,async,accessor,object_assign,constructor,iterator}.ex` (9 files, all ≤44L); completion counterpart `interpreter.ex` `return_value/2` boundary-pop clauses (:1024-1060) and `complete_call_result` (:479+).
**Signature:** `throw_from(reason, boundary, State.t()) :: action()` — dispatches on the boundary struct type; each clause returns one of `{:run, frame, execution}` | `{:resume_then_getter, boundary, execution}` | `{:complete, value, caller, execution, tail?}` | `{:idle, execution}` | `{:error, JSError.t(), execution}`.
**Data Shape:** the settlement vocabulary: `Promise.settle/3` (plain rejection), `Promise.settle_assimilated/3` (rejection that counts as the assimilation outcome), `Async.complete/3` (async function result), or rethrow into `boundary.caller`. Every boundary struct carries `depth` so unwinding restores `execution.depth = boundary.depth` before continuing.

### Decisive source
```elixir
defp throw_from_boundary(reason, %Boundary.ThenGetter{} = boundary, execution, trace) do
  thrown = thrown(reason, trace)
  execution = Promise.settle_assimilated(execution, boundary.promise, {:error, thrown})
  {:resume_then_getter, boundary, execution}
end

defp throw_from_boundary(reason, %Boundary.Thenable{} = boundary, execution, trace) do
  execution =
    Promise.settle_assimilated(execution, boundary.promise, {:error, thrown(reason, trace)})

  {:idle, execution}
end

defp throw_from_boundary(reason, %Boundary.PromiseExecutor{} = boundary, execution, trace) do
  execution = Promise.settle(execution, boundary.promise, {:error, thrown(reason, trace)})
  {:complete, boundary.promise, boundary.caller, execution, boundary.tail?}
end
```

**Flow (the full map):** `ThenGetter` (the `then` property getter threw) → `settle_assimilated` + `{:resume_then_getter, ...}` so the resolution procedure still runs its post-getter step. `Thenable` (a foreign thenable's `then(resolve, reject)` body threw) → `settle_assimilated` + `{:idle, ...}` — the assimilation is over, nothing resumes. `PromiseExecutor` (executor body threw synchronously) → plain `settle` + `{:complete, promise, caller, ...}` — the caller of `new Promise(...)` gets the rejected promise as the expression value. `Iterator` with `consumer: :promise` → materialize + plain `settle` + `{:complete, promise, ...}`; with `consumer: :set` under a `%Boundary.Constructor{}` caller → rethrow into `constructor.caller` (a throwing iterable aborts `new Set(...)` like any constructor throw). `Reaction` (a then/finally callback threw) → plain `settle` + `{:idle, ...}` — the rejection chain continues via the settled promise's own waiters. `Async` → `Async.complete(boundary, {:error, thrown}, execution)` + `{:async, ...}` — the async function's promise rejects with the thrown value. `ObjectAssign`/`Accessor`/`Constructor`/`Native`/`Frame` → rethrow into `boundary.caller` (these are transparent pass-through boundaries). The mirror-image completion path (`return_value/2` in interpreter.ex) pops the same structs and restores `depth` identically — throw and completion are two exits from one boundary discipline.
**Invariant:** exactly one settlement per boundary type, and the settlement uses the assimilated variant precisely where the spec treats the throw as the resolution outcome (ThenGetter, Thenable) vs the plain variant where it is an ordinary rejection (executor, iterator, reaction); `depth` is restored from `boundary.depth` in every clause before any further throw or resume.
**Probe:** `test/vm/runtime/exception_test.exs:34-62` — thenable throw → `{:idle, execution}` + `Promise.state == {:rejected, %Thrown{value: "then failed"}}`; executor throw → `{:complete, ^executor_promise, ^caller, execution, false}` + rejected state. `test/vm/runtime/promise_test.exs:80-85` — native parity for getter/factory/next/done/value throws inside `Promise.all`; `:86-87` — `return()` close after a throwing `next` (observed gap: not implemented in iterator.ex).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "throw_from_boundary settle_assimilated Boundary.Thenable PromiseExecutor Reaction idle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the settlement map as a table: for each mid-flight-JS boundary in your host, decide (a) which promise or caller receives the failure, (b) settle vs settle-assimilated, (c) what action resumes (idle / complete / rethrow / protocol continuation). The assimilated-vs-plain distinction is the subtle part — getting it wrong double-rejects or stalls the resolution procedure. Adapt boundary struct fields to your state; keep `depth` on every boundary. Omit the Set-consumer arm if you have no resumable Set construction. Caveat: direct-read fallback; the Reaction/Async settlement clauses are exercised via exception_test's async case and promise_test native parity, not by a dedicated per-boundary unit suite.

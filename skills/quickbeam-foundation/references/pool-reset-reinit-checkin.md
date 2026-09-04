<!-- capsule-v2 -->
# pool-reset-reinit-checkin — What makes a pooled JS runtime safe to hand to the next request?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** Where in the pool lifecycle is per-request isolation enforced, and what happens when the reset fails?

## NimblePool reset-on-checkin seam
**Path/Symbol:** `lib/quickbeam/pool.ex:handle_checkin/3` (:88-99), `run/3` (:63-72), `init_worker/1` (:75-80).
**Signature:** `start_link(opts)` with `:size` (default 10), `:init` (fun applied after creation AND after every reset), `:lazy`; `run(pool, fun, timeout \\ 5000)`.
**Data Shape:** Worker state IS the runtime pid; checkout passes it raw; client fun executes inline on the checker-outer process.

### Decisive source
```elixir
def handle_checkin(rt, _from, _old_rt, opts) do
  init_fun = Keyword.get(opts, :init)
  case QuickBEAM.Runtime.reset(rt) do
    :ok ->
      if init_fun, do: init_fun.(rt)
      {:ok, rt, opts}
    {:error, _} ->
      {:remove, :reset_failed, opts}     # ← worker leaves the pool
  end
end
```

**Flow:** checkout → client fun mutates the runtime freely → checkin → FULL reset (fresh JS context) → re-run init fun (reinstall app globals/scripts) → return to pool; reset failure ⇒ remove worker so a poisoned runtime can never be reused.
**Invariant:** (1) Isolation happens at CHECK-IN not check-out — the reset cost lands on the returning request, keeping latency off the critical path of the next borrower only if you accept that trade; porters who move reset to checkout double-pay. (2) init must be idempotent and complete: everything a request needs is installed here, nothing persists from prior requests (pinned by "pool resets state between checkouts" test asserting `typeof globalThis.x == "undefined"`). (3) A crashing CLIENT fun still returns the worker (NimblePool handles it), but a failing RESET removes capacity permanently — size degrades under poison. (4) Default run timeout 5 s bounds checkout wait, separate from any JS eval timeout.
**Probe:** `grep -c '{:remove, :reset_failed' lib/quickbeam/pool.ex` → 1.
**Probe:** direct test `test/core/pool_test.exs` line 16 `test \"pool resets state between checkouts\"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "NimblePool reset checkin init", limit: 10 });
```

## Verdict
Adopt reset-and-reinitialize-on-return as the isolation point for stateful pooled engines; adapt the reset verb to your engine's context-free/reload primitive; keep the remove-on-failed-reset rule. Coverage: pool.ex no_recorded_issue; direct tests test/core/pool_test.exs (5 tests) execute this seam at the pin.

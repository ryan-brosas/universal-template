<!-- capsule-v2 -->
# runtime-genserver-ref-pending — How does a GenServer call into native JS without blocking its own message loop?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the exact reply protocol between `QuickBEAM.eval/3` and the NIF so the GenServer stays responsive while JS runs?

## NIF ref + pending-transform seam
**Path/Symbol:** `lib/quickbeam/runtime.ex:eval/3` (:68-78), shared clauses in `lib/quickbeam/server.ex:handle_call({:eval,...})` (:106-116) and `handle_pending_ref/3` (:78-95).
**Signature:** `eval(server, code, opts \\ []) :: {:ok, term()} | {:error, QuickBEAM.JSError.t()}`; internal `put_pending(state, ref, from, transform \\ nil)`.
**Data Shape:** Every client call → `GenServer.call(..., :infinity)`; handler fires a Native.* NIF that returns immediately with a `reference()`; state gains `pending: %{ref => {from, transform}}`. The NIF later sends `{ref, result}` to the server pid.

### Decisive source
```elixir
def handle_call({:eval, code, timeout_ms}, from, state) do
  ref = nif_eval(state, code, timeout_ms)
  {:noreply, put_pending(state, ref, from, js_error_transform())}
end

defp handle_pending_ref(ref, result, state) do
  case Map.pop(state.pending, ref) do
    {nil, _} -> {:noreply, state}                      # unknown ref: drop silently
    {{from, nil}, pending} -> GenServer.reply(from, result); {:noreply, ...}
    {{from, transform}, pending} -> GenServer.reply(from, transform.(result)); ...
  end
end

def handle_info({ref, result}, state) when is_reference(ref), do: handle_pending_ref(ref, result, state)
```

**Flow:** client call (:infinity timeout) → handle_call invokes NIF (returns ref instantly) → pending map records `{from, transform}` → GenServer loop stays free for other messages → NIF completion message `{ref, result}` arrives → handle_info pops pending, applies transform (`js_error_transform/0` converts raw error maps to `%JSError{}`), replies.
**Invariant:** (1) Client-side timeouts are NEVER used (`:infinity` everywhere); cancellation/deadline is enforced natively via the interrupt handler, not by abandoning the call. (2) Unknown refs are dropped silently — late/duplicate completions must not crash. (3) The transform runs inside the GenServer, so it must be cheap; heavy handler work is dispatched to Tasks elsewhere. (4) eval_with_vars uses the same pattern but its transform ALSO deletes injected globals first — cleanup-on-completion including on error paths.
**Probe:** `grep -c 'put_pending' lib/quickbeam/runtime.ex` → 8.
**Probe:** `grep -c 'Map.pop(state.pending, ref)' lib/quickbeam/server.ex` → 1.
**Probe:** `grep -c ':infinity' lib/quickbeam/runtime.ex` → ≥15 (every client entry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "pending ref transform GenServer reply", limit: 10 });
```
(rank-1 hits: types.send_reply, engine.flush_reply, runtime.receive_host_reply)

## Verdict
Adopt the ref-tagged pending map with per-call transforms and silent unknown-ref drops; adapt the NIF boundary to your host's async-call mechanism; omit QuickJS-specific interrupt plumbing if your engine lacks it. Coverage: both cited paths no_recorded_issue+metadata_match; direct tests test/core/pool_test.exs, test/core/concurrency_test.exs exercise this seam end-to-end.

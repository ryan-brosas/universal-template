<!-- capsule-v2 -->
# server-macro-shared-clauses — How do two server modules share one protocol without a behaviour boilerplate tax?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How is the identical eval/call/DOM/global protocol injected into both Runtime (own OS thread) and Context (pool thread) without duplication?

## `use QuickBEAM.Server` injection seam
**Path/Symbol:** `lib/quickbeam/server.ex:__using__/1` (:64-206); consumers `runtime.ex:use QuickBEAM.Server` (:4) and `context.ex:use QuickBEAM.Server` (:38).
**Signature:** macro injects client APIs (`global_client_api/0`, `dom_client_api/0`), shared `handle_call/cast` clauses, and REQUIRES the consumer module to define private `nif_*` dispatch functions (`nif_eval/3`, `nif_call/4`, `nif_dom_find/2`, `nif_dom_find_all/2`, `nif_dom_text/2`, `nif_dom_html/1`, `nif_reset/1`, `nif_get_global/2`, `nif_set_global/3`, `nif_send_message/2`).
**Data Shape:** Runtime's nif_* call `Native.eval(resource,...)`; Context's call `Native.pool_eval(pool_resource, context_id, ...)` — same arity contract, different native entry points.

### Decisive source
```elixir
defmacro __using__(_opts) do
  quote do
    require QuickBEAM.Server
    QuickBEAM.Server.global_client_api()
    QuickBEAM.Server.dom_client_api()

    defp handle_pending_ref(ref, result, state),  # shared reply machinery
    defp put_pending(state, ref, from, transform \\ nil),
    defp js_error_transform,

    @impl true
    def handle_call({:eval, code, timeout_ms}, from, state) do
      ref = nif_eval(state, code, timeout_ms)          # ← consumer hook
      {:noreply, put_pending(state, ref, from, js_error_transform())}
    end
    # ... reset / get_global / set_global / dom_* / send_message ...
  end
end
```

**Flow:** module does `use QuickBEAM.Server` → gains client fns + shared clauses → compiles only if it defines every nif_* hook → each hook routes to its own native surface (direct resource vs pool+context_id).
**Invariant:** (1) memory_usage is deliberately NOT shared — Runtime unwraps `{:ok,v}→v` while Context returns `{:ok,map}`; the source comment marks this exception explicitly. (2) The hook contract means adding a new protocol verb touches exactly three places (server.ex clause + two nif_* impls). (3) set_global replies :ok synchronously (define_global NIF is sync) — asymmetric with get_global which rides pending; porters copying symmetry break it.
**Probe:** `grep -c 'use QuickBEAM.Server' lib/quickbeam/runtime.ex lib/quickbeam/context.ex` → 1 and 1.
**Probe:** `grep -c 'nif_eval' lib/quickbeam/runtime.ex lib/quickbeam/context.ex` → ≥1 each (hook definitions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "global_client_api dom_client_api __using__ nif hooks", limit: 10 });
```

## Verdict
Adopt the macro-injected-protocol-with-required-hooks pattern for twin servers over different transports; adapt hook names to your native API; omit the DOM client API if your engine has no DOM plane. Coverage: server.ex no_recorded_issue; parity of behavior across both consumers pinned by test/core/{pool_test,context_pool_test}.exs.

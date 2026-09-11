<!-- capsule-v2 -->
# context-bytecode-cache — How do you install the same polyfill bundle into thousands of contexts cheaply?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How does Context avoid recompiling builtin JS for every context while still loading it per-context?

## persistent_term MD5-keyed bytecode cache seam
**Path/Symbol:** `lib/quickbeam/context.ex:get_bytecode/2` (:196-208), `get_bytecode_for/2` (:210-222), `compile_to_bytecode/1` (:224-235), `install_builtins/2` (:182-194).
**Signature:** `key = {__MODULE__, :bytecode, :crypto.hash(:md5, :erlang.term_to_binary(apis))}`; `:persistent_term.get(key, nil)` / `.put(key, bytecodes)`.
**Data Shape:** Value = list of compiled bytecode binaries (QuickJS compile-once artifacts), safe to load into any context on any thread.

### Decisive source
```elixir
defp get_bytecode(apis, js_sources) do
  key = {__MODULE__, :bytecode, :crypto.hash(:md5, :erlang.term_to_binary(apis))}
  case :persistent_term.get(key, nil) do
    nil ->
      bytecodes = compile_to_bytecode(js_sources)   # spins a throwaway apis:false runtime
      :persistent_term.put(key, bytecodes)
      bytecodes
    cached -> cached
  end
end

defp install_builtins(state, apis) do
  js_sources = QuickBEAM.JS.polyfills_for(apis)
  for bc <- get_bytecode(apis, js_sources), do: sync_load_bytecode(state, bc)
  ...
end
```

**Flow:** first Context with an apis combo → compile polyfills once in a temporary bare runtime → cache bytecodes node-wide in persistent_term → every subsequent Context loads (not compiles) them via pool_load_bytecode; group-specific sets (:node, :beam) get their own fixed keys.
**Invariant:** (1) persistent_term is global and effectively immortal — the cache is keyed ONLY by apis tuple + module code version; a hot code upgrade that changes polyfills must change keys (module identity does this implicitly). (2) Compile uses a disposable `QuickBEAM.start(apis: false)` runtime stopped immediately — no ambient runtime dependency. (3) Loading bytecode per-context is still required: compilation is shared, execution state is not. (4) Runtime (the heavyweight path) instead evals JS SOURCE strings — the bytecode fast-path exists precisely because Context creation happens per-connection.
**Probe:** `grep -c 'persistent_term' lib/quickbeam/context.ex` → 4.
**Probe:** `grep -c 'persistent_term' lib/quickbeam/beam_api.ex` → 2 (same primitive reused for UUID atomics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "persistent_term bytecode md5 apis cache", limit: 10 });
```

## Verdict
Adopt compile-once-load-everywhere via a node-global cache keyed by config fingerprint; adapt to your engine's bytecode format stability guarantees (QuickBEAM pins bytecode to the exact vendored QuickJS ABI elsewhere); omit if your contexts boot from source rarely enough that compile cost is negligible. Coverage: context.ex no_recorded_issue+metadata_match.

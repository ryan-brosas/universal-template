<!-- capsule-v2 -->
# wasm-api-handle-table-gen-server — How do you expose NIF-backed WASM modules and instances to a JS guest without leaking references across the boundary?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What handle-table + lazy-singleton GenServer shape lets a JS guest's `WebAssembly.*` builtins compile, instantiate (with host imports), call, and poke linear memory of WASM guests, with integer ids as the only thing that crosses the BEAM/JS boundary?

## Shared handle-table bridge seam
**Path/Symbol:** `lib/quickbeam/wasm_api.ex` whole (473L): `ensure_started/0` (:22-33), state (:36-38), `handle_call` clauses for compile/start/call/memory/globals/custom-sections (:156-319), `terminate/2` (:321-328), id allocation (:330-346), prepare pipeline (:348-371), instance start ladder (:382-398), result encoding (:460-472). Wiring: `runtime.ex:194-207` maps `__wasm_*` Beam.call names to these functions (`__wasm_start` uses `{:with_caller, ...}` to capture the JS runtime pid). Contrast plane: `wasm/server.ex` (53L whole-read) + facade `wasm.ex` (189L whole-read) — the per-instance supervised alternative.
**Signature:** `compile([bytes]) :: %{"ok" => id} | %{"error" => msg}`; `start([mod_id, import_payload], caller_pid) :: %{"ok" => inst_id} | %{"error" => msg}`; `call([inst_id, func_name, params]) :: %{"ok" => encoded} | %{"error" => msg}`; memory/global accessors take `[inst_id, ...]`.
**Data Shape:** state `%{next_id: pos_integer(), modules: %{integer() => {mod_ref, bytes, exports, imports, custom_sections}}, instances: %{integer() => {inst_ref, compiled_mod_ref, exports, imports, custom_sections}}}` — ONE shared `next_id` counter for both tables; NIF refs never leave the server process.

### Decisive source
```elixir
def ensure_started do
  case Process.whereis(__MODULE__) do
    nil ->
      case GenServer.start(__MODULE__, :ok, name: __MODULE__) do
        {:ok, _pid} -> :ok
        {:error, {:already_started, _pid}} -> :ok
      end

    _pid ->
      :ok
  end
end

defp start_instance(mod_ref, nil, []), do: QuickBEAM.Native.wasm_start(mod_ref, 65_536, 65_536)

defp start_instance(mod_ref, _runtime_resource, []),
  do: QuickBEAM.Native.wasm_start(mod_ref, 65_536, 65_536)

defp start_instance(_mod_ref, nil, [_ | _]),
  do {:error, "runtime resource not available for function imports"}

defp start_instance(mod_ref, runtime_resource, function_imports) do
  QuickBEAM.Native.wasm_start_with_imports(
    mod_ref, runtime_resource, function_imports, 65_536, 65_536
  )
end
```

**Flow:** every JS builtin funnels through `ensure_started` — the server is an UNLINKED lazy singleton (`GenServer.start`, not `start_link`, so a dying caller cannot take the table down; it is also a supervised app child at `application.ex:19`, and `ensure_started` tolerates `:already_started`) → `compile` stores the NIF module ref plus metadata extracted by the PURE parser (exports/imports/custom sections normalized to string-keyed maps, `:func`→`"function"`) under a fresh integer id → `start` re-runs the import rewrite (capsule `wasm-import-rewriter-binary-surgery`) against the stored bytes, recompiles the rewritten binary, starts the instance through a four-clause ladder — no imports needs no runtime resource; function imports REQUIRE the caller's `QuickBEAM.Runtime.resource(caller)` (the JS runtime handle the NIF calls back into) and error explicitly when absent → imported memory bytes are written at offset 0 AFTER start (exactly one memory import allowed) → `call` looks up the export by name+kind to get the result types, then encodes results: i64 integers become STRINGS so the JS side materializes BigInts, multi-value results zip value×type → `terminate/2` stops every live instance ref, so no WAMR instance outlives the table.
**Invariant:** (1) Only integer ids cross the BEAM/JS boundary — NIF refs, binaries, and export maps stay inside the server; a guest cannot address another guest's memory except through its own id. (2) The single shared `next_id` counter makes module ids and instance ids mutually unique, so a flat id space is safe for any future lookup-by-id API. (3) Function-import instantiation is refused rather than silently dropped when the caller's runtime resource is unavailable — the four-clause ladder makes "imports present but no callback target" a typed error. (4) Two hosting shapes coexist over the same NIF: this shared table (JS builtins, many guests per process) vs `WASM.Server` (one supervised GenServer per instance with `child_spec/1`, `terminate` stopping its instance, memory ops as plain `handle_call`s) — adopt whichever matches your supervision story; they are not interchangeable mid-flight because refs are process-local. (5) i64-as-string encoding is the wire contract for BigInt fidelity; changing it silently breaks 64-bit arithmetic in the guest.
**Probe:** `grep -n 'def ensure_started\|def terminate\|defp put_module\|defp put_instance\|defp start_instance\|defp encode_scalar' lib/quickbeam/wasm_api.ex` → 6 hits (:22/:321/:330/:336/:382/:471); key-def census ×22 executed this pass; `grep -n '__wasm_' lib/quickbeam/runtime.ex` → 14 wiring lines (:194-207).
**Probe:** `test/wasm_test.exs:980-1075` — `WebAssembly.compile` + `instantiate` round-trip, `WebAssembly.validate`, `Module.exports/imports`, multiple instances from the same module id, and i64 exports arriving as BigInt (`1n << 63n` class assertions); `:1108-1122` exported memory identity + byte readback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "WasmAPI ensure_started next_id modules instances start_instance runtime_resource", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the integer-handle-table pattern for any NIF-backed resource exposed to an embedded language: one GenServer owns all native refs, ids are the only currency across the boundary, and `terminate` drains every resource so nothing leaks past process death. Adopt the unlinked-lazy-singleton `ensure_started` when the resource must outlive any single caller but also has a supervised home (tolerate `:already_started`). Adopt the explicit "callback target required" clause for any host-import feature — refuse, don't degrade. Adapt the 64 KB stack/heap defaults and the i64-string encoding to your guest language's numeric model; omit the dual hosting shape if you only need one supervision story. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

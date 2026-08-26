<!-- capsule-v2 -->
# Soft-purge-only slot lifecycle — how do you retire generated modules without ever killing a process that still runs them?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How should a bounded generated-module pool evict and reload fixed module slots when live processes may still hold the old code?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/code/lifecycle.ex:retire/1` (lines 36-42), `install/2` (lines 18-32), `ensure_slot_available/1`, `soft_purge/2` (lines 50-61).
**Signature:** `install(module(), Artifact.t()) :: :ok | {:error, term()}`; `retire(module()) :: :ok | {:error, {:live_generated_code, module(), phase}}`.
**Data Shape:** slots are the fixed pool atoms from `Contract.pool_modules()`; `@source ~c"quickbeam_compiler"` stamps every load_binary so generated code is identifiable in the code server.

### Decisive source
```elixir
def install(module, %Artifact{module: module, binary: binary} = artifact) do
  with :ok <- validate_module(module),
       :ok <- Artifact.validate(artifact),
       :ok <- Import.validate(binary),
       :ok <- ensure_slot_available(module),
       {:module, ^module} <- :code.load_binary(module, @source, binary) do
    :ok
  else ...
end

defp ensure_slot_available(module) do
  case :code.is_loaded(module) do
    false -> soft_purge(module, :install)
    _loaded -> {:error, {:compiler_slot_not_retired, module}}
  end
end

defp soft_purge(module, phase) do
  if :code.soft_purge(module), do: :ok, else: {:error, {:live_generated_code, module, phase}}
end

def retire(module) do
  with :ok <- validate_module(module),
       :ok <- soft_purge(module, :old),
       :ok <- delete_current(module) do
    soft_purge(module, :current)
  end
end
```

**Flow:** retirement never hard-purges: `soft_purge(:old)` → delete current (`:code.delete/1`) → `soft_purge(:current)`; any live reference makes soft purge return false and the whole operation fails with `{:error, {:live_generated_code, module, phase}}` — the POOL turns that error into slot quarantine instead of killing the holder. Installation refuses non-empty slots outright (`{:compiler_slot_not_retired, module}`): a slot is retired to emptiness first, then loaded fresh; modules are never overwritten in place.
**Invariant:** no process is ever terminated by slot management; a slot's code is either fully absent or fully current — there is no in-place hot swap. One static slot name legitimately serves many distinct artifacts sequentially (code_test reuses `hd(Contract.pool_modules())` for 25 different keys; final stats `%{ready: 1}`).
**Probe:** `test/vm/compiler/code_test.exs` "soft purge quarantines a slot instead of killing a live code reference": a runner process blocks inside generated code (`receive` template), then stats show exactly `[%{status: :quarantined, reason: {:live_generated_code, ^module, :current}}]`; after releasing the runner, `Lifecycle.retire(module)` returns `:ok`. Also lines 55-59: after checkin + drain, `:code.is_loaded(lease.module) == false`. Probe executed: grep test tree → `live_generated_code` ×1 (line 126); `compiler_slot_not_retired` ×0 in tests (source-only path, lifecycle.ex:53).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "soft purge generated code slot retire install load_binary", limit: 5 });
// observed: lifecycle.soft_purge #1 (lifecycle.ex:57-61), pool.retire_slot #2,
// pool.retire_ready_slot #3, Code.retire #4, lifecycle.retire #5 — rank-exact cluster.
```

## Verdict
Adopt soft-purge-only retirement with quarantine-instead-of-kill semantics and empty-slot-only installation; adapt the quarantine policy owner (here the pool GenServer) and the loader source tag to your host; omit hard purge entirely from eviction paths. Coverage: both cited paths returned `no_recorded_issue` + `metadata_match`.

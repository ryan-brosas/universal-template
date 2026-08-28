<!-- capsule-v2 -->
# vm-facade-locked-engine-delegation — How do you expose a locked-down public facade over an internal engine that supports more than the public contract?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** When an internal engine has capabilities you do not want to promise publicly (a second execution engine, extra metrics fields), how do you delegate without leaking them into the public API?

## Locked-engine delegation seam
**Path/Symbol:** `lib/quickbeam/vm.ex` (facade): `eval/2` (:200-208), `call/4` (:221-236), `measure/2` (:246-256), `measure_call/4` (:271-293), `public_measurement/1` (:322-324), evaluation-option allowlist `@evaluation_options` (:93-102, 8 keys vs the engine's 13); `lib/quickbeam/vm/runtime/engine.ex` `@type option` (:23-29, includes `:engine`, `:compiler_pool`, `:compiler_profile`, `:compiler_region_probe`, `:compiler_regions`).
**Signature:** `VM.eval(program, opts)` = `Engine.eval(program, Keyword.put(opts, :engine, :interpreter))`; `public_measurement(internal_measurement) :: %QuickBEAM.VM.Measurement{}`.
**Data Shape:** public `@evaluation_options` = [:handlers, :isolation, :max_stack_depth, :max_steps, :memory_limit, :profile, :timeout, :vars]; public `%Measurement{}` struct omits `:compiler_counters` and `:compiler_regions` that the internal `%Engine.Measurement{}` carries.

### Decisive source
```elixir
def eval(program, opts) when is_list(opts) do
  with :ok <- Options.validate(opts, @evaluation_options) do
    Engine.eval(program, Keyword.put(opts, :engine, :interpreter))
  end
end

defp public_measurement(measurement) do
  struct(Measurement, Map.from_struct(measurement))
end
```

**Flow:** every public entry validates the caller's options against the PUBLIC (smaller) allowlist first — an unknown option like `engine: :compiler` fails with `{:unknown_option, :engine}` at the facade, before the engine ever sees it → the facade then FORCES `engine: :interpreter` into the options it forwards, so even a future allowlist change cannot select the internal engine through the public path → measurement results come back as the internal struct and are rebuilt with `struct(Measurement, Map.from_struct(m))`, which silently drops the compiler-only fields because the public struct lacks those keys → the compiler engine remains reachable for tests and benchmarks through `Engine.eval/2` directly (release-quarantined, filtered from public ExDoc per the engine moduledoc).
**Invariant:** (1) the public allowlist is a SUBSET of the engine allowlist — validation at the facade is the gate, not the engine; (2) the facade pins the engine choice by overwriting the option, never by trusting the caller to omit it; (3) the public result struct is a projection of the internal one — new internal fields do not become public API by accident; (4) internal helpers stay unexported (`test/vm/api_test.exs` :69-72 asserts `worker_spawn_options` is not a facade function).
**Probe:** `test/vm/api_test.exs` :55-58 (`refute Map.has_key?(measurement, :compiler_counters)` and `:compiler_regions` on a public measurement); :69-72 (internal helper not exported); `test/vm/measurement_test.exs` :6-21 (public measurement carries exactly result/wall_time_us/steps/logical_memory_bytes/process_memory_bytes/reductions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "public_measurement evaluation_options facade engine interpreter Keyword.put", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-allowlist facade: validate against the public subset, then force the internal choice by overwriting the option, and project internal result structs onto smaller public ones — internal capability grows without public API churn. Adopt the `struct(Public, Map.from_struct(internal))` projection idiom. Adapt the option names and struct fields to your host. Omit the direct `Engine.eval` test escape hatch only if you have no quarantined internal engine to test. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); Retrieve block is a documented live-call template, not an executed call.

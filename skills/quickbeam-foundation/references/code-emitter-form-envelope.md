<!-- capsule-v2 -->
# Emitter form envelope — how do untrusted abstract forms become a loadable BEAM module binary without ever reaching `:compile.forms` unchecked?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What gates must abstract Erlang forms pass before a generated module is compiled, and which compile options keep the output deterministic and warning-free?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/code/emitter.ex:Emitter.emit/3` (lines 26-34, gates at 38-134).
**Signature:** `emit(binary(), module(), Template.t()) :: {:ok, Artifact.t()} | {:error, term()}`.
**Data Shape:** input = SHA-256 artifact key (byte width pinned to `Contract.artifact_key_bytes`), a slot atom from the fixed 32-slot pool, and a `%Template{forms: [tuple()]}` whose `:module` attribute is the reserved `QuickBEAM.VM.Compiler.Code.Placeholder` atom; output = validated `%Artifact{}` or one of six typed error tuples — never a raise.

### Decisive source
```elixir
def emit(key, module, %Template{forms: forms}) do
  with :ok <- validate_key(key),
       :ok <- validate_module(module),
       {:ok, forms} <- prepare_forms(forms, module),
       {:ok, binary} <- compile_forms(forms, module),
       :ok <- Import.validate(binary) do
    Artifact.new(module, binary)
  end
end

defp compile_forms(forms, module) do
  options = [:binary, :deterministic, :no_ssa_opt, :return_errors, :return_warnings]
  case :compile.forms(forms, options) do
    {:ok, ^module, binary} -> {:ok, binary}
    {:ok, ^module, binary, []} -> {:ok, binary}
    {:ok, ^module, _binary, warnings} -> {:error, {:generated_module_warnings, warnings}}
    ...
```

**Flow:** key width check → slot ∈ `Contract.pool_modules()` → form count ≤5,000 (`{:compiler_resource_limit,:forms,n,5000}`) → `:erlang.external_size/1` ≤8 MiB (`:form_bytes`) → top-level whitelist (`{:attribute,…}` only for module/export/file; `{:function,name,arity,clauses}` with atom name + non-negative arity + list clauses; `{:eof,_}`; anything else `{:unsupported_compiler_form, form}`) → exactly one `:module` attribute equal to the Placeholder atom → exports exactly `[[{:run,3}]]` → rewrite ONLY the `:module` attribute to the leased slot atom → `:compile.forms` → import allowlist → artifact.
**Invariant:** the emitted module is byte-deterministic for identical forms+slot (`:deterministic`), carries no compiler warnings (warnings are errors), and is compiled with `:no_ssa_opt` because affected OTP releases emit invalid register-liveness metadata for these bounded tuple/branch forms — the ordinary BEAM validator still checks every emitted module.
**Probe:** `test/vm/compiler/code_test.exs` "rejects malformed module attributes, exports, and artifact digests" pins `{:error, {:invalid_compiler_module_attributes, [Other.Generated.Module]}}` and `{:error, {:invalid_compiler_exports, [[other: 3]]}}`. Probe executed: grep `compiler_resource_limit|no_ssa_opt` in emitter.ex → 3 matches (limits at lines 53 & 60, options at line 104).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "emit bounded slot module forms placeholder compile", limit: 5 });
// observed: emitter.compile_forms #1 (emitter.ex:103-122), template.placeholder_module #2,
// profile.scalar.bounded_blocks? #3, bounded_levels? #4, emitter.prepare_forms #5
```

## Verdict
Adopt the five-gate envelope (count → bytes → top-level whitelist → single placeholder attribute → exact entry export) with typed `{:compiler_resource_limit, tag, actual, max}` errors and warnings-as-errors; adapt the specific limits (5000 forms / 8 MiB) and the reserved Placeholder atom name to your host; omit direct reuse of QuickBEAM's `run/3` entry convention if your pool uses a different calling convention. Coverage: both cited paths returned `no_recorded_issue` + `metadata_match`.

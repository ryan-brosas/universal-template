<!-- capsule-v2 -->
# Closed import allowlist — how can a porter guarantee generated code cannot call anything outside a versioned runtime ABI?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you make "generated code may only call the sanctioned runtime" mechanically enforceable rather than a code-review promise?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/code/import.ex:Import.validate/1` (lines 78-87; allowlist at 12-55).
**Signature:** `validate(binary()) :: :ok | {:error, {:disallowed_generated_calls, [{module(), atom(), arity()}]}}` (sorted).
**Data Shape:** input = compiled BEAM binary; internally reads the `:imports` chunk via `:beam_lib.chunks(binary, [:imports])`; the closed allowlist is a compile-time `MapSet` of `{module, fun, arity}` tuples — erlang arithmetic/comparison/guard BIFs (`:*`, `:+`, `:-/1,2`, `<`, `=<`, `==`, `>`, `>=`, `/=`, `element/2`, `setelement/3`, `rem/2`, `is_integer/1`, `is_number/1`, `get_module_info/1,2`) plus ~20 `Runtime` ABI functions (`charge_block/4`, `execute_fast_block/4`, `deopt/4`, `frame_state/1`, …).

### Decisive source
```elixir
def validate(binary) do
  with {:ok, imports} <- imports(binary) do
    rejected = imports |> Enum.reject(&MapSet.member?(@allowed_set, &1)) |> Enum.sort()
    case rejected do
      [] -> :ok
      _calls -> {:error, {:disallowed_generated_calls, rejected}}
    end
  end
end
```

**Flow:** the check runs at TWO points: once inside `Emitter.emit/3` right after `:compile.forms` (a template calling `File.cwd!/0` fails emission itself), and again inside `Lifecycle.install/2` immediately before `:code.load_binary` (defense in depth against a substituted binary).
**Invariant:** every external reference in a shipped generated module is a member of the closed set; adding any new runtime helper or BIF to the tier requires a deliberate, reviewed allowlist edit (the moduledoc demands differential + disassembly coverage for each addition). Rejections name the exact offending MFA tuples.
**Probe:** `test/vm/compiler/code_test.exs:85` pins the exact rejection `{:error, {:disallowed_generated_calls, [{File, :cwd!, 0}]}}` and lines 26-34 pin the positive case — the deopt-only module's full sorted import list equals `[{Runtime, :deopt, 4}, {:erlang, :get_module_info, 1}, {:erlang, :get_module_info, 2}]`. Probe executed: grep over test tree → `disallowed_generated_calls` ×1 (line 85).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "disallowed generated calls import validate", limit: 5 });
// observed: wasm.import_rewriter.validate_import #1-#2,#4-#5 are noise; the seam ranks #3:
// code.import.validate (import.ex:78-87). Natural-language queries on this seam scatter to
// the WASM plane — retrieve with these exact tokens.
```

## Verdict
Adopt post-compilation import-chunk inspection against a closed MapSet with double application (after emit AND before load); adapt the allowlist contents to your runtime's real ABI surface; omit nothing from rejection reporting — always return the sorted rejected MFA list so failures are debuggable. Coverage caveat: this seam's BM25 retrieval is noisy against `wasm/*` import machinery; use the exact query above. Both cited paths returned `no_recorded_issue` + `metadata_match`.

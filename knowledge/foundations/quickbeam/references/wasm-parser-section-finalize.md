<!-- capsule-v2 -->
# wasm-parser-section-finalize — How do you decode an untrusted WASM binary into structured Elixir data without crashing on malformed input?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What parse shape lets a pure-Elixir disassembler turn hostile `.wasm` bytes into `%WASM.Module{}` structs where every failure is a typed `{:error, String.t()}` and unknown opcodes degrade instead of raising?

## Two-phase section-parse → finalize-join seam
**Path/Symbol:** `lib/quickbeam/wasm/parser.ex` whole (934L): magic/version gate (:27-35), section loop (:47-56), section dispatch (:58-133), finalize (:135-166), name extraction (:171-206), import/export enrichment (:208-252), opcode decoder clauses (165 × `decode_one_instruction`, :452-768), 0xFC sub-opcodes (:770-831), LEB128 decoders (:881-915). Facade: `wasm.ex:disasm/validate/exports/imports` (:150-189).
**Signature:** `parse(binary()) :: {:ok, Module.t()} | {:error, String.t()}`; `validate(binary()) :: boolean()`; opcodes as `{offset, name, ...operands}` tuples.
**Data Shape:** `%WASM.Module{version, start, types, imports, exports, functions: [%WASM.Function{index, name, type_idx, params, results, locals, opcodes}], memories, tables, globals, data, elements, tags, custom_sections}`. Function section and code section are stashed separately as struct-map keys (`:_func_type_indices` :78, `:_code_bodies` :113) and joined only in `finalize/1`.

### Decisive source
```elixir
defp parse_sections(<<id, rest::binary>>, mod) do
  {size, rest} = decode_u32(rest)
  <<section_data::binary-size(^size), rest::binary>> = rest

  mod = parse_section(id, section_data, mod)
  parse_sections(rest, mod)
rescue
  MatchError -> {:error, "truncated section (id=#{id})"}
end

defp finalize(mod) do
  func_type_indices = Map.get(mod, :_func_type_indices, [])
  code_bodies = Map.get(mod, :_code_bodies, [])
  names = extract_names(mod.custom_sections)

  num_imports = Enum.count(mod.imports, &(&1.kind == :func))

  functions =
    Enum.zip(func_type_indices, code_bodies)
    |> Enum.map(fn {{local_idx, type_idx}, {locals, opcodes}} ->
      func_idx = num_imports + local_idx
      type = Enum.at(mod.types, type_idx, %{params: [], results: []})

      %Function{
        index: func_idx,
        name: Map.get(names, func_idx),
        type_idx: type_idx,
        params: type.params,
        results: type.results,
        locals: locals,
        opcodes: opcodes
      }
    end)
  # ...stashed keys deleted; imports/exports enriched with params/results from types
end
```

**Flow:** magic+version gate first (wrong magic → `"not a WASM binary..."`, wrong version → `"unsupported WASM version: ..."`) → the section loop size-slices each section so a truncated payload raises `MatchError` which is rescued ONCE at the loop level into a typed error naming the section id → function/code/data_count sections stash into struct-map keys because WASM orders the function section BEFORE the code section, so functions cannot be built until both arrive → `finalize/1` zips them, offsets every function index by the number of imported functions (the spec's global function-index space), pulls human names from the custom `"name"` section (subsection id 1 only, :171-206), and enriches imports/exports with params/results resolved through the type table → unknown OPCODES degrade to `{:unknown, byte}` / `{:unknown_fc, sub}` tuples instead of raising, so a future-extension binary still parses.
**Invariant:** (1) Every malformed-input path returns `{:error, String.t()}` — the only raise is a `MatchError` that is always caught by the section-loop rescue or by the `{_, <<>>} =` full-consumption matches inside section decoders. (2) The two-phase join is what makes import-offset indices correct: `func_idx = num_imports + local_idx` (test "function indices account for imports" asserts index 1 for a module with one imported function). (3) Unknown-opcode degradation keeps the parser forward-compatible; the price is recorded honestly — an unknown VALTYPE does NOT consume its input byte (:270-271 reconstructs the full input), so a bad type section surfaces later as the misleading `"truncated section"` error rather than a precise one. (4) `_data_count` is parsed and stored (:123) but never cross-checked against the data segment count — deleted silently at finalize (:163); structural validation of that invariant is left to the native compiler. (5) Offsets in opcode tuples are computed by byte-size delta per instruction (:445-447), not maintained by hand.
**Probe:** `grep -c 'defp decode_one_instruction' lib/quickbeam/wasm/parser.ex` → 165; `grep -n ':unknown_valtype\|:unknown_fc\|:unhandled_element_kind\|:unknown,' lib/quickbeam/wasm/parser.ex` → 4 degrade sites (:271/:377/:768/:831); `grep -n '_data_count' lib/quickbeam/wasm/parser.ex` → 3 hits (:21/:123/:163, store+delete only, no check).
**Probe:** `test/wasm_test.exs:626-646` — "parses a minimal add module": hand-assembled 40-byte binary → exact opcode list `[{0,:local_get,0},{2,:local_get,1},{4,:i32_add},{5,:end}]`; `:658-662` import-offset indices; `:693-706` validate true/false/truncated; `:1244-1258` empty module ok, wrong magic + unsupported version exact error prefixes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Parser parse_sections finalize func_type_indices code_bodies wasm", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase "stash then join" shape for any container format whose sections reference each other out of order (function-before-code is exactly that): parse sections into independent stashes, join once at finalize, and keep the join pure so it is testable on synthetic stashes. Adopt the single rescue point at the loop level plus full-consumption `{_, <<>>} =` matches as the cheap hostile-input contract; adopt unknown-opcode tuple degradation for forward compatibility. Adapt the error taxonomy if your port needs precise failures — QuickBEAM's non-consuming unknown-valtype clause shows the failure mode of a catch-all that fails to advance the cursor (misleading downstream error). Omit the data-count cross-check gap deliberately only if your native tier re-validates; otherwise close it in finalize. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

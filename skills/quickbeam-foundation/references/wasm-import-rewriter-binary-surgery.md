<!-- capsule-v2 -->
# wasm-import-rewriter-binary-surgery — How do you inject host-provided imports into an already-built WASM binary before native compilation?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What validation + byte-rewrite pipeline lets a host supply function/memory/global imports for a `.wasm` module whose import section it does not control, and how is that different from the generated-code Import allowlist seam?

## Order-validated import rewrite seam
**Path/Symbol:** `lib/quickbeam/wasm/import_rewriter.ex` whole (403L): `rewrite/3` (:12-28, fast path when both lists empty), `validate_imports/2` (:30-51), per-import matchers (:53-98), memory limit ladder (:100-133), `build_function_imports/1` (:135-149), signature encoding (:151-167), section surgery (:170-236), split/rebuild (:243-276), raw entry splicing (:314-341). Consumed by `wasm_api.ex:prepare_bytes/prepare_module` (:348-371).
**Signature:** `rewrite(bytes, expected_imports, provided_imports) :: {:ok, rewritten_bytes, memory_initializers, function_imports} | {:error, String.t()}` — expected imports come from the pure parser (`WASM.disasm`), provided imports are the host's JS-side payload as string-keyed maps.
**Data Shape:** expected/provided entries `%{"module" => _, "name" => _, "kind" => "function"|"memory"|"global", ...}`; function imports gain `callback_name`; memory imports carry `"bytes"`; output `function_imports` = `%{module_name, symbol: "__qb_wasm_import_<N>", signature: "(ii)i"-style string, callback_name, type_idx}`.

### Decisive source
```elixir
defp validate_imports(expected_imports, provided_imports) do
  expected_imports
  |> Enum.reduce_while({provided_imports, []}, fn expected, {remaining, acc} ->
    case validate_import(expected, remaining) do
      {:ok, merged, rest} -> {:cont, {rest, [merged | acc]}}
      {:error, _} = error -> {:halt, error}
    end
  end)
  |> case do
    {:error, _} = error -> error
    {[], validated} -> {:ok, Enum.reverse(validated)}
    {_extra, _validated} -> {:error, "unexpected extra imports"}
  end
end

defp prepend_section_entries(sections, section_id, imports, encode_fun, decode_fun) do
  new_entries = Enum.map(imports, encode_fun)

  case List.keytake(sections, section_id, 0) do
    {{^section_id, payload}, rest} ->
      existing_entries = decode_fun.(payload)
      insert_section(rest, {section_id, encode_vec_raw(new_entries ++ existing_entries)})

    nil ->
      insert_section(sections, {section_id, encode_vec_raw(new_entries)})
  end
end
```

**Flow:** the pure parser first extracts the module's EXPECTED imports (metadata plane) → `validate_imports` walks expected against provided IN ORDER (WASM import order is semantic): name match, kind match, then kind-specific value validation — functions require a binary `callback_name`, tables are rejected ("not supported yet"), memories require page-aligned bytes plus a four-arm min/max limit ladder (:108-133), globals require type+mutable equality and a typed value → any leftover provided import is an error ("unexpected extra imports") → note the two-name split: the JS layer MINTS the `callback_name` itself (`priv/ts/webassembly.ts:393-401` `registerHostImportCallback` defines the host function as a NON-ENUMERABLE `globalThis` property named `__qb_wasm_import_<N>` from its own sequence) so the NIF can resolve the callback by name; the rewriter's separate `symbol` field (`System.unique_integer`) is the BEAM-side native identifier — same prefix, distinct namespaces → surgery: `split_sections` keeps `{id, payload}` pairs, the original import section is DELETED, a new one is inserted id-ordered (`insert_section` skips custom sections id 0), and memory/global imports are PREPENDED into the existing memory/global sections by re-encoding only the new entries and splicing them ahead of the old ones — old entries are consumed RAW (`take_limits_raw`/`take_global_raw` slice exact byte spans without full decoding, so unsupported sub-features in existing entries survive untouched) → `rebuild` re-emits magic + id + u32 size + payload → the returned `memory_initializers` let the caller write imported memory bytes into linear memory AFTER instance start (wasm_api.ex:373-379, exactly one allowed).
**Invariant:** (1) Order is part of the contract: matching is positional, not by name lookup — a reordered provided list fails with "import order mismatch". (2) Function imports become native host callbacks via unique symbols `__qb_wasm_import_#{System.unique_integer([:positive])}` plus a C-style single-char signature string (`i/I/f/F`); multi-value results RAISE ArgumentError rather than emit an unrepresentable signature (:159-161). (3) The rewrite is total over section structure but conservative over entry contents: existing entries are byte-preserved, never re-serialized from decoded values. (4) Disambiguation vs the compiler Import seam: `code/import.ex` (capsule `code-import-closed-allowlist`) validates BEAM `:imports` chunks of GENERATED ELIXIR modules against a closed MFA MapSet after compilation; this rewriter validates WASM BINARY import sections BEFORE native compilation. Same "closed boundary" idea, opposite direction (one restricts what generated code may call; this defines what the guest may call into the host).
**Probe:** `grep -n 'def rewrite\|defp validate_imports\|defp build_function_imports\|defp prepend_section_entries\|defp take_limits_raw\|defp take_global_raw' lib/quickbeam/wasm/import_rewriter.ex` → 6 hits (:14/:30/:135/:217/:314/:329); `grep -c '__qb_wasm_import' lib/quickbeam/wasm/import_rewriter.ex` → 1 (:143); `grep -n '__qb_wasm_import' priv/ts/webassembly.ts` → 1 (:395, JS-side callback minting); key-def census ×22 executed this pass.
**Probe:** `test/wasm_test.exs:1124-1180` — JS `WebAssembly.instantiate` binding tests: immutable global identity (`instance.exports.base === global`), mutable global write-through (`[true, 7, 7]`), sync AND async function imports, memory identity with pre-written byte 65, and non-function import object → `TypeError`; `:1207-1217` bulk-memory opcodes compile through the rewritten path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "ImportRewriter rewrite validate_imports prepend_section_entries __qb_wasm_import", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-stage shape for any "host injects dependencies into a foreign binary format": (a) parse the artifact's declared needs with your READ-ONLY decoder, (b) validate provided values positionally with kind-specific ladders before touching bytes, (c) rewrite structurally while preserving unknown content byte-for-byte (raw-entry splicing) so the rewriter never has to understand every sub-feature of the format. Adopt unique-symbol + explicit-signature-string encoding for bridging host callbacks into a C-ABI world, and fail loud (raise) when the signature space cannot represent the request. Adapt the page-alignment/limit constants to your memory model; omit the fast path if your caller already short-circuits empty imports. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.

<!-- capsule-v2 -->
# value-utf16-wtf8-string-model — How do you give JavaScript strings UTF-16 code-unit semantics while storing them as ordinary Elixir binaries?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you implement JS string indexing/slicing/length over UTF-16 code units when your runtime stores strings as UTF-8 binaries, including lone surrogates?

## WTF-8 ↔ UTF-16 code-unit seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/string/utf16.ex` (102L): `length/1` (:11-13), `at/2` (:16-23), `char_code_at/2` (:26-29), `from_units/1` (:32-34), `slice/3` (:37-42), `decode/2` 6 clauses (:49-73), `encode_units/2` surrogate-pair join (:76-84), `encode_unit/1` (:86-91), `encode_scalar/1` (:93-95). Consumers: `value.ex` string ops (`string_length` :314, `string_at` :317, `string_slice` :320, `string_char_code_at` :323, `string_from_units` :326, `string_from_char_codes` :329-332) and `property.ex` binary receiver arms (:66-72).
**Signature:** `at(binary(), integer()) :: binary() | :undefined`; `char_code_at(binary(), integer()) :: non_neg_integer() | :nan`; `from_units([non_neg_integer()]) :: binary()`; `slice(binary(), non_neg_integer(), non_neg_integer()) :: binary()`.
**Data Shape:** A JS string IS an Elixir binary in WTF-8: valid scalar values use standard UTF-8; a LONE surrogate (0xD800–0xDFFF without its pair) is encoded as a 3-byte sequence in the 0xED 0xA0–0xBF range. Code units are decoded to a list of integers per operation; there is no persistent code-unit array.

### Decisive source
```elixir
defp decode(<<first, second, third, fourth, rest::binary>>, units)
     when first in 0xF0..0xF4 do
  codepoint =
    (first &&& 0x07) <<< 18 ||| (second &&& 0x3F) <<< 12 |||
      (third &&& 0x3F) <<< 6 ||| (fourth &&& 0x3F)

  scalar = codepoint - 0x10000
  high = 0xD800 + (scalar >>> 10)
  low = 0xDC00 + (scalar &&& 0x3FF)
  decode(rest, [low, high | units])
end

defp decode(<<byte, rest::binary>>, units), do: decode(rest, [byte | units])
```

**Flow:** a JS string operation (`"😀".length`, `s[0]`, `charCodeAt`, `slice`, `String.fromCharCode`) routes through `Value.string_*` → `UTF16.units/1` decodes the WTF-8 binary into a flat list of UTF-16 code units (4-byte scalars split into high+low surrogates; a 3-byte 0xED-prefixed sequence decodes via the fallback clause to its lone-surrogate unit) → the operation is list arithmetic (`length`, `Enum.at`, `Enum.slice`) → `encode_units/2` re-encodes, joining adjacent surrogate pairs back into a 4-byte scalar and encoding unpaired units as 3-byte WTF-8 → the result is an ordinary binary again.
**Invariant:** the code-unit list is the semantic index space — `length("😀") == 2`, `s[0]` is the high surrogate — and every decode/encode round-trip is lossless, including lone surrogates, so a string can cross the QuickJS NIF boundary unchanged; out-of-range reads return `:undefined` (or `:nan` for charCodeAt), never raise.
**Probe:** `test/vm/runtime/value_test.exs:100-110` — `Value.string_length("😀") == 2`, `string_at("😀", 0) == <<0xED, 0xA0, 0xBD>>` (the lone high surrogate in WTF-8), `string_char_code_at("😀", 0) == 0xD83D`, `string_from_char_codes([0x1D83D]) == high_surrogate`; `test/vm/runtime/property_test.exs:41` — `Property.get("😀", "length") == 2` and `Property.get("😀", 0)` returns the surrogate binary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "UTF16 units decode encode surrogate from_units string_at char_code_at", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the WTF-8 storage convention — it is the only binary encoding that keeps lone surrogates representable while staying byte-compatible with the QuickJS conversion boundary. Adopt decode-per-operation (no cached unit arrays) for a value-semantics host. Adapt the per-call list materialization if your host needs O(1) indexing — you would need an explicit rope or unit-array representation instead. Omit the fallback `decode(<<byte, …>>)` catch-all only if your strings are guaranteed well-formed. Caveat: direct-read fallback (Codebase Memory MCP not connected this session).

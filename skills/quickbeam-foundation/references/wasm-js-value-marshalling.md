<!-- capsule-v2 -->
# wasm-js-value-marshalling — How should a JS WebAssembly façade marshal values across a NIF boundary that has no native i64?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do arguments and results cross the QuickJS→Zig NIF line when i64 cannot be represented natively, and where is the argument-count check?

## i64-as-BigInt/string wire seam
**Path/Symbol:** `priv/ts/webassembly.ts` (648L): `encodeArgs/2` (:464-471), `encodeScalar/2` (:473-486), `decodeResult/2` (:488-497), `decodeScalar/2` (:499-502), `decodeNumericScalar/2` (:504-514), `toInteger/2` (:516-520), `qbWasmCall/2` (:559-565), `wasmToUint8Array/1` (:567-574), export-call wrapper in `buildExports` (:413-421), streaming `toArrayBufferFromResponseLike` + `compileStreaming`/`instantiateStreaming` (:607-635). BEAM-side twin: `lib/quickbeam/wasm_api.ex:460-472` encodes i64 as decimal string (capsule wasm-api-handle-table-gen-server).
**Signature:** `encodeArgs(args: unknown[], params: ValueType[]): unknown[]`; `decodeResult(value: unknown, results: ValueType[]): unknown`.
**Data Shape:** args/results are positional arrays zipped against the module's param/result `ValueType` lists (`i32 | i64 | f32 | f64`); i64 rides as `bigint` (JS side) or decimal `string`/safe-integer `number` (wire from BEAM).

### Decisive source
```ts
function encodeArgs(args: unknown[], params: ValueType[]): unknown[] {
  if (params.length > 0 && args.length !== params.length) {
    throw new TypeError(`Expected ${params.length} arguments, got ${args.length}`)
  }
  if (params.length === 0) return args
  return args.map((arg, index) => encodeScalar(arg, params[index]))
}

function decodeNumericScalar(value: unknown, type: ValueType): number | bigint {
  if (type === 'i64') {
    if (typeof value === 'bigint') return value
    if (typeof value === 'string') return BigInt(value)
    if (typeof value === 'number' && Number.isSafeInteger(value)) return BigInt(value)
    throw new WebAssembly.RuntimeError('invalid i64 value')
  }
  if (typeof value === 'number') return value
  throw new WebAssembly.RuntimeError(`invalid ${type} value`)
}
```

**Flow:** export call → `encodeArgs` (count checked ONLY when `params.length > 0` — zero-param exports take args verbatim) → `encodeScalar` per param (i32 → `toInteger`; i64 → bigint or `BigInt(toInteger(...))`; f32/f64 must be `number`) → `__qb_wasm_call(handle, name, encodedArgs)` wrapped in `qbWasmCall` (any thrown error becomes `WebAssembly.RuntimeError`) → `decodeResult` zips multi-value results, unwraps single, `undefined` for none → i64 results decode through the three-arm ladder (bigint | decimal string | safe-integer number → BigInt). `wasmToUint8Array` normalizes `Uint8Array`/`ArrayBuffer`/typed views (offset+length preserved) for compile/instantiate inputs. Streaming is NOT streaming: `compileStreaming`/`instantiateStreaming` just `await response.arrayBuffer()` and fall through to the synchronous path.
**Invariant:** no i64 value is ever truncated — the string arm exists because the BEAM side encodes i64 as string, so a port must keep all three decode arms (or prove which arms its wire can produce); errors crossing the NIF are normalized to `WebAssembly.RuntimeError` so JS `instanceof` checks hold.
**Probe:** `test/wasm_test.exs` :1076-1091 (`add64(40n, 2n)` → `typeof result === 'bigint' && result === 42n`), :1092-1107 (f64 `addf64(1.5, 2.25)` with `assert_in_delta`), :1220-1241 (`compileStreaming`/`instantiateStreaming` round-trips through a fake `{arrayBuffer: async () => ...}` response).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "encodeScalar decodeNumericScalar toInteger qbWasmCall i64 BigInt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-arm i64 decode ladder and the params.length-gated arity check (spec-faithful quirk: zero-param exports ignore extra args). Adapt the wire encoding to your NIF's type system — if your NIF has real i64, the string arm becomes dead but harmless. Omit true streaming (this implementation has none; the streaming API is a thin await wrapper). Caveat: `toInteger` rejects non-integer numbers and non-numeric bigints with TypeError, matching WebAssembly spec coercion. Direct-read fallback: whole-file webassembly.ts read + wasm_test decisive ranges + probe census (LinkError ×11 / TypeError ×8 / RuntimeError ×5 throws, callSync ×5, declares ×7 re-grepped); no graph coverage check in-session.

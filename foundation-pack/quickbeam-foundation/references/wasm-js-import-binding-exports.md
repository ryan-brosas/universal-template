<!-- capsule-v2 -->
# wasm-js-import-binding-exports — How do you validate and bind host imports/exports so JS object identity survives instantiation?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Where does each import failure become LinkError vs TypeError, how do function imports cross into the NIF by name, and how does an exported imported-memory stay the SAME JS object the caller passed in?

## Import validation ladder + identity-preserving export binding seam
**Path/Symbol:** `priv/ts/webassembly.ts` (648L): `prepareImports/2` (:281-318), `lookupImportValue/2` (:320-329), `prepareFunctionImport/2` (:331-340), `prepareMemoryImport/2` (:342-371), `prepareGlobalImport/2` (:373-389), `registerHostImportCallback/1` (:394-403), `buildExports/3` (:405-460), `WasmInstance` ctor (:131-155), `WasmMemory` (:175-205), `WasmGlobal` value get/set (:253-278). NIF registration: `lib/quickbeam/wasm_js.zig:97-103` (7 `__qb_wasm_*` C functions via `JS_SetPropertyStr`). Module-level channel: `Beam.callSync('__wasm_*')` ×5 → `runtime.ex:194-196` (`__wasm_compile/validate/prepare_module` → `WasmAPI`). Disambiguation: NOT the compiler Import seam (`code/import.ex` BEAM `:imports` chunk allowlist) and NOT `wasm-import-rewriter-binary-surgery` (BEAM-side byte surgery); this is the JS-side binding façade.
**Signature:** `prepareImports(imports: ImportInfo[], importObject?: ImportObject): { payload, boundMemories, boundGlobals }`; `buildExports(instHandle, exportList, preparedImports?): Record<string, Function | WasmMemory | WasmTable | WasmGlobal>`.
**Data Shape:** `payload` rows go to the NIF start call; `boundMemories`/`boundGlobals` are `{index, object}` pairs matched against export `index`es after instantiation; function imports travel only as a minted `callback_name` string.

### Decisive source
```ts
function registerHostImportCallback(value: Function) {
  const callbackName = `__qb_wasm_import_${++wasmImportCallbackSeq}`
  Object.defineProperty(globalThis, callbackName, {
    configurable: true,
    enumerable: false,
    writable: true,
    value
  })
  return callbackName
}

// WasmInstance ctor, after __qb_wasm_start succeeds:
for (const binding of prepared.boundMemories) {
  if (binding.memory._handle === null) {
    binding.memory._buffer = null
    binding.memory._handle = this._handle
  }
}
this.exports = buildExports(this._handle, WasmModule.exports(module), prepared)

// buildExports, memory export:
const importedMemory = preparedImports?.boundMemories.find((b) => b.index === exp.index)
exports[exp.name] =
  importedMemory?.memory ??
  new WasmMemory({ initial: exp.min ?? 0, maximum: exp.max ?? undefined }, instHandle)
```

**Flow:** `new WasmModule(bytes)` asks BEAM for the import list (module-level channel) → `prepareImports` walks imports: missing `importObject`/module/name → LinkError; table imports → LinkError (unsupported); memory too small / exceeds max / incompatible max → LinkError; global type/mutability mismatch → LinkError (11 LinkError throw sites total); non-function function-import, non-Memory, non-Global, immutable-global set → TypeError (8 sites). Function imports mint a unique `__qb_wasm_import_N` globalThis property (configurable, non-enumerable) whose NAME crosses to the NIF — the NIF looks the function up by name at call time. Memory imports ship `{min: currentPages, max, bytes}` for the BEAM-side rewriter (capsule wasm-import-rewriter-binary-surgery). After `__qb_wasm_start`, bound memories get `_handle` rebound to the instance (buffer cache dropped), and `buildExports` REUSES the same WasmMemory/WasmGlobal object when an export references that import by index (globals additionally get `_handle`/`_name` rebound so reads/writes hit the instance). Dual channel: module ops via `Beam.callSync('__wasm_*')` → Elixir WasmAPI handle table; instance ops via the 7 `__qb_wasm_*` C functions living in the NIF — instance refs never enter Elixir.
**Invariant:** identity preservation — `instance.exports.mem === importedMemory` and `instance.exports.base === importedGlobal` (tests assert `=== true`); a LinkError-vs-TypeError port must keep the split (shape/missing = LinkError, wrong JS value type = TypeError); the minted callback name must stay resolvable on globalThis for the lifetime of the instance.
**Probe:** `test/wasm_test.exs` :1125-1134 (immutable global identity `[instance.exports.base === global, ...value]`), :1136-1146 (mutable global write-back `7 === 7`), :1148-1157 (function import `run(41) → 42`), :1159-1168 (async function import), :1170-1181 (memory import identity + byte `65` visible), :1183-1196 (non-function import → `err.name == "TypeError"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "prepareImports registerHostImportCallback buildExports boundMemories LinkError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the identity-preserving binding pattern: record `{index, object}` pairs at import time, rebind handles post-start, and reuse the imported object when an export references it by index. Adopt the name-minting trick for function imports when your FFI can only pass strings. Adapt the LinkError/TypeError split to your error taxonomy but keep the distinction (spec requires it). Omit table imports (unsupported, LinkError) and note the caveat that the globalThis callback registry is never cleaned up (bounded by module lifetime). Direct-read fallback: whole-file webassembly.ts read + wasm_js.zig registration range + wasm_test import-binding ranges + probe census (LinkError ×11, TypeError ×8, declares ×7, zig registrations ×7 re-grepped); no graph coverage check in-session.

<!-- capsule-v2 -->
# Dual-environment byte codec — how does one UTF-8 conversion API serve both Node and browser without per-call branching?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are Uint8Array↔string conversions implemented once for two runtimes, and why reuse encoder instances?

## Module-level feature detect picks TextEncoder/Decoder pair or Buffer twins; exported as mutable let bindings assigned once
**Path/Symbol:** `app/common/arrayToString.ts`: whole file (28L) — detect (:11), reused decoder/encoder consts (:13–14), Node fallback (:22–27).
**Signature:** `arrayToString(data: Uint8Array): string`; `stringToArray(str: string): Uint8Array`.
**Data Shape:** Mutable `export let` bindings — assigned exactly once at module init (no live-swap contract).

### Decisive source
```ts
declare const TextDecoder: any, TextEncoder: any;
if (typeof TextDecoder !== "undefined") {
  // Note that constructing a TextEncoder/Decoder takes time, so it's faster to reuse.
  const dec = new TextDecoder("utf8");
  const enc = new TextEncoder("utf8");
  arrayToString = function(uint8Array: Uint8Array): string { return dec.decode(uint8Array); };
  stringToArray = function(str: string): Uint8Array { return enc.encode(str); };
} else {
  arrayToString = function(uint8Array: Uint8Array): string { return Buffer.from(uint8Array).toString("utf8"); };
  stringToArray = function(str: string): Uint8Array { return new Uint8Array(Buffer.from(str, "utf8")); };
}
```

**Flow:** sandboxed/grist-core builds compile this shared module into BOTH the browser bundle and the server/sandbox bundles; the typeof check resolves at first load in whichever runtime hosts it. Consumers (uploads, exports, doc parsing) call one API everywhere.
**Invariant:** Encoder CONSTRUCTION is hoisted deliberately (comment: construction is expensive) — a porter creating encoders per-call regresses hot paths. The Buffer branch wraps in `new Uint8Array(...)` because Buffer IS a Uint8Array subclass but consumers expect plain views (structured-clone/serialization safety). The `declare const` shim keeps TS happy when globals are absent at compile time but present at runtime.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "takes time" app/common/arrayToString.ts && grep -n "Buffer.from(uint8Array)" app/common/arrayToString.ts'` → :12 comment; :23 fallback.
Direct tests: no dedicated spec (trivial codec) — stated coverage caveat; exercised via upload/export suites.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"arrayToString stringToArray Uint8Array utf8","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the hoisted-instance pattern and plain-view wrapping; adapt detection to your bundler targets; omit only if you target a single runtime.

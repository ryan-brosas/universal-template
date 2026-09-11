<!-- capsule-v2 -->
# Code-mode sandbox semantics — fresh scope, type stripping, JSON-only results, and what the model's program may assume

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What execution semantics does the QuickJS-backed sandbox guarantee to generated programs?

## Per-invocation world + type-stripped TS
**Path/Symbol:** `packages/code-mode/src/run-code-mode.ts` — wrapping IIFE in `createCodeModeSource` (:211), `assertSourceSize` (:194–202); direct behavior pinned by `packages/code-mode/src/core.test.ts` (:10–90) and exceptions tests.
**Signature:** program = async body: top-level `await`/`return` legal; result forced through `JSON.parse(JSON.stringify(...))` when non-undefined.
**Data Shape:** limits from execution policy (see byte-expansion capsule); worker cap process-global via `setMaxWorkers` (re-exported, index.ts:34; core.test.ts sets 32).

### Decisive source
```ts
// core.test.ts pins the observable contract:
runCodeMode({ js: 'const value: number = 7; return { value };' })        // → {value:7}
runCodeMode({ js: 'interface Item { value: number }\nconst item = { value: 12 } satisfies Item;\nreturn item;' }) // → {value:12}
// fresh globals per run:
js: 'globalThis.sharedValue = 123; ...'   then   js: "return globalThis.sharedValue ?? 'missing';" // → 'missing'
```

**Flow:** source size checked against RAW maxSourceBytes before any work (CodeModeSourceTooLargeError) → runner strips TypeScript annotations/interfaces/satisfies (no transforms beyond stripping — generics-dependent code won't compile) → executes in a FRESH global scope per invocation (no cross-run leakage; test :63–75) → concurrency capped by process-global workers with CodeModeConcurrencyError mapping → 20 parallel invocations all resolve correctly (:77–90). Available surface per the description contract: JSON.parse/stringify only; NO fetch; host tools exclusively via the proxy. Sandbox syntax errors propagate with `/syntax|unexpected|expression expected/i` messages (exceptions :83–90); runtime throws surface verbatim message-wise (`sandbox exploded`, :92–99) but bigint results REJECT (`1n` is not JSON-serializable, :101–108).
**Invariant:** everything crossing OUT is JSON-serialized twice (sandbox-internal stringify + host payload gate), so the return value's type system is JSON, not JS — Maps, Sets, class instances, symbols cannot survive. A porter adding globals (fetch, console beyond caps) changes the security envelope, not just features; console output has its own byte budget (maxConsoleOutputBytes).
**Probe:** deterministic (repo root): `grep -nF 'resolves.toEqual({ answer: 42 })' packages/code-mode/src/core.test.ts` → `16:`; `grep -cF 'resolves.toEqual(' packages/code-mode/src/core.test.ts` → `3`; `grep -nF 'rejects.toThrow(/syntax|unexpected|expression expected/i)' packages/code-mode/src/exceptions.test.ts` → `89:`; `grep -nF 'rejects.toThrow(/sandbox exploded/)' packages/code-mode/src/exceptions.test.ts` → matches :98 region (`rejects.toThrow(/sandbox exploded/)`); `grep -nF 'resolves.toEqual({ type: ' packages/code-mode/src/tool-invocation.test.ts | head -1` → `68:`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "runCodeMode createCodeModeSource", limit: 3 });` // verified live @9d9a73f: runCodeMode :71-159 rank#1 (createCodeModeSource is closure-local; anchor via its caller)

## Verdict
Adopt fresh-scope-per-invocation, strip-only TS handling, and the JSON-only exit boundary; adapt allowed globals to your isolation layer deliberately (each addition is a security decision); omit nothing.

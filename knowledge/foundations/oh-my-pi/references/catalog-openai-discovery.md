<!-- capsule-v2 -->
# Bounded OpenAI-compatible discovery — how do you fetch `/models` so a stalled endpoint can never hang startup?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** What does a defensive generic `/models` probe look like (timeouts, envelope tolerance, mapper contract)?

## Cancellable-timer deadline + recursive envelope extraction + null-vs-empty contract
**Path/Symbol:** `packages/catalog/src/discovery/openai-compatible.ts:DEFAULT_OPENAI_COMPATIBLE_DISCOVERY_TIMEOUT_MS` (:17), `withOpenAICompatibleDiscoveryTimeout` (:24), `fetchOpenAICompatibleModels` (:141), `extractModelEntriesFromNode` (:244).
**Signature:** `fetchOpenAICompatibleModels<T>(options): Promise<ModelSpec[] | null>` — `null` = transport/protocol failure; `[]` = endpoint responded successfully with no usable models.
**Data Shape:** tolerant envelope `{data?|models?|result?|items?}` or bare array, validated with a minimal type schema (`{id: string >= 1}`); defaults fill `{reasoning: false, input:["text"], zero cost, null limits}`.

### Decisive source
```ts
// Issue #8315: built-in provider managers called this with neither signal
// nor timeoutMs; the no-timeout branch passed signal: undefined, so one
// stalled /models endpoint blocked the awaited discovery pass FOREVER.
// Uses a cancellable timer rather than the native abort-timeout helper so
// successful fast requests don't leave armed signals for concurrent GC.
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(new DOMException("The operation timed out.", "TimeoutError")), timeoutMs);
try { return await run(controller.signal); } finally { clearTimeout(timer); }

// mapModel returning null skips the entry (documented contract); only a
// MISSING mapper falls back to the defaults.
const mapped = options.mapModel ? options.mapModel(entry, defaults, context) : defaults;
```

**Flow:** normalize baseUrl (strip trailing slash) → build headers (Accept + caller's + optional bearer) → fetch under caller signal OR default 10s deadline → parse JSON defensively → extract entries by recursing candidate keys until an array of valid records surfaces → dedupe by id into a Map → sort by id localeCompare → return.
**Invariant:** (1) every failure mode collapses to `null`, never throw — callers treat null as "no dynamic data this cycle"; (2) the deadline arms ONLY when the caller supplied no signal of its own; (3) envelope recursion tolerates nested wrappers (`{data: {models: [...]}}`) but requires every entry to carry a non-empty string id; (4) dedupe keeps LAST occurrence per id.
**Probe:** direct `packages/catalog/test/issue-8315-repro.test.ts:12–40` (regression: capturing fetch asserts the transport received a REAL abort signal when neither signal nor timeoutMs given).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "fetchOpenAICompatibleModels discovery timeout envelope", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the default-deadline-with-cancellable-timer pattern and the null-vs-empty contract for any startup-critical network probe; adapt envelope keys to your providers; omit the type-schema layer if you already validate elsewhere. Coverage caveat: none.

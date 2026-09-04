<!-- capsule-v2 -->
# Warning pipeline — how do provider warnings reach stderr once, in what format, and how does the AI_SDK_LOG_WARNINGS global suppress or replace them?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the exact logging ladder (suppress → custom → default), the one-time info-note latch, and the per-type message formats?

## Global-configured logging ladder
**Path/Symbol:** `packages/ai/src/logger/log-warnings.ts:logWarnings` (:121–161; global read :127).
**Signature:** `logWarnings({warnings: Warning[], provider?, model?}): void` (type `LogWarningsFunction`, assignable to `globalThis.AI_SDK_LOG_WARNINGS`).
**Data Shape:** Warning = `{type:'unsupported'|'compatibility'|'deprecated'|'other', ...}` discriminated union.

### Decisive source
```ts
if (options.warnings.length === 0) return;
const logger = globalThis.AI_SDK_LOG_WARNINGS;
if (logger === false) return;              // suppression knob
if (typeof logger === 'function') { logger(options); return; }
// first-call info note, then default emission
```

**Flow:** empty ⇒ silent no-op (does NOT count as "first call") → `false` ⇒ suppressed → function ⇒ called with the FULL options envelope (warnings + provider + model) and nothing is emitted by the SDK itself → otherwise emit one-time info note then each warning.
**Invariant:** the global is read PER CALL, so flipping it mid-process takes effect immediately — but the info-note latch (`hasLoggedBefore`) is module state that survives until `resetLogWarningsState()`; a test suite that logs once keeps the note silenced for later assertions. Custom loggers receive raw options and own formatting entirely.
**Probe:** `packages/ai/src/logger/log-warnings.test.ts:38/:70/:88/:172` (suppression, empty-array-not-first-call, custom-function envelope, note-once); byte-exact `grep -n 'AI_SDK_LOG_WARNINGS' packages/ai/src/logger/log-warnings.ts` → hits :10,:87,:111,:127.

## Emission channel + per-type formats
**Path/Symbol:** `packages/ai/src/logger/log-warnings.ts:emitWarning` (:93–107) + `formatWarning` (:53–84).
**Data Shape:** Node `process.emitWarning(msg, {type})` when available, else `console.warn`; deprecation warnings use type `'DeprecationWarning'`.

### Decisive source
```ts
case 'unsupported': {
  let message = `${prefix} The feature "${warning.feature}" is not supported.`;
  ...
}
...
type: warning.type === 'deprecated' ? 'DeprecationWarning' : 'Warning',
```

**Flow:** every call site (embed :233, embedMany :254/:380, rerank :289) invokes logWarnings ONCE per operation with AGGREGATED warnings — chunked embedMany concatenates all chunk warnings before this single call.
**Invariant:** messages are prefixed `AI SDK Warning (provider / model):` with four exact templates plus a JSON.stringify fallback for unknown types — porters who reformat break anyone grepping logs. Because emission rides process.emitWarning, warnings do NOT appear on stdout by default and can be filtered by Node warning type; porters who swap in console.log change stream routing.
**Probe:** `packages/ai/src/logger/log-warnings.test.ts:148/:203/:259` (emitWarning channel, console.warn fallback, per-type formats); byte-exact `grep -n 'hasLoggedBefore' packages/ai/src/logger/log-warnings.ts` → hits :89,:141,:142,:167.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "logWarnings AI_SDK_LOG_WARNINGS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung ladder, empty-array no-op semantics, one-time latch, and exact message templates verbatim — this is user-visible surface where formatting IS contract. Adapt the prefix branding to your host if desired but keep the `process.emitWarning` typing split. Omit nothing (~170 lines). Direct tests cover every rung of the ladder including fallback channels; runner unavailable here (no node_modules).

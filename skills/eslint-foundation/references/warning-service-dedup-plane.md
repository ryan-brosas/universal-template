<!-- capsule-v2 -->
# Warning-service dedup plane — one injectable emitter, typed warning channels, and why workers stub exactly two of them

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0; direct source+test fallback — Codebase Memory MCP not connected this session). **Question:** How do you keep user-facing warnings from firing once per worker thread, and which warning types must a host reproduce for behavioral parity?

## WarningService
**Path/Symbol:** `lib/services/warning-service.js:WarningService` (:15-84); worker stubbing `lib/eslint/worker.js:141-143`; construction `lib/eslint/eslint.js:727`, `lib/config/config-loader.js:310-312`, `lib/linter/linter.js:752`; emit sites `linter.js:778` (inactive flag), `linter.js:1594` (circular fixes), `config-loader.js:635` (empty config), `eslint.js:778` (.eslintignore), `eslint.js:1067` (poor concurrency).
**Signature:** `new WarningService({ emitWarning = globalThis.process?.emitWarning ?? (() => {}) } = {})`; methods `emitCircularFixesWarning(filename)`, `emitEmptyConfigWarning(configFilePath)`, `emitESLintIgnoreWarning()`, `emitInactiveFlagWarning(flag, message)`, `emitPoorConcurrencyWarning(notice)`.
**Data Shape:** every warning carries a stable TYPE string: `ESLintCircularFixesWarning`, `ESLintEmptyConfigWarning`, `ESLintIgnoreWarning`, `ESLintInactiveFlag_<flag>`, `ESLintPoorConcurrencyWarning`. The poor-concurrency body is templated: `"You may ${notice} to improve performance."` — the notice text comes from the lintFiles trichotomy, not the service.

### Decisive source

```js
constructor({
	emitWarning = globalThis.process?.emitWarning ?? (() => {}),
} = {}) {
	this.emitWarning = emitWarning;
}
```

```js
// worker.js — these warnings are always emitted by the controlling thread.
const warningService = new WarningService();
warningService.emitEmptyConfigWarning =
	warningService.emitInactiveFlagWarning = () => {};
```

**Flow:** the ESLint constructor creates one WarningService (:727) and threads it into `createLinter` and `createConfigLoader`; ConfigLoader defaults its own instance when none is injected (:310-312); Linter defaults likewise (:752). Each method forwards a fixed message + type to the injected emitter. In worker threads the SAME config files are re-loaded and the SAME flags re-processed as on the main thread, so `emitEmptyConfigWarning` and `emitInactiveFlagWarning` would fire redundantly — worker.js overwrites those two INSTANCE PROPERTIES with no-ops (not subclassing), silencing exactly the duplicated channels while `emitCircularFixesWarning` stays live (fix cycles happen inside the worker's own linting).
**Invariant:** the emitter is injectable at every layer (test seam + non-Node safety: the default falls back to a no-op when `process` is undefined, so Linter-only methods never throw outside Node); warning TYPES are part of the observable contract and must not be renamed; dedup is achieved by muting the DUPLICATED channels at the consumer, never by suppressing inside the service.
**Probe:** `tests/lib/services/warning-service.js` — 5 passing (sinon-stubbed `process.emitWarning` calledOnceWithExactly per method; "should not throw when `process` is not defined" for the two Linter-only methods). Executed live: all five types captured via injected emitter; worker-style instance stubbing silences the two methods while the live emitter still receives circular-fixes warnings; `new WarningService({})` in Node gets a function emitter.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "WarningService emitWarning emitCircularFixesWarning", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/services/warning-service.js :15-84; lib/eslint/worker.js :141-143 (direct-read confirmed at pin)
```

## Verdict

Adopt one injectable emitter with typed channels and consumer-side muting for duplicated channels; adapt the type strings and message templates to host vocabulary. Omit the non-Node no-op fallback only if your host is Node-only. Critical porting note: if you add worker threads, enumerate which warnings the controlling thread already owns and stub exactly those on the worker instance — stubbing too much hides real worker-local problems (ESLint keeps circular-fix warnings live on purpose).

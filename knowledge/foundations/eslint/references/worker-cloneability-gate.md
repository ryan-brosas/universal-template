<!-- capsule-v2 -->
# Worker cloneability gate — how do you fail fast with named keys when options must cross a structured-clone boundary?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does ESLint decide whether its options object can be shipped to worker threads, and how does it bypass the check internally?

## validateOptionCloneability + disableCloneabilityCheck
**Path/Symbol:** `lib/eslint/eslint.js:validateOptionCloneability(options)` (:662–684), `disableCloneabilityCheck` Symbol (:431–433), constructor gate (:719–728), `fromOptionsModule` bypass (:870).
**Signature:** throws `TypeError` with `error.code = "ESLINT_UNCLONEABLE_OPTIONS"`; message lists offending keys via `Intl.ListFormat("en-US")`.
**Data Shape:** probe = `structuredClone(options)`; on failure, per-key re-probe to NAME the uncloneable subset, sorted.

### Decisive source
```js
try { structuredClone(options); return; } catch { /* continue */ }
const uncloneableOptionKeys = Object.keys(options)
  .filter(key => { try { structuredClone(options[key]); } catch { return true; } return false; })
  .sort();
const error = new TypeError(`The ${uncloneableOptionKeys.length === 1 ? "option" : "options"} ${new Intl.ListFormat("en-US").format(uncloneableOptionKeys.map(key => `"${key}"`))} cannot be cloned. When concurrency is enabled, all options must be cloneable values (JSON values). Remove uncloneable options or use an options module.`);
error.code = "ESLINT_UNCLONEABLE_OPTIONS";
throw error;
// internal bypass: const options = { ...loadedOptions, [disableCloneabilityCheck]: true };
```

**Flow:** constructor checks the gate ONLY when `concurrency !== "off"` AND the sentinel symbol is absent → whole-object probe first (fast path) → per-key diagnosis only on failure.
**Invariant:** the error names the MINIMAL offending key set (whole-probe short-circuit means mixed cases still diagnose per-key) and points at the escape hatch (options module). The Symbol-keyed sentinel is deliberately non-forgeable from config files: `fromOptionsModule` sets it because module-loaded options are passed by URL, not by value. Functions/plugins in options are the canonical uncloneables — this gate exists so workers receive a serializable snapshot instead of failing inside `new Worker` with an opaque DataCloneError.
**Probe:** `tests/lib/eslint/eslint.js` (:406–440 exact-code + exact-message matrix for numeric concurrency and "auto"; both assert `code: "ESLINT_UNCLONEABLE_OPTIONS"` :419/:437).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "validateOptionCloneability disableCloneabilityCheck fromOptionsModule", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.eslint.validateOptionCloneability" });
```

## Verdict
Adopt whenever a host API gains a multi-threaded mode: probe-first + per-key naming + coded error + symbol escape hatch is the complete pattern; omit if your API never crosses process boundaries.

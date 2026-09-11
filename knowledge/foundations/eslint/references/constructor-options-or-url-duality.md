<!-- capsule-v2 -->
# Constructor engine bundle + options-or-URL duality — how does one instance assemble its engine, and how do options cross the thread boundary when they may contain functions?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How do you assemble a per-instance engine bundle once at construction, and transport user options to worker threads when those options may contain non-cloneable functions?

## privateMembers WeakMap bundle + #optionsOrURL object-vs-URL duality
**Path/Symbol:** `lib/eslint/eslint.js`: `privateMembers` module-level WeakMap (:84), `fileRetryCodes` {ENFILE, EMFILE} (:96), `class ESLint` (:693), `#optionsOrURL` field decl (:710, "Only set when concurrency is enabled"), constructor (:716–780: cloneability gate + raw-options store :718–726, linter :727–728, cacheFilePath/lintResultCache :730–739, conditional suppressionsService :741–751, defaultConfigs/configLoader :753–762, 9-field `privateMembers.set` :764–774, `.eslintignore` ctor-time warning :776–779); `static fromOptionsModule` (:864–880); sequential twin `lintFilesWithoutMultithreading` (:605–654); `module.exports.calculateWorkerCount` (file tail). Bypass symbol `disableCloneabilityCheck` (:431). Worker-side consumption: `lib/eslint/worker.js` :71–75 (see worker-file-claim-loop).
**Signature:** `constructor(options = {})`; `static async fromOptionsModule(optionsURL: URL): Promise<ESLint>`; bundle = `{ options, linter, cacheFilePath, lintResultCache, defaultConfigs, configs: null, configLoader, warningService, suppressionsService }`.
**Data Shape:** `#optionsOrURL: ESLintOptions | string | undefined` — the RAW unprocessed options object (direct construction) or the options-module URL string (`fromOptionsModule`); set ONLY when `concurrency !== "off"`.

### Decisive source
```js
// constructor — validate cloneability, then keep the RAW options for workers:
if (!options[disableCloneabilityCheck] && processedOptions.concurrency !== "off") {
    validateOptionCloneability(options);
    // Save the unprocessed options in an instance field to pass to worker threads in `lintFiles()`.
    this.#optionsOrURL = options;
}
...
privateMembers.set(this, {
    options: processedOptions, linter, cacheFilePath, lintResultCache,
    defaultConfigs, configs: null, configLoader: this.#configLoader,
    warningService, suppressionsService,
});
// Check for the .eslintignore file, and warn if it's present.
if (existsSync(path.resolve(processedOptions.cwd, ".eslintignore"))) {
    warningService.emitESLintIgnoreWarning();
}

// fromOptionsModule — second construction path overwrites the field with a URL string:
const options = { ...loadedOptions, [disableCloneabilityCheck]: true };
const eslint = new ESLint(options);
if (options.concurrency !== "off") {
    eslint.#optionsOrURL = optionsURLString;
}
```

**Flow:** processOptions (validate/normalize) → cloneability gate unless bypass symbol → store raw options in `#optionsOrURL` → build linter + cache + conditional suppressionsService (cache-file prefix `"suppressions_"` vs `.cache_` default) → configLoader → ONE WeakMap `set()` of the 9-field bundle (`configs: null` filled lazily on first use) → construction-time `.eslintignore` existence warning. `fromOptionsModule`: URL-instance guard → `(await import(url)).default` → spread with bypass symbol → `new ESLint` → overwrite `#optionsOrURL` with the URL string. At lint time the worker discriminates `typeof === "object"` (raw cloneable options, re-processed via processOptions in-thread) vs string (dynamic-import the URL); the sequential twin `lintFilesWithoutMultithreading` consumes the same bundle via `privateMembers.get` with a shared AbortController + `Retrier(fileRetryCodes, concurrency 100)` over `Promise.all`.
**Invariant:** the RAW unprocessed options — not the processed ones — cross the boundary, because each worker re-runs processOptions itself (a processed copy would double-normalize); `#optionsOrURL` is only populated when concurrency is on (no workers ⇒ nothing to ship); the bypass symbol must travel with module-loaded options or cloneability validation runs twice; the `.eslintignore` warning fires at CONSTRUCTION (before any lint call) on both construction paths; suppressionsService is null unless applySuppressions.
**Probe:** `tests/lib/eslint/eslint.js` (:390–405 "should warn if .eslintignore file is present" — emitESLintIgnoreWarning calledOnce; :9214–9273 "Environment sharing in multithread mode" — SHARE_ENV propagation pinned BOTH directions through a data-URL options module with concurrency 2; :15389–15530 fromOptionsModule suite — ESM/CJS file URLs, data URL, `fromOptionsModule(42)` rejects TypeError, `javascript:` scheme rejected). Live probes this pass: ctor-time `ESLintIgnoreWarning` observed via process.emitWarning for BOTH `new ESLint({cwd})` and `fromOptionsModule(dataURL)`; `fromOptionsModule(42)` → `TypeError: Argument must be a URL object`; data-URL `concurrency: 2` lint (URL path) and direct-ctor `concurrency: 2` lint (object path) both returned all files with identical message counts. Mocha subset `--grep "fromOptionsModule|Environment sharing|warn if .eslintignore"` → 13 passing, 2 pending.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "ESLint constructor privateMembers optionsOrURL fromOptionsModule disableCloneabilityCheck", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.eslint.ESLint.constructor" });
```

## Verdict
Adopt the one-shot WeakMap engine-bundle factory and the raw-options-or-URL duality whenever a host must ship user-supplied options (possibly containing functions) across a thread/process boundary: validate cloneability once, keep the raw form for re-processing in the child, and offer a module-URL escape hatch for non-cloneable configs. Adapt the bypass symbol and the legacy-config warning to your host's history. Omit the `configs: null` lazy slot if your host resolves configs eagerly. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.

<!-- capsule-v2 -->
# SQLite native loader — lazy better-sqlite3 load with ABI-mismatch detection and one-shot rebuild

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an extension load the native better-sqlite3 module when the host Node differs from the one that compiled it — detecting the ABI mismatch, attempting one npm rebuild against the current runtime, and surfacing an actionable recovery path instead of a cryptic load failure?

## Native module loader
**Path/Symbol:** `src/store/sqlite-native.ts` — `loadBetterSqlite3` (183–241), `isBunRuntime` (55–57), `isNativeModuleAbiMismatch` (59–68), `resolveBetterSqlite3PackageRoot` (70–100), `defaultRebuild` (101–133), `formatBetterSqlite3AbiError` (149–178), `BetterSqlite3LoadError` (31–42).
**Signature:** `loadBetterSqlite3(options?: { requireFrom?, requireImpl?, rebuild?, allowRebuild? }) → BetterSqlite3DatabaseCtor`.
**Data Shape:** `BetterSqlite3DatabaseCtor = new (dbPath: string, options?: {readonly?, fileMustExist?, timeout?}) => unknown`. `BetterSqlite3LoadError` carries `code = "BETTER_SQLITE3_LOAD_FAILED"`, `packageRoot`, `causeError`. The ABI-mismatch regex matches `NODE_MODULE_VERSION|was compiled against a different Node.js version|ERR_DLOPEN_FAILED`.

### Decisive source
```ts
// isBunRuntime: compiled Pi cannot resolve better-sqlite3 at all → must use bun:sqlite
export function isBunRuntime() { return "Bun" in globalThis; }

export function isNativeModuleAbiMismatch(error) {
  const message = error instanceof Error ? error.message : String(error);
  if (ABI_MISMATCH_RE.test(message)) return true;
  if (typeof error === "object" && error !== null && "code" in error) {
    if (String(error.code) === "ERR_DLOPEN_FAILED") return true;
  }
  return false;
}

// loadBetterSqlite3 (183-241): try load; on failure, resolve package root + rebuild once
export function loadBetterSqlite3(options = {}) {
  const requireImpl = options.requireImpl ?? createRequire(options.requireFrom ?? import.meta.url);
  const loadOnce = () => unwrapModule(requireImpl("better-sqlite3"));
  try { return loadOnce(); }
  catch (firstError) {
    const packageRoot = resolveBetterSqlite3PackageRoot(requireImpl);
    const canRebuild = options.allowRebuild ?? isNativeModuleAbiMismatch(firstError);
    if (!canRebuild || !packageRoot) {
      if (isNativeModuleAbiMismatch(firstError))
        throw new BetterSqlite3LoadError(formatBetterSqlite3AbiError({ originalError: firstError, packageRoot, rebuildAttempted: false }), { packageRoot, cause: firstError });
      throw firstError;
    }
    const rebuildResult = (options.rebuild ?? defaultRebuild)(packageRoot);
    clearBetterSqlite3RequireCache(requireImpl, packageRoot);
    if (rebuildResult.ok) {
      try { return loadOnce(); }
      catch (secondError) { throw new BetterSqlite3LoadError(formatBetterSqlite3AbiError({ originalError: secondError, packageRoot, rebuildAttempted: true, rebuildDetail: rebuildResult.detail }), ...); }
    }
    throw new BetterSqlite3LoadError(formatBetterSqlite3AbiError({ originalError: firstError, packageRoot, rebuildAttempted: true, rebuildDetail: rebuildResult.detail }), ...);
  }
}

// defaultRebuild (101-133): try `node npm_execpath rebuild better-sqlite3`, then `npm rebuild`
// returns { ok, detail }; spawnSync with 120s timeout, cwd = packageRoot
```

**Flow:** (1) `loadOnce` requires better-sqlite3 (unwrapping a possible `default` export). (2) On failure, resolve the package root by walking up from the resolved entry to the `better-sqlite3` package.json. (3) If the error is an ABI/dlopen mismatch, run one `npm rebuild better-sqlite3` against the current runtime, clear the require cache, and retry load once. (4) If rebuild fails or load still fails, throw a `BetterSqlite3LoadError` with an actionable message naming the runtime, module path, original error, and the exact `cd <root> && npm rebuild better-sqlite3` fix. (5) Non-ABI failures rethrow unchanged.

**Invariant:** the native module is loaded lazily (never at import time) so a resolve/ABI failure surfaces as an actionable error rather than bricking the whole extension; at most one rebuild is attempted; a Bun runtime never attempts better-sqlite3.

**Probe:** `tests/store/sqlite-native.test.ts` — `detects NODE_MODULE_VERSION ABI mismatch errors` (:28), `detects ERR_DLOPEN_FAILED codes` (:40), `rebuilds once on ABI mismatch then succeeds` (:61), `throws BetterSqlite3LoadError with recovery guidance when rebuild fails` (:98), `formats actionable ABI recovery text` (:127), `does not rebuild for non-ABI load failures` (:140). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "loadBetterSqlite3 isNativeModuleAbiMismatch resolveBetterSqlite3PackageRoot defaultRebuild", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy native load, the ABI/dlopen mismatch detection, the one-shot npm rebuild with require-cache clearing, and the actionable error formatting. Adapt the module specifier, the rebuild command, and the error text to the host. Omit the Bun-runtime branch and the `npm_execpath` detection unless a target runs under Bun or a packaged binary.

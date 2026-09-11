<!-- capsule-v2 -->
# Plugin resolution cache & two-root shadowing — how do you cache filesystem discovery without serving stale plugins (issue #4197)?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Plugin discovery walks node_modules on every session start; caching it invites staleness after installs — what exact cache shape makes both fast AND correct?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/loader.ts:getEnabledPlugins` (:176-192), `enabledPluginsCache`/`enabledPluginsCacheKey`/`clearEnabledPluginsCache` (:23-33), `collectPluginsAtRoot` (:77-159), `loadEnabledPlugins` two-root merge (:194-217).
**Signature:** `getEnabledPlugins(cwd, opts?: { home? }): Promise<ScopedInstalledPlugin[]>`; cache = `Map<string, Promise<ScopedInstalledPlugin[]>>` keyed `` `${path.resolve(cwd)}\0${home === undefined ? "" : path.resolve(home)}` ``.
**Data Shape:** per root: union of `package.json#dependencies` keys ∪ `omp-plugins.lock.json#plugins` keys; entries carry `scope: "user" | "project"`; merge = Map keyed by package name, user inserted first, project second (project shadows user).

### Decisive source
```ts
const loadPromise = loadEnabledPlugins(cwd, home);
enabledPluginsCache.set(cacheKey, loadPromise);   // cache the PROMISE, not the result:
try { return await loadPromise; }                  // concurrent callers share one discovery walk
catch (err) {
	if (enabledPluginsCache.get(cacheKey) === loadPromise) {
		enabledPluginsCache.delete(cacheKey);        // evict on failure — no negative caching
	}
	throw err;
}
```
**Flow:** first caller per (cwd, home) starts the walk; others await the same promise. Invalidation is EXTERNAL: module registers `registerPluginCacheInvalidator(clearEnabledPluginsCache)` so install/uninstall/marketplace flows call `clearClaudePluginRootsCache()` and every map entry dies. Enumeration skips: no `node_modules/` → empty; lockfile entry whose tree vanished → skip silently (deleted symlink); non-omp package → skip; `enabled:false` or project-disabled → excluded. issue-4197 test pins all three legs: same-result on repeat, staleness until `clearClaudePluginRootsCache()`, fresh read after.
**Invariant:** never cache a rejected promise (identity-checked delete); cache key must include BOTH cwd and home or tempdir-rooted callers cross-contaminate; project-scope wins by NAME over user-scope, and a disabled project copy does NOT hide the user copy elsewhere (`listInstalledPlugins` marks `shadowedBy` only for enabled project entries).
**Probe:** direct test: `test/issue-4197-plugin-resolution-cache.test.ts` "getEnabledPlugins caches repeated discovery for the same cwd and home until plugin caches clear" (:28-63) whole; anchor-grep at pin: `enabledPluginsCache.set(cacheKey, loadPromise);` loader.ts:183.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.loader.getEnabledPlugins" });
```

## Verdict
Adopt: promise-valued memoization + identity-checked error eviction + externally-registered invalidator hooks called by every mutating flow. Adapt: your invalidator registry; keep the `\0`-joined resolved-path key. Omit: legacy-pi shim reset in the same test's afterEach (compat surface only).

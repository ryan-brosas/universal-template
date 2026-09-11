<!-- capsule-v2 -->
# Positive-only install cache — why must "extension NOT installed" never be persisted, even though "installed" is cached freely?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a capability probe is expensive and its result lives in shared config, which polarity do you cache?

## positive-only-install-cache
**Path/Symbol:** `src/utils/claudeInChrome/setup.ts` (`isChromeExtensionInstalled_CACHED_MAY_BE_STALE` :362-383, `shouldAutoEnableClaudeInChrome` :70-84).
**Signature:** `isChromeExtensionInstalled_CACHED_MAY_BE_STALE(): boolean` — reads `globalConfig.cachedChromeExtensionInstalled` synchronously; kicks a background rescan that writes back.
**Data Shape:** config flag `cachedChromeExtensionInstalled?: boolean` in the user-global config file (shared across machines via settings sync); background write guarded by inequality check to avoid redundant saves.

### Decisive source
```ts
// Only persist positive detections — see docstring. The cost of a stale
// `true` is one silent MCP connection attempt per session; the cost of a
// stale `false` is auto-enable never working again without manual repair.
if (!isInstalled) {
  return
}
```
and the docstring's rationale:
```
Only positive detections are persisted. A negative result from the
filesystem scan is not cached, because it may come from a machine that
shares ~/.claude.json but has no local Chrome (e.g. a remote dev
environment using the bridge), and caching it would permanently poison
auto-enable for every session on every machine that reads that config.
```

**Flow:** `shouldAutoEnableClaudeInChrome()` memoizes once per process: `interactive && CACHED(installed) && (ant || featureFlag)` → the cached read makes startup non-blocking while a fresh filesystem scan (7 browsers × profiles × extension IDs) runs in the background and persists ONLY `true`.
**Invariant:** cache asymmetry follows failure cost — a false-positive cache costs one failed connection attempt per session; a false-negative cache permanently disables auto-enable everywhere the config syncs. Never cache a negative whose cause may be environmental ("this machine happens to lack Chrome") rather than dispositional ("user never installed it").
**Probe:** no upstream test. Deterministic pins: `grep -n "cachedChromeExtensionInstalled" src/utils/claudeInChrome/setup.ts` → :372/:375/:381; comment anchor `grep -n "permanently poison" src/utils/claudeInChrome/setup.ts` → :359.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isChromeExtensionInstalled cachedChromeExtensionInstalled", limit: 10 });
```

## Verdict
Adopt positive-only persistence for any shared-config capability probe. Adapt the storage location to your config system. Omit the specific extension-ID scan internals (see chromium-extension-detection). Coverage caveat: no unit tests upstream.

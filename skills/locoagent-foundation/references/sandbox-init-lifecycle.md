<!-- capsule-v2 -->
# Sandbox init lifecycle — sync promise assignment, settings hot-reload, and the worktree allowWrite carve-out

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the adapter initialize once, hot-reload config on every settings change, and keep wrapWithSandbox from racing initialization — while a git-worktree session still gets working git?

## Initialization & refresh lifecycle
**Path/Symbol:** `src/utils/sandbox/sandbox-adapter.ts` : `initialize` (:733-795), `wrapWithSandbox` (:707-728), `refreshConfig` (:801-806), module state `initializationPromise`/`settingsSubscriptionCleanup`/`worktreeMainRepoPath` (:390-400), `detectWorktreeMainRepoPath` (:425-448).
**Signature:** `initialize(sandboxAskCallback?): Promise<void>` (idempotent via shared promise); `wrapWithSandbox(command, binShell?, customConfig?, abortSignal?): Promise<string>`.
**Data Shape:** `worktreeMainRepoPath: string | null | undefined` — three-state: undefined=unresolved, null=not-a-worktree/detection-failed, string=cached main-repo path.

### Decisive source
```ts
// Create the initialization promise synchronously (before any await) to prevent
// race conditions where wrapWithSandbox() is called before the promise is assigned.
initializationPromise = (async () => {
  try {
    ...
    await BaseSandboxManager.initialize(runtimeConfig, wrappedCallback)
    // Subscribe to settings changes to update sandbox config dynamically
    settingsSubscriptionCleanup = settingsChangeDetector.subscribe(() => {
      const newConfig = convertToSandboxRuntimeConfig(getSettings_DEPRECATED())
      BaseSandboxManager.updateConfig(newConfig)
    })
  } catch (error) {
    // Clear the promise on error so initialization can be retried
    initializationPromise = undefined
    logForDebugging(...)
  }
})()
```

**Flow:** `initialize` returns the existing promise if present (idempotent across REPL/print callers); assigns it SYNCHRONOUSLY before the first await; resolves worktree path once (status cannot change mid-session) BEFORE building config so `refreshConfig()` can stay synchronous; wraps the network ask-callback to enforce `allowManagedDomainsOnly` at EVERY call site rather than in each caller. On failure the promise clears (retryable) and errors only log — sandboxing degrades gracefully instead of crashing startup. `wrapWithSandbox` throws 'Sandbox failed to initialize.' when enabled but never initialized (callers must have awaited initialize). Hot-reload has TWO channels: passive settingsChangeDetector subscription AND active `refreshConfig()` called after permission updates "to avoid race conditions" — pending requests must not slip through with stale config.

**Invariant:** (1) Promise assignment must precede any await or a fast caller sees undefined and throws. (2) The worktree marker match uses `${sep}.git${sep}worktrees${sep}` with `lastIndexOf`, NEVER bare `.git` substring — `/home/user/.github-projects/...` would false-match. Relative gitdir lines are resolved against cwd before matching. (3) Worktree main repo goes into ALLOW-write (git needs index.lock there) while everything else about the fence stays deny-defaulted. (4) `reset()` tears down in reverse order: unsubscribe → clear three-state cache → reset scrub list → clear memoize caches → null the promise → base reset.

**Probe:** anchored at the locoagent repo root — `grep -n 'initializationPromise = (async' src/utils/sandbox/sandbox-adapter.ts` → :762; `grep -n 'initializationPromise = undefined' src/utils/sandbox/sandbox-adapter.ts | head -1` → :787; `grep -n 'settingsChangeDetector.subscribe' src/utils/sandbox/sandbox-adapter.ts` → :779; `grep -n 'worktreeMainRepoPath === undefined' src/utils/sandbox/sandbox-adapter.ts` → :768; `grep -n 'lastIndexOf(marker)' src/utils/sandbox/sandbox-adapter.ts` → :439; `grep -n 'const marker = ' src/utils/sandbox/sandbox-adapter.ts` → :438.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "initialize sandbox initializationPromise worktree detectWorktreeMainRepoPath", limit: 5 });
```

## Verdict
Adopt sync-promise-assignment + retry-on-error clearing + subscribe-AND-refresh dual reload channels as the lifecycle package. Adapt `detectWorktreeMainRepoPath` freely (pure fs parsing) but keep the sep-anchored marker and three-state cache semantics. Omit BaseSandboxManager forwarding (host-specific). Coverage caveat: no upstream unit tests for this file.
